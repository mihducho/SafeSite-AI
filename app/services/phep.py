"""Phep / giai trinh (Q21, docs/LOGIC_CHAM_CONG.md): them, huy, liet ke. Moi lan them / huy ghi 1 dong
nhat_ky_cham_cong (them_phep / huy_phep) va tinh lai ngay cong do (neu da co dong cong).

Loai: ve_som (tu_gio = gio duoc phep ve), di_muon (den_gio = gio du kien den), ra_ngoai_cong_viec [tu_gio, den_gio]
(mac dinh tinh cong), nghi_ca_ngay. TTTN chi co admin nen tao la duyet luon (trang_thai da_duyet).
Ngay cua phep: qua khu hoac tuong lai toi da attendance.phep_toi_da_truoc_ngay ngay, trong khoang lam viec.
"""
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import utcnow
from app.models import Phep, User, Worker
from app.services.cham_cong import (ChamCongError, _kiem_tra_ngay_lam, _ly_do, ca_mac_dinh, ghi_nhat_ky, khoa_cong_nhan,
                                    mui_gio, ngay_cong, tim_bang_cong, tinh_lai_ngay)
from app.services.tinh_cong import DI_MUON, LOAI_PHEP, NGHI_CA_NGAY, RA_NGOAI_CONG_VIEC, VE_SOM

DA_DUYET, HUY = "da_duyet", "huy"
THEM_PHEP, HUY_PHEP = "them_phep", "huy_phep"
TEN_LOAI = {VE_SOM: "Về sớm", DI_MUON: "Đi muộn", RA_NGOAI_CONG_VIEC: "Ra ngoài công việc", NGHI_CA_NGAY: "Nghỉ cả ngày"}


def mo_ta(p: Phep) -> str:
    """Chu de doc cho nhat ky / danh sach, vd "Về sớm từ 15:00"."""
    ten = TEN_LOAI.get(p.loai, p.loai)
    if p.loai == VE_SOM:
        return f"{ten} từ {p.tu_gio:%H:%M}"
    if p.loai == DI_MUON:
        return f"{ten} đến {p.den_gio:%H:%M}"
    if p.loai == RA_NGOAI_CONG_VIEC:
        return f"{ten} {p.tu_gio:%H:%M}–{p.den_gio:%H:%M}" + ("" if p.tinh_cong else " (không tính công)")
    return ten


def _tinh_lai(db: Session, worker: Worker, ngay: date, att_cfg: dict, now: datetime) -> None:
    att = tim_bang_cong(db, worker.id, ngay, ca_mac_dinh(db).id)
    if att is not None:
        tinh_lai_ngay(db, att, att_cfg, now)


def them_phep(db: Session, worker: Worker, ngay: date, loai: str, ly_do: str, user: User, att_cfg: dict, *,
              tu_gio: time | None = None, den_gio: time | None = None, tinh_cong: bool | None = None,
              now: datetime | None = None) -> Phep:
    ly_do, now, tz = _ly_do(ly_do), now or utcnow(), mui_gio(att_cfg)
    if loai not in LOAI_PHEP:
        raise ChamCongError(f"Loại phép không hợp lệ: {loai} (dùng {', '.join(LOAI_PHEP)})")
    han = ngay_cong(now, tz) + timedelta(days=att_cfg["phep_toi_da_truoc_ngay"])
    if ngay > han:
        raise ChamCongError(f"Chỉ tạo phép trước tối đa {att_cfg['phep_toi_da_truoc_ngay']} ngày (đến {han:%d/%m/%Y})")
    if loai == VE_SOM and tu_gio is None:
        raise ChamCongError("Phép về sớm cần giờ được phép về (từ giờ)")
    if loai == DI_MUON and den_gio is None:
        raise ChamCongError("Phép đi muộn cần giờ dự kiến đến (đến giờ)")
    if loai == RA_NGOAI_CONG_VIEC and (tu_gio is None or den_gio is None or den_gio <= tu_gio):
        raise ChamCongError("Phép ra ngoài công việc cần từ giờ và đến giờ, đến giờ phải sau từ giờ")
    if loai == VE_SOM:
        den_gio = None
    elif loai == DI_MUON:
        tu_gio = None
    elif loai == NGHI_CA_NGAY:
        tu_gio = den_gio = None
    with khoa_cong_nhan(db, worker.id):
        _kiem_tra_ngay_lam(worker, ngay, tz)
        p = Phep(worker_id=worker.id, ngay=ngay, loai=loai, tu_gio=tu_gio, den_gio=den_gio,
                 tinh_cong=(loai == RA_NGOAI_CONG_VIEC) if tinh_cong is None else bool(tinh_cong), ly_do=ly_do,
                 trang_thai=DA_DUYET, nguoi_tao=user.id, thoi_diem_tao=now)
        db.add(p)
        att = tim_bang_cong(db, worker.id, ngay, ca_mac_dinh(db).id)
        ghi_nhat_ky(db, worker.id, ngay, THEM_PHEP, att=att, phep=p, moi=mo_ta(p), ly_do=ly_do, user=user, now=now)
        _tinh_lai(db, worker, ngay, att_cfg, now)
        db.commit()
    return p


def huy_phep(db: Session, p: Phep, ly_do: str, user: User, att_cfg: dict, now: datetime | None = None) -> Phep:
    ly_do, now = _ly_do(ly_do), now or utcnow()
    with khoa_cong_nhan(db, p.worker_id):
        if p.trang_thai == HUY:
            raise ChamCongError("Phép này đã huỷ")
        p.trang_thai = HUY
        att = tim_bang_cong(db, p.worker_id, p.ngay, ca_mac_dinh(db).id)
        ghi_nhat_ky(db, p.worker_id, p.ngay, HUY_PHEP, att=att, phep=p, cu=mo_ta(p), moi="(huỷ)", ly_do=ly_do,
                    user=user, now=now)
        _tinh_lai(db, p.worker, p.ngay, att_cfg, now)
        db.commit()
    return p


def liet_ke(db: Session, worker_id: int | None = None, ngay: date | None = None, tu: date | None = None,
            den: date | None = None, ca_huy: bool = False) -> list[Phep]:
    q = select(Phep)
    if worker_id is not None:
        q = q.where(Phep.worker_id == worker_id)
    if ngay is not None:
        q = q.where(Phep.ngay == ngay)
    if tu is not None:
        q = q.where(Phep.ngay >= tu)
    if den is not None:
        q = q.where(Phep.ngay <= den)
    if not ca_huy:
        q = q.where(Phep.trang_thai == DA_DUYET)
    return db.scalars(q.order_by(Phep.ngay.desc(), Phep.id)).all()
