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
REC_SNAPSHOT_ID = "invrec-20261020-b2c3d4e5f6a7"
DATASET_V2_ID = "plds-test00000002"
REC_AS_OF = "2026-10-20T23:59:59-05:00"
LAST_MOVEMENT = "2026-10-21T16:26:38-05:00"
RAW_V2 = {**RAW, "decision_date": "2026-10-21"}
UNTOUCHED = ("recommendations", "runs", "inventory_snapshot", "inventory_reported_snapshots", "inventory_reported_items",
             "inventory_reconstructed_snapshots", "inventory_reconstructed_items",
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


def seed_dataset(db, dataset_id=DATASET_ID, *, noise=True, status="current", version=1, cutoff=CUTOFF) -> None:
    rows, n = [], 0
    for pid, (_libre, _u, spec, _c) in PRODUCTS.items():
        if spec in ("2",):
            for k in range(28):
                n += 1
                rows.append(_sale(dataset_id, n, pid, cutoff - timedelta(days=27) + timedelta(days=k), "2"))
        elif spec == "AUG":
            n += 1
            rows.append(_sale(dataset_id, n, pid, date(2026, 8, 10), "5"))
        elif spec == "CAJA":
            for k in range(28):
                n += 1
                rows.append(_sale(dataset_id, n, pid, cutoff - timedelta(days=27) + timedelta(days=k), "1", unit="CAJA"))
    if noise:       # fuera de la ventana o posterior al corte: no debe cambiar nada
        n += 1
        rows.append(_sale(dataset_id, n, "1000001", date(2026, 8, 1), "999"))
        n += 1
        rows.append(_sale(dataset_id, n, "1000001", date(2026, 9, 2), "999"))
    db.plan_sales.insert_many(rows)
    db.plan_datasets.insert_one({
        "dataset_id": dataset_id, "version": version, "status": status, "sales_cutoff": cutoff.isoformat(),
        "window_start": "2026-03-01", "window_end": cutoff.isoformat(), "source_rows": len(rows), "counts": {"VENTA": len(rows)},
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


# producto -> libre al cierre (existencia reconstruida). 1000005 (sin cantidad en el conteo informado) no existe en v2.
REC_NET = {"entradas_cierre": 5, "salidas_cierre": 2}


def seed_reconstructed(db, snapshot_id=REC_SNAPSHOT_ID, *, version=1, status="current", libres=None,
                       discrepancies=None) -> None:
    """Existencia reconstruida SINTETICA (T20). `discrepancies` = {producto_id: diferencia}; el resto coincide con el sistema."""
    libres, discrepancies = libres or {}, discrepancies if discrepancies is not None else {"1000003": -3}
    items = []
    for pid, (libre, _u, _s, _c) in PRODUCTS.items():
        libre = libres.get(pid, libre)
        if libre is None:
            continue
        net = REC_NET if libre >= 3 else {"entradas_cierre": 0, "salidas_cierre": 0}
        diff = discrepancies.get(pid)
        items.append({
            "snapshot_id": snapshot_id, "producto_id": pid, "producto": f"PRODUCTO {pid}", "categoria": "CAT",
            "unidad_reporte": "UND", "unidad_descripcion": f"Unidad {pid}", "libre": libre,
            "base_count": libre - net["entradas_cierre"] + net["salidas_cierre"],
            "movements": {**net, "entradas_ultimo_mov": net["entradas_cierre"], "salidas_ultimo_mov": net["salidas_cierre"]},
            "reconstructed_at_last_movement": libre, "system_stock_at_last_movement": libre + (diff or 0),
            "system_reserved": 0, "discrepancy": None if not diff else {"difference": diff, "compared_at_local": LAST_MOVEMENT}})
    db.inventory_reconstructed_snapshots.insert_one({
        "snapshot_id": snapshot_id, "kind": "EXISTENCIA_RECONSTRUIDA", "version": version, "status": status, "supersedes": None,
        "as_of_utc": datetime(2026, 10, 21, 4, 59, 59), "as_of_local": REC_AS_OF, "warehouse": {"id": "1", "name": "Almacen 1"},
        "source": {"sha256": "b2c3d4e5f6a7" + "0" * 52, "csv_sha256": "d" * 64},
        "base_count": {"snapshot_id": SNAPSHOT_ID, "as_of_local": AS_OF, "csv_sha256": "c" * 64},
        "movements": {"from_local": AS_OF, "closing_local": REC_AS_OF, "last_movement_local": LAST_MOVEMENT},
        "counts": {"products": len(items), "discrepancies": sum(1 for i in items if i["discrepancy"])},
        "rule": "existencia_cierre = conteo + entradas - salidas", "imported_at": datetime(2026, 10, 21, 18, 0, 0)})
    db.inventory_reconstructed_items.insert_many(items)


def seed_v2(db, **kw) -> None:
    """Dataset v2 (corte 20/10) y existencia reconstruida; el dataset v1 pasa a `superseded` (se lee por id)."""
    db.plan_datasets.update_many({"dataset_id": DATASET_ID}, {"$set": {"status": "superseded"}})
    seed_dataset(db, DATASET_V2_ID, version=2, cutoff=date(2026, 10, 20))
    db.plan_datasets.update_one({"dataset_id": DATASET_V2_ID}, {"$set": {
        "base_dataset_id": DATASET_ID, "october_verification": {"sql_match": True, "lines": 10, "documents": 5},
        "partial": {"date": "2026-10-21", "used_for_forecast": False}}})
    seed_reconstructed(db, **kw)


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
