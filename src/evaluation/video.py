"""Lay mau khung tu video de mo phong 1 luot check() (DE_TAI.md muc 10).

check() xu ly khung ngay khi lay duoc: khung dau o t = 0, xu ly mat 1/fps giay, roi lay khung MOI NHAT
tai thoi diem do, ... cho den khi het timeout. Voi video: thoi diem t ung voi khung thu floor(t * fps_video).
fps o day la toc do XU LY cua may (do bang measure_fps), khong phai FPS cua video.
"""
import math
import time

import cv2
import numpy as np

from src.checkpoint.camera import rotate_frame


def sample_times(sample_fps: float, timeout: float) -> list[float]:
    """Cac thoi diem (giay, tinh tu dau video) bat dau xu ly 1 khung trong 1 luot."""
    if sample_fps <= 0 or timeout <= 0:
        raise ValueError(f"sample_fps va timeout phai > 0, nhan {sample_fps}, {timeout}")
    n = math.ceil(timeout * sample_fps - 1e-9)  # khung bat dau truoc khi het gio deu duoc xu ly
    return [k / sample_fps for k in range(n)]


def sample_indices(sample_fps: float, timeout: float, video_fps: float) -> list[int]:
    """Chi so khung video tuong ung. Khong lap lai: may nhanh hon camera thi check() phai cho khung moi."""
    if video_fps <= 0:
        raise ValueError(f"FPS cua video khong hop le: {video_fps}")
    out: list[int] = []
    for t in sample_times(sample_fps, timeout):
        i = int(math.floor(t * video_fps + 1e-6))
        if not out or i > out[-1]:
            out.append(i)
    return out


def read_sampled_frames(path: str, sample_fps: float, timeout: float, rotate: int = 0) -> tuple[list[np.ndarray], dict]:
    """Doc cac khung lay mau trong `timeout` giay dau cua video (da xoay theo rotate).
    Video ngan hon timeout thi chi lay cac khung co that. Tra ve (khung, thong tin)."""
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise IOError(f"Khong mo duoc video: {path}")
    try:
        video_fps = float(cap.get(cv2.CAP_PROP_FPS) or 0)
        wanted = sample_indices(sample_fps, timeout, video_fps)
        frames, idx, pos = [], [], 0
        want = set(wanted)
        while pos <= wanted[-1]:
            ok, frame = cap.read()
            if not ok:
                break
            if pos in want:
                frames.append(rotate_frame(frame, rotate))
                idx.append(pos)
            pos += 1
    finally:
        cap.release()
    h, w = frames[0].shape[:2] if frames else (0, 0)
    return frames, {"video_fps": round(video_fps, 2), "chi_so_khung": idx, "khung_hinh": [w, h],
                    "video_ngan_hon_timeout": len(idx) < len(wanted)}


def measure_fps(process_frame, frame: np.ndarray, n: int) -> float:
    """Toc do xu ly (khung/giay) cua process_frame(frame) tren may nay: trung binh n lan.
    Nen goi sau khi da warmup model (lan dau cham hon nhieu)."""
    t = time.perf_counter()
    for _ in range(n):
        process_frame(frame)
    return n / max(time.perf_counter() - t, 1e-9)
