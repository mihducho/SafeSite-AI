"""Test camera cong (camera dien thoai DroidCam): mo URL co thoi gian cho, cong tu thu mo lai camera moi 2 giay, bao
"mat ket noi camera" khi khong co khung moi va tu het khi co hinh lai, trang/API cau hinh cong (nguon, goc xoay, vung),
chieu rong mat trong ket qua luot, va khong co cho nao trong app/ mo thang camera (DroidCam chi cho 1 ket noi).
Chay: .venv\\Scripts\\python.exe -m unittest discover -s tests -v"""
import re
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

import cv2
import numpy as np
from starlette.websockets import WebSocketDisconnect

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from test_app import AppCase, FrameReader  # noqa: E402

import app.gate_service as gs  # noqa: E402
from app.models import Gate  # noqa: E402
from fakes import FRAME, FULL, SETTINGS, ZONE  # noqa: E402
from src.checkpoint import camera  # noqa: E402
from src.checkpoint.camera import CameraError, parse_source  # noqa: E402
from src.gate.round import evaluate_round  # noqa: E402
from test_face import HEAD_FACE  # noqa: E402
from test_gate import AlwaysDetector, FakeEmbedder, FakeFaceDetector  # noqa: E402


class OpenUrlTest(unittest.TestCase):
    def test_url_mo_bang_ffmpeg_co_thoi_gian_cho(self):
        calls = []

        class Cap:
            def __init__(self, *args):
                calls.append(args)

            def set(self, *a):
                return True

            def isOpened(self):
                return True

        with mock.patch.object(camera.cv2, "VideoCapture", Cap):
            camera.open_capture(parse_source("http://192.0.2.1:4747/video/force/1280x720"),
                                {"url_open_timeout_s": 5, "url_read_timeout_s": 4})
        url, backend, params = calls[0]
        self.assertEqual(backend, cv2.CAP_FFMPEG)
        self.assertEqual(params, [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000, cv2.CAP_PROP_READ_TIMEOUT_MSEC, 4000])

    def test_khong_noi_nao_trong_app_mo_thang_camera(self):
        for f in (ROOT / "app").rglob("*.py"):
            text = f.read_text(encoding="utf-8")
            with self.subTest(file=f.name):
                self.assertNotIn("VideoCapture", text)
                if f.name != "gate_service.py":
                    self.assertIsNone(re.search(r"CameraReader\(", text))


class RongMatTest(unittest.TestCase):
    def test_ket_qua_luot_co_chieu_rong_mat(self):
        r = evaluate_round([FRAME] * 4, ZONE, SETTINGS, AlwaysDetector(FULL), FakeFaceDetector([HEAD_FACE]), FakeEmbedder())
        self.assertEqual(r["khuon_mat"]["rong_mat_px"], 60)


class StuckReader:
    """Camera gia: latest_id chi doi khi test goi tick() (gia lap dien thoai khoa man hinh roi mo lai)."""

    def __init__(self):
        self.fid, self.frame = 1, np.zeros((1280, 720, 3), np.uint8)

    def tick(self):
        self.fid += 1

    @property
    def latest_id(self):
        return self.fid

    def latest(self):
        return self.fid, self.frame

    def wait_new(self, after_id, timeout):
        time.sleep(min(timeout, 0.05))
        return (self.fid, self.frame) if self.fid > after_id else None

    def stop(self):
        pass


class GateCameraTest(AppCase):
    def add_gate(self, rotate=90):
        with self.app.state.db.session() as s:
            s.add(Gate(name="Cổng chính", camera_source="http://192.0.2.1:4747/video/force/1280x720", zone=ZONE,
                       rotate=rotate))
            s.commit()

    def wait(self, cond, timeout=10.0):
        t = time.monotonic()
        while not cond() and time.monotonic() - t < timeout:
            time.sleep(0.02)
        return cond()

    def test_chua_mo_duoc_camera_thi_thu_lai_den_khi_co_hinh(self):
        self.add_gate()
        gate = self.app.state.gate
        gate.settings = {**gate.settings, "camera": {**gate.settings["camera"], "reconnect_delay_s": 0.05}}
        gate._models_factory = lambda: (AlwaysDetector(FULL), FakeFaceDetector([]), FakeEmbedder())
        attempts, seen_cfg = [], []

        class Reader(StuckReader):
            def start(self):
                attempts.append(1)
                if len(attempts) < 3:
                    raise CameraError("Khong mo duoc nguon hinh")
                return self

        def factory(src, cam_cfg):
            seen_cfg.append((src, cam_cfg["rotate"]))
            return Reader()

        gate._reader_factory = factory
        gate.start()
        self.assertTrue(self.wait(lambda: len(attempts) >= 1))
        self.assertTrue(self.wait(lambda: gate.status()["trang_thai"] == "dang_chay"))
        self.assertEqual(len(attempts), 3)                       # 2 lan loi, lan 3 duoc
        self.assertEqual(seen_cfg[0], ("http://192.0.2.1:4747/video/force/1280x720", 90))  # goc xoay cua cong
        st = gate.status()
        self.assertEqual((st["mat_camera"], st["loi"], st["xoay"], st["do_phan_giai"]), (False, None, 90, "720x1280"))
        gate.stop()

    def test_dang_thu_lai_thi_bao_mat_camera(self):
        self.add_gate()
        gate = self.app.state.gate
        gate._models_factory = lambda: (AlwaysDetector(FULL), FakeFaceDetector([]), FakeEmbedder())

        class Broken(StuckReader):
            def start(self):
                raise CameraError("Khong mo duoc nguon hinh")
        gate._reader_factory = lambda src, cfg: Broken()
        gate.start()
        self.assertTrue(self.wait(lambda: gate.status()["mat_camera"]))
        self.login()
        st = self.client.get("/api/cong/trang-thai").json()
        self.assertTrue(st["gian_doan"])
        self.assertTrue(st["loi"].startswith("Mất kết nối camera, đang thử lại"))
        self.assertEqual(self.client.get("/api/cong-nhan").status_code, 200)  # web van chay
        t = time.monotonic()
        gate.stop()                                                # dung ngay, khong doi het luot thu
        self.assertLess(time.monotonic() - t, 1.0)

    def test_mat_khung_hinh_khi_dang_chay_roi_co_lai(self):
        gate = self.app.state.gate
        reader = StuckReader()
        gate.reader, gate.worker, gate.trang_thai = reader, mock.Mock(state=mock.Mock(phase="CHO"), rounds=0, error=None, round=None), "dang_chay"
        with mock.patch.object(gs, "NO_FRAME_SECONDS", 0.2):
            self.assertFalse(gate.status()["mat_camera"])
            for _ in range(5):      # co khung moi deu dan -> do duoc so khung/giay
                time.sleep(0.03)
                reader.tick()
                gate.status()
            self.assertIsNotNone(gate.status()["khung_giay"])
            normal = gate.render_frame()
            time.sleep(0.3)         # khong co khung moi (dien thoai khoa man hinh)
            st = gate.status()
            self.assertEqual((st["mat_camera"], st["loi"], st["khung_giay"]), (True, "Mất kết nối camera, đang thử lại", None))
            self.assertIsNone(gate.latest_frame())                 # khong chup mau tu khung cu
            self.assertNotEqual(gate.render_frame(), normal)       # luong hinh hien "mat ket noi camera"
            reader.tick()                                          # co hinh lai -> tu het bao loi
            st = gate.status()
            self.assertEqual((st["mat_camera"], st["loi"]), (False, None))
        gate.reader = gate.worker = None
        gate.trang_thai = "tat"


class GateConfigApiTest(AppCase):
    def setUp(self):
        super().setUp()
        with self.app.state.db.session() as s:
            s.add(Gate(name="Cổng chính", camera_source="0", zone=ZONE, rotate=0))
            s.commit()
        self.login()

    def test_doc_va_sua_nguon_goc_xoay_vung(self):
        g = self.client.get("/api/cong").json()
        self.assertEqual((g["camera_source"], g["rotate"], g["zone"], g["ghi_de_boi_env"]), ("0", 0, ZONE, False))
        r = self.client.patch("/api/cong", json={"camera_source": " http://192.0.2.1:4747/video/force/1280x720 ",
                                                 "rotate": 90, "khoi_dong_lai": False}).json()
        self.assertEqual((r["camera_source"], r["rotate"]), ("http://192.0.2.1:4747/video/force/1280x720", 90))
        self.assertEqual(r["zone"], [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])  # doi goc xoay -> vung ve lai
        self.assertIn("vẽ lại vùng", r["ghi_chu"])
        zone = [[0.2, 0.55], [0.8, 0.55], [0.85, 0.98], [0.15, 0.98]]
        r = self.client.patch("/api/cong", json={"zone": zone, "khoi_dong_lai": False}).json()
        self.assertEqual((r["zone"], r["rotate"], r["ghi_chu"]), (zone, 90, None))

    def test_tu_choi_du_lieu_sai(self):
        for body, code in (({"rotate": 45}, 422), ({"zone": [[0.1, 0.1], [0.5, 0.5]]}, 400),
                           ({"zone": [[0, 0], [640, 0], [640, 480]]}, 400),
                           ({"camera_source": "rtsp://admin:matkhau@192.0.2.1/live"}, 400)):
            with self.subTest(body=body):
                self.assertEqual(self.client.patch("/api/cong", json={**body, "khoi_dong_lai": False}).status_code, code)
        self.assertEqual(self.client.get("/api/cong").json()["camera_source"], "0")

    def test_anh_hien_tai_lay_tu_luong_doc_chung(self):
        self.assertEqual(self.client.get("/api/cong/anh-hien-tai").status_code, 503)
        self.app.state.gate.reader = FrameReader(np.zeros((1280, 720, 3), np.uint8))
        r = self.client.get("/api/cong/anh-hien-tai")
        self.assertEqual((r.status_code, r.headers["content-type"]), (200, "image/jpeg"))
        img = cv2.imdecode(np.frombuffer(r.content, np.uint8), cv2.IMREAD_COLOR)
        self.assertEqual(img.shape[:2], (1280, 720))  # khung doc sau khi xoay, khong bi doi kich thuoc
        page = self.client.get("/cau-hinh-cong")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Vùng kiểm tra", page.text)


class ShutdownTest(AppCase):
    def test_ung_dung_dang_tat_thi_dong_websocket(self):
        self.login()
        with self.client.websocket_connect("/ws/events") as ws:
            self.assertEqual(ws.receive_json()["loai"], "trang_thai")
            self.client.portal.call(self.app.state.shutting_down.set)  # nhu luc bam Ctrl+C
            with self.assertRaises(WebSocketDisconnect):
                ws.receive_json()
        r = self.client.get("/stream/gate")  # luong hinh ket thuc ngay, khong phat mai
        self.assertEqual(r.status_code, 200)


if __name__ == "__main__":
    unittest.main()
