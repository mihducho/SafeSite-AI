"""Cac bang CSDL (DE_TAI.md muc 10). Ten bang, ten cot theo dung muc 10; them 2 cot:
  gates.rotate        goc xoay hinh camera (truoc day luu cung vung trong configs/gates.yaml)
  ppe_checks.detail   so lieu de xem lai/hieu chinh nguong: ket qua bao ho goc, so khung, ti le khung nhieu mat,
                      nguoi giong nhat va diem nguoi thu hai... KHONG chua vector khuon mat.
Vector khuon mat chi nam o face_samples.embedding (128 so float32 = 512 byte).
"""
from datetime import date, datetime, time

from sqlalchemy import JSON, Boolean, Date, Float, ForeignKey, Integer, LargeBinary, String, Text, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, UTCDateTime, utcnow

# workers.status
DANG_LAM = "dang_lam"
NGHI_VIEC = "nghi_viec"


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    full_name: Mapped[str] = mapped_column(String(100), default="")
    role: Mapped[str] = mapped_column(String(20), default="admin")  # giai doan nuoc rut chi co admin
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Team(Base):
    __tablename__ = "teams"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    contractor: Mapped[str | None] = mapped_column(String(100))   # nha thau phu
    leader_name: Mapped[str | None] = mapped_column(String(100))  # to truong


class Worker(Base):
    __tablename__ = "workers"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)  # vd CN001
    full_name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(20))
    trade: Mapped[str | None] = mapped_column(String(50))  # nghe
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"))
    status: Mapped[str] = mapped_column(String(20), default=DANG_LAM)
    consent_at: Mapped[datetime | None] = mapped_column(UTCDateTime)  # luc ghi nhan dong y dang ky khuon mat
    consent_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    team: Mapped[Team | None] = relationship()
    samples: Mapped[list["FaceSample"]] = relationship(back_populates="worker", cascade="all, delete-orphan")


class FaceSample(Base):
    __tablename__ = "face_samples"
    id: Mapped[int] = mapped_column(primary_key=True)
    worker_id: Mapped[int] = mapped_column(ForeignKey("workers.id", ondelete="CASCADE"), index=True)
    embedding: Mapped[bytes] = mapped_column(LargeBinary)  # 128 x float32 (little-endian) = 512 byte
    quality: Mapped[float] = mapped_column(Float)
    thumb_path: Mapped[str] = mapped_column(String(255))  # anh mat 112x112, tinh tu paths.face_samples
    source: Mapped[str] = mapped_column(String(10))  # camera / upload
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    worker: Mapped[Worker] = relationship(back_populates="samples")


class Gate(Base):
    __tablename__ = "gates"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    camera_source: Mapped[str] = mapped_column(String(500))  # so webcam / URL / file video. URL co mat khau: dat o .env
    zone: Mapped[list] = mapped_column(JSON)  # da giac ti le 0-1
    required_ppe: Mapped[list | None] = mapped_column(JSON)  # None = ppe.required trong settings.yaml
    rotate: Mapped[int] = mapped_column(Integer, default=0)


class PpeCheck(Base):
    """1 luot kiem tra tai cong."""
    __tablename__ = "ppe_checks"
    id: Mapped[int] = mapped_column(primary_key=True)
    gate_id: Mapped[int | None] = mapped_column(ForeignKey("gates.id"))
    worker_id: Mapped[int | None] = mapped_column(ForeignKey("workers.id", ondelete="SET NULL"), index=True)
    checked_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    face_status: Mapped[str] = mapped_column(String(20))  # DA_NHAN_RA / KHONG_NHAN_RA / KHONG_THAY_MAT
    face_score: Mapped[float | None] = mapped_column(Float)  # diem cua nguoi giong nhat (ke ca khi khong nhan ra)
    result: Mapped[str] = mapped_column(String(20))  # DAT / KHONG_DAT / KHONG_XAC_DINH / NHIEU_NGUOI / KHONG_CO_NGUOI
    missing: Mapped[list] = mapped_column(JSON, default=list)
    presence_ratio: Mapped[dict] = mapped_column(JSON, default=dict)
    reason: Mapped[str | None] = mapped_column(String(30))
    duration_ms: Mapped[float | None] = mapped_column(Float)
    direction: Mapped[str | None] = mapped_column(String(5))  # vao / ra / None
    action: Mapped[str] = mapped_column(String(20))  # ghi_vao / ghi_ra / khong_ghi / bo_qua_trung
    image_path: Mapped[str | None] = mapped_column(String(255))  # tinh tu paths.check_images
    review_status: Mapped[str | None] = mapped_column(String(20))  # F3/F4: dung / bao_nham
    detail: Mapped[dict] = mapped_column(JSON, default=dict)

    worker: Mapped[Worker | None] = relationship()


class Shift(Base):
    __tablename__ = "shifts"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    start_time: Mapped[time] = mapped_column(Time)  # gio Viet Nam
    end_time: Mapped[time] = mapped_column(Time)
    break_minutes: Mapped[int] = mapped_column(Integer, default=60)
    grace_minutes: Mapped[int] = mapped_column(Integer, default=5)
    early_checkin_minutes: Mapped[int] = mapped_column(Integer, default=60)
    is_overnight: Mapped[bool] = mapped_column(Boolean, default=False)
    is_overtime: Mapped[bool] = mapped_column(Boolean, default=False)


class Attendance(Base):
    """Bang cong: 1 dong / cong nhan / ngay / ca."""
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("worker_id", "work_date", "shift_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    worker_id: Mapped[int] = mapped_column(ForeignKey("workers.id", ondelete="CASCADE"), index=True)
    work_date: Mapped[date] = mapped_column(Date, index=True)  # ngay theo gio Viet Nam
    shift_id: Mapped[int] = mapped_column(ForeignKey("shifts.id"))
    check_in: Mapped[datetime | None] = mapped_column(UTCDateTime)
    check_out: Mapped[datetime | None] = mapped_column(UTCDateTime)
    ppe_check_id: Mapped[int | None] = mapped_column(ForeignKey("ppe_checks.id", ondelete="SET NULL"))  # luot vao
    late_minutes: Mapped[int] = mapped_column(Integer, default=0)
    early_leave_minutes: Mapped[int] = mapped_column(Integer, default=0)
    worked_minutes: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="binh_thuong")  # binh_thuong / ngoai_ca / cham_thu_cong
    note: Mapped[str | None] = mapped_column(Text)  # cham thu cong: ly do
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    worker: Mapped[Worker] = relationship()
    shift: Mapped[Shift] = relationship()
