"""Protocolo de publicacion con PROPIEDAD POR INTENTO y fencing (T10 §1). Mongo standalone, sin transacciones.

Diseno (cada paso es una operacion atomica sobre UN documento):

* La corrida (`runs`) lleva `owner` (token del intento), `generation` (solo crece) y `lease_expires_at`.
  `claim_run` crea la corrida o toma una fallida/abandonada con CAS sobre (status, generation).
* Los hijos (forecasts/recommendations/backtests) de un intento se escriben con `run_id = children_id =
  "<run_id>~g<generation>"`: un intento obsoleto escribe en SU espacio y jamas pisa el de otro (los indices
  unicos incluyen run_id). La limpieza de un intento solo borra su propio `children_id`.
* `guard` (= renovar lease con CAS sobre owner+generation+status=staging) se invoca antes de cada lote, antes
  de validar y antes de completar. Si el intento perdio la propiedad lanza LostOwnership y el publicador se
  detiene sin escribir mas ni limpiar nada ajeno.
* Visibilidad atomica: `complete_run` es un CAS que cambia status->completed y fija `children_ref =
  children_id` (los lectores consultan los hijos de `children_ref`). Un intento obsoleto no puede completar,
  de modo que sus hijos quedan invisibles; luego `purge_orphans` los elimina.
* Activacion monotona: el puntero solo avanza si `published_at` del puntero <= el de la corrida nueva, y
  solo lo intenta quien acaba de completar con exito.
"""
from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from .schema import SCHEMA_VERSION, validate_doc

LEASE_SECONDS = 60   # igual al lease del trabajo: un worker muerto libera ambos en ~1 minuto
BATCH = 5000
CHILD_COLLECTIONS = ("forecasts", "recommendations", "backtests")


class PublishInProgressError(RuntimeError):
    """Otra publicacion con la misma clave sigue en staging con lease vigente."""


class PublishValidationError(RuntimeError):
    """La validacion de conteos/coherencia fallo antes de completar."""


class LostOwnership(RuntimeError):
    """El intento ya no es el dueno de la corrida: se detiene sin escribir ni limpiar nada ajeno."""


@dataclass(frozen=True)
class Attempt:
    run_id: str
    children_id: str
    owner: str
    generation: int


def utcnow() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _aware(t: datetime) -> datetime:
    return t if t.tzinfo else t.replace(tzinfo=UTC)


def children_id_for(run_id: str, generation: int) -> str:
    return f"{run_id}~g{generation}"


def claim_run(db, run_doc: dict, now: datetime | None = None, lease_seconds: int = LEASE_SECONDS):
    """('existing', run) si ya esta completed/superseded; ('claimed', Attempt) si este intento es el dueno.
    Lanza PublishInProgressError si otro intento vivo es el dueno."""
    t = _aware(now or utcnow())
    key, run_id = run_doc["idempotency_key"], run_doc["run_id"]
    lease = t + timedelta(seconds=lease_seconds)
    for _ in range(4):
        cur = db.runs.find_one({"idempotency_key": key})
        if cur is None:
            owner = uuid.uuid4().hex
            try:
                db.runs.insert_one({**run_doc, "owner": owner, "generation": 1, "attempts": 1,
                                    "lease_expires_at": lease})
                return "claimed", Attempt(run_id, children_id_for(run_id, 1), owner, 1)
            except DuplicateKeyError:
                continue
        if cur["status"] in ("completed", "superseded"):
            return "existing", cur
        expired = cur.get("lease_expires_at") is None or _aware(cur["lease_expires_at"]) <= t
        if cur["status"] == "staging" and not expired:
            raise PublishInProgressError("hay una publicacion en curso con la misma clave")
        owner = uuid.uuid4().hex
        # CAS sobre el lease LEIDO: si el dueno renovo entre la lectura y este paso, `lease_expires_at` ya no coincide
        # (None coincide con ausente/nulo) y no se le desplaza.
        got = db.runs.find_one_and_update(
            {"_id": cur["_id"], "status": cur["status"], "generation": cur.get("generation", 0),
             "lease_expires_at": cur.get("lease_expires_at")},
            {"$set": {**{k: v for k, v in run_doc.items() if k not in ("run_id", "status")}, "status": "staging",
                      "owner": owner, "lease_expires_at": lease, "error": None},
             "$inc": {"generation": 1, "attempts": 1}}, return_document=ReturnDocument.AFTER)
        if got is not None:
            return "claimed", Attempt(run_id, children_id_for(run_id, got["generation"]), owner, got["generation"])
    raise PublishInProgressError("no se pudo reservar la corrida")


def guard(db, attempt: Attempt, *, extra: Callable[[], None] | None = None, now: datetime | None = None,
          lease_seconds: int = LEASE_SECONDS) -> None:
    """Comprueba y RENUEVA la propiedad (CAS); lanza LostOwnership si otro intento la tomo. `extra` permite
    encadenar el latido del trabajo de la cola."""
    t = _aware(now or utcnow())
    res = db.runs.update_one({"run_id": attempt.run_id, "status": "staging", "owner": attempt.owner,
                              "generation": attempt.generation},
                             {"$set": {"lease_expires_at": t + timedelta(seconds=lease_seconds)}})
    if res.matched_count != 1:
        raise LostOwnership(attempt.run_id)
    if extra is not None:
        extra()


def stamp(attempt: Attempt, prepared: dict[str, list]) -> None:
    """Asigna el espacio de hijos del intento (run_id = children_id; backtest_id propio del intento)."""
    for name, docs in prepared.items():
        for d in docs:
            d["run_id"] = attempt.children_id
            if name == "backtests":
                d["backtest_id"] = f"bt-{attempt.children_id}"


def insert_children(db, attempt: Attempt, prepared: dict[str, list], g: Callable[[], None], hook=None) -> None:
    for name in CHILD_COLLECTIONS:
        docs = prepared.get(name, [])
        for i in range(0, len(docs), BATCH):
            g()                                    # propiedad comprobada antes de CADA lote
            chunk = docs[i:i + BATCH]
            for d in chunk[:1] + chunk[-1:]:
                validate_doc(name, d)
            db[name].insert_many(chunk, ordered=False)
        if hook:
            hook(name)


def delete_own_children(db, attempt: Attempt) -> None:
    """Borra SOLO los hijos del propio intento (un obsoleto solo puede tocar su espacio, nunca el de otro)."""
    for name in CHILD_COLLECTIONS:
        db[name].delete_many({"run_id": attempt.children_id})


def complete_run(db, attempt: Attempt, fields: dict, now: datetime | None = None) -> datetime:
    """CAS de promocion: unico paso que hace visibles los hijos. LostOwnership si el intento ya no es dueno."""
    published_at = _aware(now or utcnow())
    res = db.runs.update_one(
        {"run_id": attempt.run_id, "status": "staging", "owner": attempt.owner, "generation": attempt.generation},
        {"$set": {**fields, "status": "completed", "children_ref": attempt.children_id,
                  "published_at": published_at, "error": None, "schema_version": SCHEMA_VERSION},
         "$unset": {"lease_expires_at": ""}})
    if res.matched_count != 1:
        raise LostOwnership(attempt.run_id)
    return published_at


def activate_monotonic(db, run_id: str, published_at: datetime, now: datetime | None = None) -> bool:
    """Mueve el puntero activo solo hacia adelante (published_at del puntero <= el nuevo)."""
    if db.runs.find_one({"run_id": run_id, "status": "completed"}, {"_id": 1}) is None:
        raise PublishValidationError("solo una corrida completed puede ser activa")
    t = _aware(now or utcnow())
    new = {"run_id": run_id, "published_at": published_at, "updated_at": t}
    res = db.run_pointer.update_one(
        {"_id": "active", "$or": [{"published_at": {"$lte": published_at}}, {"published_at": {"$exists": False}}]},
        {"$set": new})
    if res.matched_count == 1:
        return True
    try:
        db.run_pointer.insert_one({"_id": "active", **new})
        return True
    except DuplicateKeyError:
        return False               # un puntero mas nuevo ya existe: no se retrocede


def fail_attempt(db, attempt: Attempt, stage: str, exc: Exception, now: datetime | None = None) -> bool:
    """Marca failed SOLO si el intento sigue siendo el dueno; limpia solo sus hijos. Devuelve si lo marco."""
    t = _aware(now or utcnow())
    try:
        delete_own_children(db, attempt)
    except Exception:  # noqa: BLE001, S110 - limpieza best-effort; purge_orphans repite
        pass
    res = db.runs.update_one(
        {"run_id": attempt.run_id, "status": "staging", "owner": attempt.owner, "generation": attempt.generation},
        {"$set": {"status": "failed", "error": {"code": "PUBLICACION_FALLIDA", "stage": stage,
                                                "type": type(exc).__name__, "at": t},
                  "lease_expires_at": None}})
    return res.matched_count == 1


ABANDONED_CODE = "INTENTO_ABANDONADO"


def reserve_abandoned(db, run_id: str, generation: int, t: datetime) -> bool:
    """Reserva atomica de una generacion en staging con lease VENCIDO antes de borrar sus hijos.

    CAS sobre (run_id, status=staging, generation, lease vencido o ausente): pasa la corrida a `failed` (se conserva
    el documento con su motivo). Desde ese instante `guard`, `complete_run`, `insert_children` y la activacion del
    intento antiguo fallan (exigen status=staging + owner). Si el dueno renovo el lease o promovio la corrida antes,
    el CAS no coincide y los hijos se conservan. Devuelve si esta llamada hizo la reserva."""
    res = db.runs.update_one(
        {"run_id": run_id, "status": "staging", "generation": generation,
         "$or": [{"lease_expires_at": None}, {"lease_expires_at": {"$lte": t}}]},
        {"$set": {"status": "failed", "owner": None, "lease_expires_at": None,
                  "error": {"code": ABANDONED_CODE, "stage": "mantenimiento", "at": t,
                            "message": "intento sin latido; reservado por el mantenimiento antes de limpiar"}}})
    return res.matched_count == 1


def purge_orphans(db, now: datetime | None = None) -> dict:
    """Elimina hijos de intentos muertos. Un intento todavia reclamable (staging de su generacion) solo se limpia
    tras `reserve_abandoned`; el resto (generacion superada, failed, sin corrida) ya no puede renovarse ni promoverse.
    Nunca toca `children_ref`, corridas completed/superseded ni las historicas (sin sufijo ~g). Idempotente."""
    t = _aware(now or utcnow())
    removed: dict = {}
    ids = set()
    for name in CHILD_COLLECTIONS:
        ids |= {i for i in db[name].distinct("run_id") if isinstance(i, str) and "~g" in i}
    for cid in sorted(ids):
        base, _, gen = cid.rpartition("~g")
        run = db.runs.find_one({"run_id": base}, {"children_ref": 1, "status": 1, "generation": 1,
                                                  "lease_expires_at": 1})
        if run is not None:
            if run.get("children_ref") == cid:
                continue
            if run.get("status") == "staging" and run.get("generation") == int(gen):
                lease = run.get("lease_expires_at")
                if lease is not None and _aware(lease) > t:
                    continue                       # intento vivo
                if not reserve_abandoned(db, base, int(gen), t):
                    continue                       # renovo o promovio primero: se conserva
        for name in CHILD_COLLECTIONS:
            n = db[name].delete_many({"run_id": cid}).deleted_count
            if n:
                removed[name] = removed.get(name, 0) + n
    # corridas staging con lease vencido y sin hijos: se reservan (quedan failed con su motivo; no se borran)
    for run in db.runs.find({"status": "staging", "$or": [{"lease_expires_at": None},
                                                          {"lease_expires_at": {"$lte": t}}]},
                            {"run_id": 1, "generation": 1}):
        if reserve_abandoned(db, run["run_id"], run.get("generation", 0), t):
            removed["runs_abandonadas"] = removed.get("runs_abandonadas", 0) + 1
    return removed
