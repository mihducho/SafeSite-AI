"""Danh gia Giai doan 2 (DE_TAI.md muc 10): moi video la 1 luot kiem tra tai cong.

Moi video: lay mau khung theo FPS xu ly cua may (mo phong check() chay that) trong `timeout` giay
tinh tu dau video, goi evaluate_frames voi vung kiem tra chi dinh, so voi file dap an.

Chay (tao dap an truoc bang scripts\\make_answers.py, kiem tra va sua tay):
  .venv\\Scripts\\python.exe scripts\\evaluate_videos.py --videos E:\\video_cong --gate cong_video
  .venv\\Scripts\\python.exe scripts\\evaluate_videos.py --videos E:\\video_cong --gate cong_video --imgsz 960
Ve vung cho video: scripts\\define_zone.py --source E:\\video_cong\\du_do_01.mp4 --gate cong_video

Dau ra trong paths.eval_runs/<thoi_gian>_imgsz<N>/:
  ket_qua.csv          1 dong / video (dap an, ket qua, dem khung, ti le co mat, thoi gian)
  tom_tat.md           ti le dung, ma tran nham lan, precision/recall "vi pham", ti le KHONG_XAC_DINH,
                       thoi gian TB moi luot, bang theo dieu kien, danh sach luot sai
  chi_tiet_khung.jsonl box tung khung cua tung video (chi so, khong co anh) de tim nguyen nhan luot sai
  sai/                 anh cac luot sai (co ve khung nhan dien)
  anh/                 (--save-images all) anh moi luot, ten <video>__<ket qua>__<dung|SAI>.jpg
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.checkpoint.camera import ROTATIONS
from src.checkpoint.detector import get_detector
from src.checkpoint.evaluate import FrameEvaluator, evaluate_frames
from src.config import DEFAULT_SETTINGS, ROOT, load_settings
from src.evaluation.answers import list_videos, read_answers
from src.evaluation.metrics import RoundResult, summarize
from src.evaluation.report import round_columns, to_markdown, write_rounds_csv
from src.evaluation.video import measure_fps, read_sampled_frames, sample_times
from src.zone.zone import choose_rotate, load_gate


def show_path(p: Path) -> str:
    p = Path(p)
    return str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)


def main():
    parser = argparse.ArgumentParser(description="Danh gia kiem tra bao ho tai cong tren thu muc video (Giai doan 2).")
    parser.add_argument("--videos", default=None, help="Thu muc video. Mac dinh paths.eval_videos.")
    parser.add_argument("--answers", default=None,
                        help="File dap an CSV. Mac dinh: dap_an.csv trong thu muc --videos, hoac paths.eval_answers.")
    parser.add_argument("--gate", default=None, help="Ten cong trong paths.gates_file (vung + goc xoay). Bo trong = ca khung.")
    parser.add_argument("--rotate", type=int, choices=sorted(ROTATIONS), default=None,
                        help="Xoay hinh (do). Mac dinh: goc luu cung vung cua --gate, khong co --gate thi camera.rotate.")
    parser.add_argument("--imgsz", type=int, choices=[640, 960], default=None, help="Kich thuoc anh vao model. Mac dinh model.imgsz.")
    parser.add_argument("--fps", type=float, default=None,
                        help="So khung/giay mo phong. Mac dinh evaluation.sample_fps, null thi do tren may.")
    parser.add_argument("--timeout", type=float, default=None, help="Giay moi luot. Mac dinh checkpoint.timeout_s.")
    parser.add_argument("--out", default=None, help="Thu muc ket qua. Mac dinh paths.eval_runs.")
    parser.add_argument("--save-images", choices=["wrong", "all"], default="wrong",
                        help="wrong: chi luu anh luot sai (sai/); all: luu them anh moi luot vao anh/ (vd lam bao cao).")
    parser.add_argument("--settings", default=str(DEFAULT_SETTINGS))
    args = parser.parse_args()

    settings = load_settings(args.settings)
    ev_cfg, cp = settings["evaluation"], settings["checkpoint"]
    if args.imgsz:
        settings["model"]["imgsz"] = args.imgsz
    imgsz = settings["model"]["imgsz"]
    timeout = args.timeout or cp["timeout_s"]
    videos_dir = Path(args.videos) if args.videos else settings["paths"]["eval_videos"]
    answers_path = Path(args.answers) if args.answers else (
        videos_dir / "dap_an.csv" if args.videos else settings["paths"]["eval_answers"])

    try:
        gate = load_gate(settings["paths"]["gates_file"], args.gate) if args.gate else None
    except KeyError as e:
        sys.exit(f"Loi: {e.args[0]}\nVe vung truoc: .venv\\Scripts\\python.exe scripts\\define_zone.py "
                 f"--source <1 video trong {videos_dir}> --gate {args.gate}  (bam s de luu)")
    zone = gate["zone"] if gate else None
    try:
        rotate = choose_rotate(args.rotate, gate, settings["camera"]["rotate"])
    except ValueError as e:
        sys.exit(f"Loi: cong '{args.gate}': {e}")
    if zone is None:
        print("Canh bao: khong co --gate, xet CA KHUNG HINH.")

    # --- dap an + danh sach video ---
    if not answers_path.exists():
        sys.exit(f"Khong co file dap an {answers_path}. Tao bang: scripts\\make_answers.py --videos {videos_dir}")
    missing_codes = [item["missing_code"] for item in settings["ppe"]["items"].values()]
    try:
        answers = read_answers(answers_path, missing_codes)
    except ValueError as e:
        sys.exit(str(e))
    on_disk = set(list_videos(videos_dir, ev_cfg["video_exts"]))
    todo = [a for a in answers if a.ket_qua_dung and a.ten_file in on_disk]
    skipped = {"chua co dap an": [a.ten_file for a in answers if not a.ket_qua_dung],
               "khong thay file video": [a.ten_file for a in answers if a.ket_qua_dung and a.ten_file not in on_disk],
               "chua co trong file dap an": sorted(on_disk - {a.ten_file for a in answers})}
    for why, names in skipped.items():
        if names:
            print(f"Bo qua {len(names)} video ({why}): {names}")
    if not todo:
        sys.exit("Khong co video nao de danh gia.")

    # --- model + toc do may ---
    t = time.perf_counter()
    detector = get_detector(settings)
    print(f"Nap model: {time.perf_counter() - t:.1f} s | imgsz={imgsz} conf={settings['model']['conf']}")
    fps = args.fps or ev_cfg["sample_fps"]
    fps_source = "tham so --fps" if args.fps else "cau hinh evaluation.sample_fps"
    measured = not fps
    if measured:
        probe, _ = read_sampled_frames(videos_dir / todo[0].ten_file, 1.0, 0.5, rotate)
        evaluator = FrameEvaluator(zone, None, settings, detector)
        evaluator.add(probe[0])  # lan dau o kich thuoc khung moi cham hon, khong tinh
        fps = measure_fps(evaluator.add, probe[0], ev_cfg["fps_probe_frames"])
        fps_source = f"do tren may nay ({ev_cfg['fps_probe_frames']} khung cua {todo[0].ten_file})"
    n_max = len(sample_times(fps, timeout))
    print(f"FPS mo phong: {fps:.1f} khung/giay ({fps_source}) -> toi da {n_max} khung trong {timeout} s moi luot")

    out_dir = Path(args.out) if args.out else settings["paths"]["eval_runs"]
    out_dir = out_dir / f"{time.strftime('%Y%m%d_%H%M%S')}_imgsz{imgsz}"
    wrong_dir = out_dir / "sai"
    wrong_dir.mkdir(parents=True, exist_ok=True)
    all_dir = out_dir / "anh"
    if args.save_images == "all":
        all_dir.mkdir(exist_ok=True)
    required = list(settings["ppe"]["required"])

    rows, records, wrong = [], [], []
    with open(out_dir / "chi_tiet_khung.jsonl", "w", encoding="utf-8") as detail_file:
        for i, a in enumerate(todo, 1):
            frames, info = read_sampled_frames(videos_dir / a.ten_file, fps, timeout, rotate)
            if not frames:
                print(f"[{i}/{len(todo)}] {a.ten_file}: khong doc duoc khung nao, bo qua")
                continue
            r = evaluate_frames(frames, zone, None, settings, detector, record_frames=True)
            row = RoundResult(a.ten_file, a.dieu_kien, a.ket_qua_dung, a.thieu_dung, r["ket_qua"], r["thieu"], r["thoi_gian_ms"])
            rows.append(row)

            if args.save_images == "all":
                mark = "dung" if row.dung else "SAI"
                (all_dir / f"{Path(a.ten_file).stem}__{r['ket_qua']}__{mark}.jpg").write_bytes(r["anh_jpeg"] or b"")
            image = ""
            if not row.dung:
                image = wrong_dir / f"{Path(a.ten_file).stem}__{r['ket_qua']}__dap_an_{a.ket_qua_dung}.jpg"
                image.write_bytes(r["anh_jpeg"] or b"")
                dem = ", ".join(f"{k} {v}" for k, v in r["dem_khung"].items() if v)
                wrong.append({"ten_file": a.ten_file, "dieu_kien": a.dieu_kien,
                              "dap_an": " ".join([a.ket_qua_dung] + a.thieu_dung),
                              "ket_qua": " ".join([r["ket_qua"]] + r["thieu"]), "dem_khung": dem,
                              "anh": f"sai/{image.name}"})
            records.append({
                "ten_file": a.ten_file, "dieu_kien": a.dieu_kien, "ket_qua_dung": a.ket_qua_dung,
                "thieu_dung": ";".join(a.thieu_dung), "ket_qua": r["ket_qua"], "thieu": ";".join(r["thieu"]),
                "dung": int(row.dung), "ly_do": r["ly_do"] or "", "so_khung": r["so_khung"],
                "so_khung_hop_le": r["so_khung_hop_le"], **{k: r["dem_khung"][k] for k in ("trong", "nhieu_nguoi", "qua_nho", "cat_dau")},
                **{f"ty_le_{n}": r["ty_le_co_mat"].get(n, "") for n in required},
                "thoi_gian_ms": r["thoi_gian_ms"], "ms_moi_khung": r["ms_moi_khung"], "video_fps": info["video_fps"],
                "khung_hinh": "x".join(map(str, info["khung_hinh"])), "anh_sai": image.name if image else "",
            })
            detail_file.write(json.dumps({"ten_file": a.ten_file, "ket_qua": r["ket_qua"], "chi_so_khung_video": info["chi_so_khung"],
                                          "chi_tiet_khung": r["chi_tiet_khung"]}, ensure_ascii=False) + "\n")
            note = " (video ngan hon timeout)" if info["video_ngan_hon_timeout"] else ""
            print(f"[{i}/{len(todo)}] {a.ten_file:40s} dap an {a.ket_qua_dung:14s} -> {r['ket_qua']:14s} "
                  f"{'DUNG' if row.dung else 'SAI '} | {r['so_khung']} khung, {r['thoi_gian_ms']:.0f} ms{note}")

    if not rows:
        sys.exit("Khong danh gia duoc video nao (khong doc duoc khung hinh).")
    write_rounds_csv(out_dir / "ket_qua.csv", records, round_columns(required))
    meta = {
        "Thời điểm chạy": time.strftime("%Y-%m-%d %H:%M"),
        "Model": show_path(settings["model"]["weights"]),
        "imgsz": imgsz,
        "conf / iou": f"{settings['model']['conf']} / {settings['model']['iou']}",
        "Thời gian mỗi lượt (timeout)": f"{timeout} s",
        "FPS mô phỏng": f"{fps:.1f} khung/giây, " + ("đo tốc độ xử lý trên máy chạy đánh giá" if measured
                                                    else "đặt bằng tham số"),
        "Số khung tối đa mỗi lượt": n_max,
        "Vùng kiểm tra": f"cổng {args.gate} (xoay {rotate}°)" if gate else f"cả khung hình (xoay {rotate}°)",
        "Video": f"{show_path(videos_dir)}: {len(rows)} video được đánh giá"
                 + (f", bỏ qua {sum(map(len, skipped.values()))}" if any(skipped.values()) else ""),
        "File đáp án": show_path(answers_path),
        "Ngưỡng": f"present_ratio {cp['present_ratio']}, absent_ratio {cp['absent_ratio']}, "
                  f"min_valid_frames {cp['min_valid_frames']}, multi_person_ratio {cp['multi_person_ratio']}",
    }
    (out_dir / "tom_tat.md").write_text(to_markdown(rows, meta, wrong), encoding="utf-8")

    s = summarize(rows)
    v = s["vi_pham"]
    pct = lambda x: "-" if x is None else f"{x * 100:.1f}%"
    print(f"\nDung {s['so_dung']}/{s['so_luot']} ({pct(s['ty_le_dung'])}) | KHONG_XAC_DINH {pct(s['ty_le_khong_xac_dinh'])}"
          f" | vi pham: precision {pct(v['precision'])}, recall {pct(v['recall'])}, bo lot {v['bo_lot']}"
          f" | TB {s['thoi_gian_tb_ms']:.0f} ms/luot")
    print(f"Ket qua: {out_dir}")


if __name__ == "__main__":
    main()
