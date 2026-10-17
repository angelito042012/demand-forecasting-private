"""Features y etiquetas de T06 sin informacion futura.

Una muestra es (entidad, origen o, horizonte h=1..7). Todas las features usan columnas <= o de la
matriz de entrenamiento (o el rezago t+h-7, que con h<=7 tambien cae en <= o); la etiqueta es la
columna o+h y solo existe si o+h <= corte del fold. NaN = dia no utilizable (antes de la primera
observacion, enmascarado o sin registros); se mantiene como NaN (Random Forest y XGBoost lo
soportan de forma nativa), de modo que no hay imputacion que ajustar. El vocabulario de
categorias y almacenes se ajusta SOLO con el entrenamiento del fold; lo desconocido se codifica -1.
Precio: no incorporado en esta iteracion (limitacion registrada en el protocolo).
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np

FEATURE_NAMES = (["h"] + [f"lag{k}" for k in range(7)]
                 + ["lag_mismo_dia_1s", "lag_mismo_dia_2s", "media7", "media28", "desv28", "prop_ceros28",
                    "usables28", "dias_desde_ultima_venta", "historia_dias", "media_historica",
                    "dow", "dia_mes", "mes", "cat_code", "cat_media28", "alm_code"])
UNKNOWN_CODE = -1


@dataclass(frozen=True)
class Vocab:
    categorias: tuple
    almacenes: tuple

    @staticmethod
    def fit(categories, almacenes) -> Vocab:
        return Vocab(tuple(sorted(set(categories))), tuple(sorted(set(almacenes))))

    def cat(self, c) -> int:
        return self.categorias.index(c) if c in self.categorias else UNKNOWN_CODE

    def alm(self, a) -> int:
        return self.almacenes.index(a) if a in self.almacenes else UNKNOWN_CODE


@dataclass(frozen=True)
class SeriesContext:
    """Todo lo conocido al corte del fold para un nivel."""
    values: np.ndarray          # (n, T) entrenamiento; ultima columna = corte
    start: date                 # fecha de la columna 0
    cat_codes: np.ndarray       # (n,) codigo de categoria (vocab de entrenamiento)
    alm_codes: np.ndarray       # (n,)
    cat_values: np.ndarray      # (n, T) serie de la categoria de cada entidad (NaN si no hay)


def _nan_stat(fn, arr):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        return fn(arr, axis=1)


def base_features(ctx: SeriesContext, oi: int) -> tuple[np.ndarray, dict]:
    """Features que dependen solo de columnas <= oi. Devuelve (entidades conocidas, dict de arrays)."""
    w = ctx.values[:, : oi + 1]
    ok = ~np.isnan(w)
    known = ok.any(axis=1)
    first = np.where(known, ok.argmax(axis=1), oi + 1)
    win28, win7 = w[:, max(0, oi - 27): oi + 1], w[:, max(0, oi - 6): oi + 1]
    usable28 = (~np.isnan(win28)).sum(axis=1).astype(float)
    pos = np.nan_to_num(w, nan=0.0) > 0
    last_sale = np.where(pos.any(axis=1), oi - pos[:, ::-1].argmax(axis=1), -1)
    f = {"media7": _nan_stat(np.nanmean, win7), "media28": _nan_stat(np.nanmean, win28),
         "desv28": _nan_stat(np.nanstd, win28),
         "prop_ceros28": np.where(usable28 > 0, (win28 == 0).sum(axis=1) / np.maximum(usable28, 1), np.nan),
         "usables28": usable28,
         "dias_desde_ultima_venta": np.where(last_sale >= 0, oi - last_sale, np.nan),
         "historia_dias": np.where(known, oi - first + 1, 0).astype(float),
         "media_historica": _nan_stat(np.nanmean, w),
         "cat_media28": _nan_stat(np.nanmean, ctx.cat_values[:, max(0, oi - 27): oi + 1]),
         "cat_code": ctx.cat_codes.astype(float), "alm_code": ctx.alm_codes.astype(float)}
    for k in range(7):
        f[f"lag{k}"] = w[:, oi - k] if oi - k >= 0 else np.full(w.shape[0], np.nan)
    return known, f


def build_matrix(ctx: SeriesContext, oi: int, h: int, known: np.ndarray, base: dict) -> np.ndarray:
    """Matriz (n_known, n_features) en el orden FEATURE_NAMES para el horizonte h."""
    if not 1 <= h <= 7:
        raise ValueError("h debe estar entre 1 y 7")
    n = int(known.sum())
    target = ctx.start + timedelta(days=oi + h)       # fecha objetivo (calendario natural)
    cols = {"h": np.full(n, float(h)), "dow": np.full(n, float(target.weekday())),
            "dia_mes": np.full(n, float(target.day)), "mes": np.full(n, float(target.month))}
    for name, lag in (("lag_mismo_dia_1s", 7), ("lag_mismo_dia_2s", 14)):
        idx = oi + h - lag
        if idx > oi:
            raise AssertionError("rezago posterior al origen")
        cols[name] = ctx.values[known, idx] if idx >= 0 else np.full(n, np.nan)
    out = np.empty((n, len(FEATURE_NAMES)), dtype=np.float32)
    for j, name in enumerate(FEATURE_NAMES):
        out[:, j] = cols[name] if name in cols else base[name][known]
    return out


def training_origins(total_cols: int, *, step: int, min_origin: int, horizon: int = 7) -> list[int]:
    """Origenes deterministas alineados hacia atras desde corte-horizonte (o+horizonte <= corte)."""
    last = total_cols - 1 - horizon
    return sorted(range(last, min_origin - 1, -step))


def build_training(ctx: SeriesContext, origins: list[int], horizon: int = 7):
    """(X, y, meta) con etiquetas utilizables unicamente (ausentes/enmascaradas se excluyen; los ceros validos se conservan)."""
    xs, ys, meta = [], [], []
    total = ctx.values.shape[1]
    for oi in origins:
        known, base = base_features(ctx, oi)
        for h in range(1, horizon + 1):
            if oi + h > total - 1:
                raise AssertionError("etiqueta posterior al corte de entrenamiento")
            y = ctx.values[known, oi + h]
            keep = ~np.isnan(y)
            x = build_matrix(ctx, oi, h, known, base)
            xs.append(x[keep])
            ys.append(y[keep])
            ent = np.flatnonzero(known)[keep]
            meta.append(np.column_stack([np.full(ent.size, oi), ent, np.full(ent.size, h)]))
    if not xs:
        raise ValueError("sin origenes de entrenamiento: calendario demasiado corto para el paso/origen minimo")
    return np.vstack(xs), np.concatenate(ys), np.vstack(meta)


def inference_matrices(ctx: SeriesContext, horizon: int = 7):
    """Features al origen (ultima columna) para h=1..7: lista de (h, matriz) y entidades conocidas."""
    oi = ctx.values.shape[1] - 1
    known, base = base_features(ctx, oi)
    return known, [(h, build_matrix(ctx, oi, h, known, base)) for h in range(1, horizon + 1)]
