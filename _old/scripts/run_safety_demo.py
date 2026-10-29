"""[HUONG CU - giu de tham khao] Demo giam sat an toan lao dong tren video cong
truong: detect + track nguoi, kiem tra vi pham PPE theo tung khung va xam nhap
vung nguy hiem, ve ket qua len video va luu vao runs/safety/.

Che do cong (DE_TAI.md muc 5) se la module rieng o Giai doan 1b, khong dung
script nay. Moi tham so doc tu configs/settings.yaml; lop tra theo TEN trong
model.names (Person, Hardhat, Safety-Vest), khong con --person-cls/--hardhat-cls/--vest-cls.

Chay:
    .venv\\Scripts\\python.exe scripts\\run_safety_demo.py --source data\\raw\\ten_video.mp4
    .venv\\Scripts\\python.exe scripts\\run_safety_demo.py --source data\\raw\\ten_video.mp4 --camera camera_1 --show
"""
import argparse
import sys
import time
from pathlib import Path

import cv2
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import DEFAULT_SETTINGS, ROOT, load_settings
from src.detection.detect import detect, find_class_ids, load_model
from src.ppe.compliance import assign_kwargs, assign_ppe, missing_ppe, rules_from_config
from src.tracking.tracker import PersonTracker
from src.utils.postprocess import suppress_contained
from src.utils.visualize import draw_header, draw_person, draw_zone
from src.zone.zone import load_gate_zone, person_feet_point, point_in_zone, zone_to_pixels

OUT_DIR = ROOT / "runs" / "safety"

# Nhan hien thi tren video cho tung loai vi pham.
MISSING_LABELS = {"hardhat": "KHONG NON", "vest": "KHONG AO"}
ZONE_LABEL = "XAM NHAP"


def main():
    parser = argparse.ArgumentParser(description="[Huong cu] Demo giam sat an toan lao dong (PPE + vung nguy hiem).")
    parser.add_argument("--source", type=str, required=True, help="Duong dan video.")
    parser.add_argument("--camera", type=str, default=None, help="Ten vung trong paths.gates_file (ti le 0-1).")
    parser.add_argument("--settings", type=str, default=str(DEFAULT_SETTINGS), help="File cau hinh chung.")
    parser.add_argument("--zones-file", type=str, default=None, help="Mac dinh: paths.gates_file trong cau hinh.")
    parser.add_argument("--show", action="store_true", help="Hien cua so xem truc tiep (bam q de dung).")
    args = parser.parse_args()

    settings = load_settings(args.settings)
    mcfg, ppe_cfg = settings["model"], settings["ppe"]

    model = load_model(mcfg["weights"])
    item_classes = [ppe_cfg["items"][n]["class_name"] for n in ppe_cfg["required"]]
    class_ids = find_class_ids(model.names, [mcfg["person_class"], *item_classes])  # thieu ten lop -> bao loi, dung
    person_cls = class_ids[mcfg["person_class"]]
    rules = rules_from_config(ppe_cfg, class_ids)

    zones_file = args.zones_file or settings["paths"]["gates_file"]
    zone_ratio = None
    if args.camera:
        try:
            zone_ratio = load_gate_zone(zones_file, args.camera)
        except KeyError as e:
            print(f"Canh bao: {e}")
    zone_polygon = None  # quy doi sang pixel o khung dau tien (biet kich thuoc khung)

    print(f"Video dau vao: {args.source}")
    print(f"Weights: {mcfg['weights']} | conf={mcfg['conf']} | iou={mcfg['iou']} | imgsz={mcfg['imgsz']} | lop: {class_ids}")
    print(f"Kiem tra PPE: {', '.join(r.name for r in rules) if rules else 'TAT (ppe.required rong)'}")
    print(f"Kiem tra vung nguy hiem: {'BAT' if zone_ratio is not None else 'TAT'}")

    cap = cv2.VideoCapture(args.source)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    cap.release()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{Path(args.source).stem}_{args.camera or 'cam'}_{time.strftime('%Y%m%d_%H%M%S')}.mp4"
    writer = None

    classes = [person_cls] + [r.cls_id for r in rules]
    # Detect tung frame (giu nguyen moi box PPE), chi box nguoi duoc dua vao tracker.
    results = detect(model, source=args.source, conf=mcfg["conf"], classes=classes, imgsz=mcfg["imgsz"], iou=mcfg["iou"], stream=True, verbose=False)
    tracker = PersonTracker(settings["paths"]["tracker_config"])
    ppe_kwargs = assign_kwargs(ppe_cfg)

    n_frames = 0
    ppe_ids: set[int] = set()
    zone_ids: set[int] = set()
    for r in results:
        n_frames += 1
        frame = r.orig_img.copy()
        if writer is None:
            h, w = frame.shape[:2]
            writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
            if zone_ratio is not None:
                zone_polygon = zone_to_pixels(zone_ratio, w, h)

        if zone_polygon is not None:
            draw_zone(frame, zone_polygon)

        boxes = r.boxes
        person_boxes = boxes[boxes.cls == person_cls]
        keep = suppress_contained(person_boxes.xyxy.cpu().numpy(), contain_thresh=ppe_cfg["contain_thresh"])  # bo box nguoi trung lap
        person_boxes = person_boxes[torch.as_tensor(keep, device=person_boxes.data.device)]
        person_ids = tracker.update(person_boxes, r.orig_img)
        if len(person_boxes) > 0:
            xyxy = boxes.xyxy.cpu().numpy()
            cls = boxes.cls.cpu().numpy().astype(int)
            person_xyxy = person_boxes.xyxy.cpu().numpy()
            ppe_status = assign_ppe(person_xyxy, xyxy, cls, rules, **ppe_kwargs) if rules else [{}] * len(person_xyxy)

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
