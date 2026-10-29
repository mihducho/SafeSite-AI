"""So khop khuon mat voi danh sach mau (DE_TAI.md muc 6.2, phan "So khop").

Ham thuan: nhan vector cua luot kiem tra va mau cua cac cong nhan (truyen vao), khong doc CSDL hay file.
Ban demo dong lenh doc mau tu file .npz (load_gallery); sang F2, app/services/nhan_dien.py doc mau tu CSDL roi goi
match() o day. Vi vay dich vu AI van khong "biet" cong nhan la ai.

Diem cua 1 cong nhan = trung binh, qua cac vector cua luot, cua cosine lon nhat voi cac mau cua cong nhan do.
Nhan ra khi diem cao nhat >= nguong VA hon nguoi thu hai it nhat `margin`.
"""
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


def l2_normalize(v: np.ndarray) -> np.ndarray:
    """Chia moi vector cho do dai cua no (vector 0 giu nguyen)."""
    v = np.asarray(v, np.float32)
    norm = np.linalg.norm(v, axis=-1, keepdims=True)
    return np.divide(v, norm, out=np.zeros_like(v), where=norm > 0)


@dataclass
class MatchResult:
    ma: str | None                 # ma cong nhan nhan ra; None = khong nhan ra
    diem: float | None = None      # diem cua nguoi giong nhat
    ma_gan_nhat: str | None = None  # nguoi giong nhat (ke ca khi duoi nguong), de xem lai
    diem_thu_hai: float | None = None
    diem_theo_nguoi: dict = field(default_factory=dict)


def score_workers(vectors: np.ndarray, gallery: dict[str, np.ndarray]) -> dict[str, float]:
    """{ma: diem}. vectors (k, 128) va mau (m, 128) deu da chuan hoa L2."""
    vecs = l2_normalize(np.asarray(vectors, np.float32).reshape(-1, 128))
    out = {}
    for code, samples in gallery.items():
        samples = l2_normalize(np.asarray(samples, np.float32).reshape(-1, 128))
        if len(samples) == 0 or len(vecs) == 0:
            continue
        sims = vecs @ samples.T  # (k, m) cosine
        out[code] = float(sims.max(axis=1).mean())
    return out


def match(vectors: np.ndarray, gallery: dict[str, np.ndarray], threshold: float, margin: float) -> MatchResult:
    scores = score_workers(vectors, gallery) if len(np.asarray(vectors).reshape(-1)) else {}
    if not scores:
        return MatchResult(None, diem_theo_nguoi=scores)
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    best_code, best = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else None  # chi 1 cong nhan co mau: khong xet khoang cach
    ok = best >= threshold and (second is None or best - second >= margin)
    return MatchResult(best_code if ok else None, best, best_code, second, scores)


def save_gallery(path: str | Path, gallery: dict[str, np.ndarray]) -> None:
    """Luu {ma_nguoi: (m, 128)} ra file .npz (chi dung khi chua co CSDL; file khong dua vao git)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(path, **{code: np.asarray(v, np.float32) for code, v in gallery.items()})


def load_gallery(path: str | Path) -> dict[str, np.ndarray]:
    path = Path(path)
    if not path.exists():
        return {}
    with np.load(path) as data:
        return {code: data[code] for code in data.files}
