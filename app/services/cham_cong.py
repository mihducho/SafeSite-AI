"""Cham cong v2 (docs/LOGIC_CHAM_CONG.md, DE_TAI.md muc 7). CSDL luu gio UTC; ngay cong va gio ca tinh theo
attendance.timezone (Asia/Ho_Chi_Minh).

Phien (attendance_segments): moi lan VAO mo 1 phien, moi lan RA dong phien dang mo; vao lai KHONG xoa gio ra cu.
attendance (1 dong / cong nhan / ngay) la bang TONG HOP, tinh lai tu cac phien bang tinh_cong.tong_hop (ham thuan)
moi khi phien hoac phep cua ngay do thay doi (tinh_lai_ngay).
  - Huong: ngay cong cua luot co phien "mo" -> RA; khong co -> VAO. Phien mo cua ngay khac khong anh huong.
  - VAO: nhan ra mat + bao ho DAT + cong nhan dang lam, da dong y + thoi diem trong [bat dau - vao som, ket thuc]
    (ca 2 bien). Ngoai cua so: khong ghi, ly do ngoai_gio_vao.
  - RA: nhan ra mat + ket qua khac NHIEU_NGUOI (khong xet bao ho, KHONG_CO_NGUOI van ghi ra).
  - Chong trung 2 chieu: tu moc ghi cong gan nhat trong ngay (gio vao hoac gio ra cua 1 phien, tu dong hoac tay) toi
    luc nay chua du shifts.phut_chong_trung phut -> bo_qua_trung.
  - Thieu gio ra: tac vu nen danh_dau_thieu_gio_ra LUU phien mo qua ket thuc ca + missing_checkout_hours.
  - Cham tay theo phien: them / sua gio vao, gio ra / huy; bat buoc ly do; moi thao tac 1 dong nhat_ky_cham_cong.
  - Ghi dong thoi: moi luot va moi thao tac tay chay duoi khoa_cong_nhan (khoa trong tien trinh + SELECT ... FOR UPDATE
    dong workers neu CSDL ho tro). Loi IntegrityError: xu_ly_luot rollback, doc lai, thu lai 1 lan.
"""
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import utcnow
from app.models import DANG_LAM, Attendance, AttendanceSegment, NhatKyChamCong, Phep, PpeCheck, Shift, User, Worker
from app.services import tinh_cong as tc
from app.services.tinh_cong import DONG, HUY, MO, THIEU_GIO_RA, THU_CONG, TU_DONG, GioCa, PhepNgay, Phien, TongHopNgay
from src.checkpoint.evaluate import DAT, NHIEU_NGUOI

VAO, RA = "vao", "ra"
GHI_VAO, GHI_RA, KHONG_GHI, BO_QUA_TRUNG = "ghi_vao", "ghi_ra", "khong_ghi", "bo_qua_trung"
BINH_THUONG, NGOAI_CA, CHAM_THU_CONG = "binh_thuong", "ngoai_ca", "cham_thu_cong"  # ngoai_ca: chi con de tuong thich
NGOAI_GIO_VAO = "ngoai_gio_vao"
# nhat ky
THEM_PHIEN, SUA_VAO, SUA_RA, HUY_PHIEN = "them_phien", "sua_vao", "sua_ra", "huy_phien"
DONG_KHI_NGHI_VIEC, XAC_NHAN_KHONG_PHEP = "dong_khi_nghi_viec", "xac_nhan_khong_phep"
TRONG = "(trống)"


class ChamCongError(ValueError):
    pass


# --- thoi gian ---
def mui_gio(att_cfg: dict) -> ZoneInfo:
    return ZoneInfo(att_cfg["timezone"])


def ngay_cong(t: datetime, tz: ZoneInfo) -> date:
    """Ngay theo gio Viet Nam (vd 23:30 UTC ngay 28 = 06:30 ngay 29 o Viet Nam)."""
    return t.astimezone(tz).date()


def khoang_ngay(ngay: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    """[0h, 24h) cua 1 ngay theo gio Viet Nam, de loc luot kiem tra luu bang UTC."""
    start = datetime.combine(ngay, time(0), tzinfo=tz)
    return start, start + timedelta(days=1)


def gio_phut(t: datetime | None, tz: ZoneInfo) -> str | None:
    return t.astimezone(tz).strftime("%H:%M") if t else None


def _gio(t: datetime | None, tz: ZoneInfo) -> str:
    """Gio:phut:giay de ghi nhat ky (rong -> "(trống)")."""
    return t.astimezone(tz).strftime("%H:%M:%S") if t else TRONG


def _khoang(vao: datetime, ra: datetime | None, tz: ZoneInfo) -> str:
    return f"{_gio(vao, tz)}–{_gio(ra, tz)}"


_phut = tc.phut_xuong  # giu ten cu (scripts/kich_ban_cham_cong.py ban dau)


# --- ca lam ---
def ca_mac_dinh(db: Session) -> Shift:
    shift = db.scalar(select(Shift).order_by(Shift.id).limit(1))
    if shift is None:
        raise ChamCongError("Chưa có ca làm trong CSDL: chạy scripts\\seed_demo.py")
    return shift


def moc_ca(shift: Shift, ngay: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    start = datetime.combine(ngay, shift.start_time, tzinfo=tz)
    end = datetime.combine(ngay, shift.end_time, tzinfo=tz)
    if end <= start:  # ca qua dem (chua ho tro: sua_ca va seed_demo deu chan)
        end += timedelta(days=1)
    return start, end


def moc_nghi(shift: Shift, ngay: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    start = datetime.combine(ngay, shift.break_start, tzinfo=tz)
    return start, start + timedelta(minutes=shift.break_minutes)


def gio_ca(shift: Shift, ngay: date, tz: ZoneInfo) -> GioCa:
    start, end = moc_ca(shift, ngay, tz)
    return GioCa(start, end, *moc_nghi(shift, ngay, tz), an_han=shift.grace_minutes, vao_som=shift.early_checkin_minutes)


def trong_khung_vao(shift: Shift, t: datetime, ngay: date, tz: ZoneInfo) -> bool:
    """t trong [bat dau - cho vao som, ket thuc], tinh ca 2 bien, chinh xac toi giay."""
    ca = gio_ca(shift, ngay, tz)
    return ca.mo_cua_vao <= t <= ca.ket_thuc


def khoang_lam_viec(worker: Worker, tz: ZoneInfo) -> tuple[date | None, date | None]:
    """[ngay vao lam, ngay nghi viec]; chua dat ngay vao lam -> ngay tao cong nhan (gio Viet Nam)."""
    start = worker.ngay_vao_lam or (worker.created_at.astimezone(tz).date() if worker.created_at else None)
    return start, worker.ngay_nghi_viec


# --- khoa theo cong nhan (Q15) ---
_KHOA_CHUNG = threading.Lock()
_KHOA: dict[int, threading.RLock] = {}


@contextmanager
def khoa_cong_nhan(db: Session, worker_id: int):
    """Moi thay doi bang cong cua 1 cong nhan chay lan luot: khoa trong tien trinh (thread cong, API cham tay, tac vu
    nen) + SELECT ... FOR UPDATE dong workers (MariaDB / PostgreSQL; SQLite bo qua) cho nhieu tien trinh.
    Ket thuc giao dich cu truoc khi khoa va doc lai moi doi tuong sau khi khoa: MariaDB (REPEATABLE READ) chi thay du
    lieu moi nhat neu lan doc dau tien cua giao dich dien ra SAU khi da giu khoa. Loi -> rollback roi bao tiep."""
    db.commit()
    with _KHOA_CHUNG:
        lock = _KHOA.setdefault(worker_id, threading.RLock())
    with lock:
        db.expire_all()
        try:
            db.execute(select(Worker.id).where(Worker.id == worker_id).with_for_update())
            yield
        except BaseException:
            db.rollback()
            raise


# --- doc du lieu ---
def tim_bang_cong(db: Session, worker_id: int, ngay: date, shift_id: int) -> Attendance | None:
    return db.scalar(select(Attendance).where(Attendance.worker_id == worker_id, Attendance.work_date == ngay,
                                              Attendance.shift_id == shift_id))


def cac_phien(att: Attendance | None) -> list[AttendanceSegment]:
    """Cac phien con hieu luc (khong tinh phien huy) cua 1 ngay, theo gio vao."""
    return [] if att is None else sorted((s for s in att.segments if s.trang_thai != HUY), key=lambda s: s.vao_at)


def moc_gan_nhat(segs: list[AttendanceSegment]) -> tuple[datetime, str] | None:
    """Lan ghi cong gan nhat trong ngay: (thoi diem, "vao" / "ra")."""
    moc = [(s.vao_at, VAO) for s in segs] + [(s.ra_at, RA) for s in segs if s.ra_at is not None]
    return max(moc, key=lambda m: m[0]) if moc else None


def phep_ngay(p: Phep, tz: ZoneInfo) -> PhepNgay:
    tu = datetime.combine(p.ngay, p.tu_gio, tzinfo=tz) if p.tu_gio else None
    den = datetime.combine(p.ngay, p.den_gio, tzinfo=tz) if p.den_gio else None
    return PhepNgay(p.loai, tu, den, p.tinh_cong)


def phep_cua_ngay(db: Session, worker_id: int, ngay: date) -> list[Phep]:
    return db.scalars(select(Phep).where(Phep.worker_id == worker_id, Phep.ngay == ngay, Phep.trang_thai == "da_duyet")
                      .order_by(Phep.id)).all()


def tinh_tu_du_lieu(worker: Worker, ngay: date, att: Attendance | None, segs: list[AttendanceSegment],
                    pheps: list[Phep], shift: Shift, att_cfg: dict, now: datetime) -> TongHopNgay:
    """Tong hop 1 ngay tu du lieu da doc (segs: moi phien cua ngay, ke ca phien huy). Dung chung cho ghi va bao cao."""
    tz = mui_gio(att_cfg)
    vao_lam, nghi = khoang_lam_viec(worker, tz)
    return tc.tong_hop(
        ngay, gio_ca(shift, ngay, tz), [Phien(s.vao_at, s.ra_at, s.trang_thai, s.nguon_vao, s.nguon_ra) for s in segs],
        [phep_ngay(p, tz) for p in pheps], now=now, ngay_vao_lam=vao_lam, ngay_nghi_viec=nghi,
        nghi_tuan=tc.nghi_tuan_tu_cau_hinh(att_cfg), dung_sai_phut=att_cfg["dung_sai_phep_phut"],
        nguong_phut=att_cfg["nguong_can_giai_trinh_phut"], da_xac_nhan_khong_phep=bool(att and att.da_xac_nhan_khong_phep))


def tong_hop_ngay(db: Session, worker: Worker, ngay: date, att: Attendance | None, att_cfg: dict,
                  now: datetime | None = None, shift: Shift | None = None) -> TongHopNgay:
    shift = shift or (att.shift if att is not None else ca_mac_dinh(db))
    segs = list(att.segments) if att is not None else []
    return tinh_tu_du_lieu(worker, ngay, att, segs, phep_cua_ngay(db, worker.id, ngay), shift, att_cfg, now or utcnow())


def tinh_lai_ngay(db: Session, att: Attendance, att_cfg: dict, now: datetime | None = None) -> TongHopNgay:
    """Tinh lai dong tong hop cua 1 ngay tu cac phien + phep (sau moi thay doi). Chua commit."""
    th = tong_hop_ngay(db, att.worker, att.work_date, att, att_cfg, now)
    att.check_in, att.check_out = th.check_in, th.check_out
    att.late_minutes, att.early_leave_minutes, att.worked_minutes = th.late_minutes, th.early_leave_minutes, \
        th.worked_minutes
    att.so_lan_ra_ngoai, att.phut_ra_ngoai, att.phut_cong_tac = th.so_lan_ra_ngoai, th.phut_ra_ngoai, th.phut_cong_tac
    att.status = CHAM_THU_CONG if th.co_sua_tay else BINH_THUONG
    first = cac_phien(att)[:1]
    att.ppe_check_id = first[0].vao_check_id if first else None
    return th


def _tao_bang_cong(db: Session, worker: Worker, ngay: date, shift: Shift) -> Attendance:
    att = Attendance(worker=worker, work_date=ngay, shift=shift, status=BINH_THUONG)
    db.add(att)
    return att


# --- cham cong tu dong (luot o cong) ---
@dataclass
class KetQuaChamCong:
    huong: str | None             # vao / ra / None (khong xet)
    hanh_dong: str                # ghi_vao / ghi_ra / khong_ghi / bo_qua_trung
    bang_cong: Attendance | None = None
    vao_lai: bool = False         # ghi_vao phien thu 2 tro di trong ngay
    moc: datetime | None = None   # bo_qua_trung: lan ghi cong gan nhat; ngoai_gio_vao (som): gio mo cua vao
    moc_huong: str | None = None  # bo_qua_trung: lan gan nhat la vao hay ra
    ly_do: str | None = None      # khong_ghi: ngoai_gio_vao / chua_du_dieu_kien
    som_qua: bool = False         # ngoai_gio_vao: True = chua den gio vao, False = da het gio vao
    tong_hop: TongHopNgay | None = None
    nhac_ve_som: bool = False     # ghi_ra: ve som KHONG phep qua nguong (khong phai ra nghi trua / cong tac co phep)


def cham_cong_tu_dong(db: Session, worker: Worker, ket_qua: str, t: datetime, ppe_check: PpeCheck,
                      att_cfg: dict) -> KetQuaChamCong:
    """Goi khi da NHAN RA cong nhan, DUOI khoa_cong_nhan. ket_qua: ket qua cua luot (sau luat nhieu_mat). Chua commit."""
    if ket_qua == NHIEU_NGUOI:
        return KetQuaChamCong(None, KHONG_GHI)
    tz, shift = mui_gio(att_cfg), ca_mac_dinh(db)
    ngay = ngay_cong(t, tz)
    att = tim_bang_cong(db, worker.id, ngay, shift.id)
    segs = cac_phien(att)
    mo = next((s for s in segs if s.trang_thai == MO), None)
    huong = RA if mo is not None else VAO
    moc = moc_gan_nhat(segs)
    if moc is not None and t - moc[0] < timedelta(minutes=shift.phut_chong_trung):
        return KetQuaChamCong(huong, BO_QUA_TRUNG, att, moc=moc[0], moc_huong=moc[1])

    if mo is not None:  # RA: dong phien dang mo
        mo.ra_at, mo.ra_check_id, mo.nguon_ra, mo.trang_thai = t, ppe_check.id, TU_DONG, DONG
        th = tinh_lai_ngay(db, att, att_cfg, t)
        ca = gio_ca(shift, ngay, tz)
        dung_sai = timedelta(minutes=att_cfg["dung_sai_phep_phut"])
        ra_nghi = ca.nghi_tu - dung_sai <= t <= ca.nghi_den
        cong_tac = any(p.loai == tc.RA_NGOAI_CONG_VIEC and p.tu and p.den and p.tu - dung_sai <= t <= p.den
                       for p in (phep_ngay(p, tz) for p in phep_cua_ngay(db, worker.id, ngay)))
        nhac = th.early_leave_minutes > att_cfg["nguong_can_giai_trinh_phut"] and not th.som_co_phep \
            and not ra_nghi and not cong_tac
        return KetQuaChamCong(RA, GHI_RA, att, tong_hop=th, nhac_ve_som=nhac)

    ca = gio_ca(shift, ngay, tz)
    if t < ca.mo_cua_vao or t > ca.ket_thuc:
        return KetQuaChamCong(VAO, KHONG_GHI, att, ly_do=NGOAI_GIO_VAO, som_qua=t < ca.mo_cua_vao, moc=ca.mo_cua_vao)
    if ket_qua != DAT:
        return KetQuaChamCong(VAO, KHONG_GHI, att)
    if worker.status != DANG_LAM or worker.consent_at is None:  # da loc o nhan dien (Q13); giu de chac chan
        return KetQuaChamCong(VAO, KHONG_GHI, att, ly_do="chua_du_dieu_kien")
    att = att or _tao_bang_cong(db, worker, ngay, shift)
    att.segments.append(AttendanceSegment(worker_id=worker.id, vao_at=t, vao_check_id=ppe_check.id, nguon_vao=TU_DONG,
                                          trang_thai=MO))
    th = tinh_lai_ngay(db, att, att_cfg, t)
    return KetQuaChamCong(VAO, GHI_VAO, att, vao_lai=bool(segs), tong_hop=th)


# --- thieu gio ra (Q9): tac vu nen ---
def danh_dau_thieu_gio_ra(db: Session, att_cfg: dict, now: datetime | None = None) -> int:
    """LUU phien "mo" qua (ket thuc ca + missing_checkout_hours) thanh "thieu_gio_ra" (lon hon han). Chay lai nhieu lan
    khong sai (phien da danh dau khong con "mo"). Tra ve so phien vua danh dau."""
    now, tz = now or utcnow(), mui_gio(att_cfg)
    han = timedelta(hours=att_cfg["missing_checkout_hours"])

    def qua_han(att: Attendance) -> bool:
        return now > moc_ca(att.shift, att.work_date, tz)[1] + han

    rows = db.execute(select(AttendanceSegment.worker_id, Attendance)
                      .join(Attendance, AttendanceSegment.attendance_id == Attendance.id)
                      .where(AttendanceSegment.trang_thai == MO)).all()
    n = 0
    for wid in sorted({wid for wid, att in rows if qua_han(att)}):
        with khoa_cong_nhan(db, wid):
            segs = db.scalars(select(AttendanceSegment).where(AttendanceSegment.worker_id == wid,
                                                              AttendanceSegment.trang_thai == MO)).all()
            touched = {}
            for s in segs:
                if qua_han(s.attendance):
                    s.trang_thai = THIEU_GIO_RA
                    touched[s.attendance_id] = s.attendance
                    n += 1
            for att in touched.values():
                tinh_lai_ngay(db, att, att_cfg, now)
            db.commit()
    return n


# --- nhat ky ---
def ghi_nhat_ky(db: Session, worker_id: int, ngay: date, hanh_dong: str, *, att: Attendance | None = None,
                seg: AttendanceSegment | None = None, phep: Phep | None = None, cu: str | None = None,
                moi: str | None = None, ly_do: str | None = None, user: User | None = None,
                now: datetime | None = None) -> NhatKyChamCong:
    db.flush()  # lay id cua dong cong / phien / phep vua tao
    nk = NhatKyChamCong(worker_id=worker_id, ngay=ngay, attendance_id=att.id if att else None,
                        segment_id=seg.id if seg else None, phep_id=phep.id if phep else None, hanh_dong=hanh_dong,
                        gia_tri_cu=cu, gia_tri_moi=moi, ly_do=ly_do, user_id=user.id if user else None,
                        thoi_diem=now or utcnow())
    db.add(nk)
    return nk


def _ly_do(ly_do: str | None) -> str:
    ly_do = (ly_do or "").strip()
    if not ly_do:
        raise ChamCongError("Bắt buộc ghi lý do khi chấm công thủ công")
    return ly_do


def _danh_dau_sua_tay(att: Attendance, user: User, now: datetime, ly_do: str, tz: ZoneInfo) -> None:
    line = f"{gio_phut(now, tz)} {now.astimezone(tz):%d/%m} {user.username}: {ly_do}"
    att.note = f"{att.note}\n{line}" if att.note else line  # tom tat; day du o nhat_ky_cham_cong
    att.updated_by, att.updated_at = user.id, now


def _kiem_tra_ngay_lam(worker: Worker, ngay: date, tz: ZoneInfo) -> None:
    start, end = khoang_lam_viec(worker, tz)
    if (start and ngay < start) or (end and ngay > end):
        khoang = f"từ {start:%d/%m/%Y}" + (f" đến {end:%d/%m/%Y}" if end else "")
        raise ChamCongError(f"Ngày {ngay:%d/%m/%Y} nằm ngoài thời gian làm việc của công nhân ({khoang})")


def _kiem_tra_thoi_diem(t: datetime, now: datetime, tz: ZoneInfo) -> None:
    if t > now:
        raise ChamCongError(f"Không chấm công cho thời điểm chưa tới ({t.astimezone(tz):%H:%M %d/%m/%Y})")


def _kiem_tra_chong_lan(vao: datetime, ra: datetime | None, others: list[AttendanceSegment], tz: ZoneInfo) -> None:
    """Phien [vao, ra] khong duoc chong len phien khac (phien chua co gio ra: keo dai mai)."""
    end = ra or datetime.max.replace(tzinfo=tz)
    for o in others:
        o_end = o.ra_at or datetime.max.replace(tzinfo=tz)
        if vao < o_end and o.vao_at < end:
            raise ChamCongError(f"Phiên {_khoang(vao, ra, tz)} chồng lên phiên {_khoang(o.vao_at, o.ra_at, tz)}")


def _luc(ngay: date, gio: time, tz: ZoneInfo) -> datetime:
    return datetime.combine(ngay, gio, tzinfo=tz)


# --- cham cong thu cong theo phien (Q11) ---
def _them_phien(db: Session, worker: Worker, ngay: date, gio_vao: time | None, gio_ra: time | None, ly_do: str,
                user: User, att_cfg: dict, now: datetime) -> AttendanceSegment:
    tz, shift = mui_gio(att_cfg), ca_mac_dinh(db)
    _kiem_tra_ngay_lam(worker, ngay, tz)
    if gio_vao is None:
        raise ChamCongError("Chưa có giờ vào: nhập giờ vào trước")
    vao = _luc(ngay, gio_vao, tz)
    ra = _luc(ngay, gio_ra, tz) if gio_ra is not None else None
    _kiem_tra_thoi_diem(vao, now, tz)
    if ra is not None:
        _kiem_tra_thoi_diem(ra, now, tz)
        if ra <= vao:
            raise ChamCongError("Giờ ra phải sau giờ vào")
    att = tim_bang_cong(db, worker.id, ngay, shift.id)
    others = cac_phien(att)
    mo = next((s for s in others if s.trang_thai == MO), None)
    if ra is None and mo is not None:
        raise ChamCongError(f"Đã có phiên đang mở (vào {_gio(mo.vao_at, tz)}): đóng phiên đó trước")
    _kiem_tra_chong_lan(vao, ra, others, tz)
    att = att or _tao_bang_cong(db, worker, ngay, shift)
    seg = AttendanceSegment(worker_id=worker.id, vao_at=vao, ra_at=ra, nguon_vao=THU_CONG,
                            nguon_ra=THU_CONG if ra else None, trang_thai=DONG if ra else MO)
    att.segments.append(seg)
    ghi_nhat_ky(db, worker.id, ngay, THEM_PHIEN, att=att, seg=seg, moi=_khoang(vao, ra, tz), ly_do=ly_do, user=user,
                now=now)
    _danh_dau_sua_tay(att, user, now, ly_do, tz)
    tinh_lai_ngay(db, att, att_cfg, now)
    return seg


def _sua_phien(db: Session, seg: AttendanceSegment, gio_vao: time | None, gio_ra: time | None, ly_do: str, user: User,
               att_cfg: dict, now: datetime) -> AttendanceSegment:
    tz = mui_gio(att_cfg)
    if seg.trang_thai == HUY:
        raise ChamCongError("Phiên này đã huỷ, không sửa được")
    if gio_vao is None and gio_ra is None:
        raise ChamCongError("Cần nhập giờ vào hoặc giờ ra")
    att = seg.attendance
    _kiem_tra_ngay_lam(att.worker, att.work_date, tz)
    vao = _luc(att.work_date, gio_vao, tz) if gio_vao is not None else seg.vao_at
    ra = _luc(att.work_date, gio_ra, tz) if gio_ra is not None else seg.ra_at
    if gio_vao is not None:
        _kiem_tra_thoi_diem(vao, now, tz)
    if gio_ra is not None:
        _kiem_tra_thoi_diem(ra, now, tz)
    if ra is not None and ra <= vao:
        raise ChamCongError("Giờ ra phải sau giờ vào")
    _kiem_tra_chong_lan(vao, ra, [s for s in cac_phien(att) if s.id != seg.id], tz)
    changed = False
    if gio_vao is not None and vao != seg.vao_at:
        ghi_nhat_ky(db, att.worker_id, att.work_date, SUA_VAO, att=att, seg=seg, cu=_gio(seg.vao_at, tz),
                    moi=_gio(vao, tz), ly_do=ly_do, user=user, now=now)
        seg.vao_at, seg.nguon_vao, changed = vao, THU_CONG, True
    if gio_ra is not None and (ra != seg.ra_at or seg.trang_thai != DONG):
        cu = _gio(seg.ra_at, tz) if seg.ra_at else ("(thiếu giờ ra)" if seg.trang_thai == THIEU_GIO_RA else TRONG)
        ghi_nhat_ky(db, att.worker_id, att.work_date, SUA_RA, att=att, seg=seg, cu=cu, moi=_gio(ra, tz), ly_do=ly_do,
                    user=user, now=now)
        seg.ra_at, seg.nguon_ra, seg.trang_thai, changed = ra, THU_CONG, DONG, True
    if not changed:
        raise ChamCongError("Giờ nhập giống giờ đang có, không có gì để sửa")
    _danh_dau_sua_tay(att, user, now, ly_do, tz)
    tinh_lai_ngay(db, att, att_cfg, now)
    return seg


def them_phien(db: Session, worker: Worker, ngay: date, gio_vao: time | None, gio_ra: time | None, ly_do: str,
               user: User, att_cfg: dict, now: datetime | None = None) -> AttendanceSegment:
    """Them 1 phien (gio ra co the trong = phien dang mo). Tu choi: thoi diem chua toi, ra <= vao, chong lan phien
    khac, ngoai [ngay vao lam, ngay nghi viec], da co phien mo ma them phien mo nua."""
    ly_do = _ly_do(ly_do)
    with khoa_cong_nhan(db, worker.id):
        seg = _them_phien(db, worker, ngay, gio_vao, gio_ra, ly_do, user, att_cfg, now or utcnow())
        db.commit()
    return seg


def sua_phien(db: Session, seg: AttendanceSegment, gio_vao: time | None, gio_ra: time | None, ly_do: str,
              user: User, att_cfg: dict, now: datetime | None = None) -> AttendanceSegment:
    """Sua gio vao / gio ra cua 1 phien (ke ca dong phien thieu gio ra). Moi thay doi 1 dong nhat ky (cu, moi)."""
    ly_do = _ly_do(ly_do)
    with khoa_cong_nhan(db, seg.worker_id):
        seg = _sua_phien(db, seg, gio_vao, gio_ra, ly_do, user, att_cfg, now or utcnow())
        db.commit()
    return seg


def huy_phien(db: Session, seg: AttendanceSegment, ly_do: str, user: User, att_cfg: dict,
              now: datetime | None = None) -> AttendanceSegment:
    ly_do, now, tz = _ly_do(ly_do), now or utcnow(), mui_gio(att_cfg)
    with khoa_cong_nhan(db, seg.worker_id):
        if seg.trang_thai == HUY:
            raise ChamCongError("Phiên này đã huỷ")
        att = seg.attendance
        ghi_nhat_ky(db, att.worker_id, att.work_date, HUY_PHIEN, att=att, seg=seg, cu=_khoang(seg.vao_at, seg.ra_at, tz),
                    moi="(huỷ)", ly_do=ly_do, user=user, now=now)
        seg.trang_thai = HUY
        _danh_dau_sua_tay(att, user, now, ly_do, tz)
        tinh_lai_ngay(db, att, att_cfg, now)
        db.commit()
    return seg


def cham_thu_cong(db: Session, worker: Worker, ngay: date, gio_vao: time | None, gio_ra: time | None, ly_do: str,
                  user: User, att_cfg: dict, now: datetime | None = None) -> Attendance:
    """API cu (POST /api/cham-cong-thu-cong): them / sua gio vao, gio ra CUA NGAY. Ngay chua co phien -> them 1 phien;
    da co -> gio vao sua phien DAU, gio ra sua (hoac dong) phien CUOI. Cung kiem tra va nhat ky nhu thao tac theo phien."""
    ly_do, now = _ly_do(ly_do), now or utcnow()
    if gio_vao is None and gio_ra is None:
        raise ChamCongError("Cần nhập giờ vào hoặc giờ ra")
    with khoa_cong_nhan(db, worker.id):
        shift = ca_mac_dinh(db)
        segs = cac_phien(tim_bang_cong(db, worker.id, ngay, shift.id))
        if not segs:
            _them_phien(db, worker, ngay, gio_vao, gio_ra, ly_do, user, att_cfg, now)
        else:
            if gio_vao is not None:
                _sua_phien(db, segs[0], gio_vao, None, ly_do, user, att_cfg, now)
            if gio_ra is not None:
                _sua_phien(db, cac_phien(segs[0].attendance)[-1], None, gio_ra, ly_do, user, att_cfg, now)
        db.commit()
    return tim_bang_cong(db, worker.id, ngay, shift.id)


def dong_phien_khi_nghi_viec(db: Session, worker: Worker, user: User | None, att_cfg: dict, now: datetime) -> int:
    """Q12, goi DUOI khoa_cong_nhan: dong moi phien dang mo tai thoi diem cho nghi viec (nguon tay, nhat ky)."""
    tz = mui_gio(att_cfg)
    segs = db.scalars(select(AttendanceSegment).where(AttendanceSegment.worker_id == worker.id,
                                                      AttendanceSegment.trang_thai == MO)).all()
    for s in segs:
        ra = max(now, s.vao_at)
        ghi_nhat_ky(db, worker.id, s.attendance.work_date, DONG_KHI_NGHI_VIEC, att=s.attendance, seg=s, cu=TRONG,
                    moi=_gio(ra, tz), ly_do="Cho nghỉ việc", user=user, now=now)
        s.ra_at, s.nguon_ra, s.trang_thai = ra, THU_CONG, DONG
        tinh_lai_ngay(db, s.attendance, att_cfg, now)
    return len(segs)


def xac_nhan_khong_phep(db: Session, att: Attendance, ly_do: str | None, user: User, att_cfg: dict,
                        now: datetime | None = None) -> Attendance:
    """Q21: can bo xac nhan ngay di muon / ve som la KHONG co phep -> roi khoi danh sach Viec can xu ly (co nhat ky)."""
    now = now or utcnow()
    with khoa_cong_nhan(db, att.worker_id):
        att.da_xac_nhan_khong_phep = True
        ghi_nhat_ky(db, att.worker_id, att.work_date, XAC_NHAN_KHONG_PHEP, att=att,
                    moi=f"muộn {att.late_minutes} phút, về sớm {att.early_leave_minutes} phút",
                    ly_do=(ly_do or "").strip() or "Xác nhận không phép", user=user, now=now)
        db.commit()
    return att


# --- sua ca lam (trang Cau hinh ca) ---
SHIFT_FIELDS = ("name", "start_time", "end_time", "break_start", "break_minutes", "grace_minutes", "early_checkin_minutes",
                "phut_chong_trung")


def sua_ca(db: Session, shift: Shift, data: dict, att_cfg: dict, now: datetime | None = None) -> int:
    """Sua ca (ban demo: 1 ca, khong qua dem). Kiem tra hop le roi tinh lai bang cong HOM NAY theo ca moi
    (ngay cu giu nguyen nhu da ghi). Tra ve so dong bang cong da tinh lai."""
    values = {k: data[k] for k in SHIFT_FIELDS if k in data and data[k] is not None}
    new = {k: values.get(k, getattr(shift, k)) for k in SHIFT_FIELDS}
    if not str(new["name"]).strip():
        raise ChamCongError("Tên ca không được để trống")
    if new["end_time"] <= new["start_time"]:
        raise ChamCongError("Giờ kết thúc ca phải sau giờ bắt đầu (ca qua đêm chưa hỗ trợ)")
    for k, lo, hi, label in (("break_minutes", 0, 240, "Số phút nghỉ"), ("grace_minutes", 0, 120, "Số phút ân hạn"),
                             ("early_checkin_minutes", 0, 240, "Số phút cho vào sớm"),
                             ("phut_chong_trung", 1, 120, "Số phút chống quét trùng")):
        if not lo <= int(new[k]) <= hi:
            raise ChamCongError(f"{label} phải từ {lo} đến {hi}")
    if new["break_minutes"]:
        b_start = datetime.combine(date(2000, 1, 1), new["break_start"])
        b_end = b_start + timedelta(minutes=int(new["break_minutes"]))
        if not (datetime.combine(date(2000, 1, 1), new["start_time"]) <= b_start
                and b_end <= datetime.combine(date(2000, 1, 1), new["end_time"])):
            raise ChamCongError("Giờ nghỉ phải nằm trong giờ ca")
    for k, v in values.items():
        setattr(shift, k, v.strip() if isinstance(v, str) else v)
    tz, now = mui_gio(att_cfg), now or utcnow()
    today = ngay_cong(now, tz)
    rows = db.scalars(select(Attendance).where(Attendance.shift_id == shift.id, Attendance.work_date == today)).all()
    for a in rows:
        tinh_lai_ngay(db, a, att_cfg, now)
    db.commit()
    return len(rows)
