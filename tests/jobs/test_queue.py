"""T10 §2: cola durable: idempotencia, reclamo atomico, lease/fencing, reintentos acotados."""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest

from pipeline.jobs import queue as q
from tests.publish.helpers import temp_db

pytestmark = pytest.mark.mongo
T0 = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)


def new(db, key="k", **kw):
    return q.enqueue(db, "generate_run", {"origin": "2026-07-10", "secreto_interno": "/ruta/privada"}, key, "admin",
                     public={"origin": "2026-07-10"}, now=T0, **kw)


def test_enqueue_is_idempotent_and_rejects_unknown_types():
    with temp_db() as db:
        q.ensure_indexes(db)
        a, created = new(db)
        b, created2 = new(db)
        assert created and not created2 and a["job_id"] == b["job_id"] and db.jobs.count_documents({}) == 1
        with pytest.raises(ValueError):
            q.enqueue(db, "ejecutar_comando", {}, "x", "admin")
        assert new(db, "k2")[0]["job_id"] != a["job_id"]


def test_atomic_claim_many_threads_one_winner_per_job():
    with temp_db() as db:
        q.ensure_indexes(db)
        for i in range(5):
            new(db, f"k{i}")
        with ThreadPoolExecutor(max_workers=16) as pool:
            res = list(pool.map(lambda i: q.claim(db, f"w{i}", now=T0), range(40)))
        got = [c for c in res if c is not None]
        assert len(got) == 5 and len({c.job_id for c in got}) == 5                # cada trabajo lo gano un solo worker
        assert all(c.generation == 1 and c.attempt == 1 for c in got)
        assert db.jobs.count_documents({"status": "running"}) == 5


def test_lease_expiry_takeover_fences_the_old_worker_on_every_operation():
    with temp_db() as db:
        q.ensure_indexes(db)
        new(db)
        old = q.claim(db, "w1", lease_seconds=30, now=T0)
        assert q.claim(db, "w2", now=T0 + timedelta(seconds=10)) is None          # lease vigente: nadie lo toma
        q.heartbeat(db, old, lease_seconds=30, now=T0 + timedelta(seconds=20), stage="leyendo", progress={"filas": 5})
        assert q.claim(db, "w2", now=T0 + timedelta(seconds=40)) is None          # el latido extendio el lease
        newc = q.claim(db, "w2", now=T0 + timedelta(seconds=100))                 # vencido: w2 toma el control
        assert newc and newc.generation == old.generation + 1 and newc.attempt == 2 and newc.owner != old.owner
        for op in (lambda: q.heartbeat(db, old), lambda: q.complete(db, old, {"x": 1}),
                   lambda: q.fail(db, old, "E", "m", retryable=True)):
            with pytest.raises(q.LostOwnership):
                op()
        assert not q.still_owner(db, old) and q.still_owner(db, newc)
        q.complete(db, newc, {"ok": True}, now=T0 + timedelta(seconds=110))
        with pytest.raises(q.LostOwnership):
            q.complete(db, newc, {"otra": 1})                                      # ya termino: no se completa dos veces
        doc = db.jobs.find_one({})
        assert doc["status"] == "completed" and doc["result"] == {"ok": True}


def test_retry_with_backoff_then_failed_when_attempts_run_out_and_permanent_errors_do_not_loop():
    with temp_db() as db:
        q.ensure_indexes(db)
        new(db, max_attempts=2)
        c1 = q.claim(db, "w", now=T0)
        assert q.fail(db, c1, "TRANSITORIO", "mongo caido", retryable=True, backoff_seconds=10, now=T0) == "queued"
        assert q.claim(db, "w", now=T0 + timedelta(seconds=5)) is None            # backoff: aun no disponible
        c2 = q.claim(db, "w", now=T0 + timedelta(seconds=11))
        assert c2.attempt == 2
        assert q.fail(db, c2, "TRANSITORIO", "otra vez", retryable=True, now=T0 + timedelta(seconds=12)) == "failed"
        assert q.claim(db, "w", now=T0 + timedelta(days=1)) is None                # sin bucle infinito
        new(db, "perm")
        c = q.claim(db, "w", now=T0)
        assert q.fail(db, c, "DATOS", "archivo invalido", retryable=False, now=T0) == "failed"
        assert db.jobs.find_one({"idempotency_key": "perm"})["attempts"] == 1


def test_dead_worker_on_last_attempt_is_swept_to_failed_not_reclaimed():
    with temp_db() as db:
        q.ensure_indexes(db)
        new(db, max_attempts=1)
        q.claim(db, "w", lease_seconds=10, now=T0)                                 # muere sin terminar
        assert q.claim(db, "w2", now=T0 + timedelta(minutes=5)) is None
        assert q.sweep_exhausted(db, now=T0 + timedelta(minutes=5)) == 1
        doc = db.jobs.find_one({})
        assert doc["status"] == "failed" and doc["error"]["code"] == "WORKER_PERDIDO"


def test_public_view_hides_internal_input_owner_and_paths():
    with temp_db() as db:
        q.ensure_indexes(db)
        job, _ = new(db)
        c = q.claim(db, "w", now=T0)
        pub = q.public_job(db.jobs.find_one({"job_id": job["job_id"]}))
        text = str(pub)
        assert "/ruta/privada" not in text and c.owner not in text and "idempotency_key" not in pub
        assert pub["public"] == {"origin": "2026-07-10"} and pub["status"] == "running"


def test_concurrent_completion_race_only_the_owner_wins():
    with temp_db() as db:
        q.ensure_indexes(db)
        new(db)
        old = q.claim(db, "w1", lease_seconds=1, now=T0)
        newc = q.claim(db, "w2", now=T0 + timedelta(seconds=5))
        outcomes = []

        def attempt(c):
            try:
                q.complete(db, c, {"por": c.worker_id})
                outcomes.append(c.worker_id)
            except q.LostOwnership:
                outcomes.append("perdio-" + c.worker_id)

        ts = [threading.Thread(target=attempt, args=(c,)) for c in (old, newc)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(30)
        assert sorted(outcomes) == ["perdio-w1", "w2"] and db.jobs.find_one({})["result"] == {"por": "w2"}
