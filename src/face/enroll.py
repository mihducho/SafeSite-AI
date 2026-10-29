"""Dang ky mau khuon mat (DE_TAI.md muc 7, 12): kiem tra anh mau, lay vector, gom thanh danh sach mau.

Anh mau hop le: DUNG 1 khuon mat, score YuNet >= enroll_min_score, rong >= min_face_px. Moi nguoi giu toi da
max_samples mau chat luong cao nhat; it hon min_samples thi canh bao (van luu de chay thu).
Dung chung cho scripts/enroll_from_images.py, scripts/evaluate_faces.py; sang F2 dung cho trang dang ky khuon mat.
"""
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from src.face.analyze import face_quality

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp"}


@dataclass
class Sample:
    vector: np.ndarray      # (128,) da chuan hoa L2
    quality: float
    thumb: np.ndarray       # anh mat da can chinh 112x112
    source: str             # ten anh / "camera"


def check_enroll_face(rows, min_score: float, min_face_px: float) -> tuple[int | None, str]:
    """Kiem tra 1 anh mau. Tra ve (chi so mat, "") neu hop le, nguoc lai (None, ly do)."""
    r = np.asarray(rows, np.float32).reshape(-1, 15)
    if len(r) == 0:
        return None, "khong thay mat"
    if len(r) > 1:
        return None, f"co {len(r)} mat (can dung 1)"
    if r[0, 14] < min_score:
        return None, f"diem mat {r[0, 14]:.2f} < {min_score}"
    if r[0, 2] < min_face_px:
        return None, f"mat rong {r[0, 2]:.0f}px < {min_face_px}px"
    return 0, ""


def sample_from_image(image: np.ndarray, face_detector, embedder, face_cfg: dict, source: str) -> tuple[Sample | None, str]:
    faces = face_detector.detect(image)
    idx, why = check_enroll_face(faces.rows, face_cfg["enroll_min_score"], face_cfg["min_face_px"])
    if idx is None:
        return None, why
    row = faces.rows[idx]
    thumb = embedder.align(image, row)
    q = face_quality(row[14], row[2], face_cfg["quality_full_width_px"])
    return Sample(embedder.embed_aligned(thumb), q, thumb, source), ""


def enroll_folder(folder: str | Path, face_detector, embedder, face_cfg: dict) -> tuple[dict[str, list[Sample]], list[str]]:
    """Doc <folder>/<ma_nguoi>/*.jpg. Tra ve ({ma: [Sample]}, cac dong thong bao anh bi bo qua)."""
    samples: dict[str, list[Sample]] = {}
    notes = []
    for person_dir in sorted(p for p in Path(folder).iterdir() if p.is_dir()):
        for img_path in sorted(p for p in person_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS):
            image = cv2.imdecode(np.fromfile(str(img_path), np.uint8), cv2.IMREAD_COLOR)  # doc duoc ca ten co dau
            if image is None:
                notes.append(f"{person_dir.name}/{img_path.name}: khong doc duoc anh")
                continue
            s, why = sample_from_image(image, face_detector, embedder, face_cfg, img_path.name)
            if s is None:
                notes.append(f"{person_dir.name}/{img_path.name}: bo qua ({why})")
            else:
                samples.setdefault(person_dir.name, []).append(s)
    return samples, notes


def best_samples(samples: list[Sample], max_samples: int) -> list[Sample]:
    """Toi da max_samples mau chat luong cao nhat."""
    return sorted(samples, key=lambda s: s.quality, reverse=True)[:max_samples]


def to_gallery(samples: dict[str, list[Sample]], max_samples: int) -> dict[str, np.ndarray]:
    """{ma: (m, 128)} de so khop (match.py)."""
    return {code: np.stack([s.vector for s in best_samples(lst, max_samples)]) for code, lst in samples.items() if lst}


def similarity_report(gallery: dict[str, np.ndarray]) -> list[str]:
    """Do giong nhau giua cac mau: cung nguoi (nho nhat, trung binh) va khac nguoi (lon nhat) -> de chon nguong."""
    lines = []
    codes = sorted(gallery)
    for c in codes:
        g = gallery[c]
        if len(g) > 1:
            sims = (g @ g.T)[np.triu_indices(len(g), 1)]
            lines.append(f"{c}: cung nguoi {len(g)} mau, giong nhau nho nhat {sims.min():.2f}, trung binh {sims.mean():.2f}")
        else:
            lines.append(f"{c}: chi co 1 mau")
    for i, a in enumerate(codes):
        for b in codes[i + 1:]:
            lines.append(f"{a} - {b}: khac nguoi, giong nhau lon nhat {(gallery[a] @ gallery[b].T).max():.2f}")
    return lines
