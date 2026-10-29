"""Cham cong (DE_TAI.md muc 7). CSDL luu gio UTC; ngay cong va gio ca tinh theo attendance.timezone (Asia/Ho_Chi_Minh).

Vao hay ra (theo bang cong cua cong nhan trong ngay):
  - chua co gio vao, hoac da co CA gio vao VA gio ra -> luot nay la VAO;
  - da vao ma chua ra -> luot nay la RA.
Luot VAO: chi khi bao ho DAT moi ghi (khong dat -> chua ghi cong, bo sung roi kiem tra lai). Gio vao = luot DAT dau tien.
  Vao lai sau khi da ra (vd an trua): phai DAT; GIU gio vao dau tien, xoa gio ra cu (dang co mat) -> lan ra sau ghi gio ra moi.
Luot RA: khong yeu cau bao ho. Cach lan vao gan nhat < duplicate_minutes -> bo qua (bo_qua_trung, dung lai truoc camera).
NHIEU_NGUOI / KHONG_CO_NGUOI: khong ghi cong ca vao lan ra.

Ca lam (ban demo: 1 ca mac dinh, bang shifts):
  - di muon = gio vao - bat dau ca (phut), chi tinh khi > grace_minutes (an han);
  - ve som = ket thuc ca - gio ra;
  - so phut lam = [max(vao, bat dau), min(ra, ket thuc)] tru phan GIAO NHAU voi gio nghi [break_start, break_start +
    break_minutes], khong am: lam ca ngay tru du nghi trua; vao roi ra trong buoi sang thi khong tru;
  - gio vao ngoai [bat dau - early_checkin_minutes, ket thuc] -> trang thai ngoai_ca;
  - chua co gio ra sau ket thuc ca missing_checkout_hours gio -> hien "thieu gio ra".
Cham cong thu cong: them/sua gio vao, ra; BAT BUOC co ly do; trang thai cham_thu_cong; luu nguoi sua.
"""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import utcnow
from app.models import Attendance, PpeCheck, Shift, User, Worker
from src.checkpoint.evaluate import DAT, KHONG_CO_NGUOI, NHIEU_NGUOI

VAO, RA = "vao", "ra"
GHI_VAO, GHI_RA, KHONG_GHI, BO_QUA_TRUNG = "ghi_vao", "ghi_ra", "khong_ghi", "bo_qua_trung"
BINH_THUONG, NGOAI_CA, CHAM_THU_CONG = "binh_thuong", "ngoai_ca", "cham_thu_cong"


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


def _phut(td: timedelta) -> int:
    return max(0, int(td.total_seconds() // 60))


# --- ca lam ---
def ca_mac_dinh(db: Session) -> Shift:
    shift = db.scalar(select(Shift).order_by(Shift.id).limit(1))
    if shift is None:
        raise ChamCongError("Chưa có ca làm trong CSDL: chạy scripts\\seed_demo.py")
    return shift


def moc_ca(shift: Shift, ngay: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    start = datetime.combine(ngay, shift.start_time, tzinfo=tz)
    end = datetime.combine(ngay, shift.end_time, tzinfo=tz)
    if end <= start:  # ca qua dem (de danh cho do an)
        end += timedelta(days=1)
    return start, end


def moc_nghi(shift: Shift, ngay: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    start = datetime.combine(ngay, shift.break_start, tzinfo=tz)
    return start, start + timedelta(minutes=shift.break_minutes)


def giao_nhau(a1: datetime, a2: datetime, b1: datetime, b2: datetime) -> timedelta:
    """Do dai phan chung cua 2 khoang [a1, a2] va [b1, b2] (0 neu khong giao nhau)."""
    return max(timedelta(0), min(a2, b2) - max(a1, b1))


def trong_khung_vao(shift: Shift, t: datetime, ngay: date, tz: ZoneInfo) -> bool:
    start, end = moc_ca(shift, ngay, tz)
    return start - timedelta(minutes=shift.early_checkin_minutes) <= t <= end


def tinh_cong(att: Attendance, shift: Shift, tz: ZoneInfo) -> None:
    """Cap nhat phut di muon, ve som, so phut lam cua 1 dong bang cong."""
    start, end = moc_ca(shift, att.work_date, tz)
    late = _phut(att.check_in - start) if att.check_in else 0
    att.late_minutes = late if late > shift.grace_minutes else 0
    if att.check_in and att.check_out:
        att.early_leave_minutes = _phut(end - att.check_out)
        lam_tu, lam_den = max(att.check_in, start), min(att.check_out, end)  # chi tinh trong gio ca
        nghi = giao_nhau(lam_tu, lam_den, *moc_nghi(shift, att.work_date, tz))
        att.worked_minutes = _phut(lam_den - lam_tu - nghi)
    else:
        att.early_leave_minutes = att.worked_minutes = 0


def thieu_gio_ra(att: Attendance, shift: Shift, now: datetime, att_cfg: dict) -> bool:
    if not att.check_in or att.check_out:
        return False
    _, end = moc_ca(shift, att.work_date, mui_gio(att_cfg))
    return now > end + timedelta(hours=att_cfg["missing_checkout_hours"])


# --- vao / ra ---
def tim_bang_cong(db: Session, worker_id: int, ngay: date, shift_id: int) -> Attendance | None:
    return db.scalar(select(Attendance).where(Attendance.worker_id == worker_id, Attendance.work_date == ngay,
                                              Attendance.shift_id == shift_id))


def huong(att: Attendance | None) -> str:
    if att is None or att.check_in is None or att.check_out is not None:
        return VAO
    return RA


def lan_vao_gan_nhat(db: Session, att: Attendance, tz: ZoneInfo) -> datetime:
    """Luot ghi_vao moi nhat trong ngay (vao lai sau gio an trua); khong co (vd gio vao cham thu cong) -> gio vao."""
    start, end = khoang_ngay(att.work_date, tz)
    t = db.scalar(select(PpeCheck.checked_at).where(
        PpeCheck.worker_id == att.worker_id, PpeCheck.action == GHI_VAO,
        PpeCheck.checked_at >= start, PpeCheck.checked_at < end).order_by(PpeCheck.checked_at.desc()).limit(1))
    return max(t, att.check_in) if t else att.check_in


@dataclass
class KetQuaChamCong:
    huong: str | None             # vao / ra / None (khong xet)
    hanh_dong: str                # ghi_vao / ghi_ra / khong_ghi / bo_qua_trung
    bang_cong: Attendance | None = None
    vao_lai: bool = False         # ghi_vao lan 2 tro di trong ngay
    gio_vao_truoc: datetime | None = None  # bo_qua_trung: lan vao gan nhat


def cham_cong_tu_dong(db: Session, worker: Worker, ket_qua: str, t: datetime, ppe_check: PpeCheck,
                      att_cfg: dict) -> KetQuaChamCong:
    """Goi khi da NHAN RA cong nhan. ket_qua: ket qua cua luot (sau luat nhieu_mat). Chua commit."""
    if ket_qua in (NHIEU_NGUOI, KHONG_CO_NGUOI):
        return KetQuaChamCong(None, KHONG_GHI)
    tz, shift = mui_gio(att_cfg), ca_mac_dinh(db)
    ngay = ngay_cong(t, tz)
    att = tim_bang_cong(db, worker.id, ngay, shift.id)

    if huong(att) == VAO:
        if ket_qua != DAT:
            return KetQuaChamCong(VAO, KHONG_GHI, att)
        vao_lai = att is not None and att.check_in is not None
        if att is None:
            att = Attendance(worker_id=worker.id, work_date=ngay, shift_id=shift.id, status=BINH_THUONG)
            db.add(att)
        if vao_lai:
            att.check_out = None  # dang co mat tro lai; giu gio vao dau tien
        else:
            att.check_in, att.ppe_check_id = t, ppe_check.id
            if att.status != CHAM_THU_CONG:
                att.status = BINH_THUONG if trong_khung_vao(shift, t, ngay, tz) else NGOAI_CA
        tinh_cong(att, shift, tz)
        att.updated_at = t
        return KetQuaChamCong(VAO, GHI_VAO, att, vao_lai=vao_lai)

    last_in = lan_vao_gan_nhat(db, att, tz)
    if t - last_in < timedelta(minutes=att_cfg["duplicate_minutes"]):
        return KetQuaChamCong(RA, BO_QUA_TRUNG, att, gio_vao_truoc=last_in)
    att.check_out = t
    tinh_cong(att, shift, tz)
    att.updated_at = t
    return KetQuaChamCong(RA, GHI_RA, att)


# --- cham cong thu cong ---
def cham_thu_cong(db: Session, worker: Worker, ngay: date, gio_vao: time | None, gio_ra: time | None, ly_do: str,
                  user: User, att_cfg: dict, now: datetime | None = None) -> Attendance:
    """Them hoac sua gio vao/ra cua 1 ngay (gio Viet Nam). Thieu ly do, gio ra truoc gio vao... -> ChamCongError."""
    ly_do = (ly_do or "").strip()
    if not ly_do:
        raise ChamCongError("Bắt buộc ghi lý do khi chấm công thủ công")
    if gio_vao is None and gio_ra is None:
        raise ChamCongError("Cần nhập giờ vào hoặc giờ ra")
    tz, shift, now = mui_gio(att_cfg), ca_mac_dinh(db), now or utcnow()
    if ngay > ngay_cong(now, tz):
        raise ChamCongError("Không chấm công cho ngày trong tương lai")
    att = tim_bang_cong(db, worker.id, ngay, shift.id)
    check_in = datetime.combine(ngay, gio_vao, tzinfo=tz) if gio_vao is not None else (att and att.check_in)
    check_out = datetime.combine(ngay, gio_ra, tzinfo=tz) if gio_ra is not None else (att and att.check_out)
    if check_in is None:
        raise ChamCongError("Chưa có giờ vào: nhập giờ vào trước")
    if check_out is not None and check_out < check_in:
        raise ChamCongError("Giờ ra phải sau giờ vào")
    if att is None:
        att = Attendance(worker_id=worker.id, work_date=ngay, shift_id=shift.id)
        db.add(att)
    att.check_in, att.check_out = check_in, check_out
    att.status = CHAM_THU_CONG
    line = f"{gio_phut(now, tz)} {now.astimezone(tz):%d/%m} {user.username}: {ly_do}"
    att.note = f"{att.note}\n{line}" if att.note else line  # giu lich su cac lan sua
    att.updated_by, att.updated_at = user.id, now
    tinh_cong(att, shift, tz)
    db.commit()
    return att


# --- sua ca lam (trang /ca-lam) ---
SHIFT_FIELDS = ("name", "start_time", "end_time", "break_start", "break_minutes", "grace_minutes", "early_checkin_minutes")


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
                             ("early_checkin_minutes", 0, 240, "Số phút cho vào sớm")):
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
    tz = mui_gio(att_cfg)
    today = ngay_cong(now or utcnow(), tz)
    rows = db.scalars(select(Attendance).where(Attendance.shift_id == shift.id, Attendance.work_date == today)).all()
    for a in rows:
        tinh_cong(a, shift, tz)
        if a.status != CHAM_THU_CONG and a.check_in is not None:
            a.status = BINH_THUONG if trong_khung_vao(shift, a.check_in, today, tz) else NGOAI_CA
    db.commit()
    return len(rows)
