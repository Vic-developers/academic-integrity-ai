import json
import logging
import time
import uuid
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app import auth, institutions
from app.claims import api as claims
from app.experimental_ai import api as experimental_ai
from app.forensics import api as forensics
from app.bibliography import api as bibliography
from app.audits import api as audits
from app.audits.limits import AuditBodyLimitMiddleware
from app.config import settings
from app.db import engine
from app.documents import api as documents, courses
from app.documents.limits import UploadLimitMiddleware

app = FastAPI(
    title="Academic Integrity AI", version="0.1.0", docs_url=None, redoc_url=None, openapi_url="/api/openapi.json"
)
app.include_router(auth.router)
app.include_router(institutions.router)
app.include_router(documents.router)
app.include_router(courses.router)
app.include_router(audits.router)
app.include_router(bibliography.router)
app.include_router(claims.router)
app.include_router(experimental_ai.router)
app.include_router(forensics.router)
app.add_middleware(AuditBodyLimitMiddleware)
app.add_middleware(UploadLimitMiddleware)
log = logging.getLogger("uvicorn.error")


def problem(request: Request, status: int, detail: str, headers: dict | None = None) -> JSONResponse:
    return JSONResponse(
        {
            "type": "about:blank",
            "status": status,
            "detail": detail,
            "request_id": getattr(request.state, "request_id", ""),
        },
        status_code=status,
        media_type="application/problem+json",
        headers=headers,
    )


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
    return problem(request, exc.status_code, str(exc.detail), exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    return problem(request, 422, "Revisa los campos y sus límites")


@app.exception_handler(IntegrityError)
async def conflict(request: Request, exc: IntegrityError) -> JSONResponse:
    return problem(request, 409, "La operación entra en conflicto con un registro existente")


@app.middleware("http")
async def security(request: Request, call_next):
    request.state.request_id = str(uuid.uuid4())
    start = time.monotonic()
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        if (
            request.headers.get("origin") != settings().public_origin
            or request.headers.get("x-requested-with") != "AcademicIntegrityAI"
        ):
            return problem(request, 403, "Origen o cabecera de solicitud inválidos")
    try:
        response = await call_next(request)
    except Exception:
        # No exception text, bodies, SQL parameters, cookies or reset links in logs.
        log.error(json.dumps({"event": "request.failed", "request_id": request.state.request_id}))
        response = problem(request, 500, "No se pudo completar la solicitud")
    response.headers.update(
        {
            "X-Request-ID": request.state.request_id,
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "Cache-Control": "no-store",
            "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
        }
    )
    log.info(
        json.dumps(
            {
                "event": "request",
                "request_id": request.state.request_id,
                "method": request.method,
                "status": response.status_code,
                "duration_ms": round((time.monotonic() - start) * 1000),
            }
        )
    )
    return response


@app.get("/api/health/live")
def live() -> dict:
    return {"status": "ok"}


@app.get("/api/health/ready")
def ready() -> dict:
    from redis import Redis

    from redis.exceptions import RedisError

    try:
        with engine.connect() as conn:
            revision = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            if revision != "0009_forensics":
                raise HTTPException(503, "Migraciones pendientes")
        with Redis.from_url(settings().redis_url, socket_timeout=2, socket_connect_timeout=2) as redis:
            redis.ping()
    except (SQLAlchemyError, RedisError) as exc:
        raise HTTPException(503, "Dependencias temporalmente no disponibles") from exc
    return {"status": "ready"}
