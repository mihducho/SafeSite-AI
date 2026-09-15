"""Tracking: theo doi nguoi xuyen cac frame trong 1 camera bang BoT-SORT
(tich hop san trong Ultralytics, khong can cai them thu vien rieng)."""
from typing import Iterator

from ultralytics import YOLO
from ultralytics.engine.results import Results


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
