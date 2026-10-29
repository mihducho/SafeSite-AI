"""Cac ham thuan xu ly khuon mat (DE_TAI.md muc 6.2). Nhan du lieu (dong YuNet, khung nguoi, vung kiem tra),
khong doc camera, khong chay mo hinh -> test duoc bang du lieu gia, giong cach lam cua evaluate_frames.

Moi khung trong 1 luot kiem tra:
  - mat cua NGUOI DANG KIEM TRA (main_face_index): tam mat nam trong VUNG DAU cua nguoi lon nhat co diem chan trong
    vung kiem tra (dung lai tham so vung dau cua compliance), rong >= min_face_px. Mat khong gan duoc voi ai trong vung
    thi khong dung de nhan dang (chan truong hop gio anh/dien thoai co anh nguoi khac len).
  - DEM MAT trong vung (count_faces_in_zone) de phat hien nhieu nguoi, ke ca nguoi dung sau bi che than nhung van
    thay mat: tam mat nam trong khoang x cua vung, rong >= multi_min_px va >= multi_min_ratio x mat lon nhat
    (nguoi xep hang o xa phia sau co mat nho hon han -> khong bi tinh).
Ca luot (FaceAccumulator): giu toi da max_vectors vector chat luong cao nhat, ti le khung co >= 2 mat.
"""
import numpy as np

from src.ppe.compliance import _region_boxes

CO_MAT = "CO_MAT"
KHONG_THAY_MAT = "KHONG_THAY_MAT"


def _rows(rows) -> np.ndarray:
    return np.asarray(rows, np.float32).reshape(-1, 15)


def face_centers(rows) -> np.ndarray:
    """(N, 2) tam khung mat."""
    r = _rows(rows)
    return np.stack([r[:, 0] + r[:, 2] / 2, r[:, 1] + r[:, 3] / 2], axis=1)


def zone_x_range(zone_px: np.ndarray | None, frame_width: int) -> tuple[float, float]:
    """Khoang x cua vung kiem tra (nho nhat, lon nhat). Khong co vung (chay thu) = ca chieu ngang khung."""
    if zone_px is None or len(zone_px) == 0:
        return 0.0, float(frame_width)
    xs = np.asarray(zone_px, np.float32)[:, 0]
    return float(xs.min()), float(xs.max())


def largest_person(persons: np.ndarray) -> np.ndarray | None:
    """Nguoi co khung lon nhat (dien tich) trong cac nguoi o trong vung; None neu khong co ai."""
    p = np.asarray(persons, np.float32).reshape(-1, 4)
    if len(p) == 0:
        return None
    return p[np.argmax((p[:, 2] - p[:, 0]) * (p[:, 3] - p[:, 1]))]


def head_box(person_xyxy, ppe_cfg: dict) -> np.ndarray:
    """Vung dau cua 1 nguoi, dung DUNG tham so cua kiem tra bao ho (ppe.items.hardhat.region; nguoi cui -> ca khung)."""
    person = np.asarray(person_xyxy, np.float32).reshape(1, 4)
    h, w = person[0, 3] - person[0, 1], person[0, 2] - person[0, 0]
    region = ppe_cfg["whole_box_region"] if h < ppe_cfg["upright_min_ratio"] * w else ppe_cfg["items"]["hardhat"]["region"]
    return _region_boxes(person, tuple(region))[0]


def main_face_index(rows, zone_persons, ppe_cfg: dict, min_face_px: float) -> int | None:
    """Chi so mat cua nguoi dang kiem tra, hoac None. Nhieu mat hop le trong vung dau -> lay mat rong nhat."""
    r = _rows(rows)
    person = largest_person(zone_persons)
    if person is None or len(r) == 0:
        return None
    x1, y1, x2, y2 = head_box(person, ppe_cfg)
    c = face_centers(r)
    ok = (c[:, 0] >= x1) & (c[:, 0] <= x2) & (c[:, 1] >= y1) & (c[:, 1] <= y2) & (r[:, 2] >= min_face_px)
    if not ok.any():
        return None
    idx = np.flatnonzero(ok)
    return int(idx[np.argmax(r[idx, 2])])


def count_faces_in_zone(rows, zone_px: np.ndarray | None, frame_width: int, multi_min_px: float,
                        multi_min_ratio: float) -> int:
    """So mat tinh cho luat nhieu nguoi (xem dau file)."""
    r = _rows(rows)
    if len(r) == 0:
        return 0
    xmin, xmax = zone_x_range(zone_px, frame_width)
    cx = face_centers(r)[:, 0]
    in_x = (cx >= xmin) & (cx <= xmax)
    if not in_x.any():
        return 0
    widths = r[in_x, 2]
    return int(((widths >= multi_min_px) & (widths >= multi_min_ratio * widths.max())).sum())


def idle_face_present(rows, zone_px: np.ndarray | None, frame_width: int, min_face_px: float) -> bool:
    """Che do CHO (chua chay YOLO): co mat du lon (>= min_face_px) co tam trong khoang x cua vung khong."""
    r = _rows(rows)
    if len(r) == 0:
        return False
    xmin, xmax = zone_x_range(zone_px, frame_width)
    cx = face_centers(r)[:, 0]
    return bool(((cx >= xmin) & (cx <= xmax) & (r[:, 2] >= min_face_px)).any())


def face_quality(score: float, width: float, full_width_px: float) -> float:
    """Diem chat luong = score YuNet x min(1, rong / full_width_px)."""
    return float(score) * min(1.0, float(width) / float(full_width_px))


def select_vectors(candidates: list[tuple[float, np.ndarray]], max_vectors: int) -> list[tuple[float, np.ndarray]]:
    """Giu toi da max_vectors cap (chat luong, vector) co chat luong cao nhat, cao truoc."""
    return sorted(candidates, key=lambda qv: qv[0], reverse=True)[:max_vectors]


class FaceAccumulator:
    """Gom ket qua khuon mat cua cac khung trong 1 luot."""

    def __init__(self, max_vectors: int):
        self.max_vectors = max_vectors
        self.frames = 0
        self.frames_with_face = 0   # khung co mat cua nguoi dang kiem tra
        self.frames_multi = 0       # khung dem duoc >= 2 mat trong vung
        self.candidates: list[tuple[float, np.ndarray]] = []

    def add(self, faces_in_zone: int, vector: np.ndarray | None, quality: float) -> None:
        self.frames += 1
        self.frames_multi += faces_in_zone >= 2
        if vector is not None:
            self.frames_with_face += 1
            self.candidates.append((quality, vector))

    def summary(self) -> dict:
        best = select_vectors(self.candidates, self.max_vectors)
        return {
            "vectors": [v for _, v in best],
            "chat_luong": [round(q, 3) for q, _ in best],
            "so_khung": self.frames,
            "so_khung_co_mat": self.frames_with_face,
            "so_khung_nhieu_mat": self.frames_multi,
            "ty_le_khung_nhieu_mat": round(self.frames_multi / self.frames, 3) if self.frames else 0.0,
            "trang_thai": CO_MAT if best else KHONG_THAY_MAT,
        }
