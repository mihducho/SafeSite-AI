"""Menu demo bao cao tien do: chon so thay vi go lenh dai.

Chay (tu thu muc goc du an):  .\\demo      (hoac bam dup file demo.bat)
Cau hinh (thu muc video, dap an, vung, FPS, danh sach video) o muc `demo` trong configs/settings.yaml.
Menu chi goi lai cac script co san (evaluate_videos.py, run_checkpoint.py), khong co logic rieng.
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import DEFAULT_SETTINGS, load_settings, project_path


def find_video(folder: Path, name: str, exts: list[str]) -> Path:
    """File video theo ten (khong can duoi file, khong phan biet hoa thuong), tra ve dung ten that tren o dia."""
    exts = {e.lower() for e in exts}
    for p in sorted(folder.iterdir()) if folder.is_dir() else []:
        if p.is_file() and p.stem.lower() == name.lower() and p.suffix.lower() in exts:
            return p
    raise FileNotFoundError(f"Khong thay video '{name}' trong {folder}")


def eval_command(demo: dict) -> list[str]:
    return [sys.executable, str(ROOT / "scripts" / "evaluate_videos.py"),
            "--videos", str(project_path(demo["videos_dir"])), "--answers", str(project_path(demo["answers"])),
            "--gate", demo["gate"], "--imgsz", str(demo["imgsz"]), "--fps", str(demo["sample_fps"]),
            "--save-images", "all"]


def video_command(demo: dict, video: Path) -> list[str]:
    return [sys.executable, str(ROOT / "scripts" / "run_checkpoint.py"),
            "--source", str(video), "--gate", demo["gate"], "--rounds", "1"]


def newest(folder: Path, pattern: str) -> Path | None:
    items = list(Path(folder).glob(pattern)) if Path(folder).exists() else []
    return max(items, key=lambda p: p.stat().st_mtime) if items else None


def open_path(path: Path, in_vscode: bool = False) -> None:
    """Mo file/thu muc: file Markdown mo trong VS Code (neu co lenh `code`), con lai mo bang ung dung mac dinh."""
    print(f"   Mo: {path}")
    code = shutil.which("code") if in_vscode else None
    if code:
        subprocess.run([code, str(path)], check=False)
    else:
        os.startfile(str(path))  # Windows


def main():
    parser = argparse.ArgumentParser(description="Menu demo bao cao tien do.")
    parser.add_argument("--settings", default=str(DEFAULT_SETTINGS))
    parser.add_argument("--no-open", action="store_true", help="Khong tu mo anh/file sau khi chay (de kiem tra).")
    args = parser.parse_args()
    settings = load_settings(args.settings)
    demo, exts = settings["demo"], settings["evaluation"]["video_exts"]
    videos_dir = project_path(demo["videos_dir"])
    show = (lambda p, vs=False: None) if args.no_open else open_path

    while True:
        print("\n================= DEMO SAFESITE-AI =================")
        print("  1. Danh gia ca bo video (khoang 2 phut)")
        for i, v in enumerate(demo["videos"], start=2):
            print(f"  {i}. Chay video {v['name']:24s} ({v['note']})")
        k = len(demo["videos"]) + 2
        print(f"  {k}. Chay video khac (go ten video)")
        print(f"  {k + 1}. Mo thu muc anh minh hoa")
        print(f"  {k + 2}. Mo tai lieu ket qua danh gia")
        print("  0. Thoat")
        choice = input("Chon so roi bam Enter: ").strip()

        try:
            if choice == "0" or choice == "":
                break
            if choice == "1":
                subprocess.run(eval_command(demo), check=False)
                out = newest(settings["paths"]["eval_runs"], "*_imgsz*")
                if out:
                    print(f"\nBang ket qua: {out / 'tom_tat.md'}  (trong VS Code bam Ctrl+Shift+V de xem dang bang)")
                    show(out / "tom_tat.md", True)
            elif choice.isdigit() and 2 <= int(choice) < k or choice == str(k):
                name = demo["videos"][int(choice) - 2]["name"] if choice != str(k) else input("Ten video (vd thieu_mu_01): ").strip()
                subprocess.run(video_command(demo, find_video(videos_dir, name, exts)), check=False)
                image = newest(settings["paths"]["checkpoint_runs"], "*.jpg")
                if image:
                    show(image)
            elif choice == str(k + 1):
                show(project_path(demo["images_dir"]))
            elif choice == str(k + 2):
                show(project_path(demo["report"]), True)
            else:
                print("Khong co lua chon nay.")
        except FileNotFoundError as e:
            print(f"Loi: {e}")


if __name__ == "__main__":
    main()
