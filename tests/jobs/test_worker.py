"""T10 §4: worker. Procesos reales (dos workers, reinicio tras matar el proceso) y perdida de propiedad."""
from __future__ import annotations

import subprocess
import sys
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from pipeline.jobs import queue
from pipeline.jobs.worker import housekeeping, run
from pipeline.publish.source import PROJECT_ROOT
from tests.generate.helpers import build_months, patch_reference
from tests.jobs.jobs_support import (
    enqueue_generate,
    enqueue_import,
    fast_cfg,
    month_rows,
    run_job,
    store_upload,
)
from tests.publish.helpers import kids, temp_db

pytestmark = pytest.mark.mongo
ORIGIN = date(2026, 6, 20)

# Proceso "worker lento": igual que el real pero el handler se detiene a mitad de trabajo (para matarlo).
SLOW_WORKER = r'''
import pathlib, sys, time
from pipeline.jobs import handlers, worker

marker, mode, rest = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3:]
if mode == "import":
    def slow(ctx):
        ctx.progress("importando", {"filas_leidas": 13})
        marker.write_text("a mitad")
        time.sleep(600)
    handlers.HANDLERS["import_excel"] = slow
else:
    real = handlers.HANDLERS["generate_run"]
    def wrapped(ctx):
        def hook(stage):
            if stage == "forecasts_sku":
                marker.write_text("a mitad de la publicacion")
                time.sleep(600)
        ctx.stage_hook = hook
        return real(ctx)
    handlers.HANDLERS["generate_run"] = wrapped
sys.exit(worker.main(rest))
'''


def spawn(db_name: str, uploads: Path, *args: str, lease: int = 30, beat: float = 5) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-m", "pipeline.jobs.worker", "--db", db_name, "--uploads-dir", str(uploads),
         "--lease-seconds", str(lease), "--heartbeat-seconds", str(beat), *args],
        cwd=PROJECT_ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def spawn_slow(db_name: str, uploads: Path, marker: Path, mode: str) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-c", SLOW_WORKER, str(marker), mode, "--once", "--db", db_name, "--uploads-dir",
         str(uploads), "--lease-seconds", "4", "--heartbeat-seconds", "1", "--worker-id", "w-condenado"],
        cwd=PROJECT_ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def wait_for(cond, timeout: float = 90, step: float = 0.2):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        v = cond()
        if v:
            return v
        time.sleep(step)
    raise AssertionError("tiempo de espera agotado")


def finish(proc: subprocess.Popen, timeout: float = 180) -> tuple[int, str]:
    try:
        _out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        raise
    return proc.returncode, err


def test_once_lap_processes_available_jobs_and_runs_maintenance(tmp_path, monkeypatch):
    patch_reference(monkeypatch)
    uploads = tmp_path / "up"
    with temp_db() as db:
        build_months(db, tmp_path, months=(3, 4, 5, 6))      # 4 fuentes aprobadas (no se reimportan)
        sha, size = store_upload(uploads, tmp_path, month_rows(7, seed=7))
        enqueue_import(db, sha, size, "2026-07")
        enqueue_generate(db, ORIGIN)
        # mantenimiento: un trabajo agotado con el lease vencido y un hijo huerfano de una publicacion abandonada
        old = datetime.now(UTC) - timedelta(hours=1)
        db.jobs.insert_one({"job_id": "muerto", "type": "generate_run", "status": "running", "attempts": 3,
                            "max_attempts": 3, "lease_expires_at": old, "owner": "x", "generation": 3,
                            "idempotency_key": "muerto", "created_at": old, "available_at": old, "input": {}})
        db.forecasts.insert_one({"run_id": "gen-x~g1", "level": "sku", "entity_id": "1|1", "target_date": "2026-06-21"})
        code = run(db, "w-vuelta", once=True, poll_seconds=0.1, cfg=fast_cfg(), uploads_dir=uploads, lease_seconds=60,
                   heartbeat_seconds=15)
        assert code == 0
        jobs = {j["type"]: j for j in db.jobs.find({"job_id": {"$ne": "muerto"}})}
        assert jobs["import_excel"]["status"] == "completed" and jobs["import_excel"]["result"]["ventas"] == 10
        assert jobs["generate_run"]["status"] == "completed" and jobs["generate_run"]["result"]["outcome"] == "generada"
        assert jobs["generate_run"]["worker_id"] == "w-vuelta"
        dead = db.jobs.find_one({"job_id": "muerto"})
        assert dead["status"] == "failed" and dead["error"]["code"] == "WORKER_PERDIDO"
        assert db.forecasts.count_documents({"run_id": "gen-x~g1"}) == 0
        # una segunda vuelta sin trabajo no hace nada
        assert run(db, "w-vuelta", once=True, poll_seconds=0.1, cfg=fast_cfg(), uploads_dir=uploads, lease_seconds=60,
                   heartbeat_seconds=15) == 0
        assert housekeeping(db) == {"swept": 0, "orphans": {}}


def test_two_real_worker_processes_process_each_job_exactly_once(tmp_path):
    uploads = tmp_path / "up"
    with temp_db() as db:
        shas = {}
        for month in (3, 4, 5, 6, 7):
            sha, size = store_upload(uploads, tmp_path, month_rows(month, seed=month), f"m{month}.xlsx")
            enqueue_import(db, sha, size, f"2026-{month:02d}")
            shas[month] = sha
        procs = [spawn(db.name, uploads, "--once", "--worker-id", f"proc-{i}") for i in range(2)]
        results = [finish(p) for p in procs]
        assert [r[0] for r in results] == [0, 0], results
        jobs = list(db.jobs.find({}))
        assert len(jobs) == 5 and {j["status"] for j in jobs} == {"completed"}
        assert all(j["attempts"] == 1 and j["generation"] == 1 for j in jobs)        # ningun trabajo se repitio
        assert {j["worker_id"] for j in jobs} <= {"proc-0", "proc-1"}
        assert db.imports.count_documents({"noop": {"$ne": True}}) == 5 and db.imports.count_documents({"noop": True}) == 0
        assert db.sales.count_documents({}) == 50 and db.credit_notes.count_documents({}) == 10
        assert len(db.sales.distinct("linea_id")) == 50
        assert sorted(i["sha256"] for i in db.imports.find({})) == sorted(shas.values())


def test_real_process_restart_recovers_an_import_killed_midway_without_duplicating(tmp_path):
    uploads = tmp_path / "up"
    marker = tmp_path / "marcador"
    with temp_db() as db:
        sha, size = store_upload(uploads, tmp_path, month_rows(4, n_sales=12))
        job = enqueue_import(db, sha, size, "2026-04")
        a = spawn_slow(db.name, uploads, marker, "import")
        try:
            wait_for(lambda: marker.exists())
            doc = db.jobs.find_one({"job_id": job["job_id"]})
            assert doc["status"] == "running" and doc["worker_id"] == "w-condenado" and doc["generation"] == 1
            assert doc["stage"] == "importando" and doc["progress"] == {"filas_leidas": 13}
        finally:
            a.kill()                                      # muerte abrupta del proceso a mitad del trabajo
            a.communicate(timeout=30)
        assert db.sales.count_documents({}) == 0          # nada a medias
        stuck = db.jobs.find_one({"job_id": job["job_id"]})
        assert stuck["status"] == "running"               # nadie lo completo ni lo fallo
        wait_for(lambda: db.jobs.find_one({"job_id": job["job_id"]})["lease_expires_at"].replace(tzinfo=UTC)
                 < datetime.now(UTC), timeout=30)
        code, err = finish(spawn(db.name, uploads, "--once", "--worker-id", "w-recuperador", "--lease-seconds", "30"))
        assert code == 0, err
        done = db.jobs.find_one({"job_id": job["job_id"]})
        assert done["status"] == "completed" and done["generation"] == 2 and done["attempts"] == 2
        assert done["worker_id"] == "w-recuperador" and done["result"]["outcome"] == "importado"
        assert db.sales.count_documents({}) == 12 and len(db.sales.distinct("linea_id")) == 12
        assert db.imports.count_documents({"sha256": sha}) == 1
        assert db.jobs.count_documents({}) == 1


def test_real_process_restart_recovers_a_generation_killed_during_publication(tmp_path):
    uploads = tmp_path / "up"
    marker = tmp_path / "marcador"
    with temp_db() as db:
        build_months(db, tmp_path)
        job = enqueue_generate(db, ORIGIN)
        a = spawn_slow(db.name, uploads, marker, "generate")
        try:
            wait_for(lambda: marker.exists(), timeout=180)
            run_doc = db.runs.find_one({})
            assert run_doc["status"] == "staging" and run_doc["generation"] == 1
            assert db.forecasts.count_documents({"run_id": run_doc["run_id"] + "~g1"}) > 0     # hijos a medias
        finally:
            a.kill()
            a.communicate(timeout=30)
        assert db.runs.count_documents({"status": "completed"}) == 0
        # el lease del trabajo vence solo (4 s sin latido); el de la corrida lo adelantamos para no esperar 120 s
        db.runs.update_one({"status": "staging"}, {"$set": {"lease_expires_at": datetime.now(UTC) - timedelta(seconds=5)}})
        wait_for(lambda: db.jobs.find_one({"job_id": job["job_id"]})["lease_expires_at"].replace(tzinfo=UTC)
                 < datetime.now(UTC), timeout=30)
        code, err = finish(spawn(db.name, uploads, "--once", "--worker-id", "w-recuperador"))
        assert code == 0, err
        done = db.jobs.find_one({"job_id": job["job_id"]})
        assert done["status"] == "completed" and done["generation"] == 2 and done["result"]["outcome"] == "generada"
        runs = list(db.runs.find({}))
        assert len(runs) == 1 and runs[0]["status"] == "completed" and runs[0]["children_ref"].endswith("~g2")
        ids = set(db.forecasts.distinct("run_id"))
        assert ids == {runs[0]["children_ref"]}            # los hijos del intento muerto se purgaron; no hay duplicados
        n = db.forecasts.count_documents({"run_id": runs[0]["children_ref"], "level": "sku"})
        assert n == done["result"]["counts"]["forecasts_sku"] == runs[0]["counts"]["forecasts_sku"]


def test_ownership_lost_mid_generation_stops_the_old_worker_without_writing(tmp_path, monkeypatch):
    patch_reference(monkeypatch)
    uploads = tmp_path / "up"
    with temp_db() as db:
        build_months(db, tmp_path)
        job = enqueue_generate(db, ORIGIN)
        stolen = []

        def steal(stage):
            if stage == "forecasts_sku" and not stolen:
                db.jobs.update_one({"job_id": job["job_id"]}, {"$set": {"lease_expires_at": datetime.now(UTC) - timedelta(seconds=1)}})
                stolen.append(queue.claim(db, "ladron", lease_seconds=300))

        after = run_job(db, uploads, worker="w-viejo", stage_hook=steal)
        thief = stolen[0]
        assert thief is not None and thief.generation == 2
        assert after["status"] == "running" and after["worker_id"] == "ladron" and after["owner"] == thief.owner
        assert after["result"] is None and after["error"] is None       # el viejo no completo, ni fallo, ni escribio
        run_doc = db.runs.find_one({})
        assert run_doc["status"] == "failed"                              # su intento quedo cerrado, nunca completed
        assert db.forecasts.count_documents({"run_id": {"$regex": "~g1$"}}) == 0   # limpio SOLO su propio espacio
        assert db.run_pointer.find_one({"_id": "active"}) is None
        # el nuevo dueno termina el trabajo (otro worker lo retoma al vencer su lease) sin duplicar
        db.jobs.update_one({"job_id": job["job_id"]}, {"$set": {"lease_expires_at": datetime.now(UTC) - timedelta(seconds=1)}})
        final = run_job(db, uploads, worker="w-nuevo")
        assert final["status"] == "completed" and final["generation"] == 3 and final["result"]["outcome"] == "generada"
        runs = list(db.runs.find({}))
        assert len(runs) == 1 and runs[0]["status"] == "completed"
        assert set(db.forecasts.distinct("run_id")) == {kids(db, runs[0]["run_id"])}
        with pytest.raises(queue.LostOwnership):
            queue.complete(db, queue.Claim(job["job_id"], "generate_run", "viejo", 1, 1, {}, "w-viejo"), {"x": 1})
