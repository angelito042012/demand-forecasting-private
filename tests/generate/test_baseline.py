"""T10 §4: generador promedio_28 sobre ventas SINTETICAS en bases temporales aisladas (df_test_<uuid>)."""
from __future__ import annotations

import math
from datetime import date, timedelta
from fractions import Fraction

import numpy as np
import pytest

from pipeline.generate import baseline
from pipeline.generate.baseline import build, collect_inputs, generate_and_publish
from pipeline.generate.config import GenerationError
from pipeline.publish.source import PROJECT_ROOT
from tests.generate.helpers import (
    Spec,
    build_months,
    default_specs,
    expected_signal,
    needs_artifacts,
    patch_reference,
    qty_var,
)
from tests.publish.helpers import ENTRY, kids, temp_db

pytestmark = pytest.mark.mongo
ORIGIN = date(2026, 6, 20)
SKIP = frozenset({date(2026, 6, 12)})        # dia sin NINGUN registro (no es cero)


@pytest.fixture
def world(tmp_path, monkeypatch):
    patch_reference(monkeypatch)
    with temp_db() as db:
        build_months(db, tmp_path, skip_days=SKIP)
        yield db


def test_forecast_is_exact_28_day_mean_constant_over_natural_dates(world):
    inp = collect_inputs(world, ORIGIN, 21, "promedio_28")
    gen = build(inp)
    specs = default_specs()
    docs = [d for d in gen.prepared["forecasts"] if d["level"] == "sku"]
    for sku, sp in specs.items():
        total, days = expected_signal(sp, ORIGIN, SKIP)
        assert inp.signals.per_sku[(sku, "1")] == (total, days)
        assert days < 28                               # 06/06 enmascarado + dia sin registros: no se asume 28
        mine = sorted((d for d in docs if d["sku"] == sku), key=lambda d: d["h"])
        assert [d["h"] for d in mine] == list(range(1, 22))
        assert [d["target_date"] for d in mine] == [(ORIGIN + timedelta(days=h)).isoformat() for h in range(1, 22)]
        assert {d["pred"]["promedio_28"] for d in mine} == {float(total / days)}
        assert all(d["pred"]["cero"] == 0.0 and d["pred"]["rf_categoria_distribuido"] is None for d in mine)
    assert len(docs) == 21 * len(specs)


def test_cohorts_follow_t05_rule_at_origin(world):
    inp = collect_inputs(world, ORIGIN, 21, "promedio_28")
    assert inp.cohort[("9000002", "1")] == "historia_corta"      # primera venta 10/06: < 56 dias de historia
    assert inp.cohort[("9000001", "1")] == "primaria"
    docs = [d for d in build(inp).prepared["forecasts"] if d["sku"] == "9000002"]
    assert {d["cohorte"] for d in docs} == {"historia_corta"}


def test_data_after_origin_never_changes_the_output(world):
    before = build(collect_inputs(world, ORIGIN, 21, "promedio_28"))
    world.sales.update_many({"fecha": {"$gt": ORIGIN.isoformat()}},
                            {"$set": {"cantidad_base": 999, "categoria_original": "ZZZ"}})
    world.sales.insert_one({"linea_id": "tardia", "fecha": "2026-06-25", "sku": "9000001", "cantidad_base": 5000,
                            "importe": None, "categoria_original": "ZZZ", "almacen": "1", "sources": []})
    after = build(collect_inputs(world, ORIGIN, 21, "promedio_28"))
    assert after.run_doc["fingerprint"] == before.run_doc["fingerprint"]
    assert after.run_doc["run_id"] == before.run_doc["run_id"]
    assert after.prepared["forecasts"] == before.prepared["forecasts"]


def test_categories_are_sum_of_skus_and_unknown_is_separate(world):
    res = generate_and_publish(world, ORIGIN, 21, "promedio_28")
    cid = kids(world, res["run_id"])
    cats = list(world.forecasts.find({"run_id": cid, "level": "categoria"}))
    assert {c["entity_id"] for c in cats} >= {"CAT A", "CAT B", "DESCONOCIDA"}
    for c in cats:
        members = list(world.forecasts.find({"run_id": cid, "level": "sku", "categoria": c["entity_id"],
                                             "target_date": c["target_date"]}))
        assert c["pred"]["promedio_28"] == pytest.approx(sum(m["pred"]["promedio_28"] for m in members))
        assert c["observed"] is None and c["evaluable"] is False and c["pred"]["rf_categoria_distribuido"] is None
    unknown = world.forecasts.find_one({"run_id": cid, "level": "sku", "sku": "9000004"})
    assert unknown["categoria"] == "DESCONOCIDA"
    assert res["coverage"]["skus_categoria_desconocida"] == 1


def test_published_run_has_no_future_fields_and_correct_kind_and_labels(world):
    res = generate_and_publish(world, ORIGIN, 21, "promedio_28")
    run = world.runs.find_one({"run_id": res["run_id"]})
    assert run["status"] == "completed" and run["kind"] == "generated_baseline"
    assert run["run_label"] == "Corrida de desarrollo generada por la aplicación con origen 20/06/2026"
    assert run["run_id"].startswith("gen-20260620-") and len(run["run_id"]) == len("gen-20260620-") + 12
    assert run["method"]["chosen"] == "promedio_28" and run["method"]["comparator_available"] is False
    assert run["method"]["comparator_note"].startswith("comparador no disponible")
    assert run["evaluation_period"]["evaluable_days"] == 0
    assert (run["origin"], run["target_start"], run["target_end"], run["horizon_days"]) == (
        "2026-06-20", "2026-06-21", "2026-07-11", 21)
    assert run["counts"]["backtests"] == 0 and world.backtests.count_documents({}) == 0
    man = run["manifest"]
    assert man["entrenamiento_fingerprint"] == run["sources_fingerprint"]
    assert man["fuentes_sha256"] == [s["sha256"] for s in run["sources"]] and len(run["sources"]) == 4
    assert len(man["codigo"]["codigo_sha256"]) == 64 and man["senales"]["fingerprint"]
    cid = kids(world, run["run_id"])
    assert world.forecasts.count_documents({"run_id": cid, "observed": {"$ne": None}}) == 0
    assert world.forecasts.count_documents({"run_id": cid, "evaluable": {"$ne": False}}) == 0
    assert world.forecasts.count_documents({"run_id": cid, "target_date": {"$gt": "2026-07-31"}}) == 0
    assert world.run_pointer.find_one({"_id": "active"}) is None        # no desplaza a la corrida historica


def test_missing_days_are_not_zero_and_a_fully_uncovered_window_is_rejected(tmp_path, monkeypatch):
    patch_reference(monkeypatch)
    window = frozenset(ORIGIN - timedelta(days=i) for i in range(28))
    with temp_db() as db:
        build_months(db, tmp_path, skip_days=window)
        with pytest.raises(GenerationError) as exc:
            collect_inputs(db, ORIGIN, 21, "promedio_28")
        assert exc.value.code == "SIN_DATOS_UTILES" and not exc.value.retryable
        assert db.runs.count_documents({}) == 0


def test_identity_is_stable_and_changes_with_any_input(world):
    a = collect_inputs(world, ORIGIN, 21, "promedio_28").identity
    b = collect_inputs(world, ORIGIN, 21, "promedio_28").identity
    assert a["fingerprint"] == b["fingerprint"] and a["run_id"] == b["run_id"]
    assert collect_inputs(world, ORIGIN, 14, "promedio_28").identity["fingerprint"] != a["fingerprint"]
    assert collect_inputs(world, ORIGIN - timedelta(days=1), 21, "promedio_28").identity["run_id"] != a["run_id"]
    world.sales.update_one({"fecha": "2026-06-15", "sku": "9000001"}, {"$set": {"cantidad_base": 40}})
    assert collect_inputs(world, ORIGIN, 21, "promedio_28").identity["fingerprint"] != a["fingerprint"]


def test_same_input_same_run_and_second_publication_changes_nothing(world):
    first = generate_and_publish(world, ORIGIN, 21, "promedio_28")
    n = (world.forecasts.count_documents({}), world.runs.count_documents({}))
    second = generate_and_publish(world, ORIGIN, 21, "promedio_28")
    assert first["outcome"] == "generada" and second["outcome"] == "sin_cambios"
    assert first["run_id"] == second["run_id"]
    assert (world.forecasts.count_documents({}), world.runs.count_documents({})) == n


@pytest.mark.parametrize("origin,horizon,method", [
    (date(2026, 5, 31), 21, "promedio_28"), (date(2026, 7, 11), 21, "promedio_28"),
    (date(2026, 8, 1), 21, "promedio_28"), (ORIGIN, 22, "promedio_28"), (ORIGIN, 0, "promedio_28"),
    (ORIGIN, 21, "xgboost")])
def test_origin_horizon_and_method_out_of_policy_are_rejected_before_reading_data(tmp_path, origin, horizon, method):
    with temp_db() as db:
        with pytest.raises(GenerationError) as exc:
            generate_and_publish(db, origin, horizon, method)
        assert exc.value.code in ("CORTE_FUERA_DE_RANGO", "METODO_NO_PERMITIDO") and not exc.value.retryable
        assert db.runs.count_documents({}) == 0


def test_unapproved_sources_stop_generation_without_publishing(tmp_path, monkeypatch):
    patch_reference(monkeypatch)
    with temp_db() as db:
        build_months(db, tmp_path, months=(3, 4, 5))            # falta junio
        with pytest.raises(GenerationError) as exc:
            generate_and_publish(db, ORIGIN, 21, "promedio_28")
        assert exc.value.code == "FUENTES_NO_APROBADAS" and "MES_SIN_FUENTE_APROBADA" in exc.value.message
        assert db.runs.count_documents({}) == 0 and db.forecasts.count_documents({}) == 0


def test_comparator_is_unavailable_when_training_does_not_match_the_t07_fold(tmp_path, monkeypatch):
    patch_reference(monkeypatch)
    with temp_db() as db:
        build_months(db, tmp_path, through=date(2026, 7, 10), months=(3, 4, 5, 6, 7),
                     specs=default_specs({k: Spec("CAT A", date(2026, 3, 1), date(2026, 7, 10)) for k in ("9000009",)}))
        inp = collect_inputs(db, date(2026, 7, 10), 21, "promedio_28")      # mismo origen que G4, datos distintos
        assert inp.rf is None and "comparador no disponible" in inp.rf_note
        gen = build(inp)
        assert gen.run_doc["method"]["comparator_available"] is False
        assert all(d["pred"]["rf_categoria_distribuido"] is None for d in gen.prepared["forecasts"])
        assert gen.coverage["comparador_disponible"] is False


# ----------------------------------------------------------------- recomendaciones y snapshot T07
@needs_artifacts
def test_recommendation_uses_snapshot_and_transit_at_origin_manual_check(tmp_path, monkeypatch):
    patch_reference(monkeypatch)
    z = np.load(PROJECT_ROOT / ENTRY["artifacts_dir"] / "simulacion_series.npz", allow_pickle=False)
    key, idx = "L7_S7_promedio_28__", (ORIGIN - date(2026, 6, 1)).days
    ordered, received, on_hand = z[key + "ordered"], z[key + "received"], z[key + "on_hand"]
    transit_at = ordered[:idx + 1].sum(axis=0) - received[:idx + 1].sum(axis=0)
    transit_final = ordered.sum(axis=0) - received.sum(axis=0)
    cand = np.flatnonzero((transit_at > 0) & (transit_at != transit_final) & (on_hand[idx] >= 0))
    assert cand.size, "debe existir un SKU con transito al origen distinto del final"
    i = int(cand[0])
    sku = str(z["skus"][i])
    specs = default_specs({sku: Spec("CAT A", date(2026, 3, 1), date(2026, 6, 30), qty=qty_var)})
    with temp_db() as db:
        build_months(db, tmp_path, skip_days=SKIP, specs=specs)
        res = generate_and_publish(db, ORIGIN, 21, "promedio_28")
        cid = kids(db, res["run_id"])
        doc = db.recommendations.find_one({"run_id": cid, "sku": sku})
        total, days = expected_signal(specs[sku], ORIGIN, SKIP)
        target = math.ceil(Fraction(21) * total / days)
        on, tr = int(on_hand[idx, i]), int(transit_at[i])
        assert doc["status"] == "ok" and doc["snapshot_date"] == "2026-06-20" and doc["origin"] == "2026-06-20"
        assert doc["scenario_id"] == "T07_L7_S7_promedio_28_2026-06-20"
        assert (doc["forecast_from"], doc["forecast_to"]) == ("2026-06-21", "2026-07-04")
        assert doc["in_transit"] == tr and doc["in_transit"] != int(transit_final[i])
        assert doc["on_hand"] == on and doc["position"] == on + tr
        assert doc["sum_28"] == str(total) and doc["days_28"] == days
        assert doc["target"] == target and doc["order_qty"] == max(0, target - (on + tr))
        assert doc["unit_cost_assumed"] == float(z["costo"][i])
        assert doc["provenance"] == "SYNTHETIC_NOT_REAL_INVENTORY"
        assert any("20/06" in s for s in doc["explanation_steps"]) and not any("10/07" in s for s in doc["explanation_steps"])
        # SKU fuera del universo simulado: sin snapshot y NUNCA stock cero
        out = db.recommendations.find_one({"run_id": cid, "sku": "9000001"})
        assert out["status"] == "sin_snapshot" and out["reason"].startswith("SIN_INVENTARIO_SIMULADO_AL_20_06")
        for f in ("on_hand", "in_transit", "position", "target", "order_qty", "unit_cost_assumed", "sum_28"):
            assert out[f] is None
        assert res["recommendations_available"] is True
        assert res["coverage"]["skus_con_recomendacion"] + res["coverage"]["skus_sin_snapshot"] == res["counts"][
            "forecasts_sku"] // 21


def test_missing_simulation_artifact_publishes_forecasts_with_reason_and_no_numeric_recommendations(
        tmp_path, monkeypatch):
    patch_reference(monkeypatch, available=False)
    with temp_db() as db:
        build_months(db, tmp_path, skip_days=SKIP)
        res = generate_and_publish(db, ORIGIN, 21, "promedio_28")
        run = db.runs.find_one({"run_id": res["run_id"]})
        assert run["status"] == "completed" and res["recommendations_available"] is False
        assert res["recommendations_reason"] == "ARTEFACTO_SIMULACION_NO_DISPONIBLE"
        assert run["coverage"]["recomendaciones_razon_ausencia"] == "ARTEFACTO_SIMULACION_NO_DISPONIBLE"
        assert db.recommendations.count_documents({}) == 0 and run["counts"]["recommendations"] == 0
        assert db.forecasts.count_documents({"level": "sku"}) == 21 * len(default_specs()) and run["artifacts"] == []
        assert run["manifest"]["snapshot"] == {"disponible": False, "razon": "ARTEFACTO_SIMULACION_NO_DISPONIBLE"}


def test_generalized_snapshot_requires_origin_inside_the_simulation_window():
    from pipeline.publish.source import SourceVerificationError, load_snapshot
    from tests.publish.helpers import ARTIFACTS_OK, real_source
    if not ARTIFACTS_OK:
        pytest.skip("artefactos T07 reales no disponibles")
    src = real_source()
    with pytest.raises(SourceVerificationError):
        load_snapshot(src, date(2026, 5, 31))
    with pytest.raises(SourceVerificationError):
        load_snapshot(src, date(2026, 8, 5))
    snap = load_snapshot(src, date(2026, 6, 1))
    assert snap["index"] == 0 and len(snap["skus"]) == 3347
    assert load_snapshot(src, date(2026, 7, 10))["index"] == 39
    assert baseline.NO_SIM == "ARTEFACTO_SIMULACION_NO_DISPONIBLE"
