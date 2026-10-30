"""API JSON /api/... (DE_TAI.md muc 12, F2). Moi API tru /api/dang-nhap deu can dang nhap (cookie phien).
Thu bang trang /docs (dang nhap o /login truoc). Gio tra ve theo gio Viet Nam (ISO 8601, +07:00).
Loi nghiep vu (chua dong y, thieu ly do, anh khong dat...) -> 400 {"detail": "cau tieng Viet"} (xem main.py).
"""
import re
from datetime import date, datetime, time
from typing import Literal

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.auth import authenticate, current_user, login_session
from app.db import get_db, utcnow
from app.config import mask_source
from app.models import DANG_LAM, Attendance, AttendanceSegment, FaceSample, Gate, NhatKyChamCong, Phep, PpeCheck, Shift, \
    Team, User, Worker
from app.services import bao_cao, cham_cong, cong_nhan, phep
from app.services.tinh_cong import LOAI_PHEP, THU
from app.services.dang_ky_mat import CAMERA, NOI_DUNG_DONG_Y, UPLOAD, DangKyMatError
from src.zone.zone import zone_to_pixels

public = APIRouter(prefix="/api", tags=["dang nhap"])
router = APIRouter(prefix="/api", dependencies=[Depends(current_user)])

KET_QUA = Literal["DAT", "KHONG_DAT", "KHONG_XAC_DINH", "NHIEU_NGUOI", "KHONG_CO_NGUOI"]
HANH_DONG = Literal["ghi_vao", "ghi_ra", "khong_ghi", "bo_qua_trung"]


# ---------- tien ich ----------
def _state(request: Request):
    return request.app.state


def _tz(request: Request):
    return cham_cong.mui_gio(request.app.state.settings["attendance"])


def _iso(t: datetime | None, tz) -> str | None:
    return t.astimezone(tz).isoformat(timespec="seconds") if t else None


def _get(db: Session, model, obj_id: int, name: str):
    obj = db.get(model, obj_id)
    if obj is None:
        raise HTTPException(404, f"Không có {name} id={obj_id}")
    return obj


def worker_json(w: Worker, tz, so_mau: int | None = None) -> dict:
    vao_lam = cham_cong.khoang_lam_viec(w, tz)[0]
    return {"id": w.id, "code": w.code, "full_name": w.full_name, "phone": w.phone, "trade": w.trade,
            "team_id": w.team_id, "team_name": w.team.name if w.team else None, "status": w.status,
            "consent_at": _iso(w.consent_at, tz), "consent_by": w.consent_by,
            "consent_by_name": (w.consent_user.full_name or w.consent_user.username) if w.consent_user else None,
            "created_at": _iso(w.created_at, tz), "so_mau": so_mau,
            "ngay_vao_lam": vao_lam.isoformat() if vao_lam else None,
            "ngay_nghi_viec": w.ngay_nghi_viec.isoformat() if w.ngay_nghi_viec else None}


def team_json(t: Team, so_cong_nhan: int | None = None) -> dict:
    return {"id": t.id, "name": t.name, "contractor": t.contractor, "leader_name": t.leader_name,
            "so_cong_nhan": so_cong_nhan}


def sample_json(s: FaceSample, tz) -> dict:
    return {"id": s.id, "worker_id": s.worker_id, "quality": round(s.quality, 3), "source": s.source,
            "created_at": _iso(s.created_at, tz), "anh": f"/api/mau-mat/{s.id}/anh"}


def check_json(c: PpeCheck, tz) -> dict:
    return {"id": c.id, "thoi_diem": _iso(c.checked_at, tz), "gio": cham_cong.gio_phut(c.checked_at, tz),
            "cong_id": c.gate_id,
            "cong_nhan": None if c.worker is None else {"id": c.worker.id, "ma": c.worker.code, "ten": c.worker.full_name},
            "trang_thai_mat": c.face_status, "diem": c.face_score, "ket_qua": c.result, "thieu": c.missing,
            "ty_le_co_mat": c.presence_ratio, "ly_do": c.reason, "thoi_gian_ms": c.duration_ms, "huong": c.direction,
            "hanh_dong": c.action, "ly_do_ghi": c.action_reason, "anh": f"/api/luot/{c.id}/anh" if c.image_path else None,
            "danh_gia": c.review_status, "chi_tiet": c.detail}


def attendance_json(a: Attendance, tz) -> dict:
    return {"id": a.id, "worker_id": a.worker_id, "ngay": a.work_date.isoformat(), "shift_id": a.shift_id,
            "gio_vao": _iso(a.check_in, tz), "gio_ra": _iso(a.check_out, tz), "ppe_check_id": a.ppe_check_id,
            "di_muon_phut": a.late_minutes, "ve_som_phut": a.early_leave_minutes, "so_phut_lam": a.worked_minutes,
            "trang_thai": a.status, "ghi_chu": a.note, "updated_by": a.updated_by, "updated_at": _iso(a.updated_at, tz),
            "so_lan_ra_ngoai": a.so_lan_ra_ngoai, "phut_ra_ngoai": a.phut_ra_ngoai, "phut_cong_tac": a.phut_cong_tac,
            "phien": [bao_cao.phien_json(s, tz) for s in sorted(a.segments, key=lambda s: s.vao_at)]}


def nhat_ky_json(n: NhatKyChamCong, tz) -> dict:
    return {"id": n.id, "worker_id": n.worker_id, "ngay": n.ngay.isoformat(), "attendance_id": n.attendance_id,
            "segment_id": n.segment_id, "phep_id": n.phep_id, "hanh_dong": n.hanh_dong, "gia_tri_cu": n.gia_tri_cu,
            "gia_tri_moi": n.gia_tri_moi, "ly_do": n.ly_do, "user_id": n.user_id,
            "nguoi_sua": (n.user.full_name or n.user.username) if n.user else None, "thoi_diem": _iso(n.thoi_diem, tz)}


def _sample_count(db: Session, worker_id: int) -> int:
    return db.scalar(select(func.count(FaceSample.id)).where(FaceSample.worker_id == worker_id)) or 0


# ---------- dang nhap ----------
class LoginIn(BaseModel):
    username: str
    password: str


@public.post("/dang-nhap")
def api_login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    user = authenticate(db, body.username, body.password)
    if user is None:
        raise HTTPException(401, "Sai tên đăng nhập hoặc mật khẩu")
    login_session(request, user)
    return {"id": user.id, "username": user.username, "full_name": user.full_name}


@public.post("/dang-xuat")
def api_logout(request: Request):
    request.session.clear()
    return {"ok": True}


@router.get("/toi", tags=["dang nhap"])
def me(user: User = Depends(current_user)):
    return {"id": user.id, "username": user.username, "full_name": user.full_name, "role": user.role}


@router.get("/cau-hinh-web", tags=["dang nhap"])
def web_config(request: Request):
    """Tham số cho giao diện web (React) lấy từ settings.yaml (giao diện Jinja2 cũ nhận qua template), và ngày hôm nay
    theo giờ Việt Nam (không phụ thuộc giờ máy của trình duyệt)."""
    s = _state(request).settings
    return {"ngay_hom_nay": cham_cong.ngay_cong(utcnow(), _tz(request)).isoformat(),
            "mui_gio": s["attendance"]["timezone"],
            "mau_toi_thieu": s["face"]["min_samples"], "mau_toi_da": s["face"]["max_samples"],
            "giay_hien_ket_qua": s["web"]["gate_result_seconds"],
            "so_dong_trang": s["web"]["page_size"], "so_dong_toi_da": s["web"]["max_page_size"],
            "tai_len_toi_da_mb": s["web"]["max_upload_mb"]}


# ---------- cong nhan ----------
class WorkerIn(BaseModel):
    code: str = Field(min_length=1, max_length=20, examples=["CN001"])
    full_name: str = Field(min_length=1, max_length=100, examples=["Nguyễn Văn An"])
    phone: str | None = Field(None, max_length=20)
    trade: str | None = Field(None, max_length=50, examples=["Thợ xây"])
    team_id: int | None = None
    ngay_vao_lam: date | None = Field(None, description="YYYY-MM-DD; bỏ trống = hôm nay")


class WorkerPatch(BaseModel):
    code: str | None = Field(None, min_length=1, max_length=20)
    full_name: str | None = Field(None, min_length=1, max_length=100)
    phone: str | None = Field(None, max_length=20)
    trade: str | None = Field(None, max_length=50)
    team_id: int | None = None
    ngay_vao_lam: date | None = None


class ConsentIn(BaseModel):
    dong_y: bool = Field(description="Ô xác nhận: công nhân đồng ý (xem GET /api/dong-y/noi-dung)")


@router.get("/cong-nhan", tags=["cong nhan"])
def list_workers(request: Request, q: str | None = Query(None, description="Tìm theo mã, họ tên, số điện thoại"),
                 to_doi: int | None = None, trang_thai: Literal["dang_lam", "nghi_viec"] | None = None,
                 db: Session = Depends(get_db)):
    counts = (select(FaceSample.worker_id, func.count(FaceSample.id).label("n"))
              .group_by(FaceSample.worker_id).subquery())
    stmt = select(Worker, func.coalesce(counts.c.n, 0)).outerjoin(counts, counts.c.worker_id == Worker.id)
    if q and q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Worker.code.ilike(like), Worker.full_name.ilike(like), Worker.phone.ilike(like)))
    if to_doi is not None:
        stmt = stmt.where(Worker.team_id == to_doi)
    if trang_thai:
        stmt = stmt.where(Worker.status == trang_thai)
    rows = db.execute(stmt.order_by(Worker.code)).all()
    tz = _tz(request)
    return {"tong": len(rows), "ds": [worker_json(w, tz, n) for w, n in rows]}


@router.post("/cong-nhan", status_code=201, tags=["cong nhan"])
def create_worker(body: WorkerIn, request: Request, db: Session = Depends(get_db)):
    data = body.model_dump()
    data["ngay_vao_lam"] = data["ngay_vao_lam"] or cham_cong.ngay_cong(utcnow(), _tz(request))
    w = cong_nhan.tao_cong_nhan(db, data)
    return worker_json(w, _tz(request), 0)


@router.get("/cong-nhan/{worker_id}", tags=["cong nhan"])
def get_worker(worker_id: int, request: Request, db: Session = Depends(get_db)):
    w = _get(db, Worker, worker_id, "công nhân")
    return worker_json(w, _tz(request), _sample_count(db, w.id))


@router.patch("/cong-nhan/{worker_id}", tags=["cong nhan"])
def update_worker(worker_id: int, body: WorkerPatch, request: Request, db: Session = Depends(get_db)):
    w = cong_nhan.sua_cong_nhan(db, _get(db, Worker, worker_id, "công nhân"), body.model_dump(exclude_unset=True))
    return worker_json(w, _tz(request), _sample_count(db, w.id))


@router.post("/cong-nhan/{worker_id}/nghi-viec", tags=["cong nhan"])
def worker_quit(worker_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Cho nghỉ việc: lưu ngày nghỉ việc, đóng phiên đang mở (nếu có) tại lúc này, không còn được nhận diện,
    XOÁ toàn bộ mẫu khuôn mặt (vector + ảnh)."""
    w = _get(db, Worker, worker_id, "công nhân")
    n = cong_nhan.cho_nghi_viec(db, w, _state(request).dang_ky, user)
    return {"cong_nhan": worker_json(w, _tz(request), 0), "so_mau_da_xoa": n}


@router.post("/cong-nhan/{worker_id}/di-lam-lai", tags=["cong nhan"])
def worker_rejoin(worker_id: int, request: Request, db: Session = Depends(get_db)):
    """Nhận lại công nhân đã nghỉ: phải ghi nhận đồng ý và đăng ký khuôn mặt lại."""
    w = cong_nhan.di_lam_lai(db, _get(db, Worker, worker_id, "công nhân"), _state(request).dang_ky)
    return worker_json(w, _tz(request), 0)


@router.get("/cong-nhan/{worker_id}/bang-cong", tags=["cong nhan"])
def worker_recent_attendance(worker_id: int, request: Request, so_ngay: int = Query(14, ge=1, le=366),
                             db: Session = Depends(get_db)):
    """Bảng công các ngày gần đây của 1 công nhân (mới nhất trước)."""
    w = _get(db, Worker, worker_id, "công nhân")
    return {"ds": bao_cao.bang_cong_gan_day(db, w, _state(request).settings["attendance"], utcnow(), so_ngay)}


@router.get("/dong-y/noi-dung", tags=["mau mat"])
def consent_text():
    return {"noi_dung": NOI_DUNG_DONG_Y}


@router.post("/cong-nhan/{worker_id}/dong-y", tags=["mau mat"])
def record_consent(worker_id: int, body: ConsentIn, request: Request, db: Session = Depends(get_db),
                   user: User = Depends(current_user)):
    """Ghi nhận đồng ý đăng ký khuôn mặt (lưu thời điểm và người thực hiện). Bắt buộc trước khi thêm mẫu."""
    if not body.dong_y:
        raise HTTPException(400, "Phải tích ô đồng ý mới ghi nhận được")
    w = _state(request).dang_ky.ghi_nhan_dong_y(db, _get(db, Worker, worker_id, "công nhân"), user)
    return worker_json(w, _tz(request), _sample_count(db, w.id))


# ---------- to doi ----------
class TeamIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    contractor: str | None = Field(None, max_length=100)
    leader_name: str | None = Field(None, max_length=100)


class TeamPatch(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    contractor: str | None = Field(None, max_length=100)
    leader_name: str | None = Field(None, max_length=100)


@router.get("/to-doi", tags=["to doi"])
def list_teams(db: Session = Depends(get_db)):
    counts = dict(db.execute(select(Worker.team_id, func.count(Worker.id)).where(Worker.status == DANG_LAM)
                             .group_by(Worker.team_id)).all())
    return {"ds": [team_json(t, counts.get(t.id, 0)) for t in db.scalars(select(Team).order_by(Team.name))]}


@router.post("/to-doi", status_code=201, tags=["to doi"])
def create_team(body: TeamIn, db: Session = Depends(get_db)):
    return team_json(cong_nhan.tao_to_doi(db, body.model_dump()), 0)


@router.patch("/to-doi/{team_id}", tags=["to doi"])
def update_team(team_id: int, body: TeamPatch, db: Session = Depends(get_db)):
    return team_json(cong_nhan.sua_to_doi(db, _get(db, Team, team_id, "tổ đội"), body.model_dump(exclude_unset=True)))


# ---------- mau khuon mat ----------
def _samples_json(db: Session, w: Worker, request: Request) -> dict:
    face_cfg, tz = _state(request).settings["face"], _tz(request)
    samples = db.scalars(select(FaceSample).where(FaceSample.worker_id == w.id).order_by(FaceSample.id)).all()
    return {"worker_id": w.id, "so_mau": len(samples), "toi_thieu": face_cfg["min_samples"],
            "toi_da": face_cfg["max_samples"], "du_mau": len(samples) >= face_cfg["min_samples"],
            "da_dong_y": w.consent_at is not None, "ds": [sample_json(s, tz) for s in samples]}


@router.get("/cong-nhan/{worker_id}/mau-mat", tags=["mau mat"])
def list_samples(worker_id: int, request: Request, db: Session = Depends(get_db)):
    return _samples_json(db, _get(db, Worker, worker_id, "công nhân"), request)


@router.post("/cong-nhan/{worker_id}/mau-mat/chup", status_code=201, tags=["mau mat"])
def capture_sample(worker_id: int, request: Request, db: Session = Depends(get_db)):
    """Chụp 1 mẫu từ khung hình hiện tại của camera cổng (cần đúng 1 khuôn mặt đủ lớn, rõ)."""
    st = _state(request)
    w = _get(db, Worker, worker_id, "công nhân")
    st.dang_ky.kiem_tra(db, w)  # chua dong y / du mau: bao ngay, khong can chup
    frame = st.gate.latest_frame()
    if frame is None:
        raise HTTPException(503, "Camera cổng chưa chạy, chưa chụp được (xem GET /api/cong/trang-thai)")
    s = st.dang_ky.them_mau(db, w, frame, CAMERA)
    return {"mau": sample_json(s, _tz(request)), "so_mau": _sample_count(db, w.id)}


@router.post("/cong-nhan/{worker_id}/mau-mat/tai-len", tags=["mau mat"])
def upload_samples(worker_id: int, request: Request, files: list[UploadFile] = File(..., description="Một hoặc nhiều ảnh"),
                   db: Session = Depends(get_db)):
    """Tải ảnh lên (nhiều ảnh). Mỗi ảnh cần đúng 1 khuôn mặt. Chỉ lưu vector + ảnh mặt 112×112, KHÔNG lưu ảnh gốc."""
    st = _state(request)
    w = _get(db, Worker, worker_id, "công nhân")
    st.dang_ky.kiem_tra(db, w)
    max_bytes = int(st.settings["web"]["max_upload_mb"] * 1024 * 1024)
    tz, results = _tz(request), []
    for f in files:
        data = f.file.read(max_bytes + 1)
        try:
            if len(data) > max_bytes:
                raise DangKyMatError(f"Ảnh lớn hơn {st.settings['web']['max_upload_mb']} MB")
            image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR) if data else None
            s = st.dang_ky.them_mau(db, w, image, UPLOAD)
            results.append({"ten": f.filename, "ok": True, "ly_do": None, "mau": sample_json(s, tz)})
        except DangKyMatError as e:
            results.append({"ten": f.filename, "ok": False, "ly_do": str(e), "mau": None})
        finally:
            del data  # anh goc chi nam trong bo nho, khong ghi ra dia
    return {"ket_qua": results, "so_mau": _sample_count(db, w.id)}


@router.get("/mau-mat/{sample_id}/anh", tags=["mau mat"])
def sample_image(sample_id: int, request: Request, db: Session = Depends(get_db)):
    path = _state(request).dang_ky.thumb_file(_get(db, FaceSample, sample_id, "mẫu khuôn mặt"))
    if not path.is_file():
        raise HTTPException(404, "Không thấy file ảnh mẫu")
    return FileResponse(path, media_type="image/jpeg")


@router.delete("/mau-mat/{sample_id}", tags=["mau mat"])
def delete_sample(sample_id: int, request: Request, db: Session = Depends(get_db)):
    s = _get(db, FaceSample, sample_id, "mẫu khuôn mặt")
    worker_id = s.worker_id
    _state(request).dang_ky.xoa_mau(db, s)
    return {"ok": True, "so_mau": _sample_count(db, worker_id)}


@router.delete("/cong-nhan/{worker_id}/mau-mat", tags=["mau mat"])
def delete_all_samples(worker_id: int, request: Request, db: Session = Depends(get_db)):
    """Xoá dữ liệu khuôn mặt (toàn bộ vector + ảnh mẫu) của 1 công nhân."""
    n = _state(request).dang_ky.xoa_tat_ca(db, _get(db, Worker, worker_id, "công nhân"))
    return {"so_mau_da_xoa": n}


# ---------- luot kiem tra ----------
@router.get("/luot", tags=["luot kiem tra"])
def list_checks(request: Request, ngay: date | None = Query(None, description="YYYY-MM-DD, giờ Việt Nam"),
                cong_nhan_id: int | None = None, ket_qua: KET_QUA | None = None, hanh_dong: HANH_DONG | None = None,
                trang: int = Query(1, ge=1), so_dong: int | None = Query(None, ge=1), db: Session = Depends(get_db)):
    st, tz = _state(request), _tz(request)
    so_dong = min(so_dong or st.settings["web"]["page_size"], st.settings["web"]["max_page_size"])
    stmt = select(PpeCheck)
    if ngay is not None:
        start, end = cham_cong.khoang_ngay(ngay, tz)
        stmt = stmt.where(PpeCheck.checked_at >= start, PpeCheck.checked_at < end)
    if cong_nhan_id is not None:
        stmt = stmt.where(PpeCheck.worker_id == cong_nhan_id)
    if ket_qua:
        stmt = stmt.where(PpeCheck.result == ket_qua)
    if hanh_dong:
        stmt = stmt.where(PpeCheck.action == hanh_dong)
    tong = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(PpeCheck.checked_at.desc(), PpeCheck.id.desc())
                      .offset((trang - 1) * so_dong).limit(so_dong)).all()
    return {"tong": tong, "trang": trang, "so_dong": so_dong, "so_trang": (tong + so_dong - 1) // so_dong,
            "ds": [check_json(c, tz) for c in rows]}


@router.get("/luot/{check_id}", tags=["luot kiem tra"])
def get_check(check_id: int, request: Request, db: Session = Depends(get_db)):
    return check_json(_get(db, PpeCheck, check_id, "lượt kiểm tra"), _tz(request))


class ReviewIn(BaseModel):
    danh_gia: Literal["dung", "bao_nham"] | None = Field(description="dung / bao_nham; null = bỏ đánh giá")


@router.patch("/luot/{check_id}/danh-gia", tags=["luot kiem tra"])
def review_check(check_id: int, body: ReviewIn, request: Request, db: Session = Depends(get_db)):
    """Cán bộ xác nhận kết quả lượt kiểm tra đúng hay báo nhầm (số liệu để đánh giá hệ thống)."""
    c = _get(db, PpeCheck, check_id, "lượt kiểm tra")
    c.review_status = body.danh_gia
    db.commit()
    return check_json(c, _tz(request))


@router.get("/luot/{check_id}/anh", tags=["luot kiem tra"])
def check_image(check_id: int, request: Request, db: Session = Depends(get_db)):
    c = _get(db, PpeCheck, check_id, "lượt kiểm tra")
    path = _state(request).image_dir / c.image_path if c.image_path else None
    if path is None or not path.is_file():
        raise HTTPException(404, "Lượt này không có ảnh")
    return FileResponse(path, media_type="image/jpeg")


# ---------- cham cong ----------
class ManualIn(BaseModel):
    worker_id: int
    ngay: date = Field(description="YYYY-MM-DD")
    gio_vao: time | None = Field(None, description="HH:MM giờ Việt Nam", examples=["07:00"])
    gio_ra: time | None = Field(None, description="HH:MM giờ Việt Nam", examples=["17:00"])
    ly_do: str = Field(description="Bắt buộc", examples=["Camera cổng hỏng, cán bộ xác nhận có mặt"])


@router.get("/bang-cong", tags=["cham cong"])
def daily_sheet(request: Request, ngay: date | None = Query(None, description="YYYY-MM-DD, mặc định hôm nay"),
                to_doi: int | None = None, db: Session = Depends(get_db)):
    att_cfg, now = _state(request).settings["attendance"], utcnow()
    ngay = ngay or cham_cong.ngay_cong(now, cham_cong.mui_gio(att_cfg))
    return {"ngay": ngay.isoformat(), "ds": bao_cao.bang_cong_ngay(db, ngay, att_cfg, now, to_doi)}


def _month(thang: str | None, request: Request) -> tuple[int, int]:
    if thang is None:
        today = cham_cong.ngay_cong(utcnow(), _tz(request))
        return today.year, today.month
    m = re.fullmatch(r"(\d{4})-(\d{2})", thang)
    if not m or not 1 <= int(m.group(2)) <= 12:
        raise HTTPException(422, "Tháng phải có dạng YYYY-MM, vd 2026-10")
    return int(m.group(1)), int(m.group(2))


@router.get("/bang-cong/thang", tags=["cham cong"])
def monthly_sheet(request: Request, thang: str | None = Query(None, description="YYYY-MM, mặc định tháng này"),
                  to_doi: int | None = None, db: Session = Depends(get_db)):
    nam, th = _month(thang, request)
    return bao_cao.bang_cong_thang(db, nam, th, _state(request).settings["attendance"], utcnow(), to_doi)


@router.get("/bang-cong/thang/excel", tags=["cham cong"])
def monthly_excel(request: Request, thang: str | None = Query(None, description="YYYY-MM"), to_doi: int | None = None,
                  db: Session = Depends(get_db)):
    """Xuất bảng công tháng ra file Excel (.xlsx)."""
    nam, th = _month(thang, request)
    data = bao_cao.bang_cong_thang(db, nam, th, _state(request).settings["attendance"], utcnow(), to_doi)
    return Response(bao_cao.excel_bang_cong_thang(data),
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="bang_cong_{nam:04d}_{th:02d}.xlsx"'})


@router.post("/cham-cong-thu-cong", tags=["cham cong"])
def manual_attendance(body: ManualIn, request: Request, db: Session = Depends(get_db),
                      user: User = Depends(current_user)):
    """Thêm hoặc sửa giờ vào/ra CỦA NGÀY (giữ cho giao diện cũ). Ngày chưa có phiên: thêm 1 phiên; đã có: giờ vào sửa
    phiên đầu, giờ ra sửa (hoặc đóng) phiên cuối. Bắt buộc có lý do; mỗi thay đổi 1 dòng nhật ký."""
    w = _get(db, Worker, body.worker_id, "công nhân")
    a = cham_cong.cham_thu_cong(db, w, body.ngay, body.gio_vao, body.gio_ra, body.ly_do, user,
                                _state(request).settings["attendance"])
    return attendance_json(a, _tz(request))


@router.get("/bang-cong/cong-nhan/{worker_id}/{ngay}", tags=["cham cong"])
def day_detail(worker_id: int, ngay: date, request: Request, db: Session = Depends(get_db)):
    """Bảng công 1 ngày của 1 công nhân: trạng thái, các phiên, các phép, nhật ký sửa."""
    st, tz = _state(request), _tz(request)
    w = _get(db, Worker, worker_id, "công nhân")
    row = bao_cao.chi_tiet_ngay(db, w, ngay, st.settings["attendance"], utcnow())
    logs = db.scalars(select(NhatKyChamCong).where(NhatKyChamCong.worker_id == w.id, NhatKyChamCong.ngay == ngay)
                      .order_by(NhatKyChamCong.thoi_diem, NhatKyChamCong.id)).all()
    return {**row, "nhat_ky": [nhat_ky_json(n, tz) for n in logs]}


@router.get("/bang-cong/{attendance_id}/nhat-ky", tags=["cham cong"])
def attendance_log(attendance_id: int, request: Request, db: Session = Depends(get_db)):
    """Nhật ký mọi thao tác tay của 1 ngày công (giá trị cũ, mới, người sửa, lý do), cũ trước."""
    a = _get(db, Attendance, attendance_id, "dòng bảng công")
    logs = db.scalars(select(NhatKyChamCong).where(or_(NhatKyChamCong.attendance_id == a.id, (
        NhatKyChamCong.worker_id == a.worker_id) & (NhatKyChamCong.ngay == a.work_date)))
                      .order_by(NhatKyChamCong.thoi_diem, NhatKyChamCong.id)).all()
    return {"attendance_id": a.id, "ds": [nhat_ky_json(n, _tz(request)) for n in logs]}


class SegmentIn(BaseModel):
    worker_id: int
    ngay: date = Field(description="YYYY-MM-DD (ngày công)")
    gio_vao: time = Field(description="HH:MM[:SS] giờ Việt Nam", examples=["07:00"])
    gio_ra: time | None = Field(None, description="bỏ trống = phiên đang mở", examples=["17:00"])
    ly_do: str = Field(description="Bắt buộc")


class SegmentPatch(BaseModel):
    gio_vao: time | None = None
    gio_ra: time | None = Field(None, description="nhập giờ ra cho phiên đang mở / thiếu giờ ra = đóng phiên")
    ly_do: str = Field(description="Bắt buộc")


class ReasonIn(BaseModel):
    ly_do: str = Field(description="Bắt buộc")


def _day_json(db: Session, a: Attendance, request: Request) -> dict:
    return bao_cao.chi_tiet_ngay(db, a.worker, a.work_date, _state(request).settings["attendance"], utcnow())


@router.post("/phien", status_code=201, tags=["cham cong"])
def add_segment(body: SegmentIn, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Chấm tay: thêm 1 phiên. Từ chối: thời điểm chưa tới, giờ ra ≤ giờ vào, chồng lấn phiên khác, ngoài thời gian
    làm việc của công nhân, đã có phiên mở mà thêm phiên mở nữa."""
    w = _get(db, Worker, body.worker_id, "công nhân")
    s = cham_cong.them_phien(db, w, body.ngay, body.gio_vao, body.gio_ra, body.ly_do, user,
                             _state(request).settings["attendance"])
    return {"phien": bao_cao.phien_json(s, _tz(request)), "ngay": _day_json(db, s.attendance, request)}


@router.patch("/phien/{segment_id}", tags=["cham cong"])
def edit_segment(segment_id: int, body: SegmentPatch, request: Request, db: Session = Depends(get_db),
                 user: User = Depends(current_user)):
    """Chấm tay: sửa giờ vào / giờ ra của 1 phiên (kể cả đóng phiên thiếu giờ ra). Mỗi thay đổi 1 dòng nhật ký."""
    s = cham_cong.sua_phien(db, _get(db, AttendanceSegment, segment_id, "phiên"), body.gio_vao, body.gio_ra,
                            body.ly_do, user, _state(request).settings["attendance"])
    return {"phien": bao_cao.phien_json(s, _tz(request)), "ngay": _day_json(db, s.attendance, request)}


@router.post("/phien/{segment_id}/huy", tags=["cham cong"])
def cancel_segment(segment_id: int, body: ReasonIn, request: Request, db: Session = Depends(get_db),
                   user: User = Depends(current_user)):
    s = cham_cong.huy_phien(db, _get(db, AttendanceSegment, segment_id, "phiên"), body.ly_do, user,
                            _state(request).settings["attendance"])
    return {"phien": bao_cao.phien_json(s, _tz(request)), "ngay": _day_json(db, s.attendance, request)}


# ---------- phep / giai trinh ----------
class PhepIn(BaseModel):
    worker_id: int
    ngay: date = Field(description="YYYY-MM-DD (ngày công)")
    loai: Literal[LOAI_PHEP] = Field(description="ve_som | di_muon | ra_ngoai_cong_viec | nghi_ca_ngay")
    tu_gio: time | None = Field(None, description="về sớm: giờ được về; ra ngoài: từ giờ")
    den_gio: time | None = Field(None, description="đi muộn: giờ dự kiến đến; ra ngoài: đến giờ")
    tinh_cong: bool | None = Field(None, description="mặc định: có cho ra_ngoai_cong_viec, không cho loại khác")
    ly_do: str = Field(description="Bắt buộc")


@router.get("/phep", tags=["phep"])
def list_leaves(request: Request, worker_id: int | None = None, ngay: date | None = None, tu: date | None = None,
                den: date | None = None, ca_huy: bool = False, db: Session = Depends(get_db)):
    """Liệt kê phép theo công nhân và / hoặc theo ngày (mới nhất trước)."""
    tz = _tz(request)
    return {"ds": [bao_cao.phep_json(p, tz) for p in phep.liet_ke(db, worker_id, ngay, tu, den, ca_huy)]}


@router.post("/phep", status_code=201, tags=["phep"])
def add_leave(body: PhepIn, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    w = _get(db, Worker, body.worker_id, "công nhân")
    p = phep.them_phep(db, w, body.ngay, body.loai, body.ly_do, user, _state(request).settings["attendance"],
                       tu_gio=body.tu_gio, den_gio=body.den_gio, tinh_cong=body.tinh_cong)
    return bao_cao.phep_json(p, _tz(request))


@router.post("/phep/{phep_id}/huy", tags=["phep"])
def cancel_leave(phep_id: int, body: ReasonIn, request: Request, db: Session = Depends(get_db),
                 user: User = Depends(current_user)):
    p = phep.huy_phep(db, _get(db, Phep, phep_id, "phép"), body.ly_do, user, _state(request).settings["attendance"])
    return bao_cao.phep_json(p, _tz(request))


# ---------- viec can xu ly ----------
@router.get("/viec-can-xu-ly", tags=["cham cong"])
def todo_list(request: Request, db: Session = Depends(get_db)):
    """Ngày thiếu giờ ra; ngày đi muộn / về sớm KHÔNG phép quá ngưỡng (attendance.nguong_can_giai_trinh_phut)."""
    ds = bao_cao.viec_can_xu_ly(db, _state(request).settings["attendance"], utcnow())
    return {"tong": len(ds), "ds": ds}


class ConfirmIn(BaseModel):
    attendance_id: int
    ly_do: str | None = None


@router.post("/viec-can-xu-ly/xac-nhan-khong-phep", tags=["cham cong"])
def confirm_no_leave(body: ConfirmIn, request: Request, db: Session = Depends(get_db),
                     user: User = Depends(current_user)):
    """Xác nhận ngày đi muộn / về sớm là KHÔNG có phép: ghi nhật ký, rời khỏi danh sách Việc cần xử lý."""
    a = cham_cong.xac_nhan_khong_phep(db, _get(db, Attendance, body.attendance_id, "dòng bảng công"), body.ly_do, user,
                                      _state(request).settings["attendance"])
    return _day_json(db, a, request)


@router.get("/tong-quan", tags=["cham cong"])
def overview(request: Request, db: Session = Depends(get_db)):
    st, tz = _state(request), _tz(request)
    data = bao_cao.tong_quan(db, st.settings["attendance"], utcnow())
    data["luot_moi_nhat"] = [check_json(c, tz) for c in data["luot_moi_nhat"]]
    data["cong"] = st.gate.status()
    return data


# ---------- ca lam ----------
class ShiftPatch(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=50)
    start_time: time | None = Field(None, examples=["07:00"])
    end_time: time | None = Field(None, examples=["17:00"])
    break_start: time | None = Field(None, examples=["11:30"])
    break_minutes: int | None = Field(None, ge=0, le=240)
    grace_minutes: int | None = Field(None, ge=0, le=120)
    early_checkin_minutes: int | None = Field(None, ge=0, le=240)
    phut_chong_trung: int | None = Field(None, ge=1, le=120, description="2 lần ghi công cách nhau dưới chừng này phút "
                                                                       "-> bỏ qua trùng")
    ngay_nghi_tuan: list[Literal[tuple(THU)]] | None = Field(None, examples=[["chu_nhat"]],
                                                             description="ngày nghỉ hằng tuần; [] = không nghỉ ngày nào")


def shift_json(s: Shift, att_cfg: dict) -> dict:
    return {"id": s.id, "name": s.name, "start_time": f"{s.start_time:%H:%M}", "end_time": f"{s.end_time:%H:%M}",
            "break_start": f"{s.break_start:%H:%M}", "break_minutes": s.break_minutes, "grace_minutes": s.grace_minutes,
            "early_checkin_minutes": s.early_checkin_minutes, "phut_chong_trung": s.phut_chong_trung,
            "ngay_nghi_tuan": cham_cong.ngay_nghi_tuan(s, att_cfg)}


@router.get("/ca-lam", tags=["ca lam"])
def get_shift(request: Request, db: Session = Depends(get_db)):
    return shift_json(cham_cong.ca_mac_dinh(db), _state(request).settings["attendance"])


@router.patch("/ca-lam", tags=["ca lam"])
def update_shift(body: ShiftPatch, request: Request, db: Session = Depends(get_db)):
    """Sửa ca mặc định. Bảng công HÔM NAY được tính lại theo ca mới; các ngày trước giữ nguyên."""
    att_cfg = _state(request).settings["attendance"]
    shift = cham_cong.ca_mac_dinh(db)
    n = cham_cong.sua_ca(db, shift, body.model_dump(exclude_unset=True), att_cfg)
    return {**shift_json(shift, att_cfg), "so_dong_tinh_lai": n}


# ---------- cong ----------
FULL_FRAME = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]


class GatePatch(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=50)
    camera_source: str | None = Field(None, min_length=1, max_length=500,
                                      examples=["0", "http://192.168.1.10:4747/video/force/1280x720"])
    rotate: Literal[0, 90, 180, 270] | None = Field(None, description="Xoay hình theo chiều kim đồng hồ (độ)")
    zone: list[list[float]] | None = Field(None, description="Vùng kiểm tra: các điểm [x, y] tỷ lệ 0–1 trên hình ĐÃ xoay")
    khoi_dong_lai: bool = Field(True, description="Khởi động lại cổng để áp dụng ngay")


def gate_json(g: Gate, request: Request) -> dict:
    cfg = _state(request).cfg
    return {"id": g.id, "name": g.name, "camera_source": mask_source(g.camera_source), "rotate": g.rotate, "zone": g.zone,
            "required_ppe": g.required_ppe, "ghi_de_boi_env": cfg.gate_source is not None,
            "nguon_env": mask_source(cfg.gate_source)}


def _gate_row(db: Session) -> Gate:
    g = db.scalar(select(Gate).order_by(Gate.id).limit(1))
    if g is None:
        raise HTTPException(404, "Chưa có cổng trong CSDL: chạy scripts\\seed_demo.py")
    return g


@router.get("/cong", tags=["cong"])
def get_gate(request: Request, db: Session = Depends(get_db)):
    """Cấu hình cổng: nguồn camera, góc xoay, vùng kiểm tra."""
    return gate_json(_gate_row(db), request)


@router.patch("/cong", tags=["cong"])
def update_gate(body: GatePatch, request: Request, db: Session = Depends(get_db)):
    """Sửa nguồn camera / góc xoay / vùng kiểm tra rồi khởi động lại cổng. Đổi góc xoay mà không gửi vùng mới thì vùng
    đặt lại thành cả khung hình (vùng cũ vẽ trên hình xoay khác). URL có mật khẩu: đặt GATE_SOURCE trong .env."""
    g = _gate_row(db)
    note = None
    if body.camera_source is not None:
        src = body.camera_source.strip()
        if "://" in src and "@" in src:
            raise HTTPException(400, "URL camera có mật khẩu: đặt GATE_SOURCE trong file .env, không lưu vào CSDL")
        g.camera_source = src
    if body.zone is not None:
        try:
            zone_to_pixels(body.zone, 1, 1)  # >= 3 diem, trong khoang 0-1
        except ValueError as e:
            raise HTTPException(400, f"Vùng kiểm tra không hợp lệ: {e}")
        g.zone = [[round(float(x), 4), round(float(y), 4)] for x, y in body.zone]
    if body.rotate is not None and body.rotate != g.rotate:
        g.rotate = body.rotate
        if body.zone is None:
            g.zone, note = FULL_FRAME, "Đã đổi góc xoay: vùng kiểm tra đặt lại thành cả khung hình, cần vẽ lại vùng"
    if body.name is not None:
        g.name = body.name.strip()
    db.commit()
    gate = _state(request).gate
    if body.khoi_dong_lai:
        gate.restart()
    return {**gate_json(g, request), "ghi_chu": note, "trang_thai": gate.status()}


@router.get("/cong/anh-hien-tai", tags=["cong"])
def gate_snapshot(request: Request):
    """Khung hình hiện tại của camera cổng (đã xoay, không vẽ gì), để vẽ vùng kiểm tra. Lấy từ luồng đọc camera dùng
    chung, không mở thêm kết nối tới camera (DroidCam chỉ cho 1 kết nối)."""
    frame = _state(request).gate.latest_frame()
    if frame is None:
        raise HTTPException(503, "Chưa có hình từ camera cổng")
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return Response(buf.tobytes(), media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@router.get("/cong/trang-thai", tags=["cong"])
def gate_status(request: Request):
    return _state(request).gate.status()


@router.post("/cong/khoi-dong-lai", tags=["cong"])
def gate_restart(request: Request):
    """Mở lại camera + vòng lặp cổng (vd sau khi cắm lại camera). Mô hình đã nạp thì không nạp lại."""
    gate = _state(request).gate
    gate.restart()
    return gate.status()
