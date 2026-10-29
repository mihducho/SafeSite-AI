"""Du lieu gia dung chung cho test ung dung web (khong phai file test): CSDL SQLite trong bo nho, cong nhan co mau
khuon mat gia (vector don vi), LuotKiemTra gia, bo tim mat / lay vector gia cho dang ky khuon mat. Khong can camera,
khong can mo hinh.

Mac dinh CSDL SQLite trong bo nho. Chay toan bo test tren MySQL / MariaDB / PostgreSQL: dat bien moi truong
TEST_DATABASE_URL tro toi 1 CSDL RIENG cho test (moi test XOA SACH cac bang), ten CSDL phai co chu "test", vd
  TEST_DATABASE_URL=mysql+pymysql://safegate:mat_khau@127.0.0.1:3307/safegate_test?charset=utf8mb4
"""
import copy
import os
import sys
import tempfile
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy.engine import make_url

from app.auth import hash_password
from app.config import AppConfig, normalize_database_url
from app.db import Base, Database, utcnow
from app.models import FaceSample, Shift, User, Worker
from app.services.luot import LuotKiemTra
from app.services.nhan_dien import NhanDien, vector_to_embedding
from fakes import SETTINGS as BASE_SETTINGS
from src.checkpoint.evaluate import DAT
from src.face.face_detector import Faces
from src.face.match import l2_normalize
from test_face import face

TZ = ZoneInfo("Asia/Ho_Chi_Minh")
PASSWORD = "mat-khau-test"
FAST_HASH = hash_password(PASSWORD, iterations=1000)  # test khong can 600 000 vong

# Co dinh cac tham so test dua vao (gia tri DE_TAI muc 7, 15), de doi settings.yaml khong lam hong test.
SETTINGS = copy.deepcopy(BASE_SETTINGS)
SETTINGS["face"].update(min_samples=3, max_samples=10, match_threshold=0.40, match_margin=0.05, enroll_min_score=0.85,
                        min_face_px=50, enroll_long_side=1280)
SETTINGS["attendance"].update(duplicate_minutes=2, missing_checkout_hours=4, timezone="Asia/Ho_Chi_Minh")
SETTINGS["web"].update(page_size=20, max_page_size=200, max_upload_mb=10)


def vn(day: int, hour: int, minute: int = 0, second: int = 0, month: int = 10, year: int = 2026) -> datetime:
    """Thoi diem theo gio Viet Nam (co mui gio)."""
    return datetime(year, month, day, hour, minute, second, tzinfo=TZ)


def unit(i: int) -> np.ndarray:
    v = np.zeros(128, np.float32)
    v[i] = 1.0
    return v


def near(i: int, noise: float = 0.05, seed: int = 0) -> np.ndarray:
    """Vector gan unit(i) (cosine ~0.99): mau khuon mat gia cua cong nhan thu i."""
    rng = np.random.default_rng(seed)
    return l2_normalize(unit(i) + noise * rng.standard_normal(128).astype(np.float32))


TEST_DB = normalize_database_url(os.environ.get("TEST_DATABASE_URL", "sqlite://"))
if not TEST_DB.startswith("sqlite") and "test" not in (make_url(TEST_DB).database or ""):
    # chot an toan: test xoa sach cac bang, khong duoc chay nham len CSDL that (du lieu cong nhan, cham cong)
    raise RuntimeError(f"TEST_DATABASE_URL phai tro toi CSDL rieng cho test (ten co chu 'test'), "
                       f"khong phai '{make_url(TEST_DB).database}'")


def reset_db(url: str = TEST_DB) -> None:
    """PostgreSQL: xoa het bang de moi test bat dau tu CSDL trong (SQLite trong bo nho thi luon moi)."""
    if not url.startswith("sqlite"):
        db = Database(url)
        db.create_all()
        Base.metadata.drop_all(db.engine)
        db.engine.dispose()


def make_db() -> Database:
    reset_db()
    db = Database(TEST_DB)
    db.create_all()
    return db


def add_admin(s, username: str = "admin") -> User:
    user = User(username=username, password_hash=FAST_HASH, full_name="Quản trị", role="admin", is_active=True)
    s.add(user)
    s.commit()
    return user


def add_shift(s) -> Shift:
    shift = Shift(name="Ca hành chính", start_time=time(7, 0), end_time=time(17, 0), break_start=time(11, 30),
                  break_minutes=60, grace_minutes=5, early_checkin_minutes=60)
    s.add(shift)
    s.commit()
    return shift


def add_worker(s, code: str, name: str, face_index: int | None = None, n_samples: int = 3, consent: bool = True,
               team_id: int | None = None) -> Worker:
    """Cong nhan co n_samples mau gia quanh unit(face_index) (ghi thang vao CSDL, bo qua buoc anh)."""
    w = Worker(code=code, full_name=name, team_id=team_id, consent_at=utcnow() if consent else None)
    s.add(w)
    s.flush()
    if face_index is not None:
        for k in range(n_samples):
            s.add(FaceSample(worker_id=w.id, embedding=vector_to_embedding(near(face_index, seed=k)), quality=0.9,
                             thumb_path=f"{w.id}/gia_{k}.jpg", source="upload"))
    s.commit()
    return w


def luot(t: datetime, ket_qua: str = DAT, thieu=(), face_index: int | None = None, ly_do=None) -> LuotKiemTra:
    """Luot gia: face_index=None -> khong thay mat; co -> 3 vector gan unit(face_index)."""
    vecs = (np.stack([near(face_index, seed=10 + k) for k in range(3)]) if face_index is not None
            else np.zeros((0, 128), np.float32))
    return LuotKiemTra(thoi_diem=t, ket_qua=ket_qua, thieu=list(thieu), vectors=vecs, anh_jpeg=b"\xff\xd8gia\xff\xd9",
                       ly_do=ly_do, thoi_gian_ms=1500.0, chi_tiet={"so_khung": 10})


# --- dang ky khuon mat: anh gia ---
# Anh mau gia: pixel (0,0) kenh 0 = chi so vector (unit(i)), kenh 1 = so mat bo tim mat gia tra ve (0, 1, 2).
def sample_image(face_index: int, n_faces: int = 1, size=(240, 320)) -> np.ndarray:
    img = np.full((*size, 3), 128, np.uint8)
    img[0, 0, 0], img[0, 0, 1] = face_index, n_faces
    return img


def sample_jpeg_bytes(face_index: int, n_faces: int = 1) -> bytes:
    # PNG (khong nen mat) de giu dung gia tri pixel danh dau sau khi giai ma
    return cv2.imencode(".png", sample_image(face_index, n_faces))[1].tobytes()


class FakeEnrollDetector:
    def detect(self, image, long_side=None):
        n = int(image[0, 0, 1])
        rows = [face(60 + 120 * k, 60, 80, score=0.95) for k in range(n)]
        return Faces(np.asarray(rows, np.float32).reshape(-1, 15))


class FakeEnrollEmbedder:
    def align(self, image, row):
        out = np.zeros((112, 112, 3), np.uint8)
        out[0, 0, 0] = image[0, 0, 0]
        return out

    def embed_aligned(self, aligned):
        return near(int(aligned[0, 0, 0]), seed=99)


def fake_face_models():
    return FakeEnrollDetector(), FakeEnrollEmbedder()


def app_config(database_url: str = TEST_DB, tmp: str | None = None) -> AppConfig:
    """Cau hinh ung dung cho test: CSDL test (trong), anh luot + anh mau ghi vao thu muc tam; giao dien React chua build
    (thu muc frontend_dist trong thu muc tam, chua co; test giao dien React tu tao)."""
    reset_db(database_url)
    s = copy.deepcopy(SETTINGS)
    tmp = Path(tmp or tempfile.mkdtemp())
    s["paths"]["check_images"] = tmp / "anh_luot"
    s["paths"]["face_samples"] = tmp / "anh_mau_mat"
    s["paths"]["frontend_dist"] = tmp / "frontend_dist"
    return AppConfig(settings=s, database_url=database_url, secret_key="khoa-test", admin_password=PASSWORD,
                     gate_enabled=False)


def nhan_dien() -> NhanDien:
    return NhanDien(SETTINGS["face"])
