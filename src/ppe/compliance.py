"""Kiem tra tuan thu PPE (trang bi bao ho ca nhan): gan tung box PPE (non bao
ho, ao phan quang...) cho dung nguoi, roi xem moi nguoi con thieu mon nao.

Moi mon PPE chi duoc tinh khi nam dung VUNG co the tuong ung tren box nguoi:
non o vung dau, ao o vung than. Ti le chong lan tinh theo dien tich box PPE
(bao nhieu phan cai non nam trong vung dau), KHONG theo dien tich box nguoi —
vi non chi chiem ~3-5% box nguoi, chia theo box nguoi thi khong bao gio dat
nguong va moi nguoi deu bi bao vi pham.

Neu dataset co class "vi pham" rieng (NO-Hardhat...), khong can dua vao day:
nguoi khong duoc gan box PPE "duong tinh" nao da duoc tinh la thieu.
"""
from dataclasses import dataclass

import numpy as np

# Vung tinh theo ti le chieu cao box nguoi, tinh tu canh tren (0) xuong canh
# duoi (1). Vung dau bat dau tu -0.1 vi non hay nho ra khoi canh tren box nguoi.
HEAD_REGION = (-0.1, 0.35)
TORSO_REGION = (0.15, 0.7)


@dataclass(frozen=True)
class PPERule:
    name: str  # ten mon PPE, vd "hardhat"
    cls_id: int  # class id cua mon PPE trong model
    region: tuple[float, float]  # (tu, den) theo ti le chieu cao box nguoi


def _region_boxes(person_xyxy: np.ndarray, region: tuple[float, float]) -> np.ndarray:
    """Cat box nguoi theo chieu doc thanh vung con (dau/than), giu nguyen chieu ngang."""
    x1, y1, x2, y2 = person_xyxy.T
    h = y2 - y1
    return np.stack([x1, y1 + h * region[0], x2, y1 + h * region[1]], axis=1)


def _inside_ratio(regions: np.ndarray, ppe_xyxy: np.ndarray) -> np.ndarray:
    """Ma tran (so vung, so PPE): ti le dien tich moi box PPE nam trong moi vung."""
    ix1 = np.maximum(regions[:, None, 0], ppe_xyxy[None, :, 0])
    iy1 = np.maximum(regions[:, None, 1], ppe_xyxy[None, :, 1])
    ix2 = np.minimum(regions[:, None, 2], ppe_xyxy[None, :, 2])
    iy2 = np.minimum(regions[:, None, 3], ppe_xyxy[None, :, 3])
    inter = np.clip(ix2 - ix1, 0, None) * np.clip(iy2 - iy1, 0, None)
    ppe_area = (ppe_xyxy[:, 2] - ppe_xyxy[:, 0]) * (ppe_xyxy[:, 3] - ppe_xyxy[:, 1])
    return np.divide(inter, ppe_area[None, :], out=np.zeros_like(inter), where=ppe_area[None, :] > 0)


def assign_ppe(
    person_xyxy: np.ndarray,
    det_xyxy: np.ndarray,
    det_cls: np.ndarray,
    rules: list[PPERule],
    min_inside: float = 0.5,
) -> list[dict[str, bool]]:
    """Tra ve list (cung thu tu person_xyxy) cac dict {ten PPE: True neu co}.

    Moi box PPE chi duoc gan cho 1 nguoi — nguoi co vung tuong ung chua phan
    lon box do nhat — de khi 2 nguoi dung sat nhau, non cua nguoi nay khong bi
    tinh luon cho nguoi kia.
    """
    person_xyxy = np.asarray(person_xyxy, dtype=np.float32).reshape(-1, 4)
    det_xyxy = np.asarray(det_xyxy, dtype=np.float32).reshape(-1, 4)
    det_cls = np.asarray(det_cls).reshape(-1)

    status = [{rule.name: False for rule in rules} for _ in range(len(person_xyxy))]
    if len(person_xyxy) == 0:
        return status

    for rule in rules:
        ppe_xyxy = det_xyxy[det_cls == rule.cls_id]
        if len(ppe_xyxy) == 0:
            continue
        ratio = _inside_ratio(_region_boxes(person_xyxy, rule.region), ppe_xyxy)
        best_person = ratio.argmax(axis=0)
        best_ratio = ratio.max(axis=0)
        for p in best_person[best_ratio >= min_inside]:
            status[p][rule.name] = True
    return status


def missing_ppe(status: dict[str, bool]) -> list[str]:
    """Ten cac mon PPE con thieu cua 1 nguoi, tu 1 phan tu ket qua assign_ppe()."""
    return [name for name, ok in status.items() if not ok]
