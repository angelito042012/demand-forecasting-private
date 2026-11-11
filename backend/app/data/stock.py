"""T20 §3 — Lectura de la existencia reconstruida al cierre (`inventory_reconstructed_*`). Solo lee; nunca escribe ni recalcula.

Es una cifra derivada (conteo fisico del 18/10 + entradas - salidas registradas), no un conteo nuevo: se muestra con su
procedencia y las discrepancias frente al stock del sistema solo en los productos afectados.
"""
from __future__ import annotations

import re

from backend.app.errors import ApiError, page_response
from pipeline.plan import store

from .common import check_sort, iso_utc

PROVENANCE = "EXISTENCIA_RECONSTRUIDA"
UNAVAILABLE = "SIN_EXISTENCIA_RECONSTRUIDA"
DISCLAIMER = ("Existencia reconstruida al cierre: conteo físico informado más entradas menos salidas registradas; "
              "no es un conteo nuevo. La comparación con el stock del sistema se hace en la fecha del último movimiento.")
SORTS = {
    "producto_id": [("producto_id", 1)], "-producto_id": [("producto_id", -1)],
    "producto": [("producto", 1), ("producto_id", 1)], "-producto": [("producto", -1), ("producto_id", 1)],
    "libre": [("libre", 1), ("producto_id", 1)], "-libre": [("libre", -1), ("producto_id", 1)],
}
_ITEM_FIELDS = ("producto_id", "producto", "categoria", "unidad_reporte", "unidad_descripcion", "libre", "base_count",
                "movements", "reconstructed_at_last_movement", "system_stock_at_last_movement", "system_reserved")


def _snapshot_view(s: dict, discrepancies: list[str]) -> dict:
    src = s.get("source", {})
    return {"snapshot_id": s["snapshot_id"], "kind": store.RECONSTRUIDO, "version": s.get("version"), "status": s.get("status"),
            "as_of_local": s.get("as_of_local") or s.get("as_of_utc"), "as_of_utc": iso_utc(s.get("as_of_utc")),
            "warehouse": {"id": (s.get("warehouse") or {}).get("id", "ALM1"),
                          "name": (s.get("warehouse") or {}).get("name", "Almacén principal")},
            "base_count": dict(s.get("base_count") or {}), "movements": dict(s.get("movements") or {}),
            "counts": dict(s.get("counts") or {}), "rule": s.get("rule"), "supersedes": s.get("supersedes"),
            "source": {"sha256_short": str(src.get("sha256", ""))[:12], "csv_sha256_short": str(src.get("csv_sha256", ""))[:12]},
            "confirmations": store.build_confirmations(discrepancies), "imported_at": iso_utc(s.get("imported_at"))}


def _resolve(db, snapshot_id: str | None) -> dict | None:
    coll = db[store.REC_SNAP_COLL]
    if snapshot_id:
        s = coll.find_one({"snapshot_id": snapshot_id, "status": {"$in": store.VISIBLE}}, {"_id": 0})
        if s is None:
            raise ApiError(404, "NO_ENCONTRADO", "Existencia reconstruida no encontrada.")
        return s
    return coll.find_one({"status": "current"}, {"_id": 0}, sort=[("as_of_utc", -1), ("version", -1)])


def get_stock(db, *, snapshot_id: str | None, q: str | None, view: str, sort: str | None, page: int, page_size: int) -> dict:
    snap = _resolve(db, snapshot_id)
    labels = {"provenance": PROVENANCE, "disclaimer": DISCLAIMER}
    if snap is None:
        return {"snapshot": None, "items": [], "page": page, "page_size": page_size, "total": 0, "has_more": False,
                "view_counts": {"all": 0, "discrepancias": 0, "coinciden": 0}, "unavailable_reason": UNAVAILABLE, **labels}
    order = check_sort(sort, SORTS, "producto_id")
    coll = db[store.REC_ITEM_COLL]
    sid = {"snapshot_id": snap["snapshot_id"]}
    discrepancies = sorted(d["producto_id"] for d in coll.find({**sid, "discrepancy": {"$ne": None}}, {"producto_id": 1, "_id": 0}))
    base: dict = dict(sid)
    if q:
        rx = re.escape(q)
        base["$or"] = [{"producto_id": {"$regex": f"^{rx}"}}, {"producto": {"$regex": rx, "$options": "i"}}]
    with_disc = {**base, "discrepancy": {"$ne": None}}
    view_counts = {"all": coll.count_documents(base), "discrepancias": coll.count_documents(with_disc)}
    view_counts["coinciden"] = view_counts["all"] - view_counts["discrepancias"]
    flt = with_disc if view == "discrepancias" else base
    cur = coll.find(flt, {"_id": 0, "discrepancy": 1, **{f: 1 for f in _ITEM_FIELDS}}).sort(order) \
        .skip((page - 1) * page_size).limit(page_size)
    items = [{**{f: d.get(f) for f in _ITEM_FIELDS}, "discrepancy": d.get("discrepancy") or None} for d in cur]
    resp = page_response(items, view_counts["discrepancias"] if view == "discrepancias" else view_counts["all"], page, page_size)
    return {"snapshot": _snapshot_view(snap, discrepancies), **resp, "view_counts": view_counts, **labels}
