"""Loc box bi nham lan giua 2 class (vd: nguoi bi nham thanh xe may) truoc khi
tracker gan ID. Dung nhu callback 'on_predict_postprocess_end' cua Ultralytics —
callback nay chay ngay sau khi model detect xong va truoc khi tracker/luu video,
nen sua boxes o day se anh huong ca ket qua tracking lan video luu ra.
"""
import numpy as np
import torch


def suppress_contained(xyxy: np.ndarray, *, contain_thresh: float,
                       group_max_x_overlap: float | None = None) -> np.ndarray:
    """Mask giu lai cac box KHONG nam gan tron trong 1 box lon hon cung class.

    Model hay ve 2 box "Person" cho 1 nguoi dang cui/bi che (1 box ca nguoi +
    1 box nho ben trong). NMS cua YOLO khong loai duoc vi IoU giua 2 box chi
    ~0.5. Neu khong loai, non bi gan cho box nay, ao cho box kia -> ca 2 "nguoi"
    deu bi bao thieu PPE, va tracker cap them ID.

    Box bi bo neu >= contain_thresh dien tich cua no nam trong 1 box khac co
    dien tich lon hon. contain_thresh lay tu settings.yaml (ppe.contain_thresh,
    hien la 0.8): nguong cao de nguoi dung sau, bi che 1 phan, van duoc giu.

    Box gop (group_max_x_overlap, ppe.group_max_x_overlap): 2 nguoi dung sat vai nhau
    thi model co the ve them 1 box bao ca hai. Box lon chua >= 2 box dung CANH NHAU
    (chong nhau theo chieu ngang <= group_max_x_overlap chieu rong box hep hon) la box
    gop: bo box gop, giu tung nguoi. Box nua than tren + nua than duoi cua 1 nguoi
    chong nhau gan het chieu ngang nen khong bi coi la 2 nguoi. None = khong xet box gop.
    """
    xyxy = np.asarray(xyxy, dtype=np.float32).reshape(-1, 4)
    area = (xyxy[:, 2] - xyxy[:, 0]) * (xyxy[:, 3] - xyxy[:, 1])
    ix1 = np.maximum(xyxy[:, None, 0], xyxy[None, :, 0])
    iy1 = np.maximum(xyxy[:, None, 1], xyxy[None, :, 1])
    ix2 = np.minimum(xyxy[:, None, 2], xyxy[None, :, 2])
    iy2 = np.minimum(xyxy[:, None, 3], xyxy[None, :, 3])
    inter = np.clip(ix2 - ix1, 0, None) * np.clip(iy2 - iy1, 0, None)
    # contained[i, j]: ti le dien tich box i nam trong box j
    contained = np.divide(inter, area[:, None], out=np.zeros_like(inter), where=area[:, None] > 0)
    inside_bigger = (contained >= contain_thresh) & (area[None, :] > area[:, None])
    if group_max_x_overlap is None:
        return ~inside_bigger.any(axis=1)

    group = _group_boxes(xyxy, inside_bigger, group_max_x_overlap)
    inside_bigger[:, group] = False  # nguoi nam trong box gop khong bi bo vi box gop
    return ~inside_bigger.any(axis=1) & ~group


def _group_boxes(xyxy: np.ndarray, inside_bigger: np.ndarray, max_x_overlap: float) -> np.ndarray:
    """Mask cac box chua >= 2 box (inside_bigger[:, j]) dung canh nhau theo chieu ngang."""
    width = xyxy[:, 2] - xyxy[:, 0]
    group = np.zeros(len(xyxy), dtype=bool)
    for j in range(len(xyxy)):
        members = np.flatnonzero(inside_bigger[:, j])
        for k, a in enumerate(members):
            for b in members[k + 1:]:
                x_inter = max(0.0, float(min(xyxy[a, 2], xyxy[b, 2]) - max(xyxy[a, 0], xyxy[b, 0])))
                if x_inter <= max_x_overlap * max(float(min(width[a], width[b])), 1e-6):
                    group[j] = True
    return group


def make_class_overlap_filter(keep_class: int, ref_classes: list[int], overlap_thresh: float = 0.5):
    """Tao callback: bo box thuoc keep_class neu no chong lan > overlap_thresh
    dien tich len bat ky box nao thuoc ref_classes (vd: person(0) hay bi ve chong
    len motorcycle(3) tren cung 1 chiec xe do model pretrained COCO nham lan).
    Cac box thuoc ref_classes cung bi bo khoi ket qua cuoi — chi dung de tham
    chieu loc, khong hien thi/track.
    """

    def _callback(predictor) -> None:
        for result in predictor.results:
            boxes = result.boxes
            if boxes is None or len(boxes) == 0:
                continue
            cls, xyxy = boxes.cls, boxes.xyxy
            keep_idx = (cls == keep_class).nonzero(as_tuple=True)[0]
            ref_mask = torch.zeros_like(cls, dtype=torch.bool)
            for c in ref_classes:
                ref_mask |= cls == c
            ref_idx = ref_mask.nonzero(as_tuple=True)[0]
            if len(ref_idx) == 0:
                continue

            keep_mask = torch.ones(len(boxes), dtype=torch.bool, device=cls.device)
            for i in keep_idx:
                box = xyxy[i]
                area = (box[2] - box[0]) * (box[3] - box[1])
                if area <= 0:
                    continue
                ix1 = torch.maximum(box[0], xyxy[ref_idx, 0])
                iy1 = torch.maximum(box[1], xyxy[ref_idx, 1])
                ix2 = torch.minimum(box[2], xyxy[ref_idx, 2])
                iy2 = torch.minimum(box[3], xyxy[ref_idx, 3])
                inter = (ix2 - ix1).clamp(min=0) * (iy2 - iy1).clamp(min=0)
                if (inter / area).max() > overlap_thresh:
                    keep_mask[i] = False

            keep_mask[ref_idx] = False
            result.update(boxes=boxes.data[keep_mask])

    return _callback
