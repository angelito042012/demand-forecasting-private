"""Modelos globales de T06 (Random Forest y XGBoost acotados), paquete de inferencia e interfaz.

Un modelo global por nivel y fold. Los hiperparametros vienen de config/t06_config.json y no se
buscan. Prediccion negativa: se recorta a 0 (igual en todos los modelos y folds). Los paquetes
serializados (joblib) solo deben cargarse si fueron generados localmente por este proyecto.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import joblib
import numpy as np
import pandas as pd

from .features import FEATURE_NAMES, SeriesContext, Vocab, inference_matrices

BUNDLE_VERSION = "t06-bundle-1"


def make_estimator(name: str, params: dict):
    if name == "random_forest":
        from sklearn.ensemble import RandomForestRegressor
        return RandomForestRegressor(**params)
    if name == "xgboost":
        from xgboost import XGBRegressor
        return XGBRegressor(**params)
    raise ValueError(f"modelo desconocido: {name}")


@dataclass
class ModelBundle:
    """Modelo + todo lo necesario para reproducir la inferencia desde un origen."""
    nombre: str
    nivel: str
    corte: str                  # fin de entrenamiento (origen de inferencia)
    estimator: object
    vocab: Vocab
    feature_names: tuple
    config_sha256: str
    inicio: str
    version: str = BUNDLE_VERSION
    entrenamiento: dict = field(default_factory=dict)   # filas, tiempos, origenes (trazabilidad)


def fit_bundle(name: str, params: dict, X: np.ndarray, y: np.ndarray, *, nivel: str, corte: str, vocab: Vocab,
               config_sha256: str, inicio: str, meta: dict) -> ModelBundle:
    est = make_estimator(name, params)
    t0 = time.perf_counter()
    est.fit(X, y)
    return ModelBundle(nombre=name, nivel=nivel, corte=corte, estimator=est, vocab=vocab,
                       feature_names=tuple(FEATURE_NAMES), config_sha256=config_sha256, inicio=inicio,
                       entrenamiento={**meta, "filas": int(X.shape[0]), "caracteristicas": int(X.shape[1]),
                                      "segundos_ajuste": round(time.perf_counter() - t0, 2),
                                      "memoria_matriz_mb": round(X.nbytes / 1e6, 1)})


def predict_block(bundle: ModelBundle, ctx: SeriesContext, horizon: int = 7) -> tuple[np.ndarray, int]:
    """Pronostico emitido una vez en el origen (ultima columna de ctx.values).

    Retorna (n, horizon) con NaN para entidades sin historia y el numero de valores negativos recortados."""
    if tuple(bundle.feature_names) != tuple(FEATURE_NAMES):
        raise ValueError("el paquete fue entrenado con otro conjunto de features")
    known, mats = inference_matrices(ctx, horizon)
    out = np.full((ctx.values.shape[0], horizon), np.nan)
    clipped = 0
    for h, x in mats:
        raw = np.asarray(bundle.estimator.predict(x), dtype=float)
        clipped += int((raw < 0).sum())
        out[known, h - 1] = np.maximum(raw, 0.0)
    return out, clipped


def forecast_origin(bundle: ModelBundle, ctx: SeriesContext, entities, horizon: int = 7) -> pd.DataFrame:
    """Interfaz reproducible: siete fechas futuras con cantidades no negativas (sin redondeo a pedidos)."""
    from datetime import date as _date
    from datetime import timedelta
    origin = _date.fromisoformat(bundle.inicio) + timedelta(days=ctx.values.shape[1] - 1)
    if origin.isoformat() != bundle.corte:
        raise ValueError(f"el contexto termina en {origin} pero el modelo corresponde al corte {bundle.corte}")
    pred, _ = predict_block(bundle, ctx, horizon)
    rows = [(str(ent), (origin + timedelta(days=h + 1)).isoformat(), h + 1, float(pred[i, h]), bundle.nombre,
             bundle.nivel, bundle.corte, bundle.version)
            for i, ent in enumerate(entities) for h in range(horizon) if not np.isnan(pred[i, h])]
    return pd.DataFrame(rows, columns=["entidad", "fecha", "h", "pred", "modelo", "nivel", "corte", "version"])


def save_bundle(bundle: ModelBundle, path) -> None:
    joblib.dump(bundle, path)


def load_bundle(path) -> ModelBundle:
    """Solo para artefactos generados localmente por este proyecto (joblib/pickle no es seguro con origen externo)."""
    return joblib.load(path)
