"""Ve ket qua giam sat an toan len frame: vung nguy hiem, box nguoi (xanh =
binh thuong, do = vi pham) kem nhan ly do. Chu khong dau vi cv2.putText khong
ho tro tieng Viet co dau.

Net ve va co chu tu co gian theo do phan giai frame (moc 1280px) de video
720p va 4K deu doc duoc.
"""
import cv2
import numpy as np

GREEN = (0, 200, 0)
RED = (0, 0, 255)
YELLOW = (0, 220, 255)  # vung kiem tra o cong, khong lan voi mau do cua vi pham
WHITE = (255, 255, 255)
FONT = cv2.FONT_HERSHEY_SIMPLEX
BASE_SIZE = 1280  # canh dai frame ma tai do he so = 1


def _scale(frame: np.ndarray) -> float:
    """He so phong to theo canh dai cua frame, gioi han de chu khong qua nho/qua to."""
    return min(max(max(frame.shape[:2]) / BASE_SIZE, 0.6), 4.0)


def _px(value: float, s: float) -> int:
    """Kich thuoc net/khoang cach (pixel) sau khi nhan he so, toi thieu 1."""
    return max(1, round(value * s))


def draw_zone(frame: np.ndarray, polygon: np.ndarray, alpha: float = 0.25, color: tuple = RED) -> None:
    """To mo vung (mac dinh mau do) + vien cung mau, ve truc tiep len frame."""
    s = _scale(frame)
    overlay = frame.copy()
    cv2.fillPoly(overlay, [polygon], color)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, dst=frame)
    cv2.polylines(frame, [polygon], isClosed=True, color=color, thickness=_px(2, s))


def draw_person(frame: np.ndarray, xyxy, label: str, violations: list[str]) -> None:
    """Box nguoi + nhan "#id" va cac ly do vi pham (neu co) phia tren box."""
    s = _scale(frame)
    x1, y1, x2, y2 = (int(v) for v in xyxy)
    color = RED if violations else GREEN
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, _px(2, s))
    cv2.circle(frame, ((x1 + x2) // 2, y2), _px(4, s), color, -1)  # diem chan dung kiem tra vung

    text = " | ".join([label, *violations]) if label else " | ".join(violations)
    if not text:
        return
    font_scale, thickness, pad = 0.5 * s, _px(1, s), _px(2, s)
    (tw, th), baseline = cv2.getTextSize(text, FONT, font_scale, thickness)
    ty = max(y1, th + baseline + pad)
    cv2.rectangle(frame, (x1, ty - th - baseline - pad), (x1 + tw + 2 * pad, ty), color, -1)
    cv2.putText(frame, text, (x1 + pad, ty - baseline), FONT, font_scale, WHITE, thickness, cv2.LINE_AA)


def draw_header(frame: np.ndarray, lines: list[str]) -> None:
    """Cac dong thong ke o goc tren ben trai, nen den mo de doc duoc tren moi khung hinh."""
    s = _scale(frame)
    font_scale, thickness = 0.6 * s, _px(1, s)
    line_h, margin = _px(22, s), _px(10, s)
    width = max(cv2.getTextSize(line, FONT, font_scale, thickness)[0][0] for line in lines)
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (width + 2 * margin, _px(8, s) + line_h * len(lines)), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, dst=frame)
    for i, line in enumerate(lines):
        y = line_h * (i + 1)
        cv2.putText(frame, line, (margin, y), FONT, font_scale, (0, 0, 0), _px(3, s), cv2.LINE_AA)
        cv2.putText(frame, line, (margin, y), FONT, font_scale, WHITE, thickness, cv2.LINE_AA)
