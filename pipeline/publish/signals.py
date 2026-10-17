"""Senales EXACTAS de la recomendacion (R05): suma de unidades y dias utiles de la ventana de 28 dias.

La media operativa NO se recupera del CSV de T07 (diez cifras significativas): se deriva de la
historia aprobada <= origen, con ceros validos y mascaras vigentes. La aritmetica es racional
(Fraction): el techo del objetivo no depende de coma flotante ni de un epsilon. Los decimales de
presentacion se derivan despues y nunca alimentan el calculo.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from fractions import Fraction

from pipeline.data import daily_series as ds
from pipeline.data.training_access import TrainingData

SIGNALS_VERSION = "exact-fraction-1"
WINDOW_DAYS = 28


@dataclass(frozen=True)
class Signals:
    origin: str
    window_start: str
    window_end: str
    per_sku: dict = field(default_factory=dict)     # (sku, almacen) -> (Fraction suma, int dias_utiles)
    training_fingerprint: str = ""
    fingerprint: str = ""
    version: str = SIGNALS_VERSION


def to_fraction(value) -> Fraction:
    """Cantidad -> Fraction decimal exacta (no la expansion binaria del float)."""
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value)
    return Fraction(Decimal(repr(float(value))))


def fingerprint_signals(origin: str, start: str, end: str, per_sku: dict, training_fp: str) -> str:
    h = hashlib.sha256()
    h.update(json.dumps({"v": SIGNALS_VERSION, "o": origin, "w": [start, end], "t": training_fp}).encode())
    for (sku, alm) in sorted(per_sku):
        s, d = per_sku[(sku, alm)]
        h.update(f"|{sku}|{alm}|{s}|{d}".encode())
    return h.hexdigest()


def compute_signals(train: TrainingData, origin: date, window: int = WINDOW_DAYS) -> Signals:
    """Suma y dias utiles de los `window` dias naturales que terminan en `origin`, por (sku, almacen).
    Dia util = venta observada o cero observado (no enmascarado ni sin registros)."""
    if train.cutoff != origin:
        raise ValueError("el conjunto de entrenamiento no termina en el origen pedido")
    start = origin - timedelta(days=window - 1)
    pairs = ds.pair_daily(train)
    w = pairs[(pairs["fecha"] >= start.isoformat()) & (pairs["fecha"] <= origin.isoformat())
              & pairs["estado"].isin([ds.VENTA, ds.CERO])]
    per: dict = {}
    for (sku, alm), g in w.groupby(["sku", "almacen"], sort=True):
        total = sum((to_fraction(v) for v in g["cantidad_base"].tolist()), Fraction(0))
        per[(str(sku), str(alm))] = (total, len(g))
    return Signals(origin=origin.isoformat(), window_start=start.isoformat(), window_end=origin.isoformat(),
                   per_sku=per, training_fingerprint=train.fingerprint,
                   fingerprint=fingerprint_signals(origin.isoformat(), start.isoformat(), origin.isoformat(), per,
                                                   train.fingerprint))


def fraction_text(f: Fraction) -> str:
    return str(f)           # "12", "3/7": exacto y reproducible


def parse_fraction(text: str) -> Fraction:
    return Fraction(text)


def exact_target(total: Fraction, days: int, horizon: int, safety_days: int) -> tuple[Fraction, int]:
    """(objetivo antes del techo, objetivo entero) = techo(horizon*media + safety_days*media), media = suma/dias."""
    if days <= 0:
        raise ValueError("dias utiles <= 0: no hay media operativa")
    raw = (horizon + safety_days) * total / days
    return raw, math.ceil(raw)
