"""Test module khuon mat (src/face/): gan mat voi nguoi trong vung, dem mat nhieu nguoi, chon vector, so khop,
kiem tra anh dang ky. Dung du lieu gia (dong YuNet tu tao). Rieng FaceDetectorRealTest dung mo hinh that va video
cong_gia_v1, tu bo qua neu may chua co.
Chay: .venv\\Scripts\\python.exe -m unittest discover -s tests -v"""
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from src.face.analyze import (CO_MAT, KHONG_THAY_MAT, FaceAccumulator, count_faces_in_zone, face_quality,
                              idle_face_present, main_face_index, select_vectors)
from src.face.enroll import check_enroll_face, to_gallery, Sample
from src.face.match import l2_normalize, load_gallery, match, save_gallery, score_workers
from src.zone.zone import zone_to_pixels
from fakes import FRAME_W, FRAME_H, PERSON, PERSON_2, SETTINGS, ZONE

PPE = SETTINGS["ppe"]
ZONE_PX = zone_to_pixels(ZONE, FRAME_W, FRAME_H)  # x 320..960


def face(x, y, w, h=None, score=0.9):
    """1 dong YuNet gia: khung (x, y, w, h), 5 diem moc trong khung, score."""
    h = w if h is None else h
    marks = [x + 0.3 * w, y + 0.4 * h, x + 0.7 * w, y + 0.4 * h, x + 0.5 * w, y + 0.6 * h, x + 0.35 * w, y + 0.8 * h,
             x + 0.65 * w, y + 0.8 * h]
    return [x, y, w, h, *marks, score]


# PERSON = [500, 100, 700, 650]: cao 550 -> vung dau y 45..292.5, x 500..700.
HEAD_FACE = face(570, 120, 60)       # tam (600, 150): trong vung dau
CHEST_FACE = face(570, 300, 60)      # tam (600, 330): ngang nguc (vd gio dien thoai co anh nguoi khac) -> loai
SMALL_FACE = face(585, 135, 30)      # rong 30 < min_face_px 50


class MainFaceTest(unittest.TestCase):
    def test_mat_trong_vung_dau_cua_nguoi_trong_vung(self):
        self.assertEqual(main_face_index([CHEST_FACE, HEAD_FACE], [PERSON], PPE, 50), 1)

    def test_loai_mat_ngoai_vung_dau(self):
        self.assertIsNone(main_face_index([CHEST_FACE], [PERSON], PPE, 50))

    def test_loai_mat_qua_nho(self):
        self.assertIsNone(main_face_index([SMALL_FACE], [PERSON], PPE, 50))

    def test_khong_co_nguoi_trong_vung(self):
        self.assertIsNone(main_face_index([HEAD_FACE], np.zeros((0, 4)), PPE, 50))

    def test_nhieu_nguoi_lay_nguoi_lon_nhat(self):
        # PERSON (200x550) lon hon PERSON_2 (150x530): mat cua PERSON_2 khong duoc chon.
        face_p2 = face(795, 140, 60)
        self.assertEqual(main_face_index([face_p2, HEAD_FACE], [PERSON_2, PERSON], PPE, 50), 1)

    def test_nguoi_cui_xet_ca_khung(self):
        bent = [400, 400, 800, 650]  # cao 250 < rong 400 -> nguoi cui, dau co the o giua canh ben
        self.assertEqual(main_face_index([face(420, 520, 60)], [bent], PPE, 50), 0)


class CountFacesTest(unittest.TestCase):
    def count(self, rows, zone_px=ZONE_PX):
        return count_faces_in_zone(rows, zone_px, FRAME_W, multi_min_px=40, multi_min_ratio=0.7)

    def test_hai_mat_cung_co(self):
        self.assertEqual(self.count([face(570, 120, 60), face(780, 130, 55)]), 2)

    def test_nguoi_xep_hang_xa_khong_tinh(self):
        # Mat 30 px < 0.7 x 60 va < 40 px: nguoi dung xa phia sau (vach cho) khong lam bao nhieu nguoi.
        self.assertEqual(self.count([face(570, 120, 60), face(700, 60, 30)]), 1)

    def test_mat_vua_nho_hon_ti_le(self):
        self.assertEqual(self.count([face(570, 120, 60), face(780, 130, 41)]), 1)  # 41 < 0.7 x 60 = 42

    def test_mat_ngoai_khoang_x_cua_vung(self):
        self.assertEqual(self.count([face(570, 120, 60), face(1000, 130, 60)]), 1)  # tam x 1030 > 960

    def test_khong_co_vung_xet_ca_khung(self):
        self.assertEqual(self.count([face(50, 120, 60), face(1000, 130, 60)], zone_px=None), 2)

    def test_khong_co_mat(self):
        self.assertEqual(self.count([]), 0)

    def test_che_do_cho(self):
        self.assertTrue(idle_face_present([HEAD_FACE], ZONE_PX, FRAME_W, 50))
        self.assertFalse(idle_face_present([SMALL_FACE], ZONE_PX, FRAME_W, 50))
        self.assertFalse(idle_face_present([face(1000, 130, 60)], ZONE_PX, FRAME_W, 50))


class VectorTest(unittest.TestCase):
    def test_diem_chat_luong(self):
        self.assertAlmostEqual(face_quality(0.9, 50, 100), 0.45)
        self.assertAlmostEqual(face_quality(0.9, 150, 100), 0.9)  # rong hon 100 px khong tang them

    def test_chon_vector_chat_luong_cao(self):
        cands = [(q, np.full(128, q)) for q in (0.3, 0.9, 0.5, 0.7, 0.1, 0.8)]
        self.assertEqual([q for q, _ in select_vectors(cands, 3)], [0.9, 0.8, 0.7])

    def test_tong_hop_luot(self):
        acc = FaceAccumulator(max_vectors=2)
        acc.add(1, np.ones(128), 0.5)
        acc.add(2, np.ones(128), 0.9)
        acc.add(2, None, 0.0)   # khung khong co mat nguoi kiem tra nhung dem duoc 2 mat
        acc.add(0, None, 0.0)
        s = acc.summary()
        self.assertEqual((s["so_khung"], s["so_khung_co_mat"], s["so_khung_nhieu_mat"]), (4, 2, 2))
        self.assertEqual((s["ty_le_khung_nhieu_mat"], s["chat_luong"], s["trang_thai"]), (0.5, [0.9, 0.5], CO_MAT))

    def test_khong_thay_mat(self):
        acc = FaceAccumulator(5)
        acc.add(0, None, 0.0)
        self.assertEqual((acc.summary()["trang_thai"], acc.summary()["vectors"]), (KHONG_THAY_MAT, []))


def unit(*idx):
    """Vector don vi gan truc idx (de tinh cosine bang tay)."""
    v = np.zeros(128, np.float32)
    for i, w in idx:
        v[i] = w
    return l2_normalize(v)


A = np.stack([unit((0, 1.0)), unit((0, 1.0), (1, 0.2))])       # mau cua A
B = np.stack([unit((2, 1.0)), unit((2, 1.0), (3, 0.3))])       # mau cua B (vuong goc voi A)


class MatchTest(unittest.TestCase):
    def test_nhan_ra(self):
        m = match(np.stack([unit((0, 1.0))]), {"A": A, "B": B}, threshold=0.4, margin=0.05)
        self.assertEqual((m.ma, m.ma_gan_nhat), ("A", "A"))
        self.assertAlmostEqual(m.diem, 1.0, places=5)
        self.assertAlmostEqual(m.diem_thu_hai, 0.0, places=5)

    def test_duoi_nguong_khong_nhan_ra(self):
        v = unit((0, 0.3), (5, 1.0))  # cosine voi A ~0.29
        m = match(np.stack([v]), {"A": A, "B": B}, threshold=0.4, margin=0.05)
        self.assertIsNone(m.ma)
        self.assertEqual(m.ma_gan_nhat, "A")  # van ghi nguoi gan nhat de xem lai

    def test_hai_nguoi_qua_sat_nhau_khong_nhan_ra(self):
        v = unit((0, 1.0), (2, 0.95))  # giong A va B gan bang nhau -> khoang cach < margin
        m = match(np.stack([v]), {"A": A, "B": B}, threshold=0.4, margin=0.05)
        self.assertIsNone(m.ma)

    def test_chi_mot_cong_nhan_khong_xet_khoang_cach(self):
        self.assertEqual(match(np.stack([unit((0, 1.0))]), {"A": A}, 0.4, 0.05).ma, "A")

    def test_khong_co_mau_hoac_khong_co_vector(self):
        self.assertIsNone(match(np.stack([unit((0, 1.0))]), {}, 0.4, 0.05).ma)
        self.assertIsNone(match(np.zeros((0, 128)), {"A": A}, 0.4, 0.05).ma)

    def test_diem_la_trung_binh_cua_cosine_lon_nhat(self):
        vecs = np.stack([unit((0, 1.0)), unit((0, 1.0), (2, 1.0))])  # cosine lon nhat voi A: 1.0 va ~0.707
        self.assertAlmostEqual(score_workers(vecs, {"A": A})["A"], (1.0 + 2 ** -0.5) / 2, places=2)

    def test_luu_va_doc_file_mau(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mau.npz"
            save_gallery(path, {"A": A, "CN001": B})
            g = load_gallery(path)
        self.assertEqual(sorted(g), ["A", "CN001"])
        np.testing.assert_allclose(g["A"], A)
        self.assertEqual(load_gallery(Path(tmp) / "khong_co.npz"), {})


class EnrollTest(unittest.TestCase):
    def test_kiem_tra_anh_dang_ky(self):
        self.assertEqual(check_enroll_face([face(100, 100, 80, score=0.95)], 0.85, 50), (0, ""))
        self.assertIn("khong thay mat", check_enroll_face([], 0.85, 50)[1])
        self.assertIn("co 2 mat", check_enroll_face([face(0, 0, 80), face(200, 0, 80)], 0.85, 50)[1])
        self.assertIn("diem mat", check_enroll_face([face(100, 100, 80, score=0.8)], 0.85, 50)[1])
        self.assertIn("rong", check_enroll_face([face(100, 100, 40, score=0.95)], 0.85, 50)[1])

    def test_giu_toi_da_max_samples_mau_tot_nhat(self):
        samples = {"A": [Sample(unit((0, 1.0), (1, q)), q, None, "x") for q in (0.2, 0.9, 0.5, 0.7)]}
        self.assertEqual(to_gallery(samples, 2)["A"].shape, (2, 128))


VIDEOS = ROOT / "data" / "raw" / "cong_gia_v1"
try:
    from src.config import load_settings
    _face_cfg = load_settings()["face"]
    HAVE_MODELS = Path(_face_cfg["detector_model"]).exists() and Path(_face_cfg["recognizer_model"]).exists()
except Exception:  # pragma: no cover
    HAVE_MODELS = False


@unittest.skipUnless(HAVE_MODELS and (VIDEOS / "du_do_01.mp4").exists(), "chua co mo hinh khuon mat hoac video cong_gia_v1")
class FaceDetectorRealTest(unittest.TestCase):
    """Mo hinh that tren 2 khung cua video du_do_01 (chi kiem tra so lieu, khong luu anh)."""

    @classmethod
    def setUpClass(cls):
        import cv2
        from src.face.face_detector import face_detector_from_settings
        from src.face.face_embedder import face_embedder_from_settings
        cls.fd, cls.emb = face_detector_from_settings(_face_cfg), face_embedder_from_settings(_face_cfg)
        cap = cv2.VideoCapture(str(VIDEOS / "du_do_01.mp4"))
        cls.frames = []
        for idx in (10, 60):
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            cls.frames.append(cap.read()[1])
        cap.release()

    def test_tim_dung_1_mat(self):
        self.assertEqual(len(self.fd.detect(self.frames[0])), 1)

    def test_thu_nho_van_tra_toa_do_anh_goc(self):
        full = self.fd.detect(self.frames[0]).boxes[0]
        small = self.fd.detect(self.frames[0], long_side=427).boxes[0]  # thu nho 1/2
        np.testing.assert_allclose(small, full, atol=8)

    def test_cung_nguoi_hai_khung_giong_nhau(self):
        vecs = [self.emb.embed(f, self.fd.detect(f).rows[0]) for f in self.frames]
        self.assertAlmostEqual(float(np.linalg.norm(vecs[0])), 1.0, places=4)
        self.assertGreater(float(vecs[0] @ vecs[1]), 0.5)


if __name__ == "__main__":
    unittest.main()
