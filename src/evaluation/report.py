"""Xuat ket qua danh gia Giai doan 2: CSV tung luot va file tom tat Markdown (dung cho bao cao)."""
import csv
from pathlib import Path

from src.evaluation.metrics import LABELS, RoundResult, by_condition, confusion_matrix, summarize

def round_columns(ppe_names: list[str]) -> list[str]:
    """Cot cua CSV tung luot; ty_le_<mon> cho tung mon bao ho bat buoc (vd ty_le_hardhat)."""
    return (["ten_file", "dieu_kien", "ket_qua_dung", "thieu_dung", "ket_qua", "thieu", "dung", "ly_do",
             "so_khung", "so_khung_hop_le", "trong", "nhieu_nguoi", "qua_nho", "cat_dau"]
            + [f"ty_le_{n}" for n in ppe_names]
            + ["thoi_gian_ms", "ms_moi_khung", "video_fps", "khung_hinh", "anh_sai"])


def write_rounds_csv(path: str | Path, records: list[dict], columns: list[str]) -> None:
    """records: moi phan tu la 1 dict theo columns (thieu khoa thi de trong)."""
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        for rec in records:
            w.writerow(rec)


def _pct(x: float | None) -> str:
    return "–" if x is None else f"{x * 100:.1f}%"


def _frac(num: int, den: int) -> str:
    return f"{num}/{den} ({_pct(num / den if den else None)})"


def to_markdown(rows: list[RoundResult], meta: dict, wrong: list[dict]) -> str:
    """meta: cau hinh lan chay (thu tu giu nguyen). wrong: cac luot sai (ten_file, dap an, ket qua, ly do, anh)."""
    s = summarize(rows)
    v = s["vi_pham"]
    lines = ["# Kết quả đánh giá kiểm tra bảo hộ tại cổng", "", "## Cấu hình", ""]
    lines += [f"- **{k}:** {val}" for k, val in meta.items()]

    lines += ["", "## Kết quả chung", "",
              "| Chỉ số | Giá trị |", "|---|---|",
              f"| Số lượt (video) | {s['so_luot']} |",
              f"| Tỷ lệ đúng | {_frac(s['so_dung'], s['so_luot'])} |",
              f"| Tỷ lệ đúng khi hệ thống đã kết luận (bỏ KHONG_XAC_DINH) | {_pct(s['ty_le_dung_khi_ket_luan'])} |",
              f"| Tỷ lệ KHONG_XAC_DINH (mời quét lại) | {_frac(s['so_khong_xac_dinh'], s['so_luot'])} |",
              "| Thời gian trung bình mỗi lượt | " + ("–" if s["thoi_gian_tb_ms"] is None else f"{s['thoi_gian_tb_ms']:.0f} ms") + " |"]

    lines += ["", "## Phát hiện vi phạm (KHONG_DAT là dương tính)", "",
              f"Xét {v['so_luot_xet']} lượt có đáp án DAT hoặc KHONG_DAT.", "",
              "| Chỉ số | Giá trị |", "|---|---|",
              f"| Precision (báo vi phạm thì đúng là vi phạm) | {_pct(v['precision'])} |",
              f"| Recall (vi phạm bị phát hiện) | {_pct(v['recall'])} |",
              f"| TP / FP / FN / TN | {v['tp']} / {v['fp']} / {v['fn']} / {v['tn']} |",
              f"| Bỏ lọt: vi phạm nhưng ra DAT | {v['bo_lot']} |",
              f"| Vi phạm nhưng ra KHONG_XAC_DINH (mời quét lại) | {v['vi_pham_khong_xac_dinh']} |",
              f"| Phát hiện vi phạm nhưng sai danh sách thiếu | {v['sai_danh_sach_thieu']} |"]

    m = confusion_matrix(rows)
    lines += ["", "## Ma trận nhầm lẫn", "", "Hàng: đáp án; cột: kết quả hệ thống.", "",
              "| Đáp án \\ Kết quả | " + " | ".join(LABELS) + " |",
              "|---|" + "---|" * len(LABELS)]
    lines += [f"| {t} | " + " | ".join(str(m[t][p]) for p in LABELS) + " |" for t in m]

    lines += ["", "## Theo điều kiện", "",
              "| Điều kiện | Số lượt | Đúng | Sai | KHONG_XAC_DINH | Tỷ lệ đúng | Kết quả hệ thống |",
              "|---|---|---|---|---|---|---|"]
    for c in by_condition(rows):
        res = ", ".join(f"{k} {n}" for k, n in sorted(c["ket_qua"].items()))
        lines.append(f"| {c['dieu_kien']} | {c['so_luot']} | {c['dung']} | {c['sai']} | {c['khong_xac_dinh']} | "
                     f"{_pct(c['ty_le_dung'])} | {res} |")

    lines += ["", f"## Các lượt sai ({len(wrong)})", ""]
    if wrong:
        lines += ["| Video | Điều kiện | Đáp án | Kết quả | Đếm khung | Ảnh |", "|---|---|---|---|---|---|"]
        lines += [f"| {w['ten_file']} | {w['dieu_kien']} | {w['dap_an']} | {w['ket_qua']} | {w['dem_khung']} | {w['anh']} |"
                  for w in wrong]
    else:
        lines.append("Không có lượt sai.")
    return "\n".join(lines) + "\n"
