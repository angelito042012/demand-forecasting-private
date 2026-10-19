"""Paquete derivado SINTETICO (14 libros .xlsx reales minimos + CSV/manifiesto) para el dataset de planificacion.

Los libros tienen la disposicion de los reales (hoja Hoja1, encabezado en la fila 2). El derivado se genera con la
re-normalizacion del propio modulo; la equivalencia con el script academico se prueba aparte (classify) y contra los
CSV reales en test_dataset_real.py. No contiene datos comerciales.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import shutil
from collections import Counter
from decimal import Decimal
from pathlib import Path

import pytest
from openpyxl import Workbook

from pipeline.plan.normalize import FIELDS, normalize_all, sha256_file

VENTAS = ["marzo", "abril", "mayo", "junio", "julio", "agosto", "setiembre"]
COMPRAS = ["compras marzo", "compras abril", "compra mayo", "compras junio", "compras julio", "compras agosto", "compras seitembre"]
MONTHS = {n: m for n, m in zip(VENTAS, range(3, 10), strict=True)}
MONTHS.update({n: m for n, m in zip(COMPRAS, range(3, 10), strict=True)})
HEADERS_V = ["ID_PEDIDO", "TIPO_DOC", "SERIE_NUMERO", "FECHA", "MONEDA", "ID_ARTICULO", "ARTICULO", "ID_ALMACEN", "CANTIDAD",
             "TOTAL_LINEA", "EQUIVALENCIA", "UM_BASE", "CANTIDAD_UM_BASE", "GRUPO", "VEN_ESTADO"]
HEADERS_C = ["ID_PEDIDO", "TIPO_DOC", "SERIE_NUMERO", "ID_PROVEEDOR", "FECHA", "MONEDA", "ID_ARTICULO", "ARTICULO", "ID_ALMACEN",
             "CANTIDAD", "TOTAL_LINEA", "EQUIVALENCIA", "UM_BASE", "CANTIDAD_UM_BASE", "GRUPO", "ESTADO"]
PEN = "SOLES (S/)"
USD = "$ DOLARES"
PRODUCTS = {"1001": "PRODUCTO UNO", "1002": "PRODUCTO DOS", "1003": "PRODUCTO TRES", "1004": "PRODUCTO CUATRO"}
GROUP_SIZE = 2


def line(kind, month, day, prod, qty=2, total=20, *, tipo="1", moneda=PEN, estado="ACTIVO", serie="F001-1", extra=None):
    base = {"ID_PEDIDO": f"P{month}{day}{prod}", "TIPO_DOC": tipo, "SERIE_NUMERO": serie, "FECHA": dt.datetime(2026, month, day),
            "MONEDA": moneda, "ID_ARTICULO": int(prod), "ARTICULO": PRODUCTS[prod], "ID_ALMACEN": 1, "CANTIDAD": qty,
            "TOTAL_LINEA": total, "EQUIVALENCIA": 1, "UM_BASE": "UND", "CANTIDAD_UM_BASE": qty, "GRUPO": f"CAT {prod[-1]}"}
    if kind == "ventas":
        base["VEN_ESTADO"] = estado
    else:
        base.update(ID_PROVEEDOR="900", ESTADO=estado)
    base.update(extra or {})
    return base


def default_books() -> dict[str, list[dict]]:
    books: dict[str, list[dict]] = {}
    for name in VENTAS:
        m = MONTHS[name]
        rows = []
        for p in ("1001", "1002", "1003"):
            rows += [line("ventas", m, 5, p, serie=f"B001-{p}5"), line("ventas", m, 15, p, serie=f"B001-{p}15")]
        rows.append(line("ventas", m, 20, "1001", -1, -10, tipo="7", serie="NC01-1"))      # nota de credito
        if m == 3:
            rows.append(line("ventas", m, 21, "1002", 0.5, 7.5, serie="B001-frac"))        # cantidad fraccionaria
        if m == 4:
            rows.append(line("ventas", m, 3, "1001", serie="B001-d3"))                   # dia enmascarado 03/04
        if m == 9:
            rows.append(line("ventas", m, 30, "1001", serie="B001-cut"))                 # ultimo dia con cobertura
            rows.append(line("ventas", m, 30, "1004", serie="B001-p4"))
            rows.append(line("ventas", m, 22, "1002", estado="ANULADO", serie="B001-anu"))                      # cuarentena
            rows.append(line("ventas", m, 23, "1003", None, 10, serie="B001-sin", extra={"CANTIDAD_UM_BASE": None}))  # dato faltante
        books[name] = rows
    for name in COMPRAS:
        m = MONTHS[name]
        rows = [line("compras", m, 2, p, 24, 100, serie=f"F002-{p}") for p in ("1001", "1002", "1003")]
        rows.append(line("compras", m, 3, "1001", 6, 0, serie="F002-gratis"))               # sin cargo registrado
        if m == 7:
            rows.append(line("compras", m, 4, "1002", 12, 50, moneda=USD, serie="F002-usd"))  # otra moneda
        if m == 6:
            dup = line("compras", m, 6, "1003", 8, 40, serie="F002-dup")
            rows += [dup, dict(dup)]                                                      # copia exacta
        books[name] = rows
    return books


def write_book(path: Path, kind: str, rows: list[dict]) -> None:
    headers = HEADERS_V if kind == "ventas" else HEADERS_C
    wb = Workbook()
    ws = wb.active
    ws.title = "Hoja1"
    ws["A1"] = "REPORTE SINTETICO"
    for c, h in enumerate(headers, start=1):
        ws.cell(row=2, column=c, value=h)
    for r, row in enumerate(rows, start=3):
        for c, h in enumerate(headers, start=1):
            ws.cell(row=r, column=c, value=row.get(h))
    wb.save(path)


def _ser(v):
    if isinstance(v, (dt.date, dt.datetime)):
        return v.isoformat()
    return str(v)


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r[k] is None else _ser(r[k])) for k in fields})


def build_package(root: Path, books: dict[str, list[dict]] | None = None, *, with_audit: bool = True) -> Path:
    """Crea root/pkg (paquete) y, si with_audit, root/auditoria_14_excel/audit.json (hermano, como el real)."""
    books = books if books is not None else default_books()
    pkg = root / "pkg"
    orig, norm, grp = pkg / "00_originales", pkg / "01_normalizados", pkg / "02_grupo"
    for d in (orig, norm, grp):
        d.mkdir(parents=True, exist_ok=True)
    for name, rows in books.items():
        write_book(orig / f"{name}.xlsx", "compras" if name.startswith("compra") else "ventas", rows)
    files = sorted(orig.glob("*.xlsx"))
    digests = {p.name: sha256_file(p) for p in files}
    recs, sources, eligible = normalize_all(files, digests, GROUP_SIZE)
    classes = Counter(r["clasificacion"] for r in recs)
    parts = {"ventas": ("VENTA",), "compras": ("COMPRA", "COMPRA_SIN_CARGO_REGISTRADO"), "creditos": ("CREDITO",),
             "cuarentena": ("CUARENTENA",)}
    for name, cl in parts.items():
        write_csv(norm / f"{name}.csv", [r for r in recs if r["clasificacion"] in cl], FIELDS)
    chosen = sorted({(r["producto_id"], r["almacen"], r["unidad"]) for r in recs if r["incluido_grupo"]})
    write_csv(grp / "productos.csv", [{"producto_id": a, "almacen": b, "unidad": c, "seleccionado": True} for a, b, c in chosen],
              ["producto_id", "almacen", "unidad", "seleccionado"])
    manifest = {"version": "academico_v1", "window_start": "2026-03-01", "window_end": "2026-09-30", "group_size": GROUP_SIZE,
                "eligible_products": eligible, "source_rows": len(recs), "class_counts": dict(classes),
                "sources": [{**s, "importes_por_moneda": {k: str(v) for k, v in s["importes_por_moneda"].items()}} for s in sources]}
    (pkg / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    if with_audit:
        a = root / "auditoria_14_excel"
        a.mkdir(exist_ok=True)
        (a / "audit.json").write_text(json.dumps({"files": [{"file": n, "sha256": h} for n, h in digests.items()]}), encoding="utf-8")
    return pkg


def audit_of(pkg: Path) -> Path:
    return pkg.parent / "auditoria_14_excel" / "audit.json"


def edit_csv(pkg: Path, name: str, fn) -> None:
    path = pkg / "01_normalizados" / name
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fields, rows = reader.fieldnames, list(reader)
    out = fn(rows)
    write_csv_raw(path, fields, rows if out is None else out)


def write_csv_raw(path: Path, fields, rows) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def edit_manifest(pkg: Path, fn) -> None:
    p = pkg / "manifest.json"
    m = json.loads(p.read_text(encoding="utf-8"))
    fn(m)
    p.write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")


@pytest.fixture(scope="session")
def _base(tmp_path_factory):
    return build_package(tmp_path_factory.mktemp("plan_base"))


@pytest.fixture()
def pkg(_base, tmp_path):
    """Copia mutable del paquete base (con su audit hermano)."""
    root = tmp_path / "root"
    shutil.copytree(_base.parent, root)
    return root / "pkg"


@pytest.fixture()
def db():
    from tests.publish.helpers import temp_db
    with temp_db() as d:
        yield d


def total_qty(docs) -> Decimal:
    return sum((Decimal(d["cantidad"]) for d in docs if d["cantidad"] is not None), Decimal(0))
