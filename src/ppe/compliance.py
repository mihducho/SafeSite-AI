"""Kiem tra tuan thu PPE (trang bi bao ho ca nhan): gan tung box PPE (non bao
ho, ao phan quang...) cho dung nguoi, roi xem moi nguoi con thieu mon nao.

Moi mon PPE chi duoc tinh khi nam dung VUNG co the tuong ung tren box nguoi:
non o vung dau, ao o vung than. Ti le chong lan tinh theo dien tich box PPE
(bao nhieu phan cai non nam trong vung dau), KHONG theo dien tich box nguoi —
vi non chi chiem ~3-5% box nguoi, chia theo box nguoi thi khong bao gio dat
nguong va moi nguoi deu bi bao vi pham.

Khong dung cac lop "vi pham" (NO-Hardhat...): nguoi khong duoc gan box PPE
"duong tinh" nao thi tinh la thieu.

Moi nguong (vung dau/than, ti le toi thieu...) doc tu configs/settings.yaml
(muc ppe), truyen vao qua tham so — khong ghi cung trong file nay.
"""
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PPERule:
    name: str  # ten mon PPE trong cau hinh, vd "hardhat"
    cls_id: int  # chi so lop cua mon PPE trong model (tra theo ten, xem rules_from_config)
    region: tuple[float, float]  # (tu, den) theo ti le chieu cao box nguoi


def rules_from_config(ppe_cfg: dict, class_ids: dict[str, int], required: list[str] | None = None) -> list[PPERule]:
    """Tao luat kiem tra tu muc `ppe` cua settings.yaml.

    class_ids: ten lop -> chi so lop (ket qua cua find_class_ids).
    required: cac mon can kiem tra; None = dung ppe.required trong cau hinh.
    """
    names = ppe_cfg["required"] if required is None else required
    rules = []
    for name in names:
        item = ppe_cfg["items"][name]
        rules.append(PPERule(name, class_ids[item["class_name"]], tuple(item["region"])))
    return rules


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
    *,
    min_inside: float,
    upright_min_ratio: float,
    whole_box_region: tuple[float, float],
) -> list[dict[str, bool]]:
    """Tra ve list (cung thu tu person_xyxy) cac dict {ten PPE: True neu co}.

    Moi box PPE chi duoc gan cho 1 nguoi — nguoi co vung tuong ung chua phan
    lon box do nhat — de khi 2 nguoi dung sat nhau, non cua nguoi nay khong bi
    tinh luon cho nguoi kia.

    min_inside: ti le dien tich box PPE toi thieu phai nam trong vung.
    upright_min_ratio, whole_box_region: box nguoi co cao/rong < upright_min_ratio
    (nguoi cui gap, ngoi xom, bo) thi dau va than khong con nam theo chieu doc —
    vd nguoi cui: dau o giua canh ben — nen dung whole_box_region (gan ca box)
    thay cho vung dau/than. Nguoi dung thang (ti le ~2-3) van giu quy tac chat,
    non cam o chan khong duoc tinh.
    Ca 3 tham so lay tu settings.yaml (muc ppe), xem assign_kwargs().
    """
    person_xyxy = np.asarray(person_xyxy, dtype=np.float32).reshape(-1, 4)
    det_xyxy = np.asarray(det_xyxy, dtype=np.float32).reshape(-1, 4)
    det_cls = np.asarray(det_cls).reshape(-1)

    status = [{rule.name: False for rule in rules} for _ in range(len(person_xyxy))]
    if len(person_xyxy) == 0:
        return status

    h = person_xyxy[:, 3] - person_xyxy[:, 1]
    w = person_xyxy[:, 2] - person_xyxy[:, 0]
    not_upright = h < upright_min_ratio * w

    for rule in rules:
        ppe_xyxy = det_xyxy[det_cls == rule.cls_id]
        if len(ppe_xyxy) == 0:
            continue
        regions = _region_boxes(person_xyxy, rule.region)
        regions[not_upright] = _region_boxes(person_xyxy[not_upright], whole_box_region)
        ratio = _inside_ratio(regions, ppe_xyxy)
        best_person = ratio.argmax(axis=0)
        best_ratio = ratio.max(axis=0)
        for p in best_person[best_ratio >= min_inside]:
            status[p][rule.name] = True
    return status


def assign_kwargs(ppe_cfg: dict) -> dict:
    """Cac tham so nguong cua assign_ppe() lay tu muc `ppe` cua settings.yaml."""
    return {
        "min_inside": ppe_cfg["min_inside"],
        "upright_min_ratio": ppe_cfg["upright_min_ratio"],
        "whole_box_region": tuple(ppe_cfg["whole_box_region"]),
    }


def missing_ppe(status: dict[str, bool]) -> list[str]:
    """Ten cac mon PPE con thieu cua 1 nguoi, tu 1 phan tu ket qua assign_ppe()."""
    return [name for name, ok in status.items() if not ok]
