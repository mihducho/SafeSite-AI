"""Vung nguy hiem: kiem tra 1 diem (vd vi tri chan cua nguoi) co nam trong
vung cam duoc dinh nghia boi da giac (polygon) hay khong. Moi camera co 1
polygon rieng, doc tu configs/zones.yaml (dung scripts/define_zone.py de tao
file nay bang cach click chuot thay vi go toa do tay).
"""
from pathlib import Path

import cv2
import numpy as np
import yaml


def load_zones(path: str | Path) -> dict[str, np.ndarray]:
    """Doc file yaml dang {camera_id: [[x1,y1],[x2,y2],...]} va tra ve
    dict camera_id -> polygon (np.ndarray int32, shape (N,2))."""
    path = Path(path)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return {cam: np.array(pts, dtype=np.int32) for cam, pts in raw.items()}


def point_in_zone(point: tuple[float, float], polygon: np.ndarray) -> bool:
    """point: (x, y). polygon: np.ndarray (N,2) int32, tu load_zones()."""
    return cv2.pointPolygonTest(polygon, (float(point[0]), float(point[1])), False) >= 0


def person_feet_point(xyxy_box) -> tuple[float, float]:
    """Diem 'chan' cua 1 box nguoi (x1,y1,x2,y2) — dung diem nay thay vi tam
    box de kiem tra vi tri thuc te tren mat dat, on dinh hon khi box bi cat
    o phia tren do che khuat."""
    x1, y1, x2, y2 = xyxy_box
    return ((x1 + x2) / 2, y2)
