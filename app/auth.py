"""Dang nhap (DE_TAI.md muc 12, F2): mat khau bam, phien dang nhap luu trong cookie co chu ky (SessionMiddleware).

Bam mat khau: PBKDF2-HMAC-SHA256 cua thu vien chuan hashlib, muoi ngau nhien 16 byte, 600 000 vong lap.
Chuoi luu trong users.password_hash:  pbkdf2_sha256$<so vong>$<muoi base64>$<ket qua base64>
Cookie chi chua id nguoi dung (kem chu ky bang SECRET_KEY, khong sua duoc); khong chua mat khau.
"""
import base64
import hashlib
import hmac
import secrets

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User

ITERATIONS = 600_000
SESSION_KEY = "user_id"


def hash_password(password: str, iterations: int = ITERATIONS) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    b64 = lambda b: base64.b64encode(b).decode("ascii")  # noqa: E731
    return f"pbkdf2_sha256${iterations}${b64(salt)}${b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt, digest = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        got = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), base64.b64decode(salt), int(iterations))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(got, base64.b64decode(digest))  # so sanh khong lo thoi gian


def authenticate(db: Session, username: str, password: str) -> User | None:
    user = db.query(User).filter(User.username == username.strip()).one_or_none()
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        return None
    return user


def login_session(request: Request, user: User) -> None:
    request.session.clear()
    request.session[SESSION_KEY] = user.id


def session_user(session: dict, db: Session) -> User | None:
    """Nguoi dung dang dang nhap theo cookie (dung cho ca HTTP va WebSocket)."""
    uid = session.get(SESSION_KEY)
    user = db.get(User, uid) if isinstance(uid, int) else None
    return user if user is not None and user.is_active else None


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Dependency cho API: chua dang nhap -> 401."""
    user = session_user(request.session, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Chưa đăng nhập")
    return user


class LoginRequired(Exception):
    """Trang HTML khi chua dang nhap -> chuyen ve /login (xu ly o main.py)."""

    def __init__(self, next_url: str):
        self.next_url = next_url


def page_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Dependency cho trang HTML: chua dang nhap -> chuyen ve trang dang nhap."""
    user = session_user(request.session, db)
    if user is None:
        raise LoginRequired(request.url.path)
    return user
