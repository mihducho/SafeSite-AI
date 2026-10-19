"""Test YoloDetector bang model gia (khong can file model).
Chay: .venv\\Scripts\\python.exe -m unittest discover -s tests -v"""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.checkpoint.detector import YoloDetector
from fakes import MODEL_NAMES, SETTINGS


class FakeYolo:
    """Gia lap YOLO: ghi lai tham so predict, tra ve 1 box nguoi."""

    names = MODEL_NAMES

    def __init__(self):
        self.calls = []

    def predict(self, frame, **kw):
        self.calls.append((frame.shape, kw))
        boxes = SimpleNamespace(xyxy=torch.tensor([[1.0, 2.0, 3.0, 4.0]]), cls=torch.tensor([3.0]),
                                conf=torch.tensor([0.9]))
        return [SimpleNamespace(boxes=boxes)]


class YoloDetectorTest(unittest.TestCase):
    def test_classes_by_name_and_params_from_config(self):
        model = FakeYolo()
        det = YoloDetector(SETTINGS, model=model)
        d = det(np.zeros((720, 1280, 3), np.uint8))
        _, kw = model.calls[-1]
        self.assertEqual(sorted(kw["classes"]), [1, 3, 7])  # Safety-Vest, Person, Hardhat tra theo ten
        self.assertEqual((kw["conf"], kw["iou"], kw["imgsz"]),
                         (SETTINGS["model"]["conf"], SETTINGS["model"]["iou"], SETTINGS["model"]["imgsz"]))
        self.assertEqual(d.cls.tolist(), [3])
        self.assertEqual(d.xyxy.shape, (1, 4))
        self.assertAlmostEqual(float(d.conf[0]), 0.9, places=5)

    def test_warmup_runs_model_once_on_blank_image(self):
        model = FakeYolo()
        YoloDetector(SETTINGS, model=model).warmup()
        size = SETTINGS["model"]["imgsz"]
        self.assertEqual([shape for shape, _ in model.calls], [(size, size, 3)])


if __name__ == "__main__":
    unittest.main()
