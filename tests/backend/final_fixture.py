"""Fixture SINTETICA de T11A: una corrida historica, una generada y una final_evaluation minimas, insertadas en una
base temporal df_test_<uuid>. Los numeros son inventados SOLO para probar separacion de corridas/fechas/roles;
no representan resultados reales ni se usan fuera de las pruebas."""
from __future__ import annotations

from datetime import date, datetime, timedelta

HIST_ID = "hist-test-0001"
GEN_ID = "gen-test-0001"
GEN_CHILD = "gen-test-0001-att1"
FINAL_ID = "final-20260731-0123456789ab"
FINAL_CHILD = "final-20260731-attempt-xyz"       # los hijos guardan el id de su intento
SEAL = "d587255d87fb2d99e449a098e4c1fa6e1c1c6d5838180b7aa8fe098e9a2ce663"

PHASES = ["verificacion", "preparacion", "lectura_agosto", "evaluacion_predictiva", "simulacion",
          "auditoria", "reporte"]
METHODS = ("promedio_28", "rf_categoria_distribuido", "cero")


def _fc(run_id, kind, level, entity, d, *, sku=None, cohorte="primaria", observed=0.0, evaluable=True,
        rf=1.5, categoria="CAT A"):
    return {"run_id": run_id, "run_kind": kind, "level": level, "entity_id": entity, "sku": sku,
            "almacen": "1" if sku else None, "categoria": categoria, "cohorte": cohorte if sku else "primaria",
            "target_date": d.isoformat(), "h": 1, "chosen_method": "promedio_28",
            "pred": {"promedio_28": 1.0, "rf_categoria_distribuido": rf, "cero": 0.0},
            "observed": observed, "evaluable": evaluable, "provenance": "OBSERVED_EXCEL", "schema_version": 1}


def _days(start: date, n: int):
    return [start + timedelta(days=i) for i in range(n)]


def _run(run_id, kind, cutoff, **extra):
    base = {"run_id": run_id, "status": "completed", "kind": kind, "cutoff": cutoff, "origin": cutoff,
            "run_label": "etiqueta de prueba", "generated_at": datetime(2026, 10, 17, 12, 0, 0),
            "published_at": datetime(2026, 10, 17, 12, 5, 0), "idempotency_key": "secreta", "attempts": 1,
            "counts": {}, "coverage": {}, "schema_version": 1}
    base.update(extra)
    return base


def _backtest(run_id, kind, label):
    row = {"fold": "FINAL", "cohorte": "primaria", "metodo": "promedio_28", "vista": "acum14", "n": 10,
           "unidades_observadas": 100.0, "unidades_predichas": 90.0, "WAPE": 0.5}
    block = {"fill_rate": 0.7, "perdidas_unidades": 10.0}
    return {"backtest_id": f"bt-{run_id}", "run_id": run_id, "kind": kind, "label": label, "folds": ["FINAL"],
            "created": datetime(2026, 10, 17, 12, 6, 0), "scenario_id": f"sc-{run_id}",
            "provenance": "SYNTHETIC_NOT_REAL_INVENTORY",
            "disclaimer": "Inventario simulado con supuestos; no corresponde al inventario real de la empresa",
            "predictive": {"sku": [row], "categoria": [{**row, "metodo": "rf_categoria"}], "nota": "fixture"},
            "selection": {"chosen": "promedio_28", "rf_declared_winner": False, "primary_criterion": "fixture",
                          "primary": {"WAPE_promedio_28": 0.5, "WAPE_rf_distribuido": 0.6, "WAPE_cero": 1.0,
                                      "mejora_relativa": -0.2, "sesgo_relativo": 0.02},
                          "note": "fixture"},
            "coverage": {"sku": [{"fold": "FINAL", "cohorte": "primaria", "metodo": "universo_comun",
                                  "entidades": 1, "comunes": 1, "dias_evaluables_21": 21}], "categoria": []},
            "simulation": [{"scenario_id": "s", "L": 7, "S": 7, "R": 7, "policy": "promedio_28", "total": block,
                            "primaria": block, "historia_corta": block}],
            "simulation_differences": [{"scenario": "L7_S7", "policy": "promedio_28", "vs": "referencia_fija",
                                        "cohorte": "total", "metrics": {"fill_rate": {"abs": 0.02, "rel": 0.03}}}],
            "assumptions": {"L": [7], "S": [7], "R": 7, "escenario_principal": {"L": 7, "S": 7}},
            "schema_version": 1}


def seed(db) -> dict:
    """Inserta las tres corridas (+ hijos) y el puntero activo -> historica. Devuelve los ids."""
    db.runs.insert_many([
        _run(HIST_ID, "historical_development", "2026-07-10", target_start="2026-07-11",
             target_end="2026-07-31", horizon_days=21, run_label="Corrida histórica de desarrollo al 10/07/2026"),
        _run(GEN_ID, "generated_baseline", "2026-06-20", children_ref=GEN_CHILD, target_start="2026-06-21",
             target_end="2026-07-11", horizon_days=21, published_at=datetime(2026, 10, 17, 12, 7, 0)),
        _run(FINAL_ID, "final_evaluation", "2026-07-31", children_ref=FINAL_CHILD, target_start="2026-08-01",
             target_end="2026-08-21", horizon_days=21, published_at=datetime(2026, 10, 17, 12, 8, 0),
             run_label="Evaluación final de agosto (origen 31/07/2026, bloque 01–21/08/2026)",
             evaluation_period={"start": "2026-08-01", "end": "2026-08-21", "single_block": True},
             method={"chosen": "promedio_28", "comparator": "rf_categoria_distribuido", "control": "cero",
                     "rf_declared_winner": False, "category_baseline": "suma de pronósticos SKU"},
             final_package={"seal_sha256": SEAL, "frozen_selection_sha256": "8" * 64,
                            "phases": {p: "completa" for p in PHASES},
                            "corrections": [{"code": "R11", "label": "reconciliación técnica posterior"}],
                            "audit_ok": True},
             counts={"forecasts_sku": 42, "forecasts_categoria": 21, "recommendations": 0, "backtests": 1},
             recommendations_unavailable_reason="RECOMENDACION_NO_VALIDADA_PARA_ESTE_ORIGEN", see_run=HIST_ID,
             artifacts=[{"name": "predictivo.json", "sha256": "e" * 64, "size_bytes": 10}]),
    ])
    db.run_pointer.insert_one({"_id": "active", "run_id": HIST_ID})

    db.forecasts.insert_many(
        [_fc(HIST_ID, "historical_development", "sku", "1|1", d, sku="1") for d in _days(date(2026, 7, 11), 21)]
        + [_fc(GEN_CHILD, "generated_baseline", "sku", "1|1", d, sku="1", observed=None, evaluable=None, rf=None)
           for d in _days(date(2026, 6, 21), 3)])
    fin = []
    for d in _days(date(2026, 8, 1), 21):
        fin.append(_fc(FINAL_CHILD, "final_evaluation", "sku", "1|1", d, sku="1", observed=2.0))
        # un dia sin ningun registro del archivo: no evaluable (no es cero)
        fin.append(_fc(FINAL_CHILD, "final_evaluation", "sku", "2|1", d, sku="2", cohorte="historia_corta",
                       observed=None if d.day == 15 else 0.0, evaluable=d.day != 15))
        fin.append(_fc(FINAL_CHILD, "final_evaluation", "categoria", "CAT A", d, observed=2.0))
    db.forecasts.insert_many(fin)

    db.recommendations.insert_many([
        {"run_id": HIST_ID, "sku": "1", "almacen": "1", "categoria": "CAT A", "status": "ok", "order_qty": 3,
         "explanation_steps": ["a"], "schema_version": 1},
        {"run_id": GEN_CHILD, "sku": "1", "almacen": "1", "categoria": "CAT A", "status": "sin_snapshot",
         "order_qty": None, "schema_version": 1},
        {"run_id": FINAL_CHILD, "sku": "9", "almacen": "1", "categoria": "CAT Z", "status": "ok", "order_qty": 99,
         "schema_version": 1},   # NUNCA debe exponerse: la evaluacion final no tiene recomendaciones
    ])
    db.backtests.insert_many([
        _backtest(HIST_ID, "T07_desarrollo", "Backtest T07 (fixture)"),
        _backtest(FINAL_CHILD, "final_evaluation", "Evaluación final T12 (fixture)"),
    ])
    return {"hist": HIST_ID, "gen": GEN_ID, "final": FINAL_ID}
