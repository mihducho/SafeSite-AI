"""So lieu cho web (DE_TAI.md muc 9.1): bang cong theo ngay, tong quan hom nay. Gio hien thi theo gio Viet Nam."""
from datetime import date, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import DANG_LAM, Attendance, PpeCheck, Worker
from app.services.cham_cong import ca_mac_dinh, gio_phut, khoang_ngay, mui_gio, ngay_cong, thieu_gio_ra
from src.checkpoint.evaluate import KHONG_DAT


def bang_cong_ngay(db: Session, ngay: date, att_cfg: dict, now: datetime, team_id: int | None = None) -> list[dict]:
    """1 dong / cong nhan dang lam (va cong nhan da nghi nhung co cong ngay do), ke ca nguoi chua vao."""
    tz, shift = mui_gio(att_cfg), ca_mac_dinh(db)
    rows = {a.worker_id: a for a in db.scalars(select(Attendance).where(Attendance.work_date == ngay,
                                                                        Attendance.shift_id == shift.id))}
    q = select(Worker).where(or_(Worker.status == DANG_LAM, Worker.id.in_(list(rows) or [-1])))
    if team_id is not None:
        q = q.where(Worker.team_id == team_id)
    out = []
    for w in db.scalars(q.order_by(Worker.code)):
        a = rows.get(w.id)
        out.append({
            "worker_id": w.id, "ma": w.code, "ho_ten": w.full_name, "to_doi": w.team.name if w.team else None,
            "ngay": ngay.isoformat(), "ca": shift.name,
            "gio_vao": gio_phut(a.check_in, tz) if a else None, "gio_ra": gio_phut(a.check_out, tz) if a else None,
            "di_muon_phut": a.late_minutes if a else 0, "ve_som_phut": a.early_leave_minutes if a else 0,
            "so_phut_lam": a.worked_minutes if a else 0,
            "trang_thai": a.status if a else "chua_vao",
            "thieu_gio_ra": bool(a) and thieu_gio_ra(a, shift, now, att_cfg),
            "ghi_chu": a.note if a else None,
        })
    return out


def tong_quan(db: Session, att_cfg: dict, now: datetime, latest: int = 5) -> dict:
    """So cong nhan, da vao, dang co mat, luot khong dat hom nay, cac luot moi nhat."""
    tz = mui_gio(att_cfg)
    today = ngay_cong(now, tz)
    start, end = khoang_ngay(today, tz)
    came = db.scalars(select(Attendance).where(Attendance.work_date == today, Attendance.check_in.is_not(None))).all()
    checks_today = select(func.count(PpeCheck.id)).where(PpeCheck.checked_at >= start, PpeCheck.checked_at < end)
    return {
        "ngay": today.isoformat(),
        "so_cong_nhan": db.scalar(select(func.count(Worker.id)).where(Worker.status == DANG_LAM)) or 0,
        "da_vao": len({a.worker_id for a in came}),
        "dang_co_mat": len({a.worker_id for a in came if a.check_out is None}),
        "so_luot": db.scalar(checks_today) or 0,
        "luot_khong_dat": db.scalar(checks_today.where(PpeCheck.result == KHONG_DAT)) or 0,
        "luot_moi_nhat": db.scalars(select(PpeCheck).order_by(PpeCheck.checked_at.desc(), PpeCheck.id.desc())
                                    .limit(latest)).all(),  # API doi sang JSON
    }
