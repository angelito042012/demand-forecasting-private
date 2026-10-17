"""T05: baselines y metricas (puras, sin Mongo)."""
import numpy as np
import pytest

from pipeline.forecast import metrics as mt
from pipeline.forecast.baselines import forecast_block, primary_mask

NAN = np.nan


def _row(*vals):
    return np.array([vals], dtype=float)


def test_mean28_includes_valid_zeros_and_excludes_missing():
    v = _row(*([NAN] * 10), *([0.0, 2.0] * 9))      # 28 columnas: 10 no utilizables + 18 observaciones
    b = forecast_block(v)
    assert b.usable_28[0] == 18 and b.forecasts["promedio_28"][0, 0] == pytest.approx(1.0)   # no solo dias con venta (=2)
    assert b.history_days[0] == 18


def test_last_day_records_age_and_can_be_an_observed_zero():
    v = _row(NAN, NAN, 5.0, 3.0, 0.0, NAN, NAN)
    b = forecast_block(v)
    assert b.forecasts["ultimo_dia"][0, 0] == 0.0 and b.last_day_age[0] == 2
    assert np.isnan(forecast_block(_row(*([NAN] * 7))).forecasts["ultimo_dia"]).all()


def test_naive_weekly_uses_t_plus_h_minus_7_and_counts_fallback():
    v = _row(*range(1, 15), )          # origen = columna 13 (valor 14); t+h-7 -> columnas 7..13
    v[0, 9] = NAN                      # un hueco dentro de la semana previa
    b = forecast_block(v)
    f = b.forecasts["naive_semanal"][0]
    assert f[0] == 8 and f[1] == 9 and f[3] == 11                      # h=1 -> col 7 (valor 8); h=4 -> col 10
    assert f[2] == pytest.approx(b.forecasts["promedio_28"][0, 0]) and b.naive_fallback[0].tolist() == [
        False, False, True, False, False, False, False]


def test_naive_not_available_not_zero_when_no_observation():
    b = forecast_block(_row(*([NAN] * 14)))
    assert np.isnan(b.forecasts["naive_semanal"]).all() and (b.forecasts["cero"] == 0).all()
    assert not b.naive_fallback.any()


def test_future_columns_cannot_change_forecasts():
    full = np.arange(1, 22, dtype=float)[None, :]
    base = forecast_block(full[:, :14])
    again = forecast_block(np.concatenate([full[:, :14]], axis=1))
    for m in base.forecasts:
        assert np.array_equal(base.forecasts[m], again.forecasts[m], equal_nan=True)
    # la funcion solo ve las columnas hasta el origen: el bloque 14..20 no esta en su entrada
    assert base.forecasts["naive_semanal"][0, 0] == full[0, 7] and base.forecasts["naive_semanal"][0, 6] == full[0, 13]


def test_primary_cohort_uses_history_and_recent_observations():
    long_dense = np.ones((1, 60))
    sparse = np.full((1, 60), NAN)
    sparse[0, ::3] = 1.0
    short = np.concatenate([np.full((1, 40), NAN), np.ones((1, 20))], axis=1)
    got = [primary_mask(forecast_block(x))[0] for x in (long_dense, sparse, short)]
    assert got == [True, False, False]       # sparse: 56 dias de historia pero <21 observaciones recientes


def test_metrics_basic_and_pooled_by_counts_not_by_averaging_percentages():
    a1, p1 = np.array([0, 2, 4.0]), np.array([1, 2, 2.0])
    a2, p2 = np.array([10.0, 0.0]), np.array([5.0, 0.0])
    s1, s2 = mt.stats(a1, p1), mt.stats(a2, p2)
    m1 = mt.finalize(s1, r2_min_n=30)
    assert m1["MAE"] == pytest.approx(1.0) and m1["WAPE"] == pytest.approx(0.5)
    assert m1["sesgo_acumulado"] == pytest.approx(-1.0)
    assert m1["MAPE"] == pytest.approx((0 + 0.5) / 2) and m1["MAPE_ceros_excluidos"] == 1
    assert m1["MAPE_cobertura_reales_positivos"] == pytest.approx(2 / 3) and m1["R2"] is None
    pooled = mt.finalize(mt.add_stats(s1, s2))
    assert pooled["WAPE"] == pytest.approx((3 + 5) / 16)       # sumas, no el promedio de 0.5 y 0.5
    assert pooled["n"] == 5 and pooled["unidades_predichas"] == pytest.approx(10)


def test_constant_zero_and_empty_cases_do_not_force_values():
    z = mt.finalize(mt.stats(np.zeros(40), np.zeros(40)))
    assert z["WAPE"] is None and z["MAPE"] is None and z["R2"] is None and z["MAE"] == 0
    assert mt.finalize(mt.stats(np.full(40, 3.0), np.full(40, 3.0)))["R2"] is None      # varianza nula
    assert mt.finalize(mt.new_stats()) == {"n": 0}
    big = mt.finalize(mt.stats(np.arange(40.0), np.arange(40.0) + 1))
    assert big["R2"] is not None and big["R2"] < 1
    with pytest.raises(ValueError):
        mt.stats(np.array([1.0]), np.array([np.nan]))
