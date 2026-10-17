"""Baselines deterministas de T05. Funciones puras sobre una matriz entidad x dia de ENTRENAMIENTO.

`values` tiene una columna por dia natural desde el inicio hasta el origen (ultima columna =
corte). NaN = dia no utilizable para esa entidad: antes de su primera observacion, enmascarado
o sin registros. Un cero observado es 0.0 (utilizable). La matriz no contiene dias posteriores
al origen, de modo que ningun metodo puede ver el bloque de validacion.

Horizonte h=1..H: el pronostico se emite una vez en el origen y no se realimenta.
  cero           0
  ultimo_dia     ultimo valor utilizable (puede ser un cero observado); registra antiguedad
  naive_semanal  dato de t+h-7 (dentro de entrenamiento para h<=7); si no es utilizable usa
                 promedio_28 como fallback contabilizado; si tampoco existe: NaN (no disponible)
  promedio_28    media de las observaciones utilizables de los ultimos 28 dias naturales
                 (incluye ceros validos, excluye ausentes/enmascarados); NaN si no hay ninguna
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

METHODS = ("cero", "ultimo_dia", "naive_semanal", "promedio_28")


@dataclass(frozen=True)
class BaselineBlock:
    forecasts: dict             # metodo -> (n, H) float, NaN = no disponible
    last_day_age: np.ndarray    # (n,) dias entre el origen y el ultimo dia utilizable (NaN si no hay)
    naive_fallback: np.ndarray  # (n, H) bool: se uso promedio_28 en lugar del dato t+h-7
    history_days: np.ndarray    # (n,) dias naturales desde la primera observacion hasta el origen
    usable_28: np.ndarray       # (n,) observaciones utilizables en los ultimos 28 dias


def first_usable_index(values: np.ndarray) -> np.ndarray:
    ok = ~np.isnan(values)
    return np.where(ok.any(axis=1), ok.argmax(axis=1), values.shape[1])


def forecast_block(values: np.ndarray, *, horizon: int = 7, window: int = 28) -> BaselineBlock:
    n, total = values.shape
    origin = total - 1
    ok = ~np.isnan(values)
    first = first_usable_index(values)
    history = np.where(first <= origin, origin - first + 1, 0)
    win = values[:, max(0, total - window):]
    usable = (~np.isnan(win)).sum(axis=1)
    mean28 = np.where(usable > 0, np.nansum(win, axis=1) / np.maximum(usable, 1), np.nan)
    last_idx = np.where(ok.any(axis=1), origin - ok[:, ::-1].argmax(axis=1), -1)
    last_val = np.where(last_idx >= 0, values[np.arange(n), np.maximum(last_idx, 0)], np.nan)
    age = np.where(last_idx >= 0, origin - last_idx, np.nan)
    naive = np.full((n, horizon), np.nan)
    fallback = np.zeros((n, horizon), dtype=bool)
    for h in range(1, horizon + 1):
        src = origin + h - 7   # t+h-7: dentro de entrenamiento para 1<=h<=7
        if h > 7 or src < 0:
            raise ValueError("naive_semanal exige 1<=h<=7 y suficiente calendario")
        col = values[:, src]
        missing = np.isnan(col)
        naive[:, h - 1] = np.where(missing, mean28, col)
        fallback[:, h - 1] = missing & ~np.isnan(mean28)
    return BaselineBlock(
        forecasts={"cero": np.zeros((n, horizon)), "ultimo_dia": np.repeat(last_val[:, None], horizon, axis=1),
                   "naive_semanal": naive, "promedio_28": np.repeat(mean28[:, None], horizon, axis=1)},
        last_day_age=age, naive_fallback=fallback, history_days=history, usable_28=usable)


def primary_mask(block: BaselineBlock, *, min_history: int = 56, min_usable: int = 21) -> np.ndarray:
    """Cohorte primaria fijada con datos de entrenamiento (igual para los cuatro metodos)."""
    return (block.history_days >= min_history) & (block.usable_28 >= min_usable)
