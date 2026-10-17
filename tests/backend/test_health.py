import pytest
from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.main import create_app


class _OkClient:
    def __init__(self, *args, **kwargs):
        self.admin = self

    def command(self, name):
        assert name == "ping"
        return {"ok": 1}

    def close(self):
        pass


def test_health_reports_ok_when_database_answers(monkeypatch):
    monkeypatch.setattr("backend.app.main.MongoClient", _OkClient)
    body = TestClient(create_app()).get("/api/v1/health").json()
    assert body["status"] == "ok" and body["database"] == "ok"
    assert body["timezone"] == "America/Lima"
    assert "mongodb" not in str(body).lower()


@pytest.mark.mongo
def test_health_with_real_local_mongo_is_ok():
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError
    probe = MongoClient(Settings().mongodb_uri, serverSelectionTimeoutMS=1500)
    try:
        probe.admin.command("ping")
    except PyMongoError:
        pytest.skip("MongoDB local no disponible")
    finally:
        probe.close()
    body = TestClient(create_app()).get("/api/v1/health").json()
    assert body["status"] == "ok" and body["database"] == "ok"


def test_health_degraded_when_mongo_unreachable(monkeypatch):
    monkeypatch.setattr(
        "backend.app.main.get_settings",
        lambda: Settings(mongodb_uri="mongodb://127.0.0.1:1"),
    )
    body = TestClient(create_app()).get("/api/v1/health").json()
    assert body["status"] == "degraded" and body["database"] == "unavailable"


def test_cors_only_allows_configured_origin():
    client = TestClient(create_app())
    ok = client.options("/api/v1/health", headers={"Origin": "http://localhost:4200", "Access-Control-Request-Method": "GET"})
    bad = client.options("/api/v1/health", headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "GET"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:4200"
    assert "access-control-allow-origin" not in bad.headers
