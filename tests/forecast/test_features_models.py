"""T06: features sin futuro, etiquetas dentro de corte, vocabulario de train, serializacion e inferencia."""
from datetime import date, timedelta

import numpy as np
import pytest

from pipeline.forecast import features as ft
from pipeline.forecast.models import (
    fit_bundle,
    forecast_origin,
    load_bundle,
    predict_block,
    save_bundle,
)

NAN = np.nan
START = date(2026, 4, 1)


def _ctx(values, cat_codes=None, cat_values=None):
    n = values.shape[0]
    return ft.SeriesContext(values, START, np.zeros(n, int) if cat_codes is None else cat_codes, np.zeros(n, int),
                            values if cat_values is None else cat_values)


def _series(total=60, seed=0, n=5):
    rng = np.random.default_rng(seed)
    v = rng.poisson(1.0, size=(n, total)).astype(float)
    v[0, :10] = NAN                       # producto que aparece despues
    v[1, 20] = NAN                        # dia no utilizable (enmascarado) aislado
    return v


def test_features_at_origin_ignore_columns_after_origin():
    v = _series()
    a = ft.base_features(_ctx(v), 40)
    w = v.copy()
    w[:, 41:] = 999.0                     # el futuro cambia por completo
    b = ft.base_features(_ctx(w), 40)
    assert np.array_equal(a[0], b[0])
    for k in a[1]:
        assert np.array_equal(a[1][k], b[1][k], equal_nan=True), k
    for h in range(1, 8):
        xa = ft.build_matrix(_ctx(v), 40, h, *a)
        xb = ft.build_matrix(_ctx(w), 40, h, *b)
        assert np.array_equal(xa, xb, equal_nan=True)


def test_labels_never_past_cutoff_and_masked_labels_excluded_but_zeros_kept():
    v = _series(total=40)
    origins = ft.training_origins(v.shape[1], step=3, min_origin=27)
    assert max(origins) + 7 <= v.shape[1] - 1 and origins == sorted(origins) and min(origins) >= 27
    _x, y, meta = ft.build_training(_ctx(v), origins)
    assert (meta[:, 0] + meta[:, 2] <= v.shape[1] - 1).all()
    assert not np.isnan(y).any() and (y == 0).any()                 # ceros validos presentes
    # etiqueta enmascarada (entidad 1, columna 20) no entra
    hit = (meta[:, 1] == 1) & (meta[:, 0] + meta[:, 2] == 20)
    assert not hit.any()
    with pytest.raises(AssertionError):
        ft.build_training(_ctx(v), [v.shape[1] - 3])                # etiqueta posterior al corte


def test_training_origins_deterministic_and_calendar_not_compressed():
    assert ft.training_origins(100, step=3, min_origin=27) == ft.training_origins(100, step=3, min_origin=27)
    v = np.arange(60, dtype=float)[None, :]
    known, base = ft.base_features(_ctx(v), 40)
    x = ft.build_matrix(_ctx(v), 40, 3, known, base)
    j = ft.FEATURE_NAMES.index
    assert x[0, j("lag0")] == 40 and x[0, j("lag3")] == 37 and x[0, j("lag_mismo_dia_1s")] == 36   # 40+3-7
    assert x[0, j("dow")] == float((START + timedelta(days=43)).weekday())   # fecha objetivo = inicio + 43 dias


def test_unknown_entities_and_vocab_fitted_only_on_train():
    v = _series()
    known, _ = ft.base_features(_ctx(v), 5)
    assert not known[0]                                             # producto nuevo (aparece en col 10): sin historia al origen
    vocab = ft.Vocab.fit(["A", "B", "A"], ["1"])
    assert vocab.cat("A") == 0 and vocab.cat("B") == 1 and vocab.cat("Z-validacion") == -1 and vocab.alm("9") == -1


def _bundle(name, params, v):
    ctx = _ctx(v)
    origins = ft.training_origins(v.shape[1], step=3, min_origin=27)
    x, y, _ = ft.build_training(ctx, origins)
    b = fit_bundle(name, params, x, y, nivel="sku", corte="2026-05-30", vocab=ft.Vocab.fit(["A"], ["1"]),
                   config_sha256="abc", inicio=START.isoformat(), meta={"origenes": len(origins)})
    return ctx, b


RF = {"n_estimators": 10, "max_depth": 4, "min_samples_leaf": 5, "random_state": 1, "n_jobs": 1}
XG = {"n_estimators": 10, "max_depth": 3, "learning_rate": 0.2, "random_state": 1, "n_jobs": 1, "tree_method": "hist"}


@pytest.mark.parametrize(("name", "params"), [("random_forest", RF), ("xgboost", XG)])
def test_prediction_does_not_see_future_nonnegative_and_is_reproducible(name, params, tmp_path):
    v = _series(total=60)
    ctx, bundle = _bundle(name, params, v)
    p1, _ = predict_block(bundle, ctx)
    assert p1.shape == (5, 7) and (p1[1:] >= 0).all() and np.isnan(p1[0]).sum() == 0     # la entidad 0 ya tiene historia al corte
    # reentrenar con la misma semilla reproduce la prediccion; datos posteriores al corte no existen en la entrada
    _, bundle2 = _bundle(name, params, v)
    p2, _ = predict_block(bundle2, ctx)
    assert np.array_equal(p1, p2)
    # guardar/cargar
    path = tmp_path / "m.joblib"
    save_bundle(bundle, path)
    loaded = load_bundle(path)
    p3, _ = predict_block(loaded, ctx)
    assert np.array_equal(p1, p3)
    assert loaded.corte == "2026-05-30" and loaded.version and loaded.feature_names == tuple(ft.FEATURE_NAMES)


def test_forecast_origin_interface_returns_seven_future_dates_without_future_sales(tmp_path):
    v = _series(total=60)
    ctx, bundle = _bundle("xgboost", XG, v)
    bundle.corte = "2026-05-30"                                     # inicio 04-01 + 59 dias = ultima columna
    df = forecast_origin(bundle, ctx, [f"e{i}" for i in range(5)])
    assert sorted(df["h"].unique()) == list(range(1, 8)) and df["fecha"].min() == "2026-05-31"
    assert df["fecha"].max() == "2026-06-06" and (df["pred"] >= 0).all()
    assert set(df["modelo"]) == {"xgboost"} and set(df["corte"]) == {"2026-05-30"}
    bundle.corte = "2026-05-31"
    with pytest.raises(ValueError, match="corte"):
        forecast_origin(bundle, ctx, ["e"] * 5)
