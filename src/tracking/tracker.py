"""Tracking: theo doi nguoi xuyen cac frame trong 1 camera bang BoT-SORT
(tich hop san trong Ultralytics, khong can cai them thu vien rieng)."""
from pathlib import Path
from typing import Iterator

import numpy as np
from ultralytics import YOLO
from ultralytics.engine.results import Boxes, Results
from ultralytics.trackers.track import TRACKER_MAP
from ultralytics.utils import YAML, IterableSimpleNamespace
from ultralytics.utils.checks import check_yaml


class PersonTracker:
    """Gan track ID chi cho box nguoi.

    Khong dung model.track() khi model co ca class PPE: tracker cua Ultralytics
    ghep box giua cac frame khong phan biet class, nen box ao (chiem gan nua
    box nguoi) va box non nho bi ghep nham/bi bo — thu tren video cong truong
    mat ~65% box non, 1 ID doi class lien tuc. Tach rieng: tracker chi nhan box
    nguoi, box PPE lay thang tu ket qua detect cua tung frame.
    """

    def __init__(self, tracker_cfg: str | Path):
        cfg = IterableSimpleNamespace(**YAML.load(check_yaml(str(tracker_cfg))))
        if getattr(cfg, "with_reid", False):
            # ReID "auto" can dac trung lay tu ben trong predictor, khong co khi goi tracker rieng.
            raise ValueError("PersonTracker chua ho tro with_reid=True, dung configs/botsort_tracking.yaml.")
        self.tracker = TRACKER_MAP[cfg.tracker_type](args=cfg)

    def update(self, person_boxes: Boxes, img: np.ndarray) -> list[int | None]:
        """Cap nhat tracker voi box nguoi cua 1 frame.

        Tra ve list track ID cung thu tu person_boxes; None voi box chua thanh
        track chinh thuc (vd nguoi moi xuat hien o frame dau tien).
        """
        ids: list[int | None] = [None] * len(person_boxes)
        # Van goi ca khi khong co nguoi de tracker dem frame va danh dau track bi mat dau.
        tracks = self.tracker.update(person_boxes.cpu().numpy(), img)
        for t in tracks:  # moi dong: x1, y1, x2, y2, track_id, score, cls, idx (vi tri trong person_boxes)
            ids[int(t[-1])] = int(t[4])
        return ids


def track(
    model: YOLO,
    source,
    tracker: str = "botsort.yaml",
    conf: float = 0.25,
    classes: list[int] | None = [0],
    persist: bool = True,
    **kwargs,
) -> Iterator[Results]:
    """Tra ve iterator cac Results theo tung frame cua video.

    Moi Results.boxes.id la track ID on dinh xuyen frame (None neu frame do
    khong track duoc object nao). persist=True de giu track ID xuyen cac
    lan goi lien tiep khi xu ly video theo stream.
    """
    return model.track(
        source=source,
        tracker=tracker,
        conf=conf,
        classes=classes,
        persist=persist,
        stream=True,
        **kwargs,
    )
