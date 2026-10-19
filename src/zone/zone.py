"""Vung kiem tra tai cong: da giac luu dang TI LE 0-1 so voi khung hinh (DE_TAI
muc 4), quy doi sang pixel luc chay; kiem tra diem chan nguoi co nam trong vung.

Cho toi khi co bang `gates` trong co so du lieu, vung luu tam o configs/gates.yaml
(ve bang scripts/define_zone.py), moi cong 1 muc, cung cau truc voi cot "vung
kiem tra" cua bang gates de sau nay chuyen sang de dang:
    cong_1:
      zone: [[0.25, 0.5], [0.75, 0.5], [0.75, 1.0], [0.25, 1.0]]
      rotate: 0      # goc xoay hinh camera cua cong; vung ve tren hinh DA XOAY theo goc nay
"""
from pathlib import Path

import cv2
import numpy as np
import yaml

from src.checkpoint.camera import check_rotate

# yaml.safe_dump xoa het comment trong file, nen ghi lai phan huong dan moi lan luu.
GATES_HEADER = """\
# Vung kiem tra cua tung cong (luu tam, cho toi khi co bang `gates` trong co so du lieu).
# zone: danh sach diem [x, y] dang TI LE 0-1 so voi chieu rong/chieu cao khung hinh,
# noi lai thanh da giac khep kin. rotate: goc xoay hinh camera cua cong (0/90/180/270,
# chieu kim dong ho); vung ve tren hinh da xoay. Ghi tu dong boi scripts/define_zone.py:
#   .venv\\Scripts\\python.exe scripts\\define_zone.py --source <video | so webcam | URL> --gate cong_1 [--rotate 90]
"""


def clicks_to_ratio(points, width: int, height: int) -> list[list[float]]:
    """Diem click (pixel tren anh dang hien thi, rong x cao) -> ti le 0-1, lam tron 4 chu so."""
    pts = np.clip(np.asarray(points, dtype=np.float64).reshape(-1, 2) / [width, height], 0.0, 1.0)
    return [[round(float(x), 4), round(float(y), 4)] for x, y in pts]


def load_gates(path: str | Path) -> dict:
    """Doc file vung {ten_cong: {zone: [[x, y], ...]}}; file chua co thi tra ve {}."""
    path = Path(path)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_gate(path: str | Path, gate: str) -> dict:
    """{"zone": vung ti le 0-1, "rotate": goc xoay hinh} cua 1 cong. Muc ve truoc khi co
    tinh nang xoay (chua co rotate) -> 0. Khong co cong do thi bao loi kem danh sach cong co san."""
    gates = load_gates(path)
    entry = gates.get(gate) or {}
    if "zone" not in entry:
        raise KeyError(f"Khong co vung cho cong '{gate}' trong {path}. Cac cong co san: {list(gates)}")
    zone_to_pixels(entry["zone"], 1, 1)  # kiem tra hop le (>= 3 diem, trong khoang 0-1)
    return {"zone": entry["zone"], "rotate": check_rotate(entry.get("rotate", 0))}


def load_gate_zone(path: str | Path, gate: str) -> list[list[float]]:
    """Vung ti le 0-1 cua 1 cong (xem load_gate)."""
    return load_gate(path, gate)["zone"]


def save_gate_zone(path: str | Path, gate: str, zone, rotate: int = 0) -> None:
    """Ghi (hoac ghi de) vung ti le 0-1 va goc xoay hinh cua 1 cong, giu nguyen cac cong khac."""
    zone_to_pixels(zone, 1, 1)  # tu choi luu toa do pixel hoac vung < 3 diem
    rotate = check_rotate(rotate)
    path = Path(path)
    data = load_gates(path)
    data[gate] = {**(data.get(gate) or {}), "zone": [[float(x), float(y)] for x, y in zone], "rotate": rotate}
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(GATES_HEADER)
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=None)


def choose_rotate(cli_rotate: int | None, gate: dict | None, default: int) -> int:
    """Goc xoay hinh khi chay kiem tra.
    Co cong (gate tu load_gate): dung goc da luu cung vung, vi vung ve tren hinh da xoay theo
    goc do; cli_rotate khac goc nay thi bao ValueError (vung se lech). Khong co cong:
    cli_rotate neu co, khong thi default (camera.rotate)."""
    if gate is not None:
        if cli_rotate is not None and check_rotate(cli_rotate) != gate["rotate"]:
            raise ValueError(f"vung da ve tren hinh xoay {gate['rotate']} do, khong dung duoc voi --rotate {cli_rotate}. "
                             f"Bo --rotate, hoac ve lai vung voi --rotate {cli_rotate}.")
        return gate["rotate"]
    return check_rotate(default if cli_rotate is None else cli_rotate)


def load_zones(path: str | Path) -> dict[str, np.ndarray]:
    """[Huong cu] Doc file yaml dang {camera_id: [[x1,y1],[x2,y2],...]} toa do PIXEL
    va tra ve dict camera_id -> polygon (np.ndarray int32, shape (N,2))."""
    path = Path(path)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return {cam: np.array(pts, dtype=np.int32) for cam, pts in raw.items()}


def zone_to_pixels(points, width: int, height: int) -> np.ndarray:
    """Vung kiem tra dang ti le 0-1 [[x, y], ...] (nhu backend gui, DE_TAI muc 4)
    -> da giac pixel int32 shape (N,2) theo kich thuoc khung hinh dang xu ly.

    Bao loi neu toa do ngoai [0, 1] — thuong do truyen nham toa do pixel.
    """
    pts = np.asarray(points, dtype=np.float64).reshape(-1, 2)
    if len(pts) < 3:
        raise ValueError(f"Vung kiem tra can toi thieu 3 diem, nhan duoc {len(pts)}")
    if pts.min() < 0 or pts.max() > 1:
        raise ValueError("Toa do vung kiem tra phai la ti le 0-1 so voi khung hinh, khong phai pixel")
    return np.round(pts * [width, height]).astype(np.int32)


def point_in_zone(point: tuple[float, float], polygon: np.ndarray) -> bool:
    """point: (x, y) pixel. polygon: np.ndarray (N,2) int32 pixel, tu zone_to_pixels()."""
    return cv2.pointPolygonTest(polygon, (float(point[0]), float(point[1])), False) >= 0


def person_feet_point(xyxy_box) -> tuple[float, float]:
    """Diem 'chan' cua 1 box nguoi (x1,y1,x2,y2) — dung diem nay thay vi tam
    box de kiem tra vi tri thuc te tren mat dat, on dinh hon khi box bi cat
    o phia tren do che khuat."""
    x1, y1, x2, y2 = xyxy_box
    return ((x1 + x2) / 2, y2)
