"""T06: mismo universo que T05, sin fuga de datos posteriores al corte, seleccion y reproducibilidad (Mongo sintetico)."""
import numpy as np
import pytest

from pipeline.data.importer import import_workbook
from pipeline.forecast.t05 import run_all
from pipeline.forecast.t06 import ML_MODELS, make_extras_fn, select_models
from tests.forecast.test_t05_integration import CFG, RM, rows

pytestmark = pytest.mark.mongo
CFG6 = {"origenes_entrenamiento": {"paso_dias": 1, "origen_minimo_indice": 1},
        "modelos": {"random_forest": {"parametros": {"n_estimators": 8, "max_depth": 4, "min_samples_leaf": 3,
                                                     "random_state": 1, "n_jobs": 1}},
                    "xgboost": {"parametros": {"n_estimators": 8, "max_depth": 3, "learning_rate": 0.3,
                                               "random_state": 1, "n_jobs": 1, "tree_method": "hist"}}},
        "seleccion": {"sku": {"vista": "bloque7"}, "categoria": {"vista": "diaria"}, "mejora_relativa_minima": 0.02,
                      "folds_favorables_minimos": 1, "sesgo_relativo_maximo_abs": 0.25}}


@pytest.fixture
def loaded(xlsx, db):
    import_workbook(xlsx("abril.xlsx", rows()), db)
    return db


def _run(db, tmp_path):
    log: list = []
    return run_all(db, CFG, required_months=RM, extras_fn=make_extras_fn(CFG6, "sha", tmp_path, log)), log


def test_ml_uses_same_targets_and_coverage_as_baselines(loaded, tmp_path):
    base = run_all(loaded, CFG, required_months=RM)
    res, log = _run(loaded, tmp_path)
    keep = {"fold", "nivel", "cohorte", "universo", "vista", "metodo", "n", "MAE", "WAPE", "sesgo_acumulado"}
    strip = lambda recs: sorted(({k: r.get(k) for k in keep} for r in recs if r["metodo"] in
                                 ("cero", "ultimo_dia", "naive_semanal", "promedio_28")), key=repr)
    assert strip(base["metricas"]) == strip(res["metricas"])            # baselines identicos con ML anadido
    p = res["predicciones"]
    for m in ML_MODELS:
        assert f"pred_{m}" in p.columns and (p[f"pred_{m}"].dropna() >= 0).all()
        mm = next(r for r in res["metricas"] if r["metodo"] == m and r["fold"] == "A" and r["nivel"] == "sku"
              and r["cohorte"] == "primaria" and r["universo"] == "comun" and r["vista"] == "diaria")
        cero = next(r for r in res["metricas"] if r["metodo"] == "cero" and r["fold"] == "A" and r["nivel"] == "sku"
                and r["cohorte"] == "primaria" and r["universo"] == "comun" and r["vista"] == "diaria")
        assert mm["n"] == cero["n"]                                      # misma cobertura/targets
    assert {e["modelo"] for e in log} == set(ML_MODELS) and all(e["filas"] > 0 for e in log)
    sel = select_models(res["metricas"], {**CFG6}, ["A", "B"])
    assert sel["sku"]["propuesta_para_simulacion"] in ("ultimo_dia", "naive_semanal", "promedio_28", *ML_MODELS)


def test_changes_after_cutoff_do_not_change_ml_predictions(loaded, tmp_path):
    before, _ = _run(loaded, tmp_path)
    loaded.sales.update_many({"fecha": {"$gt": "2026-04-20"}}, {"$set": {"cantidad_base": 77}})
    after, _ = _run(loaded, tmp_path)
    cols = [f"pred_{m}" for m in ML_MODELS]
    b = before["predicciones"][before["predicciones"]["fold"] == "B"][cols].to_numpy(float)   # fold B: corte 04-09
    a = after["predicciones"][after["predicciones"]["fold"] == "B"][cols].to_numpy(float)
    assert np.array_equal(b, a, equal_nan=True)


def test_repeated_training_gives_identical_predictions(loaded, tmp_path):
    r1, _ = _run(loaded, tmp_path)
    r2, _ = _run(loaded, tmp_path)
    assert r1["predicciones"].equals(r2["predicciones"]) and r1["metricas"] == r2["metricas"]


def test_selection_requires_all_conditions_and_never_crowns_zero():
    def rec(fold, nivel, metodo, vista, wape, sesgo=0.0, obs=100.0):
        return {"fold": fold, "nivel": nivel, "metodo": metodo, "vista": vista, "cohorte": "primaria",
                "universo": "comun", "WAPE": wape, "sesgo_acumulado": sesgo, "unidades_observadas": obs}
    folds = ["A", "B", "C", "D", "E"]
    recs = []
    for nivel, vista in (("sku", "bloque7"), ("categoria", "diaria")):
        for m, w in (("cero", 1.0), ("ultimo_dia", 1.3), ("naive_semanal", 1.1), ("promedio_28", 0.99),
                     ("random_forest", 0.90), ("xgboost", 0.985)):
            for f in ["AGREGADO", *folds]:
                recs.append(rec(f, nivel, m, vista, w, sesgo=(-100.0 if m == "cero" else 5.0)))
    sel = select_models(recs, CFG6 | {"seleccion": {**CFG6["seleccion"], "folds_favorables_minimos": 3}}, folds)
    assert sel["sku"]["ganador_ml"] == "random_forest" and sel["sku"]["mejor_referencia"] == "promedio_28"
    assert not sel["sku"]["ml"]["xgboost"]["cumple_regla"]            # mejora < 2 %
    # sin mejora suficiente: no hay ganador y se propone el baseline no nulo mas solido
    worse = [r for r in recs if r["metodo"] != "random_forest"]
    sel2 = select_models(worse, CFG6, folds)
    assert sel2["sku"]["ganador_ml"] is None and sel2["sku"]["propuesta_para_simulacion"] == "promedio_28"
