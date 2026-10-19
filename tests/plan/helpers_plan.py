"""Ayudas del motor de plan T19 (agente B): datos SINTETICOS con la forma de plan_sales/plan_datasets y del snapshot T18."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime, timedelta

CUTOFF = date(2026, 9, 30)
DATASET_ID = "plds-test00000001"
SNAPSHOT_ID = "invrep-20261018T1700-a1-608d15a74a58"
AS_OF = "2026-10-18T17:00:00-05:00"
RAW = {"month": "2026-11", "decision_date": "2026-10-18", "lead_days": [7, 14], "reserve_days": 7, "min_order": 1,
       "order_multiple": 1, "pending_orders": []}
UNTOUCHED = ("recommendations", "runs", "inventory_snapshot", "inventory_reported_snapshots", "inventory_reported_items",
             "plan_sales", "plan_datasets", "plan_purchases", "plan_credits", "plan_quarantine")

# producto -> (libre, unidad_reporte, ventas_por_dia_en_septiembre, caso)
PRODUCTS = {
    "1000001": (40, "UND", "2", "stock 40, m=2"),
    "1000002": (500, "UND", "2", "stock 500, m=2"),
    "1000003": (10, "UND", "2", "stock 10, m=2"),
    "1000004": (0, "UND", "2", "libre 0 informado"),
    "1000005": (None, "UND", "2", "sin cantidad libre"),
    "1000006": (30, "UND", None, "sin ninguna venta (sin señal)"),
    "1000007": (30, "UND", "AUG", "ventas solo en agosto: m=0 explicado"),
    "1000008": (30, "UND", "CAJA", "ventas en otra unidad"),
}


def _sale(dataset_id, n, pid, day, qty, unit="UND"):
    return {"dataset_id": dataset_id, "registro_id": f"r{n}", "fecha": day.isoformat(), "producto_id": pid,
            "producto": f"PRODUCTO {pid}", "categoria": "CAT", "almacen": "1", "unidad": unit, "cantidad": qty,
            "moneda": "PEN", "importe": "0", "tipo_documento": "1", "documento_id": f"d{n}", "clase": "VENTA",
            "grupo_repeticion": None, "ocurrencia": 1, "dia_excluido_pronostico": False, "archivo": "x.xlsx",
            "hoja": "H", "fila": n, "sha256_origen": "0" * 64}


def seed_dataset(db, dataset_id=DATASET_ID, *, noise=True, status="current", version=1) -> None:
    rows, n = [], 0
    for pid, (_libre, _u, spec, _c) in PRODUCTS.items():
        if spec in ("2",):
            for k in range(28):
                n += 1
                rows.append(_sale(dataset_id, n, pid, date(2026, 9, 3) + timedelta(days=k), "2"))
        elif spec == "AUG":
            n += 1
            rows.append(_sale(dataset_id, n, pid, date(2026, 8, 10), "5"))
        elif spec == "CAJA":
            for k in range(28):
                n += 1
                rows.append(_sale(dataset_id, n, pid, date(2026, 9, 3) + timedelta(days=k), "1", unit="CAJA"))
    if noise:       # fuera de la ventana o posterior al corte: no debe cambiar nada
        n += 1
        rows.append(_sale(dataset_id, n, "1000001", date(2026, 8, 1), "999"))
        n += 1
        rows.append(_sale(dataset_id, n, "1000001", date(2026, 9, 2), "999"))
    db.plan_sales.insert_many(rows)
    db.plan_datasets.insert_one({
        "dataset_id": dataset_id, "version": version, "status": status, "sales_cutoff": CUTOFF.isoformat(),
        "window_start": "2026-03-01", "window_end": "2026-09-30", "source_rows": len(rows), "counts": {"VENTA": len(rows)},
        "imported_at": datetime(2026, 10, 18, 12, 0, 0), "schema_version": 1})
    db.plan_purchases.insert_one({"dataset_id": dataset_id, "registro_id": "c1", "producto_id": "1000001", "cantidad": "50"})


def seed_snapshot(db, snapshot_id=SNAPSHOT_ID, *, version=1, status="current", sha="608d15a74a58" + "0" * 52,
                  libres=None) -> None:
    libres = libres or {}
    db.inventory_reported_snapshots.insert_one({
        "snapshot_id": snapshot_id, "version": version, "status": status, "as_of_utc": datetime(2026, 10, 18, 22, 0, 0),
        "as_of_local": AS_OF, "timezone": "America/Lima", "warehouse": {"id": "1", "name": "Almacen 1"},
        "nature": "CONTEO_FISICO_REPORTADO_POR_USUARIO", "independent_verification": False,
        "source": {"file": "conteo.xlsx", "sheet": "H", "sha256": sha, "csv_sha256": "c" * 64},
        "counts": {"items": len(PRODUCTS)}, "imported_at": datetime.now(UTC).replace(tzinfo=None, microsecond=0)})
    db.inventory_reported_items.insert_many([
        {"snapshot_id": snapshot_id, "producto_id": pid, "producto": f"PRODUCTO {pid}", "categoria": "CAT",
         "unidad_reporte": "UND", "unidad_descripcion": f"Unidad {pid}",
         "libre": libres.get(pid, libre), "reservada": 0, "no_vendible": 0, "fisica_total": libres.get(pid, libre),
         "source_row": 9} for pid, (libre, _u, _s, _c) in PRODUCTS.items()])


def seed_other(db) -> None:
    """Colecciones que el plan NO debe tocar (se comparan antes/despues)."""
    db.recommendations.insert_one({"run_id": "r1", "sku": "x", "qty": 1})
    db.runs.insert_one({"run_id": "r1", "status": "completed"})
    db.inventory_snapshot.insert_one({"sku": "x", "stock": 5})


def fingerprint(db, names=UNTOUCHED) -> dict:
    out = {}
    for n in names:
        docs = sorted(json.dumps(d, sort_keys=True, default=str) for d in db[n].find({}, {"_id": 0}))
        out[n] = hashlib.sha256("\n".join(docs).encode()).hexdigest()
    return out


def seed_all(db) -> None:
    seed_dataset(db)
    seed_snapshot(db)
    seed_other(db)
