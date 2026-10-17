"""Calendario de negocio (America/Lima) y mascara de exclusion.

EXCLUDED_DATES son fechas que el usuario pidio omitir del entrenamiento
supervisado y de las metricas (DECISIONES_DATOS.md). Es SOLO una mascara:
no elimina filas, no genera ventas cero y NO implica cierre de la tienda.
Un rezago de siete dias sigue siendo siete dias naturales.
"""
from __future__ import annotations

import calendar as _stdcal
from collections.abc import Iterable
from datetime import date, datetime

TIMEZONE = "America/Lima"

EXCLUDED_DATES = frozenset({date(2026, 4, 3), date(2026, 4, 12), date(2026, 6, 7)})

# Agosto 2026 queda reservado como test final: no se usa para entrenar,
# elegir modelos, categorias ni hiperparametros.
FINAL_TEST_START = date(2026, 8, 1)
FINAL_TEST_END = date(2026, 8, 31)
LAST_TRAIN_DATE = date(2026, 7, 31)  # corte reservado


def to_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def is_excluded(value) -> bool:
    """True si la fecha esta en la mascara de exclusion (no implica cierre)."""
    return to_date(value) in EXCLUDED_DATES


def is_final_test(value) -> bool:
    d = to_date(value)
    return FINAL_TEST_START <= d <= FINAL_TEST_END


def month_days(year: int, month: int) -> list[date]:
    """Todos los dias naturales del mes (sin comprimir el calendario)."""
    return [date(year, month, d) for d in range(1, _stdcal.monthrange(year, month)[1] + 1)]


def exclusion_mask(dates: Iterable) -> list[bool]:
    """Mascara booleana alineada con `dates`; no altera ni elimina elementos."""
    return [is_excluded(d) for d in dates]
