"""Giao dien chinh (React, thu muc frontend/) o CHE DO DEMO: FastAPI phuc vu ban build frontend/dist (paths.frontend_dist),
khong can Node. Che do phat trien thi chay `npm run dev` (cong 3000, Vite chuyen /api, /ws, /stream... sang cong 8000).

- File co trong dist (vd /assets/index-abc123.js, /favicon.svg) -> tra file do. File trong /assets/ co ma bam trong ten
  nen cho trinh duyet giu lau; index.html luon tai lai (no-cache) de thay ban build moi.
- Duong dan con lai (vd /cong-nhan/5, /login) -> index.html: React tu dinh tuyen phia trinh duyet.
- KHONG che cac nhanh cua backend: /api, /ws, /stream, /docs, /openapi.json, /cu (giao dien cu), /static. Router nay
  dang ky SAU cung nen chi nhan duong dan cac router kia khong co; duong dan sai trong cac nhanh do -> 404 that.
- Chua build (khong co index.html) -> chuyen sang giao dien cu /cu/ de ung dung van dung duoc.
"""
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse

RESERVED = {"api", "ws", "stream", "docs", "openapi.json", "cu", "static"}


def frontend_router(dist: str | Path) -> APIRouter:
    dist = Path(dist).resolve()
    router = APIRouter(include_in_schema=False)

    @router.get("/{path:path}")
    def spa(path: str, request: Request):
        if path.split("/", 1)[0] in RESERVED:
            raise HTTPException(404, "Không có đường dẫn này")
        index = dist / "index.html"
        if not index.is_file():
            query = f"?{request.url.query}" if request.url.query else ""
            return RedirectResponse(("/cu/login" + query) if path == "login" else "/cu/", status_code=307)
        f = (dist / path).resolve()
        if path and f.is_file() and dist in f.parents:
            cache = "public, max-age=31536000, immutable" if path.startswith("assets/") else "no-cache"
            return FileResponse(f, headers={"Cache-Control": cache})
        return FileResponse(index, headers={"Cache-Control": "no-cache"})

    return router
