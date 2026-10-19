"""T19 §8 — comprobacion DESCRIPTIVA del salto de `promedio_28` a un mes objetivo (no es T12 ni validacion de noviembre).

Origen O (31/08 o 31/07): media exacta `promedio_28` de las ventas brutas de los 28 dias naturales que terminan en O
(dias enmascarados fuera del denominador) x 30 dias de septiembre, contra las ventas reales de septiembre (usadas SOLO
para evaluar, nunca como entrada del origen). Sin seleccion de modelos, sin agosto como entrada del origen 31/07, sin el
conteo de octubre. Septiembre ya fue inspeccionado: no es una prueba final independiente y no valida noviembre.
"""
from __future__ import annotations

import csv
from datetime import date, timedelta
from fractions import Fraction
from pathlib import Path

MASK_DAYS = frozenset({date(2026, 4, 3), date(2026, 4, 12), date(2026, 6, 7)})
WINDOW = 28


def _d(s: str) -> date:
    return date.fromisoformat(s)


def read_sales(csv_path: Path, products: set[str]) -> dict[str, dict[date, Fraction]]:
    """Ventas brutas por producto y dia desde `ventas.csv` normalizado (solo clase VENTA, almacen 1, UND)."""
    out: dict[str, dict[date, Fraction]] = {p: {} for p in products}
    with Path(csv_path).open("r", encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            if r["clasificacion"] != "VENTA" or r["producto_id"] not in out or r["unidad"] != "UND" or r["almacen"] != "1":
                continue
            day = _d(r["fecha"])
            out[r["producto_id"]][day] = out[r["producto_id"]].get(day, Fraction(0)) + Fraction(r["cantidad"])
    return out


def promedio_28(sales: dict[date, Fraction], origin: date) -> tuple[Fraction, Fraction, int]:
    """(media diaria, suma, dias validos) de los 28 dias naturales que terminan en `origin`; enmascarados fuera."""
    days = [origin - timedelta(days=i) for i in range(WINDOW)]
    valid = [d for d in days if d not in MASK_DAYS]
    total = sum((sales.get(d, Fraction(0)) for d in valid), Fraction(0))
    return total / len(valid), total, len(valid)


def month_total(sales: dict[date, Fraction], first: date, last: date) -> Fraction:
    return sum((v for d, v in sales.items() if first <= d <= last), Fraction(0))


def evaluate(sales_by_product: dict[str, dict[date, Fraction]], origin: date, first: date, last: date) -> dict:
    """Metricas descriptivas del total mensual previsto frente al real, por producto y agregadas."""
    ndays = (last - first).days + 1
    rows = []
    for pid, s in sorted(sales_by_product.items()):
        m, _, _ = promedio_28(s, origin)
        f, a = m * ndays, month_total(s, first, last)
        rows.append((pid, f, a))
    tot_a = sum((a for _, _, a in rows), Fraction(0))
    tot_f = sum((f for _, f, _ in rows), Fraction(0))
    abs_err = sum((abs(f - a) for _, f, a in rows), Fraction(0))
    pos = [(f, a) for _, f, a in rows if a > 0]
    mape = sum((abs(f - a) / a for f, a in pos), Fraction(0)) / len(pos) if pos else None

    def fl(x):
        return None if x is None else round(float(x), 6)
    return {
        "origen": origin.isoformat(), "objetivo": f"{first.isoformat()}..{last.isoformat()}", "dias_objetivo": ndays,
        "separacion_dias_origen_a_fin_objetivo": (last - origin).days, "productos": len(rows),
        "total_previsto": fl(tot_f), "total_real": fl(tot_a), "wape": fl(abs_err / tot_a) if tot_a else None,
        "sesgo_relativo": fl((tot_f - tot_a) / tot_a) if tot_a else None, "mae_por_producto": fl(abs_err / len(rows)),
        "mape": fl(mape), "mape_cobertura": f"{len(pos)}/{len(rows)}",
        "productos_con_real_cero": sum(1 for _, _, a in rows if a == 0),
        "productos_con_prevision_cero": sum(1 for _, f, _ in rows if f == 0),
        "r2": "no se informa (no aporta a totales mensuales de 50 productos heterogeneos)",
    }
