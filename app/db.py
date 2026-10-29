"""Ket noi CSDL bang SQLAlchemy 2 (DE_TAI.md muc 4, 10). Chay duoc voi PostgreSQL va SQLite, chi doi DATABASE_URL.

- Thoi diem luu kem mui gio, quy ve UTC (UTCDateTime). SQLite khong luu mui gio nen ghi gio UTC khong kem mui gio
  va khi doc ra gan lai UTC; PostgreSQL dung kieu timestamptz. Ngay cong va gio hien thi tinh theo Asia/Ho_Chi_Minh
  o tang nghiep vu (services/cham_cong.py).
- Tao bang tu dong khi khoi dong (create_all), giai doan nuoc rut chua dung Alembic.
"""
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Request
from sqlalchemy import DateTime, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.types import TypeDecorator


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """Thoi diem co mui gio. Ghi: doi ve UTC (thoi diem khong co mui gio -> loi, tranh nham gio Viet Nam voi UTC).
    Doc: luon tra ve datetime co tzinfo=UTC."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError(f"Thoi diem phai co mui gio (nhan duoc {value!r})")
        value = value.astimezone(timezone.utc)
        return value.replace(tzinfo=None) if dialect.name == "sqlite" else value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def make_engine(url: str):
    if not url.startswith("sqlite"):
        return create_engine(url, pool_pre_ping=True)
    kw = {"connect_args": {"check_same_thread": False}}  # vong lap cong ghi CSDL tu thread rieng
    if url in ("sqlite://", "sqlite:///:memory:"):
        kw["poolclass"] = StaticPool  # CSDL trong bo nho (test): moi session dung chung 1 ket noi
    else:
        Path(url[len("sqlite:///"):]).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url, **kw)

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _record):  # SQLite mac dinh khong kiem tra khoa ngoai
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    return engine


class Database:
    def __init__(self, url: str):
        self.url = url
        self.engine = make_engine(url)
        self.Session = sessionmaker(self.engine, expire_on_commit=False)

    @property
    def kind(self) -> str:
        return self.engine.dialect.name  # "sqlite" | "postgresql"

    def create_all(self) -> None:
        from app import models  # noqa: F401  (dang ky cac bang voi Base.metadata)
        Base.metadata.create_all(self.engine)

    def session(self) -> Session:
        return self.Session()


def get_db(request: Request):
    """Dependency cua FastAPI: 1 session cho moi request, tu dong dong."""
    with request.app.state.db.session() as session:
        yield session
