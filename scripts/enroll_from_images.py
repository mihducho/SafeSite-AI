"""Dang ky mau khuon mat, luu vector ra file .npz (DE_TAI.md muc 12, F1) - dung cho chay thu va danh gia khi chua
co CSDL. File .npz chua du lieu sinh trac hoc: chi de tren may, khong dua vao git (data/face/ trong .gitignore).

Che do 1 - tu thu muc anh:  <thu_muc>/<ma_nguoi>/*.jpg   (moi anh dung 1 khuon mat, ro, nhin thang)
  .venv\\Scripts\\python.exe scripts\\enroll_from_images.py --images data\\anh_dang_ky
Che do 2 - chup tu camera (webcam so 0, URL dien thoai, file video):
  .venv\\Scripts\\python.exe scripts\\enroll_from_images.py --camera 0 --code ME --count 5
  Dung truoc camera, nhin thang; moi khi lay duoc 1 mau hop le se nghi 1 giay (quay dau nhe de mau da dang).
  Chi luu anh mat da can chinh 112x112 vao paths.face_thumbs (khong luu anh goc, DE_TAI muc 7).

Ma nguoi da co trong file mau se duoc THAY bang mau moi; cac nguoi khac giu nguyen.
"""
import argparse
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.checkpoint.camera import CameraError, CameraReader
from src.config import DEFAULT_SETTINGS, load_settings
from src.face.enroll import best_samples, enroll_folder, sample_from_image, similarity_report, to_gallery
from src.face.face_detector import face_detector_from_settings
from src.face.face_embedder import face_embedder_from_settings
from src.face.match import load_gallery, save_gallery


def capture(source: str, code: str, count: int, timeout_s: float, settings: dict, fd, emb) -> dict:
    face_cfg = settings["face"]
    got, last_note, t0 = [], "", time.monotonic()
    with CameraReader(source, settings["camera"]) as cam:
        last_id = 0
        print(f"Dung truoc camera, nhin thang. Can {count} mau, toi da {timeout_s:.0f} giay...")
        while len(got) < count and time.monotonic() - t0 < timeout_s:
            item = cam.wait_new(last_id, 1.0)
            if item is None:
                continue
            last_id, frame = item
            s, why = sample_from_image(frame, fd, emb, face_cfg, "camera")
            if s is None:
                if why != last_note:
                    print(f"   chua lay duoc: {why}")
                    last_note = why
                continue
            got.append(s)
            last_note = ""
            print(f"   da lay {len(got)}/{count} mau (chat luong {s.quality:.2f})")
            time.sleep(1.0)
    return {code: got} if got else {}


def main():
    settings = load_settings()
    parser = argparse.ArgumentParser(description="Dang ky mau khuon mat -> file .npz.")
    parser.add_argument("--images", default=None, help="Thu muc <ma_nguoi>/*.jpg. Mac dinh paths.enroll_images.")
    parser.add_argument("--camera", default=None, help="Chup tu camera thay vi doc anh: so webcam, URL, file video.")
    parser.add_argument("--code", default=None, help="Ma nguoi khi chup tu camera (vd ME, A).")
    parser.add_argument("--count", type=int, default=None, help="So mau chup tu camera. Mac dinh face.min_samples + 2.")
    parser.add_argument("--timeout", type=float, default=40.0, help="Giay toi da khi chup tu camera.")
    parser.add_argument("--gallery", default=str(settings["paths"]["face_gallery"]), help="File .npz luu vector mau.")
    parser.add_argument("--no-thumbs", action="store_true", help="Khong luu anh mat 112x112.")
    parser.add_argument("--settings", default=str(DEFAULT_SETTINGS))
    args = parser.parse_args()
    settings = load_settings(args.settings)
    face_cfg = settings["face"]

    fd, emb = face_detector_from_settings(face_cfg), face_embedder_from_settings(face_cfg)
    if args.camera is not None:
        if not args.code:
            sys.exit("Che do camera can --code (ma nguoi).")
        try:
            samples = capture(args.camera, args.code, args.count or face_cfg["min_samples"] + 2, args.timeout, settings, fd, emb)
        except CameraError as e:
            sys.exit(f"Loi camera: {e}")
        notes = []
    else:
        folder = Path(args.images) if args.images else settings["paths"]["enroll_images"]
        if not folder.is_dir():
            sys.exit(f"Khong thay thu muc anh dang ky: {folder} (can co {folder}\\<ma_nguoi>\\*.jpg)")
        samples, notes = enroll_folder(folder, fd, emb, face_cfg)
    for n in notes:
        print("   " + n)
    if not samples:
        sys.exit("Khong lay duoc mau nao.")

    gallery = load_gallery(args.gallery)
    new = to_gallery(samples, face_cfg["max_samples"])
    gallery.update(new)
    save_gallery(args.gallery, gallery)
    for code, lst in samples.items():
        kept = best_samples(lst, face_cfg["max_samples"])
        warn = f"  CANH BAO: it hon {face_cfg['min_samples']} mau" if len(kept) < face_cfg["min_samples"] else ""
        print(f"{code}: {len(kept)} mau (tu {len(lst)} anh hop le){warn}")
        if not args.no_thumbs:
            out = settings["paths"]["face_thumbs"] / code
            out.mkdir(parents=True, exist_ok=True)
            for old in out.glob("*.jpg"):
                old.unlink()
            for i, s in enumerate(kept, 1):
                cv2.imencode(".jpg", s.thumb)[1].tofile(str(out / f"{code}_{i:02d}.jpg"))
    print(f"Da luu {args.gallery} ({len(gallery)} nguoi: {', '.join(sorted(gallery))})")
    for line in similarity_report(gallery):
        print("   " + line)


if __name__ == "__main__":
    main()
