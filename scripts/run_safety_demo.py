"""Demo giam sat an toan lao dong: detect+track nguoi (rieng tung camera,
khong Re-ID xuyen camera), kiem tra vi pham PPE va canh bao xam nhap vung
nguy hiem.

Chay: .venv\\Scripts\\python.exe scripts\\run_safety_demo.py --source data\\raw\\ten_video.mp4
      .venv\\Scripts\\python.exe scripts\\run_safety_demo.py --source data\\raw\\ten_video.mp4 --camera camera_1 --weights best_ppe.pt
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.detection.detect import load_model
from src.ppe.compliance import check_ppe_compliance
from src.tracking.tracker import track
from src.zone.zone import load_zones, person_feet_point, point_in_zone

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRACKER = ROOT / "configs" / "botsort_tracking.yaml"
DEFAULT_ZONES = ROOT / "configs" / "zones.yaml"

# Mac dinh theo configs/data_ppe.yaml (class 5 = Person, class 0 = Hardhat).
# Doi lai cho dung model/dataset PPE ban thuc te dang dung.
DEFAULT_PERSON_CLS = 5
DEFAULT_PPE_CLASSES = [0]


def main():
    parser = argparse.ArgumentParser(description="Demo giam sat an toan lao dong (PPE + vung nguy hiem).")
    parser.add_argument("--source", type=str, required=True, help="Duong dan video.")
    parser.add_argument("--camera", type=str, default=None, help="Ten camera, de lay dung vung nguy hiem trong zones.yaml.")
    parser.add_argument("--weights", type=str, default=None, help="Weight model (nen la model da fine-tune PPE).")
    parser.add_argument("--conf", type=float, default=0.35)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--tracker", type=str, default=str(DEFAULT_TRACKER))
    parser.add_argument("--zones-file", type=str, default=str(DEFAULT_ZONES))
    parser.add_argument("--person-cls", type=int, default=DEFAULT_PERSON_CLS, help="Class id cua nguoi trong model.")
    parser.add_argument(
        "--ppe-classes",
        type=int,
        nargs="*",
        default=DEFAULT_PPE_CLASSES,
        help="Danh sach class id cua PPE bat buoc (vd non bao ho).",
    )
    args = parser.parse_args()

    # Neu class nguoi trung class PPE thi moi box nguoi tu chong lan len chinh
    # no -> khong bao gio bao vi pham.
    if args.person_cls in args.ppe_classes:
        parser.error(f"--person-cls ({args.person_cls}) khong duoc trung voi --ppe-classes ({args.ppe_classes}).")

    zones = load_zones(args.zones_file)
    zone_polygon = zones.get(args.camera) if args.camera else None
    if args.camera and zone_polygon is None:
        print(f"Canh bao: khong tim thay vung nguy hiem cho camera '{args.camera}' trong {args.zones_file}.")

    print(f"Video dau vao: {args.source}")
    print(f"Weights: {args.weights or 'yolo11n.pt (mac dinh)'} | conf={args.conf} | imgsz={args.imgsz} | person_cls={args.person_cls} | ppe_classes={args.ppe_classes}")

    model = load_model(args.weights) if args.weights else load_model()
    classes = [args.person_cls] + list(args.ppe_classes)
    results = track(model, source=args.source, tracker=args.tracker, conf=args.conf, imgsz=args.imgsz, classes=classes, save=True)

    n_frames = 0
    ppe_violation_frames = 0
    zone_intrusion_frames = 0
    for r in results:
        n_frames += 1
        boxes = r.boxes
        if boxes is None or len(boxes) == 0:
            continue

        violations = check_ppe_compliance(boxes, person_cls=args.person_cls, required_cls=args.ppe_classes)
        if any(violations.values()):
            ppe_violation_frames += 1

        if zone_polygon is not None:
            person_idx = (boxes.cls == args.person_cls).nonzero(as_tuple=True)[0]
            for i in person_idx:
                feet = person_feet_point(boxes.xyxy[i].tolist())
                if point_in_zone(feet, zone_polygon):
                    zone_intrusion_frames += 1
                    break

    print(f"So frame da xu ly: {n_frames}")
    print(f"So frame co vi pham PPE: {ppe_violation_frames}")
    if zone_polygon is not None:
        print(f"So frame co nguoi xam nhap vung nguy hiem: {zone_intrusion_frames}")


if __name__ == "__main__":
    main()
