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
# Frame lon hon khung nay (vd video 4K) duoc thu nho khi hien thi de vua man hinh;
# toa do click duoc quy doi nguoc ve kich thuoc goc truoc khi luu.
MAX_DISPLAY = (1280, 720)
# yaml.safe_dump xoa het comment trong file, nen ghi lai phan huong dan moi lan luu.
ZONES_HEADER = """\
# Dinh nghia vung nguy hiem theo tung camera: danh sach diem (x, y) theo pixel
# cua khung hinh goc, noi lai thanh da giac khep kin. File nay duoc ghi tu dong
# boi scripts/define_zone.py (click chuot tren 1 frame mau), khong can go tay:
#   .venv\\Scripts\\python.exe scripts\\define_zone.py --source data\\raw\\ten_video.mp4 --camera camera_1
"""


def save_zone(path: Path, camera: str, points: list[list[int]]) -> None:
    data = {}
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    data[camera] = [[round(x), round(y)] for x, y in points]
    with open(path, "w", encoding="utf-8") as f:
        f.write(ZONES_HEADER)
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

    h, w = frame.shape[:2]
    scale = min(MAX_DISPLAY[0] / w, MAX_DISPLAY[1] / h, 1.0)
    frame = cv2.resize(frame, (round(w * scale), round(h * scale))) if scale < 1 else frame

    points: list[list[int]] = []  # toa do tren frame hien thi (da thu nho)

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
            save_zone(Path(args.zones_file), args.camera, [[x / scale, y / scale] for x, y in points])
            print(f"Da luu vung '{args.camera}' voi {len(points)} diem vao {args.zones_file}")
            break
        elif key == ord("q"):
            print("Thoat, khong luu.")
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
