"""Demo detect + track tren 1 video (single-camera baseline, Phase 1).

Chay: .venv\\Scripts\\python.exe scripts\\run_tracking_demo.py
      .venv\\Scripts\\python.exe scripts\\run_tracking_demo.py --source data\\raw\\ten_video.mp4
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.detection.detect import load_model
from src.tracking.tracker import track
from src.utils.postprocess import make_class_overlap_filter

ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DEFAULT_TRACKER = ROOT / "configs" / "botsort_tracking.yaml"
VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv"}


def find_default_video() -> Path:
    videos = sorted(p for p in DATA_RAW.iterdir() if p.suffix.lower() in VIDEO_EXTS)
    if not videos:
        raise FileNotFoundError(
            f"Khong tim thay video nao trong {DATA_RAW}. Hay copy video vao thu muc nay hoac dung --source."
        )
    return videos[0]


def main():
    parser = argparse.ArgumentParser(description="Demo detect + track tren 1 video.")
    parser.add_argument("--source", type=str, default=None, help="Duong dan video. Mac dinh: video dau tien trong data/raw/")
    parser.add_argument("--weights", type=str, default=None, help="Duong dan weights YOLO. Mac dinh: yolo11n.pt. Vi du: yolo11s.pt de tang do chinh xac.")
    parser.add_argument("--conf", type=float, default=0.25, help="Nguong confidence. Tang de giam false positive, giam de bot bo sot nguoi.")
    parser.add_argument("--imgsz", type=int, default=640, help="Kich thuoc anh dua vao model. Tang (vd 960) de bat nguoi nho/xa tot hon, chay se cham hon.")
    parser.add_argument("--tracker", type=str, default=str(DEFAULT_TRACKER), help="Duong dan file cau hinh tracker (.yaml).")
    parser.add_argument(
        "--no-suppress-moto",
        dest="suppress_moto",
        action="store_false",
        default=True,
        help="Tat bo loc nguoi bi nham voi xe may (mac dinh: bat).",
    )
    args = parser.parse_args()

    source = Path(args.source) if args.source else find_default_video()
    print(f"Video dau vao: {source}")
    print(
        f"Weights: {args.weights or 'yolo11n.pt (mac dinh)'} | conf={args.conf} | imgsz={args.imgsz} "
        f"| tracker={args.tracker} | loc nham xe may={args.suppress_moto}"
    )

    model = load_model(args.weights) if args.weights else load_model()
    classes = [0, 3] if args.suppress_moto else [0]
    if args.suppress_moto:
        model.add_callback(
            "on_predict_postprocess_end",
            make_class_overlap_filter(keep_class=0, ref_classes=[3], overlap_thresh=0.5),
        )
    results = track(model, source=str(source), tracker=args.tracker, conf=args.conf, imgsz=args.imgsz, classes=classes, save=True)

    track_ids = set()
    n_frames = 0
    for r in results:
        n_frames += 1
        if r.boxes.id is not None:
            track_ids.update(int(i) for i in r.boxes.id.tolist())

    print(f"So frame da xu ly: {n_frames}")
    print(f"So nguoi (track ID) khac nhau phat hien duoc: {len(track_ids)}")


if __name__ == "__main__":
    main()
