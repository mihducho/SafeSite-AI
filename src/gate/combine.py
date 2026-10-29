"""Ket hop ket qua bao ho va ket qua khuon mat cua 1 luot (DE_TAI.md muc 6.3).

Luat moi "nhieu_mat": neu ti le khung dem duoc >= 2 mat trong vung >= multi_person_ratio (dung chung nguong 0.5 voi
kiem tra bao ho) thi ghi de ket qua thanh NHIEU_NGUOI, ly_do = "nhieu_mat". Muc dich: bat truong hop nguoi dung sau
bi che than (YOLO chi thay 1 nguoi) nhung van thay mat.

KHONG sua evaluate_frames / aggregate: ket qua bao ho goc giu trong truong "ket_qua_bao_ho" de so sanh truoc/sau.
"""
from src.checkpoint.evaluate import NHIEU_NGUOI

FACE_KEYS = ("vectors", "chat_luong", "so_khung_co_mat", "so_khung_nhieu_mat", "ty_le_khung_nhieu_mat", "trang_thai")


def combine(ppe: dict, faces: dict, multi_person_ratio: float) -> dict:
    """ppe: ket qua kiem tra bao ho (evaluate_frames / FrameEvaluator.finish). faces: FaceAccumulator.summary().
    Tra ve dict moi: cac truong bao ho (co the bi ghi de) + ket_qua_bao_ho + khuon_mat."""
    out = dict(ppe)
    out["ket_qua_bao_ho"], out["thieu_bao_ho"] = ppe["ket_qua"], list(ppe["thieu"])  # truoc khi ap luat khuon mat
    out["khuon_mat"] = {k: faces[k] for k in FACE_KEYS}
    n = faces["so_khung"]
    if n and faces["so_khung_nhieu_mat"] / n >= multi_person_ratio and ppe["ket_qua"] != NHIEU_NGUOI:
        out.update(ket_qua=NHIEU_NGUOI, ly_do="nhieu_mat", thieu=[])
    return out
