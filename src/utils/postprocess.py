"""Loc box bi nham lan giua 2 class (vd: nguoi bi nham thanh xe may) truoc khi
tracker gan ID. Dung nhu callback 'on_predict_postprocess_end' cua Ultralytics —
callback nay chay ngay sau khi model detect xong va truoc khi tracker/luu video,
nen sua boxes o day se anh huong ca ket qua tracking lan video luu ra.
"""
import torch


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
