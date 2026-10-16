"""Du lieu gia dung chung cho test (khong phai file test).

- Box gia + bo phat hien gia: thay model YOLO.
- Nguon camera gia (FakeCapture): thay cv2.VideoCapture, sinh khung hinh danh so
  (so thu tu ghi vao pixel goc tren trai) de test biet khung nao duoc xu ly.
"""
import copy
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.checkpoint.detector import Detections
from src.config import load_settings

MODEL_NAMES = {0: "Mask", 1: "Safety-Vest", 2: "NO-Safety-Vest", 3: "Person", 4: "machinery",
               5: "Safety-Cone", 6: "vehicle", 7: "Hardhat", 8: "NO-Mask", 9: "NO-Hardhat"}
CLS = {name: idx for idx, name in MODEL_NAMES.items()}

# Co dinh cac nguong test dua vao (bang gia tri mac dinh trong DE_TAI.md muc 5), de
# hieu chinh settings.yaml o Giai doan 2 khong lam hong test cua thuat toan.
SETTINGS = copy.deepcopy(load_settings())
SETTINGS["checkpoint"].update(min_person_height_px=150, top_edge_margin_px=2, min_valid_frames=3,
                              present_ratio=0.6, absent_ratio=0.2)
REQUIRED = ["hardhat", "vest"]

FRAME_H, FRAME_W = 720, 1280
FRAME = np.zeros((FRAME_H, FRAME_W, 3), dtype=np.uint8)
# Vung kiem tra ti le 0-1 -> pixel: x 320..960, y 360..720 (nua duoi, o giua khung).
ZONE = [[0.25, 0.5], [0.75, 0.5], [0.75, 1.0], [0.25, 1.0]]

# 1 nguoi dung thang trong vung: cao 550px, diem chan (600, 650) nam trong vung.
PERSON = [500, 100, 700, 650]
HAT = [560, 80, 640, 150]  # vung dau
VEST = [520, 220, 680, 450]  # vung than
PERSON_2 = [750, 120, 900, 650]  # nguoi thu 2 cung trong vung (chan (825, 650))
HEAD_CUT = [500, 0, 700, 650]  # mep tren cham mep tren khung
SMALL = [600, 520, 640, 660]  # cao 140px < 150
OUTSIDE = [50, 100, 200, 300]  # chan (125, 300) ngoai vung


def dets(*boxes) -> Detections:
    """boxes: cac cap (xyxy, ten lop)."""
    if not boxes:
        return Detections(np.zeros((0, 4), np.float32), np.zeros(0, int))
    return Detections(np.array([b for b, _ in boxes], np.float32), np.array([CLS[n] for _, n in boxes]))


FULL = dets((PERSON, "Person"), (HAT, "Hardhat"), (VEST, "Safety-Vest"))
NO_HAT = dets((PERSON, "Person"), (VEST, "Safety-Vest"))
NO_VEST = dets((PERSON, "Person"), (HAT, "Hardhat"))
BARE = dets((PERSON, "Person"))
TWO = dets((PERSON, "Person"), (HAT, "Hardhat"), (VEST, "Safety-Vest"), (PERSON_2, "Person"))
EMPTY = dets()


class FakeDetector:
    """Tra ve lan luot cac Detections trong script, moi lan goi la 1 khung."""

    def __init__(self, script, names=MODEL_NAMES):
        self.script, self.names, self.i = list(script), names, 0

    def __call__(self, frame):
        d = self.script[self.i]
        self.i += 1
        return d


# --- khung hinh danh so ---
def numbered_frame(i: int, h: int = FRAME_H, w: int = FRAME_W) -> np.ndarray:
    f = np.zeros((h, w, 3), dtype=np.uint8)
    f[0, 0, 0], f[0, 0, 1] = i % 256, i // 256
    return f


def frame_number(frame: np.ndarray) -> int:
    return int(frame[0, 0, 0]) + 256 * int(frame[0, 0, 1])


class IndexDetector:
    """Bo phat hien gia theo SO THU TU khung (doc tu pixel): script(i) -> Detections.
    delay: gia lap thoi gian chay model moi khung. Ghi lai cac khung da xu ly."""

    def __init__(self, script, delay: float = 0.0, names=MODEL_NAMES):
        self.script, self.delay, self.names = script, delay, names
        self.seen: list[int] = []

    def __call__(self, frame):
        i = frame_number(frame)
        self.seen.append(i)
        if self.delay:
            time.sleep(self.delay)
        return self.script(i)


class FakeCapture:
    """Thay cv2.VideoCapture. n_frames=None: camera chay mai; fps: FPS bao cao (file video);
    read_delay: gia lap toc do camera; fail_after: doc loi sau so khung nay (mat ket noi)."""

    def __init__(self, n_frames=None, fps=0.0, read_delay=0.0, fail_after=None, start=1, h=FRAME_H, w=FRAME_W):
        self.n, self.fps, self.read_delay, self.fail_after = n_frames, fps, read_delay, fail_after
        self.pos, self.start, self.h, self.w = 0, start, h, w
        self.released = False
        self.seeks: list[int] = []

    def read(self):
        if self.read_delay:
            time.sleep(self.read_delay)
        if (self.n is not None and self.pos >= self.n) or (self.fail_after is not None and self.pos >= self.fail_after):
            return False, None
        frame = numbered_frame(self.start + self.pos, self.h, self.w)
        self.pos += 1
        return True, frame

    def get(self, prop):
        return self.fps if prop == cv2.CAP_PROP_FPS else 0.0

    def set(self, prop, value):
        if prop == cv2.CAP_PROP_POS_FRAMES:
            self.pos = int(value)
            self.seeks.append(int(value))
        return True

    def isOpened(self):
        return True

    def release(self):
        self.released = True


CAM_CFG = {"webcam_width": 1280, "webcam_height": 720, "first_frame_timeout_s": 2.0,
           "reconnect_delay_s": 0.01, "loop_video": True}
