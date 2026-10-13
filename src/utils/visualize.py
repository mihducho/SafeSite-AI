"""Ve ket qua giam sat an toan len frame: vung nguy hiem, box nguoi (xanh =
binh thuong, do = vi pham) kem nhan ly do. Chu khong dau vi cv2.putText khong
ho tro tieng Viet co dau.
"""
import cv2
import numpy as np

GREEN = (0, 200, 0)
RED = (0, 0, 255)
WHITE = (255, 255, 255)


def draw_zone(frame: np.ndarray, polygon: np.ndarray, alpha: float = 0.25) -> None:
    """To mo vung nguy hiem + vien do, ve truc tiep len frame."""
    overlay = frame.copy()
    cv2.fillPoly(overlay, [polygon], RED)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, dst=frame)
    cv2.polylines(frame, [polygon], isClosed=True, color=RED, thickness=2)


def draw_person(frame: np.ndarray, xyxy, label: str, violations: list[str]) -> None:
    """Box nguoi + nhan "#id" va cac ly do vi pham (neu co) phia tren box."""
    x1, y1, x2, y2 = (int(v) for v in xyxy)
    color = RED if violations else GREEN
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    cv2.circle(frame, ((x1 + x2) // 2, y2), 4, color, -1)  # diem chan dung kiem tra vung

    text = " | ".join([label, *violations]) if label else " | ".join(violations)
    if not text:
        return
    (tw, th), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    ty = max(y1, th + baseline + 2)
    cv2.rectangle(frame, (x1, ty - th - baseline - 2), (x1 + tw + 4, ty), color, -1)
    cv2.putText(frame, text, (x1 + 2, ty - baseline), cv2.FONT_HERSHEY_SIMPLEX, 0.5, WHITE, 1, cv2.LINE_AA)


def draw_header(frame: np.ndarray, lines: list[str]) -> None:
    """Cac dong thong ke o goc tren ben trai, nen den mo de doc duoc tren moi khung hinh."""
    width = max(cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)[0][0] for line in lines)
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (width + 20, 8 + 22 * len(lines)), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, dst=frame)
    for i, line in enumerate(lines):
        y = 22 + i * 22
        cv2.putText(frame, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(frame, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, WHITE, 1, cv2.LINE_AA)
