"""Mot luot kiem tra tai cong = kiem tra bao ho + khuon mat tren CUNG cac khung hinh (DE_TAI.md muc 5 buoc 3, 6).

Moi khung (GateRound.add):
  1. Kiem tra bao ho: FrameEvaluator.add (detect YOLO + classify_frame) - GIU NGUYEN, khong sua logic.
  2. YuNet tren khung day du -> dem mat trong vung (luat nhieu_mat), tim mat cua nguoi dang kiem tra
     (gan vao vung dau cua nguoi trong vung lay tu ket qua buoc 1) -> SFace lay vector.
Het luot (GateRound.finish): aggregate (giu nguyen) + tong hop khuon mat -> combine (luat nhieu_mat) + anh minh chung.

Hai cach chay dung chung GateRound: run_round (camera, giong check()) va evaluate_round (danh sach khung, de danh gia
tren video va de test).
"""
import time

import cv2
import numpy as np

from src.checkpoint.camera import CameraError
from src.checkpoint.evaluate import FrameEvaluator
from src.face.analyze import FaceAccumulator, count_faces_in_zone, face_quality, main_face_index
from src.gate.combine import combine
from src.utils.visualize import draw_faces, draw_header
from src.zone.zone import zone_to_pixels


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 1) if values else None


class GateRound:
    def __init__(self, zone, settings: dict, detector, face_detector, embedder, required_ppe: list[str] | None = None,
                 record: bool = False):
        self.zone, self.settings = zone, settings
        self.face_cfg, self.ppe_cfg = settings["face"], settings["ppe"]
        self.ppe = FrameEvaluator(zone, required_ppe, settings, detector, record=record)
        self.fd, self.emb = face_detector, embedder
        self.faces = FaceAccumulator(self.face_cfg["max_vectors"])
        self.record = record
        self.face_detail: list[dict] = []
        self.ms = {"bao_ho": [], "yunet": [], "sface": []}  # thoi gian moi buoc (ms) de bao cao
        self._snap: tuple[np.ndarray, int | None] | None = None  # mat tren khung duoc chon lam anh minh chung

    def add(self, frame: np.ndarray):
        t0 = time.perf_counter()
        r = self.ppe.add(frame)  # bao ho: YOLO + classify_frame
        t1 = time.perf_counter()
        faces = self.fd.detect(frame)
        t2 = time.perf_counter()
        self.ms["bao_ho"].append((t1 - t0) * 1000)
        self.ms["yunet"].append((t2 - t1) * 1000)

        h, w = frame.shape[:2]
        zone_px = None if self.zone is None else zone_to_pixels(self.zone, w, h)
        fc = self.face_cfg
        n_zone = count_faces_in_zone(faces.rows, zone_px, w, fc["multi_min_px"], fc["multi_min_ratio"])
        idx = main_face_index(faces.rows, r.zone_persons, self.ppe_cfg, fc["min_face_px"])
        vector, quality = None, 0.0
        if idx is not None:
            t3 = time.perf_counter()
            vector = self.emb.embed(frame, faces.rows[idx])
            self.ms["sface"].append((time.perf_counter() - t3) * 1000)
            quality = face_quality(faces.rows[idx, 14], faces.rows[idx, 2], fc["quality_full_width_px"])
        self.faces.add(n_zone, vector, quality)

        if self.ppe.picker.frame is frame:  # khung nay dang duoc chon lam anh minh chung -> nho mat cua no
            self._snap = (faces.rows, idx)
        if self.record:
            self.face_detail.append({"so_mat": len(faces), "so_mat_trong_vung": n_zone, "mat_chinh": idx is not None,
                                     "rong_mat": [round(float(x)) for x in faces.widths]})
        return r, faces, idx

    def finish(self, t0: float) -> dict:
        ppe = self.ppe.finish(t0)
        out = combine(ppe, self.faces.summary(), self.settings["checkpoint"]["multi_person_ratio"])
        out["thoi_gian_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        out["ms_tb"] = {k: _mean(v) for k, v in self.ms.items()}
        out["anh_jpeg"] = self._annotate(ppe["anh_jpeg"], out)
        if self.record:
            out["chi_tiet_mat"] = self.face_detail
        return out

    def _annotate(self, jpeg: bytes | None, out: dict) -> bytes | None:
        """Anh minh chung: anh bao ho (vung + khung nguoi) + khung mat + dong ket qua."""
        if not jpeg:
            return jpeg
        img = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
        if self._snap is not None:
            draw_faces(img, *self._snap)
        line = out["ket_qua"] + (f" ({out['ly_do']})" if out.get("ly_do") else "")
        if out.get("thieu"):
            line += " thieu: " + ", ".join(out["thieu"])
        km = out["khuon_mat"]
        draw_header(img, [line, f"mat: {km['so_khung_co_mat']}/{out['so_khung']} khung, "
                                f"nhieu mat {km['ty_le_khung_nhieu_mat']:.0%}"])
        ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, int(self.settings["checkpoint"]["snapshot_jpeg_quality"])])
        return buf.tobytes() if ok else jpeg


def run_round(reader, rnd: GateRound, timeout: float) -> dict:
    """1 luot tren camera (giong check()): xu ly tung khung MOI NHAT ngay khi lay duoc cho den het timeout.
    Chi xet khung moi hon luc goi. Khong nhan duoc khung nao -> CameraError."""
    t0 = time.perf_counter()
    deadline = t0 + timeout
    last_id = reader.latest_id
    while (remaining := deadline - time.perf_counter()) > 0:
        got = reader.wait_new(last_id, remaining)
        if got is None:
            break
        last_id, frame = got
        rnd.add(frame)
    if rnd.faces.frames == 0:
        raise CameraError(f"Khong nhan duoc khung hinh nao trong {timeout} giay")
    return rnd.finish(t0)


def evaluate_round(frames: list[np.ndarray], zone, settings: dict, detector, face_detector, embedder,
                   required_ppe: list[str] | None = None, record: bool = False) -> dict:
    """1 luot tren danh sach khung co san (danh gia tren video, test)."""
    t0 = time.perf_counter()
    rnd = GateRound(zone, settings, detector, face_detector, embedder, required_ppe, record)
    for frame in frames:
        rnd.add(frame)
    return rnd.finish(t0)
