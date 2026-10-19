"""Equivalencia de la copia fiel (pipeline.plan.normalize) con scripts.prepare_academic_data sobre casos sinteticos."""
from __future__ import annotations

import itertools
from datetime import date, datetime
from decimal import Decimal

import pytest

from pipeline.plan import normalize as n
from scripts import prepare_academic_data as s


def base(**ch):
    r = {"FECHA": datetime(2026, 3, 1), "CANTIDAD": 12, "EQUIVALENCIA": 1, "CANTIDAD_UM_BASE": 12, "TOTAL_LINEA": 20,
         "ESTADO": "ACTIVO", "VEN_ESTADO": "ACTIVO", "ID_ARTICULO": 1, "ID_ALMACEN": 1, "UM_BASE": "UND", "TIPO_DOC": 1}
    r.update(ch)
    return r


VARIANTS = [{}, {"TOTAL_LINEA": 0}, {"TOTAL_LINEA": -2}, {"CANTIDAD": 0.01, "CANTIDAD_UM_BASE": 0}, {"FECHA": "x"}, {"FECHA": date(2026, 3, 2)},
            {"TIPO_DOC": 7, "CANTIDAD": -1, "CANTIDAD_UM_BASE": -1, "TOTAL_LINEA": -2}, {"ESTADO": "ANULADO", "VEN_ESTADO": "anulado"},
            {"CANTIDAD": None}, {"EQUIVALENCIA": 0}, {"EQUIVALENCIA": 12, "CANTIDAD": 1}, {"ID_ARTICULO": ""}, {"UM_BASE": None},
            {"CANTIDAD": True}, {"CANTIDAD_UM_BASE": "12"}, {"CANTIDAD": 0, "CANTIDAD_UM_BASE": 0}, {"TIPO_DOC": "7"}]


@pytest.mark.parametrize(("kind", "ch"), list(itertools.product(("ventas", "compras"), VARIANTS)))
def test_classify_matches_script(kind, ch):
    assert n.classify(kind, base(**ch)) == s.classify(kind, base(**ch))


@pytest.mark.parametrize("v", [None, "", 1, 1.0, 2.5, "ab", " 7 ", Decimal("3.0"), float("nan"), True, 10**15, 1e-7])
def test_text_number_match_script(v):
    assert n.text(v) == s.text(v)
    a, b = n.number(v), s.number(v)
    assert (a is None and b is None) or a == b or (a.is_nan() and b.is_nan())


@pytest.mark.parametrize("v", [None, "S/", "SOLES (S/)", "soles", "$ DOLARES", "US$ DOLAR", "EUR", 3])
def test_currency_matches_script(v):
    assert n.currency(v) == s.currency(v)


def test_constants_match_script():
    assert n.FIELDS == s.FIELDS and n.START == s.START and n.END == s.END
    assert n.EXCLUDED_FORECAST_DAYS == s.EXCLUDED_FORECAST_DAYS and n.SELECTION_CUTOFF == s.CUTOFF and n.VERSION == s.VERSION
