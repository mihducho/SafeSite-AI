"""Danh gia khuon mat + bao ho tren bo video (DE_TAI.md muc 11.1, 11.3): moi video 1 luot cong day du.

Moi video: lay mau khung theo toc do may cua CA LUONG CONG (YOLO + YuNet + SFace) trong `timeout` giay dau,
chay GateRound (bao ho giu nguyen + khuon mat), roi so voi dap an:
  - ket qua bao ho TRUOC (chi aggregate) va SAU luat nhieu_mat, tren cung cac khung -> so sanh cong bang;
  - neu co mau khuon mat (--enroll-dir anh dang ky RIENG, hoac --gallery file .npz) va cot `nguoi` trong dap an:
    ti le nhan dung nguoi, nhan nham, khong nhan ra, nguoi la bi nhan nham; quet nguong match_threshold.

Chay:
  .venv\\Scripts\\python.exe scripts\\evaluate_faces.py --videos data\\raw\\cong_gia_v1 --answers data\\annotations\\cong_gia_v1.csv --gate cong_gia_v1
  ... --enroll-dir data\\anh_dang_ky_cong_gia_v1      (anh dang ky <ma_nguoi>/*.jpg, KHONG lay tu video test)
Dau ra trong paths.eval_runs/<thoi_gian>_khuon_mat/: ket_qua.csv, tom_tat.md, chi_tiet.jsonl (khong co vector), sai/.
"""
import argparse
import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.checkpoint.camera import ROTATIONS
from src.checkpoint.detector import get_detector
from src.config import DEFAULT_SETTINGS, ROOT, load_settings
from src.evaluation.answers import list_videos, read_answers
from src.evaluation.face_eval import FaceRound, outcome, decide_at, sweep, to_markdown
from src.evaluation.metrics import RoundResult, summarize
from src.evaluation.report import write_rounds_csv
from src.evaluation.video import measure_fps, read_sampled_frames, sample_times
from src.face.analyze import CO_MAT
from src.face.enroll import enroll_folder, to_gallery
from src.face.face_detector import face_detector_from_settings
from src.face.face_embedder import face_embedder_from_settings
from src.face.match import load_gallery, match
from src.gate.round import GateRound, evaluate_round
from src.zone.zone import choose_rotate, load_gate

COLUMNS = ["ten_file", "dieu_kien", "ket_qua_dung", "thieu_dung", "ket_qua_bao_ho", "dung_bao_ho", "ket_qua", "ly_do",
           "dung", "so_khung", "so_khung_co_mat", "so_khung_nhieu_mat", "ty_le_khung_nhieu_mat", "trang_thai_mat",
           "nguoi", "nhan_ra", "gan_nhat", "diem", "diem_thu_hai", "ket_qua_nhan_dien",
           "ms_bao_ho", "ms_yunet", "ms_sface", "thoi_gian_ms", "anh"]
SWEEP = [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60]


def show_path(p: Path) -> str:
    return str(p.relative_to(ROOT)) if Path(p).is_relative_to(ROOT) else str(p)


def main():
    parser = argparse.ArgumentParser(description="Danh gia khuon mat + bao ho tren bo video.")
    parser.add_argument("--videos", required=True)
    parser.add_argument("--answers", required=True)
    parser.add_argument("--gate", default=None)
    parser.add_argument("--rotate", type=int, choices=sorted(ROTATIONS), default=None)
    parser.add_argument("--enroll-dir", default=None, help="Thu muc anh dang ky rieng <ma_nguoi>/*.jpg.")
    parser.add_argument("--gallery", default=None, help="Hoac file mau .npz (scripts/enroll_from_images.py).")
    parser.add_argument("--fps", type=float, default=None, help="So khung/giay mo phong. Mac dinh do toc do ca luong cong.")
    parser.add_argument("--timeout", type=float, default=None)
    parser.add_argument("--out", default=None)
    parser.add_argument("--save-images", choices=["none", "wrong", "all"], default="wrong")
    parser.add_argument("--settings", default=str(DEFAULT_SETTINGS))
    args = parser.parse_args()

    settings = load_settings(args.settings)
    face_cfg, cp = settings["face"], settings["checkpoint"]
    timeout = args.timeout or cp["timeout_s"]
    videos_dir = Path(args.videos)
    try:
        gate = load_gate(settings["paths"]["gates_file"], args.gate) if args.gate else None
        rotate = choose_rotate(args.rotate, gate, settings["camera"]["rotate"])
        answers = read_answers(args.answers, [i["missing_code"] for i in settings["ppe"]["items"].values()])
    except (KeyError, ValueError) as e:
        sys.exit(f"Loi: {e}")
    zone = gate["zone"] if gate else None
    on_disk = set(list_videos(videos_dir, settings["evaluation"]["video_exts"]))
    todo = [a for a in answers if a.ket_qua_dung and a.ten_file in on_disk]
    if not todo:
        sys.exit("Khong co video nao de danh gia.")

    t = time.perf_counter()
    detector = get_detector(settings)  # nap YOLO truoc, roi moi nap model mat (xem face.opencv_threads)
    fd, emb = face_detector_from_settings(face_cfg), face_embedder_from_settings(face_cfg)
    print(f"Nap model: {time.perf_counter() - t:.1f} s")

    gallery, gallery_note = {}, "không có (chỉ đánh giá bảo hộ + đếm mặt)"
    if args.enroll_dir:
        samples, notes = enroll_folder(args.enroll_dir, fd, emb, face_cfg)
        for n in notes:
            print("   dang ky: " + n)
        gallery = to_gallery(samples, face_cfg["max_samples"])
        gallery_note = f"{len(gallery)} người từ ảnh đăng ký riêng {show_path(Path(args.enroll_dir))}"
    elif args.gallery:
        gallery = load_gallery(args.gallery)
        gallery_note = f"{len(gallery)} người từ {show_path(Path(args.gallery))}"
    enrolled = set(gallery)
    print(f"Mau khuon mat: {gallery_note}: {sorted(enrolled)}")

    fps, measured = args.fps, args.fps is None
    if measured:
        probe, _ = read_sampled_frames(videos_dir / todo[0].ten_file, 1.0, 0.5, rotate)
        rnd = GateRound(zone, settings, detector, fd, emb)
        rnd.add(probe[0])
        fps = measure_fps(rnd.add, probe[0], settings["evaluation"]["fps_probe_frames"])
    n_max = len(sample_times(fps, timeout))
    print(f"FPS mo phong (ca luong cong): {fps:.1f} khung/giay -> toi da {n_max} khung trong {timeout} s")

    out_dir = (Path(args.out) if args.out else settings["paths"]["eval_runs"]) / f"{time.strftime('%Y%m%d_%H%M%S')}_khuon_mat"
    (out_dir / "sai").mkdir(parents=True, exist_ok=True)
    if args.save_images == "all":
        (out_dir / "anh").mkdir(exist_ok=True)

    before, after, faces_rows, records, by_cond = [], [], [], [], {}
    ms = {"bao_ho": [], "yunet": [], "sface": [], "luot": []}
    with open(out_dir / "chi_tiet.jsonl", "w", encoding="utf-8") as detail:
        for i, a in enumerate(todo, 1):
            frames, info = read_sampled_frames(videos_dir / a.ten_file, fps, timeout, rotate)
            if not frames:
                print(f"[{i}/{len(todo)}] {a.ten_file}: khong doc duoc khung nao, bo qua")
                continue
            r = evaluate_round(frames, zone, settings, detector, fd, emb, record=True)
            km = r["khuon_mat"]
            b_row = RoundResult(a.ten_file, a.dieu_kien, a.ket_qua_dung, a.thieu_dung, r["ket_qua_bao_ho"], r["thieu_bao_ho"])
            a_row = RoundResult(a.ten_file, a.dieu_kien, a.ket_qua_dung, a.thieu_dung, r["ket_qua"], r["thieu"], r["thoi_gian_ms"])
            before.append(b_row)
            after.append(a_row)
            m = match(np.array(km["vectors"]).reshape(-1, 128), gallery, face_cfg["match_threshold"], face_cfg["match_margin"])
            fr = FaceRound(a.ten_file, a.nguoi, m.ma_gan_nhat, m.diem, m.diem_thu_hai)
            faces_rows.append(fr)
            res_face = outcome(a.nguoi, decide_at(fr, face_cfg["match_threshold"], face_cfg["match_margin"]), enrolled) if enrolled else None
            for k in ("bao_ho", "yunet", "sface"):
                if r["ms_tb"][k] is not None:
                    ms[k].append(r["ms_tb"][k])
            ms["luot"].append(r["thoi_gian_ms"])

            image = ""
            if (args.save_images == "wrong" and not a_row.dung) or args.save_images == "all":
                sub = "anh" if args.save_images == "all" else "sai"
                image = f"{sub}/{Path(a.ten_file).stem}__{r['ket_qua']}__{'dung' if a_row.dung else 'SAI'}.jpg"
                (out_dir / image).write_bytes(r["anh_jpeg"] or b"")
            g = by_cond.setdefault(a.dieu_kien, {"dieu_kien": a.dieu_kien, "so_luot": 0, "luot_co_mat": 0, "khung": [], "nhieu": []})
            g["so_luot"] += 1
            g["luot_co_mat"] += km["trang_thai"] == CO_MAT
            g["khung"].append(km["so_khung_co_mat"] / r["so_khung"])
            g["nhieu"].append(km["ty_le_khung_nhieu_mat"])
            records.append({
                "ten_file": a.ten_file, "dieu_kien": a.dieu_kien, "ket_qua_dung": a.ket_qua_dung,
                "thieu_dung": ";".join(a.thieu_dung), "ket_qua_bao_ho": r["ket_qua_bao_ho"], "dung_bao_ho": int(b_row.dung),
                "ket_qua": r["ket_qua"], "ly_do": r["ly_do"] or "", "dung": int(a_row.dung), "so_khung": r["so_khung"],
                "so_khung_co_mat": km["so_khung_co_mat"], "so_khung_nhieu_mat": km["so_khung_nhieu_mat"],
                "ty_le_khung_nhieu_mat": km["ty_le_khung_nhieu_mat"], "trang_thai_mat": km["trang_thai"], "nguoi": a.nguoi,
                "nhan_ra": m.ma or "", "gan_nhat": m.ma_gan_nhat or "", "diem": "" if m.diem is None else round(m.diem, 3),
                "diem_thu_hai": "" if m.diem_thu_hai is None else round(m.diem_thu_hai, 3), "ket_qua_nhan_dien": res_face or "",
                "ms_bao_ho": r["ms_tb"]["bao_ho"], "ms_yunet": r["ms_tb"]["yunet"], "ms_sface": r["ms_tb"]["sface"],
                "thoi_gian_ms": r["thoi_gian_ms"], "anh": image,
            })
            detail.write(json.dumps({"ten_file": a.ten_file, "chi_so_khung_video": info["chi_so_khung"],
                                     "chi_tiet_khung": r["chi_tiet_khung"], "chi_tiet_mat": r["chi_tiet_mat"]},
                                    ensure_ascii=False) + "\n")
            changed = "" if r["ket_qua"] == r["ket_qua_bao_ho"] else f" (bao ho: {r['ket_qua_bao_ho']})"
            who = f" | nhan ra {m.ma or '-'}" + (f" ({m.diem:.2f})" if m.diem is not None else "") if enrolled else ""
            print(f"[{i}/{len(todo)}] {a.ten_file:28s} dap an {a.ket_qua_dung:14s} -> {r['ket_qua']:14s}{changed:24s} "
                  f"{'DUNG' if a_row.dung else 'SAI '} | mat {km['so_khung_co_mat']}/{r['so_khung']}, "
                  f"nhieu mat {km['ty_le_khung_nhieu_mat']:.0%}{who}")

    write_rounds_csv(out_dir / "ket_qua.csv", records, COLUMNS)
    face_table = [{"dieu_kien": g["dieu_kien"], "so_luot": g["so_luot"], "luot_co_mat": g["luot_co_mat"],
                   "khung_co_mat_tb": statistics.mean(g["khung"]), "ty_le_nhieu_mat_tb": statistics.mean(g["nhieu"])}
                  for _, g in sorted(by_cond.items())]
    recog = None
    if enrolled and any(f.nguoi for f in faces_rows):
        thresholds = sorted(set(SWEEP) | {face_cfg["match_threshold"]})
        recog = sweep(faces_rows, thresholds, face_cfg["match_margin"], enrolled)
    med = lambda v: f"{statistics.median(v):.0f}" if v else "-"
    timing = {"Bảo hộ (YOLO + phân loại khung)": med(ms["bao_ho"]), "YuNet (tìm mặt, khung đầy đủ)": med(ms["yunet"]),
              "SFace (vector, mỗi mặt)": med(ms["sface"]), "Một lượt (mô phỏng, cả luồng)": med(ms["luot"])}
    meta = {
        "Thời điểm chạy": time.strftime("%Y-%m-%d %H:%M"),
        "Video": f"{show_path(videos_dir)}: {len(after)} video", "File đáp án": show_path(Path(args.answers)),
        "Vùng kiểm tra": f"cổng {args.gate} (xoay {rotate}°)" if gate else "cả khung hình",
        "FPS mô phỏng (cả luồng cổng)": f"{fps:.1f} khung/giây, " + ("đo trên máy" if measured else "đặt bằng tham số")
                                        + f" → tối đa {n_max} khung trong {timeout} s",
        "Mô hình mặt": f"{Path(face_cfg['detector_model']).name}, {Path(face_cfg['recognizer_model']).name}",
        "Ngưỡng mặt": f"score ≥ {face_cfg['score_threshold']}, mặt nhận dạng ≥ {face_cfg['min_face_px']} px, đếm nhiều mặt: "
                      f"≥ {face_cfg['multi_min_px']} px và ≥ {face_cfg['multi_min_ratio']} × mặt lớn nhất",
        "Mẫu khuôn mặt": gallery_note,
    }
    (out_dir / "tom_tat.md").write_text(to_markdown(meta, before, after, face_table, recog, face_cfg["match_threshold"], timing),
                                        encoding="utf-8")
    sb, sa = summarize(before), summarize(after)
    print(f"\nBao ho truoc: dung {sb['so_dung']}/{sb['so_luot']} | sau luat nhieu_mat: dung {sa['so_dung']}/{sa['so_luot']}"
          f" | ms/khung trung vi: bao ho {timing['Bảo hộ (YOLO + phân loại khung)']}, YuNet {timing['YuNet (tìm mặt, khung đầy đủ)']},"
          f" SFace {timing['SFace (vector, mỗi mặt)']}")
    print(f"Ket qua: {out_dir}")


if __name__ == "__main__":
    main()
