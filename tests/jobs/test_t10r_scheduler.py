"""T10R R10: una reserva de ranura fallida, caida o a medias se recupera sin duplicar trabajos (Mongo real)."""
from __future__ import annotations

import threading
from datetime import UTC, date, datetime, timedelta

import pytest
from pymongo.errors import AutoReconnect

from pipeline.generate.config import load_t10_config
from pipeline.jobs import queue, scheduler
from pipeline.jobs.keys import generate_run_key
from pipeline.jobs.scheduler import COLLECTION, tick
from tests.publish.helpers import temp_db

pytestmark = pytest.mark.mongo
CFG = load_t10_config()
NOW = datetime(2026, 6, 10, 12, 0, tzinfo=UTC)            # ranura diaria 2026-06-10 00:00Z => origen 09/06 (Lima)
SLOT = scheduler.slot_of(NOW, 1440)


def dead_reservation(db, status="procesando", lease_ago=300, **extra):
    """Lo que deja un proceso que murio despues de reservar la ranura y antes de terminar."""
    scheduler.ensure_indexes(db)
    db[COLLECTION].insert_one({"interval_minutes": 1440, "slot": SLOT, "slot_start": scheduler.slot_start(SLOT, 1440),
                               "origin": "2026-06-09", "horizon_days": 21, "method": "promedio_28", "status": status,
                               "owner": "muerto", "lease_expires_at": datetime.now(UTC) - timedelta(seconds=lease_ago),
                               "created_at": datetime.now(UTC), **extra})


def standard_job(db):
    key = generate_run_key(db, date(2026, 6, 9), 21, "promedio_28")
    job, created = queue.enqueue(db, "generate_run", {"origin": "2026-06-09", "horizon_days": 21,
                                 "method": "promedio_28"}, key, "scheduler", public={"trigger": "scheduler"})
    assert created
    return job


def test_transient_enqueue_failure_is_recovered_by_the_next_tick_of_the_same_slot(monkeypatch):
    with temp_db() as db:
        real = scheduler.queue.enqueue
        calls = {"n": 0}

        def flaky(*a, **k):
            calls["n"] += 1
            if calls["n"] == 1:
                raise AutoReconnect("transitorio")
            return real(*a, **k)
        monkeypatch.setattr(scheduler.queue, "enqueue", flaky)
        with pytest.raises(AutoReconnect):
            tick(db, NOW, 1440, CFG)
        assert db[COLLECTION].find_one({})["status"] == "error" and db.jobs.count_documents({}) == 0
        res = tick(db, NOW + timedelta(minutes=5), 1440, CFG)        # mismo slot, mas tarde
        assert res["outcome"] == "encolado" and res["origin"] == "2026-06-09" and calls["n"] == 2
        t = db[COLLECTION].find_one({})
        assert t["status"] == "completado" and t["job_id"] == res["job_id"] and db.jobs.count_documents({}) == 1


def test_crash_after_reserving_and_before_enqueue_is_recovered_once_the_lease_expires():
    with temp_db() as db:
        dead_reservation(db)
        res = tick(db, NOW, 1440, CFG)
        assert res["outcome"] == "encolado" and db.jobs.count_documents({}) == 1
        assert db[COLLECTION].find_one({})["status"] == "completado"
        assert tick(db, NOW, 1440, CFG)["outcome"] == "ranura_ya_procesada"
        assert db.jobs.count_documents({}) == 1


def test_a_live_reservation_is_not_stolen(monkeypatch):
    with temp_db() as db:
        dead_reservation(db, lease_ago=-120)                          # lease vigente de otro timer
        monkeypatch.setattr(scheduler.queue, "enqueue", lambda *a, **k: pytest.fail("no debe encolar"))
        res = tick(db, NOW, 1440, CFG)
        assert res["outcome"] == "ranura_en_proceso" and db.jobs.count_documents({}) == 0


def test_job_created_but_tick_not_finalized_reuses_the_existing_job_identity():
    with temp_db() as db:
        job = standard_job(db)
        dead_reservation(db)                                          # murio tras crear el job, antes de guardar job_id
        res = tick(db, NOW, 1440, CFG)
        assert res["outcome"] == "recuperado" and res["job_id"] == job["job_id"]
        assert db.jobs.count_documents({}) == 1
        t = db[COLLECTION].find_one({})
        assert t["status"] == "completado" and t["job_id"] == job["job_id"] and t["outcome"] == "recuperado"


def test_failure_while_recording_the_job_id_is_reconciled_by_the_retry(monkeypatch):
    with temp_db() as db:
        cls = db[COLLECTION].__class__
        real = cls.update_one
        boom = {"armed": True}

        def update_one(self, flt, upd, *a, **k):
            if boom["armed"] and "completado" in str(upd):
                boom["armed"] = False
                raise AutoReconnect("cae al guardar job_id")
            return real(self, flt, upd, *a, **k)
        monkeypatch.setattr(cls, "update_one", update_one)
        with pytest.raises(AutoReconnect):
            tick(db, NOW, 1440, CFG)
        assert db.jobs.count_documents({}) == 1
        db[COLLECTION].update_one({"slot": SLOT}, {"$set": {"lease_expires_at": datetime.now(UTC) - timedelta(seconds=9)}})
        res = tick(db, NOW, 1440, CFG)
        assert res["outcome"] == "recuperado" and db.jobs.count_documents({}) == 1
        assert db[COLLECTION].find_one({})["job_id"] == res["job_id"]


@pytest.mark.parametrize("status", ["error", "procesando"])
def test_two_timers_recovering_simultaneously_yield_one_job_and_one_winner(status):
    with temp_db() as db:
        dead_reservation(db, status=status)
        gate, out, errs = threading.Barrier(2, timeout=30), [], []

        def go():
            try:
                gate.wait()
                out.append(tick(db, NOW, 1440, CFG))
            except Exception as exc:  # noqa: BLE001
                errs.append(exc)

        ts = [threading.Thread(target=go) for _ in range(2)]
        [t.start() for t in ts]
        [t.join(60) for t in ts]
        assert not errs and db.jobs.count_documents({}) == 1
        assert sum(o["outcome"] == "encolado" for o in out) == 1
        assert {o["outcome"] for o in out} <= {"encolado", "ranura_en_proceso", "ranura_ya_procesada"}
        assert db[COLLECTION].find_one({})["status"] == "completado" and db[COLLECTION].count_documents({}) == 1


def test_a_stale_timer_cannot_overwrite_the_recovery_and_creates_no_second_job(monkeypatch):
    with temp_db() as db:
        real = scheduler.queue.enqueue
        state = {"inner": False}

        def slow_enqueue(*a, **k):
            if not state["inner"]:
                state["inner"] = True
                # mientras A se cuelga dentro de enqueue, su lease vence y B recupera y termina
                db[COLLECTION].update_one({"slot": SLOT},
                                          {"$set": {"lease_expires_at": datetime.now(UTC) - timedelta(seconds=5)}})
                state["b"] = tick(db, NOW, 1440, CFG)
            return real(*a, **k)
        monkeypatch.setattr(scheduler.queue, "enqueue", slow_enqueue)
        a = tick(db, NOW, 1440, CFG)
        assert state["b"]["outcome"] == "encolado"
        assert a["outcome"] == "ranura_tomada" and a["job_id"] == state["b"]["job_id"]
        assert db.jobs.count_documents({}) == 1 and db[COLLECTION].find_one({})["status"] == "completado"


def test_completed_slot_repeated_does_not_touch_the_queue(monkeypatch):
    with temp_db() as db:
        first = tick(db, NOW, 1440, CFG)
        monkeypatch.setattr(scheduler.queue, "enqueue", lambda *a, **k: pytest.fail("no debe encolar"))
        again = tick(db, NOW + timedelta(hours=3), 1440, CFG)
        assert again["outcome"] == "ranura_ya_procesada" and again["job_id"] == first["job_id"]


def test_recovery_keeps_the_origin_of_the_slot_start_and_a_new_utc_slot_gets_its_own_origin():
    with temp_db() as db:
        dead_reservation(db)
        res = tick(db, NOW + timedelta(hours=11), 1440, CFG)        # 23:00Z del 10/06: misma ranura UTC
        assert res["origin"] == "2026-06-09" and res["slot"] == SLOT
        nxt = tick(db, NOW + timedelta(hours=13), 1440, CFG)        # 01:00Z del 11/06: ranura nueva, origen 10/06 (Lima)
        assert nxt["origin"] == "2026-06-10" and nxt["outcome"] == "encolado" and db.jobs.count_documents({}) == 2
        assert nxt["missed_slots"] == 0
