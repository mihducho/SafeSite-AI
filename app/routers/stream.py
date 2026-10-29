"""Luong hinh truc tiep /stream/gate (DE_TAI.md muc 8): MJPEG (multipart/x-mixed-replace) - trinh duyet hien bang
the <img src="/stream/gate">. Khoang gate.stream_fps khung/giay; ve vung kiem tra, dang kiem tra thi ve them khung
nguoi va khung mat. Camera chua chay -> anh bao trang thai. Can dang nhap."""
import asyncio

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from app.auth import current_user

router = APIRouter(dependencies=[Depends(current_user)], tags=["cong"])
BOUNDARY = "frame"


def mjpeg_part(jpeg: bytes) -> bytes:
    return (f"--{BOUNDARY}\r\nContent-Type: image/jpeg\r\nContent-Length: {len(jpeg)}\r\n\r\n").encode() + jpeg + b"\r\n"


@router.get("/stream/gate")
async def stream_gate(request: Request, so_khung: int = Query(0, ge=0, description="0 = phát mãi (dùng để thử)")):
    gate = request.app.state.gate
    period = 1.0 / request.app.state.settings["gate"]["stream_fps"]
    stopping = request.app.state.shutting_down

    async def frames():
        sent = 0
        while (not so_khung or sent < so_khung) and not stopping.is_set():  # ung dung dang tat -> dung
            if await request.is_disconnected():
                break
            jpeg = await run_in_threadpool(gate.render_frame)  # ve + nen JPEG ngoai event loop
            yield mjpeg_part(jpeg)
            sent += 1
            await asyncio.sleep(period)

    return StreamingResponse(frames(), media_type=f"multipart/x-mixed-replace; boundary={BOUNDARY}",
                             headers={"Cache-Control": "no-store"})
