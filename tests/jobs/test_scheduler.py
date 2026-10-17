"""T10 §5: temporizador. Reloj controlado, ranura unica, clave estandar, coalescencia y deshabilitado por defecto."""
from __future__ import annotations

import json
import subprocess
import sys
import threading
from datetime import UTC, date, datetime, timedelta

import pytest

from pipeline.generate.config import load_t10_config
from pipeline.jobs import queue
from pipeline.jobs.keys import clean_idempotency_key, generate_run_key, sources_digest
from pipeline.jobs.scheduler import (
    COLLECTION,
    effective_instant,
    eligible_origin,
    slot_of,
    slot_start,
    tick,
)
from pipeline.publish.source import PROJECT_ROOT
from tests.jobs.jobs_support import fast_cfg, month_rows, run_job, store_upload
from tests.publish.helpers import temp_db

pytestmark = pytest.mark.mongo
CFG = load_t10_config()
D1 = datetime(2026, 6, 10, 12, 0, tzinfo=UTC)          # junio: origen = fecha Lima del inicio de la ranura


def test_scheduler_is_disabled_by_default_and_loop_requires_explicit_enable():
    assert CFG["temporizador"]["habilitado_por_defecto"] is False
    r = subprocess.run([sys.executable, "-m", "pipeline.jobs.scheduler", "--loop", "--db", "df_test_no_se_usa"],
                       cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=60, check=False)
    assert r.returncode == 2 and "deshabilitado" in r.stderr
    r2 = subprocess.run([sys.executable, "-m", "pipeline.jobs.scheduler", "--once", "--loop"], cwd=PROJECT_ROOT,
                        capture_output=True, text=True, timeout=60, check=False)
    assert r2.returncode != 0                                   # --once y --loop son excluyentes
    r3 = subprocess.run([sys.executable, "-m", "pipeline.jobs.scheduler"], cwd=PROJECT_ROOT, capture_output=True,
                        text=True, timeout=60, check=False)
    assert r3.returncode != 0                                   # sin modo no hace nada


def test_slot_and_origin_arithmetic_with_a_controlled_clock():
    s = slot_of(D1, 1440)
    assert slot_start(s, 1440) == datetime(2026, 6, 10, tzinfo=UTC)
    assert eligible_origin(slot_start(s, 1440), CFG) == date(2026, 6, 9)       # 00:00Z = 19:00 Lima del 09/06
    assert eligible_origin(datetime(2026, 5, 20, tzinfo=UTC), CFG) == date(2026, 6, 1)      # acotado al minimo
    assert eligible_origin(datetime(2026, 7, 11, 12, tzinfo=UTC), CFG) == date(2026, 7, 10)  # y al maximo
    assert eligible_origin(datetime(2026, 10, 17, tzinfo=UTC), CFG) == date(2026, 7, 10)
    assert slot_of(D1, 60) != slot_of(D1 + timedelta(hours=1), 60) and slot_of(D1, 60) == slot_of(D1 + timedelta(minutes=59), 60)
    # intervalo normal: el modo --loop cuenta el ultimo 06:00 de Lima (11:00Z), no el limite UTC
    assert effective_instant(datetime(2026, 6, 10, 10, 59, tzinfo=UTC), 1440, CFG) == datetime(2026, 6, 9, 11, tzinfo=UTC)
    assert effective_instant(datetime(2026, 6, 10, 11, 0, tzinfo=UTC), 1440, CFG) == datetime(2026, 6, 10, 11, tzinfo=UTC)
    assert effective_instant(D1, 60, CFG) == D1


def test_two_simultaneous_ticks_register_one_slot_and_enqueue_one_job():
    with temp_db() as db:
        barrier, out = threading.Barrier(2), []

        def go():
            barrier.wait()
            out.append(tick(db, D1, 1440, CFG))

        ts = [threading.Thread(target=go) for _ in range(2)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(60)
        assert sorted(o["outcome"] for o in out) == ["encolado", "ranura_ya_procesada"]
        assert db[COLLECTION].count_documents({}) == 1 and db.jobs.count_documents({}) == 1
        winner = next(o for o in out if o["outcome"] == "encolado")
        job = db.jobs.find_one({})
        assert job["job_id"] == winner["job_id"] and job["type"] == "generate_run" and job["created_by"] == "scheduler"
        assert job["input"] == {"origin": "2026-06-09", "horizon_days": 21, "method": "promedio_28"}
        assert job["public"]["trigger"] == "scheduler" and job["status"] == "queued"


def test_many_threads_same_slot_never_duplicate():
    with temp_db() as db:
        barrier, out = threading.Barrier(8), []

        def go():
            barrier.wait()
            out.append(tick(db, D1 + timedelta(seconds=1), 1440, CFG)["outcome"])

        ts = [threading.Thread(target=go) for _ in range(8)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(60)
        assert out.count("encolado") == 1 and out.count("ranura_ya_procesada") == 7
        assert db.jobs.count_documents({}) == 1 and db[COLLECTION].count_documents({}) == 1


def test_new_slot_gets_a_new_origin_and_job_and_same_origin_is_sin_cambios():
    with temp_db() as db:
        a = tick(db, D1, 1440, CFG)
        b = tick(db, D1 + timedelta(days=1), 1440, CFG)
        assert (a["origin"], b["origin"]) == ("2026-06-09", "2026-06-10") and a["job_id"] != b["job_id"]
        assert db.jobs.count_documents({}) == 2
        # dos ranuras distintas que dan el mismo origen (tope 10/07): la segunda es «sin cambios»
        c = tick(db, datetime(2026, 10, 17, 11, tzinfo=UTC), 1440, CFG)
        d = tick(db, datetime(2026, 10, 18, 11, tzinfo=UTC), 1440, CFG)
        assert c["origin"] == d["origin"] == "2026-07-10"
        assert (c["outcome"], d["outcome"]) == ("encolado", "sin_cambios") and c["job_id"] == d["job_id"]
        assert db.jobs.count_documents({}) == 3 and db[COLLECTION].count_documents({}) == 4
        again = tick(db, datetime(2026, 10, 18, 20, tzinfo=UTC), 1440, CFG)         # misma ranura de nuevo
        assert again["outcome"] == "ranura_ya_procesada" and again["job_id"] == d["job_id"]
        assert db.jobs.count_documents({}) == 3


def test_missed_ticks_are_coalesced_not_replayed():
    with temp_db() as db:
        tick(db, D1, 1440, CFG)
        late = tick(db, D1 + timedelta(days=5), 1440, CFG)          # el temporizador estuvo caido 4 ranuras
        assert late["outcome"] == "encolado" and late["missed_slots"] == 4
        assert db.jobs.count_documents({}) == 2                       # solo la ranura vigente; nada de recuperacion
        assert sorted(j["input"]["origin"] for j in db.jobs.find({})) == ["2026-06-09", "2026-06-14"]
        assert db[COLLECTION].count_documents({}) == 2


def test_scheduler_key_equals_the_standard_key_and_changes_with_new_approved_sources(tmp_path):
    uploads = tmp_path / "up"
    with temp_db() as db:
        res = tick(db, D1, 1440, CFG)
        job = db.jobs.find_one({"job_id": res["job_id"]})
        assert job["idempotency_key"] == generate_run_key(db, date(2026, 6, 9), 21, "promedio_28")
        # la API usa la misma clave: encolar desde la API la misma entrada devuelve el MISMO trabajo
        from backend.app.data.jobs import enqueue_generate
        same, created = enqueue_generate(db, origin=date(2026, 6, 9), horizon_days=21, method="promedio_28",
                                         generator=CFG["generador"]["version"], idempotency_header=None,
                                         created_by="admin")
        assert created is False and same["job_id"] == job["job_id"]
        # una fuente aprobada nueva cambia el digest y por tanto la clave
        before = sources_digest(db, date(2026, 6, 9))
        sha, size = store_upload(uploads, tmp_path, month_rows(3))
        from tests.jobs.jobs_support import enqueue_import
        enqueue_import(db, sha, size, "2026-03")
        only_imports = fast_cfg()
        only_imports["cola"]["tipos"] = ["import_excel"]                # el trabajo del temporizador sigue en cola
        assert run_job(db, uploads, cfg=only_imports)["status"] == "completed"
        assert sources_digest(db, date(2026, 6, 9)) != before
        assert generate_run_key(db, date(2026, 6, 9), 21, "promedio_28") != job["idempotency_key"]
        # entradas distintas nunca comparten clave; la cabecera del administrador se une saneada
        keys = {generate_run_key(db, date(2026, 6, 9), 21, "promedio_28"),
                generate_run_key(db, date(2026, 6, 9), 14, "promedio_28"),
                generate_run_key(db, date(2026, 6, 10), 21, "promedio_28"),
                generate_run_key(db, date(2026, 6, 9), 21, "promedio_28", "mi clave/1!")}
        assert len(keys) == 4 and clean_idempotency_key("mi clave/1!") == "miclave1"
        assert generate_run_key(db, date(2026, 6, 9), 21, "promedio_28", "mi clave/1!").endswith(":k=miclave1")
        assert all(len(k) <= 200 for k in keys)


def test_cli_once_with_controlled_clock_prints_result_and_is_idempotent():
    with temp_db() as db:
        def run_cli():
            r = subprocess.run([sys.executable, "-m", "pipeline.jobs.scheduler", "--once", "--now",
                                "2026-06-10T12:00:00Z", "--interval-minutes", "1440", "--db", db.name],
                               cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=120, check=False)
            assert r.returncode == 0, r.stderr
            return json.loads(r.stdout)
        first, second = run_cli(), run_cli()
        assert first["outcome"] == "encolado" and first["origin"] == "2026-06-09"
        assert second["outcome"] == "ranura_ya_procesada" and second["job_id"] == first["job_id"]
        assert db.jobs.count_documents({}) == 1
        q = db.jobs.find_one({})
        assert queue.public_job(q)["status"] == "queued"


def test_a_failed_enqueue_marks_the_tick_and_does_not_leave_a_phantom_job(monkeypatch):
    with temp_db() as db:
        from pipeline.jobs import scheduler

        def boom(*a, **k):
            raise RuntimeError("cola caida")
        monkeypatch.setattr(scheduler.queue, "enqueue", boom)
        with pytest.raises(RuntimeError):
            tick(db, D1, 1440, CFG)
        t = db[COLLECTION].find_one({})
        assert t["status"] == "error" and db.jobs.count_documents({}) == 0
