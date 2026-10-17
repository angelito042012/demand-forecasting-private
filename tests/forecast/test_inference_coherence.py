"""T07 prerrequisito: la inferencia rechaza contextos/paquetes incompatibles y la semantica h>7 no lee futuro."""
from dataclasses import replace
from datetime import date, timedelta

import numpy as np
import pytest

from pipeline.forecast import features as ft
from pipeline.forecast.models import (
    InferenceContextError,
    encode_with_vocab,
    fit_bundle,
    forecast_origin,
    load_bundle,
    predict_block,
    save_bundle,
)

START = date(2026, 4, 1)
VOC = ft.Vocab.fit(["A", "B"], ["1"])
RF = {"n_estimators": 5, "max_depth": 3, "min_samples_leaf": 3, "random_state": 1, "n_jobs": 1}


def _values(total=70, n=4, seed=0):
    return np.random.default_rng(seed).poisson(1.0, size=(n, total)).astype(float)


def _ctx(v, start=START, vocab=VOC):
    n = v.shape[0]
    cats, alms, vid = np.array([vocab.cat("A")] * n), np.array([vocab.alm("1")] * n), vocab.id()
    return ft.SeriesContext(v, start, cats, alms, v, vid)


def _bundle(v, horizon=14, vocab=VOC):
    ctx = _ctx(v, vocab=vocab)
    origins = ft.training_origins(v.shape[1], step=3, min_origin=27, horizon=horizon)
    x, y, _ = ft.build_training(ctx, origins, horizon)
    corte = (START + timedelta(days=v.shape[1] - 1)).isoformat()
    return ctx, fit_bundle("random_forest", RF, x, y, nivel="sku", corte=corte, vocab=vocab, config_sha256="c",
                           inicio=START.isoformat(), meta={}, horizonte=horizon)


def test_shifted_context_with_same_length_is_rejected():
    ctx, b = _bundle(_values())
    shifted = ft.SeriesContext(ctx.values, START + timedelta(days=7), ctx.cat_codes, ctx.alm_codes, ctx.cat_values,
                               ctx.vocab_id)
    with pytest.raises(InferenceContextError, match="empieza"):
        predict_block(b, shifted, 7)
    with pytest.raises(InferenceContextError, match="empieza"):
        forecast_origin(b, shifted, list("wxyz"), 7)


def test_dimensions_and_entity_identity_checked():
    ctx, b = _bundle(_values())
    with pytest.raises(InferenceContextError, match="entidades"):
        forecast_origin(b, ctx, ["a", "b"], 7)
    with pytest.raises(InferenceContextError, match="repetidos"):
        forecast_origin(b, ctx, ["a", "a", "b", "c"], 7)
    bad = replace(ctx, cat_values=ctx.cat_values[:, :-1])
    with pytest.raises(InferenceContextError, match="cat_values"):
        predict_block(b, bad, 7)
    bad = replace(ctx, cat_codes=ctx.cat_codes[:2])
    with pytest.raises(InferenceContextError, match="cat_codes"):
        predict_block(b, bad, 7)
    longer = _values(total=77)
    with pytest.raises(InferenceContextError, match="termina"):
        predict_block(b, _ctx(longer), 7)


def test_vocabulary_reordered_or_unknown_is_not_silently_remapped():
    v = _values()
    ctx, b = _bundle(v)
    reordered = ft.Vocab(("B", "A"), ("1",))               # misma membresia, otro orden => otros codigos
    with pytest.raises(InferenceContextError, match="vocabulario"):
        predict_block(b, _ctx(v, vocab=reordered), 7)
    cats, alms, vid = encode_with_vocab(b, ["A", "Z-desconocida", "B", "A"], ["1", "9", "1", "1"])
    assert cats.tolist() == [0, -1, 1, 0] and alms.tolist() == [0, -1, 0, 0]       # desconocidos = -1, vocabulario guardado
    good = replace(ctx, cat_codes=cats, alm_codes=alms, vocab_id=vid)
    pred, _ = predict_block(b, good, 7)
    assert pred.shape == (4, 7) and (pred >= 0).all()


def test_horizon_and_feature_version_are_validated_and_legacy_rejected(tmp_path):
    v = _values()
    ctx, b = _bundle(v, horizon=14)
    predict_block(b, ctx, 14)
    with pytest.raises(InferenceContextError, match="fuera de lo entrenado"):
        predict_block(b, ctx, 21)
    old = replace(b, feature_version="legacy-t06", horizonte_entrenado=7)
    predict_block(old, ctx, 7)                                           # misma semantica para h<=7
    with pytest.raises(InferenceContextError):
        predict_block(replace(old, horizonte_entrenado=21), ctx, 14)     # legacy no cubre h>7
    path = tmp_path / "old.joblib"
    save_bundle(old, path)
    with pytest.raises(InferenceContextError, match="anterior a T07"):
        load_bundle(path)
    assert load_bundle(path, allow_legacy=True).feature_version == "legacy-t06"
    path2 = tmp_path / "new.joblib"
    save_bundle(b, path2)
    again = load_bundle(path2)
    assert np.array_equal(predict_block(b, ctx, 14)[0], predict_block(again, ctx, 14)[0], equal_nan=True)
    assert again.feature_version == ft.FEATURE_VERSION and again.horizonte_entrenado == 14


def test_extended_lag_uses_last_observed_week_and_never_future():
    v = np.arange(80, dtype=float)[None, :]
    ctx = _ctx(v)
    oi = 60
    known, base = ft.base_features(ctx, oi)
    j = ft.FEATURE_NAMES.index
    for h, w in ((3, 1), (7, 1), (8, 2), (14, 2), (15, 3), (21, 3)):
        x = ft.build_matrix(ctx, oi, h, known, base)
        assert x[0, j("lag_mismo_dia_1s")] == oi + h - 7 * w <= oi
        assert x[0, j("lag_mismo_dia_2s")] == oi + h - 7 * w - 7
    # cambiar todo lo posterior al origen no altera ninguna feature para h hasta 21
    w2 = v.copy()
    w2[:, oi + 1:] = -999
    k2, b2 = ft.base_features(_ctx(w2), oi)
    for h in range(1, 22):
        assert np.array_equal(ft.build_matrix(ctx, oi, h, known, base), ft.build_matrix(_ctx(w2), oi, h, k2, b2),
                              equal_nan=True)
    with pytest.raises(ValueError):
        ft.build_matrix(ctx, oi, 22, known, base)


def test_training_labels_up_to_horizon_21_stay_within_cutoff():
    v = _values(total=90)
    ctx = _ctx(v)
    origins = ft.training_origins(90, step=3, min_origin=27, horizon=21)
    assert max(origins) + 21 <= 89
    _x, _y, meta = ft.build_training(ctx, origins, 21)
    assert (meta[:, 0] + meta[:, 2] <= 89).all() and meta[:, 2].max() == 21
