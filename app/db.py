"""Ket noi CSDL bang SQLAlchemy 2 (DE_TAI.md muc 4, 10). Ban demo dung MySQL 8 / MariaDB; code chay duoc ca SQLite
(test) va PostgreSQL, chi doi DATABASE_URL.

- Thoi diem luu theo gio UTC (UTCDateTime, dung chung cho moi cot thoi diem). MySQL/MariaDB (DATETIME) va SQLite
  khong luu mui gio: ghi gio UTC "tron" (khong kem mui gio), khi doc ra gan lai mui gio UTC. MySQL dung DATETIME(6)
  de giu phan micro giay (DATETIME mac dinh lam tron toi giay). PostgreSQL dung kieu timestamptz.
  Ngay cong va gio hien thi tinh theo Asia/Ho_Chi_Minh o tang nghiep vu (services/cham_cong.py).
- Tao bang tu dong khi khoi dong (create_all), giai doan nuoc rut chua dung Alembic.
"""
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Request
from sqlalchemy import DateTime, create_engine, event
from sqlalchemy.dialects import mysql
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

    def load_dialect_impl(self, dialect):
        if dialect.name in ("mysql", "mariadb"):
            return dialect.type_descriptor(mysql.DATETIME(fsp=6))
        return dialect.type_descriptor(DateTime(timezone=True))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError(f"Thoi diem phai co mui gio (nhan duoc {value!r})")
        value = value.astimezone(timezone.utc)
        return value if dialect.name == "postgresql" else value.replace(tzinfo=None)  # chi PostgreSQL luu mui gio

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def make_engine(url: str):
    if url.startswith(("mysql", "mariadb")):
        # pool_recycle: MySQL tu dong ket noi ranh qua wait_timeout (mac dinh 8 gio) -> mo lai truoc khi bi dong
        return create_engine(url, pool_pre_ping=True, pool_recycle=3600)
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
        """sqlite / postgresql / mysql / mariadb (mysql+pymysql noi toi MariaDB van bao "mysql" -> xem is_mariadb)."""
        d = self.engine.dialect
        if d.name == "mysql" and not getattr(self, "_connected", False):
            with self.engine.connect():  # SQLAlchemy chi biet la MariaDB sau lan ket noi dau tien
                self._connected = True
        return "mariadb" if getattr(d, "is_mariadb", False) else d.name

    def create_all(self) -> None:
        from app import models  # noqa: F401  (dang ky cac bang voi Base.metadata)
        Base.metadata.create_all(self.engine)

    def cot_con_thieu(self) -> list[str]:
        """Cot co trong models nhung chua co trong CSDL (CSDL tao tu phien ban cu; create_all khong them cot)."""
        from sqlalchemy import inspect

        insp = inspect(self.engine)
        missing = []
        for table in Base.metadata.sorted_tables:
            if insp.has_table(table.name):
                have = {c["name"] for c in insp.get_columns(table.name)}
                missing += [f"{table.name}.{c.name}" for c in table.columns if c.name not in have]
        return missing

    def session(self) -> Session:
        return self.Session()


def get_db(request: Request):
    """Dependency cua FastAPI: 1 session cho moi request, tu dong dong."""
    with request.app.state.db.session() as session:
        yield session
