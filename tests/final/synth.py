"""Mundo SINTETICO de T12: marzo-agosto en una base temporal df_test_<uuid>. Nunca datos reales ni reference_v1."""
from __future__ import annotations

import calendar
from collections.abc import Callable
from datetime import date
from pathlib import Path

from pipeline.data.calendar import EXCLUDED_DATES
from pipeline.data.importer import import_workbook
from tests.data.conftest import write_xlsx
from tests.generate.helpers import Spec, rows_for_month

MONTHS = {3: "marzo", 4: "abril", 5: "mayo", 6: "junio", 7: "julio", 8: "agosto"}


def qty_a(d: date) -> int:
    return 2 + d.day % 3


def qty_b(d: date) -> int:
    return 1 + d.day % 2


def specs(aug_scale: int = 1) -> dict[str, Spec]:
    """Productos sinteticos. `aug_scale` cambia SOLO las cantidades de agosto (para probar que lo futuro no entra)."""
    def a(d: date) -> int:
        return qty_a(d) * (aug_scale if d >= date(2026, 8, 1) else 1)

    def b(d: date) -> int:
        return qty_b(d) * (aug_scale if d >= date(2026, 8, 1) else 1)
    s: dict[str, Spec] = {}
    for i in range(4):
        s[f"910000{i}"] = Spec("CAT A", date(2026, 3, 1), qty=a)
    for i in range(4, 8):
        s[f"910000{i}"] = Spec("CAT B", date(2026, 3, 1), qty=b)
    s["9100010"] = Spec("CAT B", date(2026, 7, 10), qty=b)                      # historia corta
    s["9100011"] = Spec("CAT C", date(2026, 3, 1), date(2026, 6, 30), qty=a)    # deja de vender: ceros observados despues
    s["9100012"] = Spec("CAT A", date(2026, 3, 1), qty=a)                       # cambia de categoria en agosto
    s["9100013"] = Spec("", date(2026, 3, 1), qty=b)                            # sin categoria
    s["9100020"] = Spec("CAT A", date(2026, 8, 5), qty=a)                       # SKU NUEVO (primera venta en agosto)
    return s


def build(db, tmp: Path, *, aug_scale: int = 1, drop_aug_days: tuple[date, ...] = (date(2026, 8, 10),),
          months=(3, 4, 5, 6, 7, 8), relabel_in_august: bool = True) -> dict:
    """Importa un Excel sintetico por mes. Agosto omite `drop_aug_days` (dia sin ningun registro)."""
    sp = specs(aug_scale)
    reports, n0 = {}, 0
    for m in months:
        last = date(2026, m, calendar.monthrange(2026, m)[1])
        skip = set(EXCLUDED_DATES) | (set(drop_aug_days) if m == 8 else set())
        rows = rows_for_month(2026, m, last, sp, skip, n0)
        n0 += len(rows) + 1000
        if m == 8 and relabel_in_august:
            idx = {"ID_ARTICULO": 11, "GRUPO": 22}
            for r in rows:
                if r[idx["ID_ARTICULO"]] == 9100012:
                    r[idx["GRUPO"]] = " CAT C "
        path = write_xlsx(tmp / f"{MONTHS[m]}.xlsx", rows)
        reports[m] = import_workbook(path, db, expected_month=f"2026-{m:02d}")
        assert reports[m].estado == "completed", reports[m].error
    return reports


def make_run(db, out: Path, seal: Path, **kw):
    from pipeline.final.runner import FinalRun
    return FinalRun(db, out, seal_path=seal, require_commit=False, **kw)


FLAKY: Callable | None = None
