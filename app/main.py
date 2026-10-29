"""Ung dung FastAPI SafeGate (DE_TAI.md muc 8, 12 F2). Chay tu thu muc goc du an:

    .venv\\Scripts\\python.exe -m uvicorn app.main:app --port 8000
    -> mo http://127.0.0.1:8000/login, dang nhap roi thu API o /docs

Khoi dong (lifespan): tao bang neu chua co -> lay event loop cho Broadcaster -> bat cong (GateService, thread nen)
-> theo doi trang thai cong. Tat ung dung: dung vong lap cong va camera.
create_app(start_gate=False): khong bat cong (test, hoac GATE_ENABLED=0 trong .env).
"""
import asyncio
import logging
import signal
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool
from starlette.middleware.sessions import SessionMiddleware

from app.auth import LoginRequired
from app.config import AppConfig, load_app_config
from app.db import Database
from app.events import Broadcaster
from app.gate_service import GateService
from app.models import User
from app.routers import api, pages, stream, ws
from app.services.cham_cong import ChamCongError
from app.services.cong_nhan import CongNhanError
from app.services.dang_ky_mat import DangKyMat, DangKyMatError
from app.services.nhan_dien import NhanDien

log = logging.getLogger("uvicorn.error")  # in cung cho voi thong bao cua uvicorn


def enroll_models(face_cfg: dict):
    """Bo YuNet + SFace rieng cho dang ky khuon mat (vong lap cong dung bo khac)."""
    from src.face.face_detector import face_detector_from_settings
    from src.face.face_embedder import face_embedder_from_settings
    return face_detector_from_settings(face_cfg), face_embedder_from_settings(face_cfg)


def install_exit_hook(loop: asyncio.AbstractEventLoop, on_exit):
    """Ctrl+C (hoac lenh tat): goi on_exit NGAY, roi moi chuyen cho uvicorn. Neu khong, uvicorn cho moi trinh duyet ngat
    ket noi (luong hinh MJPEG, WebSocket khong bao gio tu dong) moi chay phan tat cua lifespan -> vong lap cong van chay,
    van giu camera va ghi CSDL du cua so lenh bao "Shutting down". Tra ve ham go bo (dat lai xu ly cu)."""
    if threading.current_thread() is not threading.main_thread():  # vd TestClient: khong co tin hieu
        return lambda: None
    saved = {}
    for name in ("SIGINT", "SIGTERM", "SIGBREAK"):
        sig = getattr(signal, name, None)
        if sig is None:
            continue
        prev = signal.getsignal(sig)

        def handler(signum, frame, prev=prev):
            loop.call_soon_threadsafe(on_exit)
            if callable(prev):
                prev(signum, frame)
            elif signum == signal.SIGINT:
                raise KeyboardInterrupt
        signal.signal(sig, handler)
        saved[sig] = prev

    def restore():
        for sig, prev in saved.items():
            signal.signal(sig, prev)
    return restore


def create_app(cfg: AppConfig | None = None, *, start_gate: bool | None = None, face_models=None, gate_models=None,
               reader_factory=None) -> FastAPI:
    """face_models / gate_models / reader_factory: thay mo hinh va camera bang bo gia khi test."""
    cfg = cfg or load_app_config()
    settings = cfg.settings
    db = Database(cfg.database_url)
    nhan_dien = NhanDien(settings["face"])
    dang_ky = DangKyMat(settings, settings["paths"]["face_samples"], nhan_dien,
                        face_models or (lambda: enroll_models(settings["face"])))
    events = Broadcaster()
    gate = GateService(cfg, db, nhan_dien, events, settings["paths"]["check_images"], gate_models, reader_factory)
    run_gate = cfg.gate_enabled if start_gate is None else start_gate

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        db.create_all()
        events.bind(asyncio.get_running_loop())
        log.info("SafeGate: CSDL %s", db.kind)
        with db.session() as s:
            if not s.scalar(select(func.count(User.id))):
                log.warning("Chua co tai khoan quan tri: chay  .venv\\Scripts\\python.exe scripts\\seed_demo.py")
        if not cfg.secret_from_env:
            log.warning("Chua dat SECRET_KEY trong .env: dung khoa tam, khoi dong lai thi phai dang nhap lai")
        if run_gate:
            gate.start()
        watcher = asyncio.create_task(ws.watch_gate_status(gate, events))

        def on_exit():  # Ctrl+C: dung cong + camera ngay, ket thuc luong hinh va WebSocket de uvicorn tat duoc
            app.state.shutting_down.set()
            threading.Thread(target=gate.stop, name="gate-stop", daemon=True).start()
        restore = install_exit_hook(asyncio.get_running_loop(), on_exit)
        try:
            yield
        finally:
            restore()
            watcher.cancel()
            await run_in_threadpool(gate.stop)

    app = FastAPI(title="SafeGate API", version="F2", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None,
                  description="Chấm công bằng khuôn mặt + kiểm tra bảo hộ tại cổng. Đăng nhập ở /login trước khi thử.")
    app.add_middleware(SessionMiddleware, secret_key=cfg.secret_key, session_cookie="safegate_session",
                       max_age=int(settings["web"]["session_hours"] * 3600), same_site="lax")
    app.state.cfg, app.state.settings, app.state.db = cfg, settings, db
    app.state.nhan_dien, app.state.dang_ky, app.state.events, app.state.gate = nhan_dien, dang_ky, events, gate
    app.state.image_dir = settings["paths"]["check_images"]
    app.state.shutting_down = asyncio.Event()  # dat khi Ctrl+C: luong hinh, WebSocket tu ket thuc

    @app.exception_handler(LoginRequired)
    async def _login_required(request: Request, exc: LoginRequired):
        return RedirectResponse(f"/login?next={quote(exc.next_url)}", status_code=303)

    async def _bad_request(request: Request, exc: Exception):
        return JSONResponse({"detail": str(exc)}, status_code=400)

    for exc_type in (DangKyMatError, ChamCongError, CongNhanError):
        app.add_exception_handler(exc_type, _bad_request)

    @app.exception_handler(IntegrityError)
    async def _conflict(request: Request, exc: IntegrityError):
        return JSONResponse({"detail": "Dữ liệu bị trùng hoặc tham chiếu không hợp lệ"}, status_code=409)

    for r in (pages.router, api.public, api.router, ws.router, stream.router):
        app.include_router(r)
    # Bootstrap, CSS, JavaScript: phuc vu tu may (khong CDN), khong can dang nhap (trang /login cung dung)
    app.mount("/static", StaticFiles(directory=Path(__file__).resolve().parent / "static"), name="static")
    return app


app = create_app()
