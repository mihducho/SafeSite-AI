"""Thuat toan kiem tra cua dich vu AI o che do cong (DE_TAI.md muc 5).

evaluate_frames() la ham thuan: nhan danh sach khung hinh, khong doc camera.
Dung cho kiem tra that (check(), Giai doan 1b-2), script chay thu tren video
va test tu dong (truyen bo phat hien gia thay cho model).

Buoc 1 - xet tung khung (classify_frame):
  1. Detect (chi lop nguoi + do bao ho), bo box nguoi trung bang suppress_contained
     (box gop bao nhieu nguoi dung canh nhau thi bo box gop, giu tung nguoi).
  2. Chi giu nguoi co diem chan nam trong vung kiem tra.
  3. 0 nguoi -> "trong"; tu 2 nguoi -> "nhieu_nguoi"; dung 1 nguoi -> xet tiep.
  4. Khung 1 nguoi KHONG hop le neu box nguoi thap hon nguong (qua nho) hoac
     mep tren box cham mep tren khung (dau bi cat, khong xet duoc mu).
  5. Khung hop le: assign_ppe ghi nhan co mu / co ao trong khung do.
Buoc 2 - tong hop (aggregate):
  1. Ti le khung "nhieu_nguoi" >= multi_person_ratio -> NHIEU_NGUOI (cong chi kiem tra
     1 nguoi; co nguoi thu 2 trong vung thi khong xet do bao ho).
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
    persons = persons[suppress_contained(persons, contain_thresh=ppe_cfg["contain_thresh"],
                                         group_max_x_overlap=ppe_cfg["group_max_x_overlap"])]
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

    if n and kinds[NHIEU] / n >= cp["multi_person_ratio"]:
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


class SnapshotPicker:
    """Chon khung de chup anh khi duyet lan luot tung khung, chi giu 1 khung trong bo nho:
    khung hop le co nguoi lon nhat; khong co thi khung co nguoi lon nhat; khong co nua thi khung cuoi."""

    def __init__(self):
        self.key = None
        self.frame = self.result = self.zone_px = None

    def offer(self, frame: np.ndarray, result: FrameResult, zone_px: np.ndarray | None) -> None:
        priority = 2 if result.kind == HOP_LE else (1 if len(result.zone_persons) else 0)
        area = max((float((b[2] - b[0]) * (b[3] - b[1])) for b in result.zone_persons), default=0.0)
        key = (priority, area)
        # Bang nhau thi giu khung den truoc; rieng khung khong co nguoi thi lay khung sau cung.
        if self.key is None or key > self.key or (priority == 0 and self.key[0] == 0):
            self.key, self.frame, self.result, self.zone_px = key, frame, result, zone_px

    def jpeg(self, items: dict, quality: int) -> bytes | None:
        """Anh JPEG cua khung da chon, ve vung kiem tra va khung nhan dien."""
        if self.frame is None:
            return None
        img, r = self.frame.copy(), self.result
        if self.zone_px is not None:
            draw_zone(img, self.zone_px, color=YELLOW)
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


def _ratio_box(box, w: int, h: int) -> list[float]:
    return [round(float(box[0]) / w, 3), round(float(box[1]) / h, 3), round(float(box[2]) / w, 3), round(float(box[3]) / h, 3)]


def frame_detail(det: Detections, result: FrameResult, w: int, h: int, names: dict) -> dict:
    """Chi tiet 1 khung de chan doan (chi so, khong co anh): moi box model tra ve (lop, do tin cay,
    toa do ti le 0-1), loai khung, nguoi duoc tinh trong vung (sau buoc loc box trung)."""
    conf = det.conf if det.conf is not None else [None] * len(det.cls)
    return {
        "loai": result.kind,
        "ly_do": result.reason,
        "box": [{"lop": names[int(c)], "conf": None if cf is None else round(float(cf), 3), "xyxy": _ratio_box(b, w, h)}
                for b, c, cf in zip(det.xyxy, det.cls, conf)],
        "nguoi_trong_vung": [_ratio_box(b, w, h) for b in result.zone_persons],
        "ppe": result.ppe or None,
    }


class FrameEvaluator:
    """Phan dung chung cua evaluate_frames() va check() (DE_TAI muc 5): chuan bi luat 1 lan,
    xet tung khung bang classify_frame ngay khi nhan, chon anh, roi tong hop bang aggregate.
    Hai duong chay goi cung cac buoc nay nen cho ket qua giong nhau.
    record: ghi chi tiet tung khung (frame_detail) vao ket qua, truong "chi_tiet_khung"."""

    def __init__(self, zone, required_ppe: list[str] | None, settings: dict, detector=None, record: bool = False):
        ppe_cfg = settings["ppe"]
        self.required = list(ppe_cfg["required"] if required_ppe is None else required_ppe)
        unknown = [name for name in self.required if name not in ppe_cfg["items"]]
        if unknown:
            raise ValueError(f"Mon bao ho chua khai bao trong ppe.items: {unknown}")
        self.settings, self.zone = settings, zone
        self.detector = detector if detector is not None else get_detector(settings)
        person_class = settings["model"]["person_class"]
        ids = find_class_ids(self.detector.names,
                             [person_class] + [ppe_cfg["items"][n]["class_name"] for n in self.required])
        self.person_cls = ids[person_class]
        self.rules = rules_from_config(ppe_cfg, ids, self.required)
        self.results: list[FrameResult] = []
        self.picker = SnapshotPicker()
        self._frame_ms: list[float] = []
        self.record = record
        self.details: list[dict] = []

    def add(self, frame: np.ndarray) -> FrameResult:
        """Buoc 1 cho 1 khung (detect + classify_frame), luu ket qua va ung vien anh chup."""
        t = time.perf_counter()
        h, w = frame.shape[:2]
        zone_px = None if self.zone is None else zone_to_pixels(self.zone, w, h)
        det = self.detector(frame)
        result = classify_frame(det, frame.shape, zone_px, self.person_cls, self.rules, self.settings)
        self.results.append(result)
        self.picker.offer(frame, result, zone_px)
        self._frame_ms.append((time.perf_counter() - t) * 1000)
        if self.record:
            self.details.append(frame_detail(det, result, w, h, self.detector.names))
        return result

    def finish(self, t0: float) -> dict:
        """Buoc 2 + anh JPEG + thoi gian (tinh tu t0 = luc bat dau luot kiem tra)."""
        out = aggregate(self.results, self.required, self.settings)
        out["anh_jpeg"] = self.picker.jpeg(self.settings["ppe"]["items"],
                                           self.settings["checkpoint"]["snapshot_jpeg_quality"])
        out["ms_moi_khung"] = round(sum(self._frame_ms) / len(self._frame_ms), 1) if self._frame_ms else None
        out["thoi_gian_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        if self.record:
            out["chi_tiet_khung"] = self.details
        return out


def evaluate_frames(
    frames: list[np.ndarray],
    zone,
    required_ppe: list[str] | None = None,
    config: dict | None = None,
    detector=None,
    record_frames: bool = False,
) -> dict:
    """Kiem tra bao ho tren danh sach khung hinh (BGR, cung 1 luot kiem tra).

    zone: vung kiem tra dang ti le 0-1 [[x, y], ...]; None = ca khung hinh.
    required_ppe: ten cac mon bat buoc (vd ["hardhat", "vest"]); None = ppe.required.
    config: dict tu load_settings(); None = doc configs/settings.yaml.
    detector: bo phat hien (xem detector.py); None = model YOLO trong cau hinh.

    Tra ve dict: ket_qua, thieu, ty_le_co_mat, so_khung, so_khung_hop_le,
    dem_khung, ly_do, thoi_gian_ms, ms_moi_khung (thoi gian TB xu ly 1 khung),
    anh_jpeg (bytes; None neu khong co khung nao); record_frames=True thi them
    chi_tiet_khung (danh sach frame_detail, de chan doan).
    """
    t0 = time.perf_counter()
    bad = [i for i, f in enumerate(frames) if not isinstance(f, np.ndarray) or f.ndim != 3]
    if bad:
        # Vd doc camera/video loi tra ve None: bao ro thay vi loi kho hieu ben trong.
        raise ValueError(f"Khung hinh khong hop le (None hoac khong phai anh BGR) o vi tri {bad}")
    settings = config if config is not None else load_settings()
    evaluator = FrameEvaluator(zone, required_ppe, settings, detector, record=record_frames)
    for frame in frames:
        evaluator.add(frame)
    return evaluator.finish(t0)
