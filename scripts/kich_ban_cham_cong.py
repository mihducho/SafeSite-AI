"""Kich ban cham cong chay that (docs/LOGIC_CHAM_CONG.md, Phu luc): goi DUNG cac ham nghiep vu cua ung dung
(xu_ly_luot, cham_thu_cong, cho_nghi_viec, sua_ca, bang_cong_ngay, bang_cong_thang, tong_quan, excel_bang_cong_thang)
voi luot kiem tra gia va thoi diem gia lap (khong cho gio that). Moi kich ban in: cac luot dau vao -> hanh dong cua tung
luot (kem bang cong ngay sau luot) -> bang cong cuoi cung -> GHI CHU khi ket qua co ve vo ly.

- Moi kich ban 1 CSDL SQLite MOI trong bo nho. Rieng kich ban 23 (2 thread) dung file SQLite tam (xoa khi xong): CSDL
  trong bo nho dung chung 1 ket noi cho moi thread nen khong mo phong duoc 2 giao dich song song.
  KHONG doc / ghi CSDL that (DATABASE_URL trong .env), KHONG ghi anh. Khong import app.main hay seed_demo.py (ca 2 tao
  ung dung / mo CSDL that khi import).
- Ca lam: attendance.default_shift trong configs/settings.yaml, tao giong seed_demo.seed_shift (ca mac dinh luc cai dat).
  Tham so duplicate_minutes, missing_checkout_hours, timezone, face.* cung lay tu settings.yaml.
- Khuon mat gia: cong nhan thu i co face.min_samples mau quanh vector don vi thu i; luot gia mang 3 vector gan mau do ->
  so khop that (app/services/nhan_dien.py) nhan ra dung nguoi. Nguoi la: vector thu 99 (khong ai co).
- GHI CHU la nhan xet cua tai lieu, chi in khi dieu kien tuong ung xay ra (doi logic thi ghi chu tu doi theo).

Chay: .venv\\Scripts\\python.exe scripts\\kich_ban_cham_cong.py
      .venv\\Scripts\\python.exe scripts\\kich_ban_cham_cong.py 9 12 23     (chi chay vai kich ban)
"""
import io
import sys
import tempfile
import threading
from datetime import date, datetime, time, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select  # noqa: E402

from app.db import Database  # noqa: E402
from app.models import Attendance, FaceSample, PpeCheck, Shift, User, Worker  # noqa: E402
from app.services import bao_cao, cong_nhan  # noqa: E402
from app.services.cham_cong import ChamCongError, cham_thu_cong, mui_gio, ngay_cong, sua_ca  # noqa: E402
from app.services.dang_ky_mat import DangKyMat  # noqa: E402
from app.services.luot import LuotKiemTra, xu_ly_luot  # noqa: E402
from app.services.nhan_dien import NhanDien, vector_to_embedding  # noqa: E402
from src.checkpoint.evaluate import DAT, KHONG_CO_NGUOI, KHONG_DAT, KHONG_XAC_DINH, NHIEU_NGUOI  # noqa: E402
from src.config import load_settings  # noqa: E402
from src.face.match import l2_normalize  # noqa: E402

SETTINGS = load_settings()
ATT = SETTINGS["attendance"]
TZ = mui_gio(ATT)
NGAY = date(2026, 11, 2)  # thu Hai
THU = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ nhật"]
MAU = {"xanh": "XANH", "do": "ĐỎ", "vang": "VÀNG"}
NGUOI_LA = 99


def vn(h: int, m: int = 0, s: float = 0, ngay: date = NGAY) -> datetime:
    """Thoi diem gio Viet Nam (co mui gio)."""
    whole = int(s)
    return datetime.combine(ngay, time(h, m, whole, int(round((s - whole) * 1e6))), tzinfo=TZ)


def hm(t: datetime | None) -> str:
    return t.astimezone(TZ).strftime("%H:%M") if t else "–"


def gan(i: int, seed: int) -> np.ndarray:
    """Vector khuon mat gia gan vector don vi thu i (cosine ~0.99)."""
    v = np.zeros(128, np.float32)
    v[i] = 1.0
    return l2_normalize(v + 0.05 * np.random.default_rng(seed).standard_normal(128).astype(np.float32))


def tao_ca(s) -> Shift:
    """Giong seed_demo.seed_shift khi CSDL chua co ca: ca mac dinh tu settings.yaml."""
    d = ATT["default_shift"]
    shift = Shift(name=d["name"], start_time=time.fromisoformat(d["start"]), end_time=time.fromisoformat(d["end"]),
                  break_start=time.fromisoformat(d["break_start"]), break_minutes=d["break_minutes"],
                  grace_minutes=d["grace_minutes"], early_checkin_minutes=d["early_checkin_minutes"],
                  is_overnight=False, is_overtime=False)
    s.add(shift)
    s.commit()
    return shift


class San:
    """1 CSDL moi: 1 tai khoan quan tri, ca mac dinh, cac cong nhan co mau khuon mat gia."""

    def __init__(self, url: str = "sqlite://"):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(url)
        self.db.create_all()
        self.s = self.db.session()
        self.admin = User(username="admin", password_hash="-", full_name="Quản trị", role="admin", is_active=True)
        self.s.add(self.admin)
        self.s.commit()
        self.shift = tao_ca(self.s)
        self.nd = NhanDien(SETTINGS["face"])
        self.mat: dict[str, int] = {}
        self.notes = 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.s.close()
        self.db.engine.dispose()
        self.tmp.cleanup()

    # --- du lieu ---
    def cong_nhan(self, ma: str, ten: str, tao_luc: datetime = datetime(2026, 10, 1, 8, 0, tzinfo=TZ)) -> Worker:
        i = len(self.mat)
        w = Worker(code=ma, full_name=ten, consent_at=tao_luc, created_at=tao_luc)
        self.s.add(w)
        self.s.flush()
        for k in range(SETTINGS["face"]["min_samples"]):
            self.s.add(FaceSample(worker_id=w.id, embedding=vector_to_embedding(gan(i, seed=k)), quality=0.9,
                                  thumb_path=f"{w.id}/gia_{k}.jpg", source="upload"))
        self.s.commit()
        self.nd.xoa_bo_nho_dem()
        self.mat[ma] = i
        return w

    def worker(self, ma: str) -> Worker:
        return self.s.scalar(select(Worker).where(Worker.code == ma))

    def vectors(self, ma: str | None) -> np.ndarray:
        if ma is None:
            return np.zeros((0, 128), np.float32)  # khong thay mat
        i = NGUOI_LA if ma == "la" else self.mat[ma]
        return np.stack([gan(i, seed=10 + k) for k in range(3)])

    def bang_cong(self, ma: str, ngay: date) -> Attendance | None:
        w = self.worker(ma)
        return self.s.scalar(select(Attendance).where(Attendance.worker_id == w.id, Attendance.work_date == ngay))

    # --- hanh dong ---
    def luot(self, t: datetime, ket_qua: str = DAT, ma: str | None = "CN001", thieu=(), s=None, in_ra=True) -> dict:
        """ma: nguoi dung truoc camera (ma cong nhan; "la" = nguoi la; None = khong thay mat)."""
        if ket_qua == KHONG_DAT and not thieu:
            thieu = ["thieu_mu"]
        luot = LuotKiemTra(thoi_diem=t, ket_qua=ket_qua, thieu=list(thieu), vectors=self.vectors(ma),
                           thoi_gian_ms=1500.0, chi_tiet={"so_khung": 10})
        ev = xu_ly_luot(s or self.s, luot, settings=SETTINGS, nhan_dien=self.nd, image_dir=self.tmp.name)
        if in_ra:
            who = {None: "không thấy mặt", "la": "người lạ"}.get(ma, ma)
            kq = ket_qua + (f" ({', '.join(thieu)})" if thieu else "")
            nhan = ev["cong_nhan"]["ma"] if ev["cong_nhan"] else ev["trang_thai_mat"]
            print(f"  [{t.astimezone(TZ):%d/%m %H:%M:%S}] {who:>14} | bảo hộ {kq:<26} | mặt → {nhan:<14} | "
                  f"hướng {ev['huong'] or '–':<3} | {ev['hanh_dong']:<12} | {MAU[ev['mau']]}: \"{ev['thong_bao']}\"")
            if ev["cong_nhan"]:
                self.in_trang_thai(ev["cong_nhan"]["ma"], ngay_cong(t, TZ))
        return ev

    def tay(self, ma: str, ngay: date, gio_vao: time | None, gio_ra: time | None, ly_do: str, now: datetime):
        """Cham cong thu cong (luc now, gio Viet Nam)."""
        mo_ta = (f"  [{now:%d/%m %H:%M}] CHẤM TAY {ma} ngày {ngay:%d/%m}: giờ vào {gio_vao or '(giữ)'}"
                 f", giờ ra {gio_ra or '(giữ)'}, lý do \"{ly_do}\"")
        try:
            cham_thu_cong(self.s, self.worker(ma), ngay, gio_vao, gio_ra, ly_do, self.admin, ATT, now=now)
        except ChamCongError as e:
            print(f"{mo_ta} → TỪ CHỐI: {e}")
            return False
        print(f"{mo_ta} → chấp nhận")
        self.in_trang_thai(ma, ngay)
        return True

    # --- in ---
    def in_trang_thai(self, ma: str, ngay: date) -> None:
        a = self.bang_cong(ma, ngay)
        if a is None:
            print(f"{'':16}↳ bảng công {ma} {ngay:%d/%m}: chưa có bản ghi")
        else:
            print(f"{'':16}↳ bảng công {ma} {ngay:%d/%m}: vào {hm(a.check_in)} · ra {hm(a.check_out)} · muộn "
                  f"{a.late_minutes} · về sớm {a.early_leave_minutes} · làm {a.worked_minutes} · {a.status}")

    def ket_qua(self, ma: str, ngay: date = NGAY, now: datetime | None = None) -> dict | None:
        """Dong bang cong ngay (bao_cao.bang_cong_ngay, nhu trang Bang cong) xem luc now (mac dinh 23:59 cung ngay)."""
        now = now or vn(23, 59, ngay=ngay)
        r = next((r for r in bao_cao.bang_cong_ngay(self.s, ngay, ATT, now) if r["ma"] == ma), None)
        head = f"  → BẢNG CÔNG {ma} ngày {ngay:%d/%m} ({THU[ngay.weekday()]}), xem lúc {now:%d/%m %H:%M}:"
        if r is None:
            print(f"{head} không có dòng nào (không hiện trong bảng công ngày)")
            return None
        lam = f"{r['so_phut_lam']} phút ({r['so_phut_lam'] // 60}:{r['so_phut_lam'] % 60:02d})"
        print(f"{head} vào {r['gio_vao'] or '–'} | ra {r['gio_ra'] or '–'} | muộn {r['di_muon_phut']} | về sớm "
              f"{r['ve_som_phut']} | làm {lam} | trạng thái {r['trang_thai']} | thiếu giờ ra: "
              f"{'CÓ' if r['thieu_gio_ra'] else 'không'}")
        if r["ghi_chu"]:
            for line in r["ghi_chu"].splitlines():
                print(f"{'':6}ghi chú: {line}")
        return r

    def note(self, text: str) -> None:
        self.notes += 1
        print(f"  ! GHI CHÚ: {text}")

    def done(self) -> None:
        if not self.notes:
            print("  (không có gì bất thường)")


# ===================================== kich ban =====================================
def kb1():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.luot(vn(6, 55))
        k.luot(vn(17, 0))
        k.ket_qua("CN001")
        k.done()


def kb2():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.cong_nhan("CN002", "Trần Thị Bình")
        k.luot(vn(7, 4))
        k.luot(vn(7, 5, 59), ma="CN002")  # them: 07:05:59 (lam tron xuong 5 phut)
        k.luot(vn(17, 0))
        k.luot(vn(17, 0, 30), ma="CN002")
        k.ket_qua("CN001")
        r = k.ket_qua("CN002")
        if r["di_muon_phut"] == 0:
            k.note("07:05:59 tính là muộn 5 phút (cắt phần giây) = đúng ân hạn → không muộn. Muộn 5 phút 59 giây vẫn "
                   "không bị tính.")
        k.done()


def kb3():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.luot(vn(7, 6))
        k.luot(vn(17, 0))
        r = k.ket_qua("CN001")
        if r["di_muon_phut"] == 6:
            k.note("Vượt ân hạn thì tính muộn từ 07:00 (6 phút), không phải từ 07:05 (1 phút): ân hạn không được trừ.")
        k.done()


def kb4():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.luot(vn(7, 2), KHONG_DAT, thieu=["thieu_mu"])
        k.luot(vn(7, 10))
        k.luot(vn(17, 0))
        r = k.ket_qua("CN001")
        if r["di_muon_phut"] > 0:
            k.note(f"Đến cổng lúc 07:02 (trong ân hạn) nhưng thiếu mũ; đội mũ xong 07:10 → bị tính muộn "
                   f"{r['di_muon_phut']} phút. Lượt 07:02 vẫn lưu trong ppe_checks nhưng không dùng cho bảng công.")
        k.done()


def kb5():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.luot(vn(5, 30))
        k.luot(vn(17, 0))
        r = k.ket_qua("CN001")
        if r["trang_thai"] == "ngoai_ca" and r["so_phut_lam"] == 540:
            k.note("Vào trước cửa sổ (06:00) vẫn được ghi giờ vào, chỉ gắn nhãn ngoai_ca; số phút làm vẫn đủ 540 "
                   "(nhãn không ảnh hưởng tới công, không cần ai duyệt).")
        k.done()


def kb6():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.luot(vn(6, 10))
        k.luot(vn(17, 0))
        k.ket_qua("CN001")
        k.done()


def kb7():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.luot(vn(7, 0))
        k.luot(vn(16, 30))
        k.ket_qua("CN001")
        k.done()


def kb8():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.luot(vn(7, 0))
        k.luot(vn(19, 30))
        r = k.ket_qua("CN001")
        if r["so_phut_lam"] == 540 and r["trang_thai"] == "binh_thuong":
            k.note("2 giờ 30 phút ở lại sau 17:00 không được ghi nhận ở đâu (không có tăng ca, không có cờ, trạng thái "
                   "vẫn binh_thuong); chỉ còn dấu vết là giờ ra 19:30.")
        k.done()


def kb9():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.luot(vn(7, 0))
        k.luot(vn(11, 30))
        k.luot(vn(12, 30))
        sau_vao_lai = k.bang_cong("CN001", NGAY).worked_minutes
        k.luot(vn(17, 0))
        k.ket_qua("CN001")
        if sau_vao_lai == 0:
            k.note("Sau lượt vào lại 12:30, giờ ra 11:30 bị xoá và số phút làm buổi sáng (270) về 0 cho tới khi quét ra. "
                   "Nếu buổi chiều quên quét ra thì cả ngày còn 0 phút + 'thiếu giờ ra' (mất cả buổi sáng).")
        k.done()


def kb10():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.luot(vn(7, 0))
        k.luot(vn(11, 30))
        k.luot(vn(12, 30), KHONG_DAT, thieu=["thieu_mu"])
        k.luot(vn(12, 35))
        k.luot(vn(17, 0))
        r = k.ket_qua("CN001")
        if r["so_phut_lam"] == 540:
            k.note("Vào lại muộn 5 phút sau giờ nghỉ (12:35) nhưng vẫn đủ 540 phút: giờ làm = giờ vào đầu tiên → giờ ra "
                   "cuối cùng trừ giờ nghỉ cố định; khoảng vắng mặt thật không bị trừ, không tính muộn.")
        k.done()


def kb11():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.luot(vn(7, 0))
        k.luot(vn(7, 1))
        ev = k.luot(vn(7, 4))
        r = k.ket_qua("CN001")
        if ev["hanh_dong"] == "ghi_ra":
            k.note(f"Quét lại lúc 07:04 (đã quá {ATT['duplicate_minutes']} phút) bị coi là RA: ghi giờ ra 07:04, "
                   f"làm {r['so_phut_lam']} phút, về sớm {r['ve_som_phut']} phút. Không có xác nhận 'bạn muốn ra?'.")
        k.done()


def kb12():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.luot(vn(7, 0))
        mai = NGAY + timedelta(days=1)
        for now in (vn(20, 0), vn(21, 0), vn(21, 30), vn(6, 0, ngay=mai)):
            k.ket_qua("CN001", NGAY, now)
        print("  (sáng hôm sau)")
        k.luot(vn(7, 0, ngay=mai))
        k.luot(vn(17, 0, ngay=mai))
        r = k.ket_qua("CN001", NGAY, vn(18, 0, ngay=mai))
        k.ket_qua("CN001", mai, vn(18, 0, ngay=mai))
        th = bao_cao.bang_cong_thang(k.s, 2026, 11, ATT, vn(18, 0, ngay=mai))["ds"][0]
        print(f"  → BẢNG CÔNG THÁNG 11: số ngày công {th['so_ngay_cong']} | tổng phút {th['tong_phut']} | "
              f"số lần muộn {th['so_lan_muon']}")
        a = k.bang_cong("CN001", NGAY)
        print(f"  → bản ghi attendance ngày {NGAY:%d/%m} trong CSDL: check_out={a.check_out}, status={a.status} "
              f"(\"thiếu giờ ra\" không lưu, chỉ tính khi hiển thị)")
        if r["thieu_gio_ra"] and th["so_ngay_cong"] == 2:
            k.note(f"Ngày {NGAY:%d/%m} mãi 'thiếu giờ ra', 0 phút làm, nhưng vẫn được đếm là 1 ngày công trong bảng "
                   "công tháng (đếm theo giờ vào). Không có gì tự đóng bản ghi hay nhắc cán bộ ngoài nhãn hiển thị.")
        k.done()


def kb13():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.luot(vn(22, 0))
        k.ket_qua("CN001")
        print("  (thêm: ra lúc 23:30)")
        k.luot(vn(23, 30))
        r = k.ket_qua("CN001")
        if r["di_muon_phut"] >= 600:
            k.note(f"Vào lúc 22:00 (ngoài ca) vẫn ghi giờ vào, trạng thái ngoai_ca, và bị tính MUỘN {r['di_muon_phut']} "
                   f"phút (= 22:00 − 07:00); làm {r['so_phut_lam']} phút. Không chặn, không có ca tối.")
        k.done()


def kb14():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.luot(vn(7, 0))
        k.luot(vn(7, 30))
        k.luot(vn(8, 0))
        k.luot(vn(17, 0))
        r = k.ket_qua("CN001")
        if r["so_phut_lam"] == 540:
            k.note("30 phút ra ngoài (07:30–08:00) không bị trừ: hệ thống chỉ giữ giờ vào đầu tiên và giờ ra cuối cùng, "
                   "không lưu các cặp vào/ra ở giữa trong bảng công.")
        k.done()


def kb15():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        ev = k.luot(vn(7, 0), ma="la")
        c = k.s.get(PpeCheck, ev["id"])
        print(f"  → ppe_checks: worker_id={c.worker_id}, face_status={c.face_status}, result={c.result}, "
              f"action={c.action}, direction={c.direction}, gần nhất={c.detail['nhan_dien']['gan_nhat_ma']} "
              f"(điểm {c.face_score})")
        print(f"  → số dòng attendance: {k.s.scalar(select(func.count(Attendance.id)))}")
        k.done()


def kb16():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.luot(vn(7, 0), NHIEU_NGUOI)
        k.luot(vn(7, 1), KHONG_XAC_DINH)
        print("  (thêm: vào thật lúc 07:02, rồi lượt ra NHIEU_NGUOI 17:00, lượt ra KHONG_XAC_DINH 17:01)")
        k.luot(vn(7, 2))
        k.luot(vn(17, 0), NHIEU_NGUOI)
        ev = k.luot(vn(17, 1), KHONG_XAC_DINH)
        k.ket_qua("CN001")
        if ev["hanh_dong"] == "ghi_ra":
            k.note("Lượt RA không xét bảo hộ nên KHONG_XAC_DINH vẫn ghi giờ ra (đúng quy tắc), nhưng NHIEU_NGUOI thì "
                   "không ghi ra dù đã nhận ra mặt: hai trường hợp 'không chắc' xử lý khác nhau.")
        k.done()


def kb17():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.luot(vn(7, 0))
        ev = k.luot(vn(17, 0), KHONG_CO_NGUOI)
        r = k.ket_qua("CN001")
        if ev["hanh_dong"] == "khong_ghi" and ev["cong_nhan"]:
            k.note("Đã nhận ra mặt An nhưng kết quả bảo hộ KHONG_CO_NGUOI (YOLO không thấy đủ khung người hợp lệ) → "
                   f"không ghi giờ ra; cuối ngày 'thiếu giờ ra': {'CÓ' if r['thieu_gio_ra'] else 'không'}.")
        k.done()


def kb18():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.tay("CN001", NGAY, time(7, 0), None, "Camera cổng hỏng buổi sáng, tổ trưởng xác nhận", now=vn(8, 0))
        k.luot(vn(17, 0))
        r = k.ket_qua("CN001")
        a = k.bang_cong("CN001", NGAY)
        print(f"  → attendance: ppe_check_id={a.ppe_check_id}, updated_by={a.updated_by}, "
              f"updated_at={hm(a.updated_at)}")
        if r["trang_thai"] == "cham_thu_cong" and r["gio_ra"]:
            k.note("Giờ ra 17:00 do camera ghi nhưng cả dòng vẫn mang trạng thái cham_thu_cong; updated_at bị lượt tự "
                   "động ghi đè thành 17:00 trong khi updated_by vẫn là admin → không còn biết lúc nào admin sửa.")
        k.done()


def kb19():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.luot(vn(7, 0))
        k.tay("CN001", NGAY, time(6, 50), None, "Đến từ 06:50, camera nhận chậm", now=vn(9, 0))
        k.tay("CN001", NGAY, None, time(6, 40), "Thử nhập giờ ra trước giờ vào", now=vn(9, 5))
        print("  (thêm: giờ ra BẰNG giờ vào)")
        ok = k.tay("CN001", NGAY, None, time(6, 50), "Thử nhập giờ ra bằng giờ vào", now=vn(9, 10))
        k.ket_qua("CN001", now=vn(9, 15))
        a = k.bang_cong("CN001", NGAY)
        c = k.s.get(PpeCheck, a.ppe_check_id)
        print(f"  → attendance.ppe_check_id trỏ tới lượt lúc {hm(c.checked_at)}, trong khi giờ vào là {hm(a.check_in)}")
        k.note("Ghi chú lịch sử chỉ có 'giờ sửa + người sửa + lý do', không lưu giá trị cũ (07:00 → 06:50) → không "
               "truy được đã sửa gì. ppe_check_id vẫn trỏ lượt 07:00 nên ảnh minh chứng không khớp giờ vào.")
        if ok:
            k.note("Giờ ra = giờ vào được chấp nhận (chỉ chặn ra < vào) → dòng công 0 phút, không còn 'đang có mặt'.")
        k.done()


def kb20():
    with San() as k:
        an = k.cong_nhan("CN001", "Nguyễn Văn An")
        dk = DangKyMat(SETTINGS, Path(k.tmp.name) / "anh_mau_mat", k.nd)
        k.luot(vn(7, 0))
        n = cong_nhan.cho_nghi_viec(k.s, an, dk)
        print(f"  [02/11 10:00] CHO NGHỈ VIỆC CN001 → status={an.status}, đã xoá {n} mẫu khuôn mặt")
        k.in_trang_thai("CN001", NGAY)
        ev = k.luot(vn(17, 0))
        r = k.ket_qua("CN001")
        k.ket_qua("CN001", NGAY + timedelta(days=1))
        if ev["trang_thai_mat"] == "KHONG_NHAN_RA" and r and r["thieu_gio_ra"]:
            k.note("Cho nghỉ việc khi đang có mặt: bản ghi công hôm đó không được đóng, lượt ra 17:00 không nhận ra "
                   "→ 'thiếu giờ ra' vĩnh viễn, 0 phút làm. Không lưu ngày nghỉ việc.")
        k.done()


def kb21():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        for d in (date(2026, 11, 1), date(2026, 9, 2)):
            print(f"  ({d:%d/%m/%Y} là {THU[d.weekday()]})")
            k.luot(vn(7, 0, ngay=d))
            k.luot(vn(17, 0, ngay=d))
            k.ket_qua("CN001", d)
        k.note("Không có khái niệm ngày nghỉ / ngày lễ: Chủ nhật và 02/09 tính như ngày thường (binh_thuong, đủ 540 "
               "phút, có tính muộn / về sớm), không đánh dấu, không hệ số.")
        k.done()


def kb22():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        mai = NGAY + timedelta(days=1)
        k.luot(vn(23, 50))
        ev = k.luot(vn(0, 20, ngay=mai))
        k.ket_qua("CN001", NGAY, vn(8, 0, ngay=mai))
        k.ket_qua("CN001", mai, vn(8, 0, ngay=mai))
        if ev["hanh_dong"] == "ghi_vao":
            k.note("Lượt 00:20 thuộc ngày công mới (03/11) nên bị coi là VÀO (mở dòng công mới, ngoai_ca) thay vì RA "
                   "của ca 02/11; dòng 02/11 thành 'thiếu giờ ra'. Ca qua đêm chưa hỗ trợ.")
        k.done()


def kb23():
    """2 thread, moi thread 1 session rieng (nhu 2 cong cung ghi 1 luc), lap lai nhieu lan tren file SQLite tam."""
    lan, outcomes = 10, {}
    with tempfile.TemporaryDirectory() as d:
        for i in range(lan):
            url = "sqlite:///" + (Path(d) / f"kb23_{i}.db").as_posix()
            with San(url) as k:
                k.cong_nhan("CN001", "Nguyễn Văn An")
                k.nd.gallery(k.s)  # nap bo nho dem truoc (nhu ung dung da chay)
                barrier, res = threading.Barrier(2), {}

                def chay(ten, t, k=k, barrier=barrier, res=res):
                    with k.db.session() as s:
                        barrier.wait()
                        try:
                            ev = k.luot(t, s=s, in_ra=False)
                            res[ten] = f"{ev['hanh_dong']}"
                        except Exception as e:  # noqa: BLE001 - ghi lai moi loi de bao cao
                            res[ten] = f"LỖI {type(e).__name__}"

                th = [threading.Thread(target=chay, args=("A 07:00:00.0", vn(7, 0))),
                      threading.Thread(target=chay, args=("B 07:00:00.5", vn(7, 0, 0.5)))]
                for t in th:
                    t.start()
                for t in th:
                    t.join(30)
                k.s.expire_all()
                rows = k.s.scalars(select(Attendance)).all()
                checks = k.s.scalar(select(func.count(PpeCheck.id)))
                key = (f"A → {res.get('A 07:00:00.0')}, B → {res.get('B 07:00:00.5')} | {len(rows)} dòng attendance, "
                       f"{checks} lượt | giờ vào " + ", ".join(hm(r.check_in) + f":{r.check_in.second:02d}."
                                                         f"{r.check_in.microsecond // 100000}" for r in rows))
                outcomes[key] = outcomes.get(key, 0) + 1
    print(f"  Chạy {lan} lần (mỗi lần CSDL mới), 2 thread bắt đầu cùng lúc (Barrier), mỗi thread 1 session riêng:")
    for key, n in sorted(outcomes.items(), key=lambda kv: -kv[1]):
        print(f"    {n:>2} lần: {key}")
    print("  (SQLite khoá cả file khi ghi nên 2 giao dịch luôn chạy lần lượt; MariaDB (InnoDB) khoá theo dòng nên có "
          "thể khác, xem mục 15 của tài liệu.)")
    if any("LỖI" in key for key in outcomes):
        print("  ! GHI CHÚ: có lần bị lỗi khi 2 lượt ghi cùng lúc.")
    elif any("07:00:00.5" in key.split("giờ vào")[1] for key in outcomes):
        print("  ! GHI CHÚ: có lần lượt B (đến sau 0,5 giây) ghi giờ vào trước, lượt A thành bo_qua_trung → giờ vào bị "
              "lệch 0,5 giây so với lần đến đầu tiên (không đáng kể nhưng thứ tự không đảm bảo).")


def kb24():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.luot(vn(7, 0))
        ok = k.tay("CN001", NGAY, None, time(17, 0), "Nhập trước giờ ra cho cả tổ", now=vn(9, 0))
        k.ket_qua("CN001", now=vn(9, 1))
        if ok:
            k.note("Lúc 09:00 nhập được giờ ra 17:00 cùng ngày (giờ chưa tới): chỉ chặn NGÀY tương lai, không chặn "
                   "GIỜ tương lai trong hôm nay → có thể chấm công trước cho người chưa làm.")
        k.done()


def kb25():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.luot(vn(7, 0))
        k.tay("CN001", NGAY, None, time(16, 30), "Về sớm có phép, quên quét", now=vn(16, 35))
        ev = k.luot(vn(16, 40))
        r = k.ket_qua("CN001")
        if ev["hanh_dong"] == "ghi_vao" and not r["gio_ra"]:
            k.note("Sau khi cán bộ chấm tay giờ ra 16:30, công nhân đi ngang camera lúc 16:40 → coi là VÀO LẠI, giờ ra "
                   "chấm tay bị xoá, cuối ngày 'thiếu giờ ra'. Lượt tự động ghi đè dữ liệu chấm tay mà không báo.")
        k.done()


def kb26():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.cong_nhan("CN002", "Trần Thị Bình")
        k.luot(vn(7, 0))
        k.luot(vn(17, 0))
        ev = k.luot(vn(17, 1))
        r = k.ket_qua("CN001")
        print("  (biến thể: Bình ra 17:00, 17:01 quay lại nhưng đã tháo mũ)")
        k.luot(vn(7, 0, 30), ma="CN002", in_ra=False)
        k.luot(vn(17, 0, 30), ma="CN002")
        k.luot(vn(17, 1, 30), KHONG_DAT, ma="CN002", thieu=["thieu_mu"])
        k.ket_qua("CN002")
        if ev["hanh_dong"] == "ghi_vao":
            k.note("Ra 17:00 rồi 1 phút sau đứng lại trước camera → VÀO LẠI (chống trùng chỉ áp dụng cho lượt RA ngay "
                   "sau lượt VÀO, không áp dụng cho VÀO ngay sau RA): giờ ra 17:00 bị xoá, cuối ngày 'thiếu giờ ra' "
                   f"= {'CÓ' if r['thieu_gio_ra'] else 'không'}, {r['so_phut_lam']} phút làm.")
        k.done()


def kb27():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        hqua = NGAY - timedelta(days=1)
        k.luot(vn(7, 10, ngay=hqua))
        k.luot(vn(17, 0, ngay=hqua))
        k.luot(vn(7, 10))
        n = sua_ca(k.s, k.shift, {"start_time": time(7, 30)}, ATT, now=vn(9, 0))
        print(f"  [02/11 09:00] SỬA CA: bắt đầu 07:00 → 07:30 (sua_ca tính lại {n} dòng của hôm nay)")
        k.luot(vn(17, 0))
        r1 = k.ket_qua("CN001", hqua, vn(18, 0))
        r2 = k.ket_qua("CN001", NGAY, vn(18, 0))
        if r1["di_muon_phut"] != r2["di_muon_phut"]:
            k.note(f"Cùng giờ vào 07:10: hôm qua muộn {r1['di_muon_phut']} phút (ca cũ), hôm nay muộn "
                   f"{r2['di_muon_phut']} (ca mới). Bảng công không lưu đã tính theo ca nào; 'thiếu giờ ra' của ngày cũ "
                   "lại tính theo giờ ca hiện tại.")
        k.done()


def kb28():
    """Bao cao: bang cong thang, file Excel, trang Tong quan tren 3 ngay du lieu."""
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.cong_nhan("CN002", "Trần Thị Bình")
        k.cong_nhan("CN003", "Lê Văn Cường", tao_luc=vn(8, 0, ngay=date(2026, 11, 3)))
        d1, d2, d3 = date(2026, 11, 2), date(2026, 11, 3), date(2026, 11, 4)
        print("  (02/11) An 07:00–17:00, ra đã tháo mũ; Bình muộn 07:20–17:00")
        k.luot(vn(7, 0, ngay=d1), in_ra=False)
        k.luot(vn(7, 20, ngay=d1), ma="CN002", in_ra=False)
        k.luot(vn(17, 0, ngay=d1), KHONG_DAT, in_ra=False)
        k.luot(vn(17, 0, 30, ngay=d1), ma="CN002", in_ra=False)
        print("  (03/11) An vào 07:00, không quét ra; Bình được chấm tay 07:00–17:00")
        k.luot(vn(7, 0, ngay=d2), in_ra=False)
        k.tay("CN002", d2, time(7, 0), time(17, 0), "Quên quét cả ngày", now=vn(18, 0, ngay=d2))
        print("  (04/11, hôm nay, xem lúc 10:00) các lượt:")
        k.luot(vn(6, 58, ngay=d3), KHONG_DAT)
        k.luot(vn(7, 0, ngay=d3))
        k.luot(vn(7, 5, ngay=d3), KHONG_DAT, ma="la")
        k.luot(vn(7, 6, ngay=d3), KHONG_XAC_DINH, ma="CN002")
        k.luot(vn(7, 7, ngay=d3), ma="CN002")
        k.luot(vn(9, 0, ngay=d3), KHONG_DAT, thieu=["thieu_mu", "thieu_ao"])
        now = vn(10, 0, ngay=d3)
        tq = bao_cao.tong_quan(k.s, ATT, now)
        gio = {r["gio"]: (r["dat"], r["khong_dat"], r["khac"]) for r in tq["luot_theo_gio"] if any(
            (r["dat"], r["khong_dat"], r["khac"]))}
        print(f"  → TỔNG QUAN 04/11 10:00: số công nhân {tq['so_cong_nhan']} | đã vào {tq['da_vao']} | đang có mặt "
              f"{tq['dang_co_mat']} | số lượt {tq['so_luot']} | lượt đạt {tq['luot_dat']} | lượt không đạt "
              f"{tq['luot_khong_dat']} | tỷ lệ đạt {tq['ty_le_dat']}")
        print(f"    lượt theo giờ (đạt, không đạt, khác): {gio}")
        th = bao_cao.bang_cong_thang(k.s, 2026, 11, ATT, now)
        print("  → BẢNG CÔNG THÁNG 11/2026 (xem 04/11 10:00):")
        for w in th["ds"]:
            cells = "; ".join(f"{d}/11 {c['gio_vao']}–{c['gio_ra'] or '?'} {c['so_phut_lam']}p {c['trang_thai']}"
                              f"{' THIẾU RA' if c['thieu_gio_ra'] else ''}" for d, c in w["ngay"].items())
            print(f"    {w['ma']}: ngày công {w['so_ngay_cong']} | tổng phút {w['tong_phut']} | lần muộn "
                  f"{w['so_lan_muon']} | {cells or '(không có ngày nào)'}")
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(bao_cao.excel_bang_cong_thang(th)))
        ws = wb["Bang cong"]
        hdr = [c.value for c in ws[2]]
        print(f"  → EXCEL sheet 'Bang cong': {len(hdr)} cột = Mã, Họ tên, Tổ đội, 1..{th['so_ngay']}, "
              f"{', '.join(hdr[-3:])}")
        for row in ws.iter_rows(min_row=3, values_only=True):
            print(f"    {row[0]}: ngày 1–4 = {list(row[3:7])} | {hdr[-3]} {row[-3]} | {hdr[-2]} {row[-2]} | "
                  f"{hdr[-1]} {row[-1]}")
        ct = wb["Chi tiet"]
        print(f"  → EXCEL sheet 'Chi tiet': cột {[c.value for c in ct[1]]}")
        for row in ct.iter_rows(min_row=2, values_only=True):
            print(f"    {list(row[:10])}")
        if tq["luot_khong_dat"] > 2:
            k.note(f"'Lượt không đạt' = {tq['luot_khong_dat']} gồm cả lượt RA tháo mũ (09:00, màn hình báo XANH) và "
                   "người lạ (màn hình báo VÀNG); tỷ lệ đạt tính trên các lượt đó.")
        c3 = next(w for w in th["ds"] if w["ma"] == "CN001")
        if c3["ngay"].get(3, {}).get("thieu_gio_ra") and c3["so_ngay_cong"] == 3:
            k.note("An ngày 03/11 thiếu giờ ra (0 phút) vẫn tính 1 ngày công; Excel ô ngày 3 ghi '0:00'.")
        k.done()


def kb29():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.luot(vn(7, 0))
        k.luot(vn(11, 30))
        k.luot(vn(14, 0))
        k.luot(vn(17, 0))
        r = k.ket_qua("CN001")
        if r["so_phut_lam"] == 540:
            k.note("Ra ăn trưa 11:30, 14:00 mới vào lại (vắng 2 giờ 30 phút, quá giờ nghỉ 1 giờ 30 phút) vẫn đủ 540 phút, "
                   "không muộn, không về sớm.")
        k.done()


KICH_BAN = [
    (1, "Vào 06:55 đạt, ra 17:00", kb1),
    (2, "Vào 07:04 (trong ân hạn), ra 17:00 (thêm: người thứ hai vào 07:05:59)", kb2),
    (3, "Vào 07:06, ra 17:00", kb3),
    (4, "07:02 không đạt (thiếu mũ), 07:10 đạt, ra 17:00", kb4),
    (5, "Vào 05:30 (sớm hơn cửa sổ cho vào sớm), ra 17:00", kb5),
    (6, "Vào 06:10 (trong cửa sổ cho vào sớm), ra 17:00", kb6),
    (7, "Vào 07:00, ra 16:30 (về sớm)", kb7),
    (8, "Vào 07:00, ra 19:30 (ở lại muộn, không có ca tăng ca)", kb8),
    (9, "Vào 07:00, ra 11:30, vào lại 12:30 (đạt), ra 17:00", kb9),
    (10, "Như #9 nhưng vào lại 12:30 KHÔNG ĐẠT, 12:35 đạt", kb10),
    (11, "Vào 07:00, quét lại 07:01 (trùng), quét 07:04", kb11),
    (12, "Vào 07:00, không quét ra; xem lúc 20:00, 21:00, 21:30, sáng hôm sau; hôm sau vào 07:00", kb12),
    (13, "Vào 22:00 (ngoài khung ca)", kb13),
    (14, "Vào 07:00, ra 07:30, vào 08:00, ra 17:00", kb14),
    (15, "Người lạ (không nhận ra) đạt bảo hộ", kb15),
    (16, "Nhận ra đúng người nhưng NHIEU_NGUOI, rồi KHONG_XAC_DINH", kb16),
    (17, "Lượt ra với kết quả KHONG_CO_NGUOI", kb17),
    (18, "Chấm tay giờ vào 07:00 khi chưa có bản ghi, sau đó quét tự động ra 17:00", kb18),
    (19, "Đã quét vào 07:00, chấm tay sửa giờ vào 06:50; rồi sửa giờ ra trước giờ vào", kb19),
    (20, "Cho nghỉ việc lúc 10:00 khi đang có mặt, rồi quét ra 17:00", kb20),
    (21, "Quét vào ngày Chủ nhật và ngày 02/09 (Quốc khánh)", kb21),
    (22, "Vào 23:50, ra 00:20 hôm sau (qua nửa đêm)", kb22),
    (23, "Hai lượt của cùng một người cách nhau 0,5 giây, gọi song song từ 2 thread", kb23),
    (24, "(thêm) Chấm tay giờ ra 17:00 lúc 09:00 cùng ngày", kb24),
    (25, "(thêm) Chấm tay giờ ra 16:30, sau đó công nhân đi ngang camera 16:40", kb25),
    (26, "(thêm) Ra 17:00 rồi 17:01 quay lại đứng trước camera", kb26),
    (27, "(thêm) Sửa giờ bắt đầu ca giữa ngày (07:00 → 07:30)", kb27),
    (28, "(thêm) Báo cáo: tổng quan, bảng công tháng, Excel trên 3 ngày dữ liệu", kb28),
    (29, "(thêm) Ra ăn trưa 11:30, 14:00 mới vào lại", kb29),
]


def main(argv: list[str]) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    chon = {int(a) for a in argv}
    d = ATT["default_shift"]
    print(f"Ca: {d['name']} {d['start']}–{d['end']}, nghỉ {d['break_start']} ({d['break_minutes']} phút), ân hạn "
          f"{d['grace_minutes']} phút, cho vào sớm {d['early_checkin_minutes']} phút | duplicate_minutes "
          f"{ATT['duplicate_minutes']} | missing_checkout_hours {ATT['missing_checkout_hours']} | {ATT['timezone']}")
    print(f"Ngày chính: {NGAY:%d/%m/%Y} ({THU[NGAY.weekday()]}). Cột: [thời điểm] người đứng trước camera | kết quả "
          "bảo hộ | kết quả nhận diện | hướng | hành động | màu + câu trên màn hình cổng; ↳ = dòng attendance sau lượt.")
    for so, tieu_de, fn in KICH_BAN:
        if chon and so not in chon:
            continue
        print(f"\n=== #{so}. {tieu_de} ===")
        fn()


if __name__ == "__main__":
    main(sys.argv[1:])
