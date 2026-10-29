"""Luong doc camera rieng cho dich vu AI (DE_TAI.md muc 8).

1 thread doc lien tuc bang cv2.VideoCapture va CHI GIU KHUNG MOI NHAT (khung cu
bi ghi de, khong xep hang) de lan kiem tra nao cung dung hinh hien tai, khong
bi tre do bo dem. Model khong chay o day: check() lay khung khi co yeu cau.

Nguon hinh (parse_source):
  - so (vd "0", 0)            -> webcam
  - chuoi co "://"            -> URL camera IP tu dien thoai (http://... hoac rtsp://...)
  - con lai                   -> file video: phat DUNG TOC DO THAT (theo FPS cua
                                 video) de mo phong camera; het video thi phat lai.

Xoay hinh (camera.rotate): khung duoc xoay NGAY KHI DOC, nen moi buoc sau (vung kiem
tra, model, anh chup) deu thay hinh da dung thang.
"""
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


class CameraError(RuntimeError):
    """Khong mo duoc nguon hinh, hoac khong nhan duoc khung hinh nao."""


# Goc xoay theo chieu kim dong ho (do) -> ma cv2.rotate. Vd dien thoai dung doc ma app
# (DroidCam) van phat hinh ngang: nguoi nam ngang, dau ben trai -> xoay 90 de dung thang.
ROTATIONS = {0: None, 90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_COUNTERCLOCKWISE}


def check_rotate(degrees) -> int:
    """Goc xoay hop le (0, 90, 180, 270) -> int; goc khac thi bao ValueError."""
    if isinstance(degrees, bool) or degrees not in ROTATIONS:
        raise ValueError(f"Goc xoay hinh phai la 0, 90, 180 hoac 270 (chieu kim dong ho), nhan duoc {degrees!r}")
    return int(degrees)


def rotate_frame(frame: np.ndarray, degrees: int) -> np.ndarray:
    """Xoay khung theo chieu kim dong ho; 0 thi tra ve chinh khung do (khong sao chep)."""
    code = ROTATIONS[check_rotate(degrees)]
    return frame if code is None else cv2.rotate(frame, code)


@dataclass(frozen=True)
class Source:
    kind: str  # "webcam" | "url" | "file"
    value: int | str

    @property
    def label(self) -> str:
        """Ten ngan de dat ten file ket qua. Khong dung Path(source).stem cho webcam/URL (DE_TAI muc 8)."""
        if self.kind == "webcam":
            return f"webcam{self.value}"
        if self.kind == "url":
            return "camera_ip"
        return Path(self.value).stem


def parse_source(source) -> Source:
    if isinstance(source, int):
        return Source("webcam", source)
    s = str(source).strip()
    if s.isdigit():
        return Source("webcam", int(s))
    if "://" in s:
        return Source("url", s)
    return Source("file", s)


def open_capture(src: Source, cam_cfg: dict) -> cv2.VideoCapture:
    """Mo nguon hinh; khong mo duoc thi bao CameraError.
    URL (camera dien thoai): dat thoi gian cho khi mo / doc (camera.url_open_timeout_s, url_read_timeout_s). Khong dat thi
    FFmpeg cho mac dinh ~30 giay moi bao loi khi dien thoai khoa man hinh hoac mat wifi -> tu ket noi lai rat cham."""
    if src.kind == "file" and not Path(src.value).exists():
        raise CameraError(f"Khong tim thay file video: {src.value}")
    if src.kind == "url":
        ms = lambda key: int(cam_cfg.get(key, 5) * 1000)  # noqa: E731
        cap = cv2.VideoCapture(src.value, cv2.CAP_FFMPEG, [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, ms("url_open_timeout_s"),
                                                           cv2.CAP_PROP_READ_TIMEOUT_MSEC, ms("url_read_timeout_s")])
    else:
        cap = cv2.VideoCapture(src.value)
    if src.kind == "webcam":
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, cam_cfg["webcam_width"])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam_cfg["webcam_height"])
    if src.kind != "file":
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # it bo dem nhat co the (khong phai backend nao cung ho tro)
    if not cap.isOpened():
        cap.release()
        raise CameraError(f"Khong mo duoc nguon hinh: {src.value}")
    return cap


class CameraReader:
    """Doc nguon hinh trong 1 thread rieng, chi giu khung moi nhat.

    Cach dung:
        with CameraReader("0", settings["camera"]) as cam:
            fid, frame = cam.wait_new(after_id=0, timeout=5)
    capture_factory: thay cho open_capture (test truyen nguon gia).
    """

    def __init__(self, source, cam_cfg: dict, capture_factory=None):
        self.source = parse_source(source)
        self.cfg = cam_cfg
        self.rotate = check_rotate(cam_cfg["rotate"])  # sai goc thi bao loi ngay, truoc khi mo camera
        self._open = capture_factory or (lambda src: open_capture(src, cam_cfg))
        self._cond = threading.Condition()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._cap = None
        self._frame: np.ndarray | None = None
        self._frame_id = 0  # tang 1 moi khi co khung moi
        self._ended = False  # file video het va khong phat lai
        self.read_errors = 0  # so lan mat ket noi / doc loi (webcam, URL)
        self.source_fps = 0.0

    # --- dieu khien ---
    def start(self) -> "CameraReader":
        if self._thread is not None:  # da chay roi (vd goi start() roi lai dung `with`): khong mo them thread
            return self
        self._cap = self._open(self.source)  # loi mo nguon bao ngay, khong de trong thread
        self.source_fps = float(self._cap.get(cv2.CAP_PROP_FPS) or 0)
        self._thread = threading.Thread(target=self._run, name=f"camera-{self.source.label}", daemon=True)
        self._thread.start()
        if self.wait_new(0, self.cfg["first_frame_timeout_s"]) is None:
            self.stop()
            raise CameraError(f"Khong nhan duoc khung hinh nao tu {self.source.value} "
                              f"trong {self.cfg['first_frame_timeout_s']} giay")
        return self

    def stop(self) -> None:
        self._stop.set()
        with self._cond:
            self._cond.notify_all()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()

    # --- doc khung ---
    @property
    def latest_id(self) -> int:
        with self._cond:
            return self._frame_id

    def latest(self) -> tuple[int, np.ndarray] | None:
        with self._cond:
            return (self._frame_id, self._frame) if self._frame is not None else None

    def wait_new(self, after_id: int, timeout: float) -> tuple[int, np.ndarray] | None:
        """Cho khung co so thu tu > after_id (khung moi nhat tai luc do).
        Het thoi gian, da dung, hoac file da het thi tra ve None."""
        with self._cond:
            self._cond.wait_for(lambda: self._frame_id > after_id or self._stop.is_set() or self._ended,
                                timeout=max(timeout, 0))
            if self._frame_id > after_id:
                return self._frame_id, self._frame
            return None

    # --- thread doc ---
    def _publish(self, frame: np.ndarray) -> None:
        with self._cond:
            self._frame = frame  # ghi de khung cu: chi giu khung moi nhat
            self._frame_id += 1
            self._cond.notify_all()

    def _run(self) -> None:
        is_file = self.source.kind == "file"
        period = 1.0 / self.source_fps if is_file and self.source_fps > 0 else 0.0
        next_t = time.monotonic()
        try:
            while not self._stop.is_set():
                ok, frame = self._cap.read()
                if not ok:
                    if is_file:
                        if not self.cfg["loop_video"]:
                            break
                        self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # phat lai tu dau
                        ok, frame = self._cap.read()
                        if not ok:
                            break
                    else:
                        self._reconnect()
                        continue
                self._publish(rotate_frame(frame, self.rotate))
                if period:  # file video: giu dung toc do that
                    next_t += period
                    delay = next_t - time.monotonic()
                    if delay > 0:
                        self._stop.wait(delay)
                    elif delay < -1.0:  # cham qua nhieu (may ban): bat dau tinh lai
                        next_t = time.monotonic()
        finally:
            with self._cond:
                self._ended = True
                self._cond.notify_all()
            if self._cap is not None:
                self._cap.release()

    def _reconnect(self) -> None:
        """Webcam/URL doc loi: dong, cho reconnect_delay_s, mo lai (lap den khi duoc hoac bi dung)."""
        self.read_errors += 1
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        while not self._stop.wait(self.cfg["reconnect_delay_s"]):
            try:
                self._cap = self._open(self.source)
                return
            except CameraError:
                self.read_errors += 1
