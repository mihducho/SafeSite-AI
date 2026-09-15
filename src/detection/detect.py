"""Detection: load model YOLO va chay inference tren anh/video/thu muc."""
from pathlib import Path

from ultralytics import YOLO
from ultralytics.engine.results import Results

DEFAULT_WEIGHTS = Path(__file__).resolve().parents[2] / "yolo11n.pt"


def load_model(weights: str | Path = DEFAULT_WEIGHTS) -> YOLO:
    return YOLO(str(weights))


def detect(
    model: YOLO,
    source,
    conf: float = 0.25,
    classes: list[int] | None = [0],
    **kwargs,
) -> list[Results]:
    """Chay detect tren 1 anh / video / thu muc anh.

    classes=[0] mac dinh chi lay nguoi (COCO class 0).
    """
    return model.predict(source=source, conf=conf, classes=classes, **kwargs)
