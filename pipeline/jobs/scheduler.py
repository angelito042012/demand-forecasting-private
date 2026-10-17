"""Temporizador de generacion (T10 §5). Proceso OPCIONAL y deshabilitado por defecto: no ejecuta nada pesado, solo
registra una ranura y encola `generate_run` (el worker procesa).

    python -m pipeline.jobs.scheduler --once [--now ISO] [--interval-minutes N] [--db NOMBRE]
    python -m pipeline.jobs.scheduler --loop --enable [--interval-minutes N] [--db NOMBRE]

* ranura UTC = piso(instante UTC / intervalo); `scheduler_ticks` tiene indice unico (intervalo, ranura): dos ticks
  simultaneos => uno gana y el otro registra «ranura ya procesada»;
* origen elegible = min(fecha de negocio America/Lima del INICIO de la ranura, origen_maximo), acotado a
  origen_minimo (el inicio de la ranura hace el origen independiente del momento exacto del tick);
* clave de idempotencia estandar (`pipeline.jobs.keys.generate_run_key`, la misma que usa la API): si ya existe el
  trabajo de esa entrada => «sin_cambios» y se conserva el resultado anterior;
* ticks perdidos: politica COALESCENTE; solo cuenta la ranura vigente, las pasadas no se reejecutan (se informa
  cuantas se omitieron);
* `--loop` con el intervalo normal (1440) dispara a las 06:00 America/Lima (la ranura sigue siendo el dia UTC);
  con otros intervalos dispara en cada limite de ranura. Exige `--enable` explicito. No instala tareas del sistema.
No ejecuta experimentos ni el test final.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import threading
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError, PyMongoError

from pipeline.data.importer import get_client
from pipeline.generate.config import load_t10_config
from pipeline.jobs import queue
from pipeline.jobs.keys import generate_run_key

log = logging.getLogger("pipeline.jobs.scheduler")
COLLECTION = "scheduler_ticks"
LIMA = ZoneInfo("America/Lima")
_DB = re.compile(r"^[A-Za-z0-9_]{1,63}$")


def ensure_indexes(db) -> None:
    db[COLLECTION].create_index([("interval_minutes", ASCENDING), ("slot", ASCENDING)], unique=True,
                                name="uq_tick_slot")


def _utc(t: datetime) -> datetime:
    return t.astimezone(UTC) if t.tzinfo else t.replace(tzinfo=UTC)


def slot_of(now: datetime, interval_minutes: int) -> int:
    return int(_utc(now).timestamp() // (interval_minutes * 60))


def slot_start(slot: int, interval_minutes: int) -> datetime:
    return datetime.fromtimestamp(slot * interval_minutes * 60, tz=UTC)


def eligible_origin(start_utc: datetime, cfg: dict) -> date:
    """min(fecha de negocio Lima de la ranura, origen_maximo) acotado a origen_minimo."""
    pol = cfg["politica_desarrollo"]
    lima_day = start_utc.astimezone(LIMA).date()
    return max(date.fromisoformat(pol["origen_minimo"]), min(lima_day, date.fromisoformat(pol["origen_maximo"])))


def tick(db, now: datetime, interval_minutes: int | None = None, cfg: dict | None = None) -> dict:
    """Un tick: registra la ranura (unica) y encola la generacion. Devuelve un resumen sin datos internos."""
    cfg = cfg or load_t10_config()
    tmp = cfg["temporizador"]
    interval = int(interval_minutes or tmp["intervalo_normal_minutos"])
    if not 1 <= interval <= 1440:
        raise ValueError("intervalo fuera de rango (1-1440 minutos)")
    now = _utc(now)
    ensure_indexes(db)
    queue.ensure_indexes(db)
    slot = slot_of(now, interval)
    start = slot_start(slot, interval)
    origin = eligible_origin(start, cfg)
    pol = cfg["politica_desarrollo"]
    horizon, method = int(pol["horizonte_maximo"]), str(pol["metodos_permitidos"][0])
    doc = {"interval_minutes": interval, "slot": slot, "slot_start": start, "tick_at": now, "origin": origin.isoformat(),
           "horizon_days": horizon, "method": method, "status": "procesando", "created_at": datetime.now(UTC)}
    try:
        db[COLLECTION].insert_one(doc)
    except DuplicateKeyError:
        prev = db[COLLECTION].find_one({"interval_minutes": interval, "slot": slot}, {"_id": 0})
        return {"outcome": "ranura_ya_procesada", "slot": slot, "slot_start": start.isoformat(),
                "origin": (prev or {}).get("origin"), "job_id": (prev or {}).get("job_id"),
                "previous_outcome": (prev or {}).get("outcome")}
    last = db[COLLECTION].find_one({"interval_minutes": interval, "slot": {"$lt": slot}}, sort=[("slot", -1)])
    missed = (slot - last["slot"] - 1) if last else 0      # coalescente: no se reejecutan
    try:
        key = generate_run_key(db, origin, horizon, method)
        job, created = queue.enqueue(
            db, "generate_run", {"origin": origin.isoformat(), "horizon_days": horizon, "method": method}, key,
            "scheduler", max_attempts=int(cfg["cola"]["max_intentos"]),
            public={"origin": origin.isoformat(), "horizon_days": horizon, "method": method, "trigger": "scheduler"})
    except Exception as exc:
        db[COLLECTION].update_one({"interval_minutes": interval, "slot": slot},
                                  {"$set": {"status": "error", "error": type(exc).__name__}})
        raise
    outcome = "encolado" if created else "sin_cambios"
    db[COLLECTION].update_one({"interval_minutes": interval, "slot": slot},
                              {"$set": {"status": "completado", "outcome": outcome, "job_id": job["job_id"],
                                        "missed_slots": missed, "finished_at": datetime.now(UTC)}})
    return {"outcome": outcome, "slot": slot, "slot_start": start.isoformat(), "origin": origin.isoformat(),
            "horizon_days": horizon, "method": method, "job_id": job["job_id"], "job_status": job["status"],
            "missed_slots": missed}


def effective_instant(now: datetime, interval_minutes: int, cfg: dict) -> datetime:
    """Instante que cuenta para la ranura en modo `--loop`: con el intervalo normal, el ultimo 06:00 Lima <= ahora."""
    tmp = cfg["temporizador"]
    if interval_minutes != int(tmp["intervalo_normal_minutos"]):
        return _utc(now)
    hh, mm = (int(x) for x in str(tmp["hora_normal_lima"]).split(":"))
    local = _utc(now).astimezone(LIMA)
    due = datetime.combine(local.date(), time(hh, mm), tzinfo=LIMA)
    if due > local:
        due -= timedelta(days=1)
    return due.astimezone(UTC)


def run_loop(db, interval_minutes: int, cfg: dict, stop: threading.Event, *, poll_seconds: float = 30.0,
             clock=lambda: datetime.now(UTC)) -> None:
    """Repite hasta `stop`: en cada vuelta intenta la ranura vigente (el indice unico evita duplicados)."""
    while not stop.is_set():
        try:
            res = tick(db, effective_instant(clock(), interval_minutes, cfg), interval_minutes, cfg)
            if res["outcome"] != "ranura_ya_procesada":
                log.info("tick: %s (origen %s, trabajo %s)", res["outcome"], res.get("origin"), res.get("job_id"))
        except PyMongoError:
            log.warning("tick omitido: base de datos no disponible")
        stop.wait(poll_seconds)


def _parse_now(text: str) -> datetime:
    return _utc(datetime.fromisoformat(text))


def main(argv=None) -> int:
    cfg = load_t10_config()
    tmp = cfg["temporizador"]
    ap = argparse.ArgumentParser(description="Temporizador opcional de generacion (deshabilitado por defecto)")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--once", action="store_true", help="ejecuta un tick y sale")
    mode.add_argument("--loop", action="store_true", help="repite cada intervalo (exige --enable)")
    ap.add_argument("--enable", action="store_true", help="habilitacion explicita del modo --loop")
    ap.add_argument("--now", default=None, help="solo --once: instante ISO-8601 (reloj controlado para pruebas)")
    ap.add_argument("--interval-minutes", type=int, default=int(tmp["intervalo_normal_minutos"]))
    ap.add_argument("--db", default=os.environ.get("MONGODB_DATABASE", "demand_forecasting_v2"))
    args = ap.parse_args(argv)
    if not _DB.match(args.db):
        print("Nombre de base invalido.", file=sys.stderr)
        return 2
    if not 1 <= args.interval_minutes <= 1440:
        print("Intervalo fuera de rango (1-1440).", file=sys.stderr)
        return 2
    if args.loop and not (args.enable or tmp.get("habilitado_por_defecto")):
        print("El temporizador esta deshabilitado por defecto: use --enable para el modo --loop.", file=sys.stderr)
        return 2
    if args.now and not args.once:
        print("--now solo se admite con --once.", file=sys.stderr)
        return 2
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(asctime)s %(levelname)s %(message)s")
    client = get_client()
    try:
        db = client[args.db]
        if args.once:
            now = _parse_now(args.now) if args.now else datetime.now(UTC)
            print(json.dumps(tick(db, now, args.interval_minutes, cfg), ensure_ascii=False))
            return 0
        stop = threading.Event()
        try:
            run_loop(db, args.interval_minutes, cfg, stop)
        except KeyboardInterrupt:
            stop.set()
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
