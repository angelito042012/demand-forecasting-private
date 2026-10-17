"""Generador contra los Excel REALES (marzo-julio, SIN agosto) importados en una base TEMPORAL (RUN_REALDATA=1).

Comprueba que el origen 10/07 reproduce el resultado historico T07 G4 verificado (predicciones, cohortes, comparador
RF) y que las recomendaciones generalizadas coinciden con las de la ruta historica. No toca ninguna base real.
"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pytest

from pipeline.data.importer import import_workbook
from pipeline.generate.baseline import build, collect_inputs, generate_and_publish
from pipeline.publish import builders as b
from tests.publish.helpers import needs_artifacts, real_source, temp_db

SRC = Path(r"C:\Users\rogel\Documents\Datos")
pytestmark = [pytest.mark.mongo, pytest.mark.realdata, needs_artifacts,
              pytest.mark.skipif(not SRC.exists() or os.environ.get("RUN_REALDATA") != "1",
                                 reason="requiere C:\\Users\\rogel\\Documents\\Datos y RUN_REALDATA=1")]


@pytest.fixture(scope="module")
def real_db():
    with temp_db() as db:
        for name in ("marzo", "abril", "mayo", "junio", "julio"):          # agosto NO se importa
            rep = import_workbook(SRC / f"{name}.xlsx", db)
            assert rep.estado == "completed"
        yield db


def test_origin_0710_reproduces_the_verified_g4_run(real_db):
    src = real_source()
    inp = collect_inputs(real_db, date(2026, 7, 10), 21, "promedio_28")
    assert inp.rf is not None and inp.rf_note == ""                      # huella y fuentes iguales a las del fold G4
    gen = build(inp)
    csv = src.forecasts
    assert set(csv["entidad"]) == {f"{s}|{a}" for s, a in inp.entities} and len(inp.entities) == 3647
    first = csv.groupby("entidad").first()
    mine = {d["entity_id"]: d for d in gen.prepared["forecasts"] if d["level"] == "sku" and d["h"] == 1}
    for ent, row in first.iterrows():
        d = mine[ent]
        assert d["pred"]["promedio_28"] == pytest.approx(row["pred_promedio_28"], rel=1e-8)
        assert d["cohorte"] == row["cohorte"]
    got = {(d["entity_id"], d["target_date"]): d["pred"]["rf_categoria_distribuido"]
           for d in gen.prepared["forecasts"] if d["level"] == "sku"}
    for r in csv.itertuples(index=False):
        assert got[(r.entidad, r.fecha)] == pytest.approx(r.pred_rf_distribuido)
    assert all(d["observed"] is None and d["evaluable"] is False for d in gen.prepared["forecasts"])
    assert gen.counts["forecasts_sku"] == 76587 and gen.counts["recommendations_ok"] == 3347
    assert gen.counts["recommendations_sin_snapshot"] == 300


def test_generalized_recommendations_equal_the_historic_path(real_db):
    src = real_source()
    inp = collect_inputs(real_db, date(2026, 7, 10), 21, "promedio_28")
    gen = build(inp)
    historic = b.build_recommendations(src, inp.train.catalog, "pendiente", inp.signals)
    mine = {(d["sku"], d["almacen"]): d for d in gen.prepared["recommendations"]}
    assert len(historic) == len(mine) == 3647
    keys = ("status", "on_hand", "in_transit", "position", "target", "order_qty", "sum_28", "days_28",
            "scenario_id", "snapshot_date", "forecast_from", "forecast_to", "reason", "explanation_steps",
            "mean_28_exact", "target_raw_exact", "unit_cost_assumed", "order_value_assumed")
    for h in historic:
        m = mine[(h["sku"], h["almacen"])]
        assert {k: m[k] for k in keys} == {k: h[k] for k in keys}


def test_full_publication_at_0710_and_other_origin(real_db):
    res = generate_and_publish(real_db, date(2026, 7, 10), 21, "promedio_28")
    assert res["outcome"] == "generada" and res["comparator_available"] and res["recommendations_available"]
    again = generate_and_publish(real_db, date(2026, 7, 10), 21, "promedio_28")
    assert again["outcome"] == "sin_cambios" and again["run_id"] == res["run_id"]
    other = generate_and_publish(real_db, date(2026, 6, 15), 21, "promedio_28")
    assert other["comparator_available"] is False and other["run_id"] != res["run_id"]
    assert real_db.runs.count_documents({"status": "completed"}) == 2
