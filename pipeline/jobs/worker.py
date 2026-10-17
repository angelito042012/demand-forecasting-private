"""Worker de la cola (T10 §4). Independiente de HTTP.

    python -m pipeline.jobs.worker [--once] [--poll-seconds N] [--worker-id ID] [--db NOMBRE]

* reclama trabajos con `queue.claim` (atomico; soporta varios procesos), mantiene un HILO de latido que renueva el
  lease cada `cola.latido_segundos` y detecta la perdida de propiedad (`LostOwnership`): el handler se detiene sin
  escribir y el worker no toca el trabajo;
* completa con `queue.complete` o falla con `queue.fail(retryable=...)`: transitorio (Mongo no disponible, E/S)
  reintenta con backoff; permanente (datos) no reintenta;
* periodicamente barre trabajos que agotaron intentos (`sweep_exhausted`) y limpia hijos huerfanos de publicaciones
  abandonadas (`purge_orphans`);
* `--once`: una vuelta = tareas de mantenimiento + procesa los trabajos disponibles hasta vaciar la cola y sale
  (los reintentos con backoff pendiente no se esperan).
Opciones de operacion/pruebas: `--lease-seconds`, `--heartbeat-seconds`, `--uploads-dir`.
No imprime configuracion, URI ni entradas de trabajos.
"""
from __future__ import annotations

import argparse
import logging
import os
import re
import signal
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

from pymongo.errors import PyMongoError

from pipeline.data.importer import get_client
from pipeline.generate.config import load_t10_config
from pipeline.jobs import queue
from pipeline.jobs.handlers import HANDLERS, JobContext, classify, default_uploads_dir
from pipeline.publish.protocol import purge_orphans

log = logging.getLogger("pipeline.jobs.worker")
_DB = re.compile(r"^[A-Za-z0-9_]{1,63}$")
HOUSEKEEPING_SECONDS = 60


class HeartbeatThread(threading.Thread):
    """Renueva el lease del trabajo mientras el handler trabaja y senala la perdida de propiedad."""

    def __init__(self, db, claim: queue.Claim, interval: float, lease_seconds: int, lost: threading.Event):
        super().__init__(name=f"heartbeat-{claim.job_id[:8]}", daemon=True)
        self.db, self.claim, self.interval, self.lease, self.lost = db, claim, interval, lease_seconds, lost
        self._stop_event = threading.Event()

    def run(self) -> None:
        while not self._stop_event.wait(self.interval):
            try:
                queue.heartbeat(self.db, self.claim, lease_seconds=self.lease)
            except queue.LostOwnership:
                self.lost.set()
                return
            except PyMongoError:
                continue              # transitorio: el lease aun vive; se reintenta en el siguiente latido

    def stop(self) -> None:
        self._stop_event.set()
        self.join(timeout=10)


def housekeeping(db, now: datetime | None = None) -> dict:
    """Barrido de trabajos sin intentos y limpieza de hijos huerfanos. Idempotente; seguro con varios workers."""
    swept = queue.sweep_exhausted(db, now=now)
    removed = purge_orphans(db, now=now)
    if swept or removed:
        log.info("mantenimiento: %s trabajos agotados, huerfanos eliminados=%s", swept, removed)
    return {"swept": swept, "orphans": removed}


def process_next(db, worker_id: str, cfg: dict, *, uploads_dir: Path, lease_seconds: int, heartbeat_seconds: float,
                 stage_hook=None, activate_run: bool = False) -> str | None:
    """Reclama y procesa UN trabajo. Devuelve su job_id o None si no habia ninguno disponible."""
    claim = queue.claim(db, worker_id, tuple(cfg["cola"]["tipos"]), lease_seconds=lease_seconds)
    if claim is None:
        return None
    log.info("trabajo %s (%s) reclamado, intento %s, generacion %s", claim.job_id, claim.type, claim.attempt,
             claim.generation)
    lost = threading.Event()
    ctx = JobContext(db=db, claim=claim, cfg=cfg, uploads_dir=uploads_dir, lease_seconds=lease_seconds, lost=lost,
                     stage_hook=stage_hook, activate_run=activate_run)
    hb = HeartbeatThread(db, claim, heartbeat_seconds, lease_seconds, lost)
    hb.start()
    backoff = int(cfg["cola"]["backoff_base_segundos"])
    try:
        try:
            handler = HANDLERS[claim.type]
            result = handler(ctx)
            hb.stop()
            queue.complete(db, claim, result)
            log.info("trabajo %s completado (%s)", claim.job_id, result.get("outcome") if isinstance(result, dict) else "")
        except queue.LostOwnership:
            log.warning("trabajo %s: se perdio la propiedad; se detiene sin escribir", claim.job_id)
        except KeyboardInterrupt:
            hb.stop()
            try:
                queue.fail(db, claim, "INTERRUMPIDO", "El worker se detuvo; el trabajo se reintentará.",
                           retryable=True, backoff_seconds=1)
            except (queue.LostOwnership, PyMongoError):
                pass
            raise
        except Exception as exc:  # noqa: BLE001 - se clasifica y se registra sin trazas ni datos internos
            hb.stop()
            code, message, retryable = classify(exc)
            log.warning("trabajo %s fallo: %s (reintentable=%s)", claim.job_id, code, retryable)
            try:
                # esperar a que venza el lease del intento de publicacion anterior antes de reintentar
                wait = (int(cfg["cola"].get("backoff_publicacion_en_curso_segundos", backoff))
                        if code == "PUBLICACION_EN_CURSO" else backoff)
                state = queue.fail(db, claim, code, message, retryable=retryable, backoff_seconds=wait)
                log.info("trabajo %s -> %s", claim.job_id, state)
            except queue.LostOwnership:
                log.warning("trabajo %s: propiedad perdida al registrar el fallo", claim.job_id)
            except PyMongoError:
                log.error("trabajo %s: no se pudo registrar el fallo (base no disponible); el lease vencera",
                          claim.job_id)
    finally:
        hb.stop()
    return claim.job_id


def run(db, worker_id: str, *, once: bool, poll_seconds: float, cfg: dict, uploads_dir: Path, lease_seconds: int,
        heartbeat_seconds: float, stop: threading.Event | None = None, stage_hook=None) -> int:
    stop = stop or threading.Event()
    queue.ensure_indexes(db)
    last_clean = 0.0
    done = 0
    while not stop.is_set():
        if time.monotonic() - last_clean >= HOUSEKEEPING_SECONDS or last_clean == 0.0:
            try:
                housekeeping(db)
            except PyMongoError:
                log.warning("mantenimiento omitido: base no disponible")
            last_clean = time.monotonic()
        try:
            job = process_next(db, worker_id, cfg, uploads_dir=uploads_dir, lease_seconds=lease_seconds,
                               heartbeat_seconds=heartbeat_seconds, stage_hook=stage_hook)
        except PyMongoError:
            job = None
            log.warning("base de datos no disponible; se reintenta")
            if once:
                return 1
        if job is not None:
            done += 1
            continue
        if once:
            break
        stop.wait(poll_seconds)
    log.info("worker termina; trabajos procesados=%s", done)
    return 0


def main(argv=None) -> int:
    cfg = load_t10_config()
    cola = cfg["cola"]
    ap = argparse.ArgumentParser(description="Worker de la cola de trabajos (importacion y generacion)")
    ap.add_argument("--once", action="store_true", help="una vuelta: procesa lo disponible y sale")
    ap.add_argument("--poll-seconds", type=float, default=float(cola["sondeo_segundos"]))
    ap.add_argument("--worker-id", default=None)
    ap.add_argument("--db", default=os.environ.get("MONGODB_DATABASE", "demand_forecasting_v2"))
    ap.add_argument("--lease-seconds", type=int, default=int(cola["lease_segundos"]))
    ap.add_argument("--heartbeat-seconds", type=float, default=float(cola["latido_segundos"]))
    ap.add_argument("--uploads-dir", type=Path, default=None, help="solo operacion/pruebas: directorio privado")
    args = ap.parse_args(argv)
    if not _DB.match(args.db):
        print("Nombre de base invalido.", file=sys.stderr)
        return 2
    if args.heartbeat_seconds >= args.lease_seconds:
        print("El latido debe ser menor que el lease.", file=sys.stderr)
        return 2
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(asctime)s %(levelname)s %(message)s")
    worker_id = args.worker_id or f"worker-{os.getpid()}-{uuid.uuid4().hex[:6]}"
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, lambda *_a: stop.set())
        except (ValueError, OSError):
            pass
    client = get_client()
    try:
        return run(client[args.db], worker_id, once=args.once, poll_seconds=args.poll_seconds, cfg=cfg,
                   uploads_dir=args.uploads_dir or default_uploads_dir(cfg), lease_seconds=args.lease_seconds,
                   heartbeat_seconds=args.heartbeat_seconds, stop=stop)
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())

