"""T10R R10: el modo `--loop` del temporizador funciona como PROCESO CONTINUO real (no dos `--once`) junto a un worker
real y Mongo real, en una base aislada y con reloj de prueba acelerado. No deja procesos residuales."""
from __future__ import annotations

import os
import subprocess
import sys
import time

import pytest

from pipeline.publish.source import PROJECT_ROOT
from tests.generate.helpers import build_months
from tests.publish.helpers import temp_db

pytestmark = pytest.mark.mongo


def _alive(proc: subprocess.Popen) -> bool:
    return proc.poll() is None


def test_scheduler_loop_process_enqueues_each_slot_once_and_a_real_worker_generates_the_runs(tmp_path):
    with temp_db() as db:
        build_months(db, tmp_path)                                  # ventas sinteticas hasta 30/06 (nunca datos reales)
        uploads = tmp_path / "up"
        env = {**os.environ, "DF_TEST_TIME_SCALE": "1800", "DF_TEST_CLOCK_START": "2026-06-20T20:00:00+00:00"}
        env.pop("APP_ENV", None)
        worker = subprocess.Popen(
            [sys.executable, "-m", "pipeline.jobs.worker", "--db", db.name, "--uploads-dir", str(uploads),
             "--poll-seconds", "0.5", "--worker-id", "w-loop"], cwd=PROJECT_ROOT, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        timer = subprocess.Popen(
            [sys.executable, "-m", "pipeline.jobs.scheduler", "--loop", "--enable", "--interval-minutes", "60",
             "--poll-seconds", "0.5", "--db", db.name], cwd=PROJECT_ROOT, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        try:
            end = time.monotonic() + 240
            while time.monotonic() < end:
                done = db.jobs.count_documents({"type": "generate_run", "status": "completed"})
                if done >= 2 and db.scheduler_ticks.count_documents({"status": "completado"}) >= 6:
                    break
                assert _alive(timer) and _alive(worker), "un proceso termino antes de tiempo"
                time.sleep(0.5)
            else:
                raise AssertionError("el bucle no produjo 2 corridas generadas a tiempo")
            assert _alive(timer), "el temporizador debe seguir vivo: es un proceso continuo"
        finally:
            for p in (timer, worker):
                p.terminate()
            for p in (timer, worker):
                try:
                    p.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    p.kill()
                    p.wait(timeout=30)
        assert timer.poll() is not None and worker.poll() is not None      # sin procesos residuales
        ticks = list(db.scheduler_ticks.find({}))
        slots = [t["slot"] for t in ticks]
        assert len(slots) == len(set(slots)) and all(t["interval_minutes"] == 60 for t in ticks)
        jobs = list(db.jobs.find({"type": "generate_run"}))
        origins = [j["input"]["origin"] for j in jobs]
        assert len(origins) == len(set(origins)) >= 2                       # una ranura repetida del mismo dia no duplica
        assert {j["created_by"] for j in jobs} == {"scheduler"}
        assert sum(t.get("outcome") == "sin_cambios" for t in ticks) >= 1   # ranuras del mismo origen: misma clave
        runs = list(db.runs.find({"kind": "generated_baseline", "status": "completed"}))
        assert len(runs) == db.jobs.count_documents({"type": "generate_run", "status": "completed"}) >= 2
        assert {r["origin"] for r in runs} <= set(origins)
