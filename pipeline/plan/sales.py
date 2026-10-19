"""T19 — Cargador de ventas para el motor desde `plan_sales` / `plan_datasets` (solo lectura).

Formato de entrada esperado (lo escribe pipeline/plan/dataset.py):
  plan_datasets: {dataset_id, version, status in (staging|current|superseded), sales_cutoff "AAAA-MM-DD",
                  window_start "AAAA-MM-DD", source_rows, counts{clase: n}, imported_at}
  plan_sales   : {dataset_id, producto_id (texto), fecha "AAAA-MM-DD", cantidad (texto decimal exacto), unidad,
                  almacen (texto), clase "VENTA"}
Solo se leen la ventana del corte y las unidades de la historia; nada posterior al corte entra al calculo.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from fractions import Fraction

from pipeline.plan.engine import MASK_DAYS, WINDOW_DAYS, PlanRejected

DATASET_COLL = "plan_datasets"
SALES_COLL = "plan_sales"
WAREHOUSE = "1"
_QTY = re.compile(r"^\d+(\.\d+)?$")


@dataclass(frozen=True)
class ProductSales:
    by_day: dict           # {date: Fraction} UND, almacen 1, dentro de la ventana, sin dias enmascarados
    window_units: frozenset
    history_units: frozenset
    history_rows: int


def get_dataset(db, dataset_id: str | None = None) -> dict | None:
    """Cabecera del dataset: el `current` mas reciente, o el indicado (current/superseded; nunca staging)."""
    coll = db[DATASET_COLL]
    if dataset_id:
        return coll.find_one({"dataset_id": dataset_id, "status": {"$in": ["current", "superseded"]}}, {"_id": 0})
    return coll.find_one({"status": "current"}, {"_id": 0}, sort=[("version", -1), ("imported_at", -1)])


def cutoff_of(header: dict) -> date:
    try:
        return date.fromisoformat(str(header["sales_cutoff"])[:10])
    except (KeyError, ValueError):
        raise PlanRejected("DATASET_INVALIDO", "El dataset no declara un corte de ventas válido.") from None


def window_of(cutoff: date) -> tuple[date, date]:
    return cutoff - timedelta(days=WINDOW_DAYS - 1), cutoff


def check_coverage(header: dict, cutoff: date) -> None:
    """La ventana [corte-27, corte] debe estar dentro del periodo cubierto; si no, no se rellena con ceros."""
    ws, _ = window_of(cutoff)
    try:
        start = date.fromisoformat(str(header["window_start"])[:10])
    except (KeyError, ValueError):
        raise PlanRejected("DATASET_INVALIDO", "El dataset no declara el inicio de su cobertura.") from None
    if ws < start:
        raise PlanRejected("VENTANA_SIN_COBERTURA", "La ventana de 28 días no está cubierta por el dataset.")


def load_sales(db, dataset_id: str, product_ids, cutoff: date) -> dict[str, ProductSales]:
    """Ventas brutas (clase VENTA, almacen 1, unidad UND) por producto y dia dentro de [corte-27, corte], como fracciones
    exactas. Los dias enmascarados no se incluyen. Tambien devuelve las unidades vistas (ventana e historia hasta el
    corte) y el numero de lineas de historia para distinguir 'sin ventas en la ventana' (0 explicado) de 'sin señal'."""
    ids = sorted(set(product_ids))
    ws, we = window_of(cutoff)
    out = {p: {"by_day": {}, "wu": set(), "hu": set(), "rows": 0} for p in ids}
    base = {"dataset_id": dataset_id, "producto_id": {"$in": ids}, "clase": "VENTA", "almacen": WAREHOUSE,
            "fecha": {"$lte": cutoff.isoformat()}}
    for g in db[SALES_COLL].aggregate([{"$match": base},
                                       {"$group": {"_id": {"p": "$producto_id", "u": "$unidad"}, "n": {"$sum": 1}}}]):
        rec = out.get(g["_id"]["p"])
        if rec is not None:
            rec["hu"].add(g["_id"]["u"])
            rec["rows"] += g["n"]
    win = {**base, "fecha": {"$gte": ws.isoformat(), "$lte": we.isoformat()}}
    for d in db[SALES_COLL].find(win, {"_id": 0, "producto_id": 1, "fecha": 1, "cantidad": 1, "unidad": 1}):
        rec = out[d["producto_id"]]
        rec["wu"].add(d["unidad"])
        day = date.fromisoformat(d["fecha"])
        if d["unidad"] != "UND" or day in MASK_DAYS:
            continue
        q = str(d["cantidad"])
        if not _QTY.match(q):
            raise PlanRejected("CANTIDAD_INVALIDA", "Una venta tiene una cantidad no válida (negativa o no decimal).")
        rec["by_day"][day] = rec["by_day"].get(day, Fraction(0)) + Fraction(q)
    return {p: ProductSales(r["by_day"], frozenset(r["wu"]), frozenset(r["hu"]), r["rows"]) for p, r in out.items()}
