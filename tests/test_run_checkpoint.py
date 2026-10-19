"""Test cach ghi file JSON ket qua cua scripts/run_checkpoint.py.
Chay: .venv\\Scripts\\python.exe -m unittest discover -s tests -v"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from run_checkpoint import to_json

FRAMES = [
    {"loai": "hop_le", "ly_do": None, "box": [{"lop": "Person", "conf": 0.91, "xyxy": [0.42, 0.18, 0.77, 0.85]}],
     "nguoi_trong_vung": [[0.42, 0.18, 0.77, 0.85]], "ppe": {"hardhat": True, "vest": False}},
    {"loai": "trong", "ly_do": None, "box": [], "nguoi_trong_vung": [], "ppe": None},
]


class ToJsonTest(unittest.TestCase):
    def test_round_trip(self):
        result = {"ket_qua": "KHONG_DAT", "thieu": ["thieu_ao"], "chi_tiet_khung": FRAMES}
        self.assertEqual(json.loads(to_json(result)), result)

    def test_one_line_per_frame(self):
        lines = to_json({"ket_qua": "DAT", "chi_tiet_khung": FRAMES}).splitlines()
        frame_lines = [ln for ln in lines if '"loai"' in ln]
        self.assertEqual(len(frame_lines), 2)

    def test_without_frames(self):
        result = {"ket_qua": "DAT", "thieu": []}
        self.assertEqual(json.loads(to_json(result)), result)

    def test_input_not_modified(self):
        result = {"ket_qua": "DAT", "chi_tiet_khung": FRAMES}
        to_json(result)
        self.assertIn("chi_tiet_khung", result)


if __name__ == "__main__":
    unittest.main()
