"""Test ung dung web (app/): dang nhap, API JSON, WebSocket, luong hinh MJPEG, va cong chay that trong ung dung voi camera
gia + mo hinh gia (GateWorker -> xu_ly_luot -> CSDL -> WebSocket). CSDL SQLite trong bo nho, khong can camera/mo hinh.
Chay: .venv\\Scripts\\python.exe -m unittest discover -s tests -v"""
import copy
import logging
import sys
import tempfile
import threading
import time
import unittest
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

warnings.filterwarnings("ignore", message=".*httpx.*")  # starlette 1.x: canh bao doi sang httpx2, khong anh huong test
logging.getLogger("uvicorn.error").setLevel(logging.ERROR)  # an canh bao "chua co tai khoan" luc khoi dong ung dung test
from fastapi.testclient import TestClient  # noqa: E402
from starlette.websockets import WebSocketDisconnect  # noqa: E402

from app_helpers import (PASSWORD, add_admin, add_shift, add_worker, app_config, fake_face_models, luot,  # noqa: E402
                         sample_image, sample_jpeg_bytes, vn)
from fakes import CAM_CFG, FULL, ZONE, FakeCapture  # noqa: E402
from test_face import HEAD_FACE  # noqa: E402
from test_gate import AlwaysDetector, FakeEmbedder, FakeFaceDetector  # noqa: E402

from app.main import create_app  # noqa: E402
from app.models import Attendance, Gate, PpeCheck  # noqa: E402
from app.services.luot import xu_ly_luot  # noqa: E402
from src.checkpoint.camera import CameraError, CameraReader  # noqa: E402
from src.checkpoint.evaluate import DAT, KHONG_DAT  # noqa: E402


class FrameReader:
    """Thay CameraReader cho chuc nang chup mau: chi co latest()."""

    def __init__(self, frame):
        self.frame = frame

    def latest(self):
        return 1, self.frame

    def stop(self):
        pass


class AppCase(unittest.TestCase):
    start_gate = False

    def make_app(self, **kw):
        return create_app(self.cfg, start_gate=False, face_models=fake_face_models, **kw)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = app_config(tmp=self.tmp.name)
        self.app = self.make_app()
        self.client = TestClient(self.app)
        self.client.__enter__()  # chay lifespan: tao bang
        with self.app.state.db.session() as s:
            self.admin_id = add_admin(s).id
            add_shift(s)
            self.an_id = add_worker(s, "CN001", "Nguyễn Văn An", face_index=0).id

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.app.state.db.engine.dispose()
        self.tmp.cleanup()

    def login(self):
        r = self.client.post("/api/dang-nhap", json={"username": "admin", "password": PASSWORD})
        self.assertEqual(r.status_code, 200, r.text)

    def add_check(self, t, ket_qua=DAT, thieu=(), face_index=0) -> dict:
        st = self.app.state
        with st.db.session() as s:
            return xu_ly_luot(s, luot(t, ket_qua, thieu, face_index), settings=st.settings, nhan_dien=st.nhan_dien,
                              image_dir=st.image_dir)


class AuthTest(AppCase):
    def test_chua_dang_nhap_bi_chan(self):
        for path in ("/api/cong-nhan", "/api/tong-quan", "/api/luot", "/stream/gate?so_khung=1"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 401)
        for path, login in (("/docs", "/login"), ("/openapi.json", "/login"), ("/cu/", "/cu/login")):
            with self.subTest(path=path):  # /docs -> dang nhap o giao dien React; giao dien cu -> /cu/login
                r = self.client.get(path, follow_redirects=False)
                self.assertEqual((r.status_code, r.headers["location"]), (303, f"{login}?next={path}"))
        with self.assertRaises(WebSocketDisconnect) as cm:
            with self.client.websocket_connect("/ws/events") as ws:
                ws.receive_json()
        self.assertEqual(cm.exception.code, 1008)
        self.assertEqual(self.client.get("/cu/login").status_code, 200)  # trang dang nhap khong can dang nhap

    def test_dang_nhap_sai_dung_va_dang_xuat(self):
        r = self.client.post("/api/dang-nhap", json={"username": "admin", "password": "sai"})
        self.assertEqual(r.status_code, 401)
        self.login()
        self.assertEqual(self.client.get("/api/toi").json()["username"], "admin")
        self.assertEqual(self.client.get("/docs").status_code, 200)
        self.assertIn("/api/cong-nhan", self.client.get("/openapi.json").json()["paths"])
        self.client.post("/api/dang-xuat")
        self.assertEqual(self.client.get("/api/toi").status_code, 401)

    def test_form_dang_nhap(self):
        r = self.client.post("/cu/login", data={"username": "admin", "password": PASSWORD, "next": "/docs"},
                             follow_redirects=False)
        self.assertEqual((r.status_code, r.headers["location"]), (303, "/docs"))
        r = self.client.post("/cu/login", data={"username": "admin", "password": "sai", "next": "//trang-ngoai.com"})
        self.assertEqual(r.status_code, 401)
        self.assertNotIn("trang-ngoai", r.text)  # khong cho chuyen huong ra trang ngoai


class WorkerApiTest(AppCase):
    def setUp(self):
        super().setUp()
        self.login()

    def test_to_doi_va_cong_nhan_tim_kiem_loc_sua_nghi_viec(self):
        team = self.client.post("/api/to-doi", json={"name": "Tổ cốp pha", "contractor": "Nhà thầu A"}).json()
        r = self.client.post("/api/cong-nhan", json={"code": "CN002", "full_name": "Trần Thị Bình", "team_id": team["id"],
                                                     "trade": "Thợ cốp pha"})
        self.assertEqual(r.status_code, 201, r.text)
        binh = r.json()
        self.assertEqual(self.client.post("/api/cong-nhan", json={"code": "CN002", "full_name": "X"}).status_code, 400)
        self.assertEqual(self.client.post("/api/cong-nhan", json={"code": "", "full_name": "X"}).status_code, 422)

        ds = self.client.get("/api/cong-nhan").json()
        self.assertEqual((ds["tong"], [w["code"] for w in ds["ds"]]), (2, ["CN001", "CN002"]))
        self.assertEqual(ds["ds"][0]["so_mau"], 3)
        self.assertEqual([w["code"] for w in self.client.get("/api/cong-nhan", params={"q": "bình"}).json()["ds"]], ["CN002"])
        self.assertEqual([w["code"] for w in self.client.get("/api/cong-nhan", params={"to_doi": team["id"]}).json()["ds"]],
                         ["CN002"])
        r = self.client.patch(f"/api/cong-nhan/{binh['id']}", json={"phone": "0912345678"})
        self.assertEqual((r.json()["phone"], r.json()["full_name"]), ("0912345678", "Trần Thị Bình"))
        self.assertEqual(self.client.patch(f"/api/to-doi/{team['id']}", json={"leader_name": "Anh Tư"}).json()["leader_name"],
                         "Anh Tư")
        self.assertEqual(self.client.get("/api/to-doi").json()["ds"][0]["so_cong_nhan"], 1)

        r = self.client.post(f"/api/cong-nhan/{self.an_id}/nghi-viec").json()
        self.assertEqual((r["cong_nhan"]["status"], r["so_mau_da_xoa"]), ("nghi_viec", 3))
        self.assertEqual([w["code"] for w in self.client.get("/api/cong-nhan", params={"trang_thai": "dang_lam"}).json()["ds"]],
                         ["CN002"])
        self.assertEqual(self.client.get("/api/cong-nhan/999").status_code, 404)

    def test_dong_y_tai_anh_xem_xoa_mau(self):
        w = self.client.post("/api/cong-nhan", json={"code": "CN005", "full_name": "Võ Văn Em"}).json()
        files = [("files", ("a.png", sample_jpeg_bytes(5), "image/png"))]
        r = self.client.post(f"/api/cong-nhan/{w['id']}/mau-mat/tai-len", files=files)
        self.assertEqual(r.status_code, 400)
        self.assertIn("đồng ý", r.json()["detail"])  # chua dong y: khong them duoc mau
        self.assertEqual(self.client.post(f"/api/cong-nhan/{w['id']}/dong-y", json={"dong_y": False}).status_code, 400)
        r = self.client.post(f"/api/cong-nhan/{w['id']}/dong-y", json={"dong_y": True})
        self.assertIsNotNone(r.json()["consent_at"])
        self.assertEqual(r.json()["consent_by"], self.admin_id)

        files = [("files", (f"{i}.png", sample_jpeg_bytes(5), "image/png")) for i in range(3)]
        files.append(("files", ("khong_mat.png", sample_jpeg_bytes(5, n_faces=0), "image/png")))
        files.append(("files", ("hong.jpg", b"khong phai anh", "image/jpeg")))
        r = self.client.post(f"/api/cong-nhan/{w['id']}/mau-mat/tai-len", files=files).json()
        self.assertEqual([x["ok"] for x in r["ket_qua"]], [True, True, True, False, False])
        self.assertEqual(r["ket_qua"][3]["ly_do"], "Không thấy khuôn mặt trong ảnh")
        self.assertEqual(r["so_mau"], 3)

        ds = self.client.get(f"/api/cong-nhan/{w['id']}/mau-mat").json()
        self.assertEqual((ds["so_mau"], ds["du_mau"], ds["toi_da"]), (3, True, 10))
        img = self.client.get(ds["ds"][0]["anh"])
        self.assertEqual((img.status_code, img.headers["content-type"]), (200, "image/jpeg"))
        self.assertEqual(self.client.delete(f"/api/mau-mat/{ds['ds'][0]['id']}").json()["so_mau"], 2)
        self.assertEqual(self.client.delete(f"/api/cong-nhan/{w['id']}/mau-mat").json()["so_mau_da_xoa"], 2)
        self.assertEqual(self.client.get(f"/api/cong-nhan/{w['id']}/mau-mat").json()["so_mau"], 0)

    def test_chup_mau_tu_camera_cong(self):
        url = f"/api/cong-nhan/{self.an_id}/mau-mat/chup"
        r = self.client.post(url)
        self.assertEqual(r.status_code, 503)  # cong chua chay
        self.app.state.gate.reader = FrameReader(sample_image(0))
        r = self.client.post(url)
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(r.json()["so_mau"], 4)
        self.app.state.gate.reader = FrameReader(sample_image(0, n_faces=2))
        r = self.client.post(url)
        self.assertEqual((r.status_code, r.json()["detail"]), (400, "Ảnh có 2 khuôn mặt, cần đúng 1 người"))


class CheckApiTest(AppCase):
    def setUp(self):
        super().setUp()
        self.login()

    def test_luot_loc_phan_trang_anh(self):
        self.add_check(vn(28, 7, 0))
        for m in range(5):
            self.add_check(vn(29, 6, 50 + m), KHONG_DAT, ["thieu_mu"])
        ev = self.add_check(vn(29, 7, 0))
        self.add_check(vn(29, 7, 30), DAT, face_index=50)  # nguoi la
        r = self.client.get("/api/luot", params={"ngay": "2026-10-29", "so_dong": 3}).json()
        self.assertEqual((r["tong"], r["so_trang"], len(r["ds"])), (7, 3, 3))
        self.assertEqual(r["ds"][0]["gio"], "07:30")  # moi nhat truoc
        self.assertEqual(self.client.get("/api/luot", params={"ngay": "2026-10-29", "ket_qua": "KHONG_DAT"}).json()["tong"], 5)
        self.assertEqual(self.client.get("/api/luot", params={"cong_nhan_id": self.an_id}).json()["tong"], 7)
        self.assertEqual(self.client.get("/api/luot", params={"hanh_dong": "ghi_vao"}).json()["tong"], 2)
        c = self.client.get(f"/api/luot/{ev['id']}").json()
        self.assertEqual((c["cong_nhan"]["ma"], c["hanh_dong"], c["thoi_diem"]), ("CN001", "ghi_vao", "2026-10-29T07:00:00+07:00"))
        img = self.client.get(c["anh"])
        self.assertEqual((img.status_code, img.content), (200, b"\xff\xd8gia\xff\xd9"))

    def test_bang_cong_cham_thu_cong_tong_quan(self):
        self.add_check(vn(29, 7, 2))
        body = {"worker_id": self.an_id, "ngay": "2026-10-29", "gio_ra": "16:30"}
        self.assertEqual(self.client.post("/api/cham-cong-thu-cong", json=body).status_code, 422)  # thieu truong ly_do
        r = self.client.post("/api/cham-cong-thu-cong", json={**body, "ly_do": "   "})
        self.assertEqual((r.status_code, r.json()["detail"]), (400, "Bắt buộc ghi lý do khi chấm công thủ công"))
        r = self.client.post("/api/cham-cong-thu-cong", json={**body, "ly_do": "Quên đứng trước camera khi ra"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual((r.json()["trang_thai"], r.json()["gio_ra"], r.json()["updated_by"]),
                         ("cham_thu_cong", "2026-10-29T16:30:00+07:00", self.admin_id))
        row = self.client.get("/api/bang-cong", params={"ngay": "2026-10-29"}).json()["ds"][0]
        self.assertEqual((row["ma"], row["gio_vao"], row["gio_ra"], row["ve_som_phut"], row["trang_thai"]),
                         ("CN001", "07:02", "16:30", 30, "cham_thu_cong"))
        tq = self.client.get("/api/tong-quan").json()
        self.assertEqual(tq["so_cong_nhan"], 1)
        self.assertEqual(tq["cong"]["trang_thai"], "tat")
        self.assertEqual(len(tq["luot_moi_nhat"]), 1)


class RealtimeTest(AppCase):
    def setUp(self):
        super().setUp()
        self.login()

    def test_websocket_nhan_su_kien_tu_thread_khac(self):
        with self.client.websocket_connect("/ws/events") as ws:
            first = ws.receive_json()
            self.assertEqual((first["loai"], first["trang_thai"]), ("trang_thai", "tat"))
            event = {"loai": "luot", "id": 1, "mau": "xanh", "thong_bao": "Xin chào"}
            done = []
            t = threading.Thread(target=lambda: done.append(self.app.state.events.publish_threadsafe(event).result(2)))
            t.start()
            t.join(5)
            self.assertEqual(ws.receive_json(), event)

    def test_luong_hinh_mjpeg(self):
        r = self.client.get("/stream/gate", params={"so_khung": 2})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.headers["content-type"].startswith("multipart/x-mixed-replace"))
        self.assertEqual(r.content.count(b"--frame\r\nContent-Type: image/jpeg"), 2)
        self.assertEqual(r.content.count(b"\xff\xd8"), 2)  # 2 anh JPEG (anh bao trang thai khi cong tat)


class GateInAppTest(AppCase):
    """Cong chay that trong ung dung: camera gia (khung den) + YOLO gia (1 nguoi du do) + YuNet gia (1 mat o vung dau)
    + SFace gia (vector unit(0) = mat cua An) -> ghi gio vao, su kien qua WebSocket."""

    def make_app(self, **kw):
        s = copy.deepcopy(self.cfg.settings)
        s["checkpoint"]["timeout_s"] = 0.3
        s["gate"].update(idle_max_fps=200, trigger_frames=3, cooldown_seconds=4)
        self.cfg.settings = s
        models = lambda: (AlwaysDetector(FULL), FakeFaceDetector([HEAD_FACE]), FakeEmbedder())  # noqa: E731
        reader = lambda src, cam: CameraReader(src, CAM_CFG, capture_factory=lambda _: FakeCapture(read_delay=0.01))  # noqa: E731
        return super().make_app(gate_models=models, reader_factory=reader)

    def wait(self, cond, timeout=10.0):
        t = time.monotonic()
        while not cond() and time.monotonic() - t < timeout:
            time.sleep(0.02)
        return cond()

    def test_luot_vao_ghi_cong_va_phat_su_kien(self):
        self.login()
        with self.app.state.db.session() as s:
            s.add(Gate(name="Cổng test", camera_source="0", zone=ZONE, rotate=0))
            s.commit()
        gate = self.app.state.gate
        with self.client.websocket_connect("/ws/events") as ws:
            gate.start()
            self.assertTrue(self.wait(lambda: gate.last_event is not None), gate.status())
            events = []
            while not any(e["loai"] == "luot" for e in events):
                events.append(ws.receive_json())
        ev = next(e for e in events if e["loai"] == "luot")
        self.assertEqual((ev["hanh_dong"], ev["mau"], ev["cong_nhan"]["ma"]), ("ghi_vao", "xanh", "CN001"))
        self.assertIn("trang_thai", {e["loai"] for e in events})
        self.assertEqual(gate.status()["trang_thai"], "dang_chay")
        self.assertEqual(gate.worker.state.phase, "CHO_ROI_DI")  # da ghi cong: cho nguoi roi khoi vung
        with self.app.state.db.session() as s:
            c = s.get(PpeCheck, ev["id"])
            self.assertEqual((c.result, c.face_status, c.action), (DAT, "DA_NHAN_RA", "ghi_vao"))
            self.assertTrue((self.app.state.image_dir / c.image_path).is_file())
            self.assertEqual(s.query(Attendance).one().ppe_check_id, c.id)
        jpeg = gate.render_frame()
        self.assertTrue(jpeg.startswith(b"\xff\xd8"))
        r = self.client.post(f"/api/cong-nhan/{self.an_id}/mau-mat/chup")  # dung chung camera cong (khung den: khong co mat)
        self.assertEqual((r.status_code, r.json()["detail"]), (400, "Không thấy khuôn mặt trong ảnh"))

    def test_loi_camera_web_van_chay(self):
        with self.app.state.db.session() as s:
            s.add(Gate(name="Cổng test", camera_source="0", zone=ZONE, rotate=0))
            s.commit()
        gate = self.app.state.gate

        def broken(src, cam):
            raise CameraError("Khong mo duoc nguon hinh: 0")
        gate._reader_factory = broken
        gate.start()
        self.assertTrue(self.wait(lambda: gate.status()["mat_camera"]))  # khong bo cuoc: thu lai moi 2 giay
        self.login()
        st = self.client.get("/api/cong/trang-thai").json()
        self.assertEqual((st["gian_doan"], st["loi"]),
                         (True, "Mất kết nối camera, đang thử lại (Khong mo duoc nguon hinh: 0)"))
        self.assertEqual(self.client.get("/api/cong-nhan").status_code, 200)

    def test_chua_co_cong_bao_loi(self):
        gate = self.app.state.gate
        gate.start()
        self.assertTrue(self.wait(lambda: gate.status()["trang_thai"] == "loi"))
        self.assertIn("seed_demo", gate.status()["loi"])


if __name__ == "__main__":
    unittest.main()
