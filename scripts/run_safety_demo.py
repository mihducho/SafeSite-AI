"""Demo giam sat an toan lao dong: detect+track nguoi (rieng tung camera,
khong Re-ID xuyen camera), kiem tra vi pham PPE va canh bao xam nhap vung
nguy hiem. Ve ket qua len video va luu vao runs/safety/.

Chay voi model goc COCO (chi kiem tra vung nguy hiem, chua co PPE):
    .venv\\Scripts\\python.exe scripts\\run_safety_demo.py --source data\\raw\\ten_video.mp4 --camera camera_1
Chay voi model PPE da fine-tune (class theo configs/data_ppe.yaml):
    .venv\\Scripts\\python.exe scripts\\run_safety_demo.py --source data\\raw\\ten_video.mp4 --camera camera_1 \\
        --weights best_ppe.pt --person-cls 5 --hardhat-cls 0 --vest-cls 6
"""
import argparse
import sys
import time
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.detection.detect import load_model
from src.ppe.compliance import HEAD_REGION, TORSO_REGION, PPERule, assign_ppe, missing_ppe
from src.tracking.tracker import track
from src.utils.visualize import draw_header, draw_person, draw_zone
from src.zone.zone import load_zones, person_feet_point, point_in_zone

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRACKER = ROOT / "configs" / "botsort_tracking.yaml"
DEFAULT_ZONES = ROOT / "configs" / "zones.yaml"
OUT_DIR = ROOT / "runs" / "safety"

# Nhan hien thi tren video cho tung loai vi pham.
MISSING_LABELS = {"hardhat": "KHONG NON", "vest": "KHONG AO"}
ZONE_LABEL = "XAM NHAP"


def build_rules(hardhat_cls: int | None, vest_cls: int | None) -> list[PPERule]:
    rules = []
    if hardhat_cls is not None:
        rules.append(PPERule("hardhat", hardhat_cls, HEAD_REGION))
    if vest_cls is not None:
        rules.append(PPERule("vest", vest_cls, TORSO_REGION))
    return rules


def main():
    parser = argparse.ArgumentParser(description="Demo giam sat an toan lao dong (PPE + vung nguy hiem).")
    parser.add_argument("--source", type=str, required=True, help="Duong dan video.")
    parser.add_argument("--camera", type=str, default=None, help="Ten camera, de lay dung vung nguy hiem trong zones.yaml.")
    parser.add_argument("--weights", type=str, default=None, help="Weight model. Mac dinh yolo11n.pt (COCO, chua co PPE).")
    parser.add_argument("--conf", type=float, default=0.35)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--tracker", type=str, default=str(DEFAULT_TRACKER))
    parser.add_argument("--zones-file", type=str, default=str(DEFAULT_ZONES))
    parser.add_argument("--person-cls", type=int, default=0, help="Class id cua nguoi (COCO: 0, data_ppe.yaml: 5).")
    parser.add_argument("--hardhat-cls", type=int, default=None, help="Class id non bao ho. Bo trong = khong kiem tra non.")
    parser.add_argument("--vest-cls", type=int, default=None, help="Class id ao phan quang. Bo trong = khong kiem tra ao.")
    parser.add_argument("--show", action="store_true", help="Hien cua so xem truc tiep (bam q de dung).")
    args = parser.parse_args()

    rules = build_rules(args.hardhat_cls, args.vest_cls)
    # Neu class nguoi trung class PPE thi moi box nguoi tu duoc tinh la co PPE.
    if args.person_cls in [r.cls_id for r in rules]:
        parser.error(f"--person-cls ({args.person_cls}) khong duoc trung voi class PPE.")

    zones = load_zones(args.zones_file)
    zone_polygon = zones.get(args.camera) if args.camera else None
    if args.camera and zone_polygon is None:
        print(f"Canh bao: khong tim thay vung nguy hiem cho camera '{args.camera}' trong {args.zones_file}.")

    print(f"Video dau vao: {args.source}")
    print(f"Weights: {args.weights or 'yolo11n.pt (mac dinh)'} | conf={args.conf} | imgsz={args.imgsz} | person_cls={args.person_cls}")
    print(f"Kiem tra PPE: {', '.join(r.name for r in rules) if rules else 'TAT (chua co class PPE)'}")
    print(f"Kiem tra vung nguy hiem: {'BAT' if zone_polygon is not None else 'TAT'}")

    cap = cv2.VideoCapture(args.source)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    cap.release()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{Path(args.source).stem}_{args.camera or 'cam'}_{time.strftime('%Y%m%d_%H%M%S')}.mp4"
    writer = None

    model = load_model(args.weights) if args.weights else load_model()
    classes = [args.person_cls] + [r.cls_id for r in rules]
    results = track(model, source=args.source, tracker=args.tracker, conf=args.conf, imgsz=args.imgsz, classes=classes, verbose=False)

    n_frames = 0
    ppe_ids: set[int] = set()
    zone_ids: set[int] = set()
    for r in results:
        n_frames += 1
        frame = r.orig_img.copy()
        if writer is None:
            h, w = frame.shape[:2]
            writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))

        if zone_polygon is not None:
            draw_zone(frame, zone_polygon)

        boxes = r.boxes
        if boxes is not None and len(boxes) > 0:
            xyxy = boxes.xyxy.cpu().numpy()
            cls = boxes.cls.cpu().numpy().astype(int)
            ids = boxes.id.int().cpu().tolist() if boxes.id is not None else [None] * len(boxes)

            person_mask = cls == args.person_cls
            person_xyxy = xyxy[person_mask]
            person_ids = [i for i, m in zip(ids, person_mask) if m]
            ppe_status = assign_ppe(person_xyxy, xyxy, cls, rules) if rules else [{}] * len(person_xyxy)

            for box, tid, status in zip(person_xyxy, person_ids, ppe_status):
                violations = [MISSING_LABELS[name] for name in missing_ppe(status)]
                if violations and tid is not None:
                    ppe_ids.add(tid)
                if zone_polygon is not None and point_in_zone(person_feet_point(box), zone_polygon):
                    violations.append(ZONE_LABEL)
                    if tid is not None:
                        zone_ids.add(tid)
                draw_person(frame, box, f"#{tid}" if tid is not None else "", violations)

        header = [f"{args.camera or 'camera'} | frame {n_frames}"]
        if rules:
            header.append(f"Vi pham PPE: {len(ppe_ids)} nguoi")
        if zone_polygon is not None:
            header.append(f"Xam nhap vung: {len(zone_ids)} nguoi")
        draw_header(frame, header)
        writer.write(frame)

        if args.show:
            cv2.imshow("SafeSite AI - bam q de dung", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    if writer is not None:
        writer.release()
    cv2.destroyAllWindows()

    print(f"So frame da xu ly: {n_frames}")
    if rules:
        print(f"So nguoi (track ID) vi pham PPE: {len(ppe_ids)}")
    if zone_polygon is not None:
        print(f"So nguoi (track ID) xam nhap vung nguy hiem: {len(zone_ids)}")
    print(f"Video ket qua: {out_path}")


if __name__ == "__main__":
    main()
