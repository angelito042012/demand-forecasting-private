"""T07: agregacion, pesos, costos, pronostico RF por categoria distribuido y regla de seleccion."""
from datetime import date

import numpy as np
import pytest
from bson.decimal128 import Decimal128

from pipeline.forecast import t07 as t7

NAN = np.nan
RF = {"parametros": {"n_estimators": 8, "max_depth": 4, "min_samples_leaf": 3, "random_state": 1, "n_jobs": 1},
      "origenes_entrenamiento": {"paso_dias": 3, "origen_minimo_indice": 27}}


def test_category_aggregation_nan_rules():
    v = np.array([[NAN, 1, 2, NAN], [NAN, NAN, 3, NAN], [5, 5, 5, 5]], dtype=float)
    names, c = t7.aggregate_categories(v, ["A", "A", "B"])
    assert names == ["A", "B"]
    assert np.isnan(c[0, 0]) and c[0, 1] == 1 and c[0, 2] == 5 and np.isnan(c[0, 3])      # NaN solo si todas las filas lo son
    assert c[1].tolist() == [5, 5, 5, 5]


def test_allocation_weights_and_fallbacks_are_counted():
    v = np.zeros((5, 40))
    v[0, -3] = 2.0
    v[1, -3] = 6.0                      # categoria A: pesos 0.25 / 0.75 (28 dias)
    v[2, 5] = 4.0                       # categoria B: sin ventas en 28 dias -> historico
    # categoria C (filas 3 y 4) sin ninguna venta -> uniforme
    w, counts = t7.allocation_weights(v, ["A", "A", "B", "C", "C"], ["A", "B", "C"])
    assert w.tolist() == [0.25, 0.75, 1.0, 0.5, 0.5]
    assert counts == {"categorias_peso_28d": 1, "categorias_fallback_historico": 1, "categorias_fallback_uniforme": 1}


def _synthetic(n=8, T=100, seed=0):
    rng = np.random.default_rng(seed)
    v = rng.poisson(1.2, size=(n, T)).astype(float)
    v[0, :20] = NAN
    v[3, 40] = NAN
    return v


def test_rf_distributed_conserves_category_total_nonnegative_and_h21():
    v = _synthetic()
    cats = ["A", "A", "A", "B", "B", "B", "C", "C"]
    fc = t7.forecast_origin_t07(v, date(2026, 3, 1), cats, ["1"], RF, "sha")
    assert fc["rf_dist"].shape == (8, 21) and (fc["rf_dist"] >= 0).all()
    assert fc["conservacion_max_abs_error"] < 1e-9
    assert fc["bundle"].horizonte_entrenado == 21 and fc["bundle"].feature_version == "t07-1"
    assert fc["bundle"].corte == "2026-06-08"                                  # inicio + 99 dias
    again = t7.forecast_origin_t07(v, date(2026, 3, 1), cats, ["1"], RF, "sha")
    assert np.array_equal(fc["rf_dist"], again["rf_dist"], equal_nan=True)     # n_jobs=1 -> determinista
    # sumar los SKU de una categoria reproduce el pronostico de la categoria
    assert np.allclose(fc["rf_dist"][:3].sum(axis=0), fc["cat_pred"][0])


def test_forecast_at_origin_ignores_what_comes_after():
    full = _synthetic(T=110)
    other = full.copy()
    other[:, 100:] = 999.0
    cats = ["A", "A", "A", "B", "B", "B", "C", "C"]
    a = t7.forecast_origin_t07(full[:, :100], date(2026, 3, 1), cats, ["1"], RF, "sha")
    b = t7.forecast_origin_t07(other[:, :100], date(2026, 3, 1), cats, ["1"], RF, "sha")
    assert np.array_equal(a["rf_dist"], b["rf_dist"], equal_nan=True) and np.array_equal(a["mean28"], b["mean28"])


def test_unit_costs_median_fallbacks_and_counts():
    def row(sku, price, eq=1):
        return {"sku": sku, "precio_unitario_original": Decimal128(str(price)), "equivalencia": eq}
    rows = [row("a", 10), row("a", 20), row("a", 30), row("b", 8, 2), row("x", 0), {"sku": "y", "precio_unitario_original": None,
                                                                                   "equivalencia": 1}]
    cost, counts = t7.unit_costs(rows, ["a", "b", "c", "d"], {"a": "K", "b": "K", "c": "K", "d": "Z"}, 0.65)
    assert cost[0] == pytest.approx(0.65 * 20) and cost[1] == pytest.approx(0.65 * 4)           # mediana por unidad base
    assert cost[2] == pytest.approx(0.65 * np.median([20, 4])) and cost[3] == pytest.approx(0.65 * np.median([20, 4]))
    assert counts == {"propio": 2, "categoria": 1, "global": 1}


def test_selection_rule_needs_improvement_folds_bias_and_valid_denominator():
    def rec(fold, m, w, obs=100.0, bias=10.0):
        return {"fold": fold, "cohorte": "primaria", "metodo": m, "vista": "acum14", "WAPE": w,
                "unidades_observadas": obs, "sesgo_acumulado": bias}
    rule = {"criterio_primario": {"H": 14, "cohorte": "primaria"}, "comparador": "promedio_28",
            "mejora_relativa_minima": 0.02, "folds_favorables_minimos": 3, "sesgo_relativo_maximo_abs": 0.25}
    folds = ["G1", "G2", "G3", "G4"]
    good = [rec("AGREGADO", "promedio_28", 1.0), rec("AGREGADO", "rf_distribuido", 0.9)]
    for f in folds:
        good += [rec(f, "promedio_28", 1.0), rec(f, "rf_distribuido", 0.9)]
    assert t7.select_candidate(good, rule, folds)["cumple_regla"] is True
    two = [dict(r, WAPE=1.1) if r["fold"] in ("G3", "G4") and r["metodo"] == "rf_distribuido" else r for r in good]
    assert t7.select_candidate(two, rule, folds)["cumple_regla"] is False                     # solo 2 folds favorables
    biased = [dict(r, sesgo_acumulado=40.0) if r["fold"] == "AGREGADO" and r["metodo"] == "rf_distribuido" else r for r in good]
    assert t7.select_candidate(biased, rule, folds)["cumple_regla"] is False                  # |sesgo|/obs = 0,4 > 0,25
    zero = [dict(r, WAPE=None) if r["fold"] == "AGREGADO" else r for r in good]
    out = t7.select_candidate(zero, rule, folds)
    assert out["cumple_regla"] is None and "no evaluable" in out["nota"]


def test_eval_common_universe_and_cumulative_over_evaluable_days_only():
    actual = np.zeros((3, 21))
    actual[0, :3] = [1, 2, 3]
    preds = {"cero": np.zeros((3, 21)), "promedio_28": np.full((3, 21), 1.0), "rf_distribuido": np.full((3, 21), 2.0)}
    preds["rf_distribuido"][2, 0] = NAN                       # entidad 2 sin pronostico completo: fuera del universo comun
    ev = np.ones(21, bool)
    ev[1] = False                                              # dia 2 no evaluable (p. ej. enmascarado)
    out = t7.eval_fold_predictions(actual, preds, ev, {"primaria": np.array([True, True, True])})
    assert out[("primaria", "cobertura")]["comunes"] == 2
    s = out[("primaria", "promedio_28", "acum10")]
    assert s["n"] == 2 and s["sum_a"] == 4.0 and s["sum_p"] == 18.0       # 9 dias evaluables x 1.0 x 2 entidades; real 1+3
    assert out[("primaria", "promedio_28", "diaria")]["n"] == 2 * 20
