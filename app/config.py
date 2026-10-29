"""Cau hinh ung dung web = configs/settings.yaml (tham so) + .env (bi mat), DE_TAI.md muc 8, 14.6.

.env nam o thu muc goc du an, KHONG dua vao git (mau: .env.example). Bien moi truong cung ten ghi de .env.
  DATABASE_URL     sqlite:///data/safegate.db  hoac  postgresql+psycopg://user:mat_khau@localhost:5432/safegate
  SECRET_KEY       chuoi ngau nhien de ky cookie dang nhap
  ADMIN_USERNAME, ADMIN_PASSWORD   tai khoan quan tri ban dau (scripts/seed_demo.py tao)
  GATE_SOURCE      (tuy chon) ghi de nguon hinh cua cong: so webcam, URL dien thoai, file video
  GATE_ENABLED     (tuy chon) 0 = khong chay vong lap cong (chi xem web, chay test)
"""
import secrets
from dataclasses import dataclass
from pathlib import Path

from starlette.config import Config

from src.config import DEFAULT_SETTINGS, ROOT, load_settings

ENV_FILE = ROOT / ".env"
DEFAULT_DATABASE_URL = "sqlite:///data/safegate.db"


@dataclass
class AppConfig:
    settings: dict
    database_url: str
    secret_key: str
    admin_username: str = "admin"
    admin_password: str | None = None
    gate_source: str | None = None
    gate_enabled: bool = True
    secret_from_env: bool = True  # False: SECRET_KEY ngau nhien moi lan chay (khoi dong lai thi phai dang nhap lai)


def normalize_database_url(url: str) -> str:
    """postgresql:// -> postgresql+psycopg:// (dung psycopg 3); SQLite duong dan tuong doi -> tinh tu thu muc goc du an."""
    url = url.strip()
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            url = "postgresql+psycopg://" + url[len(prefix):]
    if url.startswith("sqlite:///") and url != "sqlite:///:memory:":
        path = Path(url[len("sqlite:///"):])
        if not path.is_absolute():
            url = "sqlite:///" + (ROOT / path).as_posix()
    return url


def load_app_config(env_file: str | Path = ENV_FILE, settings_path: str | Path = DEFAULT_SETTINGS) -> AppConfig:
    env_file = Path(env_file)
    env = Config(env_file if env_file.exists() else None)
    secret = env("SECRET_KEY", default="")
    gate_source = env("GATE_SOURCE", default="").strip()
    return AppConfig(
        settings=load_settings(settings_path),
        database_url=normalize_database_url(env("DATABASE_URL", default=DEFAULT_DATABASE_URL)),
        secret_key=secret or secrets.token_urlsafe(32),
        admin_username=env("ADMIN_USERNAME", default="admin"),
        admin_password=env("ADMIN_PASSWORD", default="") or None,
        gate_source=gate_source or None,
        gate_enabled=env("GATE_ENABLED", cast=str, default="1").strip().lower() not in ("0", "false", "no", "off"),
        secret_from_env=bool(secret),
    )


def mask_source(source: str | None) -> str | None:
    """An mat khau trong URL camera truoc khi hien len web (rtsp://user:pass@host -> rtsp://user:***@host)."""
    if not source or "://" not in source or "@" not in source:
        return source
    scheme, rest = source.split("://", 1)
    cred, host = rest.rsplit("@", 1)
    user = cred.split(":", 1)[0]
    return f"{scheme}://{user}:***@{host}"
