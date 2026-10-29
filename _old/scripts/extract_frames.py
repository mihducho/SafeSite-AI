"""Trich frame tu video de dua vao gan nhan (chuan bi fine-tune detection).

Chay: .venv\\Scripts\\python.exe scripts\\extract_frames.py --source data\\raw\\test15-9.mp4
      .venv\\Scripts\\python.exe scripts\\extract_frames.py --source data\\raw\\test15-9.mp4 --every 10
"""
import argparse
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description="Trich frame tu video, cach nhau N frame, de gan nhan.")
    parser.add_argument("--source", type=str, required=True, help="Duong dan video nguon.")
    parser.add_argument(
        "--every",
        type=int,
        default=15,
        help="Lay 1 frame moi N frame (mac dinh 15, ~2 frame/giay voi video 30fps). Giam neu can nhieu anh hon.",
    )
    parser.add_argument("--out", type=str, default=None, help="Thu muc luu anh. Mac dinh: data/processed/frames_<ten_video>/")
    args = parser.parse_args()

    source = Path(args.source)
    out_dir = Path(args.out) if args.out else ROOT / "data" / "processed" / f"frames_{source.stem}"
    out_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened():
        raise FileNotFoundError(f"Khong mo duoc video: {source}")

    idx = 0
    saved = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % args.every == 0:
            out_path = out_dir / f"{source.stem}_{idx:06d}.jpg"
            cv2.imwrite(str(out_path), frame)
            saved += 1
        idx += 1
    cap.release()

    print(f"Da doc {idx} frame, luu {saved} anh vao {out_dir}")


if __name__ == "__main__":
    main()
