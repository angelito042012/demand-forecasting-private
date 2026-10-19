"""Cola durable de trabajos en MongoDB standalone (T10 §2; sin transacciones multidocumento, sin Redis).

Cada trabajo es UN documento; todas las transiciones son operaciones atomicas sobre ese documento
(find_one_and_update / update_one con filtro de propiedad = compare-and-set):

  queued --claim--> running --complete--> completed
                       |  \\--fail(retryable, intentos < max)--> queued (available_at = ahora + backoff)
                       |   \\-fail(permanente o sin intentos)--> failed
                       \\--lease vencido (worker muerto)--> otro worker lo reclama (generation + 1)

Propiedad y fencing: cada reclamo fija `owner` (token aleatorio) y `generation` (entero que solo crece). Toda
operacion posterior (`heartbeat`, `complete`, `fail`, y los efectos laterales protegidos por `guard`) exige
{owner, generation, status=running}; si otro worker tomo el trabajo, el antiguo recibe LostOwnership y no
puede completar, fallar, renovar ni activar nada. `heartbeat` renueva el lease.

Idempotencia: `idempotency_key` unico. Encolar dos veces la misma entrada devuelve el mismo trabajo.
Errores de datos permanentes (`retryable=False`) pasan a failed sin reintentos; los transitorios reintentan
hasta `max_attempts` con backoff exponencial acotado. El progreso lo escriben los handlers con etapas y conteos
reales (`progress`), nunca porcentajes inventados.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

JOB_TYPES = ("import_excel", "generate_run", "generate_plan")
STATUSES = ("queued", "running", "completed", "failed")
COLLECTION = "jobs"
DEFAULT_LEASE_SECONDS = 60
MAX_BACKOFF_SECONDS = 600


class LostOwnership(RuntimeError):
    """Este worker ya no es el dueno del trabajo (lo tomo otro o ya termino): debe detenerse sin escribir."""


@dataclass(frozen=True)
class Claim:
    job_id: str
    type: str
    owner: str
    generation: int
    attempt: int
    input: dict
    worker_id: str


def _now(now: datetime | None) -> datetime:
    value = now or datetime.now(UTC)
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def ensure_indexes(db) -> None:
    c = db[COLLECTION]
    c.create_index("job_id", unique=True, name="uq_job_id")
    c.create_index("idempotency_key", unique=True, name="uq_job_idempotency_key")
    c.create_index([("status", 1), ("available_at", 1), ("created_at", 1)], name="ix_job_claim")
    c.create_index([("status", 1), ("lease_expires_at", 1)], name="ix_job_lease")
    c.create_index([("type", 1), ("created_at", -1)], name="ix_job_type_created")


def enqueue(db, job_type: str, job_input: dict, idempotency_key: str, created_by: str, *, max_attempts: int = 5,
            public: dict | None = None, now: datetime | None = None) -> tuple[dict, bool]:
    """Encola (o devuelve el existente). `job_input` es interno; `public` es lo que la API puede mostrar."""
    if job_type not in JOB_TYPES:
        raise ValueError(f"tipo de trabajo no permitido: {job_type}")
    if not idempotency_key or len(idempotency_key) > 200:
        raise ValueError("idempotency_key invalida")
    t = _now(now)
    doc = {"job_id": uuid.uuid4().hex, "type": job_type, "status": "queued", "input": job_input,
           "public": public or {}, "idempotency_key": idempotency_key, "created_by": created_by,
           "created_at": t, "updated_at": t, "available_at": t, "attempts": 0, "max_attempts": int(max_attempts),
           "owner": None, "generation": 0, "worker_id": None, "lease_expires_at": None, "heartbeat_at": None,
           "stage": "en cola", "progress": {}, "result": None, "error": None, "schema_version": 1}
    try:
        db[COLLECTION].insert_one(doc)
        return doc, True
    except DuplicateKeyError:
        return db[COLLECTION].find_one({"idempotency_key": idempotency_key}), False


def claim(db, worker_id: str, types: tuple[str, ...] = JOB_TYPES, *, lease_seconds: int = DEFAULT_LEASE_SECONDS,
          now: datetime | None = None) -> Claim | None:
    """Reclama atomicamente el trabajo mas antiguo disponible: en cola, o en ejecucion con lease vencido (worker
    muerto). Cada reclamo cuenta un intento; los que agotaron intentos NO se reclaman (ver `sweep_exhausted`)."""
    t = _now(now)
    flt = {"type": {"$in": list(types)}, "$expr": {"$lt": ["$attempts", "$max_attempts"]},
           "$or": [{"status": "queued", "available_at": {"$lte": t}},
                   {"status": "running", "lease_expires_at": {"$lte": t}}]}
    owner = uuid.uuid4().hex
    doc = db[COLLECTION].find_one_and_update(
        flt, {"$set": {"status": "running", "owner": owner, "worker_id": worker_id, "updated_at": t,
                       "lease_expires_at": t + timedelta(seconds=lease_seconds), "heartbeat_at": t,
                       "started_at": t, "stage": "iniciado", "error": None},
              "$inc": {"generation": 1, "attempts": 1}},
        sort=[("created_at", 1)], return_document=ReturnDocument.AFTER)
    if doc is None:
        return None
    return Claim(doc["job_id"], doc["type"], owner, doc["generation"], doc["attempts"], doc["input"], worker_id)


def _owned(claim: Claim) -> dict:
    return {"job_id": claim.job_id, "owner": claim.owner, "generation": claim.generation, "status": "running"}


def heartbeat(db, claim: Claim, *, lease_seconds: int = DEFAULT_LEASE_SECONDS, stage: str | None = None,
              progress: dict | None = None, now: datetime | None = None) -> None:
    """Renueva el lease y registra etapa/conteos reales. CAS por propietario; si lo perdio -> LostOwnership."""
    t = _now(now)
    upd = {"lease_expires_at": t + timedelta(seconds=lease_seconds), "heartbeat_at": t, "updated_at": t}
    if stage is not None:
        upd["stage"] = stage
    if progress is not None:
        upd["progress"] = progress
    if db[COLLECTION].update_one(_owned(claim), {"$set": upd}).matched_count != 1:
        raise LostOwnership(claim.job_id)


def still_owner(db, claim: Claim) -> bool:
    return db[COLLECTION].count_documents(_owned(claim), limit=1) == 1


def complete(db, claim: Claim, result: dict, *, now: datetime | None = None) -> None:
    t = _now(now)
    res = db[COLLECTION].update_one(_owned(claim), {"$set": {
        "status": "completed", "result": result, "stage": "completado", "finished_at": t, "updated_at": t,
        "lease_expires_at": None, "error": None}})
    if res.matched_count != 1:
        raise LostOwnership(claim.job_id)


def fail(db, claim: Claim, code: str, message: str, *, retryable: bool, backoff_seconds: int = 5,
         now: datetime | None = None) -> str:
    """Falla el intento. Devuelve el estado resultante: `queued` (reintento con backoff) o `failed`."""
    t = _now(now)
    cur = db[COLLECTION].find_one(_owned(claim), {"attempts": 1, "max_attempts": 1})
    if cur is None:
        raise LostOwnership(claim.job_id)
    err = {"code": code, "message": message[:300], "retryable": bool(retryable), "attempt": cur["attempts"], "at": t}
    if retryable and cur["attempts"] < cur["max_attempts"]:
        wait = min(MAX_BACKOFF_SECONDS, backoff_seconds * (2 ** (cur["attempts"] - 1)))
        upd = {"status": "queued", "owner": None, "lease_expires_at": None, "available_at": t + timedelta(seconds=wait),
               "stage": "reintento programado", "error": err, "updated_at": t}
        state = "queued"
    else:
        upd = {"status": "failed", "owner": None, "lease_expires_at": None, "stage": "fallido", "error": err,
               "finished_at": t, "updated_at": t}
        state = "failed"
    if db[COLLECTION].update_one(_owned(claim), {"$set": upd}).matched_count != 1:
        raise LostOwnership(claim.job_id)
    return state


def sweep_exhausted(db, *, now: datetime | None = None) -> int:
    """Pasa a failed los trabajos en ejecucion con lease vencido que ya agotaron intentos (nadie los reclamara)."""
    t = _now(now)
    res = db[COLLECTION].update_many(
        {"status": "running", "lease_expires_at": {"$lte": t}, "$expr": {"$gte": ["$attempts", "$max_attempts"]}},
        {"$set": {"status": "failed", "owner": None, "lease_expires_at": None, "stage": "fallido", "finished_at": t,
                  "updated_at": t, "error": {"code": "WORKER_PERDIDO", "message": "el trabajo agoto sus intentos "
                                             "(el proceso se interrumpio repetidamente)", "retryable": False, "at": t}}})
    return res.modified_count


PUBLIC_FIELDS = ("job_id", "type", "status", "stage", "progress", "result", "error", "created_by", "created_at",
                 "updated_at", "started_at", "finished_at", "attempts", "max_attempts", "public")


def public_job(doc: dict) -> dict:
    """Vista saneada para la API: sin entrada interna, propietarios, rutas privadas ni claves."""
    out = {k: doc.get(k) for k in PUBLIC_FIELDS}
    if out.get("error"):
        out["error"] = {k: out["error"].get(k) for k in ("code", "message", "retryable", "attempt", "at")}
    return out
