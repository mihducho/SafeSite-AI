"""Tim khuon mat bang YuNet (cv2.FaceDetectorYN co san trong OpenCV, DE_TAI.md muc 4).

YuNet tra ve moi khuon mat 1 dong 15 so: x, y, w, h (khung mat), 5 diem moc (2 mat, mui, 2 mep mieng) moi diem
(x, y), va diem tin cay (score). Giu nguyen dinh dang nay vi SFace (alignCrop) can dung no de can chinh mat.
"""
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


def quiet_opencv_logs() -> None:
    """Tat canh bao "Targets are not supported by the new graph engine" cua OpenCV 5 khi nap mo hinh ONNX."""
    try:
        cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)
    except AttributeError:
        pass


@dataclass
class Faces:
    """Cac khuon mat tim duoc tren 1 khung (toa do pixel cua khung goc)."""
    rows: np.ndarray  # (N, 15) float32, dinh dang YuNet

    def __len__(self) -> int:
        return len(self.rows)

    @property
    def boxes(self) -> np.ndarray:
        """(N, 4) x1, y1, x2, y2."""
        r = self.rows
        return np.stack([r[:, 0], r[:, 1], r[:, 0] + r[:, 2], r[:, 1] + r[:, 3]], axis=1) if len(r) else np.zeros((0, 4))

    @property
    def widths(self) -> np.ndarray:
        return self.rows[:, 2]

    @property
    def scores(self) -> np.ndarray:
        return self.rows[:, 14]


def empty_faces() -> Faces:
    return Faces(np.zeros((0, 15), np.float32))


class FaceDetector:
    """Boc YuNet. detect(anh) -> Faces. long_side: thu nho anh truoc khi tim (che do CHO, cho nhanh),
    toa do tra ve van theo anh goc."""

    def __init__(self, model_path: str | Path, score_threshold: float, nms_threshold: float):
        quiet_opencv_logs()
        if not Path(model_path).exists():
            raise FileNotFoundError(f"Khong thay mo hinh YuNet: {model_path}. Chay scripts\\download_face_models.py")
        self._det = cv2.FaceDetectorYN.create(str(model_path), "", (320, 320), score_threshold, nms_threshold, 5000)
        self._size: tuple[int, int] | None = None

    def detect(self, image: np.ndarray, long_side: int | None = None) -> Faces:
        h, w = image.shape[:2]
        scale = long_side / max(h, w) if long_side and max(h, w) > long_side else 1.0
        img = cv2.resize(image, (round(w * scale), round(h * scale))) if scale != 1.0 else image
        size = (img.shape[1], img.shape[0])
        if size != self._size:  # YuNet can biet kich thuoc anh vao
            self._det.setInputSize(size)
            self._size = size
        _, rows = self._det.detect(img)
        if rows is None:
            return empty_faces()
        rows = rows.astype(np.float32)
        if scale != 1.0:
            rows[:, :14] /= scale  # khung + diem moc ve toa do anh goc; score giu nguyen
        return Faces(rows)


def set_opencv_threads(n: int) -> None:
    """So luong CPU OpenCV dung cho YuNet/SFace. Phai goi SAU khi nap ultralytics (no tu dat OpenCV ve 1 luong)."""
    if n and n > 0:
        cv2.setNumThreads(int(n))


def face_detector_from_settings(face_cfg: dict) -> FaceDetector:
    set_opencv_threads(face_cfg["opencv_threads"])
    return FaceDetector(face_cfg["detector_model"], face_cfg["score_threshold"], face_cfg["nms_threshold"])
