"""Modelos globales (Random Forest y XGBoost acotados), paquete de inferencia e interfaz.

Un modelo global por nivel y fold/origen. Los hiperparametros vienen de la configuracion y no se
buscan. Prediccion negativa: se recorta a 0 (igual en todos los modelos). Los paquetes serializados
(joblib) solo deben cargarse si fueron generados localmente por este proyecto.

Coherencia de inferencia (T07): antes de predecir se valida que el contexto (fecha de inicio y fin
reales, dimensiones, identidad/numero de entidades, vocabulario con el que se codificaron categorias
y almacenes) corresponda al paquete, que la version de features y el horizonte entrenado sean
compatibles, y se rechaza lo incompatible con un mensaje util. Los paquetes T06 (sin version de
features) se rechazan salvo `allow_legacy=True`, valido solo para horizontes <= 7 (semantica identica).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import timedelta

import joblib
import numpy as np
import pandas as pd

from .features import (
    FEATURE_NAMES,
    FEATURE_VERSION,
    SeriesContext,
    Vocab,
    inference_matrices,
)

BUNDLE_VERSION = "t07-bundle-1"
LEGACY_FEATURE_VERSION = "legacy-t06"


class InferenceContextError(ValueError):
    """Contexto o paquete incompatible con la inferencia pedida."""


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
    # los paquetes T06 no tienen estos campos: al deserializar toman estos valores por defecto de clase
    feature_version: str = LEGACY_FEATURE_VERSION
    horizonte_entrenado: int = 7


def fit_bundle(name: str, params: dict, X: np.ndarray, y: np.ndarray, *, nivel: str, corte: str, vocab: Vocab,
               config_sha256: str, inicio: str, meta: dict, horizonte: int = 7) -> ModelBundle:
    est = make_estimator(name, params)
    t0 = time.perf_counter()
    est.fit(X, y)
    return ModelBundle(nombre=name, nivel=nivel, corte=corte, estimator=est, vocab=vocab,
                       feature_names=tuple(FEATURE_NAMES), config_sha256=config_sha256, inicio=inicio,
                       entrenamiento={**meta, "filas": int(X.shape[0]), "caracteristicas": int(X.shape[1]),
                                      "segundos_ajuste": round(time.perf_counter() - t0, 2),
                                      "memoria_matriz_mb": round(X.nbytes / 1e6, 1)},
                       feature_version=FEATURE_VERSION, horizonte_entrenado=int(horizonte))


def validate_inference(bundle: ModelBundle, ctx: SeriesContext, horizon: int, n_entities: int | None = None) -> None:
    """Rechaza contextos/paquetes incompatibles antes de construir features."""
    if bundle.feature_version != FEATURE_VERSION:
        if bundle.feature_version == LEGACY_FEATURE_VERSION and horizon <= 7:
            pass   # paquete T06: misma semantica para h<=7 (aceptado solo si se cargo con allow_legacy)
        else:
            raise InferenceContextError(
                f"version de features del paquete '{bundle.feature_version}' incompatible con '{FEATURE_VERSION}' "
                f"para horizonte {horizon}")
    if not 1 <= horizon <= bundle.horizonte_entrenado:
        raise InferenceContextError(
            f"horizonte pedido {horizon} fuera de lo entrenado (1..{bundle.horizonte_entrenado}); no se extrapola")
    if tuple(bundle.feature_names) != tuple(FEATURE_NAMES):
        raise InferenceContextError("el paquete fue entrenado con otro conjunto de features")
    n, total = ctx.values.shape
    for name, arr in (("cat_codes", ctx.cat_codes), ("alm_codes", ctx.alm_codes)):
        if arr.shape != (n,):
            raise InferenceContextError(f"{name} tiene forma {arr.shape}, se esperaba ({n},)")
    if ctx.cat_values.shape != (n, total):
        raise InferenceContextError(f"cat_values tiene forma {ctx.cat_values.shape}, se esperaba {(n, total)}")
    if n_entities is not None and n_entities != n:
        raise InferenceContextError(f"se recibieron {n_entities} entidades pero la matriz tiene {n} filas")
    if ctx.start.isoformat() != bundle.inicio:
        raise InferenceContextError(
            f"el contexto empieza el {ctx.start} pero el paquete se entreno con inicio {bundle.inicio}")
    end = ctx.start + timedelta(days=total - 1)
    if end.isoformat() != bundle.corte:
        raise InferenceContextError(f"el contexto termina el {end} pero el paquete corresponde al corte {bundle.corte}")
    if ctx.vocab_id != bundle.vocab.id():
        raise InferenceContextError(
            "los codigos de categoria/almacen del contexto no se construyeron con el vocabulario del paquete "
            f"(contexto: {ctx.vocab_id}, paquete: {bundle.vocab.id()}); use encode_with_vocab")


def encode_with_vocab(bundle: ModelBundle, categories, almacenes) -> tuple[np.ndarray, np.ndarray, str]:
    """Codigos con el vocabulario GUARDADO del paquete (nunca se reajusta al inferir); desconocidos = -1."""
    return (np.array([bundle.vocab.cat(c) for c in categories], dtype=int),
            np.array([bundle.vocab.alm(a) for a in almacenes], dtype=int), bundle.vocab.id())


def predict_block(bundle: ModelBundle, ctx: SeriesContext, horizon: int = 7) -> tuple[np.ndarray, int]:
    """Pronostico emitido una vez en el origen (ultima columna de ctx.values).

    Retorna (n, horizon) con NaN para entidades sin historia y el numero de valores negativos recortados."""
    validate_inference(bundle, ctx, horizon)
    known, mats = inference_matrices(ctx, horizon)
    out = np.full((ctx.values.shape[0], horizon), np.nan)
    clipped = 0
    for h, x in mats:
        raw = np.asarray(bundle.estimator.predict(x), dtype=float)
        clipped += int((raw < 0).sum())
        out[known, h - 1] = np.maximum(raw, 0.0)
    return out, clipped


def forecast_origin(bundle: ModelBundle, ctx: SeriesContext, entities, horizon: int = 7) -> pd.DataFrame:
    """Interfaz reproducible: fechas futuras con cantidades no negativas (sin redondeo a pedidos)."""
    entities = list(entities)
    validate_inference(bundle, ctx, horizon, n_entities=len(entities))
    if len(set(map(str, entities))) != len(entities):
        raise InferenceContextError("identificadores de entidad repetidos")
    origin = ctx.start + timedelta(days=ctx.values.shape[1] - 1)
    pred, _ = predict_block(bundle, ctx, horizon)
    rows = [(str(ent), (origin + timedelta(days=h + 1)).isoformat(), h + 1, float(pred[i, h]), bundle.nombre,
             bundle.nivel, bundle.corte, bundle.version, bundle.feature_version)
            for i, ent in enumerate(entities) for h in range(horizon) if not np.isnan(pred[i, h])]
    return pd.DataFrame(rows, columns=["entidad", "fecha", "h", "pred", "modelo", "nivel", "corte", "version",
                                       "version_features"])


def save_bundle(bundle: ModelBundle, path) -> None:
    joblib.dump(bundle, path)


def load_bundle(path, *, allow_legacy: bool = False) -> ModelBundle:
    """Solo para artefactos generados localmente por este proyecto (joblib/pickle no es seguro con origen externo).

    Los paquetes T06 (sin version de features) se rechazan salvo allow_legacy=True (solo horizonte <= 7)."""
    bundle = joblib.load(path)
    if bundle.feature_version == LEGACY_FEATURE_VERSION and not allow_legacy:
        raise InferenceContextError(
            f"{path}: paquete anterior a T07 (sin version de features); pase allow_legacy=True para usarlo con horizonte <= 7")
    return bundle

