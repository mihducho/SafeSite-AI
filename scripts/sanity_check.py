"""Kiem tra moi truong: tai YOLOv11n pretrained va chay detect tren anh mau.
Chay: .venv\\Scripts\\python.exe scripts\\sanity_check.py
"""
from ultralytics import YOLO

model = YOLO("yolo11n.pt")  # tu dong tai pretrained COCO weights
results = model.predict(source="https://ultralytics.com/images/bus.jpg", save=True, classes=[0])  # class 0 = person

for r in results:
    print(f"So nguoi phat hien: {len(r.boxes)}")
    print(f"Anh ket qua luu tai: {r.save_dir}")
