import hashlib
import secrets
from datetime import datetime, timezone
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import HTTPException, Request
from redis import Redis
from redis.exceptions import RedisError
from app.config import settings

hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(32))


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def now() -> datetime:
    return datetime.now(timezone.utc)


def verify(encoded: str, password: str) -> bool:
    try:
        return hasher.verify(encoded, password)
    except (VerificationError, InvalidHashError):
        return False


def rate_limit(request: Request, action: str, identity: str = "", maximum: int = 10) -> None:
    # Never trust caller-supplied forwarding headers. Uvicorn proxy headers disabled.
    ip = request.client.host if request.client else "unknown"
    keys = [f"limit:{action}:ip:{digest(ip)}"]
    if identity:
        keys.append(f"limit:{action}:account:{digest(identity)}")
    script = "local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],900) end; return n"
    try:
        with Redis.from_url(settings().redis_url, socket_timeout=2, socket_connect_timeout=2) as client:
            counts = [client.eval(script, 1, key) for key in keys]
    except RedisError as exc:
        raise HTTPException(503, "Control de acceso temporalmente no disponible") from exc
    if any(int(n) > maximum for n in counts):
        raise HTTPException(429, "Demasiados intentos; espera 15 minutos", headers={"Retry-After": "900"})
