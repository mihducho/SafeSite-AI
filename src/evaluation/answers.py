"""File dap an cho danh gia Giai doan 2 (DE_TAI.md muc 10).

CSV (utf-8-sig de mo bang Excel khong loi dau): ten_file, ket_qua_dung, thieu_dung, dieu_kien, nguoi.
thieu_dung: cac ma thieu cach nhau bang ";" (vd "thieu_mu;thieu_ao"), trong khi khong thieu.
nguoi (DE_TAI.md muc 11.1, khong bat buoc): ma nguoi DANG DUOC KIEM TRA trong video (vd A, B) de danh gia nhan dien
khuon mat; dien tay. De trong (vd video khong co nguoi, hai nguoi) thi khong tinh vao ti le nhan dung nguoi.

Dap an duoc DOAN tu tien to ten file theo quy uoc trong settings.yaml (evaluation.answer_prefixes,
evaluation.condition_prefixes), roi nguoi dung kiem tra va sua tay. Tao lai file thi GIU NGUYEN cac
dong da co (khong ghi de phan da sua tay), chi them video moi.
"""
import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

from src.checkpoint.evaluate import DAT, KHONG_CO_NGUOI, KHONG_DAT, NHIEU_NGUOI

REQUIRED_COLUMNS = ["ten_file", "ket_qua_dung", "thieu_dung", "dieu_kien"]
COLUMNS = REQUIRED_COLUMNS + ["nguoi"]  # file cu chua co cot nguoi van doc duoc; ghi lai thi luon co
TRUE_RESULTS = [DAT, KHONG_DAT, NHIEU_NGUOI, KHONG_CO_NGUOI]  # dap an khong the la KHONG_XAC_DINH
SEP = ";"


@dataclass
class Answer:
    ten_file: str
    ket_qua_dung: str  # "" = chua biet (ten file khong theo quy uoc), can sua tay
    thieu_dung: list[str] = field(default_factory=list)
    dieu_kien: str = ""
    nguoi: str = ""    # ma nguoi dang duoc kiem tra (danh gia khuon mat); "" = khong xet


def _starts_with_word(text: str, prefix: str) -> bool:
    """text bat dau bang prefix, sau do het chuoi hoac la dau ngan cach / chu so (du_do_01, du_do2)."""
    return re.match(rf"{re.escape(prefix)}(?=$|[_\-\s.\d])", text) is not None


def condition_of(file_name: str) -> str:
    """Dieu kien = ten file bo so thu tu o cuoi (hai_nguoi_dungsau_02.mp4 -> hai_nguoi_dungsau), de bang
    theo dieu kien giu duoc cac bien the nguoi quay dat ten (canh nhau / dung sau...)."""
    return re.sub(r"[_\-\s]*\d+$", "", Path(file_name).stem.lower()) or Path(file_name).stem.lower()


def guess_answer(file_name: str, prefixes: dict, condition_prefixes: list[str]) -> Answer:
    """Doan dap an tu ten file. Khong khop quy uoc -> ket_qua_dung "" (can dien tay)."""
    stem = Path(file_name).stem.lower()
    rest = stem
    for cond in sorted(condition_prefixes, key=len, reverse=True):  # vd thieu_sang_ phai xet truoc thieu_mu
        if rest.startswith(cond + "_"):
            rest = rest[len(cond) + 1:]
            break
    for prefix in sorted(prefixes, key=len, reverse=True):  # tien to dai khop truoc
        if _starts_with_word(rest, prefix):
            rule = prefixes[prefix]
            return Answer(file_name, rule["ket_qua"], list(rule.get("thieu", [])), condition_of(file_name))
    return Answer(file_name, "", [], condition_of(file_name))


def list_videos(folder: str | Path, exts: list[str]) -> list[str]:
    """Ten cac file video trong thu muc (khong de quy), sap xep theo ten."""
    exts = {e.lower() for e in exts}
    return sorted(p.name for p in Path(folder).iterdir() if p.is_file() and p.suffix.lower() in exts)


def merge_answers(existing: list[Answer], guessed: list[Answer]) -> tuple[list[Answer], list[Answer]]:
    """Giu nguyen moi dong da co dap an (ke ca dong da sua tay); dong con TRONG dap an thi dien theo quy uoc
    moi (vd vua them tien to vao settings.yaml); them dong cho video moi.
    Tra ve (tat ca dong, cac dong moi them hoac vua duoc dien)."""
    by_name = {a.ten_file: a for a in guessed}
    rows, changed = [], []
    for a in existing:
        g = by_name.get(a.ten_file)
        if not a.ket_qua_dung and g is not None and g.ket_qua_dung:
            rows.append(g)
            changed.append(g)
        else:
            rows.append(a)
    known = {a.ten_file for a in existing}
    added = [a for a in guessed if a.ten_file not in known]
    return rows + added, changed + added


def write_answers(path: str | Path, answers: list[Answer]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        for a in answers:
            w.writerow([a.ten_file, a.ket_qua_dung, SEP.join(a.thieu_dung), a.dieu_kien, a.nguoi])


def read_answers(path: str | Path, missing_codes: list[str] | None = None, strict: bool = True) -> list[Answer]:
    """Doc file dap an. strict: bao loi neu ket_qua_dung / thieu_dung sai gia tri (de sua tay sai lo ra ngay).
    Dong co ket_qua_dung trong van doc duoc (script danh gia bo qua va canh bao).
    missing_codes: cac ma thieu hop le (ppe.items.*.missing_code); None = khong kiem tra."""
    path = Path(path)
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        lacking = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
        if lacking:
            raise ValueError(f"File dap an {path} thieu cot {lacking}. Can co cac cot: {REQUIRED_COLUMNS}")
        answers, errors = [], []
        for line, row in enumerate(reader, start=2):
            ket_qua = (row["ket_qua_dung"] or "").strip().upper()
            thieu = [t.strip() for t in (row["thieu_dung"] or "").split(SEP) if t.strip()]
            if ket_qua and ket_qua not in TRUE_RESULTS:
                errors.append(f"dong {line}: ket_qua_dung '{ket_qua}' khong hop le (chon 1 trong {TRUE_RESULTS})")
            if ket_qua == KHONG_DAT and not thieu:
                errors.append(f"dong {line}: KHONG_DAT can ghi thieu_dung (vd thieu_mu)")
            if ket_qua and ket_qua != KHONG_DAT and thieu:
                errors.append(f"dong {line}: {ket_qua} khong co thieu_dung, dang ghi {thieu}")
            if missing_codes is not None:
                bad = [t for t in thieu if t not in missing_codes]
                if bad:
                    errors.append(f"dong {line}: ma thieu {bad} khong hop le (chon trong {missing_codes})")
            answers.append(Answer(row["ten_file"].strip(), ket_qua, thieu, (row["dieu_kien"] or "").strip(),
                                  (row.get("nguoi") or "").strip()))
    if strict and errors:
        raise ValueError(f"File dap an {path} co loi:\n  " + "\n  ".join(errors))
    return answers
