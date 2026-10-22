"""Test danh gia Giai doan 2: doan dap an tu ten file, file dap an, chi so, lay mau khung, bao cao.
Chi dung du lieu gia (khong can model, khong can video that).
Chay: .venv\\Scripts\\python.exe -m unittest discover -s tests -v"""
import sys
import tempfile
import time
import unittest
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import load_settings
from src.evaluation.answers import Answer, guess_answer, list_videos, merge_answers, read_answers, write_answers
from src.evaluation.metrics import RoundResult, by_condition, confusion_matrix, summarize, violation_scores
from src.evaluation.report import round_columns, to_markdown, write_rounds_csv
from src.evaluation.video import measure_fps, read_sampled_frames, sample_indices, sample_times

EV = load_settings()["evaluation"]
CODES = ["thieu_mu", "thieu_ao"]


def guess(name):
    a = guess_answer(name, EV["answer_prefixes"], EV["condition_prefixes"])
    return a.ket_qua_dung, a.thieu_dung, a.dieu_kien


class GuessAnswerTest(unittest.TestCase):
    """Quy uoc ten file cua nguoi dung (cau hinh evaluation.answer_prefixes)."""

    def test_dat(self):
        for name in ("du_do_01.mp4", "mu_trang_2.mp4", "ao_cam.mov"):
            self.assertEqual(guess(name)[:2], ("DAT", []), name)

    def test_thieu_mu(self):
        for name in ("thieu_mu_01.mp4", "non_la_1.mp4", "mu_luoi_trai_03.MP4"):
            self.assertEqual(guess(name)[:2], ("KHONG_DAT", ["thieu_mu"]), name)

    def test_thieu_ao_va_ca_hai(self):
        self.assertEqual(guess("thieu_ao_1.mp4")[:2], ("KHONG_DAT", ["thieu_ao"]))
        self.assertEqual(guess("thieu_ca_hai_1.mp4")[:2], ("KHONG_DAT", ["thieu_mu", "thieu_ao"]))

    def test_hai_nguoi_va_trong(self):
        self.assertEqual(guess("hai_nguoi_1.mp4")[:2], ("NHIEU_NGUOI", []))
        self.assertEqual(guess("trong_1.mp4")[:2], ("KHONG_CO_NGUOI", []))

    def test_dieu_kien_anh_sang_theo_phan_duoi(self):
        self.assertEqual(guess("nguoc_sang_du_do_01.mp4"), ("DAT", [], "nguoc_sang_du_do"))
        # "thieu_sang_" phai duoc tach truoc, khong bi nham thanh "thieu_..."
        self.assertEqual(guess("thieu_sang_thieu_mu_2.mp4"), ("KHONG_DAT", ["thieu_mu"], "thieu_sang_thieu_mu"))

    def test_dieu_kien_la_ten_bo_so_thu_tu(self):
        self.assertEqual(guess("mu_luoi_trai_01.mp4")[2], "mu_luoi_trai")
        # Bien the nguoi quay dat them van khop tien to, va giu rieng trong cot dieu kien.
        self.assertEqual(guess("hai_nguoi_dungsau_02.mp4"), ("NHIEU_NGUOI", [], "hai_nguoi_dungsau"))
        self.assertEqual(guess("hai_nguoi_canhnhau_01.mp4")[2], "hai_nguoi_canhnhau")
        self.assertEqual(guess("du_do1.mp4")[2], "du_do")

    def test_cach_danh_so_va_chu_hoa(self):
        for name in ("du_do.mp4", "du_do1.mp4", "du_do-1.mp4", "DU_DO_01.mp4"):
            self.assertEqual(guess(name)[0], "DAT", name)

    def test_khong_theo_quy_uoc(self):
        for name in ("video_01.mp4", "du_dox.mp4", "thieu_sang.mp4", "nguoc_sang_abc.mp4", "ao_vang_01.mp4"):
            self.assertEqual(guess(name)[:2], ("", []), name)
        self.assertEqual(guess("ao_vang_01.mp4")[2], "ao_vang")  # van ghi dieu kien de de dien tay


class AnswerFileTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "dap_an.csv"

    def tearDown(self):
        self.tmp.cleanup()

    def test_ghi_roi_doc_lai(self):
        rows = [Answer("du_do_1.mp4", "DAT", [], "du_do"), Answer("thieu_ca_hai_1.mp4", "KHONG_DAT", CODES, "thieu_ca_hai")]
        write_answers(self.path, rows)
        self.assertEqual(read_answers(self.path, CODES), rows)
        self.assertIn("thieu_mu;thieu_ao", self.path.read_text(encoding="utf-8-sig"))

    def test_tao_lai_giu_dong_da_sua_tay(self):
        edited = Answer("du_do_1.mp4", "KHONG_DAT", ["thieu_ao"], "du_do (ao bi che)")  # nguoi dung da sua
        rows, added = merge_answers([edited], [Answer("du_do_1.mp4", "DAT"), Answer("trong_1.mp4", "KHONG_CO_NGUOI")])
        self.assertEqual(rows[0], edited)
        self.assertEqual([a.ten_file for a in added], ["trong_1.mp4"])

    def test_dong_con_trong_duoc_dien_khi_co_quy_uoc_moi(self):
        blank = Answer("ao_xanh_01.mp4", "", [], "ao_xanh")
        edited = Answer("du_do_1.mp4", "KHONG_DAT", ["thieu_ao"], "du_do")
        rows, changed = merge_answers([blank, edited], [Answer("ao_xanh_01.mp4", "DAT", [], "ao_xanh"),
                                                        Answer("du_do_1.mp4", "DAT", [], "du_do")])
        self.assertEqual(rows, [Answer("ao_xanh_01.mp4", "DAT", [], "ao_xanh"), edited])  # dong da sua van giu
        self.assertEqual([a.ten_file for a in changed], ["ao_xanh_01.mp4"])

    def test_dong_trong_va_van_chua_doan_duoc_giu_nguyen(self):
        blank = Answer("la.mp4", "", [], "la")
        self.assertEqual(merge_answers([blank], [Answer("la.mp4", "", [], "la")]), ([blank], []))

    def test_quy_uoc_ao_xanh_va_mu_bao_hiem(self):
        self.assertEqual(guess("ao_xanh_01.mp4"), ("DAT", [], "ao_xanh"))
        self.assertEqual(guess("mubaohiem_02.mp4"), ("KHONG_DAT", ["thieu_mu"], "mubaohiem"))

    def test_gia_tri_sai_bao_loi_ro_dong(self):
        self.path.write_text("ten_file,ket_qua_dung,thieu_dung,dieu_kien\n"
                             "a.mp4,DATT,,x\nb.mp4,KHONG_DAT,,x\nc.mp4,DAT,thieu_mu,x\nd.mp4,KHONG_DAT,thieu_gang,x\n",
                             encoding="utf-8")
        with self.assertRaises(ValueError) as ctx:
            read_answers(self.path, CODES)
        msg = str(ctx.exception)
        for line in ("dong 2", "dong 3", "dong 4", "dong 5"):
            self.assertIn(line, msg)

    def test_khong_strict_van_doc(self):
        self.path.write_text("ten_file,ket_qua_dung,thieu_dung,dieu_kien\nx.mp4,,,?\n", encoding="utf-8")
        self.assertEqual(read_answers(self.path, CODES, strict=False), [Answer("x.mp4", "", [], "?")])

    def test_thieu_cot(self):
        self.path.write_text("ten_file,ket_qua\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "thieu cot"):
            read_answers(self.path)

    def test_file_chua_co(self):
        self.assertEqual(read_answers(self.path), [])

    def test_liet_ke_video(self):
        for name in ("b.mp4", "a.MOV", "ghi_chu.txt", "dap_an.csv"):
            (Path(self.tmp.name) / name).write_bytes(b"")
        self.assertEqual(list_videos(self.tmp.name, EV["video_exts"]), ["a.MOV", "b.mp4"])


def R(name, truth, pred, thieu_dung=(), thieu=(), ms=1500.0):
    cond = guess(name)[2]
    return RoundResult(name, cond, truth, list(thieu_dung), pred, list(thieu), ms)


# 10 luot gia, dap an tinh tay (xem tung dong):
ROWS = [
    R("du_do_1.mp4", "DAT", "DAT", ms=1500),                                                   # dung, TN
    R("du_do_2.mp4", "DAT", "KHONG_DAT", thieu=["thieu_mu"], ms=1510),                          # FP (chan nham)
    R("mu_trang_1.mp4", "DAT", "KHONG_XAC_DINH", ms=1520),                                     # sai, TN
    R("thieu_mu_1.mp4", "KHONG_DAT", "KHONG_DAT", ["thieu_mu"], ["thieu_mu"], ms=1530),         # dung, TP
    R("thieu_mu_2.mp4", "KHONG_DAT", "DAT", ["thieu_mu"], ms=1540),                             # FN, bo lot
    R("thieu_ca_hai_1.mp4", "KHONG_DAT", "KHONG_DAT", CODES, ["thieu_mu"], ms=1550),            # TP nhung sai danh sach
    R("thieu_ao_1.mp4", "KHONG_DAT", "KHONG_XAC_DINH", ["thieu_ao"], ms=1560),                  # FN, moi quet lai
    R("hai_nguoi_1.mp4", "NHIEU_NGUOI", "NHIEU_NGUOI", ms=1570),                               # dung
    R("trong_1.mp4", "KHONG_CO_NGUOI", "KHONG_CO_NGUOI", ms=1580),                             # dung
    R("hai_nguoi_2.mp4", "NHIEU_NGUOI", "DAT", ms=1590),                                       # sai
]


class MetricsTest(unittest.TestCase):
    def test_dung_can_trung_ca_danh_sach_thieu(self):
        self.assertEqual([r.dung for r in ROWS], [True, False, False, True, False, False, False, True, True, False])

    def test_tong_hop(self):
        s = summarize(ROWS)
        self.assertEqual((s["so_luot"], s["so_dung"], s["so_khong_xac_dinh"]), (10, 4, 2))
        self.assertAlmostEqual(s["ty_le_dung"], 0.4)
        self.assertAlmostEqual(s["ty_le_khong_xac_dinh"], 0.2)
        self.assertAlmostEqual(s["ty_le_dung_khi_ket_luan"], 4 / 8)
        self.assertAlmostEqual(s["thoi_gian_tb_ms"], 1545.0)

    def test_vi_pham(self):
        v = violation_scores(ROWS)
        self.assertEqual((v["so_luot_xet"], v["tp"], v["fp"], v["fn"], v["tn"]), (7, 2, 1, 2, 2))
        self.assertAlmostEqual(v["precision"], 2 / 3)
        self.assertAlmostEqual(v["recall"], 2 / 4)
        self.assertEqual((v["bo_lot"], v["vi_pham_khong_xac_dinh"], v["sai_danh_sach_thieu"]), (1, 1, 1))

    def test_mau_so_bang_0_tra_none(self):
        v = violation_scores([R("hai_nguoi_1.mp4", "NHIEU_NGUOI", "NHIEU_NGUOI")])
        self.assertEqual((v["precision"], v["recall"]), (None, None))
        self.assertIsNone(summarize([])["ty_le_dung"])

    def test_ma_tran_nham_lan(self):
        m = confusion_matrix(ROWS)
        self.assertNotIn("KHONG_XAC_DINH", m)  # dap an khong bao gio la KHONG_XAC_DINH
        self.assertEqual(m["DAT"], {"DAT": 1, "KHONG_DAT": 1, "KHONG_XAC_DINH": 1, "NHIEU_NGUOI": 0, "KHONG_CO_NGUOI": 0})
        self.assertEqual(m["KHONG_DAT"]["KHONG_DAT"], 2)
        self.assertEqual(m["KHONG_DAT"]["DAT"], 1)
        self.assertEqual(m["NHIEU_NGUOI"]["DAT"], 1)
        self.assertEqual(sum(sum(r.values()) for r in m.values()), 10)

    def test_theo_dieu_kien(self):
        table = {c["dieu_kien"]: c for c in by_condition(ROWS)}
        self.assertEqual(sorted(table), ["du_do", "hai_nguoi", "mu_trang", "thieu_ao", "thieu_ca_hai", "thieu_mu", "trong"])
        self.assertEqual((table["du_do"]["so_luot"], table["du_do"]["dung"], table["du_do"]["sai"]), (2, 1, 1))
        self.assertEqual(table["thieu_ao"]["khong_xac_dinh"], 1)
        self.assertEqual(table["hai_nguoi"]["ket_qua"], {"NHIEU_NGUOI": 1, "DAT": 1})


class SamplingTest(unittest.TestCase):
    def test_so_khung_giong_check_that(self):
        # May xu ly 85 ms/khung (~11.8 khung/s), timeout 1.5 s -> 18 khung (chay that do duoc 17-19).
        self.assertEqual(len(sample_times(1000 / 85, 1.5)), 18)
        self.assertEqual(len(sample_times(10, 1.5)), 15)  # 1.5 * 10 vua tron, khong them khung thu 16

    def test_chi_so_khung_video(self):
        # Video 30 FPS, may 10 khung/s: khung 0, 3, 6, ... (khung moi nhat tai moi thoi diem).
        self.assertEqual(sample_indices(10, 1.0, 30), [0, 3, 6, 9, 12, 15, 18, 21, 24, 27])

    def test_may_nhanh_hon_camera_khong_lap_khung(self):
        # May 50 khung/s nhung video 10 FPS: check() phai cho khung moi -> chi 10 khung khac nhau.
        self.assertEqual(sample_indices(50, 1.0, 10), list(range(10)))

    def test_tham_so_sai(self):
        with self.assertRaises(ValueError):
            sample_times(0, 1.5)
        with self.assertRaises(ValueError):
            sample_indices(10, 1.5, 0)


def write_video(path, n_frames, fps=30, w=64, h=48):
    """Video gia: khung i co mau xam = 4 * i (doc lai gan dung)."""
    out = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), fps, (w, h))
    for i in range(n_frames):
        out.write(np.full((h, w, 3), 4 * i, np.uint8))
    out.release()


class ReadSampledFramesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_lay_dung_khung(self):
        path = Path(self.tmp.name) / "v.avi"
        write_video(path, 60)
        frames, info = read_sampled_frames(path, sample_fps=10, timeout=1.0)
        self.assertEqual(info["chi_so_khung"], [0, 3, 6, 9, 12, 15, 18, 21, 24, 27])
        self.assertEqual([round(f.mean() / 4) for f in frames], info["chi_so_khung"])  # dung noi dung khung
        self.assertEqual((info["video_fps"], info["khung_hinh"], info["video_ngan_hon_timeout"]), (30.0, [64, 48], False))

    def test_xoay_hinh(self):
        path = Path(self.tmp.name) / "v.avi"
        write_video(path, 30)
        frames, info = read_sampled_frames(path, 10, 0.5, rotate=90)
        self.assertEqual(frames[0].shape, (64, 48, 3))
        self.assertEqual(info["khung_hinh"], [48, 64])

    def test_video_ngan_hon_timeout(self):
        path = Path(self.tmp.name) / "ngan.avi"
        write_video(path, 20)  # 0.67 s
        frames, info = read_sampled_frames(path, 10, 1.5)
        self.assertEqual(info["chi_so_khung"], [0, 3, 6, 9, 12, 15, 18])
        self.assertTrue(info["video_ngan_hon_timeout"])

    def test_khong_mo_duoc(self):
        with self.assertRaises(IOError):
            read_sampled_frames(Path(self.tmp.name) / "khong_co.mp4", 10, 1.5)


class MeasureFpsTest(unittest.TestCase):
    def test_do_toc_do(self):
        fps = measure_fps(lambda f: time.sleep(0.02), None, n=5)  # 20 ms/khung -> ~50 khung/s
        self.assertTrue(30 < fps <= 50, fps)


class ReportTest(unittest.TestCase):
    def test_markdown_co_cac_muc_chinh(self):
        wrong = [{"ten_file": "du_do_2.mp4", "dieu_kien": "du_do", "dap_an": "DAT", "ket_qua": "KHONG_DAT thieu_mu",
                  "dem_khung": "hop_le 18", "anh": "sai/du_do_2.jpg"}]
        md = to_markdown(ROWS, {"imgsz": 640}, wrong)
        for text in ("- **imgsz:** 640", "| Tỷ lệ đúng | 4/10 (40.0%) |", "| Precision (báo vi phạm thì đúng là vi phạm) | 66.7% |",
                     "| Recall (vi phạm bị phát hiện) | 50.0% |", "| Bỏ lọt: vi phạm nhưng ra DAT | 1 |",
                     "| DAT | 1 | 1 | 1 | 0 | 0 |", "| du_do | 2 | 1 | 1 | 0 | 50.0% |", "du_do_2.mp4"):
            self.assertIn(text, md)

    def test_csv_tung_luot(self):
        cols = round_columns(["hardhat", "vest"])
        self.assertIn("ty_le_hardhat", cols)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "kq.csv"
            write_rounds_csv(path, [{"ten_file": "a.mp4", "ket_qua": "DAT", "ty_le_hardhat": 1.0}], cols)
            lines = path.read_text(encoding="utf-8-sig").splitlines()
        self.assertEqual(lines[0].split(","), cols)
        self.assertTrue(lines[1].startswith("a.mp4,"))


if __name__ == "__main__":
    unittest.main()
