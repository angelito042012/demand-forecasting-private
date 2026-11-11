"""Esquema: el tipo generated_baseline admite rf None / observed None / sin backtests; la corrida historica no."""
from __future__ import annotations

import copy

import pytest

from pipeline.publish.schema import SchemaError, validate_doc


def fc(**over):
    base = {"run_id": "r", "level": "sku", "entity_id": "1|1", "categoria": "C", "target_date": "2026-07-11", "h": 1,
            "pred": {"promedio_28": 2.5, "rf_categoria_distribuido": None, "cero": 0.0}, "evaluable": False,
            "observed": None, "run_kind": "generated_baseline", "provenance": "OBSERVED_EXCEL", "schema_version": 1}
    base.update(over)
    return base


def run(**over):
    base = {"run_id": "gen-20260710-aaaaaaaaaaaa", "status": "staging", "kind": "generated_baseline", "run_label": "x",
            "idempotency_key": "k", "fingerprint": "f", "cutoff": "2026-07-10", "origin": "2026-07-10",
            "target_start": "2026-07-11", "target_end": "2026-07-31", "horizon_days": 21,
            "method": {"chosen": "promedio_28"}, "sources": [], "artifacts": [], "code": {}, "schema_version": 1,
            "counts": {"backtests": 0}}
    base.update(over)
    return base


def test_generated_forecast_allows_null_rf_and_observed():
    validate_doc("forecasts", fc())
    validate_doc("forecasts", fc(pred={"promedio_28": 0.0, "rf_categoria_distribuido": 1.5, "cero": 0.0}))


@pytest.mark.parametrize("over", [
    {"observed": 0}, {"observed": 3}, {"evaluable": True},
    {"pred": {"promedio_28": None, "rf_categoria_distribuido": None, "cero": 0.0}},     # el metodo elegido no puede faltar
    {"pred": {"promedio_28": -1.0, "rf_categoria_distribuido": None, "cero": 0.0}},
    {"pred": {"promedio_28": 1.0, "rf_categoria_distribuido": -2.0, "cero": 0.0}},
    {"pred": {"promedio_28": 1.0, "rf_categoria_distribuido": None}},
    {"target_date": "2026-10-22"}])
def test_generated_forecast_rejections(over):
    with pytest.raises(SchemaError):
        validate_doc("forecasts", fc(**over))


def test_historical_forecast_still_requires_numeric_rf_and_rejects_null_rf():
    hist = fc(run_kind=None, observed=4, evaluable=True)
    hist.pop("run_kind")
    with pytest.raises(SchemaError):
        validate_doc("forecasts", hist)                       # rf None no se admite fuera de generated_baseline
    hist["pred"]["rf_categoria_distribuido"] = 1.0
    validate_doc("forecasts", hist)


def test_generated_run_must_declare_zero_backtests_and_promedio_28():
    validate_doc("runs", run())
    for bad in (run(counts={"backtests": 1}), run(counts={}), run(method={"chosen": "xgboost"})):
        with pytest.raises(SchemaError):
            validate_doc("runs", bad)
    hist = copy.deepcopy(run(kind="historical_development", counts={"backtests": 1}))
    validate_doc("runs", hist)                                 # la historica no cambia
