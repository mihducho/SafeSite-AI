"""Click chuot ve VUNG KIEM TRA (da giac) cua 1 cong tren 1 khung hinh, luu dang
ti le 0-1 so voi khung hinh vao configs/gates.yaml (paths.gates_file).

Chay:
  .venv\\Scripts\\python.exe scripts\\define_zone.py --source data\\raw\\ten_video.mp4 --gate cong_1
  .venv\\Scripts\\python.exe scripts\\define_zone.py --source 0 --gate cong_1                          (webcam)
  .venv\\Scripts\\python.exe scripts\\define_zone.py --source http://192.168.1.23:8080/video --gate cong_1   (dien thoai)

Cach dung: click lan luot cac diem tao thanh da giac (toi thieu 3 diem). Vung nen
bao phan SAN noi cong nhan dung (he thong xet DIEM CHAN cua nguoi).
  s = luu va thoat | r = ve lai tu dau | q = thoat khong luu
Vung cu cua cong (neu co) hien mau xam de tham khao.
"""
import argparse
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.checkpoint.camera import CameraReader, open_capture, parse_source
from src.config import load_settings
from src.zone.zone import clicks_to_ratio, load_gates, save_gate_zone, zone_to_pixels

# Khung lon hon (vd 4K) duoc thu nho khi hien thi cho vua man hinh. Luu dang ti le
# nen khong can quy doi nguoc: ti le tren anh thu nho = ti le tren anh goc.
MAX_DISPLAY = (1280, 720)
CAMERA_WARMUP_S = 1.5  # webcam/dien thoai: cho vai khung dau de camera tu chinh sang


def grab_frame(source: str, frame_idx: int, cam_cfg: dict) -> np.ndarray:
    src = parse_source(source)
    if src.kind == "file":
        cap = open_capture(src, cam_cfg)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ok, frame = cap.read()
        cap.release()
        if not ok:
            raise RuntimeError(f"Khong doc duoc khung {frame_idx} tu {source}")
        return frame
    with CameraReader(source, cam_cfg) as cam:
        time.sleep(CAMERA_WARMUP_S)
        return cam.latest()[1]


def main():
    settings = load_settings()
    parser = argparse.ArgumentParser(description="Ve vung kiem tra (da giac, ti le 0-1) cho 1 cong.")
    parser.add_argument("--source", type=str, required=True, help="File video, so webcam (vd 0) hoac URL camera dien thoai.")
    parser.add_argument("--gate", type=str, required=True, help="Ten cong, dung lam khoa trong file vung (vd cong_1).")
    parser.add_argument("--gates-file", type=str, default=str(settings["paths"]["gates_file"]))
    parser.add_argument("--frame-idx", type=int, default=0, help="File video: lay khung thu may de ve (mac dinh khung dau).")
    args = parser.parse_args()

    frame = grab_frame(args.source, args.frame_idx, settings["camera"])
    h, w = frame.shape[:2]
    scale = min(MAX_DISPLAY[0] / w, MAX_DISPLAY[1] / h, 1.0)
    frame = cv2.resize(frame, (round(w * scale), round(h * scale))) if scale < 1 else frame
    disp_h, disp_w = frame.shape[:2]
    print(f"Khung hinh goc {w}x{h}, hien thi {disp_w}x{disp_h}")

    old = (load_gates(args.gates_file).get(args.gate) or {}).get("zone")
    old_px = zone_to_pixels(old, disp_w, disp_h) if old else None

    points: list[list[int]] = []  # toa do click tren anh dang hien thi

    def on_click(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            points.append([x, y])

    win = f"Vung kiem tra '{args.gate}' - click them diem | s=luu r=ve lai q=thoat"
    cv2.namedWindow(win)
    cv2.setMouseCallback(win, on_click)

    while True:
        disp = frame.copy()
        if old_px is not None:
            cv2.polylines(disp, [old_px], isClosed=True, color=(160, 160, 160), thickness=1)
        for p in points:
            cv2.circle(disp, tuple(p), 4, (0, 220, 255), -1)
        if len(points) > 1:
            cv2.polylines(disp, [np.array(points, dtype=np.int32)], isClosed=True, color=(0, 220, 255), thickness=2)
        cv2.imshow(win, disp)
        key = cv2.waitKey(20) & 0xFF

        if key == ord("r"):
            points.clear()
        elif key == ord("s"):
            if len(points) < 3:
                print("Can toi thieu 3 diem de tao thanh 1 vung.")
                continue
            zone = clicks_to_ratio(points, disp_w, disp_h)
            save_gate_zone(args.gates_file, args.gate, zone)
            print(f"Da luu vung '{args.gate}' ({len(zone)} diem, ti le 0-1) vao {args.gates_file}: {zone}")
            break
        elif key == ord("q"):
            print("Thoat, khong luu.")
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
