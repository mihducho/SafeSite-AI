"""Test luong doc camera (CameraReader) bang nguon gia, khong can webcam that.
Chay: .venv\\Scripts\\python.exe -m unittest discover -s tests -v"""
import sys
import time
import unittest
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.checkpoint.camera import CameraError, CameraReader, Source, open_capture, parse_source, rotate_frame
from fakes import CAM_CFG, FRAME_H, FRAME_W, FakeCapture, frame_number


def reader_with(capture, source="0", **cfg):
    """CameraReader voi nguon gia; source chi de chon kieu (webcam/url/file)."""
    caps = capture if isinstance(capture, list) else [capture]

    def factory(src):
        if not caps:
            raise CameraError("het nguon gia")
        return caps.pop(0)

    return CameraReader(source, {**CAM_CFG, **cfg}, capture_factory=factory)


class ParseSourceTest(unittest.TestCase):
    def test_kinds(self):
        self.assertEqual(parse_source("0"), Source("webcam", 0))
        self.assertEqual(parse_source(1), Source("webcam", 1))
        self.assertEqual(parse_source("http://192.168.1.23:8080/video").kind, "url")
        self.assertEqual(parse_source("rtsp://192.168.1.23:8554/live").kind, "url")
        self.assertEqual(parse_source(r"data\raw\cong.mp4"), Source("file", r"data\raw\cong.mp4"))

    def test_label_not_from_path_for_webcam_or_url(self):
        # DE_TAI muc 8: ten file ket qua khong dua vao Path(source).stem khi la webcam/URL.
        self.assertEqual(parse_source("0").label, "webcam0")
        self.assertEqual(parse_source("http://192.168.1.23:8080/video").label, "camera_ip")
        self.assertEqual(parse_source("data/raw/cong_1.mp4").label, "cong_1")

    def test_missing_file(self):
        with self.assertRaises(CameraError):
            open_capture(parse_source("data/raw/khong_ton_tai.mp4"), CAM_CFG)


class RotateFrameTest(unittest.TestCase):
    # Khung 4x6 (cao x rong), danh dau 1 diem o giua canh TRAI: nhu dau nguoi khi dien thoai
    # dung doc ma app phat hinh ngang.
    def setUp(self):
        self.frame = np.zeros((4, 6, 3), np.uint8)
        self.frame[2, 0] = 255

    def test_90_moves_left_edge_to_top(self):
        out = rotate_frame(self.frame, 90)
        self.assertEqual(out.shape, (6, 4, 3))  # ngang -> doc
        self.assertEqual(np.argwhere(out[..., 0] == 255).tolist(), [[0, 1]])  # canh trai -> canh tren

    def test_270_and_180(self):
        self.assertEqual(np.argwhere(rotate_frame(self.frame, 270)[..., 0] == 255).tolist(), [[5, 2]])  # -> canh duoi
        self.assertEqual(np.argwhere(rotate_frame(self.frame, 180)[..., 0] == 255).tolist(), [[1, 5]])  # -> canh phai

    def test_0_returns_same_frame(self):
        self.assertIs(rotate_frame(self.frame, 0), self.frame)

    def test_invalid_angle(self):
        for bad in (45, -90, 360, "90", True):
            with self.assertRaises(ValueError):
                rotate_frame(self.frame, bad)


class CameraReaderTest(unittest.TestCase):
    def test_keeps_only_latest_frame(self):
        # Camera ~200 khung/s, nguoi doc cham: chi lay khung moi nhat, cac khung giua bi bo qua.
        with reader_with(FakeCapture(read_delay=0.005)) as cam:
            time.sleep(0.2)
            fid, frame = cam.wait_new(after_id=0, timeout=1)
            self.assertGreater(fid, 10)
            self.assertEqual(frame_number(frame), fid)  # khung tra ve dung la khung moi nhat
            fid2, _ = cam.wait_new(after_id=fid, timeout=1)
            self.assertGreater(fid2, fid)

    def test_wait_new_timeout_returns_none(self):
        cap = FakeCapture(n_frames=1, fps=10)
        with reader_with(cap, source="video.mp4", loop_video=False) as cam:
            t = time.monotonic()
            self.assertIsNone(cam.wait_new(after_id=cam.latest_id, timeout=0.3))
            self.assertLess(time.monotonic() - t, 1.0)

    def test_video_file_plays_at_real_speed(self):
        # Video 50 FPS, 20 khung -> phat het mat ~0.4 s (khong doc ngay lap tuc).
        cap = FakeCapture(n_frames=20, fps=50)
        t = time.monotonic()
        with reader_with(cap, source="video.mp4", loop_video=False) as cam:
            while cam.wait_new(cam.latest_id, timeout=2) is not None:
                pass
            elapsed = time.monotonic() - t
        self.assertEqual(cam.latest_id, 20)
        self.assertGreater(elapsed, 0.3)

    def test_video_loops(self):
        cap = FakeCapture(n_frames=5, fps=200)
        with reader_with(cap, source="video.mp4", loop_video=True) as cam:
            time.sleep(0.15)
            self.assertGreater(cam.latest_id, 5)  # da phat lai
        self.assertIn(0, cap.seeks)  # quay ve khung 0

    def test_webcam_reconnects_after_read_error(self):
        first = FakeCapture(read_delay=0.005, fail_after=3)
        second = FakeCapture(read_delay=0.005, start=100)
        with reader_with([first, second]) as cam:
            time.sleep(0.2)
            fid, frame = cam.latest()
        self.assertGreaterEqual(cam.read_errors, 1)
        self.assertTrue(first.released)
        self.assertGreater(fid, 3)
        self.assertGreaterEqual(frame_number(frame), 100)  # khung moi tu lan mo lai

    def test_open_failure_raises(self):
        with self.assertRaises(CameraError):
            reader_with([]).start()

    def test_no_first_frame_raises(self):
        with self.assertRaises(CameraError):
            reader_with(FakeCapture(n_frames=0), source="video.mp4", loop_video=False).start()

    def test_start_twice_does_not_add_thread(self):
        opened = []

        def factory(src):
            opened.append(src)
            return FakeCapture(read_delay=0.005)

        cam = CameraReader("0", CAM_CFG, capture_factory=factory)
        with cam.start():  # start() roi lai `with` (goi start() lan 2)
            pass
        self.assertEqual(len(opened), 1)

    def test_frames_rotated_when_read(self):
        with reader_with(FakeCapture(read_delay=0.005), rotate=90) as cam:
            fid, frame = cam.wait_new(after_id=0, timeout=1)
        self.assertEqual(frame.shape, (FRAME_W, FRAME_H, 3))  # 1280x720 ngang -> 720x1280 doc
        self.assertEqual(frame_number(rotate_frame(frame, 270)), fid)  # xoay nguoc lai dung khung goc

    def test_invalid_rotate_rejected_before_opening(self):
        opened = []
        with self.assertRaises(ValueError):
            CameraReader("0", {**CAM_CFG, "rotate": 45}, capture_factory=opened.append)
        self.assertEqual(opened, [])

    def test_stop_releases_capture(self):
        cap = FakeCapture(read_delay=0.005)
        cam = reader_with(cap).start()
        cam.stop()
        self.assertFalse(cam._thread.is_alive())
        self.assertTrue(cap.released)


if __name__ == "__main__":
    unittest.main()
