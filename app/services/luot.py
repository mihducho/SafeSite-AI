"""Xu ly 1 luot kiem tra tai cong (DE_TAI.md muc 5 buoc 5-6, muc 7, 8; docs/LOGIC_CHAM_CONG.md).

GateWorker (thread nen) xong 1 luot -> LuotKiemTra.tu_ket_qua_cong(ket_qua, luc bat dau luot) -> xu_ly_luot(db, luot):
  1. nhan dien: vector khuon mat -> cong nhan (nhan_dien.py) hoac KHONG_NHAN_RA / KHONG_THAY_MAT;
  2. DUOI khoa theo cong nhan (cham_cong.khoa_cong_nhan): ghi ppe_checks (KHONG ghi vector), cham_cong.py quyet dinh
     vao / ra va ghi phien; commit. Loi IntegrityError (ghi dong thoi tu tien trinh khac): rollback, thu lai 1 lan;
  3. SAU khi commit thanh cong moi ghi anh minh chung paths.check_images/<ngay>/<gio>_<ma>.jpg (file tam roi doi ten):
     loi CSDL thi khong de lai file mo coi;
  4. tra ve SU KIEN cho man hinh cong: mau (xanh/do/vang, phan_loai_luot: dung chung voi trang Tong quan), cau thong
     bao (+ dong phu), cong nhan, hanh dong, gio, anh.
"""
import os
import uuid
from contextlib import nullcontext
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.models import PpeCheck, Worker
from app.services.cham_cong import (BO_QUA_TRUNG, GHI_RA, GHI_VAO, KHONG_GHI, NGOAI_GIO_VAO, VAO, KetQuaChamCong,
                                    cham_cong_tu_dong, gio_phut, khoa_cong_nhan, mui_gio)
from app.services.nhan_dien import NhanDien
from src.checkpoint.evaluate import KHONG_CO_NGUOI, KHONG_DAT, NHIEU_NGUOI

DA_NHAN_RA, KHONG_NHAN_RA, KHONG_THAY_MAT = "DA_NHAN_RA", "KHONG_NHAN_RA", "KHONG_THAY_MAT"
XANH, DO, VANG = "xanh", "do", "vang"
TEN_THIEU = {"thieu_mu": "thiếu mũ bảo hộ", "thieu_ao": "thiếu áo phản quang"}


def json_safe(v):
    """So numpy -> so Python de luu cot JSON."""
    if isinstance(v, dict):
        return {str(k): json_safe(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [json_safe(x) for x in v]
    if isinstance(v, np.generic):
        return v.item()
    return v


@dataclass
class LuotKiemTra:
    """Du lieu 1 luot gui sang backend (DE_TAI muc 5 buoc 4). Test tao truc tiep, khong can camera."""
    thoi_diem: datetime                   # co mui gio
    ket_qua: str                          # sau luat nhieu_mat (src/gate/combine.py)
    thieu: list[str] = field(default_factory=list)
    vectors: np.ndarray = field(default_factory=lambda: np.zeros((0, 128), np.float32))  # toi da 5 vector khuon mat
    anh_jpeg: bytes | None = None
    ly_do: str | None = None
    ty_le_co_mat: dict = field(default_factory=dict)
    thoi_gian_ms: float | None = None
    chi_tiet: dict = field(default_factory=dict)  # so lieu xem lai, KHONG co vector

    @classmethod
    def tu_ket_qua_cong(cls, r: dict, thoi_diem: datetime) -> "LuotKiemTra":
        """Ket qua GateRound.finish (src/gate/round.py) -> LuotKiemTra."""
        km = r["khuon_mat"]
        chi_tiet = {
            "ket_qua_bao_ho": r.get("ket_qua_bao_ho"), "thieu_bao_ho": r.get("thieu_bao_ho"),
            "so_khung": r.get("so_khung"), "so_khung_hop_le": r.get("so_khung_hop_le"), "dem_khung": r.get("dem_khung"),
            "so_khung_co_mat": km.get("so_khung_co_mat"), "ty_le_khung_nhieu_mat": km.get("ty_le_khung_nhieu_mat"),
            "chat_luong_mat": km.get("chat_luong"), "rong_mat_px": km.get("rong_mat_px"), "ms_tb": r.get("ms_tb"),
            "tu_luc_thay_mat_ms": r.get("tu_luc_thay_mat_ms"),
        }
        return cls(thoi_diem=thoi_diem, ket_qua=r["ket_qua"], thieu=list(r.get("thieu") or []),
                   vectors=np.asarray(km["vectors"], np.float32).reshape(-1, 128), anh_jpeg=r.get("anh_jpeg"),
                   ly_do=r.get("ly_do"), ty_le_co_mat=dict(r.get("ty_le_co_mat") or {}),
                   thoi_gian_ms=r.get("thoi_gian_ms"), chi_tiet=json_safe(chi_tiet))


def duong_dan_anh(t: datetime, tz) -> str:
    """Duong dan tuong doi cua anh luot (luu vao ppe_checks.image_path), vd 2026-11-02/070000_ab12cd34.jpg."""
    local = t.astimezone(tz)
    return f"{local:%Y-%m-%d}/{local:%H%M%S}_{uuid.uuid4().hex[:8]}.jpg"


def ghi_anh(jpeg: bytes, image_dir: Path, rel: str) -> None:
    """Ghi file tam roi doi ten: khong bao gio co file anh ghi do dang."""
    path = Path(image_dir) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_bytes(jpeg)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def phan_loai_luot(ket_qua: str, nhan_ra: bool, hanh_dong: str, ly_do: str | None = None) -> str:
    """Mau cua 1 luot tren man hinh cong (xanh / do / vang). Dung chung voi trang Tong quan (Q14): "luot khong dat"
    = luot mau DO = luot VAO cua nguoi DA NHAN RA bi KHONG_DAT (trong gio vao ca)."""
    if hanh_dong in (GHI_VAO, GHI_RA, BO_QUA_TRUNG):
        return XANH
    if nhan_ra and ket_qua == KHONG_DAT and not ly_do:
        return DO
    return VANG


def thong_bao_cong(luot: LuotKiemTra, worker: Worker | None, kq: KetQuaChamCong, tz) -> tuple[str, str, str | None]:
    """(mau, cau thong bao, dong phu) cho man hinh cong (DE_TAI muc 5 buoc 6)."""
    mau = phan_loai_luot(luot.ket_qua, worker is not None, kq.hanh_dong, kq.ly_do)
    if worker is None or (kq.hanh_dong == KHONG_GHI and luot.ket_qua in (NHIEU_NGUOI, KHONG_CO_NGUOI)):
        if luot.ket_qua == NHIEU_NGUOI:
            return mau, "Mời từng người một", None
        if luot.ket_qua == KHONG_CO_NGUOI:
            return mau, "Mời đứng vào vị trí, nhìn vào camera", None
        return mau, "Chưa nhận diện được, mời nhìn thẳng camera", None
    ten, gio = worker.full_name, gio_phut(luot.thoi_diem, tz)
    if kq.hanh_dong == GHI_VAO:
        return mau, (f"Chào mừng trở lại {ten}. Đã ghi giờ vào {gio}" if kq.vao_lai
                     else f"Xin chào {ten}. Đã ghi giờ vào {gio}"), None
    if kq.hanh_dong == GHI_RA:
        if kq.tong_hop is not None and kq.tong_hop.som_co_phep:
            return mau, f"Tạm biệt {ten}. Đã ghi giờ ra {gio} (về sớm có phép)", None
        return mau, f"Tạm biệt {ten}. Đã ghi giờ ra {gio}", \
            "Về sớm chưa có phép, vui lòng báo tổ trưởng" if kq.nhac_ve_som else None
    if kq.hanh_dong == BO_QUA_TRUNG:
        loai = "vào" if kq.moc_huong == VAO else "ra"
        return mau, f"{ten}: đã ghi giờ {loai} {gio_phut(kq.moc, tz)}, không ghi lặp", None
    if kq.ly_do == NGOAI_GIO_VAO:
        return mau, (f"Chưa đến giờ vào ca (từ {gio_phut(kq.moc, tz)})" if kq.som_qua
                     else "Đã hết giờ vào ca hôm nay"), None
    if luot.ket_qua == KHONG_DAT:  # luot vao khong dat
        return mau, f"{ten}: {', '.join(TEN_THIEU.get(t, t) for t in luot.thieu)}. Chưa ghi công", None
    return mau, f"{ten}: mời đứng yên để kiểm tra lại", None  # KHONG_XAC_DINH


def xu_ly_luot(db: Session, luot: LuotKiemTra, *, settings: dict, nhan_dien: NhanDien, image_dir: str | Path,
               gate_id: int | None = None) -> dict:
    tz = mui_gio(settings["attendance"])

    worker, m = None, None
    if len(luot.vectors) == 0:
        face_status = KHONG_THAY_MAT
    else:
        m = nhan_dien.nhan_dien(db, luot.vectors)
        worker = db.get(Worker, m.ma) if m.ma is not None else None
        face_status = DA_NHAN_RA if worker is not None else KHONG_NHAN_RA

    nearest = db.get(Worker, m.ma_gan_nhat) if m is not None and m.ma_gan_nhat is not None else None
    detail = {**luot.chi_tiet, "ly_do": luot.ly_do,
              "nhan_dien": None if m is None else {
                  "gan_nhat_id": m.ma_gan_nhat, "gan_nhat_ma": nearest.code if nearest else None,
                  "diem": None if m.diem is None else round(m.diem, 4),
                  "diem_thu_hai": None if m.diem_thu_hai is None else round(m.diem_thu_hai, 4)}}
    worker_id = worker.id if worker is not None else None
    rel = duong_dan_anh(luot.thoi_diem, tz) if luot.anh_jpeg else None

    for lan in (1, 2):  # ghi dong thoi tu tien trinh khac -> IntegrityError: rollback, doc lai, thu lai 1 lan
        try:
            with khoa_cong_nhan(db, worker_id) if worker_id is not None else nullcontext():
                worker = db.get(Worker, worker_id) if worker_id is not None else None
                check = PpeCheck(
                    gate_id=gate_id, worker_id=worker_id, checked_at=luot.thoi_diem, face_status=face_status,
                    face_score=None if m is None or m.diem is None else round(m.diem, 4), result=luot.ket_qua,
                    missing=list(luot.thieu), presence_ratio=json_safe(luot.ty_le_co_mat), reason=luot.ly_do,
                    duration_ms=luot.thoi_gian_ms, action=KHONG_GHI, image_path=rel, detail=json_safe(detail))
                db.add(check)
                db.flush()  # lay check.id cho phien (vao_check_id / ra_check_id)
                kq = KetQuaChamCong(None, KHONG_GHI)
                if worker is not None:
                    kq = cham_cong_tu_dong(db, worker, luot.ket_qua, luot.thoi_diem, check, settings["attendance"])
                check.direction, check.action, check.action_reason = kq.huong, kq.hanh_dong, kq.ly_do
                db.commit()
            break
        except (IntegrityError, OperationalError):
            db.rollback()
            if lan == 2:
                raise
    if rel:
        ghi_anh(luot.anh_jpeg, Path(image_dir), rel)  # sau khi commit: loi CSDL thi khong co file mo coi

    mau, text, phu = thong_bao_cong(luot, worker, kq, tz)
    return {
        "loai": "luot",
        "id": check.id,
        "mau": mau,
        "thong_bao": text,
        "thong_bao_phu": phu,  # vd "Về sớm chưa có phép, vui lòng báo tổ trưởng"
        "cong_nhan": None if worker is None else {"id": worker.id, "ma": worker.code, "ten": worker.full_name},
        "hanh_dong": kq.hanh_dong,
        "huong": kq.huong,
        "ly_do_ghi": kq.ly_do,
        "gio": gio_phut(luot.thoi_diem, tz),
        "thoi_diem": luot.thoi_diem.astimezone(tz).isoformat(timespec="seconds"),
        "ket_qua": luot.ket_qua,
        "thieu": list(luot.thieu),
        "trang_thai_mat": face_status,
        "diem": check.face_score,
        "anh": f"/api/luot/{check.id}/anh" if check.image_path else None,
        "ghi_cong": kq.hanh_dong in (GHI_VAO, GHI_RA),
        "vao_lai": kq.vao_lai,                                                   # ghi_vao phien thu 2 tro di
        "som_co_phep": bool(kq.tong_hop is not None and kq.tong_hop.som_co_phep),  # ghi_ra ve som co phep
    }
