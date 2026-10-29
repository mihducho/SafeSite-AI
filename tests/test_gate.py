"""Test cong (src/gate/): ket hop ket qua (luat nhieu_mat), may trang thai, 1 luot day du va vong lap cong voi
du lieu gia (bo phat hien nguoi gia + bo tim mat gia + camera gia). Khong can mo hinh, khong can video.
Chay: .venv\\Scripts\\python.exe -m unittest discover -s tests -v"""
import copy
import sys
import time
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.checkpoint.camera import CameraReader
from src.checkpoint.evaluate import DAT, KHONG_DAT, NHIEU_NGUOI
from src.face.face_detector import Faces
from src.face.match import l2_normalize
from src.gate.combine import combine
from src.gate.round import evaluate_round
from src.gate.state import CHO, CHO_ROI_DI, KIEM_TRA, GateState, on_idle_frame, on_round_done
from src.gate.worker import GateWorker
from fakes import CAM_CFG, FRAME, FULL, MODEL_NAMES, NO_HAT, SETTINGS, ZONE, FakeCapture
from test_face import HEAD_FACE, face

GATE = {"trigger_frames": 3, "cooldown_seconds": 4, "empty_seconds": 1.0}


def ppe(ket_qua=KHONG_DAT, thieu=("thieu_mu",), ly_do=None):
    return {"ket_qua": ket_qua, "thieu": list(thieu), "ly_do": ly_do, "so_khung": 10}


def faces_summary(multi, n=10):
    return {"vectors": [], "chat_luong": [], "so_khung": n, "so_khung_co_mat": n, "so_khung_nhieu_mat": multi,
            "ty_le_khung_nhieu_mat": multi / n, "trang_thai": "CO_MAT"}


class CombineTest(unittest.TestCase):
    def test_nhieu_mat_ghi_de_thanh_nhieu_nguoi(self):
        # Nguoi dung sau bi che than: YOLO chi thay 1 nguoi (KHONG_DAT) nhung 6/10 khung thay 2 mat.
        out = combine(ppe(), faces_summary(6), 0.5)
        self.assertEqual((out["ket_qua"], out["ly_do"], out["thieu"]), (NHIEU_NGUOI, "nhieu_mat", []))
        self.assertEqual((out["ket_qua_bao_ho"], out["thieu_bao_ho"]), (KHONG_DAT, ["thieu_mu"]))  # giu ket qua goc

    def test_bien_nguong_dung_chung(self):
        self.assertEqual(combine(ppe(), faces_summary(5), 0.5)["ket_qua"], NHIEU_NGUOI)   # 5/10 = 0.5
        self.assertEqual(combine(ppe(), faces_summary(4), 0.5)["ket_qua"], KHONG_DAT)     # 4/10 < 0.5

    def test_da_la_nhieu_nguoi_giu_ly_do_cu(self):
        out = combine(ppe(NHIEU_NGUOI, (), None), faces_summary(10), 0.5)
        self.assertEqual((out["ket_qua"], out["ly_do"]), (NHIEU_NGUOI, None))

    def test_khong_doi_ket_qua_bao_ho_khi_mot_mat(self):
        out = combine(ppe(DAT, ()), faces_summary(0), 0.5)
        self.assertEqual((out["ket_qua"], out["khuon_mat"]["trang_thai"]), (DAT, "CO_MAT"))


class StateTest(unittest.TestCase):
    def feed(self, state, t, present):
        return on_idle_frame(state, t, present, GATE)

    def test_du_3_khung_lien_tiep_moi_bat_dau(self):
        s = GateState(since=0.0)
        for t in (0.1, 0.2):
            s, start = self.feed(s, t, True)
            self.assertFalse(start)
        s, start = self.feed(s, 0.3, True)
        self.assertTrue(start)
        self.assertEqual(s.phase, KIEM_TRA)

    def test_mat_bi_ngat_thi_dem_lai(self):
        s = GateState()
        s, _ = self.feed(s, 0.1, True)
        s, _ = self.feed(s, 0.2, True)
        s, _ = self.feed(s, 0.3, False)  # mat mat 1 khung
        s, start = self.feed(s, 0.4, True)
        self.assertEqual((s.streak, start), (1, False))

    def test_da_ghi_cong_cho_nguoi_roi_di(self):
        s = on_round_done(GateState(KIEM_TRA), now=10.0, recorded=True)
        self.assertEqual(s.phase, CHO_ROI_DI)
        # Nguoi van dung do sau 6 giay (qua cooldown 4 s): khong bat dau luot moi -> khong ghi cong lap.
        for t in np.arange(10.1, 16.0, 0.1):
            s, start = self.feed(s, float(t), True)
            self.assertFalse(start)
        self.assertEqual(s.phase, CHO_ROI_DI)
        # Roi di 1 giay (vung trong) -> ve CHO; nguoi moi dung vao du 3 khung -> luot moi.
        s, _ = self.feed(s, 16.1, False)
        s, _ = self.feed(s, 17.2, False)
        self.assertEqual(s.phase, CHO)
        for t in (17.3, 17.4, 17.5):
            s, start = self.feed(s, t, True)
        self.assertTrue(start)

    def test_chua_ghi_cong_kiem_tra_lai_tai_cho_sau_cooldown(self):
        s = on_round_done(GateState(KIEM_TRA), now=10.0, recorded=False)  # vd thieu mu, nguoi dang doi mu
        s, start = self.feed(s, 13.9, True)  # chua qua cooldown 4 s
        self.assertFalse(start)
        self.assertEqual(s.phase, CHO_ROI_DI)
        s, start = self.feed(s, 14.0, True)  # het cooldown: ve CHO, khung nay tinh la khung 1
        self.assertEqual((s.phase, s.streak, start), (CHO, 1, False))
        s, _ = self.feed(s, 14.1, True)
        s, start = self.feed(s, 14.2, True)
        self.assertTrue(start)  # nguoi khong can roi di

    def test_chua_qua_cooldown_thi_chua_bat_dau_du_vung_trong(self):
        s = on_round_done(GateState(KIEM_TRA), now=10.0, recorded=True)
        s, _ = self.feed(s, 10.5, False)
        s, start = self.feed(s, 12.0, False)  # trong 1.5 s nhung moi qua 2 s
        self.assertEqual((s.phase, start), (CHO_ROI_DI, False))

    def test_dang_kiem_tra_khong_nhan_khung_cho(self):
        with self.assertRaises(ValueError):
            on_idle_frame(GateState(KIEM_TRA), 1.0, True, GATE)


class FakeFaceDetector:
    """Tra ve cung 1 danh sach mat cho moi khung."""

    def __init__(self, rows):
        self.rows = np.asarray(rows, np.float32).reshape(-1, 15)
        self.calls = 0

    def detect(self, image, long_side=None):
        self.calls += 1
        return Faces(self.rows.copy())


class FakeEmbedder:
    def embed(self, image, row):
        v = np.zeros(128, np.float32)
        v[0] = 1.0
        return l2_normalize(v)


class AlwaysDetector:
    """Bo phat hien nguoi gia tra ve cung ket qua moi khung."""

    names = MODEL_NAMES

    def __init__(self, dets):
        self.dets = dets

    def __call__(self, frame):
        return self.dets


class GateRoundTest(unittest.TestCase):
    def run_round(self, dets, faces, n=6):
        return evaluate_round([FRAME] * n, ZONE, SETTINGS, AlwaysDetector(dets), FakeFaceDetector(faces), FakeEmbedder())

    def test_du_do_mot_mat(self):
        r = self.run_round(FULL, [HEAD_FACE])
        km = r["khuon_mat"]
        self.assertEqual((r["ket_qua"], r["ket_qua_bao_ho"]), (DAT, DAT))
        self.assertEqual((km["trang_thai"], km["so_khung_co_mat"], len(km["vectors"])), ("CO_MAT", 6, 5))  # toi da 5 vector
        self.assertEqual(km["ty_le_khung_nhieu_mat"], 0.0)
        self.assertIsNotNone(r["anh_jpeg"])

    def test_nguoi_dung_sau_bi_che_than_van_bat_duoc(self):
        # YOLO chi thay 1 nguoi du do (DAT), nhung moi khung co 2 mat cung co -> NHIEU_NGUOI.
        r = self.run_round(FULL, [HEAD_FACE, face(780, 130, 55)])
        self.assertEqual((r["ket_qua_bao_ho"], r["ket_qua"], r["ly_do"]), (DAT, NHIEU_NGUOI, "nhieu_mat"))

    def test_nguoi_xep_hang_xa_khong_lam_hong_ket_qua(self):
        r = self.run_round(NO_HAT, [HEAD_FACE, face(700, 60, 30)])
        self.assertEqual((r["ket_qua"], r["thieu"]), (KHONG_DAT, ["thieu_mu"]))

    def test_mat_ngoai_vung_dau_khong_dung_de_nhan_dang(self):
        r = self.run_round(FULL, [face(570, 300, 60)])  # mat ngang nguc (gio anh/dien thoai)
        self.assertEqual((r["ket_qua"], r["khuon_mat"]["trang_thai"]), (DAT, "KHONG_THAY_MAT"))


class GateWorkerTest(unittest.TestCase):
    def test_vong_lap_cong_chay_1_luot_roi_cho_nguoi_roi_di(self):
        s = copy.deepcopy(SETTINGS)
        s["checkpoint"]["timeout_s"] = 0.3
        s["gate"].update(idle_max_fps=200, trigger_frames=3, cooldown_seconds=4)
        results = []
        with CameraReader("0", CAM_CFG, capture_factory=lambda src: FakeCapture(read_delay=0.01)) as cam:
            worker = GateWorker(cam, ZONE, s, AlwaysDetector(FULL), FakeFaceDetector([HEAD_FACE]), FakeEmbedder(),
                                on_result=lambda r: results.append(r) or True)
            t = time.monotonic()
            while not results and time.monotonic() - t < 5:
                worker.step()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["ket_qua"], DAT)
        self.assertIn("tu_luc_thay_mat_ms", results[0])
        self.assertEqual((worker.state.phase, worker.state.recorded, worker.rounds), (CHO_ROI_DI, True, 1))


if __name__ == "__main__":
    unittest.main()
