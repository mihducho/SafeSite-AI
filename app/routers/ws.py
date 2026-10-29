"""WebSocket /ws/events (DE_TAI.md muc 8): moi luot kiem tra xong -> 1 su kien {"loai": "luot", ...};
trang thai cong doi (khoi dong, loi, CHO/KIEM_TRA) -> {"loai": "trang_thai", ...}. Can dang nhap (cookie phien)."""
import asyncio

from fastapi import APIRouter, WebSocket

from app.auth import session_user

router = APIRouter()


def status_event(gate) -> dict:
    return {"loai": "trang_thai", **gate.status()}


@router.websocket("/ws/events")
async def events_ws(websocket: WebSocket):
    state = websocket.app.state
    with state.db.session() as db:
        user = session_user(websocket.session, db)
    if user is None:
        await websocket.close(code=1008, reason="Chua dang nhap")  # 1008: vi pham chinh sach
        return
    await websocket.accept()
    q = state.events.subscribe()

    async def send_events():
        await websocket.send_json(status_event(state.gate))  # trang thai hien tai ngay khi ket noi
        while True:
            await websocket.send_json(await q.get())

    async def wait_close():  # trinh duyet dong tab -> receive bao WebSocketDisconnect
        while True:
            await websocket.receive_text()

    tasks = [asyncio.create_task(send_events()), asyncio.create_task(wait_close())]
    try:
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for t in done:
            t.exception()  # doc loi cua task da xong (thuong la WebSocketDisconnect) de asyncio khong canh bao
    finally:
        for t in tasks:
            t.cancel()
        state.events.unsubscribe(q)


async def watch_gate_status(gate, events, interval: float = 0.2) -> None:
    """Chay nen trong event loop: trang thai cong doi thi phat su kien (man hinh cong hien 'tam gian doan')."""
    last = None
    while True:
        st = gate.status()
        key = (st["trang_thai"], st["loi"], st["pha"])
        if key != last:
            last = key
            await events.publish({"loai": "trang_thai", **st})
        await asyncio.sleep(interval)
