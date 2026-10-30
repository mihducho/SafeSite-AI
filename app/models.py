"""Cac bang CSDL (DE_TAI.md muc 10), viet bang SQLAlchemy nen chay tren MySQL 8 / MariaDB, SQLite, PostgreSQL.
Moi chuoi (String) deu co do dai (MySQL bat buoc VARCHAR(n)); thoi diem dung UTCDateTime (gio UTC, app/db.py);
JSON -> kieu JSON (MariaDB: LONGTEXT co kiem tra JSON); LargeBinary -> BLOB.
Ten bang, ten cot theo dung muc 10; them cac cot:
  gates.rotate        goc xoay hinh camera (truoc day luu cung vung trong configs/gates.yaml)
  ppe_checks.detail   so lieu de xem lai/hieu chinh nguong: ket qua bao ho goc, so khung, ti le khung nhieu mat,
                      nguoi giong nhat va diem nguoi thu hai... KHONG chua vector khuon mat.
Vector khuon mat chi nam o face_samples.embedding (128 so float32 = 512 byte).

Cham cong v2 (docs/LOGIC_CHAM_CONG.md): attendance_segments (phien vao-ra), phep (phep / giai trinh),
nhat_ky_cham_cong (moi thao tac tay). attendance = bang TONG HOP 1 ngay, tinh lai tu cac phien.
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
    ngay_vao_lam: Mapped[date | None] = mapped_column(Date)    # rong = ngay tao (gio Viet Nam)
    ngay_nghi_viec: Mapped[date | None] = mapped_column(Date)  # dat khi cho nghi viec, xoa khi di lam lai

    team: Mapped[Team | None] = relationship()
    consent_user: Mapped[User | None] = relationship(foreign_keys=[consent_by])  # nguoi ghi nhan dong y
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
    action_reason: Mapped[str | None] = mapped_column(String(30))  # vd ngoai_gio_vao_som / ngoai_gio_vao_muon
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
    break_start: Mapped[time] = mapped_column(Time, default=time(11, 30))  # gio bat dau nghi trua
    break_minutes: Mapped[int] = mapped_column(Integer, default=60)
    grace_minutes: Mapped[int] = mapped_column(Integer, default=5)
    early_checkin_minutes: Mapped[int] = mapped_column(Integer, default=60)
    phut_chong_trung: Mapped[int] = mapped_column(Integer, default=10)  # sua o trang Cau hinh ca
    # ngay nghi hang tuan, vd "chu_nhat" / "thu_bay,chu_nhat" / "" (khong nghi); rong (NULL) = attendance.ngay_nghi_tuan
    ngay_nghi_tuan: Mapped[str | None] = mapped_column(String(60))
    is_overnight: Mapped[bool] = mapped_column(Boolean, default=False)  # chua dung
    is_overtime: Mapped[bool] = mapped_column(Boolean, default=False)   # chua dung


class Attendance(Base):
    """Bang cong: 1 dong / cong nhan / ngay / ca. Tong hop tu cac phien (attendance_segments), tinh lai moi khi phien
    hoac phep cua ngay do thay doi (services/cham_cong.py tinh_lai_ngay)."""
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("worker_id", "work_date", "shift_id", name="uq_attendance_worker_ngay_ca"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    worker_id: Mapped[int] = mapped_column(ForeignKey("workers.id", ondelete="CASCADE"), index=True)
    work_date: Mapped[date] = mapped_column(Date, index=True)  # ngay theo gio Viet Nam
    shift_id: Mapped[int] = mapped_column(ForeignKey("shifts.id"))
    check_in: Mapped[datetime | None] = mapped_column(UTCDateTime)   # gio vao cua phien dau tien
    check_out: Mapped[datetime | None] = mapped_column(UTCDateTime)  # gio ra cua phien cuoi (neu phien cuoi da dong)
    ppe_check_id: Mapped[int | None] = mapped_column(ForeignKey("ppe_checks.id", ondelete="SET NULL"))  # luot vao dau
    late_minutes: Mapped[int] = mapped_column(Integer, default=0)
    early_leave_minutes: Mapped[int] = mapped_column(Integer, default=0)
    worked_minutes: Mapped[int] = mapped_column(Integer, default=0)
    so_lan_ra_ngoai: Mapped[int] = mapped_column(Integer, default=0)
    phut_ra_ngoai: Mapped[int] = mapped_column(Integer, default=0)
    phut_cong_tac: Mapped[int] = mapped_column(Integer, default=0)  # ra ngoai co phep cong tac (tinh cong)
    da_xac_nhan_khong_phep: Mapped[bool] = mapped_column(Boolean, default=False)  # "Xac nhan khong phep" (Viec can xu ly)
    # gio ca da ap dung cho ngay nay (chep luc tao dong): sua ca sau do khong lam doi so lieu ngay cu
    ca_bat_dau: Mapped[time | None] = mapped_column(Time)
    ca_ket_thuc: Mapped[time | None] = mapped_column(Time)
    ca_nghi_tu: Mapped[time | None] = mapped_column(Time)
    ca_nghi_phut: Mapped[int | None] = mapped_column(Integer)
    ca_an_han: Mapped[int | None] = mapped_column(Integer)
    ca_vao_som: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="binh_thuong")  # binh_thuong / cham_thu_cong (ngoai_ca: cu)
    note: Mapped[str | None] = mapped_column(Text)  # cham thu cong: ly do (lich su day du o nhat_ky_cham_cong)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))  # lan sua tay gan nhat
    updated_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    worker: Mapped[Worker] = relationship()
    shift: Mapped[Shift] = relationship()
    segments: Mapped[list["AttendanceSegment"]] = relationship(back_populates="attendance", cascade="all, delete-orphan",
                                                              order_by="AttendanceSegment.vao_at")


class AttendanceSegment(Base):
    """1 phien lam viec: vao -> ra. trang_thai: mo (dang lam) / dong / thieu_gio_ra (luu boi tac vu nen) / huy."""
    __tablename__ = "attendance_segments"
    id: Mapped[int] = mapped_column(primary_key=True)
    attendance_id: Mapped[int] = mapped_column(ForeignKey("attendance.id", ondelete="CASCADE"), index=True)
    worker_id: Mapped[int] = mapped_column(ForeignKey("workers.id", ondelete="CASCADE"), index=True)
    vao_at: Mapped[datetime] = mapped_column(UTCDateTime)
    ra_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    vao_check_id: Mapped[int | None] = mapped_column(ForeignKey("ppe_checks.id", ondelete="SET NULL"))
    ra_check_id: Mapped[int | None] = mapped_column(ForeignKey("ppe_checks.id", ondelete="SET NULL"))
    nguon_vao: Mapped[str] = mapped_column(String(10), default="tu_dong")  # tu_dong / thu_cong
    nguon_ra: Mapped[str | None] = mapped_column(String(10))
    trang_thai: Mapped[str] = mapped_column(String(15), default="mo", index=True)
    ghi_chu: Mapped[str | None] = mapped_column(Text)

    attendance: Mapped[Attendance] = relationship(back_populates="segments")


class Phep(Base):
    """Phep / giai trinh cua 1 ngay cong (Q21): ve_som (tu_gio = gio duoc ve), di_muon (den_gio = gio du kien den),
    ra_ngoai_cong_viec [tu_gio, den_gio], nghi_ca_ngay. TTTN chi co admin: tao la duyet luon (da_duyet)."""
    __tablename__ = "phep"
    id: Mapped[int] = mapped_column(primary_key=True)
    worker_id: Mapped[int] = mapped_column(ForeignKey("workers.id", ondelete="CASCADE"), index=True)
    ngay: Mapped[date] = mapped_column(Date, index=True)
    loai: Mapped[str] = mapped_column(String(25))
    tu_gio: Mapped[time | None] = mapped_column(Time)
    den_gio: Mapped[time | None] = mapped_column(Time)
    tinh_cong: Mapped[bool] = mapped_column(Boolean, default=False)
    ly_do: Mapped[str] = mapped_column(Text)
    trang_thai: Mapped[str] = mapped_column(String(10), default="da_duyet")  # da_duyet / huy
    nguoi_tao: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    thoi_diem_tao: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    worker: Mapped[Worker] = relationship()


class NhatKyChamCong(Base):
    """Nhat ky moi thao tac tay tren bang cong: them_phien / sua_vao / sua_ra / huy_phien / dong_khi_nghi_viec /
    them_phep / huy_phep / xac_nhan_khong_phep. gia_tri_cu / gia_tri_moi: chu de doc (vd "07:00:00")."""
    __tablename__ = "nhat_ky_cham_cong"
    id: Mapped[int] = mapped_column(primary_key=True)
    worker_id: Mapped[int] = mapped_column(ForeignKey("workers.id", ondelete="CASCADE"), index=True)
    ngay: Mapped[date] = mapped_column(Date)
    attendance_id: Mapped[int | None] = mapped_column(ForeignKey("attendance.id", ondelete="SET NULL"), index=True)
    segment_id: Mapped[int | None] = mapped_column(ForeignKey("attendance_segments.id", ondelete="SET NULL"))
    phep_id: Mapped[int | None] = mapped_column(ForeignKey("phep.id", ondelete="SET NULL"))
    hanh_dong: Mapped[str] = mapped_column(String(25))
    gia_tri_cu: Mapped[str | None] = mapped_column(String(200))
    gia_tri_moi: Mapped[str | None] = mapped_column(String(200))
    ly_do: Mapped[str | None] = mapped_column(Text)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    thoi_diem: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    user: Mapped[User | None] = relationship()
