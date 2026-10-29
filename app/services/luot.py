"""Xu ly 1 luot kiem tra tai cong (DE_TAI.md muc 5 buoc 5-6, muc 7, 8).

GateWorker (thread nen) xong 1 luot -> LuotKiemTra.tu_ket_qua_cong(ket_qua) -> xu_ly_luot(db, luot):
  1. nhan dien: vector khuon mat -> cong nhan (nhan_dien.py) hoac KHONG_NHAN_RA / KHONG_THAY_MAT;
  2. luu anh minh chung vao paths.check_images/<ngay>/<gio>_<ma>.jpg;
  3. ghi ppe_checks (ket qua bao ho, diem nhan dien, ...; KHONG ghi vector);
  4. da nhan ra -> cham_cong.py quyet dinh vao/ra va ghi hoac khong ghi attendance;
  5. tra ve SU KIEN cho man hinh cong: mau (xanh/do/vang), cau thong bao, cong nhan, hanh dong, gio, anh.
"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np
from sqlalchemy.orm import Session

from app.models import PpeCheck, Worker
from app.services.cham_cong import (BO_QUA_TRUNG, GHI_RA, GHI_VAO, KHONG_GHI, KetQuaChamCong, cham_cong_tu_dong,
                                    gio_phut, mui_gio)
from app.services.nhan_dien import NhanDien
from src.checkpoint.evaluate import KHONG_CO_NGUOI, KHONG_DAT, NHIEU_NGUOI

DA_NHAN_RA, KHONG_NHAN_RA, KHONG_THAY_MAT = "DA_NHAN_RA", "KHONG_NHAN_RA", "KHONG_THAY_MAT"
XANH, DO, VANG = "xanh", "do", "vang"
TEN_THIEU = {"thieu_mu": "thiếu mũ bảo hộ", "thieu_ao": "thiếu áo phản quang"}


def json_safe(v):
    """So numpy -> so Python de luu cot JSON."""
    if isinstance(v, dict):
        return {str(k): json_safe(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [json_safe(x) for x in v]
    if isinstance(v, np.generic):
        return v.item()
    return v


@dataclass
class LuotKiemTra:
    """Du lieu 1 luot gui sang backend (DE_TAI muc 5 buoc 4). Test tao truc tiep, khong can camera."""
    thoi_diem: datetime                   # co mui gio
    ket_qua: str                          # sau luat nhieu_mat (src/gate/combine.py)
    thieu: list[str] = field(default_factory=list)
    vectors: np.ndarray = field(default_factory=lambda: np.zeros((0, 128), np.float32))  # toi da 5 vector khuon mat
    anh_jpeg: bytes | None = None
    ly_do: str | None = None
    ty_le_co_mat: dict = field(default_factory=dict)
    thoi_gian_ms: float | None = None
    chi_tiet: dict = field(default_factory=dict)  # so lieu xem lai, KHONG co vector

    @classmethod
    def tu_ket_qua_cong(cls, r: dict, thoi_diem: datetime) -> "LuotKiemTra":
        """Ket qua GateRound.finish (src/gate/round.py) -> LuotKiemTra."""
        km = r["khuon_mat"]
        chi_tiet = {
            "ket_qua_bao_ho": r.get("ket_qua_bao_ho"), "thieu_bao_ho": r.get("thieu_bao_ho"),
            "so_khung": r.get("so_khung"), "so_khung_hop_le": r.get("so_khung_hop_le"), "dem_khung": r.get("dem_khung"),
            "so_khung_co_mat": km.get("so_khung_co_mat"), "ty_le_khung_nhieu_mat": km.get("ty_le_khung_nhieu_mat"),
            "chat_luong_mat": km.get("chat_luong"), "ms_tb": r.get("ms_tb"),
            "tu_luc_thay_mat_ms": r.get("tu_luc_thay_mat_ms"),
        }
        return cls(thoi_diem=thoi_diem, ket_qua=r["ket_qua"], thieu=list(r.get("thieu") or []),
                   vectors=np.asarray(km["vectors"], np.float32).reshape(-1, 128), anh_jpeg=r.get("anh_jpeg"),
                   ly_do=r.get("ly_do"), ty_le_co_mat=dict(r.get("ty_le_co_mat") or {}),
                   thoi_gian_ms=r.get("thoi_gian_ms"), chi_tiet=json_safe(chi_tiet))


def luu_anh(jpeg: bytes | None, image_dir: Path, t: datetime, tz) -> str | None:
    """Ghi anh luot ra file, tra ve duong dan tuong doi (luu vao ppe_checks.image_path)."""
    if not jpeg:
        return None
    local = t.astimezone(tz)
    rel = f"{local:%Y-%m-%d}/{local:%H%M%S}_{uuid.uuid4().hex[:8]}.jpg"
    path = Path(image_dir) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(jpeg)
    return rel


def thong_bao_cong(luot: LuotKiemTra, worker: Worker | None, kq: KetQuaChamCong, tz) -> tuple[str, str]:
    """(mau, cau thong bao) cho man hinh cong (DE_TAI muc 5 buoc 6)."""
    if luot.ket_qua == NHIEU_NGUOI:
        return VANG, "Mời từng người một"
    if luot.ket_qua == KHONG_CO_NGUOI:
        return VANG, "Mời đứng vào vị trí, nhìn vào camera"
    if worker is None:
        return VANG, "Chưa nhận diện được, mời nhìn thẳng camera"
    ten, gio = worker.full_name, gio_phut(luot.thoi_diem, tz)
    if kq.hanh_dong == GHI_VAO:
        return XANH, f"Xin chào {ten}. Đã ghi vào lại {gio}" if kq.vao_lai else f"Xin chào {ten}. Đã ghi giờ vào {gio}"
    if kq.hanh_dong == GHI_RA:
        return XANH, f"Tạm biệt {ten}. Đã ghi giờ ra {gio}"
    if kq.hanh_dong == BO_QUA_TRUNG:
        return XANH, f"{ten}: đã ghi giờ vào {gio_phut(kq.gio_vao_truoc, tz)}, không ghi lặp"
    if luot.ket_qua == KHONG_DAT:  # luot vao khong dat
        return DO, f"{ten}: {', '.join(TEN_THIEU.get(t, t) for t in luot.thieu)}. Chưa ghi công"
    return VANG, f"{ten}: mời đứng yên để kiểm tra lại"  # KHONG_XAC_DINH


def xu_ly_luot(db: Session, luot: LuotKiemTra, *, settings: dict, nhan_dien: NhanDien, image_dir: str | Path,
               gate_id: int | None = None) -> dict:
    tz = mui_gio(settings["attendance"])

    worker, m = None, None
    if len(luot.vectors) == 0:
        face_status = KHONG_THAY_MAT
    else:
        m = nhan_dien.nhan_dien(db, luot.vectors)
        worker = db.get(Worker, m.ma) if m.ma is not None else None
        face_status = DA_NHAN_RA if worker is not None else KHONG_NHAN_RA

    nearest = db.get(Worker, m.ma_gan_nhat) if m is not None and m.ma_gan_nhat is not None else None
    detail = {**luot.chi_tiet, "ly_do": luot.ly_do,
              "nhan_dien": None if m is None else {
                  "gan_nhat_id": m.ma_gan_nhat, "gan_nhat_ma": nearest.code if nearest else None,
                  "diem": None if m.diem is None else round(m.diem, 4),
                  "diem_thu_hai": None if m.diem_thu_hai is None else round(m.diem_thu_hai, 4)}}
    check = PpeCheck(
        gate_id=gate_id, worker_id=worker.id if worker else None, checked_at=luot.thoi_diem, face_status=face_status,
        face_score=None if m is None or m.diem is None else round(m.diem, 4), result=luot.ket_qua,
        missing=list(luot.thieu), presence_ratio=json_safe(luot.ty_le_co_mat), reason=luot.ly_do,
        duration_ms=luot.thoi_gian_ms, action=KHONG_GHI,
        image_path=luu_anh(luot.anh_jpeg, Path(image_dir), luot.thoi_diem, tz), detail=json_safe(detail))
    db.add(check)
    db.flush()  # lay check.id cho attendance.ppe_check_id

    kq = KetQuaChamCong(None, KHONG_GHI)
    if worker is not None:
        kq = cham_cong_tu_dong(db, worker, luot.ket_qua, luot.thoi_diem, check, settings["attendance"])
    check.direction, check.action = kq.huong, kq.hanh_dong
    db.commit()

    mau, text = thong_bao_cong(luot, worker, kq, tz)
    return {
        "loai": "luot",
        "id": check.id,
        "mau": mau,
        "thong_bao": text,
        "cong_nhan": None if worker is None else {"id": worker.id, "ma": worker.code, "ten": worker.full_name},
        "hanh_dong": kq.hanh_dong,
        "huong": kq.huong,
        "gio": gio_phut(luot.thoi_diem, tz),
        "thoi_diem": luot.thoi_diem.astimezone(tz).isoformat(timespec="seconds"),
        "ket_qua": luot.ket_qua,
        "thieu": list(luot.thieu),
        "trang_thai_mat": face_status,
        "diem": check.face_score,
        "anh": f"/api/luot/{check.id}/anh" if check.image_path else None,
        "ghi_cong": kq.hanh_dong in (GHI_VAO, GHI_RA),
    }
