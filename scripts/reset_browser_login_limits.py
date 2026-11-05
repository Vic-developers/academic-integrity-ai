"""Isolate browser login cases in the explicitly disposable local Redis DB 15 only."""

import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

from redis import Redis
from redis.exceptions import RedisError


def reset(config_path):
    config = json.loads(Path(config_path).read_text())
    profile = urlsplit(config["redis_url"])
    if (
        config.get("purpose") != "academic-integrity-browser-test"
        or config.get("database") != "aid_test"
        or profile.scheme not in {"redis", "rediss"}
        or profile.hostname not in {"localhost", "127.0.0.1", "::1"}
        or profile.path != "/15"
    ):
        raise ValueError("Dedicated local test Redis profile required")
    with Redis.from_url(
        config["redis_url"], socket_timeout=2, socket_connect_timeout=2
    ) as client:
        # Do not touch Celery, application data, or rate limits of other actions.
        for pattern in ["limit:login:ip:*", "limit:login:account:*"]:
            keys = list(client.scan_iter(match=pattern, count=100))
            if keys:
                client.delete(*keys)


if __name__ == "__main__":
    try:
        reset(sys.argv[1])
    except (OSError, ValueError, KeyError, IndexError, RedisError):
        print("No se pudieron aislar los contadores de login del perfil de pruebas")
        raise SystemExit(1) from None
