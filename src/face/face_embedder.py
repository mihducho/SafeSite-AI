"""Lay vector dac trung khuon mat bang SFace (cv2.FaceRecognizerSF co san trong OpenCV, DE_TAI.md muc 4).

Buoc 1 alignCrop: dua vao 5 diem moc cua YuNet, xoay/cat khuon mat ve anh 112x112 chuan (2 mat nam ngang).
Buoc 2 feature: SFace bien anh 112x112 thanh vector 128 so. Hai anh cung 1 nguoi cho 2 vector "gan" nhau.
Vector duoc chuan hoa L2 (do dai = 1), khi do do giong nhau = tich vo huong (cosine), tu -1 den 1.
"""
from pathlib import Path

import cv2
import numpy as np

from src.face.face_detector import quiet_opencv_logs, set_opencv_threads
from src.face.match import l2_normalize


class FaceEmbedder:
    def __init__(self, model_path: str | Path):
        quiet_opencv_logs()
        if not Path(model_path).exists():
            raise FileNotFoundError(f"Khong thay mo hinh SFace: {model_path}. Chay scripts\\download_face_models.py")
        self._rec = cv2.FaceRecognizerSF.create(str(model_path), "")

    def align(self, image: np.ndarray, face_row: np.ndarray) -> np.ndarray:
        """Anh mat da can chinh 112x112 (BGR). face_row: 1 dong 15 so cua YuNet."""
        return self._rec.alignCrop(image, np.asarray(face_row, np.float32))

    def embed_aligned(self, aligned: np.ndarray) -> np.ndarray:
        """Vector (128,) float32 da chuan hoa L2, tu anh mat 112x112."""
        return l2_normalize(self._rec.feature(aligned).reshape(-1))

    def embed(self, image: np.ndarray, face_row: np.ndarray) -> np.ndarray:
        return self.embed_aligned(self.align(image, face_row))


def face_embedder_from_settings(face_cfg: dict) -> FaceEmbedder:
    set_opencv_threads(face_cfg["opencv_threads"])
    return FaceEmbedder(face_cfg["recognizer_model"])
