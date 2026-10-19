"""Chay thu che do cong: doc nguon hinh, chay check() 1 hoac nhieu luot, in ket qua,
luu anh JPEG + ket qua JSON vao runs/checkpoint/ (paths.checkpoint_runs).

Chay:
  .venv\\Scripts\\python.exe scripts\\run_checkpoint.py --source data\\raw\\ten_video.mp4 --gate cong_1
  .venv\\Scripts\\python.exe scripts\\run_checkpoint.py --source 0 --gate cong_1 --rounds 5          (webcam)
  .venv\\Scripts\\python.exe scripts\\run_checkpoint.py --source 0 --width 1920 --height 1080        (webcam 1080p)
  .venv\\Scripts\\python.exe scripts\\run_checkpoint.py --source http://192.168.1.23:8080/video --gate cong_1
  .venv\\Scripts\\python.exe scripts\\run_checkpoint.py --source http://192.168.1.23:4747/video --rotate 90   (dien thoai dung doc)
Khong co --gate: xet ca khung hinh (CHI de chay thu, DE_TAI muc 5).
Co --gate: hinh duoc xoay theo goc da luu cung vung cua cong (define_zone --rotate).
File JSON co them "chi_tiet_khung": moi khung 1 dong (box, lop, do tin cay, loai khung), chi so, khong co anh.
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.checkpoint.camera import ROTATIONS, CameraError, CameraReader
from src.checkpoint.check import check
from src.checkpoint.detector import get_detector
from src.config import DEFAULT_SETTINGS, load_settings
from src.zone.zone import choose_rotate, load_gate


def to_json(result: dict) -> str:
    """JSON ket qua 1 luot: thut dong cho de doc, rieng chi_tiet_khung ghi moi khung tren 1 dong."""
    data = dict(result)
    frames = data.pop("chi_tiet_khung", None)
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if frames is None:
        return text
    rows = ",\n".join("    " + json.dumps(f, ensure_ascii=False) for f in frames)
    return text[:-2] + f',\n  "chi_tiet_khung": [\n{rows}\n  ]\n}}'  # text ket thuc bang "\n}"


def main():
    parser = argparse.ArgumentParser(description="Chay thu kiem tra bao ho tai cong (check).")
    parser.add_argument("--source", required=True, help="File video, so webcam (vd 0) hoac URL camera dien thoai.")
    parser.add_argument("--gate", default=None, help="Ten cong trong paths.gates_file. Bo trong = xet ca khung.")
    parser.add_argument("--rounds", type=int, default=1, help="So luot kiem tra lien tiep (mac dinh 1).")
    parser.add_argument("--pause", type=float, default=2.0, help="Nghi giua 2 luot, giay (mac dinh 2).")
    parser.add_argument("--timeout", type=float, default=None, help="Giay moi luot; mac dinh checkpoint.timeout_s.")
    parser.add_argument("--width", type=int, default=None, help="Webcam: do phan giai ngang xin camera (ghi de cau hinh).")
    parser.add_argument("--height", type=int, default=None, help="Webcam: do phan giai doc xin camera (ghi de cau hinh).")
    parser.add_argument("--required", nargs="+", default=None, help="Mon bat buoc, vd: hardhat vest. Mac dinh ppe.required.")
    parser.add_argument("--rotate", type=int, choices=sorted(ROTATIONS), default=None,
                        help="Xoay hinh theo chieu kim dong ho (do). Mac dinh: goc luu cung vung cua --gate, "
                             "khong co --gate thi camera.rotate.")
    parser.add_argument("--settings", default=str(DEFAULT_SETTINGS))
    args = parser.parse_args()

    settings = load_settings(args.settings)
    if args.width:
        settings["camera"]["webcam_width"] = args.width
    if args.height:
        settings["camera"]["webcam_height"] = args.height
    timeout = args.timeout or settings["checkpoint"]["timeout_s"]

    gate = load_gate(settings["paths"]["gates_file"], args.gate) if args.gate else None
    zone = gate["zone"] if gate else None
    try:
        rotate = choose_rotate(args.rotate, gate, settings["camera"]["rotate"])
    except ValueError as e:
        sys.exit(f"Loi: cong '{args.gate}': {e}")
    settings["camera"]["rotate"] = rotate
    if zone is None:
        print("Canh bao: khong co --gate, xet CA KHUNG HINH (chi de chay thu).")

    t = time.perf_counter()
    detector = get_detector(settings)  # nap model truoc, khong tinh vao thoi gian moi luot
    print(f"Nap model: {(time.perf_counter() - t):.1f} s | imgsz={settings['model']['imgsz']} conf={settings['model']['conf']}")

    out_dir = Path(settings["paths"]["checkpoint_runs"])
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        reader = CameraReader(args.source, settings["camera"]).start()
    except CameraError as e:
        sys.exit(f"Loi camera: {e}")
    src = reader.source
    h, w = reader.latest()[1].shape[:2]
    fps_note = f", FPS video {reader.source_fps:.1f} (phat dung toc do that)" if src.kind == "file" else ""
    print(f"Nguon: {src.kind} {src.value} | khung {w}x{h} (xoay {rotate} do){fps_note} | timeout {timeout} s")

    stats = []
    try:
        for i in range(1, args.rounds + 1):
            id_before = reader.latest_id
            r = check(reader, zone, args.required, settings, detector, timeout, record_frames=True)
            delivered = reader.latest_id - id_before  # so khung camera dua ra trong luot nay
            jpeg = r.pop("anh_jpeg")

            stem = f"{time.strftime('%Y%m%d_%H%M%S')}_{src.label}_{args.gate or 'ca_khung'}_{i}_{r['ket_qua']}"
            (out_dir / f"{stem}.jpg").write_bytes(jpeg or b"")
            r_json = {**r, "nguon": str(src.value), "cong": args.gate, "khung_hinh": [w, h], "xoay_hinh": rotate,
                      "khung_camera_dua_ra": delivered}
            (out_dir / f"{stem}.json").write_text(to_json(r_json), encoding="utf-8")

            print(f"[Luot {i}] {r['ket_qua']}" + (f" thieu={r['thieu']}" if r["thieu"] else "")
                  + (f" ly_do={r['ly_do']}" if r["ly_do"] else ""))
            print(f"   ty_le_co_mat={r['ty_le_co_mat']} | dem_khung={r['dem_khung']}")
            print(f"   xu ly {r['so_khung']} khung (camera dua ra {delivered}) | {r['ms_moi_khung']} ms/khung"
                  f" | tong {r['thoi_gian_ms']} ms | anh: {out_dir / (stem + '.jpg')}")
            stats.append(r)
            if i < args.rounds:
                time.sleep(args.pause)
    except CameraError as e:
        print(f"Loi camera: {e}")
    finally:
        reader.stop()

    if len(stats) > 1:
        n = len(stats)
        print(f"Trung binh {n} luot: {sum(s['so_khung'] for s in stats) / n:.1f} khung/luot, "
              f"{sum(s['ms_moi_khung'] for s in stats) / n:.0f} ms/khung, "
              f"tong {sum(s['thoi_gian_ms'] for s in stats) / n:.0f} ms/luot")


if __name__ == "__main__":
    main()
