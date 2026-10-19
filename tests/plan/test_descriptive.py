"""T19 §8 descriptivo: calculo exacto a mano, enmascarado y ausencia de fuga (los reales del mes no entran al origen)."""
from __future__ import annotations

from datetime import date, timedelta
from fractions import Fraction

from pipeline.plan.descriptive import evaluate, month_total, promedio_28


def _flat(per_day, start, end):
    out, d = {}, start
    while d <= end:
        out[d] = Fraction(per_day)
        d += timedelta(days=1)
    return out


def test_promedio_28_exacto_y_ventana():
    s = _flat(2, date(2026, 8, 4), date(2026, 8, 31))          # 28 dias a 2/dia
    s[date(2026, 8, 3)] = Fraction(1000)                        # fuera de la ventana: no cuenta
    m, total, days = promedio_28(s, date(2026, 8, 31))
    assert (m, total, days) == (Fraction(2), Fraction(56), 28)


def test_dias_enmascarados_salen_del_denominador():
    s = _flat(3, date(2026, 5, 11), date(2026, 6, 7))           # ventana 11/05..07/06 incluye 07/06 enmascarado
    m, total, days = promedio_28(s, date(2026, 6, 7))
    assert days == 27 and total == Fraction(81) and m == Fraction(3)


def test_evaluate_sin_fuga_y_metricas():
    a = _flat(2, date(2026, 8, 4), date(2026, 8, 31))
    a.update(_flat(5, date(2026, 9, 1), date(2026, 9, 30)))     # reales de septiembre: 150
    b = _flat(1, date(2026, 8, 4), date(2026, 8, 31))           # real septiembre 0 (sin ventas)
    r = evaluate({"A": a, "B": b}, date(2026, 8, 31), date(2026, 9, 1), date(2026, 9, 30))
    # previsto A = 2*30 = 60 (real 150), B = 1*30 = 30 (real 0): error abs 90 + 30, total real 150
    assert r["total_previsto"] == 90.0 and r["total_real"] == 150.0
    assert r["wape"] == 0.8 and r["sesgo_relativo"] == -0.4
    assert r["mape"] == 0.6 and r["mape_cobertura"] == "1/2" and r["productos_con_real_cero"] == 1
    # los reales de septiembre no cambian la prevision del origen 31/08
    a2 = dict(a)
    a2[date(2026, 9, 15)] = Fraction(10_000)
    assert promedio_28(a2, date(2026, 8, 31)) == promedio_28(a, date(2026, 8, 31))
    assert month_total(a2, date(2026, 9, 1), date(2026, 9, 30)) == 150 - 5 + 10_000


def test_origen_31_07_no_usa_agosto():
    s = _flat(2, date(2026, 7, 4), date(2026, 7, 31))
    s.update(_flat(100, date(2026, 8, 1), date(2026, 8, 31)))   # agosto muy distinto: no entra al origen 31/07
    s.update(_flat(2, date(2026, 9, 1), date(2026, 9, 30)))
    r = evaluate({"A": s}, date(2026, 7, 31), date(2026, 9, 1), date(2026, 9, 30))
    assert r["total_previsto"] == 60.0 and r["wape"] == 0.0 and r["separacion_dias_origen_a_fin_objetivo"] == 61
