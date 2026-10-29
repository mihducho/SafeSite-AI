"""Trang HTML (DE_TAI.md muc 9.1, 12 F3): Jinja2 + Bootstrap 5 + JavaScript thuan.

Trang chi la khung (bo cuc, form, bang trong); du lieu do JavaScript (app/static/js/) lay tu API JSON cua F2 va cap nhat
truc tiep qua WebSocket /ws/events. Moi trang tru /login deu can dang nhap (chua dang nhap -> /login?next=...).
Bootstrap va moi file tinh nam trong app/static/ (khong dung CDN: phong thi co the khong co mang).
"""
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import authenticate, login_session, page_user
from app.db import get_db, utcnow
from app.models import User, Worker
from app.services.cham_cong import mui_gio, ngay_cong

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))
ASSET_VERSION = "f3c"  # doi khi sua file tinh de trinh duyet tai lai (khong dung ban cu trong bo nho dem)

NAV = [  # (khoa, duong dan, ten tren menu)
    ("tong_quan", "/", "Tổng quan"),
    ("cong", "/cong", "Màn hình cổng"),
    ("cong_nhan", "/cong-nhan", "Công nhân"),
    ("to_doi", "/to-doi", "Tổ đội"),
    ("lich_su", "/lich-su", "Lịch sử kiểm tra"),
    ("bang_cong", "/bang-cong", "Bảng công"),
    ("ca_lam", "/ca-lam", "Ca làm"),
    ("cau_hinh_cong", "/cau-hinh-cong", "Cấu hình cổng"),
]


def render(request: Request, name: str, user: User | None, active: str = "", title: str = "", status: int = 200,
           **ctx) -> HTMLResponse:
    settings = request.app.state.settings
    today = ngay_cong(utcnow(), mui_gio(settings["attendance"]))
    return templates.TemplateResponse(request, name, {
        "user": user, "nav": NAV, "active": active, "title": title, "today": today.isoformat(), "v": ASSET_VERSION,
        "web": settings["web"], "min_samples": settings["face"]["min_samples"],
        "max_samples": settings["face"]["max_samples"], **ctx}, status_code=status)


def _safe_next(url: str | None) -> str:
    """Chi cho chuyen toi duong dan trong ung dung (chan chuyen huong ra trang ngoai)."""
    return url if url and url.startswith("/") and not url.startswith("//") else "/"


# ---------- dang nhap ----------
@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request, next: str = "/"):
    return render(request, "login.html", None, title="Đăng nhập", next=_safe_next(next), error=None)


@router.post("/login")
def login_submit(request: Request, username: str = Form(...), password: str = Form(...), next: str = Form("/"),
                 db: Session = Depends(get_db)):
    user = authenticate(db, username, password)
    if user is None:
        return render(request, "login.html", None, title="Đăng nhập", next=_safe_next(next), status=401,
                      error="Sai tên đăng nhập hoặc mật khẩu", username=username)
    login_session(request, user)
    return RedirectResponse(_safe_next(next), status_code=303)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


# ---------- cac trang ----------
@router.get("/", response_class=HTMLResponse)
def home(request: Request, user: User = Depends(page_user)):
    return render(request, "tong_quan.html", user, "tong_quan", "Tổng quan")


@router.get("/cong", response_class=HTMLResponse)
def gate_screen(request: Request, user: User = Depends(page_user)):
    return render(request, "cong.html", user, "cong", "Màn hình cổng")


@router.get("/cong-nhan", response_class=HTMLResponse)
def workers_page(request: Request, user: User = Depends(page_user)):
    return render(request, "cong_nhan.html", user, "cong_nhan", "Công nhân")


@router.get("/cong-nhan/{worker_id}", response_class=HTMLResponse)
def worker_page(worker_id: int, request: Request, user: User = Depends(page_user), db: Session = Depends(get_db)):
    w = db.get(Worker, worker_id)
    if w is None:
        return render(request, "loi.html", user, "cong_nhan", "Không tìm thấy", status=404,
                      message=f"Không có công nhân id={worker_id}.")
    return render(request, "chi_tiet_cong_nhan.html", user, "cong_nhan", f"{w.code} - {w.full_name}", worker=w)


@router.get("/to-doi", response_class=HTMLResponse)
def teams_page(request: Request, user: User = Depends(page_user)):
    return render(request, "to_doi.html", user, "to_doi", "Tổ đội")


@router.get("/lich-su", response_class=HTMLResponse)
def history_page(request: Request, user: User = Depends(page_user)):
    return render(request, "lich_su.html", user, "lich_su", "Lịch sử kiểm tra")


@router.get("/bang-cong", response_class=HTMLResponse)
def sheet_page(request: Request, user: User = Depends(page_user)):
    return render(request, "bang_cong.html", user, "bang_cong", "Bảng công")


@router.get("/bang-cong/thang", response_class=HTMLResponse)
def monthly_page(request: Request, user: User = Depends(page_user)):
    return render(request, "bang_cong_thang.html", user, "bang_cong", "Bảng công tháng")


@router.get("/ca-lam", response_class=HTMLResponse)
def shift_page(request: Request, user: User = Depends(page_user)):
    return render(request, "ca_lam.html", user, "ca_lam", "Ca làm")


@router.get("/cau-hinh-cong", response_class=HTMLResponse)
def gate_config_page(request: Request, user: User = Depends(page_user)):
    return render(request, "cau_hinh_cong.html", user, "cau_hinh_cong", "Cấu hình cổng")


# ---------- thu API (Swagger) ----------
@router.get("/docs", response_class=HTMLResponse)
def docs(user: User = Depends(page_user)):
    return get_swagger_ui_html(openapi_url="/openapi.json", title="SafeGate API")  # can mang (Swagger tai tu CDN)


@router.get("/openapi.json")
def openapi(request: Request, user: User = Depends(page_user)):
    return JSONResponse(request.app.openapi())
