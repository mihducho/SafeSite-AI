"""Trang HTML. F2 chi co: dang nhap/dang xuat va trang /docs (thu API) - ca hai deu ngoai /api.
Moi trang tru /login deu can dang nhap (chua dang nhap -> chuyen ve /login?next=...). Giao dien day du lam o F3."""
import html

from fastapi import APIRouter, Depends, Form, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import authenticate, login_session, page_user
from app.db import get_db
from app.models import User

router = APIRouter(include_in_schema=False)

LOGIN_PAGE = """<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>SafeGate - Đăng nhập</title>
<style>body{{font-family:system-ui,sans-serif;background:#f4f6f8;display:flex;justify-content:center;padding-top:12vh}}
form{{background:#fff;padding:28px;border-radius:8px;box-shadow:0 2px 8px #0002;width:300px}}
input{{width:100%;padding:8px;margin:6px 0 14px;box-sizing:border-box}}button{{width:100%;padding:10px}}
.err{{color:#b00020}}</style></head>
<body><form method="post" action="/login"><h2>SafeGate</h2>{error}
<label>Tên đăng nhập<input name="username" autofocus required></label>
<label>Mật khẩu<input name="password" type="password" required></label>
<input type="hidden" name="next" value="{next}"><button type="submit">Đăng nhập</button></form></body></html>"""


def _safe_next(url: str | None) -> str:
    """Chi cho chuyen toi duong dan trong ung dung (chan chuyen huong ra trang ngoai)."""
    return url if url and url.startswith("/") and not url.startswith("//") else "/docs"


@router.get("/login", response_class=HTMLResponse)
def login_form(next: str = "/docs", error: str | None = None):
    err = f'<p class="err">{html.escape(error)}</p>' if error else ""
    return LOGIN_PAGE.format(error=err, next=html.escape(_safe_next(next)))


@router.post("/login")
def login_submit(request: Request, username: str = Form(...), password: str = Form(...), next: str = Form("/docs"),
                 db: Session = Depends(get_db)):
    user = authenticate(db, username, password)
    if user is None:
        return HTMLResponse(login_form(next, "Sai tên đăng nhập hoặc mật khẩu"), status_code=401)
    login_session(request, user)
    return RedirectResponse(_safe_next(next), status_code=303)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@router.get("/")
def home(user: User = Depends(page_user)):
    return RedirectResponse("/docs", status_code=303)  # F3: trang tong quan


@router.get("/docs", response_class=HTMLResponse)
def docs(user: User = Depends(page_user)):
    return get_swagger_ui_html(openapi_url="/openapi.json", title="SafeGate API")


@router.get("/openapi.json")
def openapi(request: Request, user: User = Depends(page_user)):
    return JSONResponse(request.app.openapi())
