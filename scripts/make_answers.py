"""Tao file dap an CSV cho danh gia Giai doan 2 tu ten file video, de kiem tra va sua tay.

Chay:
  .venv\\Scripts\\python.exe scripts\\make_answers.py                                   (thu muc paths.eval_videos)
  .venv\\Scripts\\python.exe scripts\\make_answers.py --videos E:\\video_cong          (dap_an.csv dat trong thu muc do)

Dap an doan tu tien to ten file theo quy uoc trong settings.yaml (evaluation.answer_prefixes):
  du_do, mu_trang, ao_cam -> DAT | thieu_mu, non_la, mu_luoi_trai -> KHONG_DAT thieu_mu
  thieu_ao -> KHONG_DAT thieu_ao | thieu_ca_hai -> KHONG_DAT thieu_mu;thieu_ao
  hai_nguoi -> NHIEU_NGUOI | trong -> KHONG_CO_NGUOI
  nguoc_sang_*, thieu_sang_* -> theo phan duoi (vd nguoc_sang_du_do -> DAT)
File da co thi GIU NGUYEN cac dong cu (ke ca dong da sua tay), chi them video moi.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import DEFAULT_SETTINGS, load_settings
from src.evaluation.answers import guess_answer, list_videos, merge_answers, read_answers, write_answers


def main():
    parser = argparse.ArgumentParser(description="Tao file dap an CSV tu ten file video (Giai doan 2).")
    parser.add_argument("--videos", default=None, help="Thu muc video. Mac dinh paths.eval_videos.")
    parser.add_argument("--answers", default=None,
                        help="File CSV dap an. Mac dinh: dap_an.csv trong thu muc --videos, hoac paths.eval_answers.")
    parser.add_argument("--settings", default=str(DEFAULT_SETTINGS))
    args = parser.parse_args()

    settings = load_settings(args.settings)
    ev = settings["evaluation"]
    videos_dir = Path(args.videos) if args.videos else settings["paths"]["eval_videos"]
    answers_path = Path(args.answers) if args.answers else (
        videos_dir / "dap_an.csv" if args.videos else settings["paths"]["eval_answers"])
    if not videos_dir.is_dir():
        sys.exit(f"Khong tim thay thu muc video: {videos_dir}")

    names = list_videos(videos_dir, ev["video_exts"])
    if not names:
        sys.exit(f"Thu muc {videos_dir} khong co video ({', '.join(ev['video_exts'])})")
    guessed = [guess_answer(n, ev["answer_prefixes"], ev["condition_prefixes"]) for n in names]
    existing = read_answers(answers_path, strict=False)  # dang sua do dang van doc duoc de giu lai
    rows, added = merge_answers(existing, guessed)
    write_answers(answers_path, rows)

    print(f"{len(names)} video trong {videos_dir}")
    print(f"File dap an: {answers_path} ({len(existing)} dong cu, them hoac dien moi {len(added)} dong; "
          f"dong da co dap an giu nguyen)")
    for a in added:
        thieu = ";".join(a.thieu_dung)
        print(f"   + {a.ten_file:40s} {a.ket_qua_dung or '???':15s} {thieu:20s} {a.dieu_kien}")
    unknown = [a.ten_file for a in rows if not a.ket_qua_dung]
    if unknown:
        print(f"Canh bao: {len(unknown)} video khong theo quy uoc ten, can dien tay ket_qua_dung: {unknown}")
    gone = sorted({a.ten_file for a in existing} - set(names))
    if gone:
        print(f"Canh bao: {len(gone)} dong trong file dap an khong con video tuong ung: {gone}")
    print("Mo file bang Excel hoac VS Code de kiem tra, sua tay neu doan sai.")


if __name__ == "__main__":
    main()
