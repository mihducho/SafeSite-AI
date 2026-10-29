"""Detection: load model YOLO, tra chi so lop theo ten."""
from pathlib import Path

from ultralytics import YOLO

from src.config import load_settings


def load_model(weights: str | Path | None = None) -> YOLO:
    """Mac dinh lay duong dan model tu configs/settings.yaml (model.weights)."""
    if weights is None:
        weights = load_settings()["model"]["weights"]
    if not Path(weights).exists():
        raise FileNotFoundError(f"Khong tim thay file model: {weights}")
    return YOLO(str(weights))


def find_class_ids(model_names: dict[int, str], class_names: list[str]) -> dict[str, int]:
    """Tra chi so lop theo TEN trong model.names (vd "Hardhat" -> 7).

    Khong ghi cung so thu tu de doi sang model khac (vd model 3 lop) van chay.
    Thieu ten nao thi bao loi kem danh sach lop cua model va dung lai.
    """
    by_name = {name: idx for idx, name in model_names.items()}
    missing = [n for n in class_names if n not in by_name]
    if missing:
        raise ValueError(f"Model khong co lop {missing}. Cac lop cua model: {list(model_names.values())}")
    return {n: by_name[n] for n in class_names}
