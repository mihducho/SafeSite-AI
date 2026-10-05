"""Cong cu click chuot de ve vung nguy hiem (polygon) tren 1 frame cua video,
roi luu toa do vao configs/zones.yaml.

Chay: .venv\\Scripts\\python.exe scripts\\define_zone.py --source data\\raw\\ten_video.mp4 --camera camera_1

Cach dung: click lan luot cac diem tao thanh da giac (toi thieu 3 diem).
  s = luu va thoat | r = ve lai tu dau | q = thoat khong luu
"""
import argparse
from pathlib import Path

import cv2
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ZONES = ROOT / "configs" / "zones.yaml"


def save_zone(path: Path, camera: str, points: list[list[int]]) -> None:
    data = {}
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    data[camera] = [[int(x), int(y)] for x, y in points]
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


def main():
    parser = argparse.ArgumentParser(description="Ve vung nguy hiem (polygon) tren 1 frame cua video.")
    parser.add_argument("--source", type=str, required=True, help="Duong dan video de lay frame mau.")
    parser.add_argument("--camera", type=str, required=True, help="Ten camera, dung de luu vao configs/zones.yaml.")
    parser.add_argument("--zones-file", type=str, default=str(DEFAULT_ZONES))
    parser.add_argument("--frame-idx", type=int, default=0, help="Lay frame thu may trong video de ve (mac dinh frame dau).")
    args = parser.parse_args()

    cap = cv2.VideoCapture(args.source)
    cap.set(cv2.CAP_PROP_POS_FRAMES, args.frame_idx)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError(f"Khong doc duoc frame {args.frame_idx} tu {args.source}")

    points: list[list[int]] = []

    def on_click(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            points.append([x, y])

    win = "Ve vung nguy hiem - click them diem | s=luu r=ve lai q=thoat"
    cv2.namedWindow(win)
    cv2.setMouseCallback(win, on_click)

    while True:
        disp = frame.copy()
        for p in points:
            cv2.circle(disp, tuple(p), 4, (0, 0, 255), -1)
        if len(points) > 1:
            cv2.polylines(disp, [np.array(points, dtype=np.int32)], isClosed=True, color=(0, 0, 255), thickness=2)
        cv2.imshow(win, disp)
        key = cv2.waitKey(20) & 0xFF

        if key == ord("r"):
            points.clear()
        elif key == ord("s"):
            if len(points) < 3:
                print("Can toi thieu 3 diem de tao thanh 1 vung.")
                continue
            save_zone(Path(args.zones_file), args.camera, points)
            print(f"Da luu vung '{args.camera}' voi {len(points)} diem vao {args.zones_file}")
            break
        elif key == ord("q"):
            print("Thoat, khong luu.")
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
