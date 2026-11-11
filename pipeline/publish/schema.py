"""Esquema de las colecciones publicadas (T08 §4): indices y validacion de documentos.

La migracion es NO destructiva e idempotente: solo crea indices con nombre fijo; nunca
borra ni modifica colecciones existentes (`sales`, `credit_notes`, `imports`, `import_*`
quedan intactas). Si un indice del mismo nombre existe con otra definicion, PyMongo lo
rechaza y la migracion se detiene sin alterarlo.
"""
from __future__ import annotations

from pymongo import ASCENDING

SCHEMA_VERSION = 1
KIND = "historical_development"
RUN_LABEL = "Corrida histórica de desarrollo al 10/07/2026"
GENERATED_KIND = "generated_baseline"
FINAL_KIND = "final_evaluation"
LAST_HISTORIC_DATE = "2026-09-30"      # fecha objetivo maxima de las corridas historica y generada
FINAL_FIRST_DATE, FINAL_LAST_DATE = "2026-08-01", "2026-08-21"   # solo la corrida final_evaluation (T11 §1)
GENERATED_LABEL = "Corrida de desarrollo generada por la aplicación con origen {origin}"
PROVENANCE_SIM = "SYNTHETIC_NOT_REAL_INVENTORY"
PROVENANCE_OBS = "OBSERVED_EXCEL"
SIM_LABEL = "Inventario simulado con supuestos; no corresponde al inventario real de la empresa"
RUN_STATUSES = ("staging", "completed", "failed", "superseded")
READABLE_STATUSES = ("completed", "superseded")
QUALITY_ISSUES = {
    "R05_PRECISION_RECOMENDACIONES": (
        "Las recomendaciones de esta corrida se calcularon con una media redondeada del CSV histórico "
        "(error de precisión): algunos objetivos y pedidos quedaron inflados en una unidad. Fue sustituida "
        "por una corrida corregida con señales exactas; no use sus pedidos."),
}

_ASC = ASCENDING
INDEXES: dict[str, list[tuple[list[tuple[str, int]], dict]]] = {
    "runs": [
        ([("run_id", _ASC)], {"unique": True, "name": "uq_run_id"}),
        ([("idempotency_key", _ASC)], {"unique": True, "name": "uq_idempotency_key"}),
        ([("status", _ASC), ("cutoff", _ASC)], {"name": "ix_status_cutoff"}),
        ([("fingerprint", _ASC)], {"name": "ix_fingerprint"}),
    ],
    "forecasts": [
        ([("run_id", _ASC), ("level", _ASC), ("entity_id", _ASC), ("target_date", _ASC)],
         {"unique": True, "name": "uq_run_level_entity_date"}),
        ([("run_id", _ASC), ("level", _ASC), ("categoria", _ASC), ("target_date", _ASC)],
         {"name": "ix_run_level_cat_date"}),
        ([("run_id", _ASC), ("level", _ASC), ("sku", _ASC)], {"name": "ix_run_level_sku"}),
    ],
    "recommendations": [
        ([("run_id", _ASC), ("sku", _ASC), ("almacen", _ASC)],
         {"unique": True, "name": "uq_run_sku_almacen"}),
        ([("run_id", _ASC), ("categoria", _ASC)], {"name": "ix_run_categoria"}),
        ([("run_id", _ASC), ("status", _ASC), ("order_qty", _ASC)], {"name": "ix_run_status_qty"}),
    ],
    "backtests": [
        ([("backtest_id", _ASC)], {"unique": True, "name": "uq_backtest_id"}),
        ([("run_id", _ASC)], {"name": "ix_run_id"}),
    ],
}


class SchemaError(ValueError):
    """Documento que no cumple el esquema de publicacion."""


def ensure_schema(db) -> list[str]:
    """Crea los indices que falten. Devuelve los nombres garantizados (idempotente)."""
    names: list[str] = []
    for coll, specs in INDEXES.items():
        for keys, opts in specs:
            names.append(f"{coll}.{db[coll].create_index(keys, **opts)}")
    return names


_REQUIRED: dict[str, dict[str, type | tuple]] = {
    "runs": {"run_id": str, "status": str, "kind": str, "run_label": str, "idempotency_key": str,
             "fingerprint": str, "cutoff": str, "origin": str, "target_start": str, "target_end": str,
             "horizon_days": int, "method": dict, "sources": list, "artifacts": list, "code": dict,
             "schema_version": int},
    "forecasts": {"run_id": str, "level": str, "entity_id": str, "categoria": str, "target_date": str,
                  "h": int, "pred": dict, "evaluable": bool, "provenance": str, "schema_version": int},
    "recommendations": {"run_id": str, "scenario_id": str, "provenance": str, "sku": str, "almacen": str,
                        "status": str, "categoria": str, "explanation_steps": list,
                        "schema_version": int},
    "backtests": {"backtest_id": str, "run_id": str, "kind": str, "predictive": dict,
                  "simulation": list, "selection": dict, "coverage": dict, "assumptions": dict,
                  "disclaimer": str, "scenario_id": str, "provenance": str, "schema_version": int},
}
_NUM_NULL_FIELDS = ("on_hand", "in_transit", "position", "mean_28", "forecast_14d", "safety",
                    "target", "order_qty", "unit_cost_assumed", "order_value_assumed")
_EXACT_FIELDS = ("sum_28", "days_28", "mean_28_exact", "target_raw_exact", "signals")


def validate_doc(coll: str, doc: dict) -> None:
    """Valida campos obligatorios y reglas del contrato; lanza SchemaError."""
    for field, typ in _REQUIRED[coll].items():
        if field not in doc or not isinstance(doc[field], typ) or (typ is int and isinstance(doc[field], bool)):
            raise SchemaError(f"{coll}: campo '{field}' ausente o con tipo invalido")
    if doc["schema_version"] != SCHEMA_VERSION:
        raise SchemaError(f"{coll}: schema_version inesperada")
    if coll == "runs" and doc["status"] not in RUN_STATUSES:
        raise SchemaError("runs: status invalido")
    if coll == "runs" and doc["kind"] == GENERATED_KIND:
        counts = doc.get("counts")
        if not isinstance(counts, dict) or counts.get("backtests") != 0:
            raise SchemaError("runs: una corrida generada no lleva backtests (counts.backtests debe ser 0)")
        if doc["method"].get("chosen") != "promedio_28":
            raise SchemaError("runs: metodo elegido de la corrida generada debe ser promedio_28")
    if coll == "runs" and doc["kind"] == FINAL_KIND:
        counts = doc.get("counts")
        if not isinstance(counts, dict) or counts.get("recommendations") != 0 or counts.get("backtests") != 1:
            raise SchemaError("runs: la evaluacion final lleva 0 recomendaciones y 1 backtest")
        if doc["method"].get("chosen") != "promedio_28" or doc["method"].get("rf_declared_winner") is not False:
            raise SchemaError("runs: la evaluacion final conserva promedio_28 y no declara ganador al RF")
        if doc["target_end"] > FINAL_LAST_DATE:
            raise SchemaError("runs: la evaluacion final no pasa de 2026-08-21")
    if coll == "forecasts":
        if doc["level"] not in ("sku", "categoria"):
            raise SchemaError("forecasts: level invalido")
        if set(doc["pred"]) != {"promedio_28", "rf_categoria_distribuido", "cero"}:
            raise SchemaError("forecasts: metodos de pred incompletos")
        if doc.get("run_kind") == GENERATED_KIND:
            # corrida generada: sin observaciones (no son cero) y comparador opcional (None = no disponible)
            if doc.get("observed") is not None or doc["evaluable"] is not False:
                raise SchemaError("forecasts: una corrida generada no admite observed ni evaluable=true")
            for k, v in doc["pred"].items():
                if v is None and k == "rf_categoria_distribuido":
                    continue
                if isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0:
                    raise SchemaError("forecasts: pred no numerica o negativa")
        elif any(not isinstance(v, (int, float)) or v < 0 for v in doc["pred"].values()):
            raise SchemaError("forecasts: pred no numerica o negativa")
        if doc.get("run_kind") == FINAL_KIND:
            if not FINAL_FIRST_DATE <= doc["target_date"] <= FINAL_LAST_DATE:
                raise SchemaError("forecasts: fecha objetivo de la evaluacion final fuera de 2026-08-01..2026-08-21")
        elif doc["target_date"] > LAST_HISTORIC_DATE:
            raise SchemaError(f"forecasts: fecha objetivo posterior a {LAST_HISTORIC_DATE}")
    if coll == "recommendations":
        if doc["provenance"] != PROVENANCE_SIM:
            raise SchemaError("recommendations: provenance debe ser SYNTHETIC_NOT_REAL_INVENTORY")
        if doc["status"] == "sin_snapshot":
            if any(doc.get(f) is not None for f in _NUM_NULL_FIELDS + _EXACT_FIELDS):
                raise SchemaError("recommendations: sin_snapshot no admite campos numericos")
        elif doc["status"] == "ok":
            if any(not isinstance(doc.get(f), (int, float)) for f in _NUM_NULL_FIELDS):
                raise SchemaError("recommendations: ok requiere campos numericos")
            if (not isinstance(doc.get("sum_28"), str) or not isinstance(doc.get("days_28"), int)
                    or doc["days_28"] <= 0 or not isinstance(doc.get("mean_28_exact"), str)
                    or not isinstance(doc.get("target_raw_exact"), str) or not isinstance(doc.get("signals"), dict)):
                raise SchemaError("recommendations: ok requiere senales exactas (sum_28, days_28, mean_28_exact)")
        else:
            raise SchemaError("recommendations: status invalido")
    if coll == "backtests" and doc["provenance"] != PROVENANCE_SIM:
        raise SchemaError("backtests: provenance invalida")
    if coll == "backtests" and doc["kind"] == FINAL_KIND and doc["selection"].get("rf_declared_winner") is not False:
        raise SchemaError("backtests: la evaluacion final no declara ganador al RF")
