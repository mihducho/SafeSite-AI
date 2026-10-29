"""Ban demo dong lenh cua cong (DE_TAI.md muc 12, F1): vong lap cong + nhan dien khuon mat + kiem tra bao ho,
so khop voi file mau .npz, in ket qua va hien trong cua so OpenCV. Phong khi giao dien web (F3) chua xong.

Chay:
  .venv\\Scripts\\python.exe scripts\\run_gate.py --source 0                                       (webcam, ca khung)
  .venv\\Scripts\\python.exe scripts\\run_gate.py --source data\\raw\\cong_gia_v1\\du_do_01.mp4 --gate cong_gia_v1
  .venv\\Scripts\\python.exe scripts\\run_gate.py --source http://192.168.1.10:4747/video --gate cong_dt
Dang ky mau truoc: scripts\\enroll_from_images.py. Cua so: phim q hoac Esc de thoat.
Moi luot luu anh + JSON (KHONG co vector khuon mat, DE_TAI muc 4) vao paths.gate_runs.

Ghi cong o day chi la GIA LAP (nhan ra + DAT -> "da ghi cong"); vao/ra, ca lam, CSDL lam o F2.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.checkpoint.camera import ROTATIONS, CameraError, CameraReader
from src.checkpoint.detector import get_detector
from src.checkpoint.evaluate import DAT, KHONG_CO_NGUOI, KHONG_DAT, KHONG_XAC_DINH, NHIEU_NGUOI
from src.config import DEFAULT_SETTINGS, load_settings
from src.face.analyze import KHONG_THAY_MAT
from src.face.face_detector import face_detector_from_settings
from src.face.face_embedder import face_embedder_from_settings
from src.face.match import load_gallery, match
from src.gate.worker import GateWorker
from src.utils.visualize import GREEN, RED, YELLOW, draw_faces, draw_header, draw_zone
from src.zone.zone import choose_rotate, load_gate, zone_to_pixels

MISSING_TEXT = {"thieu_mu": "thieu mu bao ho", "thieu_ao": "thieu ao phan quang"}


def decide(result: dict, m) -> tuple[str, tuple, bool]:
    """Thong bao man hinh cong (DE_TAI muc 5 buoc 6, chu khong dau), mau, va co 'ghi cong' (gia lap) khong."""
    kq = result["ket_qua"]
    if kq == NHIEU_NGUOI:
        return "Moi tung nguoi mot", YELLOW, False
    if kq == KHONG_CO_NGUOI:
        return "Moi dung vao vi tri", YELLOW, False
    if result["khuon_mat"]["trang_thai"] == KHONG_THAY_MAT or m.ma is None:
        return "Chua nhan dien duoc, moi nhin thang camera", YELLOW, False
    if kq == KHONG_XAC_DINH:
        return f"{m.ma}: moi dung yen", YELLOW, False
    if kq == KHONG_DAT:
        return f"{m.ma}: {', '.join(MISSING_TEXT.get(t, t) for t in result['thieu'])}. Chua ghi cong", RED, False
    if kq == DAT:
        return f"Xin chao {m.ma}. Da ghi cong {time.strftime('%H:%M')} (gia lap)", GREEN, True
    return kq, YELLOW, False


def main():
    settings = load_settings()
    parser = argparse.ArgumentParser(description="Chay thu vong lap cong co nhan dien khuon mat.")
    parser.add_argument("--source", required=True, help="So webcam (0), URL camera dien thoai, hoac file video.")
    parser.add_argument("--gate", default=None, help="Ten cong trong paths.gates_file. Bo trong = ca khung.")
    parser.add_argument("--rotate", type=int, choices=sorted(ROTATIONS), default=None)
    parser.add_argument("--gallery", default=str(settings["paths"]["face_gallery"]), help="File mau .npz.")
    parser.add_argument("--no-window", action="store_true", help="Khong mo cua so (chi in ket qua).")
    parser.add_argument("--max-rounds", type=int, default=0, help="Dung sau so luot nay (0 = khong gioi han).")
    parser.add_argument("--duration", type=float, default=0, help="Dung sau so giay nay (0 = khong gioi han).")
    parser.add_argument("--settings", default=str(DEFAULT_SETTINGS))
    args = parser.parse_args()
    settings = load_settings(args.settings)
    face_cfg, gate_cfg = settings["face"], settings["gate"]

    try:
        gate = load_gate(settings["paths"]["gates_file"], args.gate) if args.gate else None
        settings["camera"]["rotate"] = choose_rotate(args.rotate, gate, settings["camera"]["rotate"])
    except (KeyError, ValueError) as e:
        sys.exit(f"Loi: {e}")
    zone = gate["zone"] if gate else None
    gallery = load_gallery(args.gallery)
    print(f"Mau khuon mat: {len(gallery)} nguoi ({', '.join(sorted(gallery)) or 'CHUA CO - chay enroll_from_images.py'})")

    t = time.perf_counter()
    detector = get_detector(settings)  # nap YOLO truoc (ultralytics dat OpenCV ve 1 luong) roi moi nap model mat
    fd, emb = face_detector_from_settings(face_cfg), face_embedder_from_settings(face_cfg)
    print(f"Nap model: {time.perf_counter() - t:.1f} s")
    out_dir = settings["paths"]["gate_runs"]
    out_dir.mkdir(parents=True, exist_ok=True)

    shown = {"text": "", "color": YELLOW, "until": 0.0}
    rounds: list[dict] = []

    def on_result(result: dict) -> bool:
        vecs = np.array(result["khuon_mat"]["vectors"]).reshape(-1, 128)
        m = match(vecs, gallery, face_cfg["match_threshold"], face_cfg["match_margin"])
        text, color, recorded = decide(result, m)
        shown.update(text=text, color=color, until=time.monotonic() + gate_cfg["result_display_seconds"])
        km, ms = result["khuon_mat"], result["ms_tb"]
        score = f"{m.ma_gan_nhat} {m.diem:.2f}" + (f", nguoi 2: {m.diem_thu_hai:.2f}" if m.diem_thu_hai is not None else "") \
            if m.diem is not None else "-"
        print(f"[Luot {len(rounds) + 1}] {result['ket_qua']}" + (f" ({result['ly_do']})" if result.get("ly_do") else "")
              + (f" thieu={result['thieu']}" if result["thieu"] else "") + f" | nhan dien: {m.ma or 'KHONG_NHAN_RA'} ({score})"
              + f" | {'DA GHI CONG (gia lap)' if recorded else 'chua ghi cong'}")
        print(f"   {result['so_khung']} khung, mat {km['so_khung_co_mat']} khung, nhieu mat {km['ty_le_khung_nhieu_mat']:.0%}"
              f" | ms/khung: bao ho {ms['bao_ho']}, YuNet {ms['yunet']}, SFace {ms['sface']} | luot {result['thoi_gian_ms']:.0f} ms"
              + (f", tu luc thay mat {result['tu_luc_thay_mat_ms']} ms" if "tu_luc_thay_mat_ms" in result else ""))
        stem = f"{time.strftime('%Y%m%d_%H%M%S')}_{len(rounds) + 1}_{result['ket_qua']}"
        (out_dir / f"{stem}.jpg").write_bytes(result.get("anh_jpeg") or b"")
        record = {k: v for k, v in result.items() if k not in ("anh_jpeg", "khuon_mat", "chi_tiet_khung")}
        record["khuon_mat"] = {k: v for k, v in km.items() if k != "vectors"}  # KHONG ghi vector ra file
        record["nhan_dien"] = {"ma": m.ma, "gan_nhat": m.ma_gan_nhat, "diem": m.diem, "diem_thu_hai": m.diem_thu_hai}
        record["thong_bao"], record["da_ghi_cong_gia_lap"] = text, recorded
        (out_dir / f"{stem}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        rounds.append(record)
        return recorded

    try:
        reader = CameraReader(args.source, settings["camera"]).start()
    except CameraError as e:
        sys.exit(f"Loi camera: {e}")
    worker = GateWorker(reader, zone, settings, detector, fd, emb, on_result=on_result).start()
    print("Dang chay. Dung vao vung kiem tra, nhin vao camera." + ("" if args.no_window else " Phim q de thoat."))
    t_start = time.monotonic()
    last_error = None
    try:
        while True:
            if worker.error != last_error:  # loi trong thread nen: in ra (man hinh cong bao "tam gian doan")
                last_error = worker.error
                if last_error:
                    print(f"Loi vong lap cong: {last_error}")
            if args.max_rounds and len(rounds) >= args.max_rounds:
                break
            if args.duration and time.monotonic() - t_start >= args.duration:
                break
            if args.no_window:
                time.sleep(0.1)
                continue
            got = reader.latest()
            if got is None:
                time.sleep(0.05)
                continue
            frame = got[1].copy()
            h, w = frame.shape[:2]
            if zone is not None:
                draw_zone(frame, zone_to_pixels(zone, w, h), color=YELLOW)
            draw_faces(frame, worker.last_faces.rows)
            lines = [f"Trang thai: {worker.state.phase}", f"So luot: {len(rounds)}"]
            if worker.error:
                lines.append("He thong kiem tra tam gian doan")
            draw_header(frame, lines)
            if time.monotonic() < shown["until"]:
                cv2.rectangle(frame, (0, h - 60), (w, h), shown["color"], -1)
                cv2.putText(frame, shown["text"], (10, h - 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2, cv2.LINE_AA)
            scale = min(1.0, 900 / h)
            cv2.imshow("SafeGate - cong (q: thoat)", cv2.resize(frame, (int(w * scale), int(h * scale))) if scale < 1 else frame)
            if cv2.waitKey(30) & 0xFF in (ord("q"), 27):
                break
    finally:
        worker.stop()
        reader.stop()
        cv2.destroyAllWindows()

    if rounds:
        def avg(key):
            vals = [r["ms_tb"][key] for r in rounds if r["ms_tb"][key] is not None]
            return f"{sum(vals) / len(vals):.0f}" if vals else "-"
        print(f"Tong {len(rounds)} luot | TB ms/khung: bao ho {avg('bao_ho')}, YuNet {avg('yunet')}, SFace {avg('sface')}"
              f" | TB luot {sum(r['thoi_gian_ms'] for r in rounds) / len(rounds):.0f} ms | anh + JSON: {out_dir}")


if __name__ == "__main__":
    main()
