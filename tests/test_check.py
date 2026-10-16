"""Test check(): 1 luot kiem tra tren luong camera (nguon gia + bo phat hien gia).
Chay: .venv\\Scripts\\python.exe -m unittest discover -s tests -v"""
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.checkpoint.camera import CameraError, CameraReader
from src.checkpoint.check import check
from src.checkpoint.evaluate import DAT, KHONG_DAT, KHONG_XAC_DINH, evaluate_frames
from fakes import CAM_CFG, FULL, NO_HAT, REQUIRED, SETTINGS, ZONE, FakeCapture, IndexDetector, numbered_frame


def camera(capture, source="0", **cfg):
    return CameraReader(source, {**CAM_CFG, **cfg}, capture_factory=lambda src: capture).start()


class CheckTest(unittest.TestCase):
    def test_total_time_close_to_timeout(self):
        # Camera ~100 khung/s, model gia 50 ms/khung, timeout 0.6 s: xu ly khung ngay khi co,
        # bo qua khung camera dua ra trong luc model dang chay -> tong thoi gian ~ timeout.
        det = IndexDetector(lambda i: FULL, delay=0.05)
        with camera(FakeCapture(read_delay=0.01)) as cam:
            id_before = cam.latest_id
            r = check(cam, ZONE, REQUIRED, SETTINGS, det, timeout=0.6)
            delivered = cam.latest_id - id_before
        self.assertEqual(r["ket_qua"], DAT)
        self.assertGreaterEqual(r["thoi_gian_ms"], 600)
        self.assertLess(r["thoi_gian_ms"], 800)  # vuot it nhat 1 khung dang xu ly do (~50 ms)
        self.assertTrue(5 <= r["so_khung"] <= 13, r["so_khung"])
        self.assertGreater(delivered, r["so_khung"])  # co khung bi bo qua, khong xep hang
        self.assertGreaterEqual(r["ms_moi_khung"], 50)

    def test_each_frame_processed_once_in_order(self):
        # Camera cham (~20 khung/s), model nhanh: moi khung moi chi xu ly 1 lan, dung thu tu.
        det = IndexDetector(lambda i: FULL)
        with camera(FakeCapture(read_delay=0.05)) as cam:
            r = check(cam, ZONE, REQUIRED, SETTINGS, det, timeout=0.5)
        self.assertEqual(len(det.seen), len(set(det.seen)))
        self.assertEqual(det.seen, sorted(det.seen))
        self.assertTrue(6 <= r["so_khung"] <= 11, r["so_khung"])

    def test_only_frames_after_call(self):
        # Khung da co truoc luc goi check (co the chup truoc khi cong nhan buoc vao) khong duoc xet.
        det = IndexDetector(lambda i: FULL)
        with camera(FakeCapture(read_delay=0.02)) as cam:
            time.sleep(0.1)
            id_at_call = cam.latest_id
            check(cam, ZONE, REQUIRED, SETTINGS, det, timeout=0.3)
        self.assertGreater(min(det.seen), id_at_call)

    def test_same_result_as_evaluate_frames(self):
        # Cung chuoi khung -> check va evaluate_frames cho cung ket qua (dung chung classify_frame/aggregate).
        script = lambda i: NO_HAT if i % 3 == 0 else FULL  # mu co mat ~2/3 so khung
        det_check = IndexDetector(script)
        with camera(FakeCapture(n_frames=15, fps=50), source="video.mp4", loop_video=False) as cam:
            r_check = check(cam, ZONE, REQUIRED, SETTINGS, det_check, timeout=2)
        frames = [numbered_frame(i) for i in det_check.seen]
        r_eval = evaluate_frames(frames, ZONE, REQUIRED, SETTINGS, detector=IndexDetector(script))
        for key in ("ket_qua", "thieu", "ty_le_co_mat", "so_khung", "so_khung_hop_le", "dem_khung", "ly_do"):
            self.assertEqual(r_check[key], r_eval[key], key)

    def test_missing_items_reported(self):
        det = IndexDetector(lambda i: NO_HAT)
        with camera(FakeCapture(read_delay=0.02)) as cam:
            r = check(cam, ZONE, REQUIRED, SETTINGS, det, timeout=0.3)
        self.assertEqual((r["ket_qua"], r["thieu"]), (KHONG_DAT, ["thieu_mu"]))
        self.assertTrue(r["anh_jpeg"])

    def test_timeout_from_config(self):
        settings = {**SETTINGS, "checkpoint": {**SETTINGS["checkpoint"], "timeout_s": 0.3}}
        with camera(FakeCapture(read_delay=0.02)) as cam:
            r = check(cam, ZONE, REQUIRED, settings, IndexDetector(lambda i: FULL))
        self.assertTrue(300 <= r["thoi_gian_ms"] < 450, r["thoi_gian_ms"])

    def test_no_new_frame_raises_camera_error(self):
        # Video 1 khung, khong phat lai: sau khung dau khong con khung moi -> loi thiet bi.
        with camera(FakeCapture(n_frames=1, fps=10), source="video.mp4", loop_video=False) as cam:
            with self.assertRaises(CameraError):
                check(cam, ZONE, REQUIRED, SETTINGS, IndexDetector(lambda i: FULL), timeout=0.3)

    def test_few_frames_is_khong_xac_dinh(self):
        # Camera rat cham (2 khung trong 0.3 s) -> it khung hop le -> KHONG_XAC_DINH.
        with camera(FakeCapture(read_delay=0.12)) as cam:
            r = check(cam, ZONE, REQUIRED, SETTINGS, IndexDetector(lambda i: FULL), timeout=0.3)
        self.assertEqual((r["ket_qua"], r["ly_do"]), (KHONG_XAC_DINH, "it_khung_hop_le"))


if __name__ == "__main__":
    unittest.main()
