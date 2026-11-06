"""Importacion operativa de ventas (Excel) y stock (conteo CSV) sin mongorestore.

    python -m scripts.import_operativo preview --ventas noviembre.xlsx --db <base> [--uri mongodb://...]
    python -m scripts.import_operativo importar --ventas noviembre.xlsx --db <base> [--uri mongodb://...]
    python -m scripts.import_operativo importar --ventas noviembre.xlsx --stock <carpeta_conteo> --db <base>
    python -m scripts.import_operativo activar --db <base> --origin 2026-10-20

Modos:
  preview   — valida el archivo y muestra que se importaria, sin escribir nada.
  importar  — valida e importa. Acepta meses operativos (agosto-diciembre) ademas de los academicos.
  activar   — regenera el pronostico/plan a partir de los datos ya importados.

Usa la politica_operativa de config/t10_config.json (meses ampliados, sin reserva de agosto).
No toca bases protegidas. Datos importados quedan etiquetados como operativos.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

from pymongo import MongoClient

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "t10_config.json"
DEFAULT_URI = "mongodb://127.0.0.1:27017"


def load_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def operational_months(cfg: dict) -> list[str]:
    dev = cfg["politica_desarrollo"]["meses_permitidos_de_carga"]
    ops = cfg.get("politica_operativa", {}).get("meses_adicionales_permitidos", [])
    return dev + ops


PROTECTED_DBS = frozenset({"demand_forecasting_dev", "demand_forecasting_v2", "demand_forecasting_pub"})


def connect(uri: str, db_name: str):
    if db_name in PROTECTED_DBS:
        print(f"ERROR: la base {db_name!r} esta protegida. Use una base operativa.", file=sys.stderr)
        sys.exit(1)
    client = MongoClient(uri)
    return client[db_name]


def cmd_preview(args):
    cfg = load_config()
    allowed = tuple(operational_months(cfg))

    if args.ventas:
        _preview_ventas(Path(args.ventas), allowed, cfg)
    if args.stock:
        _preview_stock(Path(args.stock))
    if not args.ventas and not args.stock:
        print("ERROR: indique al menos --ventas o --stock.", file=sys.stderr)
        sys.exit(1)


def _preview_ventas(path: Path, allowed: tuple[str, ...], cfg: dict):
    from pipeline.jobs.xlsx_check import XlsxRejected, has_zip_signature, inspect_xlsx

    print(f"\n=== Preview de ventas: {path.name} ===\n")
    if not path.is_file():
        print(f"ERROR: archivo no encontrado: {path}", file=sys.stderr)
        sys.exit(1)

    if not has_zip_signature(path):
        print("ERROR: el archivo no tiene firma ZIP valida (.xlsx).", file=sys.stderr)
        sys.exit(1)

    up = cfg["subidas"]
    try:
        info = inspect_xlsx(
            path,
            max_entries=int(up["max_entradas_zip"]),
            max_expanded=int(up["tam_max_expandido_bytes"]),
            max_rows=int(up["max_filas_hoja"]),
            allowed_months=allowed,
        )
    except XlsxRejected as exc:
        print(f"RECHAZADO [{exc.code}]: {exc.message}", file=sys.stderr)
        sys.exit(1)

    print(f"  Mes detectado:       {info.month}")
    print(f"  Entradas ZIP:        {info.entries}")
    print(f"  Tamano declarado:    {info.declared_bytes:,} bytes")

    from pipeline.data.importer import read_rows, sha256_file
    sha = sha256_file(path)
    print(f"  SHA-256:             {sha[:16]}...")

    rows = read_rows(path)
    print(f"  Filas de datos:      {len(rows)}")

    dates = set()
    for _n, rec in rows:
        f = rec.get("FECHA")
        if isinstance(f, (datetime, date)):
            d = f.date() if isinstance(f, datetime) else f
            dates.add(d)
    if dates:
        print(f"  Rango de fechas:     {min(dates)} a {max(dates)}")
        print(f"  Dias distintos:      {len(dates)}")

    print(f"\n  Resultado: APTO para importacion operativa.")
    if info.month >= "2026-08":
        print(f"  Nota: mes {info.month} es operativo (fuera del periodo academico).")


def _preview_stock(stock_dir: Path):
    print(f"\n=== Preview de stock: {stock_dir} ===\n")
    if not stock_dir.is_dir():
        print(f"ERROR: directorio no encontrado: {stock_dir}", file=sys.stderr)
        sys.exit(1)

    csv_path = stock_dir / "conteo_reportado.csv"
    review_path = stock_dir / "review.json"

    if not csv_path.is_file():
        print(f"ERROR: falta {csv_path.name} en el directorio.", file=sys.stderr)
        sys.exit(1)

    import csv as csv_mod
    with open(csv_path, encoding="utf-8-sig") as fh:
        reader = csv_mod.DictReader(fh)
        rows = list(reader)
    print(f"  Archivo CSV:         {csv_path.name}")
    print(f"  Filas:               {len(rows)}")
    if rows:
        cols = list(rows[0].keys())
        print(f"  Columnas:            {', '.join(cols[:8])}{'...' if len(cols) > 8 else ''}")

    if review_path.is_file():
        review = json.loads(review_path.read_text(encoding="utf-8"))
        print(f"  review.json:         presente")
        if "count_date" in review:
            print(f"  Fecha del conteo:    {review['count_date']}")
    else:
        print(f"  review.json:         NO encontrado (requerido para importar)")

    print(f"\n  Resultado: {'APTO' if review_path.is_file() else 'INCOMPLETO (falta review.json)'}")


def cmd_importar(args):
    cfg = load_config()
    allowed = tuple(operational_months(cfg))
    db = connect(args.uri, args.db)

    if not args.ventas and not args.stock:
        print("ERROR: indique al menos --ventas o --stock.", file=sys.stderr)
        sys.exit(1)

    if args.ventas:
        _importar_ventas(Path(args.ventas), allowed, cfg, db)

    if args.stock:
        _importar_stock(Path(args.stock), db, args)


def _importar_ventas(path: Path, allowed: tuple[str, ...], cfg: dict, db):
    from pipeline.data.importer import import_workbook, sha256_file
    from pipeline.jobs.xlsx_check import XlsxRejected, inspect_xlsx

    print(f"\n=== Importando ventas: {path.name} ===\n")

    up = cfg["subidas"]
    try:
        info = inspect_xlsx(
            path,
            max_entries=int(up["max_entradas_zip"]),
            max_expanded=int(up["tam_max_expandido_bytes"]),
            max_rows=int(up["max_filas_hoja"]),
            allowed_months=allowed,
        )
    except XlsxRejected as exc:
        print(f"RECHAZADO [{exc.code}]: {exc.message}", file=sys.stderr)
        sys.exit(1)

    print(f"  Mes: {info.month}")
    print(f"  Importando...")

    rep = import_workbook(path, db, expected_month=info.month)

    print(f"  Estado:              {rep.estado}")
    print(f"  Filas leidas:        {rep.filas_leidas}")
    print(f"  Ventas aceptadas:    {rep.ventas_aceptadas}")
    print(f"  Notas de credito:    {rep.notas_credito}")
    print(f"  Rechazadas:          {rep.rechazadas}")
    print(f"  Insertadas:          {rep.insertadas}")
    print(f"  Ya existentes:       {rep.ya_existentes}")
    print(f"  En conflicto:        {rep.en_conflicto}")
    print(f"  Import ID:           {rep.import_id}")

    if rep.noop:
        print(f"\n  Este archivo ya estaba importado (sin cambios).")
    elif rep.estado == "completed":
        print(f"\n  Importacion completada exitosamente.")
    elif rep.estado == "completed_with_conflicts":
        print(f"\n  ATENCION: importacion con {rep.en_conflicto} conflictos pendientes.")
    else:
        print(f"\n  ADVERTENCIA: estado inesperado '{rep.estado}'.")


def _importar_stock(stock_dir: Path, db, args):
    print(f"\n=== Importando stock: {stock_dir} ===\n")

    csv_path = stock_dir / "conteo_reportado.csv"
    review_path = stock_dir / "review.json"
    if not csv_path.is_file() or not review_path.is_file():
        print("ERROR: el directorio debe contener conteo_reportado.csv y review.json.", file=sys.stderr)
        sys.exit(1)

    review = json.loads(review_path.read_text(encoding="utf-8"))
    count_date = review.get("count_date", "")
    sales_end = review.get("sales_history_end", "")

    group_csv = stock_dir / "grupo_50.csv"
    if not group_csv.is_file():
        alt = ROOT / "artifacts" / "private" / "datos_preparados_v1" / "grupo_50.csv"
        if alt.is_file():
            group_csv = alt
        else:
            print("ERROR: falta grupo_50.csv (lista de 50 productos).", file=sys.stderr)
            sys.exit(1)

    from pipeline.inventory.reported_count import run as run_stock_import
    rep = run_stock_import(
        count_dir=str(stock_dir),
        group_csv=str(group_csv),
        db=db,
        sales_history_end=sales_end or "2026-09-30",
    )

    print(f"  Accion:              {rep.get('action', 'N/A')}")
    print(f"  Snapshot ID:         {rep.get('snapshot_id', 'N/A')}")
    print(f"  Items:               {rep.get('items', 'N/A')}")
    print(f"  Con existencia:      {rep.get('con_existencia', 'N/A')}")
    print(f"  Sin existencia:      {rep.get('sin_existencia', 'N/A')}")
    print(f"  Fecha conteo:        {count_date}")
    print(f"\n  Importacion de stock completada.")


def cmd_activar(args):
    cfg = load_config()
    db = connect(args.uri, args.db)

    origin = date.fromisoformat(args.origin)
    ops = cfg.get("politica_operativa", {})
    horizon = ops.get("horizonte_maximo", 21)
    method = ops.get("metodos_permitidos", ["promedio_28"])[0]

    print(f"\n=== Activando pronostico ===\n")
    print(f"  Origen:    {origin}")
    print(f"  Horizonte: {horizon} dias")
    print(f"  Metodo:    {method}")

    from pipeline.generate.baseline import generate_and_publish
    result = generate_and_publish(db, origin, horizon, method, cfg=cfg)

    print(f"  Run ID:    {result.get('run_id', 'N/A')}")
    print(f"  Estado:    {result.get('status', 'N/A')}")
    print(f"\n  Pronostico generado y publicado.")


def main():
    parser = argparse.ArgumentParser(
        description="Importacion operativa de ventas y stock",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="comando")

    # preview
    p_preview = sub.add_parser("preview", help="Validar sin escribir")
    p_preview.add_argument("--ventas", help="Archivo .xlsx de ventas")
    p_preview.add_argument("--stock", help="Directorio con conteo_reportado.csv y review.json")

    # importar
    p_import = sub.add_parser("importar", help="Validar e importar")
    p_import.add_argument("--ventas", help="Archivo .xlsx de ventas")
    p_import.add_argument("--stock", help="Directorio con conteo_reportado.csv y review.json")
    p_import.add_argument("--uri", default=DEFAULT_URI, help="URI de MongoDB")
    p_import.add_argument("--db", required=True, help="Nombre de la base de datos")

    # activar
    p_act = sub.add_parser("activar", help="Regenerar pronostico tras importar")
    p_act.add_argument("--uri", default=DEFAULT_URI, help="URI de MongoDB")
    p_act.add_argument("--db", required=True, help="Nombre de la base de datos")
    p_act.add_argument("--origin", required=True, help="Fecha de origen YYYY-MM-DD")

    args = parser.parse_args()
    if args.comando == "preview":
        cmd_preview(args)
    elif args.comando == "importar":
        cmd_importar(args)
    elif args.comando == "activar":
        cmd_activar(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
