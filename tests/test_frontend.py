"""Test giao dien React o che do demo (FastAPI phuc vu frontend/dist): fallback ve index.html cho duong dan cua giao
dien, khong che /api, /ws, /stream, /docs, /cu, /static; chua build -> chuyen sang giao dien cu /cu/. Kem 2 phan API them
cho giao dien React: /api/cau-hinh-web va so luot theo gio trong /api/tong-quan.
Chay: .venv\\Scripts\\python.exe -m unittest discover -s tests -v"""
import sys
import unittest
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from starlette.websockets import WebSocketDisconnect  # noqa: E402

from test_app import AppCase  # noqa: E402

from app.db import utcnow  # noqa: E402
from app.services.cham_cong import mui_gio  # noqa: E402
from src.checkpoint.evaluate import KHONG_DAT, KHONG_XAC_DINH  # noqa: E402

INDEX = "<!doctype html><html lang=\"vi\"><div id=\"root\">giao dien React</div></html>"


class FrontendTest(AppCase):
    def build(self) -> Path:
        """Gia lap `npm run build`: index.html + 1 file trong assets/ + favicon."""
        dist = Path(self.app.state.settings["paths"]["frontend_dist"])
        (dist / "assets").mkdir(parents=True)
        (dist / "index.html").write_text(INDEX, encoding="utf-8")
        (dist / "assets" / "index-abc123.js").write_text("console.log('ok')", encoding="utf-8")
        (dist / "favicon.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
        (dist.parent / "bi_mat.txt").write_text("khong duoc doc", encoding="utf-8")
        return dist

    def test_chua_build_thi_chuyen_sang_giao_dien_cu(self):
        for path, to in (("/", "/cu/"), ("/cong-nhan/5", "/cu/"), ("/login?next=/docs", "/cu/login?next=/docs")):
            with self.subTest(path=path):
                r = self.client.get(path, follow_redirects=False)
                self.assertEqual((r.status_code, r.headers["location"]), (307, to))

    def test_da_build_duong_dan_giao_dien_tra_index(self):
        self.build()
        for path in ("/", "/login", "/cong-nhan/5", "/man-hinh-cong", "/bang-cong-thang"):
            with self.subTest(path=path):
                r = self.client.get(path)
                self.assertEqual(r.status_code, 200)
                self.assertIn("giao dien React", r.text)
                self.assertEqual(r.headers["cache-control"], "no-cache")
        r = self.client.get("/assets/index-abc123.js")
        self.assertEqual((r.status_code, r.text), (200, "console.log('ok')"))
        self.assertIn("immutable", r.headers["cache-control"])
        self.assertEqual(self.client.get("/favicon.svg").status_code, 200)
        self.assertNotIn("khong duoc doc", self.client.get("/..%2fbi_mat.txt").text)  # khong doc file ngoai dist

    def test_khong_che_cac_nhanh_cua_backend(self):
        self.build()
        for path in ("/api/khong-co", "/stream/khong-co", "/cu/khong-co", "/static/khong-co.js", "/ws/khong-co"):
            with self.subTest(path=path):
                r = self.client.get(path)
                self.assertEqual(r.status_code, 404)
                self.assertNotIn("giao dien React", r.text)
        self.assertEqual(self.client.get("/api/cong-nhan").status_code, 401)        # API that van chay, van can dang nhap
        r = self.client.get("/docs", follow_redirects=False)
        self.assertEqual((r.status_code, r.headers["location"]), (303, "/login?next=/docs"))
        r = self.client.get("/cu/", follow_redirects=False)
        self.assertEqual((r.status_code, r.headers["location"]), (303, "/cu/login?next=/cu/"))
        self.assertEqual(self.client.get("/cu", follow_redirects=False).headers["location"], "/cu/")
        self.assertIn("Đăng nhập", self.client.get("/cu/login").text)               # giao dien cu van dung duoc
        self.assertIn("SG", self.client.get("/static/js/common.js").text)
        with self.assertRaises(WebSocketDisconnect) as cm:
            with self.client.websocket_connect("/ws/events") as ws:
                ws.receive_json()
        self.assertEqual(cm.exception.code, 1008)
        self.login()
        self.assertEqual(self.client.get("/api/toi").json()["username"], "admin")
        self.assertEqual(self.client.get("/cu/").status_code, 200)


class WebConfigTest(AppCase):
    def test_tham_so_giao_dien_lay_tu_settings(self):
        self.assertEqual(self.client.get("/api/cau-hinh-web").status_code, 401)
        self.login()
        d = self.client.get("/api/cau-hinh-web").json()
        s = self.app.state.settings
        tz = mui_gio(s["attendance"])
        self.assertEqual(d["ngay_hom_nay"], utcnow().astimezone(tz).date().isoformat())
        self.assertEqual((d["mui_gio"], d["mau_toi_thieu"], d["mau_toi_da"], d["giay_hien_ket_qua"], d["so_dong_trang"]),
                         (s["attendance"]["timezone"], s["face"]["min_samples"], s["face"]["max_samples"],
                          s["web"]["gate_result_seconds"], s["web"]["page_size"]))


class LuotTheoGioTest(AppCase):
    def test_tong_quan_dem_luot_theo_gio_hom_nay(self):
        self.ca_ca_ngay()
        tz = mui_gio(self.app.state.settings["attendance"])
        now = utcnow().astimezone(tz)
        self.add_check(now, KHONG_DAT, ["thieu_mu"])   # vao khong dat: do
        self.add_check(now)                      # DAT: ghi vao, xanh
        self.add_check(now, KHONG_XAC_DINH)      # ngay sau luot vao: bo qua trung, xanh
        self.add_check(now - timedelta(days=1))  # hom qua: khong tinh
        self.login()
        rows = self.client.get("/api/tong-quan").json()["luot_theo_gio"]
        self.assertEqual([r["gio"] for r in rows], list(range(24)))
        old = {k: rows[now.hour][k] for k in ("gio", "dat", "khong_dat", "khac")}  # truong cu: theo ket qua bao ho
        self.assertEqual(old, {"gio": now.hour, "dat": 1, "khong_dat": 1, "khac": 1})
        self.assertEqual({k: rows[now.hour][k] for k in ("xanh", "do", "vang")}, {"xanh": 2, "do": 1, "vang": 0})
        self.assertEqual(sum(r["dat"] + r["khong_dat"] + r["khac"] for r in rows), 3)


if __name__ == "__main__":
    unittest.main()
