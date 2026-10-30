"""Nhan dien cong nhan tu vector khuon mat cua 1 luot (DE_TAI.md muc 6.2 "So khop").

Doc mau khuon mat cua cong nhan DANG LAM va DA GHI NHAN DONG Y tu CSDL vao bo nho dem {worker_id: (m, 128)}, roi goi
src/face/match.py (ham thuan, da test o F1). Chi cong nhan co >= face.min_samples mau moi duoc so khop.
Bo nho dem bi xoa (doc lai o lan sau) khi them/xoa mau hoac doi trang thai cong nhan (dang_ky_mat.py, cong_nhan.py).
Vong lap cong (thread nen) va API (thread khac) cung dung -> co khoa (Lock).
"""
import threading

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import DANG_LAM, FaceSample, Worker
from src.face.match import MatchResult, match


def embedding_to_vector(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype="<f4").astype(np.float32)


def vector_to_embedding(vector: np.ndarray) -> bytes:
    v = np.asarray(vector, dtype="<f4").reshape(-1)
    if v.size != 128:
        raise ValueError(f"Vector khuon mat phai co 128 so, nhan duoc {v.size}")
    return v.tobytes()


def load_gallery(db: Session, min_samples: int) -> dict[int, np.ndarray]:
    """{worker_id: (m, 128)} cua cong nhan dang lam, da dong y, co it nhat min_samples mau."""
    enough = (select(FaceSample.worker_id).join(Worker).where(Worker.status == DANG_LAM, Worker.consent_at.is_not(None))
              .group_by(FaceSample.worker_id).having(func.count(FaceSample.id) >= min_samples))
    rows = db.execute(select(FaceSample.worker_id, FaceSample.embedding)
                      .where(FaceSample.worker_id.in_(enough)).order_by(FaceSample.id)).all()
    gallery: dict[int, list[np.ndarray]] = {}
    for worker_id, blob in rows:
        gallery.setdefault(worker_id, []).append(embedding_to_vector(blob))
    return {wid: np.stack(v) for wid, v in gallery.items()}


class NhanDien:
    def __init__(self, face_cfg: dict):
        self.cfg = face_cfg
        self._lock = threading.Lock()
        self._gallery: dict[int, np.ndarray] | None = None

    def xoa_bo_nho_dem(self) -> None:
        with self._lock:
            self._gallery = None

    def gallery(self, db: Session) -> dict[int, np.ndarray]:
        with self._lock:
            if self._gallery is None:
                self._gallery = load_gallery(db, self.cfg["min_samples"])
            return self._gallery

    def nhan_dien(self, db: Session, vectors) -> MatchResult:
        """MatchResult.ma = worker_id nhan ra (None = khong nhan ra); ma_gan_nhat, diem de xem lai."""
        vecs = np.asarray(vectors, np.float32).reshape(-1, 128)
        return match(vecs, self.gallery(db), self.cfg["match_threshold"], self.cfg["match_margin"])
