"""Kich ban cham cong chay that (docs/LOGIC_CHAM_CONG.md, Phu luc): goi DUNG cac ham nghiep vu cua ung dung
(xu_ly_luot, cham_thu_cong, them_phien, sua_phien, danh_dau_thieu_gio_ra, cho_nghi_viec, sua_ca, them_phep,
bang_cong_ngay, bang_cong_thang, tong_quan, viec_can_xu_ly, excel_bang_cong_thang) voi luot kiem tra gia va thoi diem
gia lap (khong cho gio that). Moi kich ban in: cac luot dau vao -> hanh dong cua tung luot (kem bang cong ngay sau luot)
-> bang cong cuoi cung (trang thai ngay, phien) -> GHI CHU khi ket qua co ve vo ly.

- Moi kich ban 1 CSDL SQLite MOI trong bo nho. Rieng kich ban 23 (2 thread) dung file SQLite tam (xoa khi xong): CSDL
  trong bo nho dung chung 1 ket noi cho moi thread nen khong mo phong duoc 2 giao dich song song.
  KHONG doc / ghi CSDL that (DATABASE_URL trong .env), KHONG ghi anh. Khong import app.main hay seed_demo.py (ca 2 tao
  ung dung / mo CSDL that khi import).
- Ca lam: attendance.default_shift trong configs/settings.yaml, tao giong seed_demo.seed_shift (ca mac dinh luc cai dat).
  Tham so missing_checkout_hours, timezone, phep... cung lay tu settings.yaml.
- Khuon mat gia: cong nhan thu i co face.min_samples mau quanh vector don vi thu i; luot gia mang 3 vector gan mau do ->
  so khop that (app/services/nhan_dien.py) nhan ra dung nguoi. Nguoi la: vector thu 99 (khong ai co).
- "Thieu gio ra" duoc LUU boi tac vu nen: kich ban goi danh_dau_thieu_gio_ra(now) dung luc can xem (nhu tac vu nen).
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
from app.models import Attendance, FaceSample, NhatKyChamCong, PpeCheck, Shift, User, Worker  # noqa: E402
from app.services import bao_cao, cong_nhan, phep  # noqa: E402
from app.services.cham_cong import (ChamCongError, cham_thu_cong, danh_dau_thieu_gio_ra, mui_gio, ngay_cong,  # noqa: E402
                                    sua_ca, sua_phien, them_phien)
from app.services.dang_ky_mat import DangKyMat  # noqa: E402
from app.services.luot import LuotKiemTra, xu_ly_luot  # noqa: E402
from app.services.nhan_dien import NhanDien, vector_to_embedding  # noqa: E402
from app.services.tinh_cong import TEN_TRANG_THAI  # noqa: E402
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
                  phut_chong_trung=d["phut_chong_trung"], is_overnight=False, is_overtime=False)
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
    def cong_nhan(self, ma: str, ten: str, tao_luc: datetime = datetime(2026, 8, 1, 8, 0, tzinfo=TZ)) -> Worker:
        i = len(self.mat)
        w = Worker(code=ma, full_name=ten, consent_at=tao_luc, created_at=tao_luc, ngay_vao_lam=tao_luc.date())
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
        self.s.expire_all()
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
            phu = f" + \"{ev['thong_bao_phu']}\"" if ev["thong_bao_phu"] else ""
            print(f"  [{t.astimezone(TZ):%d/%m %H:%M:%S}] {who:>14} | bảo hộ {kq:<26} | mặt → {nhan:<14} | "
                  f"hướng {ev['huong'] or '–':<3} | {ev['hanh_dong']:<12} | {MAU[ev['mau']]}: \"{ev['thong_bao']}\"{phu}")
            if ev["cong_nhan"]:
                self.in_trang_thai(ev["cong_nhan"]["ma"], ngay_cong(t, TZ))
        return ev

    def tay(self, mo_ta: str, fn, now: datetime) -> bool:
        """Thao tac tay (fn goi service, co now): in ket qua chap nhan / tu choi."""
        try:
            fn()
        except ChamCongError as e:
            print(f"  [{now:%d/%m %H:%M}] {mo_ta} → TỪ CHỐI: {e}")
            return False
        print(f"  [{now:%d/%m %H:%M}] {mo_ta} → chấp nhận")
        return True

    def tay_ngay(self, ma: str, ngay: date, gio_vao: time | None, gio_ra: time | None, ly_do: str, now: datetime):
        """API cu POST /api/cham-cong-thu-cong (sua phien dau / phien cuoi cua ngay)."""
        ok = self.tay(f"CHẤM TAY {ma} ngày {ngay:%d/%m}: giờ vào {gio_vao or '(giữ)'}, giờ ra {gio_ra or '(giữ)'}, "
                      f"lý do \"{ly_do}\"",
                      lambda: cham_thu_cong(self.s, self.worker(ma), ngay, gio_vao, gio_ra, ly_do, self.admin, ATT,
                                            now=now), now)
        if ok:
            self.in_trang_thai(ma, ngay)
        return ok

    def quet_thieu(self, now: datetime) -> int:
        n = danh_dau_thieu_gio_ra(self.s, ATT, now)
        print(f"  [{now:%d/%m %H:%M:%S}] TÁC VỤ NỀN đánh dấu thiếu giờ ra → {n} phiên")
        return n

    # --- in ---
    def in_trang_thai(self, ma: str, ngay: date) -> None:
        a = self.bang_cong(ma, ngay)
        if a is None:
            print(f"{'':16}↳ bảng công {ma} {ngay:%d/%m}: chưa có bản ghi")
            return
        ph = ", ".join(f"{hm(p.vao_at)}–{hm(p.ra_at)} {p.trang_thai}" for p in sorted(a.segments, key=lambda p: p.vao_at))
        print(f"{'':16}↳ bảng công {ma} {ngay:%d/%m}: phiên [{ph}] · muộn {a.late_minutes} · về sớm "
              f"{a.early_leave_minutes} · làm {a.worked_minutes} · ra ngoài {a.phut_ra_ngoai}")

    def ket_qua(self, ma: str, ngay: date = NGAY, now: datetime | None = None) -> dict | None:
        """Dong bang cong ngay (bao_cao.bang_cong_ngay, nhu trang Bang cong) xem luc now (mac dinh 23:59 cung ngay)."""
        self.s.expire_all()
        now = now or vn(23, 59, ngay=ngay)
        r = next((r for r in bao_cao.bang_cong_ngay(self.s, ngay, ATT, now) if r["ma"] == ma), None)
        head = f"  → BẢNG CÔNG {ma} ngày {ngay:%d/%m} ({THU[ngay.weekday()]}), xem lúc {now:%d/%m %H:%M}:"
        if r is None:
            print(f"{head} không có dòng nào (không hiện trong bảng công ngày)")
            return None
        lam = f"{r['so_phut_lam']} phút ({r['so_phut_lam'] // 60}:{r['so_phut_lam'] % 60:02d})"
        print(f"{head} {r['ten_trang_thai'].upper()} ({r['trang_thai_ngay']}), ngày công {r['ngay_cong']}, công quy "
              f"đổi {r['cong_quy_doi']}")
        print(f"{'':6}vào {r['gio_vao'] or '–'} | ra {r['gio_ra'] or '–'} | muộn {r['di_muon_phut']} | về sớm "
              f"{r['ve_som_phut']} | làm {lam} | ra ngoài {r['phut_ra_ngoai']} phút ({r['so_lan_ra_ngoai']} lần) | "
              f"công tác {r['phut_cong_tac']} | thiếu giờ ra: {'CÓ' if r['thieu_gio_ra'] else 'không'}"
              + (" | sửa tay" if r["co_sua_tay"] else "") + (" | làm ngày nghỉ" if r["lam_ngay_nghi"] else ""))
        if r["phien"]:
            print(f"{'':6}phiên: " + "; ".join(f"{p['vao']}–{p['ra'] or '?'} ({p['trang_thai']}, vào {p['nguon_vao']}"
                                              + (f", ra {p['nguon_ra']}" if p["nguon_ra"] else "") + ")"
                                              for p in r["phien"]))
        return r

    def in_nhat_ky(self) -> None:
        for n in self.s.scalars(select(NhatKyChamCong).order_by(NhatKyChamCong.id)):
            print(f"  → NHẬT KÝ: {n.thoi_diem.astimezone(TZ):%d/%m %H:%M} {n.hanh_dong}: {n.gia_tri_cu or '–'} → "
                  f"{n.gia_tri_moi or '–'} | lý do \"{n.ly_do}\" | người sửa {n.user_id}")

    def in_viec(self, now: datetime) -> list[dict]:
        self.s.expire_all()
        v = bao_cao.viec_can_xu_ly(self.s, ATT, now)
        print(f"  → VIỆC CẦN XỬ LÝ (lúc {now:%d/%m %H:%M}): " + ("; ".join(f"{x['ma']} {x['ngay']} {x['mo_ta']}"
                                                                      for x in v) or "không có"))
        return v

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
        k.luot(vn(7, 5, 59), ma="CN002")  # them: 07:05:59 (qua an han 59 giay)
        k.luot(vn(17, 0))
        k.luot(vn(17, 0, 30), ma="CN002")
        k.ket_qua("CN001")
        k.ket_qua("CN002")
        k.done()


def kb3():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.luot(vn(7, 6))
        k.luot(vn(17, 0))
        k.ket_qua("CN001")
        k.done()


def kb4():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.luot(vn(7, 2), KHONG_DAT, thieu=["thieu_mu"])
        k.luot(vn(7, 10))
        k.luot(vn(17, 0))
        k.ket_qua("CN001")
        k.done()


def kb5():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.luot(vn(5, 30))
        ev = k.luot(vn(17, 0))
        k.quet_thieu(vn(21, 0, 1))
        r = k.ket_qua("CN001")
        if ev["hanh_dong"] == "ghi_vao":
            k.note("05:30 bị từ chối (chưa đến giờ vào) là đúng, nhưng lượt lúc 17:00 (người đó ra về) lại được ghi là "
                   f"VÀO (17:00 vẫn trong cửa sổ vào) → phiên mới không bao giờ đóng → '{r['ten_trang_thai']}', "
                   "ngày công 0, phải chờ cán bộ xử lý.")
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
        k.in_viec(vn(17, 30))
        k.done()


def kb8():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.luot(vn(7, 0))
        k.luot(vn(19, 30))
        r = k.ket_qua("CN001")
        if r["so_phut_lam"] == 540:
            k.note("2 giờ 30 phút ở lại sau 17:00 vẫn không được ghi nhận ở đâu (chưa có tăng ca); chỉ còn giờ ra 19:30.")
        k.done()


def kb9():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        for t in (vn(7, 0), vn(11, 30), vn(12, 30), vn(17, 0)):
            k.luot(t)
        k.ket_qua("CN001")
        k.done()


def kb10():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.luot(vn(7, 0))
        k.luot(vn(11, 30))
        k.luot(vn(12, 30), KHONG_DAT, thieu=["thieu_mu"])
        k.luot(vn(12, 35))
        k.luot(vn(17, 0))
        k.ket_qua("CN001")
        k.done()


def kb11():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.luot(vn(7, 0))
        k.luot(vn(7, 1))
        k.luot(vn(7, 4))
        k.ket_qua("CN001", now=vn(9, 0))
        k.done()


def kb12():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.luot(vn(7, 0))
        mai = NGAY + timedelta(days=1)
        for now in (vn(20, 0), vn(21, 0), vn(21, 0, 1), vn(21, 30), vn(6, 0, ngay=mai)):
            k.quet_thieu(now)
            k.ket_qua("CN001", NGAY, now)
        print("  (sáng hôm sau)")
        k.luot(vn(7, 0, ngay=mai))
        k.luot(vn(17, 0, ngay=mai))
        k.ket_qua("CN001", mai, vn(18, 0, ngay=mai))
        th = bao_cao.bang_cong_thang(k.s, 2026, 11, ATT, vn(18, 0, ngay=mai))["ds"][0]
        print(f"  → BẢNG CÔNG THÁNG 11: số ngày công {th['so_ngay_cong']} | ngày thiếu giờ ra "
              f"{th['so_ngay_thieu_gio_ra']} | tổng phút {th['tong_phut']}")
        k.in_viec(vn(18, 0, ngay=mai))
        k.done()


def kb13():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.luot(vn(22, 0))
        k.luot(vn(23, 30))
        print(f"  → số dòng attendance: {k.s.scalar(select(func.count(Attendance.id)))}")
        k.done()


def kb14():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        for t in (vn(7, 0), vn(7, 30), vn(8, 0), vn(17, 0)):
            k.luot(t)
        k.ket_qua("CN001")
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
        k.luot(vn(17, 1), KHONG_XAC_DINH)
        k.ket_qua("CN001")
        k.done()


def kb17():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.luot(vn(7, 0))
        k.luot(vn(17, 0), KHONG_CO_NGUOI)
        k.ket_qua("CN001")
        k.done()


def kb18():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.tay_ngay("CN001", NGAY, time(7, 0), None, "Camera cổng hỏng buổi sáng, tổ trưởng xác nhận", now=vn(8, 0))
        k.luot(vn(17, 0))
        k.ket_qua("CN001")
        a = k.bang_cong("CN001", NGAY)
        print(f"  → attendance: ppe_check_id={a.ppe_check_id}, updated_by={a.updated_by}, updated_at={hm(a.updated_at)}")
        k.in_nhat_ky()
        k.done()


def kb19():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.luot(vn(7, 0))
        k.tay_ngay("CN001", NGAY, time(6, 50), None, "Đến từ 06:50, camera nhận chậm", now=vn(9, 0))
        k.tay_ngay("CN001", NGAY, None, time(6, 40), "Thử nhập giờ ra trước giờ vào", now=vn(9, 5))
        k.tay_ngay("CN001", NGAY, None, time(6, 50), "Thử nhập giờ ra bằng giờ vào", now=vn(9, 10))
        k.ket_qua("CN001", now=vn(9, 15))
        k.in_nhat_ky()
        k.done()


def kb20():
    with San() as k:
        an = k.cong_nhan("CN001", "Nguyễn Văn An")
        dk = DangKyMat(SETTINGS, Path(k.tmp.name) / "anh_mau_mat", k.nd)
        k.luot(vn(7, 0))
        n = cong_nhan.cho_nghi_viec(k.s, an, dk, k.admin, now=vn(10, 0))
        print(f"  [02/11 10:00] CHO NGHỈ VIỆC CN001 → status={an.status}, ngày nghỉ việc {an.ngay_nghi_viec:%d/%m}, "
              f"đã xoá {n} mẫu khuôn mặt")
        k.in_trang_thai("CN001", NGAY)
        k.luot(vn(17, 0))
        k.ket_qua("CN001")
        k.ket_qua("CN001", NGAY + timedelta(days=1))
        k.in_nhat_ky()
        if k.in_viec(vn(17, 30)):
            k.note("Ngày cho nghỉ việc lại nằm trong Việc cần xử lý.")
        k.done()


def kb21():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        for d in (date(2026, 11, 1), date(2026, 9, 2)):
            print(f"  ({d:%d/%m/%Y} là {THU[d.weekday()]})")
            k.luot(vn(7, 0, ngay=d))
            k.luot(vn(17, 0, ngay=d))
            k.ket_qua("CN001", d)
        k.note("02/09 (Quốc khánh) vẫn tính như ngày thường: chưa có bảng ngày lễ (Q18, đợt 2). Chủ nhật có cờ "
               "'làm ngày nghỉ'.")
        k.done()


def kb22():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        mai = NGAY + timedelta(days=1)
        k.luot(vn(23, 50))
        k.luot(vn(0, 20, ngay=mai))
        print(f"  → số dòng attendance: {k.s.scalar(select(func.count(Attendance.id)))}")
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
                            res[ten] = k.luot(t, s=s, in_ra=False)["hanh_dong"]
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
                segs = sum(len(r.segments) for r in rows)
                key = (f"A → {res.get('A 07:00:00.0')}, B → {res.get('B 07:00:00.5')} | {len(rows)} dòng attendance, "
                       f"{segs} phiên, {checks} lượt")
                outcomes[key] = outcomes.get(key, 0) + 1
    print(f"  Chạy {lan} lần (mỗi lần CSDL mới), 2 thread bắt đầu cùng lúc (Barrier), mỗi thread 1 session riêng:")
    for key, n in sorted(outcomes.items(), key=lambda kv: -kv[1]):
        print(f"    {n:>2} lần: {key}")
    print("  (Mọi lượt chạy dưới khoá theo công nhân + SELECT ... FOR UPDATE; test T22 chạy cả trên MariaDB.)")
    if any("LỖI" in key or "2 phiên" in key for key in outcomes):
        print("  ! GHI CHÚ: có lần bị lỗi hoặc sinh 2 phiên khi 2 lượt ghi cùng lúc.")


def kb24():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.luot(vn(7, 0))
        k.tay_ngay("CN001", NGAY, None, time(17, 0), "Nhập trước giờ ra cho cả tổ", now=vn(9, 0))
        k.ket_qua("CN001", now=vn(9, 1))
        k.done()


def kb25():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.luot(vn(7, 0))
        k.tay_ngay("CN001", NGAY, None, time(16, 30), "Về sớm có phép, quên quét", now=vn(16, 35))
        k.luot(vn(16, 35))
        ev = k.luot(vn(16, 40))
        k.quet_thieu(vn(21, 1))
        r = k.ket_qua("CN001")
        if ev["hanh_dong"] == "ghi_vao":
            k.note("Giờ ra chấm tay 16:30 được giữ (không bị xoá như trước), nhưng lượt đi ngang camera lúc 16:40 (đủ "
                   f"10 phút, còn trong cửa sổ vào) mở 1 phiên mới → ngày thành '{r['ten_trang_thai']}', ngày công "
                   f"{r['ngay_cong']} cho tới khi cán bộ huỷ phiên đó.")
        k.done()


def kb26():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.cong_nhan("CN002", "Trần Thị Bình")
        k.luot(vn(7, 0))
        k.luot(vn(17, 0))
        k.luot(vn(17, 1))
        k.ket_qua("CN001")
        print("  (biến thể: Bình ra 17:00, 17:01 quay lại nhưng đã tháo mũ)")
        k.luot(vn(7, 0, 30), ma="CN002", in_ra=False)
        k.luot(vn(17, 0, 30), ma="CN002")
        k.luot(vn(17, 1, 30), KHONG_DAT, ma="CN002", thieu=["thieu_mu"])
        k.ket_qua("CN002")
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
        k.ket_qua("CN001", NGAY, vn(18, 0))
        print("  (giờ ca được chép vào dòng công lúc tạo dòng: ngày cũ giữ ca cũ, hôm nay tính lại theo ca mới)")
        if r1["di_muon_phut"] == 0:
            k.note("Sửa ca làm thay đổi số liệu ngày cũ (hôm qua không còn muộn).")
        k.done()


def kb28():
    """Bao cao: tong quan, Viec can xu ly, bang cong thang, file Excel tren 3 ngay du lieu."""
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
        k.tay_ngay("CN002", d2, time(7, 0), time(17, 0), "Quên quét cả ngày", now=vn(18, 0, ngay=d2))
        k.quet_thieu(vn(21, 5, ngay=d2))
        print("  (04/11, hôm nay, xem lúc 10:00) các lượt:")
        k.luot(vn(6, 58, ngay=d3), KHONG_DAT)
        k.luot(vn(7, 0, ngay=d3))
        k.luot(vn(7, 5, ngay=d3), KHONG_DAT, ma="la")
        k.luot(vn(7, 6, ngay=d3), KHONG_XAC_DINH, ma="CN002")
        k.luot(vn(7, 7, ngay=d3), ma="CN002")
        k.luot(vn(9, 0, ngay=d3), KHONG_DAT, thieu=["thieu_mu", "thieu_ao"])
        now = vn(10, 0, ngay=d3)
        tq = bao_cao.tong_quan(k.s, ATT, now)
        gio = {r["gio"]: (r["xanh"], r["do"], r["vang"]) for r in tq["luot_theo_gio"] if r["xanh"] + r["do"] + r["vang"]}
        print(f"  → TỔNG QUAN 04/11 10:00: số công nhân {tq['so_cong_nhan']} | đã vào {tq['da_vao']} | đang có mặt "
              f"{tq['dang_co_mat']} | số lượt {tq['so_luot']} | lượt đạt (đã ghi vào) {tq['luot_dat']} | lượt không "
              f"đạt (màn hình đỏ) {tq['luot_khong_dat']} | tỷ lệ đạt {tq['ty_le_dat']} | việc cần xử lý "
              f"{tq['viec_can_xu_ly']}")
        print(f"    lượt theo giờ (xanh, đỏ, vàng): {gio}")
        k.in_viec(now)
        th = bao_cao.bang_cong_thang(k.s, 2026, 11, ATT, now)
        print("  → BẢNG CÔNG THÁNG 11/2026 (xem 04/11 10:00):")
        for w in th["ds"]:
            tt = " ".join(f"{d}:{w['trang_thai_ngay'][d]}" for d in range(1, 6))
            print(f"    {w['ma']}: ngày công {w['so_ngay_cong']} | tổng phút {w['tong_phut']} | muộn không phép "
                  f"{w['so_lan_muon_khong_phep']} | vắng {w['so_ngay_vang']} | thiếu giờ ra {w['so_ngay_thieu_gio_ra']} "
                  f"| công quy đổi {w['tong_cong_quy_doi']} | ngày 1–5: {tt}")
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(bao_cao.excel_bang_cong_thang(th)))
        ws = wb["Bang cong"]
        hdr = [c.value for c in ws[2]]
        print(f"  → EXCEL sheet 'Bang cong': {len(hdr)} cột = Mã, Họ tên, Tổ đội, 1..{th['so_ngay']}, "
              f"{', '.join(hdr[3 + th['so_ngay']:])}")
        for row in ws.iter_rows(min_row=3, values_only=True):
            print(f"    {row[0]}: ngày 1–4 = {list(row[3:7])} | tổng = {list(row[3 + th['so_ngay']:])}")
        ct = wb["Chi tiet"]
        print(f"  → EXCEL sheet 'Chi tiet': cột {[c.value for c in ct[1]]}")
        for row in ct.iter_rows(min_row=2, values_only=True):
            print(f"    {list(row[:14])}")
        k.done()


def kb29():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        for t in (vn(7, 0), vn(11, 30), vn(14, 0), vn(17, 0)):
            k.luot(t)
        k.ket_qua("CN001")
        k.in_viec(vn(17, 30))
        k.done()


def kb30():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        for t in (vn(7, 0), vn(7, 4), vn(7, 11)):
            k.luot(t)
        r = k.ket_qua("CN001")
        if r["ngay_cong"] == 1 and r["so_phut_lam"] < 60:
            k.note(f"Quét lại lúc 07:11 (đã quá 10 phút) là RA (đúng quy tắc). Ngày đó '{r['ten_trang_thai']}' vẫn được "
                   f"tính ngày công = 1 dù chỉ làm {r['so_phut_lam']} phút (Q10); công quy đổi {r['cong_quy_doi']} "
                   "phản ánh đúng hơn. Có trong Việc cần xử lý sau khi hết ca.")
        k.done()


def kb31():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        for t in (vn(7, 0), vn(17, 0), vn(17, 1), vn(17, 20)):
            k.luot(t)
        k.ket_qua("CN001")
        k.done()


def kb32():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.luot(vn(7, 0))
        k.quet_thieu(vn(21, 0, 0))
        k.quet_thieu(vn(21, 0, 1))
        k.ket_qua("CN001", NGAY, vn(21, 5))
        k.in_viec(vn(21, 5))
        mai = NGAY + timedelta(days=1)
        print("  (sáng hôm sau: vào 07:00; 09:00 cán bộ sửa giờ ra hôm trước thành 17:00)")
        k.luot(vn(7, 0, ngay=mai))
        seg = k.bang_cong("CN001", NGAY).segments[0]
        k.tay("SỬA PHIÊN hôm trước: giờ ra 17:00, lý do \"Tổ trưởng xác nhận\"",
              lambda: sua_phien(k.s, seg, None, time(17, 0), "Tổ trưởng xác nhận", k.admin, ATT, now=vn(9, 0, ngay=mai)),
              vn(9, 0, ngay=mai))
        k.ket_qua("CN001", NGAY, vn(9, 5, ngay=mai))
        k.in_nhat_ky()
        k.in_viec(vn(9, 5, ngay=mai))
        k.done()


def kb33():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.cong_nhan("CN002", "Trần Thị Bình")
        k.tay("THÊM PHÉP CN001: về sớm từ 15:00", lambda: phep.them_phep(
            k.s, k.worker("CN001"), NGAY, "ve_som", "Đi khám bệnh", k.admin, ATT, tu_gio=time(15, 0), now=vn(6, 0)),
            vn(6, 0))
        k.luot(vn(7, 2))
        k.luot(vn(7, 3), ma="CN002")
        k.luot(vn(15, 2))
        k.luot(vn(16, 30), ma="CN002")
        k.ket_qua("CN001", now=vn(17, 30))
        k.ket_qua("CN002", now=vn(17, 30))
        k.in_viec(vn(17, 30))
        k.tay("THÊM PHÉP CN002 (sau): về sớm từ 16:30", lambda: phep.them_phep(
            k.s, k.worker("CN002"), NGAY, "ve_som", "Tổ trưởng cho về", k.admin, ATT, tu_gio=time(16, 30),
            now=vn(17, 40)), vn(17, 40))
        k.ket_qua("CN002", now=vn(17, 45))
        k.in_viec(vn(17, 45))
        k.done()


def kb34():
    with San() as k:
        k.cong_nhan("CN001", "Nguyễn Văn An")
        k.tay("THÊM PHÉP: ra ngoài công việc 09:00–11:00 (tính công)", lambda: phep.them_phep(
            k.s, k.worker("CN001"), NGAY, "ra_ngoai_cong_viec", "Đi mua vật tư", k.admin, ATT, tu_gio=time(9, 0),
            den_gio=time(11, 0), now=vn(6, 0)), vn(6, 0))
        for t in (vn(7, 0), vn(9, 0), vn(11, 0), vn(17, 0)):
            k.luot(t)
        k.ket_qua("CN001")
        k.done()


KICH_BAN = [
    (1, "Vào 06:55 đạt, ra 17:00 (T1)", kb1),
    (2, "Vào 07:04 (trong ân hạn), ra 17:00 (T2) — thêm: người thứ hai vào 07:05:59 (T3)", kb2),
    (3, "Vào 07:06, ra 17:00 (T4)", kb3),
    (4, "07:02 không đạt (thiếu mũ), 07:10 đạt, ra 17:00 (T5)", kb4),
    (5, "Vào 05:30 (sớm hơn cửa sổ cho vào sớm), ra 17:00 (T6)", kb5),
    (6, "Vào 06:10 (trong cửa sổ cho vào sớm), ra 17:00", kb6),
    (7, "Vào 07:00, ra 16:30 (về sớm) (T7)", kb7),
    (8, "Vào 07:00, ra 19:30 (ở lại muộn, không có ca tăng ca) (T8)", kb8),
    (9, "Vào 07:00, ra 11:30, vào lại 12:30 (đạt), ra 17:00 (T9)", kb9),
    (10, "Như #9 nhưng vào lại 12:30 KHÔNG ĐẠT, 12:35 đạt", kb10),
    (11, "Vào 07:00, quét lại 07:01, quét 07:04", kb11),
    (12, "Vào 07:00, không quét ra; tác vụ nền lúc 20:00, 21:00, 21:00:01, 21:30, sáng hôm sau; hôm sau vào 07:00", kb12),
    (13, "Vào 22:00, ra 23:30 (ngoài khung ca) (T15)", kb13),
    (14, "Vào 07:00, ra 07:30, vào 08:00, ra 17:00 (T11)", kb14),
    (15, "Người lạ (không nhận ra) đạt bảo hộ (T16)", kb15),
    (16, "Nhận ra đúng người nhưng NHIEU_NGUOI, rồi KHONG_XAC_DINH (T16)", kb16),
    (17, "Lượt ra với kết quả KHONG_CO_NGUOI (T16)", kb17),
    (18, "Chấm tay giờ vào 07:00 khi chưa có bản ghi, sau đó quét tự động ra 17:00 (T17)", kb18),
    (19, "Đã quét vào 07:00, chấm tay sửa giờ vào 06:50; rồi sửa giờ ra trước giờ vào / bằng giờ vào (T18, T19)", kb19),
    (20, "Cho nghỉ việc lúc 10:00 khi đang có mặt, rồi quét ra 17:00 (T20)", kb20),
    (21, "Quét vào ngày Chủ nhật và ngày 02/09 (Quốc khánh)", kb21),
    (22, "Vào 23:50, ra 00:20 hôm sau (qua nửa đêm) (T15)", kb22),
    (23, "Hai lượt của cùng một người cách nhau 0,5 giây, gọi song song từ 2 thread (T22)", kb23),
    (24, "Chấm tay giờ ra 17:00 lúc 09:00 cùng ngày (T18)", kb24),
    (25, "Chấm tay giờ ra 16:30, sau đó công nhân đi ngang camera 16:35 và 16:40", kb25),
    (26, "Ra 17:00 rồi 17:01 quay lại đứng trước camera", kb26),
    (27, "Sửa giờ bắt đầu ca giữa ngày (07:00 → 07:30)", kb27),
    (28, "Báo cáo: tổng quan, Việc cần xử lý, bảng công tháng, Excel trên 3 ngày dữ liệu (T24, T25)", kb28),
    (29, "Ra ăn trưa 11:30, 14:00 mới vào lại (T10)", kb29),
    (30, "(v2) Vào 07:00, quét lại 07:04 và 07:11 (T12)", kb30),
    (31, "(v2) Ra 17:00, quét lại 17:01 và 17:20 (T13)", kb31),
    (32, "(v2) Thiếu giờ ra được lưu, hôm sau cán bộ sửa (T14)", kb32),
    (33, "(v2) Phép về sớm có trước / thêm sau (P1, P3)", kb33),
    (34, "(v2) Phép ra ngoài công việc 09:00–11:00 tính công (P5)", kb34),
]


def main(argv: list[str]) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    chon = {int(a) for a in argv}
    d = ATT["default_shift"]
    print(f"Ca: {d['name']} {d['start']}–{d['end']}, nghỉ {d['break_start']} ({d['break_minutes']} phút), ân hạn "
          f"{d['grace_minutes']} phút, cho vào sớm {d['early_checkin_minutes']} phút, chống quét trùng "
          f"{d['phut_chong_trung']} phút | missing_checkout_hours {ATT['missing_checkout_hours']} | "
          f"nghỉ tuần {ATT['ngay_nghi_tuan']} | {ATT['timezone']}")
    print(f"Ngày chính: {NGAY:%d/%m/%Y} ({THU[NGAY.weekday()]}). Cột: [thời điểm] người đứng trước camera | kết quả "
          "bảo hộ | kết quả nhận diện | hướng | hành động | màu + câu trên màn hình cổng; ↳ = dòng công sau lượt.")
    print(f"Trạng thái ngày: {', '.join(f'{k} = {v}' for k, v in TEN_TRANG_THAI.items())}")
    for so, tieu_de, fn in KICH_BAN:
        if chon and so not in chon:
            continue
        print(f"\n=== #{so}. {tieu_de} ===")
        fn()


if __name__ == "__main__":
    main(sys.argv[1:])
