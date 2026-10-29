"""Cong chay ben trong ung dung web (DE_TAI.md muc 8).

- Khoi dong (start): 1 thread rieng doc cong tu bang gates, nap YOLO + YuNet + SFace (1 lan), mo CameraReader, chay
  GateWorker (src/gate/worker.py, F1). Viec nay mat vai giay nen KHONG chan ung dung web: web len ngay, trang thai cong
  la "dang_khoi_dong". Camera hoac mo hinh loi -> trang thai "loi" kem ly do, web van chay (can bo cham thu cong).
- Moi luot xong: GateWorker goi _on_result (trong thread cua no) -> xu_ly_luot ghi CSDL bang session rieng -> phat
  su kien sang event loop (Broadcaster.publish_threadsafe) -> cac WebSocket.
- 1 CameraReader dung chung cho vong lap cong, luong hinh truc tiep (render_frame) va chup mau khuon mat (latest_frame).
Nguon hinh: GATE_SOURCE trong .env (neu co), khong thi gates.camera_source. File video lap lai theo camera.loop_video.
"""
import threading
import time
from pathlib import Path

import cv2
import numpy as np
from sqlalchemy import select

from app.config import AppConfig, mask_source
from app.db import Database, utcnow
from app.events import Broadcaster
from app.models import Gate
from app.services.cham_cong import BO_QUA_TRUNG, GHI_RA, GHI_VAO
from app.services.luot import LuotKiemTra, xu_ly_luot
from app.services.nhan_dien import NhanDien
from src.checkpoint.camera import CameraError, CameraReader
from src.gate.worker import GateWorker
from src.utils.visualize import YELLOW, draw_faces, draw_person, draw_zone
from src.zone.zone import zone_to_pixels

TAT, DANG_KHOI_DONG, DANG_CHAY, LOI = "tat", "dang_khoi_dong", "dang_chay", "loi"
NO_FRAME_SECONDS = 3.0  # khong co khung moi qua bay nhieu giay -> bao mat tin hieu camera
PLACEHOLDER_TEXT = {TAT: "Cong dang tat", DANG_KHOI_DONG: "Dang khoi dong camera va mo hinh...",
                    LOI: "He thong kiem tra tam gian doan", DANG_CHAY: "Dang cho hinh tu camera..."}
DA_XONG = (GHI_VAO, GHI_RA, BO_QUA_TRUNG)  # nguoi da duoc ghi (hoac da ghi roi): cho roi khoi vung moi kiem tra tiep


def load_gate_models(settings: dict):
    """(YOLO, YuNet, SFace). Nap YOLO TRUOC: ultralytics dat OpenCV ve 1 luong, model mat dat lai so luong sau do."""
    from src.checkpoint.detector import get_detector
    from src.face.face_detector import face_detector_from_settings
    from src.face.face_embedder import face_embedder_from_settings
    detector = get_detector(settings)
    return detector, face_detector_from_settings(settings["face"]), face_embedder_from_settings(settings["face"])


def _error_text(e: Exception) -> str:
    if isinstance(e, CameraError):
        return f"Lỗi camera: {e}"
    if isinstance(e, FileNotFoundError):
        return f"Thiếu file mô hình: {e}"
    return f"{type(e).__name__}: {e}"


class GateService:
    def __init__(self, cfg: AppConfig, db: Database, nhan_dien: NhanDien, events: Broadcaster, image_dir: str | Path,
                 models_factory=None, reader_factory=None):
        self.cfg, self.settings, self.db = cfg, cfg.settings, db
        self.nhan_dien, self.events, self.image_dir = nhan_dien, events, Path(image_dir)
        self._models_factory = models_factory or (lambda: load_gate_models(self.settings))
        self._reader_factory = reader_factory or (lambda source, cam_cfg: CameraReader(source, cam_cfg))
        self._models = None
        self.trang_thai, self.loi = TAT, None
        self.gate_id: int | None = None
        self.zone = None
        self.source: str | None = None
        self.reader = None
        self.worker: GateWorker | None = None
        self.last_event: dict | None = None
        self._lock = threading.Lock()
        self._stopping = False
        self._boot_thread: threading.Thread | None = None
        self._frame_seen = (0, time.monotonic())
        self._render_lock = threading.Lock()
        self._render_key, self._render_jpeg = None, b""

    # --- bat / tat ---
    def start(self) -> None:
        with self._lock:
            if self.trang_thai in (DANG_KHOI_DONG, DANG_CHAY):
                return
            self.trang_thai, self.loi, self._stopping = DANG_KHOI_DONG, None, False
            self._boot_thread = threading.Thread(target=self._boot, name="gate-boot", daemon=True)
            self._boot_thread.start()

    def _boot(self) -> None:
        reader = None
        try:
            with self.db.session() as s:
                gate = s.scalar(select(Gate).order_by(Gate.id).limit(1))
                if gate is None:
                    raise RuntimeError("Chưa có cổng trong CSDL: chạy scripts\\seed_demo.py")
                self.gate_id, self.zone = gate.id, gate.zone
                rotate, required, self.source = gate.rotate, gate.required_ppe, self.cfg.gate_source or gate.camera_source
            if self._models is None:
                self._models = self._models_factory()
            detector, fd, emb = self._models
            reader = self._reader_factory(self.source, {**self.settings["camera"], "rotate": rotate}).start()
            worker = GateWorker(reader, self.zone, self.settings, detector, fd, emb, on_result=self._on_result,
                                required_ppe=required)
            with self._lock:
                if self._stopping:
                    reader.stop()
                    return
                self.reader, self.worker = reader, worker.start()
                self.trang_thai = DANG_CHAY
        except Exception as e:  # camera/mo hinh loi: web van chay, trang thai cong bao loi
            if reader is not None:
                reader.stop()
            with self._lock:
                self.trang_thai, self.loi = LOI, _error_text(e)

    def stop(self) -> None:
        with self._lock:
            self._stopping = True
            worker, reader = self.worker, self.reader
            self.worker = self.reader = None
            self.trang_thai = TAT
        if worker is not None:
            worker.stop()
        if reader is not None:
            reader.stop()

    def restart(self) -> None:
        self.stop()
        if self._boot_thread is not None:
            self._boot_thread.join(timeout=30)
        self.start()

    # --- moi luot (thread cua GateWorker) ---
    def _on_result(self, result: dict) -> bool:
        luot = LuotKiemTra.tu_ket_qua_cong(result, utcnow())
        with self.db.session() as s:
            event = xu_ly_luot(s, luot, settings=self.settings, nhan_dien=self.nhan_dien, image_dir=self.image_dir,
                               gate_id=self.gate_id)
        self.last_event = event
        self.events.publish_threadsafe(event)
        return event["hanh_dong"] in DA_XONG

    # --- trang thai ---
    def status(self) -> dict:
        loi, pha, so_luot = self.loi, None, 0
        worker, reader = self.worker, self.reader
        if worker is not None and reader is not None:
            pha, so_luot = worker.state.phase, worker.rounds
            loi = worker.error or loi
            fid, now = reader.latest_id, time.monotonic()
            if fid != self._frame_seen[0]:
                self._frame_seen = (fid, now)
            elif now - self._frame_seen[1] > NO_FRAME_SECONDS:
                loi = loi or "Mất tín hiệu camera"
        return {"trang_thai": self.trang_thai, "loi": loi, "gian_doan": self.trang_thai != DANG_CHAY or loi is not None,
                "pha": pha, "so_luot": so_luot, "nguon": mask_source(self.source), "cong_id": self.gate_id}

    # --- khung hinh ---
    def latest_frame(self) -> np.ndarray | None:
        """Ban sao khung moi nhat cua camera cong (chup mau khuon mat)."""
        reader = self.reader
        got = reader.latest() if reader is not None else None
        return None if got is None else got[1].copy()

    def render_frame(self) -> bytes:
        """JPEG cho luong hinh truc tiep: vung kiem tra; dang kiem tra thi ve them khung nguoi, khung mat."""
        reader, worker = self.reader, self.worker
        got = reader.latest() if reader is not None else None
        if got is None:
            return self._placeholder(PLACEHOLDER_TEXT[self.trang_thai])
        fid, frame = got
        rnd = worker.round if worker is not None else None
        last = rnd.last if rnd is not None else None
        key = (id(reader), fid, id(last))
        with self._render_lock:
            if key == self._render_key:  # nhieu trinh duyet cung xem: khong ve lai cung 1 khung
                return self._render_jpeg
            img = frame.copy()
            h, w = img.shape[:2]
            if self.zone is not None:
                draw_zone(img, zone_to_pixels(self.zone, w, h), color=YELLOW)
            if last is not None:
                persons, face_rows, main_idx = last
                for box in persons:
                    draw_person(img, box, "", [])
                draw_faces(img, face_rows, main_idx)
            gcfg = self.settings["gate"]
            scale = gcfg["stream_long_side"] / max(h, w)
            if scale < 1:
                img = cv2.resize(img, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA)
            ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, int(gcfg["stream_jpeg_quality"])])
            self._render_key, self._render_jpeg = key, buf.tobytes() if ok else b""
            return self._render_jpeg

    def _placeholder(self, text: str) -> bytes:
        key = ("placeholder", text)
        with self._render_lock:
            if key != self._render_key:
                img = np.full((540, 960, 3), 40, np.uint8)
                cv2.putText(img, "SafeGate", (40, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (255, 255, 255), 3, cv2.LINE_AA)
                cv2.putText(img, text, (40, 310), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 220, 255), 2, cv2.LINE_AA)
                ok, buf = cv2.imencode(".jpg", img)
                self._render_key, self._render_jpeg = key, buf.tobytes() if ok else b""
            return self._render_jpeg
