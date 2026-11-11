"""Utilidades comunes de los repositorios de lectura (T08 §1, §3).

Las consultas se construyen en el servidor con valores validados y tipados; ningun
parametro del cliente se interpreta como objeto o filtro Mongo.
"""
from __future__ import annotations

import re
from datetime import UTC, date, datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import Depends, Query, Request
from pymongo.database import Database

from backend.app.auth.deps import CurrentUser, require_user
from backend.app.db import get_db
from backend.app.errors import ApiError

Db = Annotated[Database, Depends(get_db)]
User = Annotated[CurrentUser, Depends(require_user)]
Page = Annotated[int, Query(ge=1, le=100000)]
PageSize = Annotated[int, Query(ge=1, le=200)]

LAST_ALLOWED_DATE = date(2026, 10, 21)
# T11 §1: unica excepcion, solo al CONSULTAR una corrida kind=final_evaluation (nunca para otros tipos).
FINAL_KIND = "final_evaluation"
FINAL_FIRST_DATE = date(2026, 8, 1)
FINAL_LAST_DATE = date(2026, 8, 21)
FINAL_UNAVAILABLE_REASON = "RECOMENDACION_NO_VALIDADA_PARA_ESTE_ORIGEN"
FINAL_WARNINGS = [
    "WAPE no es exactitud: 0,78 significa error absoluto agregado equivalente al 78 % del volumen observado",
    "Categoría = suma de unidades base heterogéneas",
    "Un solo bloque de 21 días; sin inferencia de ganador",
    "Evaluación sobre datos históricos; no pronostica octubre",
]
MAX_RANGE_DAYS = 400
RUN_LABEL = "Corrida histórica de desarrollo al 10/07/2026"
SIM_LABEL = "Inventario simulado con supuestos; no corresponde al inventario real de la empresa"

SKU_RE = r"^[A-Za-z0-9._-]{1,32}$"
RUN_ID_RE = r"^[A-Za-z0-9._-]{1,64}$"
ALMACEN_RE = r"^[A-Za-z0-9]{1,10}$"
MES_RE = r"^\d{4}-(0[1-9]|1[0-2])$"
HEX32_RE = r"^[0-9a-f]{32}$"
_SAFE_TEXT = re.compile(r"^[^\x00-\x1f{}$\[\]]{1,100}$")


def invalid(message: str, details: list | None = None) -> ApiError:
    return ApiError(422, "ENTRADA_INVALIDA", message, details)


def strict_params(*allowed: str):
    """Dependencia: rechaza parametros no declarados, repetidos o con '$' (422)."""
    allowed_set = set(allowed) | {"page", "page_size"}

    def _check(request: Request) -> None:
        keys = [k for k, _ in request.query_params.multi_items()]
        for k in keys:
            if k not in allowed_set or "$" in k:
                raise invalid("Parámetro no permitido.", [{"campo": k[:40], "motivo": "no permitido"}])
        if len(keys) != len(set(keys)):
            raise invalid("Parámetro repetido.")
    return _check


def safe_text(value: str | None, field: str) -> str | None:
    """Texto de filtro: sin llaves, corchetes ni '$' (nada de operadores Mongo)."""
    if value is None:
        return None
    if not _SAFE_TEXT.match(value):
        raise invalid("Valor de filtro no permitido.", [{"campo": field, "motivo": "caracteres no permitidos"}])
    return value


def check_sort(sort: str | None, allowed: dict[str, list[tuple[str, int]]], default: str) -> list:
    key = sort or default
    if key not in allowed:
        raise invalid("Campo de orden no permitido.", [{"campo": "sort", "motivo": "fuera de la lista"}])
    return allowed[key]


def check_dates(frm: date | None, to: date | None) -> None:
    for d in (frm, to):
        if d is not None and d > LAST_ALLOWED_DATE:
            raise ApiError(422, "FUERA_DE_RANGO", "La fecha solicitada excede el último día de datos permitido.")
    if frm and to:
        if frm > to:
            raise invalid("El rango de fechas es inválido (from > to).")
        if (to - frm).days > MAX_RANGE_DAYS:
            raise invalid(f"El rango máximo es de {MAX_RANGE_DAYS} días.")


def is_final(run: dict | None) -> bool:
    return bool(run) and run.get("kind") == FINAL_KIND


def check_dates_for_run(run: dict, frm: date | None, to: date | None) -> None:
    """Fechas de consulta ya resuelta la corrida. Para `final_evaluation` se admite hasta 2026-08-21;
    para cualquier otro tipo rige la barrera general (agosto reservado)."""
    if not is_final(run):
        check_dates(frm, to)
        return
    for d in (frm, to):
        if d is not None and d > FINAL_LAST_DATE:
            raise invalid(f"Para la evaluación final la fecha máxima es {FINAL_LAST_DATE.isoformat()}.")
    if frm and to:
        if frm > to:
            raise invalid("El rango de fechas es inválido (from > to).")
        if (to - frm).days > MAX_RANGE_DAYS:
            raise invalid(f"El rango máximo es de {MAX_RANGE_DAYS} días.")


def iso_utc(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(UTC)
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")
    return str(value)


def today_lima() -> date:
    return datetime.now(ZoneInfo("America/Lima")).date()


def active_run_id(db) -> str | None:
    ptr = db.run_pointer.find_one({"_id": "active"})
    if ptr:
        ok = db.runs.find_one({"run_id": ptr["run_id"], "status": "completed"}, {"_id": 1})
        if ok:
            return ptr["run_id"]
    last = db.runs.find_one({"status": "completed"}, {"run_id": 1}, sort=[("published_at", -1)])
    return last["run_id"] if last else None


READABLE = ["completed", "superseded"]


def completed_run(db, run_id: str | None) -> dict:
    """Corrida legible (la activa por defecto, que siempre es completed). Una corrida `superseded` se puede
    consultar por id explicito (historial) pero se rotula como sustituida; staging/failed -> 404."""
    rid = run_id or active_run_id(db)
    run = db.runs.find_one({"run_id": rid, "status": {"$in": READABLE}}, {"_id": 0}) if rid else None
    if run is None:
        raise ApiError(404, "NO_ENCONTRADO", "Corrida no encontrada.")
    return run


def run_header(db, run: dict) -> dict:
    cutoff = date.fromisoformat(run["cutoff"])
    return {"run_id": run["run_id"], "run_label": run.get("run_label", RUN_LABEL), "cutoff": run["cutoff"],
            "status": run.get("status", "completed"),
            "generated_at": iso_utc(run.get("generated_at")), "published_at": iso_utc(run.get("published_at")),
            "age_days_at_view": (today_lima() - cutoff).days,
            "is_active": run["run_id"] == active_run_id(db),
            "superseded_by": run.get("superseded_by"), "quality_issue": run.get("quality_issue"),
            "kind": run.get("kind"), "target_start": run.get("target_start"), "target_end": run.get("target_end"),
            "evaluation_period": run.get("evaluation_period"), "warnings": list(FINAL_WARNINGS) if is_final(run) else []}


def child_key(run: dict) -> str:
    """run_id bajo el que estan los hijos visibles: `children_ref` (corridas publicadas con propiedad por
    intento) o el propio run_id (corridas historicas T08)."""
    return run.get("children_ref") or run["run_id"]


def relabel(docs: list, run: dict) -> list:
    """Los hijos guardan el id de su intento; la API siempre expone el run_id publico de la corrida."""
    for d in docs:
        if "run_id" in d:
            d["run_id"] = run["run_id"]
    return docs


def validation_status(run: dict) -> str:
    """Estado de validez de los resultados derivados de la corrida (no se escribe en los hijos)."""
    return "valid" if run.get("status") == "completed" else "superseded_precision_error"


def sim_labels() -> dict:
    return {"provenance": "SYNTHETIC_NOT_REAL_INVENTORY", "disclaimer": SIM_LABEL}
