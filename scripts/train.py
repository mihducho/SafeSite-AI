"""Fine-tune YOLO phat hien PPE (non bao ho, ao phan quang...). Chay tren
Colab/Kaggle (co GPU) — may local khong co GPU roi nen fine-tune se rat cham.

Vi du tren Colab (sau khi upload/clone project + dataset):
    !pip install ultralytics
    !python scripts/train.py --data configs/data_ppe.yaml --weights yolo11n.pt --epochs 100
"""
import argparse
from pathlib import Path

from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description="Fine-tune YOLO tren dataset gan nhan rieng.")
    parser.add_argument("--data", type=str, default=str(ROOT / "configs" / "data_ppe.yaml"), help="Duong dan file data.yaml.")
    parser.add_argument("--weights", type=str, default="yolo11n.pt", help="Weight khoi diem (pretrained COCO).")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    args = parser.parse_args()

    model = YOLO(args.weights)
    model.train(data=args.data, epochs=args.epochs, imgsz=args.imgsz, batch=args.batch)


if __name__ == "__main__":
    main()
