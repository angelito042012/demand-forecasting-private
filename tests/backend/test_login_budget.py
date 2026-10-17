"""T10 §1: presupuesto de login con reserva atomica; rafagas concurrentes reales (hilos y Uvicorn real)."""
from __future__ import annotations

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from backend.app.auth import budget
from tests.backend.test_proxy_headers_chain import ORIGIN, PASSWORD, _serve, mongo_db  # noqa: F401  (fixture)

pytestmark = pytest.mark.mongo


@pytest.fixture
def db():
    client = MongoClient(os.environ.get("MONGODB_URI", "mongodb://127.0.0.1:27017"), serverSelectionTimeoutMS=1500)
    try:
        client.admin.command("ping")
    except PyMongoError:
        client.close()
        pytest.skip("MongoDB no disponible")
    name = f"df_test_{uuid.uuid4().hex[:12]}"
    yield client[name]
    client.drop_database(name)
    client.close()


def test_burst_of_threads_never_gets_more_slots_than_the_limit(db):
    for _ in range(3):
        key = uuid.uuid4().hex
        with ThreadPoolExecutor(max_workers=48) as pool:
            res = list(pool.map(lambda _i, k=key: budget.reserve(db, k, 5, 900), range(120)))
        assert sum(r.allowed for r in res) == 5                      # exactamente el limite, sin carreras
        assert db[budget.COLLECTION].find_one({"_id": key})["count"] == 5   # el contador queda acotado
        assert all(r.retry_after >= 1 for r in res if not r.allowed)


def test_window_resets_and_keys_are_independent_with_controlled_clock(db):
    t0 = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)
    assert [budget.reserve(db, "a", 2, 60, t0).allowed for _ in range(3)] == [True, True, False]
    assert budget.reserve(db, "b", 2, 60, t0).allowed                       # otra clave no se ve afectada
    denied = budget.reserve(db, "a", 2, 60, t0 + timedelta(seconds=30))
    assert not denied.allowed and denied.retry_after == 30
    assert budget.reserve(db, "a", 2, 60, t0 + timedelta(seconds=61)).allowed   # ventana vencida: reinicia


def test_refund_returns_slot_and_never_goes_negative(db):
    budget.reserve(db, "k", 2, 900)
    budget.reserve(db, "k", 2, 900)
    budget.refund(db, "k")
    assert budget.reserve(db, "k", 2, 900).allowed
    budget.refund(db, "k", reset=True)
    assert db[budget.COLLECTION].count_documents({"_id": "k"}) == 0
    budget.refund(db, "inexistente")
    assert db[budget.COLLECTION].count_documents({}) == 0


def test_real_http_burst_validates_at_most_the_allowed_attempts(mongo_db):  # noqa: F811
    proc, url = _serve(mongo_db, "--no-proxy-headers")
    try:
        def attempt(_i):
            with httpx.Client(base_url=url, timeout=30) as c:
                return c.post("/api/v1/auth/login", json={"username": "usuario_prueba", "password": "incorrecta-xxx"},
                              headers={"Origin": ORIGIN}).status_code
        with ThreadPoolExecutor(max_workers=24) as pool:
            codes = list(pool.map(attempt, range(60)))
        assert codes.count(401) == 5 and codes.count(429) == 55, (codes.count(401), codes.count(429))
        with httpx.Client(base_url=url, timeout=30) as c:       # y la clave correcta tampoco entra durante el bloqueo
            assert c.post("/api/v1/auth/login", json={"username": "usuario_prueba", "password": PASSWORD},
                          headers={"Origin": ORIGIN}).status_code == 429
        doc_dump = str(list(MongoClient(os.environ.get("MONGODB_URI", "mongodb://127.0.0.1:27017"))[mongo_db]
                            [budget.COLLECTION].find()))
        assert "usuario_prueba" not in doc_dump and "127.0.0.1" not in doc_dump
    finally:
        proc.kill()


def test_correct_login_in_burst_with_wrong_ones_still_caps_wrong_guesses(mongo_db):  # noqa: F811
    proc, url = _serve(mongo_db, "--no-proxy-headers")
    try:
        def attempt(i):
            pw = PASSWORD if i % 10 == 0 else "incorrecta-xxx"
            with httpx.Client(base_url=url, timeout=30) as c:
                return pw == PASSWORD, c.post("/api/v1/auth/login", json={"username": "usuario_prueba", "password": pw},
                                              headers={"Origin": ORIGIN}).status_code
        with ThreadPoolExecutor(max_workers=24) as pool:
            res = list(pool.map(attempt, range(60)))
        wrong_evaluated = sum(1 for good, code in res if not good and code == 401)
        assert wrong_evaluated <= 5                      # nunca mas de 5 adivinanzas evaluadas por ventana
    finally:
        proc.kill()
