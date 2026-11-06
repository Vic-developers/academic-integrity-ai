from fastapi import HTTPException


class AuditBodyLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if (
            scope["type"] != "http"
            or scope["method"] != "POST"
            or not (
                scope["path"] == "/api/v1/audits"
                or scope["path"].startswith("/api/v1/audits/")
                or scope["path"] == "/api/v1/bibliography"
                or scope["path"].startswith("/api/v1/bibliography/")
                or scope["path"] == "/api/v1/claims"
                or scope["path"].startswith("/api/v1/claims/")
            )
        ):
            return await self.app(scope, receive, send)
        size = 0

        async def bounded_receive():
            nonlocal size
            message = await receive()
            if message["type"] == "http.request":
                size += len(message.get("body", b""))
                if size > 65536:
                    raise HTTPException(413, "La solicitud de auditoría supera 64 KiB")
            return message

        await self.app(scope, bounded_receive, send)
