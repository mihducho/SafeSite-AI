"""Test thuat toan kiem tra o cong (evaluate_frames, DE_TAI.md muc 5) bang box gia.
Chay: .venv\\Scripts\\python.exe -m unittest discover -s tests -v

Khung hinh la anh den 1280x720; bo phat hien gia tra ve box dinh san cho tung
khung theo thu tu, nen test khong can model, khong can video.
"""
import copy
import sys
import unittest
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.checkpoint.evaluate import DAT, KHONG_CO_NGUOI, KHONG_DAT, KHONG_XAC_DINH, NHIEU_NGUOI, evaluate_frames
# Box gia, bo phat hien gia, nguong co dinh: dung chung voi test_check.py (tests/fakes.py).
from fakes import (BARE, EMPTY, FRAME, FULL, HAT, HEAD_CUT, NO_HAT, NO_VEST, OUTSIDE, PERSON, REQUIRED,
                   SETTINGS, SMALL, TWO, VEST, ZONE, FakeDetector, dets)

def run(script, zone=ZONE, required=REQUIRED, settings=SETTINGS):
    return evaluate_frames([FRAME] * len(script), zone, required, settings, detector=FakeDetector(script))


class KetQuaTest(unittest.TestCase):
    """Cac truong hop DE_TAI.md Giai doan 1b yeu cau."""

    def test_dat(self):
        r = run([FULL] * 5)
        self.assertEqual(r["ket_qua"], DAT)
        self.assertEqual(r["thieu"], [])
        self.assertEqual(r["ty_le_co_mat"], {"hardhat": 1.0, "vest": 1.0})
        self.assertEqual((r["so_khung"], r["so_khung_hop_le"]), (5, 5))

    def test_khong_dat_thieu_mu(self):
        r = run([NO_HAT] * 5)
        self.assertEqual((r["ket_qua"], r["thieu"]), (KHONG_DAT, ["thieu_mu"]))

    def test_khong_dat_thieu_ao(self):
        r = run([NO_VEST] * 5)
        self.assertEqual((r["ket_qua"], r["thieu"]), (KHONG_DAT, ["thieu_ao"]))

    def test_khong_dat_thieu_ca_hai(self):
        r = run([BARE] * 5)
        self.assertEqual((r["ket_qua"], r["thieu"]), (KHONG_DAT, ["thieu_mu", "thieu_ao"]))

    def test_nhieu_nguoi(self):
        r = run([TWO] * 3 + [FULL] * 2)  # 3/5 khung co 2 nguoi > nua
        self.assertEqual(r["ket_qua"], NHIEU_NGUOI)

    def test_khong_co_nguoi(self):
        r = run([EMPTY] * 5)
        self.assertEqual(r["ket_qua"], KHONG_CO_NGUOI)
        self.assertEqual(r["ty_le_co_mat"], {})

    def test_khong_xac_dinh_it_khung_hop_le(self):
        # 2 khung hop le (< 3), 2 khung trong (khong qua nua), 1 khung nguoi qua nho.
        r = run([FULL, FULL, EMPTY, EMPTY, dets((SMALL, "Person"))])
        self.assertEqual((r["ket_qua"], r["ly_do"]), (KHONG_XAC_DINH, "it_khung_hop_le"))
        self.assertEqual(r["so_khung_hop_le"], 2)

    def test_khong_xac_dinh_dau_bi_cat(self):
        r = run([dets((HEAD_CUT, "Person"), (VEST, "Safety-Vest"))] * 5)
        self.assertEqual(r["ket_qua"], KHONG_XAC_DINH)
        self.assertEqual(r["dem_khung"]["cat_dau"], 5)

    def test_khong_xac_dinh_nguoi_qua_nho(self):
        r = run([dets((SMALL, "Person"))] * 5)
        self.assertEqual(r["ket_qua"], KHONG_XAC_DINH)
        self.assertEqual(r["dem_khung"]["qua_nho"], 5)

    def test_khong_xac_dinh_ty_le_nam_giua(self):
        r = run([FULL] * 2 + [NO_HAT] * 3)  # mu: 2/5 = 0.4, giua 0.2 va 0.6
        self.assertEqual((r["ket_qua"], r["ly_do"]), (KHONG_XAC_DINH, "khong_chac"))
        self.assertEqual(r["ty_le_co_mat"]["hardhat"], 0.4)


class NguongVaBienTest(unittest.TestCase):
    def test_bien_present_ratio_tinh_la_co(self):
        r = run([FULL] * 3 + [NO_HAT] * 2)  # 3/5 = 0.6 >= 0.6
        self.assertEqual(r["ket_qua"], DAT)

    def test_bien_absent_ratio_tinh_la_thieu(self):
        r = run([FULL] + [NO_HAT] * 4)  # 1/5 = 0.2 <= 0.2
        self.assertEqual((r["ket_qua"], r["thieu"]), (KHONG_DAT, ["thieu_mu"]))

    def test_mat_mu_mot_khung_van_dat(self):
        # Model bo sot mu 1 khung (chap chon) khong lam doi ket luan.
        r = run([FULL, FULL, NO_HAT, FULL, FULL])
        self.assertEqual(r["ket_qua"], DAT)

    def test_nhieu_nguoi_khong_qua_nua(self):
        r = run([TWO] * 2 + [FULL] * 3)  # 2/5 khung 2 nguoi, chua qua nua
        self.assertEqual(r["ket_qua"], DAT)

    def test_nguong_lay_tu_cau_hinh(self):
        s = copy.deepcopy(SETTINGS)
        s["checkpoint"]["min_valid_frames"] = 6
        self.assertEqual(run([FULL] * 5, settings=s)["ket_qua"], KHONG_XAC_DINH)


class VungVaGanPPETest(unittest.TestCase):
    def test_nguoi_ngoai_vung_khong_tinh(self):
        r = run([dets((OUTSIDE, "Person"), (VEST, "Safety-Vest"))] * 5)
        self.assertEqual(r["ket_qua"], KHONG_CO_NGUOI)

    def test_khong_co_vung_xet_ca_khung(self):
        full_outside = dets((OUTSIDE, "Person"), ([90, 85, 160, 130], "Hardhat"), ([60, 130, 190, 230], "Safety-Vest"))
        self.assertEqual(run([full_outside] * 5, zone=None)["ket_qua"], DAT)

    def test_mu_cua_nguoi_ngoai_vung_khong_tinh_cho_nguoi_trong_vung(self):
        # Mu nam tron trong vung dau nguoi ngoai vung (ti le 1.0) va 0.83 trong vung dau
        # nguoi trong vung: mu thuoc ve nguoi ngoai vung -> nguoi trong vung thieu mu.
        p_in, p_out = [330, 150, 480, 700], [200, 100, 360, 340]
        frame = dets((p_in, "Person"), (p_out, "Person"), ([325, 100, 355, 140], "Hardhat"),
                     ([340, 250, 470, 500], "Safety-Vest"))
        r = run([frame] * 5)
        self.assertEqual((r["ket_qua"], r["thieu"]), (KHONG_DAT, ["thieu_mu"]))

    def test_box_nguoi_trung_bi_bo(self):
        # Model ve them 1 box nho nam tron trong box nguoi -> van la 1 nguoi, khong NHIEU_NGUOI.
        dup = dets((PERSON, "Person"), ([520, 300, 690, 650], "Person"), (HAT, "Hardhat"), (VEST, "Safety-Vest"))
        self.assertEqual(run([dup] * 5)["ket_qua"], DAT)

    def test_tat_kiem_tra_ao(self):
        r = run([NO_VEST] * 5, required=["hardhat"])
        self.assertEqual(r["ket_qua"], DAT)
        self.assertEqual(r["ty_le_co_mat"], {"hardhat": 1.0})


class DauRaVaLoiTest(unittest.TestCase):
    def test_ket_qua_co_du_truong_va_anh_jpeg(self):
        r = run([FULL] * 5)
        for key in ("ket_qua", "thieu", "ty_le_co_mat", "so_khung", "so_khung_hop_le", "thoi_gian_ms", "anh_jpeg"):
            self.assertIn(key, r)
        img = cv2.imdecode(np.frombuffer(r["anh_jpeg"], np.uint8), cv2.IMREAD_COLOR)
        self.assertEqual(img.shape, (720, 1280, 3))
        self.assertGreaterEqual(r["thoi_gian_ms"], 0)

    def test_khong_co_khung_nao(self):
        r = run([])
        self.assertEqual(r["ket_qua"], KHONG_XAC_DINH)
        self.assertIsNone(r["anh_jpeg"])

    def test_khung_none_bao_loi_ro(self):
        with self.assertRaisesRegex(ValueError, r"vi tri \[1\]"):
            evaluate_frames([FRAME, None], ZONE, REQUIRED, SETTINGS, detector=FakeDetector([FULL, FULL]))

    def test_mon_chua_khai_bao(self):
        with self.assertRaises(ValueError):
            run([FULL], required=["gang_tay"])

    def test_model_thieu_lop_bao_loi(self):
        detector = FakeDetector([FULL], names={0: "person", 1: "helmet"})
        with self.assertRaises(ValueError):
            evaluate_frames([FRAME], ZONE, REQUIRED, SETTINGS, detector=detector)


if __name__ == "__main__":
    unittest.main()
