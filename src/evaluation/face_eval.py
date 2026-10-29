"""Chi so danh gia khuon mat (DE_TAI.md muc 11): ket qua nhan dien tung video, quet nguong, bao cao Markdown.
Ham thuan, test bang du lieu gia.

Ket qua nhan dien 1 video (outcome), so voi cot `nguoi` cua file dap an:
  dung              nguoi da dang ky, nhan ra dung nguoi
  nham              nguoi da dang ky, nhan ra thanh NGUOI KHAC (loi nguy hiem: cham cong ho)
  khong_nhan_ra     nguoi da dang ky, he thong khong nhan ra (moi nhin thang camera, khong ghi cong)
  la_tu_choi_dung   nguoi CHUA dang ky, he thong khong nhan ra (dung)
  la_bi_nhan_nham   nguoi CHUA dang ky bi nhan thanh cong nhan (phai bang 0 o nguong da chon)
  None              cot nguoi de trong -> khong xet
"""
from collections import Counter
from dataclasses import dataclass

from src.evaluation.metrics import RoundResult, by_condition, summarize
from src.evaluation.report import _frac, _pct

OUTCOMES = ["dung", "nham", "khong_nhan_ra", "la_tu_choi_dung", "la_bi_nhan_nham"]


@dataclass
class FaceRound:
    ten_file: str
    nguoi: str                 # dap an ("" = khong xet)
    gan_nhat: str | None       # nguoi giong nhat (chua xet nguong)
    diem: float | None         # diem nguoi giong nhat
    diem_thu_hai: float | None


def decide_at(r: FaceRound, threshold: float, margin: float) -> str | None:
    """Ma nhan ra o nguong cho truoc (giong match.py), None = khong nhan ra."""
    if r.diem is None or r.diem < threshold:
        return None
    if r.diem_thu_hai is not None and r.diem - r.diem_thu_hai < margin:
        return None
    return r.gan_nhat


def outcome(nguoi: str, nhan_ra: str | None, enrolled: set[str]) -> str | None:
    if not nguoi:
        return None
    if nguoi in enrolled:
        return "dung" if nhan_ra == nguoi else ("khong_nhan_ra" if nhan_ra is None else "nham")
    return "la_tu_choi_dung" if nhan_ra is None else "la_bi_nhan_nham"


def recognition_counts(rows: list[FaceRound], threshold: float, margin: float, enrolled: set[str]) -> dict:
    c = Counter(outcome(r.nguoi, decide_at(r, threshold, margin), enrolled) for r in rows)
    known = c["dung"] + c["nham"] + c["khong_nhan_ra"]
    strangers = c["la_tu_choi_dung"] + c["la_bi_nhan_nham"]
    return {"nguong": threshold, **{k: c[k] for k in OUTCOMES}, "so_luot_nguoi_da_dang_ky": known,
            "so_luot_nguoi_la": strangers, "ty_le_dung": c["dung"] / known if known else None}


def sweep(rows: list[FaceRound], thresholds: list[float], margin: float, enrolled: set[str]) -> list[dict]:
    return [recognition_counts(rows, t, margin, enrolled) for t in thresholds]


def ppe_changes(before: list[RoundResult], after: list[RoundResult]) -> list[dict]:
    """Cac video doi ket qua sau khi them luat nhieu_mat, kem dung/sai truoc va sau."""
    out = []
    for b, a in zip(before, after):
        if b.ket_qua != a.ket_qua or b.thieu != a.thieu:
            out.append({"ten_file": b.ten_file, "dieu_kien": b.dieu_kien, "dap_an": b.ket_qua_dung,
                        "truoc": b.ket_qua, "sau": a.ket_qua, "dung_truoc": b.dung, "dung_sau": a.dung})
    return out


def to_markdown(meta: dict, before: list[RoundResult], after: list[RoundResult], face_table: list[dict],
                recog: list[dict] | None, chosen: float, timing: dict) -> str:
    sb, sa = summarize(before), summarize(after)
    vb, va = sb["vi_pham"], sa["vi_pham"]
    lines = ["# Đánh giá khuôn mặt + bảo hộ trên bộ video (DE_TAI.md mục 11.1)", "", "## Cấu hình", ""]
    lines += [f"- **{k}:** {v}" for k, v in meta.items()]
    lines += ["", "## Kết quả bảo hộ trước và sau luật `nhieu_mat`", "",
              "Cùng các khung hình của mỗi video: *trước* = chỉ kiểm tra bảo hộ (`aggregate`, giữ nguyên); "
              "*sau* = thêm luật đếm khuôn mặt (≥ 50% số khung có ≥ 2 mặt trong vùng → NHIEU_NGUOI).", "",
              "| Chỉ số | Trước | Sau |", "|---|---|---|",
              f"| Tỷ lệ đúng | {_frac(sb['so_dung'], sb['so_luot'])} | {_frac(sa['so_dung'], sa['so_luot'])} |",
              f"| KHONG_XAC_DINH | {_frac(sb['so_khong_xac_dinh'], sb['so_luot'])} | {_frac(sa['so_khong_xac_dinh'], sa['so_luot'])} |",
              f"| Precision vi phạm | {_pct(vb['precision'])} | {_pct(va['precision'])} |",
              f"| Recall vi phạm | {_pct(vb['recall'])} | {_pct(va['recall'])} |",
              f"| Bỏ lọt (vi phạm ra DAT) | {vb['bo_lot']} | {va['bo_lot']} |"]
    changes = ppe_changes(before, after)
    lines += ["", f"**Video đổi kết quả ({len(changes)}):**", ""]
    if changes:
        lines += ["| Video | Điều kiện | Đáp án | Trước | Sau | Đúng trước → sau |", "|---|---|---|---|---|---|"]
        lines += [f"| {c['ten_file']} | {c['dieu_kien']} | {c['dap_an']} | {c['truoc']} | {c['sau']} | "
                  f"{'đúng' if c['dung_truoc'] else 'sai'} → {'đúng' if c['dung_sau'] else 'sai'} |" for c in changes]
    else:
        lines.append("Không có.")
    cb = {c["dieu_kien"]: c for c in by_condition(before)}
    lines += ["", "**Theo điều kiện (đúng / số lượt):**", "", "| Điều kiện | Trước | Sau | Kết quả sau |", "|---|---|---|---|"]
    for c in by_condition(after):
        res = ", ".join(f"{k} {n}" for k, n in sorted(c["ket_qua"].items()))
        lines.append(f"| {c['dieu_kien']} | {cb[c['dieu_kien']]['dung']}/{c['so_luot']} | {c['dung']}/{c['so_luot']} | {res} |")

    lines += ["", "## Khuôn mặt theo điều kiện", "",
              "| Điều kiện | Số lượt | Lượt có mặt người kiểm tra | Khung có mặt (TB) | Tỷ lệ khung ≥ 2 mặt (TB) |",
              "|---|---|---|---|---|"]
    lines += [f"| {f['dieu_kien']} | {f['so_luot']} | {f['luot_co_mat']}/{f['so_luot']} | {f['khung_co_mat_tb']:.0%} | "
              f"{f['ty_le_nhieu_mat_tb']:.0%} |" for f in face_table]

    lines += ["", "## Nhận diện người", ""]
    if not recog:
        lines.append("Chưa chạy: cần ảnh đăng ký riêng (`--enroll-dir`) hoặc file mẫu (`--gallery`), và cột `nguoi` "
                     "trong file đáp án.")
    else:
        main = next((r for r in recog if abs(r["nguong"] - chosen) < 1e-9), recog[0])
        lines += [f"Ngưỡng đang dùng `match_threshold` = {chosen}.", "",
                  "| Kết quả | Số lượt |", "|---|---|",
                  f"| Nhận đúng người | {main['dung']}/{main['so_luot_nguoi_da_dang_ky']} ({_pct(main['ty_le_dung'])}) |",
                  f"| Nhận nhầm sang người khác | {main['nham']} |", f"| Không nhận ra | {main['khong_nhan_ra']} |",
                  f"| Người lạ bị nhận nhầm thành công nhân | {main['la_bi_nhan_nham']}/{main['so_luot_nguoi_la']} |",
                  "", "**Quét ngưỡng:**", "", "| Ngưỡng | Đúng | Nhầm | Không nhận ra | Người lạ bị nhận nhầm |", "|---|---|---|---|---|"]
        lines += [f"| {r['nguong']:.2f} | {r['dung']} | {r['nham']} | {r['khong_nhan_ra']} | {r['la_bi_nhan_nham']} |" for r in recog]

    lines += ["", "## Thời gian xử lý (trung vị mỗi khung)", "", "| Bước | ms |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in timing.items()]
    return "\n".join(lines) + "\n"
