"""Cálculo del indicador de rotación de inventario (tarea 9).

Lee ventas de plan_sales y stock de inventory_reconstructed_items, calcula rotación
mensual por producto y por categoría, y reporta días de cobertura.

    python -m scripts.calc_rotation --db <base> --month 2026-09
    python -m scripts.calc_rotation --db <base> --month 2026-09 --format json
    python -m scripts.calc_rotation --db <base> --month 2026-09 --by-category
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _parse_month(s: str) -> tuple[date, date, int]:
    y, m = s.split("-")
    first = date(int(y), int(m), 1)
    if int(m) == 12:
        last = date(int(y) + 1, 1, 1) - timedelta(days=1)
    else:
        last = date(int(y), int(m) + 1, 1) - timedelta(days=1)
    n_days = (last - first).days + 1
    return first, last, n_days


def load_sales(db, first: date, last: date) -> dict[str, int]:
    """Ventas brutas por producto en el período (unidades, clase VENTA, almacén 1)."""
    coll = db["plan_sales"]
    pipeline = [
        {"$match": {
            "clase": "VENTA",
            "almacen": "1",
            "fecha": {"$gte": first.isoformat(), "$lte": last.isoformat()},
        }},
        {"$group": {"_id": "$producto_id", "total": {"$sum": "$cantidad"}}},
    ]
    return {doc["_id"]: int(doc["total"]) for doc in coll.aggregate(pipeline)}


def load_stock(db) -> dict[str, dict]:
    """Stock reconstruido vigente: {producto_id: {libre, categoria, producto}}."""
    snap = db["inventory_reconstructed_snapshots"].find_one(
        {"status": "current"}, {"snapshot_id": 1, "_id": 0},
        sort=[("version", -1)],
    )
    if snap is None:
        return {}
    items = db["inventory_reconstructed_items"].find(
        {"snapshot_id": snap["snapshot_id"]},
        {"producto_id": 1, "libre": 1, "categoria": 1, "producto": 1, "_id": 0},
    )
    return {
        i["producto_id"]: {
            "libre": int(i["libre"]),
            "categoria": i.get("categoria", ""),
            "producto": i.get("producto", ""),
        }
        for i in items
    }


def classify_rotation(rotation: float | None) -> str:
    if rotation is None or rotation == 0:
        return "sin_movimiento"
    if rotation > 4.0:
        return "muy_alta"
    if rotation > 2.0:
        return "alta"
    if rotation > 1.0:
        return "media"
    if rotation > 0.5:
        return "baja"
    return "muy_baja"


def coverage_days(rotation: float | None, month_days: int) -> float | None:
    if rotation is None or rotation <= 0:
        return None
    return round(month_days / rotation, 1)


def compute_rotation(sales: dict[str, int], stock: dict[str, dict],
                     month_days: int) -> list[dict]:
    all_products = sorted(set(sales.keys()) | set(stock.keys()))
    rows = []
    for pid in all_products:
        s_info = stock.get(pid, {})
        ventas = sales.get(pid, 0)
        existencia = s_info.get("libre", 0)

        if existencia > 0:
            rotation = round(ventas / existencia, 4)
        elif ventas > 0:
            rotation = None  # stock 0 pero hubo ventas: rotación infinita
        else:
            rotation = 0.0

        rows.append({
            "producto_id": pid,
            "producto": s_info.get("producto", ""),
            "categoria": s_info.get("categoria", ""),
            "ventas_periodo": ventas,
            "stock": existencia,
            "rotacion": rotation,
            "clasificacion": classify_rotation(rotation),
            "dias_cobertura": coverage_days(rotation, month_days),
        })
    return rows


def compute_by_category(rows: list[dict], month_days: int) -> list[dict]:
    cats: dict[str, dict] = defaultdict(lambda: {"ventas": 0, "stock": 0, "productos": 0})
    for r in rows:
        cat = r["categoria"] or "SIN_CATEGORIA"
        cats[cat]["ventas"] += r["ventas_periodo"]
        cats[cat]["stock"] += r["stock"]
        cats[cat]["productos"] += 1

    result = []
    for cat in sorted(cats.keys()):
        c = cats[cat]
        if c["stock"] > 0:
            rot = round(c["ventas"] / c["stock"], 4)
        elif c["ventas"] > 0:
            rot = None
        else:
            rot = 0.0
        result.append({
            "categoria": cat,
            "productos": c["productos"],
            "ventas_periodo": c["ventas"],
            "stock": c["stock"],
            "rotacion": rot,
            "clasificacion": classify_rotation(rot),
            "dias_cobertura": coverage_days(rot, month_days),
        })
    return result


def print_table(rows: list[dict], columns: list[tuple[str, str, int]]) -> None:
    header = "  ".join(f"{label:>{w}}" if w > 0 else f"{label:<{-w}}" for label, _, w in columns)
    print(f"  {header}")
    print(f"  {'-' * len(header)}")
    for r in rows:
        parts = []
        for _, key, w in columns:
            v = r.get(key)
            if v is None:
                s = "—"
            elif isinstance(v, float):
                s = f"{v:.4f}" if abs(v) < 100 else f"{v:.1f}"
            elif isinstance(v, int):
                s = f"{v:,}"
            else:
                s = str(v)
            parts.append(f"{s:>{w}}" if w > 0 else f"{s:<{-w}}")
        print(f"  {'  '.join(parts)}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Indicador de rotación de inventario")
    ap.add_argument("--db", required=True, help="Base de datos MongoDB")
    ap.add_argument("--uri", default="mongodb://127.0.0.1:27017")
    ap.add_argument("--month", required=True, help="Mes de ventas YYYY-MM")
    ap.add_argument("--by-category", action="store_true", help="Agrupar por categoría")
    ap.add_argument("--format", choices=["table", "json"], default="table")
    ap.add_argument("--sort", choices=["rotacion", "ventas", "stock", "producto_id"],
                    default="rotacion", help="Criterio de ordenamiento")
    args = ap.parse_args(argv)

    from pymongo import MongoClient
    client = MongoClient(args.uri)
    db = client[args.db]

    first, last, month_days = _parse_month(args.month)

    print(f"\n  Rotación de inventario — {args.month} ({first} a {last}, {month_days} días)")
    print(f"  Stock: snapshot reconstruido vigente\n")

    sales = load_sales(db, first, last)
    stock = load_stock(db)

    if not stock:
        print("  ERROR: no hay snapshot de existencia reconstruida vigente.", file=sys.stderr)
        client.close()
        return 1

    rows = compute_rotation(sales, stock, month_days)

    total_ventas = sum(r["ventas_periodo"] for r in rows)
    total_stock = sum(r["stock"] for r in rows)
    with_sales = sum(1 for r in rows if r["ventas_periodo"] > 0)
    with_stock = sum(1 for r in rows if r["stock"] > 0)
    no_movement = sum(1 for r in rows if r["clasificacion"] == "sin_movimiento")

    print(f"  Productos: {len(rows)} | Con ventas: {with_sales} | Con stock: {with_stock}")
    print(f"  Ventas totales: {total_ventas:,} u | Stock total: {total_stock:,} u")
    if total_stock > 0:
        rot_global = total_ventas / total_stock
        print(f"  Rotación global: {rot_global:.4f} ({coverage_days(rot_global, month_days):.1f} días cobertura)")
    print(f"  Sin movimiento: {no_movement}")
    print()

    dist = defaultdict(int)
    for r in rows:
        dist[r["clasificacion"]] += 1
    print("  Distribución:")
    for cls in ["muy_alta", "alta", "media", "baja", "muy_baja", "sin_movimiento"]:
        if dist[cls] > 0:
            print(f"    {cls:<16} {dist[cls]:>4} productos")
    print()

    if args.by_category:
        cat_rows = compute_by_category(rows, month_days)
        if args.format == "json":
            print(json.dumps(cat_rows, ensure_ascii=False, indent=2))
        else:
            reverse = args.sort != "producto_id"
            cat_rows.sort(key=lambda r: r.get(args.sort) or -1, reverse=reverse)
            print_table(cat_rows, [
                ("Categoría", "categoria", -20),
                ("Prod", "productos", 5),
                ("Ventas", "ventas_periodo", 10),
                ("Stock", "stock", 10),
                ("Rotación", "rotacion", 10),
                ("Clasif.", "clasificacion", 15),
                ("Cobertura", "dias_cobertura", 10),
            ])
    else:
        if args.format == "json":
            print(json.dumps(rows, ensure_ascii=False, indent=2))
        else:
            reverse = args.sort != "producto_id"
            rows.sort(key=lambda r: r.get(args.sort) or -1, reverse=reverse)
            print_table(rows[:50], [
                ("Código", "producto_id", -10),
                ("Ventas", "ventas_periodo", 10),
                ("Stock", "stock", 10),
                ("Rotación", "rotacion", 10),
                ("Clasif.", "clasificacion", 15),
                ("Cobertura", "dias_cobertura", 10),
            ])
            if len(rows) > 50:
                print(f"\n  (mostrando 50 de {len(rows)}; use --format json para todos)")

    client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
