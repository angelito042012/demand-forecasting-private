"""Presupuesto de intentos de login con reserva ATOMICA en MongoDB (T10 §1; sustituye contar-y-luego-insertar).

Cada clave (usuario+IP, o IP) tiene UN documento {_id, ws, count, expires_at, allowed}. `reserve` es una
unica actualizacion con pipeline de agregacion (find_one_and_update + upsert): MongoDB la aplica de forma
atomica sobre el documento, de modo que N peticiones concurrentes reservan como mucho `limit` cupos por
ventana; las demas reciben `allowed=False` sin incrementar (el contador queda acotado en `limit`).

Semantica:
- el cupo se reserva ANTES de verificar la contrasena: una rafaga no puede validar mas intentos de los
  permitidos aunque lleguen en paralelo;
- un intento fallido conserva su cupo; un login correcto lo devuelve (`refund`), asi la contrasena
  correcta no consume presupuesto y el atacante no gana intentos de adivinacion;
- ventana fija que empieza en la primera reserva y dura `window_seconds`; al expirar el contador se
  reinicia (limite conocido de toda ventana fija: en el cambio de ventana puede haber hasta 2 x limite
  intentos en un intervalo corto; el limite por IP lo acota por otra via);
- Retry-After = tiempo restante de la ventana. Las claves son sha256 con pimienta (sin usuario/IP en claro).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from pymongo import ReturnDocument
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

COLLECTION = "login_budget"


@dataclass(frozen=True)
class Reservation:
    allowed: bool
    count: int
    retry_after: int           # segundos hasta que se libera la ventana (>= 1 si no esta permitido)


def ensure_indexes(db: Database) -> None:
    db[COLLECTION].create_index("expires_at", expireAfterSeconds=0, name="expires_at_ttl")


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def reserve(db: Database, key: str, limit: int, window_seconds: int, now: datetime | None = None) -> Reservation:
    now = _utc(now or datetime.now(UTC))
    since = now - timedelta(seconds=window_seconds)
    epoch = datetime(1970, 1, 1, tzinfo=UTC)
    pipeline = [
        {"$set": {"_expired": {"$lte": [{"$ifNull": ["$ws", epoch]}, since]}}},
        {"$set": {"ws": {"$cond": ["$_expired", now, "$ws"]},
                  "_c0": {"$cond": ["$_expired", 0, {"$ifNull": ["$count", 0]}]}}},
        {"$set": {"allowed": {"$lt": ["$_c0", limit]}}},
        {"$set": {"count": {"$cond": ["$allowed", {"$add": ["$_c0", 1]}, "$_c0"]},
                  "expires_at": {"$add": ["$ws", window_seconds * 1000]}}},
        {"$unset": ["_expired", "_c0"]},
    ]
    for _ in range(3):          # una carrera de upsert simultaneo puede dar DuplicateKey: se reintenta
        try:
            doc = db[COLLECTION].find_one_and_update({"_id": key}, pipeline, upsert=True,
                                                     return_document=ReturnDocument.AFTER)
            break
        except DuplicateKeyError:
            continue
    else:
        raise RuntimeError("no se pudo reservar el presupuesto de login")
    ws = _utc(doc["ws"])
    remaining = (ws + timedelta(seconds=window_seconds) - now).total_seconds()
    return Reservation(bool(doc["allowed"]), int(doc["count"]), max(1, math.ceil(remaining)))


def refund(db: Database, key: str, *, reset: bool = False) -> None:
    """Devuelve un cupo (login correcto). `reset=True` vacia el contador (clave usuario+IP)."""
    if reset:
        db[COLLECTION].delete_one({"_id": key})
        return
    db[COLLECTION].update_one({"_id": key, "count": {"$gt": 0}}, {"$inc": {"count": -1}})
