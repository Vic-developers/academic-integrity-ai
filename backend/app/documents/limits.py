from fastapi import HTTPException
from app.config import settings


class UploadLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"] != "/api/v1/documents" or scope["method"] != "POST":
            return await self.app(scope, receive, send)
        consumed = 0

        async def bounded_receive():
            nonlocal consumed
            message = await receive()
            if message["type"] == "http.request":
                consumed += len(message.get("body", b""))
                if consumed > settings().max_request_bytes:
                    raise HTTPException(413, "El lote supera el límite total de carga")
            return message

        await self.app(scope, bounded_receive, send)
