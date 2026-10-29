"""Test menu demo (scripts/demo.py): lenh duoc tao dung tu cau hinh, tim video, lay file moi nhat.
Chay: .venv\\Scripts\\python.exe -m unittest discover -s tests -v"""
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from demo import eval_command, find_video, newest, video_command
from src.config import load_settings

S = load_settings()
DEMO = S["demo"]


class DemoTest(unittest.TestCase):
    def test_lenh_danh_gia_lay_tu_cau_hinh(self):
        cmd = eval_command(DEMO)
        self.assertTrue(cmd[1].endswith("evaluate_videos.py"))
        for flag, value in (("--gate", DEMO["gate"]), ("--fps", str(DEMO["sample_fps"])), ("--imgsz", str(DEMO["imgsz"])),
                            ("--save-images", "all")):
            self.assertEqual(cmd[cmd.index(flag) + 1], value)
        self.assertTrue(Path(cmd[cmd.index("--answers") + 1]).is_absolute())

    def test_lenh_chay_video(self):
        cmd = video_command(DEMO, Path("x/du_do_01.mp4"))
        self.assertTrue(cmd[1].endswith("run_checkpoint.py"))
        self.assertEqual(cmd[cmd.index("--gate") + 1], DEMO["gate"])
        self.assertEqual(cmd[cmd.index("--rounds") + 1], "1")

    def test_tim_video_khong_can_duoi_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "du_do_01.MP4").write_bytes(b"")
            self.assertEqual(find_video(Path(tmp), "du_do_01", S["evaluation"]["video_exts"]).name, "du_do_01.MP4")
            with self.assertRaises(FileNotFoundError):
                find_video(Path(tmp), "khong_co", S["evaluation"]["video_exts"])

    def test_file_moi_nhat(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = Path(tmp) / "a.jpg", Path(tmp) / "b.jpg"
            old.write_bytes(b""), new.write_bytes(b"")
            t = time.time()
            os.utime(old, (t - 100, t - 100))
            self.assertEqual(newest(Path(tmp), "*.jpg"), new)
            self.assertIsNone(newest(Path(tmp) / "khong_co", "*.jpg"))

    def test_danh_sach_video_demo_hop_le(self):
        self.assertTrue(all({"name", "note"} <= set(v) for v in DEMO["videos"]))


if __name__ == "__main__":
    unittest.main()
