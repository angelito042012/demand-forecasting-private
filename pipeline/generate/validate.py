"""Validacion de conteos y coherencia de una corrida generada, sobre los hijos del intento (T10 §4).

Se ejecuta DENTRO de `publish_prepared`, antes de promover la corrida: categorias = suma de SKU, sin campos
futuros (observed/evaluable), fechas objetivo dentro de (origen, origen+H] y <= 31/07, comparador consistente con lo
declarado y recomendaciones recalculables con la formula comun (`builders.recompute_recommendation`).
"""
from __future__ import annotations

import math
from datetime import date, timedelta

from pipeline.publish import builders as b
from pipeline.publish.protocol import PublishValidationError
from pipeline.publish.signals import parse_fraction


def _close(a: float, c: float) -> bool:
    return math.isclose(a, c, rel_tol=1e-9, abs_tol=1e-9)


def validate_generated(db, run_id: str, expected: dict, *, origin: date, horizon: int, comparator: bool,
                       recommendations: bool) -> dict:
    f, r = db.forecasts, db.recommendations
    got = {"forecasts_sku": f.count_documents({"run_id": run_id, "level": "sku"}),
           "forecasts_categoria": f.count_documents({"run_id": run_id, "level": "categoria"}),
           "recommendations": r.count_documents({"run_id": run_id}),
           "recommendations_ok": r.count_documents({"run_id": run_id, "status": "ok"}),
           "backtests": db.backtests.count_documents({"run_id": run_id})}
    for k, v in got.items():
        if expected[k] != v:
            raise PublishValidationError(f"conteo {k}: esperado {expected[k]}, hallado {v}")
    if got["backtests"] != 0:
        raise PublishValidationError("una corrida generada no admite backtests")
    if f.count_documents({"run_id": run_id, "$or": [{"observed": {"$ne": None}}, {"evaluable": {"$ne": False}},
                                                    {"run_kind": {"$ne": b.GENERATED_KIND}}]}):
        raise PublishValidationError("campos futuros (observed/evaluable) en una corrida generada")
    lo, hi = (origin + timedelta(days=1)).isoformat(), (origin + timedelta(days=horizon)).isoformat()
    if f.count_documents({"run_id": run_id, "$or": [{"target_date": {"$lt": lo}}, {"target_date": {"$gt": hi}},
                                                    {"target_date": {"$gt": "2026-09-30"}}]}):
        raise PublishValidationError("fecha objetivo fuera de la ventana permitida")
    has_rf = f.count_documents({"run_id": run_id, "pred.rf_categoria_distribuido": {"$ne": None}})
    if comparator and has_rf != got["forecasts_sku"] + got["forecasts_categoria"]:
        raise PublishValidationError("comparador declarado disponible pero incompleto")
    if not comparator and has_rf:
        raise PublishValidationError("comparador no disponible pero hay valores del RF")
    if f.count_documents({"run_id": run_id, "pred.cero": {"$ne": 0.0}}):
        raise PublishValidationError("control cero alterado")
    sums = {(g["_id"]["c"], g["_id"]["d"]): g for g in f.aggregate([
        {"$match": {"run_id": run_id, "level": "sku"}},
        {"$group": {"_id": {"c": "$categoria", "d": "$target_date"}, "p28": {"$sum": "$pred.promedio_28"},
                    "prf": {"$sum": "$pred.rf_categoria_distribuido"}}}], allowDiskUse=True)}
    seen = 0
    for c in f.find({"run_id": run_id, "level": "categoria"}):
        s = sums.get((c["entity_id"], c["target_date"]))
        if s is None or not _close(s["p28"], c["pred"]["promedio_28"]) or (
                comparator and not _close(s["prf"], c["pred"]["rf_categoria_distribuido"])):
            raise PublishValidationError("categoria no es la suma de sus SKU")
        seen += 1
    if seen != len(sums):
        raise PublishValidationError("categorias incompletas")
    skus_f = set(f.distinct("sku", {"run_id": run_id, "level": "sku"}))
    if recommendations:
        if skus_f != set(r.distinct("sku", {"run_id": run_id})):
            raise PublishValidationError("SKU con pronostico distintos de SKU con recomendacion")
        for d in r.find({"run_id": run_id, "status": "ok"}):
            calc = b.recompute_recommendation(d["on_hand"], d["in_transit"], parse_fraction(d["sum_28"]),
                                              d["days_28"], d["unit_cost_assumed"])
            if (calc["target"] != d["target"] or calc["position"] != d["position"]
                    or calc["order_qty"] != d["order_qty"] or d["in_transit"] < 0 or d["on_hand"] < 0
                    or calc["target_raw_exact"] != d["target_raw_exact"]
                    or not _close(calc["safety"], d["safety"]) or not _close(calc["mean_28"], d["mean_28"])):
                raise PublishValidationError(f"recomendacion no recalculable: {d['sku']}")
        if r.count_documents({"run_id": run_id, "status": "sin_snapshot",
                              "$or": [{x: {"$ne": None}} for x in b.NUM_FIELDS]}):
            raise PublishValidationError("sin_snapshot con campos numericos")
    elif got["recommendations"]:
        raise PublishValidationError("hay recomendaciones sin artefacto de simulacion verificado")
    return got
