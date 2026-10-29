"""Test PersonTracker. Chay: .venv\\Scripts\\python.exe -m unittest discover -s tests -v"""
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import torch
import yaml
from ultralytics.engine.results import Boxes

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import load_settings
from src.tracking.tracker import PersonTracker

TRACKER_CFG = load_settings()["paths"]["tracker_config"]
IMG = np.zeros((480, 640, 3), dtype=np.uint8)  # frame trong, chi de GMC co anh dau vao
PERSON = 3  # chi so lop gia cho box test; tracker khong phan biet lop


def person_boxes(xyxy_list):
    """Boxes Ultralytics: moi dong x1, y1, x2, y2, conf, cls."""
    data = torch.tensor([[*b, 0.9, PERSON] for b in xyxy_list], dtype=torch.float32).reshape(-1, 6)
    return Boxes(data, IMG.shape[:2])


class PersonTrackerTest(unittest.TestCase):
    def test_ids_stable_while_people_move(self):
        tracker = PersonTracker(TRACKER_CFG)
        history = []
        for t in range(10):
            boxes = person_boxes([[100 + 2 * t, 100, 160 + 2 * t, 300], [400 - 2 * t, 120, 460 - 2 * t, 320]])
            history.append(tracker.update(boxes, IMG))
        last = history[-1]
        self.assertNotIn(None, last)
        self.assertNotEqual(last[0], last[1])
        self.assertEqual(history[1:], [last] * 9)  # tu frame 2 tro di ID khong doi

    def test_ids_follow_input_order(self):
        # Dao thu tu box dau vao thi thu tu ID tra ve cung dao theo.
        tracker = PersonTracker(TRACKER_CFG)
        a, b = [100, 100, 160, 300], [400, 120, 460, 320]
        for _ in range(3):
            first = tracker.update(person_boxes([a, b]), IMG)
        swapped = tracker.update(person_boxes([b, a]), IMG)
        self.assertEqual(swapped, first[::-1])

    def test_no_person(self):
        tracker = PersonTracker(TRACKER_CFG)
        self.assertEqual(tracker.update(person_boxes([]), IMG), [])

    def test_reid_config_rejected(self):
        # Tu tao file cau hinh bat ReID (ban cu da chuyen vao _old/), khong phu thuoc _old/.
        cfg = yaml.safe_load(Path(TRACKER_CFG).read_text(encoding="utf-8"))
        cfg["with_reid"] = True
        with tempfile.TemporaryDirectory() as tmp:
            reid_cfg = Path(tmp) / "botsort_reid.yaml"
            reid_cfg.write_text(yaml.safe_dump(cfg), encoding="utf-8")
            with self.assertRaises(ValueError):
                PersonTracker(reid_cfg)


if __name__ == "__main__":
    unittest.main()
