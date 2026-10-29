"""May trang thai cua cong (DE_TAI.md muc 5): CHO -> KIEM_TRA -> CHO_ROI_DI -> CHO.

Viet thanh HAM THUAN: nhan trang thai cu, thoi diem hien tai (giay) va "co mat trong vung khong", tra ve trang thai
moi. Khong doc camera, khong doc dong ho -> test duoc tung tinh huong bang cach truyen thoi gian gia.

- CHO: moi khung tim mat (khung thu nho). Co mat du lon trong vung lien tiep trigger_frames khung -> bat dau luot.
- KIEM_TRA: chay 1 luot (khoang timeout giay, xem round.py). Xong goi on_round_done(..., recorded).
- CHO_ROI_DI: chua bat dau luot moi cho toi khi da qua cooldown_seconds VA
      (vung da trong lien tuc empty_seconds  HOAC  luot truoc KHONG ghi cong).
  Nho vay nguoi khong dat co the chinh lai mu, ao roi duoc kiem tra lai ngay tai cho; nguoi da ghi cong khong bi ghi lap.
"""
from dataclasses import dataclass, replace

CHO = "CHO"
KIEM_TRA = "KIEM_TRA"
CHO_ROI_DI = "CHO_ROI_DI"


@dataclass(frozen=True)
class GateState:
    phase: str = CHO
    streak: int = 0                   # CHO: so khung lien tiep co mat trong vung
    since: float = 0.0                # thoi diem vao trang thai hien tai
    empty_since: float | None = None  # CHO_ROI_DI: vung bat dau trong tu luc nao (None = dang co mat)
    recorded: bool = False            # luot truoc da ghi cong chua


def on_idle_frame(state: GateState, now: float, face_present: bool, cfg: dict) -> tuple[GateState, bool]:
    """Goi voi moi khung o CHO / CHO_ROI_DI. Tra ve (trang thai moi, co bat dau luot kiem tra khong).
    cfg: muc gate trong settings (trigger_frames, cooldown_seconds, empty_seconds)."""
    if state.phase == KIEM_TRA:
        raise ValueError("Dang KIEM_TRA: ket thuc luot bang on_round_done()")
    if state.phase == CHO_ROI_DI:
        empty_since = None if face_present else (state.empty_since if state.empty_since is not None else now)
        cooled = now - state.since >= cfg["cooldown_seconds"]
        left = empty_since is not None and now - empty_since >= cfg["empty_seconds"]
        if not (cooled and (left or not state.recorded)):
            return replace(state, empty_since=empty_since), False
        state = GateState(CHO, 0, now)  # het cho; xet luon khung nay o CHO
    streak = state.streak + 1 if face_present else 0
    if streak >= cfg["trigger_frames"]:
        return GateState(KIEM_TRA, 0, now), True
    return replace(state, streak=streak), False


def on_round_done(state: GateState, now: float, recorded: bool) -> GateState:
    """Ket thuc luot: sang CHO_ROI_DI. recorded: luot nay da ghi cong (vao/ra) chua."""
    return GateState(CHO_ROI_DI, 0, now, None, recorded)
