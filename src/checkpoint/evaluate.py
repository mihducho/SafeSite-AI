"""Thuat toan kiem tra cua dich vu AI o che do cong (DE_TAI.md muc 5).

evaluate_frames() la ham thuan: nhan danh sach khung hinh, khong doc camera.
Dung cho kiem tra that (check(), Giai doan 1b-2), script chay thu tren video
va test tu dong (truyen bo phat hien gia thay cho model).

Buoc 1 - xet tung khung (classify_frame):
  1. Detect (chi lop nguoi + do bao ho), bo box nguoi trung bang suppress_contained.
  2. Chi giu nguoi co diem chan nam trong vung kiem tra.
  3. 0 nguoi -> "trong"; tu 2 nguoi -> "nhieu_nguoi"; dung 1 nguoi -> xet tiep.
  4. Khung 1 nguoi KHONG hop le neu box nguoi thap hon nguong (qua nho) hoac
     mep tren box cham mep tren khung (dau bi cat, khong xet duoc mu).
  5. Khung hop le: assign_ppe ghi nhan co mu / co ao trong khung do.
Buoc 2 - tong hop (aggregate):
  1. Qua nua so khung "nhieu_nguoi" -> NHIEU_NGUOI.
  2. So khung hop le < min_valid_frames: qua nua so khung "trong" -> KHONG_CO_NGUOI,
     nguoc lai -> KHONG_XAC_DINH.
  3. Moi mon bat buoc: ti le co mat = so khung hop le thay mon do / so khung hop le.
     >= present_ratio -> co; <= absent_ratio -> thieu; o giua -> khong chac.
  4. Co mon khong chac -> KHONG_XAC_DINH; co mon thieu -> KHONG_DAT; con lai -> DAT.
"""
import time
from collections import Counter
from dataclasses import dataclass, field

import cv2
import numpy as np

from src.checkpoint.detector import Detections, get_detector
from src.config import load_settings
from src.detection.detect import find_class_ids
from src.ppe.compliance import assign_kwargs, assign_ppe, rules_from_config
from src.utils.postprocess import suppress_contained
from src.utils.visualize import YELLOW, draw_person, draw_zone
from src.zone.zone import person_feet_point, point_in_zone, zone_to_pixels

# Ket qua tra ve (DE_TAI.md muc 5)
DAT = "DAT"
KHONG_DAT = "KHONG_DAT"
KHONG_XAC_DINH = "KHONG_XAC_DINH"
NHIEU_NGUOI = "NHIEU_NGUOI"
KHONG_CO_NGUOI = "KHONG_CO_NGUOI"

# Loai khung o buoc 1
TRONG = "trong"
NHIEU = "nhieu_nguoi"
KHONG_HOP_LE = "khong_hop_le"
HOP_LE = "hop_le"
QUA_NHO = "qua_nho"  # ly do khung khong hop le
CAT_DAU = "cat_dau"


@dataclass
class FrameResult:
    kind: str  # TRONG / NHIEU / KHONG_HOP_LE / HOP_LE
    reason: str | None = None  # khung khong hop le: QUA_NHO hoac CAT_DAU
    person_xyxy: np.ndarray | None = None  # nguoi duy nhat trong vung (khung 1 nguoi)
    ppe: dict[str, bool] = field(default_factory=dict)  # khung hop le: mon -> co/khong
    zone_persons: np.ndarray = field(default_factory=lambda: np.zeros((0, 4), np.float32))  # de ve anh


def classify_frame(
    det: Detections,
    frame_shape: tuple,
    zone_px: np.ndarray | None,
    person_cls: int,
    rules: list,
    settings: dict,
) -> FrameResult:
    """Buoc 1 cho 1 khung. zone_px: da giac pixel; None = ca khung hinh."""
    ppe_cfg, cp = settings["ppe"], settings["checkpoint"]
    xyxy = np.asarray(det.xyxy, dtype=np.float32).reshape(-1, 4)
    cls = np.asarray(det.cls).reshape(-1)

    persons = xyxy[cls == person_cls]
    persons = persons[suppress_contained(persons, contain_thresh=ppe_cfg["contain_thresh"])]
    if zone_px is None:
        in_zone = np.ones(len(persons), dtype=bool)
    else:
        in_zone = np.array([point_in_zone(person_feet_point(p), zone_px) for p in persons], dtype=bool)
    zone_persons = persons[in_zone]

    if len(zone_persons) == 0:
        return FrameResult(TRONG, zone_persons=zone_persons)
    if len(zone_persons) >= 2:
        return FrameResult(NHIEU, zone_persons=zone_persons)

    person = zone_persons[0]
    if person[3] - person[1] < cp["min_person_height_px"]:
        return FrameResult(KHONG_HOP_LE, QUA_NHO, person, zone_persons=zone_persons)
    if person[1] <= cp["top_edge_margin_px"]:
        return FrameResult(KHONG_HOP_LE, CAT_DAU, person, zone_persons=zone_persons)

    # Gan PPE voi ca nguoi ngoai vung: mu/ao cua nguoi dung sat ben ngoai vung
    # se thuoc ve nguoi do, khong bi tinh nham cho nguoi trong vung.
    status = assign_ppe(persons, xyxy, cls, rules, **assign_kwargs(ppe_cfg))
    return FrameResult(HOP_LE, None, person, status[int(np.flatnonzero(in_zone)[0])], zone_persons)


def aggregate(results: list[FrameResult], required: list[str], settings: dict) -> dict:
    """Buoc 2: tong hop ket qua cac khung thanh 1 ket luan."""
    cp, items = settings["checkpoint"], settings["ppe"]["items"]
    n = len(results)
    kinds = Counter(r.kind for r in results)
    reasons = Counter(r.reason for r in results if r.kind == KHONG_HOP_LE)
    valid = [r for r in results if r.kind == HOP_LE]
    out = {
        "ket_qua": None,
        "thieu": [],
        "ty_le_co_mat": {},
        "so_khung": n,
        "so_khung_hop_le": len(valid),
        "dem_khung": {TRONG: kinds[TRONG], NHIEU: kinds[NHIEU], QUA_NHO: reasons[QUA_NHO],
                      CAT_DAU: reasons[CAT_DAU], HOP_LE: len(valid)},
        "ly_do": None,  # them cho KHONG_XAC_DINH: "it_khung_hop_le" hoac "khong_chac"
    }

    if kinds[NHIEU] > n / 2:
        out["ket_qua"] = NHIEU_NGUOI
        return out
    if len(valid) < cp["min_valid_frames"]:
        if kinds[TRONG] > n / 2:
            out["ket_qua"] = KHONG_CO_NGUOI
        else:
            out["ket_qua"], out["ly_do"] = KHONG_XAC_DINH, "it_khung_hop_le"
        return out

    ratios = {name: sum(r.ppe[name] for r in valid) / len(valid) for name in required}
    out["ty_le_co_mat"] = {name: round(v, 3) for name, v in ratios.items()}
    uncertain = [name for name, v in ratios.items() if cp["absent_ratio"] < v < cp["present_ratio"]]
    missing = [name for name, v in ratios.items() if v <= cp["absent_ratio"]]
    if uncertain:
        out["ket_qua"], out["ly_do"] = KHONG_XAC_DINH, "khong_chac"
    elif missing:
        out["ket_qua"], out["thieu"] = KHONG_DAT, [items[name]["missing_code"] for name in missing]
    else:
        out["ket_qua"] = DAT
    return out


def _snapshot(frames: list, results: list[FrameResult], zone_px_list: list, items: dict, quality: int) -> bytes:
    """Anh JPEG: khung hop le co nguoi lon nhat (khong co thi khung co nguoi lon nhat,
    khong co nua thi khung cuoi), ve vung kiem tra va khung nhan dien."""
    def area(b):
        return float((b[2] - b[0]) * (b[3] - b[1]))

    valid = [i for i, r in enumerate(results) if r.kind == HOP_LE]
    with_person = [i for i, r in enumerate(results) if len(r.zone_persons)]
    pool = valid or with_person
    idx = max(pool, key=lambda i: max(area(b) for b in results[i].zone_persons)) if pool else len(frames) - 1

    img = frames[idx].copy()
    r = results[idx]
    if zone_px_list[idx] is not None:
        draw_zone(img, zone_px_list[idx], color=YELLOW)
    for box in r.zone_persons:
        if r.kind == HOP_LE:
            labels = [items[name]["missing_code"].replace("_", " ").upper() for name, ok in r.ppe.items() if not ok]
        elif r.kind == KHONG_HOP_LE:
            labels = [r.reason.replace("_", " ").upper()]
        else:
            labels = ["NHIEU NGUOI"] if r.kind == NHIEU else []
        draw_person(img, box, "", labels)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, int(quality)])
    return buf.tobytes() if ok else b""


def evaluate_frames(
    frames: list[np.ndarray],
    zone,
    required_ppe: list[str] | None = None,
    config: dict | None = None,
    detector=None,
) -> dict:
    """Kiem tra bao ho tren danh sach khung hinh (BGR, cung 1 luot kiem tra).

    zone: vung kiem tra dang ti le 0-1 [[x, y], ...]; None = ca khung hinh.
    required_ppe: ten cac mon bat buoc (vd ["hardhat", "vest"]); None = ppe.required.
    config: dict tu load_settings(); None = doc configs/settings.yaml.
    detector: bo phat hien (xem detector.py); None = model YOLO trong cau hinh.

    Tra ve dict: ket_qua, thieu, ty_le_co_mat, so_khung, so_khung_hop_le,
    dem_khung, ly_do, thoi_gian_ms, anh_jpeg (bytes; None neu khong co khung nao).
    """
    t0 = time.perf_counter()
    bad = [i for i, f in enumerate(frames) if not isinstance(f, np.ndarray) or f.ndim != 3]
    if bad:
        # Vd doc camera/video loi tra ve None: bao ro thay vi loi kho hieu ben trong.
        raise ValueError(f"Khung hinh khong hop le (None hoac khong phai anh BGR) o vi tri {bad}")
    settings = config if config is not None else load_settings()
    ppe_cfg = settings["ppe"]
    required = list(ppe_cfg["required"] if required_ppe is None else required_ppe)
    unknown = [name for name in required if name not in ppe_cfg["items"]]
    if unknown:
        raise ValueError(f"Mon bao ho chua khai bao trong ppe.items: {unknown}")

    detector = detector if detector is not None else get_detector(settings)
    person_class = settings["model"]["person_class"]
    ids = find_class_ids(detector.names, [person_class] + [ppe_cfg["items"][n]["class_name"] for n in required])
    rules = rules_from_config(ppe_cfg, ids, required)

    results, zone_px_list = [], []
    for frame in frames:
        h, w = frame.shape[:2]
        zone_px = None if zone is None else zone_to_pixels(zone, w, h)
        zone_px_list.append(zone_px)
        results.append(classify_frame(detector(frame), frame.shape, zone_px, ids[person_class], rules, settings))

    out = aggregate(results, required, settings)
    out["anh_jpeg"] = (_snapshot(frames, results, zone_px_list, ppe_cfg["items"],
                                 settings["checkpoint"]["snapshot_jpeg_quality"]) if frames else None)
    out["thoi_gian_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    return out
