"""So lieu cho web (DE_TAI.md muc 9.1): bang cong theo ngay / thang (xuat Excel), tong quan hom nay.
Gio hien thi theo gio Viet Nam."""
import calendar
import io
from datetime import date, datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import DANG_LAM, Attendance, PpeCheck, Shift, Worker
from app.services.cham_cong import ca_mac_dinh, gio_phut, khoang_ngay, mui_gio, ngay_cong, thieu_gio_ra
from src.checkpoint.evaluate import DAT, KHONG_DAT


def dong_bang_cong(w: Worker, a: Attendance | None, shift: Shift, ngay: date, now: datetime, att_cfg: dict) -> dict:
    """1 dong bang cong (ca nguoi chua vao: a = None)."""
    tz = mui_gio(att_cfg)
    return {
        "worker_id": w.id, "ma": w.code, "ho_ten": w.full_name, "to_doi": w.team.name if w.team else None,
        "ngay": ngay.isoformat(), "ca": shift.name,
        "gio_vao": gio_phut(a.check_in, tz) if a else None, "gio_ra": gio_phut(a.check_out, tz) if a else None,
        "di_muon_phut": a.late_minutes if a else 0, "ve_som_phut": a.early_leave_minutes if a else 0,
        "so_phut_lam": a.worked_minutes if a else 0,
        "trang_thai": a.status if a else "chua_vao",
        "thieu_gio_ra": bool(a) and thieu_gio_ra(a, shift, now, att_cfg),
        "ghi_chu": a.note if a else None,
    }


def _workers_for(db: Session, worker_ids_with_rows, team_id: int | None = None):
    """Cong nhan dang lam + cong nhan (ke ca da nghi) co cong trong khoang dang xem."""
    q = select(Worker).where(or_(Worker.status == DANG_LAM, Worker.id.in_(list(worker_ids_with_rows) or [-1])))
    if team_id is not None:
        q = q.where(Worker.team_id == team_id)
    return db.scalars(q.order_by(Worker.code)).all()


def bang_cong_ngay(db: Session, ngay: date, att_cfg: dict, now: datetime, team_id: int | None = None) -> list[dict]:
    """1 dong / cong nhan dang lam (va cong nhan da nghi nhung co cong ngay do), ke ca nguoi chua vao."""
    shift = ca_mac_dinh(db)
    rows = {a.worker_id: a for a in db.scalars(select(Attendance).where(Attendance.work_date == ngay,
                                                                        Attendance.shift_id == shift.id))}
    return [dong_bang_cong(w, rows.get(w.id), shift, ngay, now, att_cfg) for w in _workers_for(db, rows, team_id)]


def bang_cong_gan_day(db: Session, worker: Worker, att_cfg: dict, now: datetime, so_ngay: int = 14) -> list[dict]:
    """Cac ngay co cong cua 1 cong nhan trong so_ngay ngay gan nhat, moi nhat truoc."""
    shift = ca_mac_dinh(db)
    tu = ngay_cong(now, mui_gio(att_cfg)) - timedelta(days=so_ngay - 1)
    rows = db.scalars(select(Attendance).where(Attendance.worker_id == worker.id, Attendance.work_date >= tu)
                      .order_by(Attendance.work_date.desc())).all()
    return [dong_bang_cong(worker, a, a.shift or shift, a.work_date, now, att_cfg) for a in rows]


def bang_cong_thang(db: Session, nam: int, thang: int, att_cfg: dict, now: datetime, team_id: int | None = None) -> dict:
    """Bang cong 1 thang: moi cong nhan 1 dong, moi ngay 1 o (so phut lam, trang thai), cong ngay cong, tong gio."""
    shift = ca_mac_dinh(db)
    so_ngay = calendar.monthrange(nam, thang)[1]
    tu, den = date(nam, thang, 1), date(nam, thang, so_ngay)
    att = db.scalars(select(Attendance).where(Attendance.work_date >= tu, Attendance.work_date <= den,
                                              Attendance.shift_id == shift.id)).all()
    by_worker: dict[int, dict[int, Attendance]] = {}
    for a in att:
        by_worker.setdefault(a.worker_id, {})[a.work_date.day] = a
    ds = []
    for w in _workers_for(db, by_worker, team_id):
        days = by_worker.get(w.id, {})
        cells = {d: dong_bang_cong(w, a, shift, a.work_date, now, att_cfg) for d, a in sorted(days.items())}
        ds.append({"worker_id": w.id, "ma": w.code, "ho_ten": w.full_name, "to_doi": w.team.name if w.team else None,
                   "ngay": cells,
                   "so_ngay_cong": sum(1 for a in days.values() if a.check_in),
                   "tong_phut": sum(a.worked_minutes for a in days.values()),
                   "so_lan_muon": sum(1 for a in days.values() if a.late_minutes > 0)})
    return {"thang": f"{nam:04d}-{thang:02d}", "so_ngay": so_ngay, "ca": shift.name, "ds": ds}


def _hm(minutes: int) -> str:
    return f"{minutes // 60}:{minutes % 60:02d}"


def excel_bang_cong_thang(data: dict) -> bytes:
    """File .xlsx: sheet "Bang cong" (moi o = so gio lam h:mm) va sheet "Chi tiet" (moi ngay 1 dong)."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "Bang cong"
    nam, thang = data["thang"].split("-")
    ws.append([f"BẢNG CÔNG THÁNG {thang}/{nam} - {data['ca']}"])
    ws["A1"].font = Font(bold=True, size=13)
    header = ["Mã", "Họ tên", "Tổ đội"] + [str(d) for d in range(1, data["so_ngay"] + 1)] + \
             ["Số ngày công", "Tổng giờ làm", "Số lần đi muộn"]
    ws.append(header)
    bold, fill = Font(bold=True), PatternFill("solid", fgColor="DDEBF7")
    late_fill = PatternFill("solid", fgColor="FCE4D6")
    for c in ws[2]:
        c.font, c.fill, c.alignment = bold, fill, Alignment(horizontal="center")
    for r in data["ds"]:
        row = [r["ma"], r["ho_ten"], r["to_doi"] or ""]
        for d in range(1, data["so_ngay"] + 1):
            cell = r["ngay"].get(d)
            row.append(_hm(cell["so_phut_lam"]) if cell and cell["gio_vao"] else "")
        row += [r["so_ngay_cong"], _hm(r["tong_phut"]), r["so_lan_muon"]]
        ws.append(row)
        for d, cell in r["ngay"].items():  # to mau ngay di muon
            if cell["di_muon_phut"] > 0:
                ws.cell(row=ws.max_row, column=3 + d).fill = late_fill
    ws.column_dimensions["A"].width, ws.column_dimensions["B"].width, ws.column_dimensions["C"].width = 10, 24, 16
    for col in range(4, 4 + data["so_ngay"]):
        ws.column_dimensions[get_column_letter(col)].width = 6
    ws.freeze_panes = "D3"

    ct = wb.create_sheet("Chi tiet")
    ct.append(["Ngày", "Mã", "Họ tên", "Tổ đội", "Giờ vào", "Giờ ra", "Đi muộn (phút)", "Về sớm (phút)",
               "Số giờ làm", "Trạng thái", "Ghi chú"])
    for c in ct[1]:
        c.font, c.fill = bold, fill
    for r in data["ds"]:
        for d, cell in sorted(r["ngay"].items()):
            y, m, dd = cell["ngay"].split("-")
            ct.append([f"{dd}/{m}/{y}", r["ma"], r["ho_ten"], r["to_doi"] or "", cell["gio_vao"] or "",
                       cell["gio_ra"] or "", cell["di_muon_phut"], cell["ve_som_phut"], _hm(cell["so_phut_lam"]),
                       cell["trang_thai"], cell["ghi_chu"] or ""])
    for col, width in zip("ABCDEFGHIJK", (12, 10, 24, 16, 9, 9, 15, 14, 11, 15, 50)):
        ct.column_dimensions[col].width = width
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def tong_quan(db: Session, att_cfg: dict, now: datetime, latest: int = 10) -> dict:
    """So cong nhan, da vao, dang co mat (kem danh sach), luot khong dat, ti le dat bao ho hom nay, so luot theo gio,
    luot moi nhat."""
    tz = mui_gio(att_cfg)
    today = ngay_cong(now, tz)
    start, end = khoang_ngay(today, tz)
    came = db.scalars(select(Attendance).where(Attendance.work_date == today, Attendance.check_in.is_not(None))).all()
    checks_today = select(func.count(PpeCheck.id)).where(PpeCheck.checked_at >= start, PpeCheck.checked_at < end)
    dat = db.scalar(checks_today.where(PpeCheck.result == DAT)) or 0
    khong_dat = db.scalar(checks_today.where(PpeCheck.result == KHONG_DAT)) or 0
    present = sorted((a for a in came if a.check_out is None), key=lambda a: a.check_in)
    theo_gio = [{"gio": h, "dat": 0, "khong_dat": 0, "khac": 0} for h in range(24)]  # bieu do so luot theo gio
    for t, kq in db.execute(select(PpeCheck.checked_at, PpeCheck.result)
                            .where(PpeCheck.checked_at >= start, PpeCheck.checked_at < end)).all():
        theo_gio[t.astimezone(tz).hour]["dat" if kq == DAT else "khong_dat" if kq == KHONG_DAT else "khac"] += 1
    return {
        "ngay": today.isoformat(),
        "so_cong_nhan": db.scalar(select(func.count(Worker.id)).where(Worker.status == DANG_LAM)) or 0,
        "da_vao": len({a.worker_id for a in came}),
        "dang_co_mat": len({a.worker_id for a in present}),
        "so_luot": db.scalar(checks_today) or 0,
        "luot_dat": dat,
        "luot_khong_dat": khong_dat,
        # trong cac luot co ket luan bao ho (DAT hoac KHONG_DAT); chua co luot nao -> None
        "ty_le_dat": round(dat / (dat + khong_dat), 3) if dat + khong_dat else None,
        "dang_co_mat_ds": [{"worker_id": a.worker_id, "ma": a.worker.code, "ho_ten": a.worker.full_name,
                            "to_doi": a.worker.team.name if a.worker.team else None,
                            "gio_vao": gio_phut(a.check_in, tz)} for a in present],
        "luot_theo_gio": theo_gio,  # 24 gio (gio Viet Nam): dat / khong_dat / khac (khong xac dinh, nhieu nguoi...)
        "luot_moi_nhat": db.scalars(select(PpeCheck).order_by(PpeCheck.checked_at.desc(), PpeCheck.id.desc())
                                    .limit(latest)).all(),  # API doi sang JSON
    }
