"""Ayudas de T10: ventas SINTETICAS importadas en bases temporales (df_test_<uuid>); nunca datos reales."""
from __future__ import annotations

import calendar
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from fractions import Fraction
from pathlib import Path

import pytest

from pipeline.data.calendar import EXCLUDED_DATES
from pipeline.data.importer import import_workbook
from tests.data.conftest import make_row, write_xlsx
from tests.publish.helpers import ARTIFACTS_OK, real_source

MONTH_NAMES = {3: "marzo", 4: "abril", 5: "mayo", 6: "junio", 7: "julio"}


@dataclass
class Spec:
    """Producto sintetico: vende `qty(dia)` unidades cada dia entre first y last (inclusive)."""
    cat: str
    first: date
    last: date | None = None
    qty: Callable[[date], int] = lambda d: 3
    almacen: int = 1


def qty_var(d: date) -> int:
    return 2 if d.day % 2 else 3


def npz_skus(n: int = 3) -> list[str]:
    """Primeros SKU del universo simulado real (para recomendaciones). Requiere artefactos."""
    return [str(s) for s in real_source().sim["skus"][:n]]


def default_specs(extra: dict[str, Spec] | None = None) -> dict[str, Spec]:
    jun30 = date(2026, 6, 30)
    specs = {
        "9000001": Spec("CAT B", date(2026, 3, 1), qty=lambda d: 1),                 # relleno: cubre el calendario
        "9000002": Spec("CAT B", date(2026, 6, 10), qty=lambda d: 2 if d.day % 2 == 0 else 0),   # historia corta
        "9000003": Spec("CAT A", date(2026, 3, 1), date(2026, 4, 30)),               # sin ventas en la ventana
        "9000004": Spec("", date(2026, 3, 1), jun30, qty=lambda d: 1),               # sin categoria
    }
    if ARTIFACTS_OK:
        for sku in npz_skus(2):
            specs[sku] = Spec("CAT A", date(2026, 3, 1), jun30, qty=qty_var)
    specs.update(extra or {})
    return specs


def rows_for_month(year: int, month: int, last_day: date, specs: dict[str, Spec], skip_days, n0: int) -> list:
    rows, n = [], n0
    for day in range(1, calendar.monthrange(year, month)[1] + 1):
        d = date(year, month, day)
        if d > last_day or d in skip_days:
            continue
        for sku, sp in specs.items():
            if d < sp.first or (sp.last and d > sp.last):
                continue
            q = sp.qty(d)
            if q <= 0:
                continue
            n += 1
            rows.append(make_row(ID_PEDIDO=n, SERIE_NUMERO=f"B{month}-{n}", ID_ARTICULO=int(sku), GRUPO=sp.cat,
                                 FECHA=datetime(year, month, day), CANTIDAD=q, CANTIDAD_UM_BASE=q,
                                 TOTAL_LINEA=q * 5.5, ID_ALMACEN=sp.almacen))
    return rows


def build_months(db, tmp_path: Path, *, through: date = date(2026, 6, 30), specs: dict[str, Spec] | None = None,
                 skip_days=frozenset(), months=(3, 4, 5, 6)) -> dict:
    """Importa un Excel sintetico por mes (marzo..junio por defecto). Devuelve {mes: ImportReport}."""
    specs = specs if specs is not None else default_specs()
    reports, n0 = {}, 0
    for m in months:
        rows = rows_for_month(2026, m, through, specs, skip_days, n0)
        n0 += len(rows) + 1000
        path = write_xlsx(tmp_path / f"{MONTH_NAMES[m]}.xlsx", rows)
        reports[m] = import_workbook(path, db, expected_month=f"2026-{m:02d}")
        assert reports[m].estado == "completed", reports[m].error
    return reports


def expected_signal(sp: Spec, origin: date, skip_days=frozenset()) -> tuple[Fraction, int]:
    """Suma y dias utiles de la ventana de 28 dias calculados A MANO (sin usar el pipeline)."""
    total, days = Fraction(0), 0
    for i in range(28):
        d = origin - timedelta(days=27 - i)
        if d in EXCLUDED_DATES or d in skip_days or d < sp.first:
            continue                                   # enmascarado, sin registros del dia o antes de la 1.a venta
        days += 1
        total += sp.qty(d) if not (sp.last and d > sp.last) else 0
    return total, days


needs_artifacts = pytest.mark.skipif(not ARTIFACTS_OK, reason="artefactos T07 reales no disponibles")


def patch_reference(monkeypatch, *, available: bool = True) -> None:
    """Evita re-verificar los artefactos en cada prueba (la verificacion real se prueba en tests/publish)."""
    from pipeline.generate import baseline
    if available and ARTIFACTS_OK:
        monkeypatch.setattr(baseline, "_load_reference", lambda: (real_source(), ""))
    else:
        monkeypatch.setattr(baseline, "_load_reference", lambda: (None, "artefactos T07 no verificados (prueba)"))
