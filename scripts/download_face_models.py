"""Tai mo hinh khuon mat YuNet (tim mat) va SFace (lay vector) cua OpenCV Zoo vao weights/face/.

Chay:  .venv\\Scripts\\python.exe scripts\\download_face_models.py          (bo qua file da co)
       .venv\\Scripts\\python.exe scripts\\download_face_models.py --force  (tai lai)

Ten file can dung lay tu configs/settings.yaml (face.detector_model, face.recognizer_model). Script tai them ban
YuNet 2026may (dau vao dong) neu co; muon dung thi doi face.detector_model. Tai xong thu nap bang OpenCV de
chac file dung. File mo hinh khong dua vao git (weights/ trong .gitignore).
"""
import argparse
import sys
import urllib.request
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import DEFAULT_SETTINGS, load_settings

ZOO = "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models"
URLS = {  # ten file -> dia chi (DE_TAI.md muc 4)
    "face_detection_yunet_2023mar.onnx": f"{ZOO}/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    "face_detection_yunet_2026may.onnx": f"{ZOO}/face_detection_yunet/face_detection_yunet_2026may.onnx",
    "face_recognition_sface_2021dec.onnx": f"{ZOO}/face_recognition_sface/face_recognition_sface_2021dec.onnx",
}
OPTIONAL = {"face_detection_yunet_2026may.onnx"}  # khong co cung khong sao


def try_load(path: Path) -> str | None:
    """Thu nap bang OpenCV; tra ve None neu duoc, nguoc lai la thong bao loi."""
    try:
        if "detection" in path.name:
            cv2.FaceDetectorYN.create(str(path), "", (320, 320), 0.7, 0.3, 5000)
        else:
            cv2.FaceRecognizerSF.create(str(path), "")
        return None
    except cv2.error as e:
        return str(e).strip().splitlines()[-1]


def download(name: str, dest: Path, force: bool) -> str:
    if dest.exists() and not force:
        return "da co"
    tmp = dest.with_suffix(".part")
    try:
        urllib.request.urlretrieve(URLS[name], tmp)
    except Exception as e:  # mang loi, 404...
        tmp.unlink(missing_ok=True)
        return f"KHONG TAI DUOC ({e})"
    tmp.replace(dest)
    return f"da tai {dest.stat().st_size / 1e6:.1f} MB"


def main():
    parser = argparse.ArgumentParser(description="Tai mo hinh YuNet + SFace vao weights/face/.")
    parser.add_argument("--force", action="store_true", help="Tai lai ca file da co.")
    parser.add_argument("--settings", default=str(DEFAULT_SETTINGS))
    args = parser.parse_args()

    face = load_settings(args.settings)["face"]
    needed = {Path(face["detector_model"]).name, Path(face["recognizer_model"]).name}
    folder = Path(face["detector_model"]).parent
    folder.mkdir(parents=True, exist_ok=True)

    failed = []
    for name in URLS:
        dest = folder / name
        status = download(name, dest, args.force)
        if dest.exists():
            err = try_load(dest)
            status += " | OpenCV nap OK" if err is None else f" | OpenCV KHONG nap duoc: {err}"
            if err and name in needed:
                failed.append(name)
        elif name in needed or name not in OPTIONAL:
            failed.append(name)
        mark = "(dang dung)" if name in needed else "(tuy chon)" if name in OPTIONAL else ""
        print(f"{name:38s} {mark:12s} {status}")
    unknown = needed - set(URLS)
    if unknown:
        print(f"Canh bao: cau hinh tro toi file khong co trong danh sach tai: {sorted(unknown)}")
    if failed:
        sys.exit(f"Loi: thieu hoac hong mo hinh can dung: {failed}")
    print(f"Xong. Mo hinh o {folder}")


if __name__ == "__main__":
    main()
