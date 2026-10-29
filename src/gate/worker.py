"""Vong lap cong (GateWorker, DE_TAI.md muc 5, 8): chay trong 1 thread rieng, dung chung CameraReader.

  CHO / CHO_ROI_DI: lay khung moi nhat, tim mat tren khung thu nho (idle_long_side), toi da idle_max_fps lan/giay,
                    dua "co mat trong vung khong" vao may trang thai (state.py).
  KIEM_TRA:         chay 1 luot (round.run_round, khoang timeout giay) roi goi on_result(ket_qua).
                    on_result tra ve True neu luot nay da ghi cong (de may trang thai biet co cho nguoi roi di khong).

Ban dong lenh (scripts/run_gate.py) va sau nay ung dung FastAPI (F2) deu dung lop nay.
"""
import threading
import time
import traceback
from pathlib import Path

from src.checkpoint.camera import CameraError
from src.face.analyze import idle_face_present
from src.face.face_detector import empty_faces
from src.gate.round import GateRound, run_round
from src.gate.state import CHO, GateState, on_idle_frame, on_round_done
from src.zone.zone import zone_to_pixels


class GateWorker:
    def __init__(self, reader, zone, settings: dict, detector, face_detector, embedder, on_result=None):
        self.reader, self.zone, self.settings = reader, zone, settings
        self.detector, self.fd, self.emb = detector, face_detector, embedder
        self.on_result = on_result
        self.state = GateState(since=time.monotonic())
        self.last_faces = empty_faces()   # mat tim duoc o khung CHO gan nhat (de hien len man hinh)
        self.last_result: dict | None = None
        self.rounds = 0
        self.error: str | None = None
        self._last_id = 0
        self._last_idle = 0.0
        self._first_seen: float | None = None  # luc bat dau thay mat (CHO) -> do "tu luc dung vao den luc co ket qua"
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def step(self) -> dict | None:
        """1 buoc o CHO / CHO_ROI_DI; neu du dieu kien thi chay luon 1 luot va tra ve ket qua, nguoc lai None."""
        gate, face = self.settings["gate"], self.settings["face"]
        wait = self._last_idle + 1.0 / gate["idle_max_fps"] - time.monotonic()  # gioi han so lan tim mat moi giay
        if wait > 0:
            self._stop.wait(wait)
        got = self.reader.wait_new(self._last_id, 1.0)
        if got is None:
            return None
        self._last_id, frame = got
        self._last_idle = time.monotonic()
        faces = self.fd.detect(frame, long_side=gate["idle_long_side"])
        self.last_faces = faces
        h, w = frame.shape[:2]
        zone_px = None if self.zone is None else zone_to_pixels(self.zone, w, h)
        present = idle_face_present(faces.rows, zone_px, w, face["min_face_px"])
        was_streak = self.state.streak if self.state.phase == CHO else 0
        self.state, start = on_idle_frame(self.state, time.monotonic(), present, gate)
        if present and was_streak == 0 and (start or self.state.phase == CHO):
            self._first_seen = self._last_idle  # khung dau tien cua chuoi co mat
        if not start:
            return None

        rnd = GateRound(self.zone, self.settings, self.detector, self.fd, self.emb)
        try:
            result = run_round(self.reader, rnd, self.settings["checkpoint"]["timeout_s"])
        except CameraError as e:
            self.error = str(e)
            self.state = GateState(CHO, since=time.monotonic())
            return None
        if self._first_seen is not None:
            result["tu_luc_thay_mat_ms"] = round((time.monotonic() - self._first_seen) * 1000)
        recorded = bool(self.on_result(result)) if self.on_result else False
        self.state = on_round_done(self.state, time.monotonic(), recorded)
        self.last_result, self.rounds, self.error = result, self.rounds + 1, None
        return result

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.step()
            except Exception as e:  # khong de thread chet im lang; man hinh cong bao "tam gian doan"
                tb = traceback.extract_tb(e.__traceback__)[-1]
                self.error = f"{type(e).__name__}: {e} ({Path(tb.filename).name}:{tb.lineno})"
                self.state = GateState(CHO, since=time.monotonic())
                self._stop.wait(1.0)

    def start(self) -> "GateWorker":
        if self._thread is None:
            self._thread = threading.Thread(target=self._loop, name="gate-worker", daemon=True)
            self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
