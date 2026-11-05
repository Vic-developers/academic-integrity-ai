"""The browser harness must never clear production counters or other test actions."""

import importlib.util
import json
import os
from pathlib import Path
import pytest
from redis import Redis

spec = importlib.util.spec_from_file_location(
    "browser_login_limits", Path(__file__).resolve().parents[2] / "scripts/reset_browser_login_limits.py"
)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


@pytest.mark.parametrize(
    "override",
    [
        {"redis_url": "redis://localhost:56379/0"},
        {"redis_url": "redis://external.example/15"},
        {"purpose": "not-a-browser-test"},
        {"database": "academic_integrity"},
    ],
)
def test_reset_rejects_any_profile_outside_disposable_local_db15(tmp_path, monkeypatch, override):
    data = {
        "purpose": "academic-integrity-browser-test",
        "database": "aid_test",
        "redis_url": os.environ["REDIS_URL"],
        **override,
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data))

    def forbidden(*args, **kw):
        raise AssertionError("Must refuse the profile before connecting")

    monkeypatch.setattr(helper.Redis, "from_url", forbidden)
    with pytest.raises(ValueError):
        helper.reset(path)


def test_reset_only_login_counters_in_real_test_redis(tmp_path):
    assert os.environ["REDIS_URL"].endswith("/15")
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {"purpose": "academic-integrity-browser-test", "database": "aid_test", "redis_url": os.environ["REDIS_URL"]}
        )
    )
    with Redis.from_url(os.environ["REDIS_URL"]) as client:
        client.set("limit:login:ip:technical-test", "1")
        client.set("limit:login:account:technical-test", "1")
        client.set("limit:upload:ip:technical-test", "keep")
        client.set("technical:celery-sentinel", "keep")
        helper.reset(path)
        assert client.get("limit:login:ip:technical-test") is None
        assert client.get("limit:login:account:technical-test") is None
        assert client.get("limit:upload:ip:technical-test") == b"keep"
        assert client.get("technical:celery-sentinel") == b"keep"
