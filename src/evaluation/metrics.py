"""Chi so danh gia Giai doan 2 (DE_TAI.md muc 10) tu ket qua tung luot (tung video). Ham thuan,
khong can model hay video, test bang du lieu gia.

Quy uoc:
- 1 luot DUNG khi ket_qua trung dap an; rieng KHONG_DAT con phai trung ca danh sach thieu.
- "Vi pham" (lop duong tinh) = KHONG_DAT. Chi xet cac luot co dap an DAT hoac KHONG_DAT:
    TP: dap an KHONG_DAT, he thong KHONG_DAT      FP: dap an DAT, he thong KHONG_DAT (chan nham)
    FN: dap an KHONG_DAT, he thong ra ket qua khac (DAT = bo lot, nguy hiem nhat; KHONG_XAC_DINH = moi quet lai)
    TN: dap an DAT, he thong khong ra KHONG_DAT
  precision = TP / (TP + FP), recall = TP / (TP + FN); mau so 0 -> None.
"""
from collections import Counter
from dataclasses import dataclass, field

from src.checkpoint.evaluate import DAT, KHONG_CO_NGUOI, KHONG_DAT, KHONG_XAC_DINH, NHIEU_NGUOI

LABELS = [DAT, KHONG_DAT, KHONG_XAC_DINH, NHIEU_NGUOI, KHONG_CO_NGUOI]


@dataclass
class RoundResult:
    ten_file: str
    dieu_kien: str
    ket_qua_dung: str
    thieu_dung: list[str]
    ket_qua: str
    thieu: list[str] = field(default_factory=list)
    thoi_gian_ms: float = 0.0

    @property
    def dung(self) -> bool:
        if self.ket_qua != self.ket_qua_dung:
            return False
        return self.ket_qua != KHONG_DAT or sorted(self.thieu) == sorted(self.thieu_dung)


def _ratio(num: int, den: int) -> float | None:
    return num / den if den else None


def confusion_matrix(rows: list[RoundResult]) -> dict[str, dict[str, int]]:
    """matrix[dap_an][ket_qua] = so luot. Hang: dap an (khong co KHONG_XAC_DINH); cot: ket qua he thong."""
    m = {t: {p: 0 for p in LABELS} for t in LABELS if t != KHONG_XAC_DINH}
    for r in rows:
        m[r.ket_qua_dung][r.ket_qua] += 1
    return m


def violation_scores(rows: list[RoundResult]) -> dict:
    """Precision/recall cho 'vi pham' (KHONG_DAT) tren cac luot co dap an DAT hoac KHONG_DAT."""
    rel = [r for r in rows if r.ket_qua_dung in (DAT, KHONG_DAT)]
    tp = sum(r.ket_qua_dung == KHONG_DAT and r.ket_qua == KHONG_DAT for r in rel)
    fp = sum(r.ket_qua_dung == DAT and r.ket_qua == KHONG_DAT for r in rel)
    fn = sum(r.ket_qua_dung == KHONG_DAT and r.ket_qua != KHONG_DAT for r in rel)
    tn = sum(r.ket_qua_dung == DAT and r.ket_qua != KHONG_DAT for r in rel)
    return {
        "so_luot_xet": len(rel), "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": _ratio(tp, tp + fp), "recall": _ratio(tp, tp + fn),
        "bo_lot": sum(r.ket_qua_dung == KHONG_DAT and r.ket_qua == DAT for r in rel),  # vi pham ma cho qua
        "vi_pham_khong_xac_dinh": sum(r.ket_qua_dung == KHONG_DAT and r.ket_qua == KHONG_XAC_DINH for r in rel),
        "sai_danh_sach_thieu": sum(r.ket_qua_dung == KHONG_DAT and r.ket_qua == KHONG_DAT and not r.dung for r in rel),
    }


def summarize(rows: list[RoundResult]) -> dict:
    n = len(rows)
    correct = sum(r.dung for r in rows)
    undecided = sum(r.ket_qua == KHONG_XAC_DINH for r in rows)
    decided = [r for r in rows if r.ket_qua != KHONG_XAC_DINH]
    return {
        "so_luot": n,
        "so_dung": correct,
        "ty_le_dung": _ratio(correct, n),
        "so_khong_xac_dinh": undecided,
        "ty_le_khong_xac_dinh": _ratio(undecided, n),
        # Bo qua cac luot he thong moi quet lai: khi da ket luan thi dung bao nhieu.
        "ty_le_dung_khi_ket_luan": _ratio(sum(r.dung for r in decided), len(decided)),
        "thoi_gian_tb_ms": sum(r.thoi_gian_ms for r in rows) / n if n else None,
        "vi_pham": violation_scores(rows),
    }


def by_condition(rows: list[RoundResult]) -> list[dict]:
    """Bang dung/sai theo dieu kien (cot dieu_kien cua file dap an), sap xep theo ten dieu kien."""
    groups: dict[str, list[RoundResult]] = {}
    for r in rows:
        groups.setdefault(r.dieu_kien or "(trong)", []).append(r)
    out = []
    for cond in sorted(groups):
        g = groups[cond]
        correct = sum(r.dung for r in g)
        out.append({
            "dieu_kien": cond, "so_luot": len(g), "dung": correct, "sai": len(g) - correct,
            "khong_xac_dinh": sum(r.ket_qua == KHONG_XAC_DINH for r in g),
            "ty_le_dung": _ratio(correct, len(g)),
            "ket_qua": dict(Counter(r.ket_qua for r in g)),
        })
    return out
