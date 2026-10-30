"""Quan ly cong nhan va to doi (DE_TAI.md muc 9.1): them, sua, cho nghi viec.

Cho nghi viec (DE_TAI muc 7, Q12): luu ngay_nghi_viec; dang co phien mo thi DONG phien tai thoi diem thao tac (nguon tay,
nhat ky dong_khi_nghi_viec); trang thai nghi_viec -> khong con duoc nhan dien (nhan_dien chi doc cong nhan dang_lam)
va XOA TOAN BO mau khuon mat (vector + anh mau). Di lam lai: xoa ngay_nghi_viec, ngay_vao_lam = hom nay, phai ghi nhan
dong y lai. Doi trang thai thi xoa bo nho dem nhan dien.
"""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import utcnow
from app.models import DANG_LAM, NGHI_VIEC, Team, User, Worker
from app.services.cham_cong import dong_phien_khi_nghi_viec, khoa_cong_nhan, mui_gio, ngay_cong
from app.services.dang_ky_mat import DangKyMat

WORKER_FIELDS = ("code", "full_name", "phone", "trade", "team_id", "ngay_vao_lam")
TEAM_FIELDS = ("name", "contractor", "leader_name")


class CongNhanError(ValueError):
    pass


def _clean(data: dict, fields) -> dict:
    out = {}
    for k in fields:
        if k in data:
            v = data[k]
            out[k] = (v.strip() or None) if isinstance(v, str) else v  # chuoi rong -> None
    return out


def _check_worker(db: Session, values: dict, worker_id: int | None = None) -> None:
    if "code" in values:
        if not values["code"]:
            raise CongNhanError("Mã công nhân không được để trống")
        other = db.scalar(select(Worker).where(Worker.code == values["code"]))
        if other is not None and other.id != worker_id:
            raise CongNhanError(f"Mã công nhân {values['code']} đã có")
    if "full_name" in values and not values["full_name"]:
        raise CongNhanError("Họ tên không được để trống")
    if values.get("team_id") is not None and db.get(Team, values["team_id"]) is None:
        raise CongNhanError(f"Không có tổ đội id={values['team_id']}")


def tao_cong_nhan(db: Session, data: dict) -> Worker:
    values = _clean(data, WORKER_FIELDS)
    for k in ("code", "full_name"):
        values.setdefault(k, None)
    _check_worker(db, values)
    worker = Worker(**values, status=DANG_LAM)
    db.add(worker)
    db.commit()
    return worker


def sua_cong_nhan(db: Session, worker: Worker, data: dict) -> Worker:
    values = _clean(data, WORKER_FIELDS)
    _check_worker(db, values, worker.id)
    for k, v in values.items():
        setattr(worker, k, v)
    db.commit()
    return worker


def cho_nghi_viec(db: Session, worker: Worker, dang_ky: DangKyMat, user: User | None = None,
                  now: datetime | None = None) -> int:
    """Tra ve so mau khuon mat da xoa."""
    att_cfg, now = dang_ky.settings["attendance"], now or utcnow()
    with khoa_cong_nhan(db, worker.id):
        worker.status, worker.ngay_nghi_viec = NGHI_VIEC, ngay_cong(now, mui_gio(att_cfg))
        dong_phien_khi_nghi_viec(db, worker, user, att_cfg, now)
        n = dang_ky.xoa_tat_ca(db, worker, commit=False)
        db.commit()
    dang_ky.nhan_dien.xoa_bo_nho_dem()
    return n


def di_lam_lai(db: Session, worker: Worker, dang_ky: DangKyMat, now: datetime | None = None) -> Worker:
    """Nhan lai cong nhan da nghi: ngay vao lam moi = hom nay; phai ghi nhan dong y va dang ky khuon mat lai tu dau."""
    tz = mui_gio(dang_ky.settings["attendance"])
    worker.status, worker.consent_at, worker.consent_by = DANG_LAM, None, None
    worker.ngay_nghi_viec, worker.ngay_vao_lam = None, ngay_cong(now or utcnow(), tz)
    db.commit()
    dang_ky.nhan_dien.xoa_bo_nho_dem()
    return worker


def tao_to_doi(db: Session, data: dict) -> Team:
    values = _clean(data, TEAM_FIELDS)
    if not values.get("name"):
        raise CongNhanError("Tên tổ đội không được để trống")
    team = Team(**values)
    db.add(team)
    db.commit()
    return team


def sua_to_doi(db: Session, team: Team, data: dict) -> Team:
    values = _clean(data, TEAM_FIELDS)
    if "name" in values and not values["name"]:
        raise CongNhanError("Tên tổ đội không được để trống")
    for k, v in values.items():
        setattr(team, k, v)
    db.commit()
    return team
