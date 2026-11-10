"""Comparación justa entre política simulada (T07) y política propuesta (tarea 2).

Usa el mismo motor de simulación (`pipeline.sim.engine`) con las mismas variables controladas
(stock inicial, demanda, horizonte) y varía solo el pronóstico y la frecuencia de revisión.

ETIQUETA: Ejercicio académico con supuestos; requiere ventas reales del mes objetivo para
ejecutarse de forma significativa. Sin esas ventas, solo se puede comparar usando datos
históricos ya vistos (no es una prueba independiente).

    python -m scripts.compare_policies --db <base> --month 2026-09 --origin-sim 2026-07-10 --origin-prop 2026-10-20
    python -m scripts.compare_policies --db <base> --month 2026-09 --origin-sim 2026-07-10 --origin-prop 2026-10-20 --lead-times 7,14 --safety 7
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from fractions import Fraction
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent


def _parse_date(s: str) -> date:
    return date.fromisoformat(s)


def _month_range(month_str: str) -> tuple[date, date]:
    y, m = month_str.split("-")
    first = date(int(y), int(m), 1)
    if int(m) == 12:
        last = date(int(y) + 1, 1, 1) - timedelta(days=1)
    else:
        last = date(int(y), int(m) + 1, 1) - timedelta(days=1)
    return first, last


def load_demand_from_db(db, first: date, last: date, products: list[str]) -> dict[str, dict[date, int]]:
    """Lee ventas brutas del plan_sales para el período y productos dados."""
    coll = db["plan_sales"]
    query = {
        "clase": "VENTA",
        "fecha": {"$gte": first.isoformat(), "$lte": last.isoformat()},
        "producto_id": {"$in": products},
        "almacen": "1",
    }
    out: dict[str, dict[date, int]] = {p: {} for p in products}
    for doc in coll.find(query, {"producto_id": 1, "fecha": 1, "cantidad": 1, "_id": 0}):
        pid = doc["producto_id"]
        d = _parse_date(doc["fecha"])
        qty = int(float(doc["cantidad"]))
        out[pid][d] = out[pid].get(d, 0) + qty
    return out


def load_stock_from_db(db) -> dict[str, int]:
    """Lee la existencia reconstruida vigente (inventory_reconstructed_items del snapshot current)."""
    snap = db["inventory_reconstructed_snapshots"].find_one(
        {"status": "current"}, {"snapshot_id": 1, "_id": 0},
        sort=[("version", -1)],
    )
    if snap is None:
        print("ERROR: no hay snapshot de existencia reconstruida vigente.", file=sys.stderr)
        sys.exit(1)
    items = db["inventory_reconstructed_items"].find(
        {"snapshot_id": snap["snapshot_id"]}, {"producto_id": 1, "libre": 1, "_id": 0},
    )
    return {i["producto_id"]: int(i["libre"]) for i in items}


def build_demand_matrix(demand: dict[str, dict[date, int]], products: list[str],
                        first: date, last: date) -> np.ndarray:
    """(n_products, n_days) con NaN para días sin dato conocido (usamos 0 si no hubo venta)."""
    n_days = (last - first).days + 1
    n = len(products)
    idx = {p: i for i, p in enumerate(products)}
    mat = np.zeros((n, n_days), dtype=float)
    for pid in products:
        for d_offset in range(n_days):
            day = first + timedelta(days=d_offset)
            mat[idx[pid], d_offset] = float(demand.get(pid, {}).get(day, 0))
    return mat


def compute_promedio_28(db, origin: date, products: list[str]) -> dict[str, float]:
    """Calcula promedio_28 para cada producto usando ventas hasta el origen."""
    window_end = origin
    window_start = origin - timedelta(days=27)
    from pipeline.plan.descriptive import MASK_DAYS

    coll = db["plan_sales"]
    query = {
        "clase": "VENTA",
        "fecha": {"$gte": window_start.isoformat(), "$lte": window_end.isoformat()},
        "producto_id": {"$in": products},
        "almacen": "1",
    }
    sales: dict[str, dict[date, float]] = {p: {} for p in products}
    for doc in coll.find(query, {"producto_id": 1, "fecha": 1, "cantidad": 1, "_id": 0}):
        pid = doc["producto_id"]
        d = _parse_date(doc["fecha"])
        qty = float(doc["cantidad"])
        sales[pid][d] = sales[pid].get(d, 0.0) + qty

    result = {}
    for pid in products:
        days_used = 0
        total = 0.0
        for offset in range(28):
            day = window_start + timedelta(days=offset)
            if day in MASK_DAYS:
                continue
            days_used += 1
            total += sales[pid].get(day, 0.0)
        result[pid] = total / days_used if days_used > 0 else 0.0
    return result


def run_simulation(demand_matrix: np.ndarray, stock0: np.ndarray, forecast_daily: np.ndarray,
                   lead_time: int, safety_days: int, review_every: int) -> dict:
    """Ejecuta la simulación y devuelve métricas agregadas."""
    from pipeline.sim.engine import SimResult, review_indices, simulate

    n, D = demand_matrix.shape
    reviews = review_indices(D, every=review_every, first=0)
    targets = {}
    for r_day in reviews:
        horizon_days = lead_time + safety_days
        target = np.ceil(forecast_daily * horizon_days).astype(np.int64)
        target = np.maximum(target, 1)
        targets[r_day] = target

    unit_cost = np.ones(n)
    res = simulate(demand_matrix, reviews, targets, lead_time, stock0, unit_cost)

    total_demand = np.nansum(demand_matrix)
    total_served = float(res.served.sum())
    total_lost = float(res.lost.sum())
    fill_rate = total_served / total_demand if total_demand > 0 else None
    stock_mean = float(res.on_hand.sum(axis=0).mean())
    total_ordered = float(res.ordered.sum())

    return {
        "fill_rate": round(fill_rate, 4) if fill_rate is not None else None,
        "demanda_total": int(total_demand),
        "atendidas": int(total_served),
        "perdidas": int(total_lost),
        "stock_medio_por_dia": round(stock_mean, 1),
        "compras_unidades": int(total_ordered),
        "dias_sku_con_faltante": int((res.lost.T > 0).sum()),
        "stock_final": int(res.on_hand[-1].sum()),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Comparación justa: política simulada vs propuesta",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--db", required=True, help="Base de datos MongoDB")
    ap.add_argument("--uri", default="mongodb://127.0.0.1:27017", help="URI de MongoDB")
    ap.add_argument("--month", required=True, help="Mes objetivo YYYY-MM (ventas reales)")
    ap.add_argument("--origin-sim", required=True, help="Origen del pronóstico simulado (YYYY-MM-DD)")
    ap.add_argument("--origin-prop", required=True, help="Origen del pronóstico propuesto (YYYY-MM-DD)")
    ap.add_argument("--lead-times", default="7,14", help="Lead times a evaluar (separados por coma)")
    ap.add_argument("--safety", type=int, default=7, help="Días de reserva de seguridad")
    ap.add_argument("--review-every", type=int, default=7, help="Frecuencia de revisión (días)")
    args = ap.parse_args(argv)

    from pymongo import MongoClient
    client = MongoClient(args.uri)
    db = client[args.db]

    first, last = _month_range(args.month)
    lead_times = [int(x) for x in args.lead_times.split(",")]
    origin_sim = _parse_date(args.origin_sim)
    origin_prop = _parse_date(args.origin_prop)

    print(f"\n{'='*70}")
    print(f"  COMPARACIÓN JUSTA: política simulada vs propuesta")
    print(f"  Mes objetivo: {args.month} ({first} a {last})")
    print(f"  Origen simulada: {origin_sim} | Origen propuesta: {origin_prop}")
    print(f"  Lead times: {lead_times} | Seguridad: {args.safety} días")
    print(f"{'='*70}\n")

    stock_map = load_stock_from_db(db)
    products = sorted(stock_map.keys())
    print(f"  Productos con stock: {len(products)}")

    demand = load_demand_from_db(db, first, last, products)
    products_with_demand = [p for p in products if any(demand[p].values())]
    print(f"  Productos con ventas en {args.month}: {len(products_with_demand)}")

    if not products_with_demand:
        print("\n  ERROR: no hay ventas para el mes objetivo. ¿Están importadas?", file=sys.stderr)
        client.close()
        return 1

    products = products_with_demand
    n = len(products)

    demand_matrix = build_demand_matrix(demand, products, first, last)
    stock0 = np.array([stock_map.get(p, 0) for p in products], dtype=np.int64)

    forecast_sim = compute_promedio_28(db, origin_sim, products)
    forecast_prop = compute_promedio_28(db, origin_prop, products)

    fc_sim_arr = np.array([forecast_sim[p] for p in products], dtype=float)
    fc_prop_arr = np.array([forecast_prop[p] for p in products], dtype=float)

    print(f"\n  Pronóstico promedio diario (media entre productos):")
    print(f"    Simulada (origen {origin_sim}):  {fc_sim_arr.mean():.2f} u/día")
    print(f"    Propuesta (origen {origin_prop}): {fc_prop_arr.mean():.2f} u/día")

    results = {}
    for L in lead_times:
        print(f"\n  --- Lead time = {L} días, Seguridad = {args.safety} días ---\n")

        try:
            res_sim = run_simulation(demand_matrix, stock0, fc_sim_arr, L, args.safety, args.review_every)
            res_prop = run_simulation(demand_matrix, stock0, fc_prop_arr, L, args.safety, args.review_every)
        except Exception as exc:
            print(f"  Error en simulación: {exc}", file=sys.stderr)
            continue

        results[f"L{L}"] = {"simulada": res_sim, "propuesta": res_prop}

        header = f"{'Métrica':<30} {'Simulada':>12} {'Propuesta':>12} {'Diferencia':>12}"
        print(f"  {header}")
        print(f"  {'-'*len(header)}")
        for key in ["fill_rate", "demanda_total", "atendidas", "perdidas",
                     "stock_medio_por_dia", "compras_unidades", "dias_sku_con_faltante"]:
            v_s = res_sim[key]
            v_p = res_prop[key]
            if v_s is not None and v_p is not None:
                diff = v_p - v_s
                sign = "+" if diff > 0 else ""
                if isinstance(v_s, float):
                    print(f"  {key:<30} {v_s:>12.4f} {v_p:>12.4f} {sign}{diff:>11.4f}")
                else:
                    print(f"  {key:<30} {v_s:>12,} {v_p:>12,} {sign}{diff:>11,}")
            else:
                print(f"  {key:<30} {str(v_s):>12} {str(v_p):>12} {'N/A':>12}")

    print(f"\n{'='*70}")
    print(f"  NOTA: variables controladas = mismo stock inicial ({n} productos),")
    print(f"  misma demanda ({args.month}), mismos parámetros (L, S, revisión).")
    print(f"  Diferencia solo en la ventana del pronóstico promedio_28.")
    print(f"{'='*70}\n")

    print(json.dumps(results, ensure_ascii=False, indent=2))
    client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
