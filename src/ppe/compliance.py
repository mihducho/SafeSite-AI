"""Kiem tra tuan thu PPE (trang bi bao ho ca nhan): 1 nguoi duoc xem la vi
pham neu khong co box PPE bat buoc (non bao ho, ao phan quang...) chong lan
du nhieu len vung box cua ho.

Day la cach lam chung, dung khi model chi co class PPE "duong tinh" (Hardhat,
Safety Vest...) + person. Neu dataset/model ban dung da co san class "vi pham"
rieng (NO-Hardhat, NO-Safety Vest...), khong can dung ham nay — chi can doc
thang cac box thuoc class do tu ket qua detect.
"""
import torch


def check_ppe_compliance(
    boxes,
    person_cls: int,
    required_cls: list[int],
    overlap_thresh: float = 0.1,
) -> dict[int, bool]:
    """Tra ve dict {chi so box nguoi (trong boxes): True neu vi pham (thieu PPE)}.

    overlap_thresh thap (mac dinh 0.1) vi non bao ho/ao phan quang thuong chi
    chiem 1 phan nho dien tich box nguoi (vung dau, vai) — khac voi nguong loc
    trung lap vat the toan than (vd 0.5) dung o noi khac trong project.
    """
    if boxes is None or len(boxes) == 0:
        return {}

    cls, xyxy = boxes.cls, boxes.xyxy
    person_idx = (cls == person_cls).nonzero(as_tuple=True)[0]

    ppe_mask = torch.zeros_like(cls, dtype=torch.bool)
    for c in required_cls:
        ppe_mask |= cls == c
    ppe_idx = ppe_mask.nonzero(as_tuple=True)[0]

    result: dict[int, bool] = {}
    for i in person_idx:
        box = xyxy[i]
        area = (box[2] - box[0]) * (box[3] - box[1])
        has_ppe = False
        if area > 0 and len(ppe_idx) > 0:
            ix1 = torch.maximum(box[0], xyxy[ppe_idx, 0])
            iy1 = torch.maximum(box[1], xyxy[ppe_idx, 1])
            ix2 = torch.minimum(box[2], xyxy[ppe_idx, 2])
            iy2 = torch.minimum(box[3], xyxy[ppe_idx, 3])
            inter = (ix2 - ix1).clamp(min=0) * (iy2 - iy1).clamp(min=0)
            has_ppe = bool((inter / area).max() > overlap_thresh)
        result[int(i)] = not has_ppe
    return result
