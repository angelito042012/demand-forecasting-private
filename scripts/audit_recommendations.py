"""Auditoria INDEPENDIENTE de las recomendaciones publicadas (T08R).

No usa builders, signals ni daily_series: recalcula desde (a) las ventas aprobadas de la coleccion `sales`
(agregacion directa en MongoDB, aritmetica entera) y (b) el NPZ de la simulacion T07 (indexado propio).
Compara objetivo, posicion y pedido de TODAS las recomendaciones `ok` de la corrida.

    python -m scripts.audit_recommendations [--run-id ID] [--db NOMBRE] [--out ruta.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from pipeline.data.calendar import EXCLUDED_DATES
from pipeline.data.importer import get_client
from pipeline.data.sources import approved_sources

ORIGIN = date(2026, 7, 10)
DAY_INDEX = 39          # 01/06 = 0
KEY = "L7_S7_promedio_28__"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id")
    ap.add_argument("--db", default="demand_forecasting_v2")
    ap.add_argument("--out", type=Path, default=Path("artifacts/private/t08r/audit_recommendations.json"))
    args = ap.parse_args(argv)
    db = get_client()[args.db]
    run_id = args.run_id or db.run_pointer.find_one({"_id": "active"})["run_id"]
    shas = sorted(approved_sources(db))
    window = [(ORIGIN - timedelta(days=27 - i)).isoformat() for i in range(28)]
    masked = {d.isoformat() for d in EXCLUDED_DATES}
    # ventas positivas aprobadas hasta el origen (agregacion directa)
    pipeline = [{"$match": {"fecha": {"$lte": ORIGIN.isoformat()}, "sources.source_sha256": {"$in": shas}}},
                {"$group": {"_id": {"s": "$sku", "a": "$almacen"}, "first": {"$min": "$fecha"},
                            "w": {"$sum": {"$cond": [{"$and": [{"$gte": ["$fecha", window[0]]}, {"$gt": ["$cantidad_base", 0]}]},
                                                    "$cantidad_base", 0]}}}}]
    agg = {(g["_id"]["s"], g["_id"]["a"]): (g["first"], g["w"]) for g in db.sales.aggregate(pipeline, allowDiskUse=True)}
    covered = set(db.sales.distinct("fecha", {"fecha": {"$in": window}, "sources.source_sha256": {"$in": shas}}))
    npz = np.load("artifacts/private/t07/simulacion_series.npz", allow_pickle=False)
    skus = [str(s) for s in npz["skus"]]
    idx = {s: i for i, s in enumerate(skus)}
    on_hand, ordered, received = npz[KEY + "on_hand"], npz[KEY + "ordered"], npz[KEY + "received"]
    diffs, n_ok, pos, units, checked = [], 0, 0, 0, 0
    for d in db.recommendations.find({"run_id": run_id, "status": "ok"}):
        n_ok += 1
        sku, alm = d["sku"], d["almacen"]
        first, wsum = agg[(sku, alm)]
        useful = [x for x in window if x >= first and x not in masked and x in covered]
        days = len(useful)
        total = wsum
        if total != int(total):
            raise SystemExit(f"cantidad no entera para {sku}")
        total = int(total)
        target = -((-21 * total) // days)             # techo exacto de 21*suma/dias con enteros
        i = idx[sku]
        stock = int(on_hand[DAY_INDEX, i])
        transit = int(ordered[:DAY_INDEX + 1, i].sum() - received[:DAY_INDEX + 1, i].sum())
        position = stock + transit
        order = max(0, target - position)
        pos += order > 0
        units += order
        checked += 1
        got = (d["on_hand"], d["in_transit"], d["position"], d["target"], d["order_qty"], d.get("days_28", days))   # corrida antigua: sin days_28
        want = (stock, transit, position, target, order, days)
        if got != want:
            diffs.append({"sku": sku, "publicado": got, "independiente": want})
    n_sin = db.recommendations.count_documents({"run_id": run_id, "status": "sin_snapshot"})
    null_ok = db.recommendations.count_documents({"run_id": run_id, "status": "sin_snapshot", "order_qty": None,
                                                  "target": None, "on_hand": None})
    pub_pos = db.recommendations.count_documents({"run_id": run_id, "status": "ok", "order_qty": {"$gt": 0}})
    summary = {"run_id": run_id, "publicado_con_pedido_positivo": pub_pos, "recomendaciones_ok_auditadas": checked, "diferencias": len(diffs),
               "con_pedido_positivo": int(pos), "unidades_sugeridas": int(units), "sin_snapshot": n_sin,
               "sin_snapshot_con_cantidades_nulas": null_ok,
               "referencia_codex_582_2655": [582, 2655], "coincide_con_referencia_codex": [int(pos), int(units)] == [582, 2655],
               "ventana": [window[0], window[-1]], "metodo": "agregacion directa de ventas aprobadas + NPZ; entero exacto"}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({**summary, "detalle_diferencias": diffs[:200]}, ensure_ascii=False, indent=1) + "\n",
                        encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0 if not diffs and checked == 3347 and null_ok == n_sin else 1


if __name__ == "__main__":
    sys.exit(main())
