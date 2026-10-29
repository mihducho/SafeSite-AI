"""Phat su kien toi cac WebSocket dang ket noi (/ws/events, DE_TAI.md muc 8).

Moi trinh duyet ket noi co 1 hang doi (asyncio.Queue). FastAPI chay trong 1 event loop (asyncio), con GateWorker chay
trong thread nen: thread khong duoc dung truc tiep vao hang doi cua event loop, nen publish_threadsafe() gui coroutine
publish() sang event loop bang asyncio.run_coroutine_threadsafe (loop lay luc ung dung khoi dong).
"""
import asyncio


class Broadcaster:
    def __init__(self, queue_size: int = 100):
        self.queue_size = queue_size
        self.loop: asyncio.AbstractEventLoop | None = None
        self._queues: set[asyncio.Queue] = set()

    def bind(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=self.queue_size)
        self._queues.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._queues.discard(q)

    @property
    def clients(self) -> int:
        return len(self._queues)

    async def publish(self, event: dict) -> None:
        """Chay trong event loop. Trinh duyet doc cham, hang doi day -> bo su kien cu nhat."""
        for q in list(self._queues):
            if q.full():
                q.get_nowait()
            q.put_nowait(event)

    def publish_threadsafe(self, event: dict):
        """Goi tu thread khac (GateWorker). Tra ve Future (test cho duoc), loop chua chay thi bo qua."""
        if self.loop is None or self.loop.is_closed():
            return None
        return asyncio.run_coroutine_threadsafe(self.publish(event), self.loop)
