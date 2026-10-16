"""check(): 1 luot kiem tra tai cong tren luong camera (DE_TAI.md muc 5).

Xu ly tung khung NGAY KHI lay duoc tu CameraReader (khong gom du timeout giay
roi moi xu ly), cho den khi het timeout, roi tong hop. Dung chung FrameEvaluator
(classify_frame + aggregate) voi evaluate_frames nen 2 duong chay cho ket qua
giong nhau. Chi lay khung moi hon thoi diem goi check (khung cu co the chup
truoc khi cong nhan buoc vao). Khung nao camera ra trong luc model dang xu ly
khung truoc thi bi bo qua, chi lay khung moi nhat -> tong thoi gian ~ timeout.
Chua co dung som (DE_TAI muc 12).
"""
import time

from src.checkpoint.camera import CameraError, CameraReader
from src.checkpoint.evaluate import FrameEvaluator
from src.config import load_settings


def check(
    reader: CameraReader,
    zone,
    required_ppe: list[str] | None = None,
    config: dict | None = None,
    detector=None,
    timeout: float | None = None,
) -> dict:
    """1 luot kiem tra. reader: CameraReader da start(). zone: vung ti le 0-1 (None = ca khung,
    chi dung khi chay thu). timeout: giay; None = checkpoint.timeout_s trong cau hinh.

    Tra ve cung cac truong voi evaluate_frames. Khong nhan duoc khung nao -> CameraError
    (loi thiet bi, khong phai ket luan ve nguoi: backend bao "tam gian doan").
    """
    t0 = time.perf_counter()
    settings = config if config is not None else load_settings()
    timeout = settings["checkpoint"]["timeout_s"] if timeout is None else timeout
    evaluator = FrameEvaluator(zone, required_ppe, settings, detector)  # model da nap san (get_detector)

    deadline = t0 + timeout
    last_id = reader.latest_id  # chi xet khung moi hon luc goi check
    while True:
        remaining = deadline - time.perf_counter()
        if remaining <= 0:
            break
        got = reader.wait_new(last_id, remaining)
        if got is None:  # het gio, hoac nguon da dung/het
            break
        last_id, frame = got
        evaluator.add(frame)

    if not evaluator.results:
        raise CameraError(f"Khong nhan duoc khung hinh nao tu {reader.source.value} trong {timeout} giay")
    return evaluator.finish(t0)
