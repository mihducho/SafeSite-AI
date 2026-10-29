"""Test nghiep vu cua ung dung web (app/services/): xu ly 1 luot, vao/ra, ghi cong, chong trung, ca lam, cham cong thu cong,
dang ky khuon mat (dong y, so mau), nghi viec. CSDL SQLite trong bo nho + LuotKiemTra gia, khong can camera/mo hinh.
Danh sach bat buoc: DE_TAI.md muc 12, F2.
Chay: .venv\\Scripts\\python.exe -m unittest discover -s tests -v"""
import sys
import tempfile
import unittest
from datetime import date, time, timezone
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app_helpers import (SETTINGS, TZ, add_admin, add_shift, add_worker, fake_face_models, luot, make_db, nhan_dien,
                         sample_image, vn)
from sqlalchemy import func, select

from app.models import NGHI_VIEC, Attendance, FaceSample, PpeCheck
from app.services import bao_cao, cong_nhan
from app.services.cham_cong import (BINH_THUONG, BO_QUA_TRUNG, CHAM_THU_CONG, GHI_RA, GHI_VAO, KHONG_GHI, NGOAI_CA, RA,
                                    VAO, ChamCongError, cham_thu_cong, ngay_cong, thieu_gio_ra, tinh_cong)
from app.services.dang_ky_mat import CAMERA, DangKyMat, DangKyMatError
from app.services.luot import DA_NHAN_RA, DO, KHONG_NHAN_RA, KHONG_THAY_MAT, VANG, XANH, xu_ly_luot
from src.checkpoint.evaluate import DAT, KHONG_CO_NGUOI, KHONG_DAT, KHONG_XAC_DINH, NHIEU_NGUOI

ATT = SETTINGS["attendance"]


class ServiceCase(unittest.TestCase):
    """CSDL moi cho moi test: 1 admin, 1 ca 07:00-17:00, 2 cong nhan co mau (An = mat so 0, Binh = mat so 1)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.db = make_db()
        self.s = self.db.session()
        self.admin = add_admin(self.s)
        self.shift = add_shift(self.s)
        self.an = add_worker(self.s, "CN001", "Nguyễn Văn An", face_index=0)
        self.binh = add_worker(self.s, "CN002", "Trần Thị Bình", face_index=1)
        self.nd = nhan_dien()
        self.dk = DangKyMat(SETTINGS, self.dir / "anh_mau_mat", self.nd, fake_face_models)

    def tearDown(self):
        self.s.close()
        self.db.engine.dispose()
        self.tmp.cleanup()

    def run_luot(self, t, ket_qua=DAT, thieu=(), face_index=0, ly_do=None) -> dict:
        return xu_ly_luot(self.s, luot(t, ket_qua, thieu, face_index, ly_do), settings=SETTINGS, nhan_dien=self.nd,
                          image_dir=self.dir / "anh_luot")

    def att(self, worker, day=29) -> Attendance | None:
        self.s.expire_all()
        return self.s.scalar(select(Attendance).where(Attendance.worker_id == worker.id,
                                                      Attendance.work_date == date(2026, 10, day)))

    def check(self, event) -> PpeCheck:
        return self.s.get(PpeCheck, event["id"])


class VaoRaTest(ServiceCase):
    def test_vao_dat_ghi_gio_vao(self):
        ev = self.run_luot(vn(29, 7, 2))
        self.assertEqual((ev["hanh_dong"], ev["huong"], ev["mau"]), (GHI_VAO, VAO, XANH))
        self.assertEqual(ev["thong_bao"], "Xin chào Nguyễn Văn An. Đã ghi giờ vào 07:02")
        a = self.att(self.an)
        self.assertEqual((a.check_in, a.check_out, a.status), (vn(29, 7, 2), None, BINH_THUONG))
        self.assertEqual(a.ppe_check_id, ev["id"])
        c = self.check(ev)
        self.assertEqual((c.worker_id, c.face_status, c.direction, c.action), (self.an.id, DA_NHAN_RA, VAO, GHI_VAO))
        self.assertTrue((self.dir / "anh_luot" / c.image_path).is_file())
        self.assertTrue(c.image_path.startswith("2026-10-29/"))  # thu muc anh theo ngay Viet Nam
        self.assertEqual(ev["anh"], f"/api/luot/{c.id}/anh")

    def test_vao_khong_dat_khong_ghi(self):
        ev = self.run_luot(vn(29, 7, 0), KHONG_DAT, ["thieu_mu"])
        self.assertEqual((ev["hanh_dong"], ev["huong"], ev["mau"]), (KHONG_GHI, VAO, DO))
        self.assertEqual(ev["thong_bao"], "Nguyễn Văn An: thiếu mũ bảo hộ. Chưa ghi công")
        self.assertIsNone(self.att(self.an))
        self.assertEqual(self.check(ev).action, KHONG_GHI)

    def test_khong_dat_roi_dat_gio_vao_la_luot_dat(self):
        self.run_luot(vn(29, 6, 58), KHONG_DAT, ["thieu_mu", "thieu_ao"])
        ev = self.run_luot(vn(29, 7, 3))
        self.assertEqual(ev["hanh_dong"], GHI_VAO)
        self.assertEqual(self.att(self.an).check_in, vn(29, 7, 3))

    def test_ra_ghi_gio_ra_khong_can_bao_ho(self):
        self.run_luot(vn(29, 7, 0))
        ev = self.run_luot(vn(29, 17, 5), KHONG_DAT, ["thieu_mu"])  # ra ve da thao mu: van ghi gio ra
        self.assertEqual((ev["hanh_dong"], ev["huong"], ev["mau"]), (GHI_RA, RA, XANH))
        self.assertEqual(ev["thong_bao"], "Tạm biệt Nguyễn Văn An. Đã ghi giờ ra 17:05")
        a = self.att(self.an)
        self.assertEqual((a.check_in, a.check_out), (vn(29, 7, 0), vn(29, 17, 5)))
        self.assertEqual((a.worked_minutes, a.early_leave_minutes, a.late_minutes), (540, 0, 0))  # 10 gio - 60 nghi

    def test_ra_trong_2_phut_sau_khi_vao_bi_bo_qua(self):
        self.run_luot(vn(29, 7, 0))
        ev = self.run_luot(vn(29, 7, 1, 30))
        self.assertEqual((ev["hanh_dong"], ev["huong"], ev["mau"]), (BO_QUA_TRUNG, RA, XANH))
        self.assertEqual(ev["thong_bao"], "Nguyễn Văn An: đã ghi giờ vào 07:00, không ghi lặp")
        self.assertIsNone(self.att(self.an).check_out)
        self.assertEqual(self.check(ev).action, BO_QUA_TRUNG)
        self.assertEqual(self.run_luot(vn(29, 7, 2))["hanh_dong"], GHI_RA)  # du 2 phut: ghi gio ra

    def test_vao_lai_sau_khi_ra_giu_gio_vao_dau_cap_nhat_gio_ra(self):
        self.run_luot(vn(29, 7, 0))
        self.run_luot(vn(29, 11, 30))                                        # ra an trua
        ev = self.run_luot(vn(29, 12, 55), KHONG_DAT, ["thieu_mu"])          # vao lai phai kiem tra bao ho
        self.assertEqual((ev["huong"], ev["hanh_dong"]), (VAO, KHONG_GHI))
        self.assertEqual(self.att(self.an).check_out, vn(29, 11, 30))
        ev = self.run_luot(vn(29, 13, 0))
        self.assertEqual((ev["hanh_dong"], ev["thong_bao"]), (GHI_VAO, "Xin chào Nguyễn Văn An. Đã ghi vào lại 13:00"))
        a = self.att(self.an)
        self.assertEqual((a.check_in, a.check_out), (vn(29, 7, 0), None))   # giu gio vao dau, dang co mat
        self.assertEqual(self.run_luot(vn(29, 13, 1))["hanh_dong"], BO_QUA_TRUNG)  # tinh tu lan vao gan nhat (13:00)
        self.assertEqual(self.run_luot(vn(29, 17, 10))["hanh_dong"], GHI_RA)
        a = self.att(self.an)
        self.assertEqual((a.check_in, a.check_out, a.worked_minutes), (vn(29, 7, 0), vn(29, 17, 10), 540))

    def test_di_muon_trong_va_ngoai_an_han(self):
        self.run_luot(vn(29, 7, 5), face_index=0)    # muon 5 phut = an han -> khong tinh
        self.run_luot(vn(29, 7, 20), face_index=1)   # muon 20 phut -> tinh 20
        self.assertEqual(self.att(self.an).late_minutes, 0)
        self.assertEqual(self.att(self.binh).late_minutes, 20)

    def test_ngoai_ca(self):
        self.run_luot(vn(29, 5, 30), face_index=0)   # truoc 06:00 (bat dau - 60 phut)
        self.run_luot(vn(29, 6, 0), face_index=1)    # dung 06:00: trong khung
        self.assertEqual((self.att(self.an).status, self.att(self.an).check_in), (NGOAI_CA, vn(29, 5, 30)))
        self.assertEqual(self.att(self.binh).status, BINH_THUONG)
        self.run_luot(vn(30, 18, 0), face_index=1)   # ngay hom sau, sau gio ket thuc ca
        self.assertEqual(self.att(self.binh, day=30).status, NGOAI_CA)

    def test_ngay_cong_tinh_theo_gio_viet_nam(self):
        t = vn(29, 6, 30).astimezone(timezone.utc)   # 23:30 UTC ngay 28
        self.assertEqual(t.day, 28)
        self.run_luot(t)
        self.assertEqual(self.att(self.an, day=29).check_in, vn(29, 6, 30))
        self.assertEqual(ngay_cong(t, TZ), date(2026, 10, 29))


class KhongGhiCongTest(ServiceCase):
    def test_nguoi_la_khong_ghi(self):
        ev = self.run_luot(vn(29, 7, 0), DAT, face_index=50)  # mat khong giong ai
        self.assertEqual((ev["trang_thai_mat"], ev["hanh_dong"], ev["cong_nhan"], ev["mau"]),
                         (KHONG_NHAN_RA, KHONG_GHI, None, VANG))
        self.assertEqual(ev["thong_bao"], "Chưa nhận diện được, mời nhìn thẳng camera")
        c = self.check(ev)
        self.assertIsNone(c.worker_id)
        self.assertLess(c.face_score, 0.4)
        self.assertIn(c.detail["nhan_dien"]["gan_nhat_ma"], ("CN001", "CN002"))  # luu nguoi giong nhat de xem lai
        self.assertEqual(self.s.scalar(select(func.count(Attendance.id))), 0)

    def test_khong_thay_mat(self):
        ev = self.run_luot(vn(29, 7, 0), DAT, face_index=None)
        self.assertEqual((ev["trang_thai_mat"], ev["hanh_dong"], ev["mau"]), (KHONG_THAY_MAT, KHONG_GHI, VANG))
        self.assertIsNone(self.check(ev).face_score)

    def test_nhieu_nguoi_khong_ghi_du_khop_mat(self):
        ev = self.run_luot(vn(29, 7, 0), NHIEU_NGUOI, face_index=0)
        self.assertEqual(ev["cong_nhan"]["ma"], "CN001")  # mat van khop
        self.assertEqual((ev["hanh_dong"], ev["huong"], ev["mau"], ev["thong_bao"]),
                         (KHONG_GHI, None, VANG, "Mời từng người một"))
        self.assertIsNone(self.att(self.an))
        self.run_luot(vn(29, 7, 5))                                   # vao that
        self.run_luot(vn(29, 17, 0), NHIEU_NGUOI, face_index=0)       # luot ra co 2 nguoi: cung khong ghi
        self.assertIsNone(self.att(self.an).check_out)

    def test_hai_cong_nhan_giong_nhau_qua_khong_nhan_ra(self):
        add_worker(self.s, "CN003", "Lê Văn Cường", face_index=0)  # mau giong het An -> chenh lech < 0.05
        self.nd.xoa_bo_nho_dem()
        self.assertEqual(self.run_luot(vn(29, 7, 0))["trang_thai_mat"], KHONG_NHAN_RA)

    def test_cong_nhan_chua_du_3_mau_khong_duoc_so_khop(self):
        add_worker(self.s, "CN004", "Phạm Thị Dung", face_index=7, n_samples=2)
        self.assertEqual(self.run_luot(vn(29, 7, 0), face_index=7)["trang_thai_mat"], KHONG_NHAN_RA)


class ThongBaoTest(ServiceCase):
    def test_mau_va_cau_thong_bao_tung_truong_hop(self):
        # (luot truoc do cua An, luot can xet) -> (mau, cau thong bao)
        cases = [
            ([], (DAT, [], 0), XANH, "Xin chào Nguyễn Văn An. Đã ghi giờ vào 08:00"),
            ([], (KHONG_DAT, ["thieu_mu", "thieu_ao"], 0), DO,
             "Nguyễn Văn An: thiếu mũ bảo hộ, thiếu áo phản quang. Chưa ghi công"),
            ([], (KHONG_DAT, ["thieu_ao"], 0), DO, "Nguyễn Văn An: thiếu áo phản quang. Chưa ghi công"),
            ([], (KHONG_XAC_DINH, [], 0), VANG, "Nguyễn Văn An: mời đứng yên để kiểm tra lại"),
            ([], (NHIEU_NGUOI, [], 0), VANG, "Mời từng người một"),
            ([], (KHONG_CO_NGUOI, [], 0), VANG, "Mời đứng vào vị trí, nhìn vào camera"),
            ([], (DAT, [], 50), VANG, "Chưa nhận diện được, mời nhìn thẳng camera"),
            ([], (DAT, [], None), VANG, "Chưa nhận diện được, mời nhìn thẳng camera"),
            ([vn(29, 7, 59)], (DAT, [], 0), XANH, "Nguyễn Văn An: đã ghi giờ vào 07:59, không ghi lặp"),
            ([vn(29, 7, 0)], (KHONG_XAC_DINH, [], 0), XANH, "Tạm biệt Nguyễn Văn An. Đã ghi giờ ra 08:00"),
        ]
        for before, (kq, thieu, fi), color, text in cases:
            with self.subTest(ket_qua=kq, thieu=thieu, mat=fi, truoc=before):
                self.s.execute(Attendance.__table__.delete())
                self.s.execute(PpeCheck.__table__.delete())
                self.s.commit()
                for t in before:
                    self.run_luot(t)
                ev = self.run_luot(vn(29, 8, 0), kq, thieu, fi)
                self.assertEqual((ev["mau"], ev["thong_bao"]), (color, text))
                self.assertEqual(ev["ghi_cong"], ev["hanh_dong"] in (GHI_VAO, GHI_RA))

    def test_su_kien_va_lich_su_khong_chua_vector(self):
        ev = self.run_luot(vn(29, 7, 0))
        c = self.check(ev)
        self.assertNotIn("vectors", str(ev))
        self.assertNotIn("vectors", str(c.detail))
        self.assertEqual(c.detail["so_khung"], 10)


class DangKyMatTest(ServiceCase):
    def test_chua_dong_y_khong_them_duoc_mau(self):
        w = add_worker(self.s, "CN010", "Võ Văn Em", consent=False)
        with self.assertRaises(DangKyMatError) as cm:
            self.dk.them_mau(self.s, w, sample_image(10), CAMERA)
        self.assertIn("đồng ý", str(cm.exception))
        self.assertEqual(self.dk.so_mau(self.s, w), 0)
        self.assertFalse((self.dir / "anh_mau_mat" / str(w.id)).exists())

    def test_ghi_nhan_dong_y_roi_them_mau_thi_nhan_ra_duoc(self):
        w = add_worker(self.s, "CN010", "Võ Văn Em", consent=False)
        self.dk.ghi_nhan_dong_y(self.s, w, self.admin)
        self.assertEqual(w.consent_by, self.admin.id)
        self.assertIsNotNone(w.consent_at)
        self.assertEqual(self.run_luot(vn(29, 7, 0), face_index=10)["trang_thai_mat"], KHONG_NHAN_RA)  # chua co mau
        samples = [self.dk.them_mau(self.s, w, sample_image(10), CAMERA) for _ in range(3)]
        thumb = cv2.imread(str(self.dk.thumb_file(samples[0])))
        self.assertEqual(thumb.shape[:2], (112, 112))  # chi luu anh mat 112x112, khong luu anh goc
        self.assertEqual(len(samples[0].embedding), 512)
        ev = self.run_luot(vn(29, 7, 5), face_index=10)  # bo nho dem da duoc xoa khi them mau
        self.assertEqual((ev["trang_thai_mat"], ev["cong_nhan"]["ma"]), (DA_NHAN_RA, "CN010"))

    def test_anh_khong_dat(self):
        w = add_worker(self.s, "CN010", "Võ Văn Em")
        for n, msg in ((0, "Không thấy khuôn mặt"), (2, "Ảnh có 2 khuôn mặt")):
            with self.subTest(so_mat=n), self.assertRaises(DangKyMatError) as cm:
                self.dk.them_mau(self.s, w, sample_image(10, n_faces=n), CAMERA)
            self.assertIn(msg, str(cm.exception))
        self.assertEqual(self.dk.so_mau(self.s, w), 0)

    def test_toi_da_10_mau(self):
        w = add_worker(self.s, "CN010", "Võ Văn Em")
        for _ in range(10):
            self.dk.them_mau(self.s, w, sample_image(10), CAMERA)
        with self.assertRaises(DangKyMatError) as cm:
            self.dk.them_mau(self.s, w, sample_image(10), CAMERA)
        self.assertIn("10 mẫu", str(cm.exception))

    def test_xoa_mot_mau_va_xoa_tat_ca(self):
        w = add_worker(self.s, "CN010", "Võ Văn Em")
        samples = [self.dk.them_mau(self.s, w, sample_image(10), CAMERA) for _ in range(4)]
        self.dk.xoa_mau(self.s, samples[0])
        self.assertFalse(self.dk.thumb_file(samples[0]).exists())
        self.assertEqual(self.dk.so_mau(self.s, w), 3)
        self.assertEqual(self.run_luot(vn(29, 7, 0), face_index=10)["trang_thai_mat"], DA_NHAN_RA)
        self.assertEqual(self.dk.xoa_tat_ca(self.s, w), 3)
        self.assertFalse((self.dir / "anh_mau_mat" / str(w.id)).exists())
        self.assertEqual(self.run_luot(vn(29, 7, 5), face_index=10)["trang_thai_mat"], KHONG_NHAN_RA)

    def test_nghi_viec_khong_nhan_dien_va_xoa_mau(self):
        w = add_worker(self.s, "CN010", "Võ Văn Em")
        for _ in range(3):
            self.dk.them_mau(self.s, w, sample_image(10), CAMERA)
        self.assertEqual(self.run_luot(vn(29, 7, 0), face_index=10)["hanh_dong"], GHI_VAO)  # bo nho dem da co Em
        self.assertEqual(cong_nhan.cho_nghi_viec(self.s, w, self.dk), 3)
        self.assertEqual(w.status, NGHI_VIEC)
        self.assertEqual(self.s.scalar(select(func.count(FaceSample.id)).where(FaceSample.worker_id == w.id)), 0)
        self.assertFalse((self.dir / "anh_mau_mat" / str(w.id)).exists())
        ev = self.run_luot(vn(29, 17, 0), face_index=10)
        self.assertEqual((ev["trang_thai_mat"], ev["hanh_dong"]), (KHONG_NHAN_RA, KHONG_GHI))
        with self.assertRaises(DangKyMatError):  # da nghi: khong dang ky lai duoc
            self.dk.them_mau(self.s, w, sample_image(10), CAMERA)
        cong_nhan.di_lam_lai(self.s, w, self.dk)   # nhan lai: phai dong y lai tu dau
        self.assertIsNone(w.consent_at)


class ChamThuCongTest(ServiceCase):
    def manual(self, gio_vao=None, gio_ra=None, ly_do="Camera hong, can bo xac nhan", day=29, worker=None):
        return cham_thu_cong(self.s, worker or self.an, date(2026, 10, day), gio_vao, gio_ra, ly_do, self.admin, ATT,
                             now=vn(29, 18, 0))

    def test_thieu_ly_do_bi_tu_choi(self):
        for ly_do in ("", "   ", None):
            with self.subTest(ly_do=ly_do), self.assertRaises(ChamCongError) as cm:
                self.manual(time(7, 0), time(17, 0), ly_do=ly_do)
            self.assertIn("lý do", str(cm.exception))
        self.assertIsNone(self.att(self.an))

    def test_them_gio_vao_ra(self):
        a = self.manual(time(7, 0), time(17, 0))
        self.assertEqual((a.check_in, a.check_out, a.status, a.updated_by), (vn(29, 7, 0), vn(29, 17, 0), CHAM_THU_CONG,
                                                                             self.admin.id))
        self.assertEqual(a.worked_minutes, 540)
        self.assertIn("Camera hong", a.note)

    def test_sua_gio_ra_giu_gio_vao_tu_dong(self):
        self.run_luot(vn(29, 7, 2))
        a = self.manual(gio_ra=time(16, 30))
        self.assertEqual((a.check_in, a.check_out, a.early_leave_minutes, a.status),
                         (vn(29, 7, 2), vn(29, 16, 30), 30, CHAM_THU_CONG))

    def test_du_lieu_sai_bi_tu_choi(self):
        with self.assertRaises(ChamCongError):
            self.manual(gio_ra=time(17, 0))                 # chua co gio vao
        with self.assertRaises(ChamCongError):
            self.manual(time(9, 0), time(8, 0))             # ra truoc vao
        with self.assertRaises(ChamCongError):
            self.manual(time(7, 0), day=30)                 # ngay mai
        self.assertIsNone(self.att(self.an))

    def test_cham_vao_thu_cong_roi_dung_truoc_camera_khong_ghi_ra_ngay(self):
        self.manual(time(7, 0))
        self.assertEqual(self.run_luot(vn(29, 7, 1))["hanh_dong"], BO_QUA_TRUNG)  # cach gio vao < 2 phut


class GioNghiTest(ServiceCase):
    """So phut lam chi tru phan giao nhau voi gio nghi trua 11:30-12:30 (ca 07:00-17:00)."""

    def worked(self, vao, ra) -> int:
        a = Attendance(worker_id=self.an.id, work_date=date(2026, 10, 29), shift_id=self.shift.id,
                       check_in=vn(29, *vao), check_out=vn(29, *ra))
        tinh_cong(a, self.shift, TZ)
        return a.worked_minutes

    def test_lam_ca_ngay_tru_nghi_trua(self):
        self.assertEqual(self.worked((7, 0), (17, 0)), 540)    # 600 - 60
        self.assertEqual(self.worked((6, 30), (17, 30)), 540)  # ngoai gio ca khong tinh

    def test_vao_ra_trong_buoi_sang_khong_tru(self):
        self.assertEqual(self.worked((7, 0), (11, 0)), 240)
        self.assertEqual(self.worked((8, 0), (11, 30)), 210)   # ra dung luc bat dau nghi

    def test_buoi_chieu_khong_tru_va_giao_mot_phan(self):
        self.assertEqual(self.worked((13, 0), (17, 0)), 240)
        self.assertEqual(self.worked((7, 0), (12, 0)), 270)    # 300 - 30 phut nghi (11:30-12:00)
        self.assertEqual(self.worked((12, 12), (12, 15)), 0)   # vao, ra trong gio nghi

    def test_luot_vao_ra_ghi_so_phut_lam_theo_gio_nghi(self):
        self.run_luot(vn(29, 8, 0))
        self.run_luot(vn(29, 11, 0))
        self.assertEqual(self.att(self.an).worked_minutes, 180)  # sang 3 gio, khong tru nghi


class BaoCaoTest(ServiceCase):
    def test_bang_cong_ngay_va_tong_quan(self):
        self.run_luot(vn(29, 7, 2), face_index=0)
        self.run_luot(vn(29, 7, 10), KHONG_DAT, ["thieu_mu"], face_index=1)
        rows = {r["ma"]: r for r in bao_cao.bang_cong_ngay(self.s, date(2026, 10, 29), ATT, vn(29, 22, 0))}
        self.assertEqual(set(rows), {"CN001", "CN002"})  # ca nguoi chua vao
        self.assertEqual((rows["CN001"]["gio_vao"], rows["CN001"]["gio_ra"], rows["CN001"]["thieu_gio_ra"]),
                         ("07:02", None, True))  # 22:00 > 17:00 + 4 gio
        self.assertEqual(rows["CN002"]["trang_thai"], "chua_vao")
        tq = bao_cao.tong_quan(self.s, ATT, vn(29, 12, 0))
        self.assertEqual({k: tq[k] for k in ("so_cong_nhan", "da_vao", "dang_co_mat", "so_luot", "luot_khong_dat")},
                         {"so_cong_nhan": 2, "da_vao": 1, "dang_co_mat": 1, "so_luot": 2, "luot_khong_dat": 1})
        self.assertEqual(tq["luot_moi_nhat"][0].result, KHONG_DAT)

    def test_thieu_gio_ra_sau_4_gio(self):
        self.run_luot(vn(29, 7, 0))
        a = self.att(self.an)
        self.assertFalse(thieu_gio_ra(a, self.shift, vn(29, 20, 59), ATT))
        self.assertTrue(thieu_gio_ra(a, self.shift, vn(29, 21, 1), ATT))


class CongNhanTest(ServiceCase):
    def test_them_sua_kiem_tra_trung_ma(self):
        team = cong_nhan.tao_to_doi(self.s, {"name": "Tổ nề", "contractor": " ", "leader_name": "Tổ trưởng"})
        self.assertIsNone(team.contractor)  # chuoi rong -> None
        w = cong_nhan.tao_cong_nhan(self.s, {"code": "CN020", "full_name": "Đỗ Văn Giang", "team_id": team.id})
        with self.assertRaises(cong_nhan.CongNhanError):
            cong_nhan.tao_cong_nhan(self.s, {"code": "CN020", "full_name": "Trùng mã"})
        with self.assertRaises(cong_nhan.CongNhanError):
            cong_nhan.sua_cong_nhan(self.s, w, {"team_id": 999})
        cong_nhan.sua_cong_nhan(self.s, w, {"phone": "0900000000", "trade": "Thợ nề"})
        self.assertEqual((w.phone, w.trade, w.team.name), ("0900000000", "Thợ nề", "Tổ nề"))


if __name__ == "__main__":
    unittest.main()
