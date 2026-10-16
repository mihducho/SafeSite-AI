"""Bo phat hien dung cho che do cong: nhan 1 khung hinh, tra ve cac box.

Tach rieng khoi evaluate_frames de test tu dong thay bang bo phat hien gia
(box gia) — khong can file model, khong can video. Bo phat hien nao cung chi
can 2 thu: thuoc tinh `names` (dict chi so lop -> ten lop, giong model.names)
va goi duoc `detector(frame) -> Detections`.
"""
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from src.detection.detect import find_class_ids, load_model


@dataclass
class Detections:
    xyxy: np.ndarray  # (N, 4) box x1, y1, x2, y2 theo pixel cua khung hinh
    cls: np.ndarray  # (N,) chi so lop cua tung box


class YoloDetector:
    """Boc model YOLO: chi giu lop nguoi + cac lop do bao ho khai bao trong cau hinh."""

    def __init__(self, settings: dict, model=None):
        mcfg = settings["model"]
        self.model = model if model is not None else load_model(mcfg["weights"])
        self.names = self.model.names
        class_names = [mcfg["person_class"]] + [item["class_name"] for item in settings["ppe"]["items"].values()]
        self.classes = list(find_class_ids(self.names, class_names).values())  # thieu ten lop -> loi, dung
        self.predict_kw = {"conf": mcfg["conf"], "iou": mcfg["iou"], "imgsz": mcfg["imgsz"], "verbose": False}

    def __call__(self, frame: np.ndarray) -> Detections:
        boxes = self.model.predict(frame, classes=self.classes, **self.predict_kw)[0].boxes
        return Detections(boxes.xyxy.cpu().numpy(), boxes.cls.cpu().numpy().astype(int))


_cache: dict[tuple, YoloDetector] = {}


def get_detector(settings: dict) -> YoloDetector:
    """Nap model 1 lan (mat vai giay) roi dung lai cho cac lan kiem tra sau.
    Doi model hoac tham so suy luan trong cau hinh thi tao bo phat hien moi."""
    mcfg = settings["model"]
    item_classes = tuple(item["class_name"] for item in settings["ppe"]["items"].values())
    key = (Path(mcfg["weights"]), mcfg["conf"], mcfg["iou"], mcfg["imgsz"], mcfg["person_class"], item_classes)
    if key not in _cache:
        _cache[key] = YoloDetector(settings)
    return _cache[key]
