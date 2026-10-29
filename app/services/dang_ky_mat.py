"""Dang ky khuon mat cong nhan (DE_TAI.md muc 7 "Du lieu khuon mat", muc 12 F2).

Quy tac:
  - BAT BUOC da ghi nhan dong y (workers.consent_at) moi cho them mau. Du lieu sinh trac hoc la du lieu ca nhan nhay cam
    (Luat 91/2025/QH15, Nghi dinh 356/2025/ND-CP).
  - Anh mau phai co DUNG 1 khuon mat, score YuNet >= face.enroll_min_score, rong >= face.min_face_px
    (dung lai src/face/enroll.py cua F1). Toi da face.max_samples mau / cong nhan.
  - Chi luu vector 128 so (CSDL) va anh mat da can chinh 112x112 (paths.face_samples/<worker_id>/). KHONG luu anh goc.
  - Them / xoa mau -> xoa bo nho dem cua nhan_dien de lan so khop sau doc lai mau moi.
"""
import re
import shutil
import threading
import uuid
from pathlib import Path

import cv2
import numpy as np
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import utcnow
from app.models import DANG_LAM, FaceSample, User, Worker
from app.services.nhan_dien import NhanDien, vector_to_embedding
from src.face.enroll import Sample, sample_from_image

NOI_DUNG_DONG_Y = (
    "Tôi đồng ý để đơn vị thi công thu thập và lưu ảnh khuôn mặt của tôi (dữ liệu sinh trắc học, là dữ liệu cá nhân "
    "nhạy cảm) dưới dạng vector đặc trưng và ảnh mặt thu nhỏ, chỉ dùng để chấm công và kiểm tra trang bị bảo hộ tại cổng. "
    "Dữ liệu được xoá khi tôi nghỉ việc hoặc khi tôi yêu cầu."
)

CAMERA, UPLOAD = "camera", "upload"


class DangKyMatError(ValueError):
    """Khong them duoc mau (chua dong y, anh khong dat, du mau...). Thong bao tieng Viet de hien len web."""


def _loi_anh(why: str) -> str:
    """Ly do anh khong dat (chu khong dau tu src/face/enroll.py) -> cau tieng Viet co dau."""
    if why == "khong thay mat":
        return "Không thấy khuôn mặt trong ảnh"
    if m := re.match(r"co (\d+) mat", why):
        return f"Ảnh có {m.group(1)} khuôn mặt, cần đúng 1 người"
    if m := re.match(r"diem mat ([\d.]+) < ([\d.]+)", why):
        return f"Khuôn mặt không rõ (điểm {m.group(1)} < {m.group(2)}): nhìn thẳng camera, đủ sáng"
    if m := re.match(r"mat rong (\d+)px < ([\d.]+)px", why):
        return f"Khuôn mặt quá nhỏ ({m.group(1)} px < {m.group(2)} px): đứng gần camera hơn"
    return why


class DangKyMat:
    """face_models: ham tra ve (FaceDetector, FaceEmbedder), goi lan dau khi can (test truyen bo gia).
    Dung bo YuNet/SFace RIENG voi vong lap cong (2 thread dung chung 1 bo OpenCV khong an toan) + khoa."""

    def __init__(self, settings: dict, sample_dir: str | Path, nhan_dien: NhanDien, face_models=None):
        self.face_cfg = settings["face"]
        self.sample_dir = Path(sample_dir)
        self.nhan_dien = nhan_dien
        self._face_models = face_models
        self._models = None
        self._lock = threading.Lock()

    # --- dong y ---
    def ghi_nhan_dong_y(self, db: Session, worker: Worker, user: User) -> Worker:
        if worker.status != DANG_LAM:
            raise DangKyMatError("Công nhân đã nghỉ việc")
        worker.consent_at, worker.consent_by = utcnow(), user.id
        db.commit()
        return worker

    # --- them mau ---
    def so_mau(self, db: Session, worker: Worker) -> int:
        return db.scalar(select(func.count(FaceSample.id)).where(FaceSample.worker_id == worker.id)) or 0

    def kiem_tra(self, db: Session, worker: Worker) -> None:
        """Con them mau duoc khong (dang lam, da dong y, chua du mau). Khong -> DangKyMatError."""
        if worker.status != DANG_LAM:
            raise DangKyMatError("Công nhân đã nghỉ việc, không đăng ký khuôn mặt")
        if worker.consent_at is None:
            raise DangKyMatError("Chưa ghi nhận đồng ý của công nhân: phải tích ô đồng ý trước khi đăng ký khuôn mặt")
        if self.so_mau(db, worker) >= self.face_cfg["max_samples"]:
            raise DangKyMatError(f"Đã đủ {self.face_cfg['max_samples']} mẫu, xoá bớt mẫu cũ trước khi thêm")

    def mau_tu_anh(self, image: np.ndarray, source: str) -> Sample:
        """Anh BGR -> Sample (vector + anh mat 112x112). Anh khong dat -> DangKyMatError."""
        if image is None or image.size == 0:
            raise DangKyMatError("Không đọc được ảnh")
        with self._lock:
            if self._models is None:
                self._models = self._face_models()
            fd, emb = self._models
            sample, why = sample_from_image(image, fd, emb, self.face_cfg, source,
                                            long_side=self.face_cfg["enroll_long_side"])
        if sample is None:
            raise DangKyMatError(_loi_anh(why))
        return sample

    def luu_mau(self, db: Session, worker: Worker, sample: Sample, source: str) -> FaceSample:
        """Luu 1 mau da kiem tra: vector vao CSDL, anh mat 112x112 ra file."""
        self.kiem_tra(db, worker)
        rel = f"{worker.id}/{uuid.uuid4().hex[:12]}.jpg"
        path = self.sample_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        ok, buf = cv2.imencode(".jpg", sample.thumb, [cv2.IMWRITE_JPEG_QUALITY, 95])
        if not ok:
            raise DangKyMatError("Không lưu được ảnh mặt")
        path.write_bytes(buf.tobytes())
        fs = FaceSample(worker_id=worker.id, embedding=vector_to_embedding(sample.vector), quality=float(sample.quality),
                        thumb_path=rel, source=source)
        db.add(fs)
        try:
            db.commit()
        except Exception:
            path.unlink(missing_ok=True)
            raise
        self.nhan_dien.xoa_bo_nho_dem()
        return fs

    def them_mau(self, db: Session, worker: Worker, image: np.ndarray, source: str) -> FaceSample:
        """Kiem tra dong y / so mau TRUOC khi chay mo hinh, roi lay vector va luu."""
        self.kiem_tra(db, worker)
        return self.luu_mau(db, worker, self.mau_tu_anh(image, source), source)

    # --- xoa ---
    def thumb_file(self, sample: FaceSample) -> Path:
        return self.sample_dir / sample.thumb_path

    def xoa_mau(self, db: Session, sample: FaceSample) -> None:
        path = self.thumb_file(sample)
        db.delete(sample)
        db.commit()
        path.unlink(missing_ok=True)
        self.nhan_dien.xoa_bo_nho_dem()

    def xoa_tat_ca(self, db: Session, worker: Worker, commit: bool = True) -> int:
        """Xoa toan bo mau khuon mat (vector + anh) cua 1 cong nhan. Tra ve so mau da xoa."""
        samples = db.scalars(select(FaceSample).where(FaceSample.worker_id == worker.id)).all()
        for s in samples:
            db.delete(s)
        if commit:
            db.commit()
        folder = self.sample_dir / str(worker.id)
        if folder.is_dir():
            shutil.rmtree(folder, ignore_errors=True)
        self.nhan_dien.xoa_bo_nho_dem()
        return len(samples)
