"""Reserva durable de UNA fuente por mes durante la importacion (T10R R09). Mongo standalone, sin transacciones.

El chequeo `approved_sources` previo a `import_workbook` no reserva nada: dos archivos distintos del mismo mes lo
pasan a la vez y ambos escriben. Esta reserva lo reemplaza como exclusion ANTES de cualquier escritura:

* coleccion `month_reservations`, `_id` = "YYYY-MM" (el indice unico de `_id` hace que solo un archivo la obtenga);
* documento: `sha256` (la fuente duena), `owner` + `generation` (fencing), `lease_expires_at`, `state`:
  `importing` (escribiendo, con lease), `partial` (hubo escrituras y el intento fallo: el mes NO se libera para otra
  fuente como si estuviera vacio), `approved` (importacion completada y sin conflictos);
* otra fuente (sha distinto) con la reserva en cualquier estado => `MonthReserved` (queda rechazada/en cuarentena con
  un motivo legible; no escribe ninguna fila);
* la MISMA fuente puede retomarla (reintento, reinicio): CAS sobre el lease leido, `generation + 1`; si el dueno
  renovo entre la lectura y el CAS, no se le desplaza (`ImportInProgress`);
* el dueno desplazado pierde la propiedad: `Fence.check` (renovacion con CAS por owner+generation) lanza
  `LostReservation` antes de cada lote de escritura y antes de finalizar, de modo que no sigue escribiendo ni
  aprueba la fuente;
* un fallo ANTES de la primera escritura libera la reserva (el mes sigue vacio); un fallo despues la deja `partial`;
  una importacion con conflictos abiertos libera (la fuente no queda aprobada, como antes de T10R).
Remediacion de una reserva `partial` (solo CLI privilegiada, fuera de la API): `release_month`.
"""
from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from pymongo.errors import DuplicateKeyError

COLLECTION = "month_reservations"
LEASE_SECONDS = 120


class MonthReserved(RuntimeError):
    """El mes pertenece a otra fuente (importando, parcial o aprobada): no se escribe nada."""

    def __init__(self, month: str, holder_state: str):
        self.month, self.holder_state = month, holder_state
        super().__init__(f"mes {month} reservado por otra fuente ({holder_state})")


class ImportInProgress(RuntimeError):
    """La misma fuente ya se esta importando por otro intento con lease vigente: reintentar mas tarde."""


class LostReservation(RuntimeError):
    """Este intento ya no es el dueno de la reserva del mes: debe detenerse sin escribir ni aprobar."""


@dataclass(frozen=True)
class Reservation:
    month: str
    sha256: str
    owner: str
    generation: int


def _now(now: datetime | None) -> datetime:
    t = now or datetime.now(UTC)
    return t if t.tzinfo else t.replace(tzinfo=UTC)


def _aware(t: datetime | None) -> datetime | None:
    return None if t is None else (t if t.tzinfo else t.replace(tzinfo=UTC))


def reserve(db, month: str, sha256: str, *, lease_seconds: int = LEASE_SECONDS, now: datetime | None = None,
            after_read: Callable[[], None] | None = None) -> Reservation:
    """Obtiene (o retoma, si es la misma fuente) la reserva del mes. `after_read` solo existe para pruebas."""
    t = _now(now)
    lease = t + timedelta(seconds=lease_seconds)
    for _ in range(4):
        owner = uuid.uuid4().hex
        try:
            db[COLLECTION].insert_one({"_id": month, "sha256": sha256, "owner": owner, "generation": 1,
                                       "state": "importing", "lease_expires_at": lease, "created_at": t,
                                       "updated_at": t})
            return Reservation(month, sha256, owner, 1)
        except DuplicateKeyError:
            pass
        cur = db[COLLECTION].find_one({"_id": month})
        if cur is None:
            continue
        if after_read is not None:
            after_read()
        if cur["sha256"] != sha256:
            raise MonthReserved(month, cur.get("state", "importing"))
        held = cur.get("state") == "importing" and _aware(cur.get("lease_expires_at")) is not None \
            and _aware(cur["lease_expires_at"]) > t
        if held:
            raise ImportInProgress(f"la fuente del mes {month} ya se esta importando")
        got = db[COLLECTION].find_one_and_update(
            {"_id": month, "sha256": sha256, "generation": cur["generation"], "state": cur.get("state"),
             "lease_expires_at": cur.get("lease_expires_at")},                  # CAS sobre el lease LEIDO
            {"$set": {"owner": owner, "state": "importing", "lease_expires_at": lease, "updated_at": t},
             "$inc": {"generation": 1}}, return_document=True)
        if got is not None:
            return Reservation(month, sha256, owner, got["generation"])
        # cambio entre la lectura y el CAS: se vuelve a leer (puede haber renovado el dueno => ImportInProgress)
    raise ImportInProgress(f"no se pudo reservar el mes {month}")


def _owned(r: Reservation) -> dict:
    return {"_id": r.month, "sha256": r.sha256, "owner": r.owner, "generation": r.generation}


def renew(db, r: Reservation, *, lease_seconds: int = LEASE_SECONDS, now: datetime | None = None) -> None:
    t = _now(now)
    res = db[COLLECTION].update_one({**_owned(r), "state": "importing"},
                                    {"$set": {"lease_expires_at": t + timedelta(seconds=lease_seconds),
                                              "updated_at": t}})
    if res.matched_count != 1:
        raise LostReservation(r.month)


def finish(db, r: Reservation, state: str, *, now: datetime | None = None) -> None:
    """`approved` | `partial`: CAS por propietario; sin lease. LostReservation si otro intento la retomo."""
    assert state in ("approved", "partial")
    res = db[COLLECTION].update_one({**_owned(r)}, {"$set": {"state": state, "lease_expires_at": None,
                                                              "updated_at": _now(now)}})
    if res.matched_count != 1:
        raise LostReservation(r.month)


def release(db, r: Reservation) -> bool:
    """Libera (borra) la reserva SOLO si seguimos siendo el dueno. True si la libero."""
    return db[COLLECTION].delete_one(_owned(r)).deleted_count == 1


def release_month(db, month: str, sha256: str) -> bool:
    """Remediacion privilegiada (CLI, nunca API): libera una reserva `partial`/vencida de esa fuente tras decidir
    como se reconstruye el mes (ver docs/REMEDIACION_FUENTES.md). No toca un `importing` con lease vigente."""
    t = _now(None)
    return db[COLLECTION].delete_one(
        {"_id": month, "sha256": sha256,
         "$or": [{"state": "partial"}, {"state": "importing", "lease_expires_at": {"$lte": t}}]}).deleted_count == 1


class Fence:
    """Valla de escritura que `import_workbook` consulta antes de cada lote: renueva la reserva (CAS) y, si se
    indico, comprueba tambien la propiedad del trabajo de la cola. `wrote` indica si ya hubo escrituras."""

    def __init__(self, db, reservation: Reservation, *, lease_seconds: int = LEASE_SECONDS,
                 extra: Callable[[], None] | None = None):
        self.db, self.reservation, self.lease_seconds, self.extra = db, reservation, lease_seconds, extra
        self.wrote = False

    def check(self, *, write: bool = False) -> None:
        if write:
            self.wrote = True
        if self.extra is not None:
            self.extra()
        renew(self.db, self.reservation, lease_seconds=self.lease_seconds)
