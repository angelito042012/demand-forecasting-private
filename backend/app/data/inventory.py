"""Lectura del inventario informado por la empresa (T18 §4). Solo lee; nunca escribe ni recalcula.

Colecciones propias (`inventory_reported_*`), separadas de `inventory_snapshot` simulado.
"""
from __future__ import annotations

import re

from backend.app.errors import ApiError, page_response

from .common import check_sort, iso_utc

SNAP_COLL = "inventory_reported_snapshots"
ITEM_COLL = "inventory_reported_items"
PROVENANCE = "INVENTARIO_INFORMADO_POR_LA_EMPRESA"
UNAVAILABLE = "SIN_INVENTARIO_INFORMADO"
DISCLAIMER = ("Inventario informado por la empresa (conteo del 18/10/2026 17:00, hora de Lima); "
              "no es inventario simulado ni se ha verificado de forma independiente.")
VISIBLE = ["current", "superseded"]
SORTS = {
    "producto_id": [("producto_id", 1)], "-producto_id": [("producto_id", -1)],
    "producto": [("producto", 1), ("producto_id", 1)], "-producto": [("producto", -1), ("producto_id", 1)],
    "libre": [("libre", 1), ("producto_id", 1)], "-libre": [("libre", -1), ("producto_id", 1)],
}
_ITEM_FIELDS = ("producto_id", "producto", "categoria", "unidad_reporte", "unidad_descripcion", "libre",
                "reservada", "no_vendible", "fisica_total")


def _snapshot_view(s: dict) -> dict:
    return {"snapshot_id": s["snapshot_id"], "version": s["version"], "status": s["status"],
            "as_of_local": s.get("as_of_local") or s.get("as_of_utc"), "as_of_utc": iso_utc(s.get("as_of_utc")), "timezone": s.get("timezone", "America/Lima"),
            "warehouse": {"id": (s.get("warehouse") or {}).get("id", "ALM1"),
                          "name": (s.get("warehouse") or {}).get("name", "Almacén principal")}, "nature": s.get("nature", "INFORMADO"),
            "independent_verification": bool(s["independent_verification"]),
            "source": {"file": s["source"]["file"], "sha256_short": s["source"]["sha256"][:12]},
            "counts": dict(s["counts"]), "declared_unknowns": [dict(u) for u in s.get("declared_unknowns", [])],
            "context": dict(s.get("context", {})), "confirmations": dict(s.get("confirmations", {})),
            "imported_at": iso_utc(s.get("imported_at"))}


def _resolve(db, snapshot_id: str | None) -> dict | None:
    coll = db[SNAP_COLL]
    if snapshot_id:
        s = coll.find_one({"snapshot_id": snapshot_id, "status": {"$in": VISIBLE}}, {"_id": 0})
        if s is None:
            raise ApiError(404, "NO_ENCONTRADO", "Snapshot de inventario no encontrado.")
        return s
    return coll.find_one({"status": "current"}, {"_id": 0}, sort=[("as_of_utc", -1), ("version", -1)])


def list_snapshots(db, page: int, page_size: int) -> dict:
    flt = {"status": {"$in": VISIBLE}}
    total = db[SNAP_COLL].count_documents(flt)
    cur = db[SNAP_COLL].find(flt, {"_id": 0}).sort([("as_of_utc", -1), ("version", -1)]) \
        .skip((page - 1) * page_size).limit(page_size)
    items = [{"snapshot_id": s["snapshot_id"], "version": s["version"], "status": s["status"],
              "as_of_local": s.get("as_of_local") or s.get("as_of_utc"),
              "warehouse": {"id": (s.get("warehouse") or {}).get("id", "ALM1"),
                            "name": (s.get("warehouse") or {}).get("name", "Almacén principal")},
              "source": {"sha256_short": s["source"]["sha256"][:12]}, "imported_at": iso_utc(s.get("imported_at"))}
             for s in cur]
    return page_response(items, total, page, page_size)


def get_reported(db, *, snapshot_id: str | None, q: str | None, view: str, sort: str | None,
                 page: int, page_size: int) -> dict:
    snap = _resolve(db, snapshot_id)
    labels = {"provenance": PROVENANCE, "disclaimer": DISCLAIMER}
    if snap is None:
        return {"snapshot": None, "items": [], "page": page, "page_size": page_size, "total": 0, "has_more": False,
                "view_counts": {"all": 0, "with_stock": 0, "no_stock": 0}, "unavailable_reason": UNAVAILABLE, **labels}
    order = check_sort(sort, SORTS, "producto_id")
    base: dict = {"snapshot_id": snap["snapshot_id"]}
    if q:
        rx = re.escape(q)
        base["$or"] = [{"producto_id": {"$regex": f"^{rx}"}}, {"producto": {"$regex": rx, "$options": "i"}}]
    items_coll = db[ITEM_COLL]
    view_counts = {"all": items_coll.count_documents(base),
                   "with_stock": items_coll.count_documents({**base, "libre": {"$gt": 0}}),
                   "no_stock": items_coll.count_documents({**base, "libre": 0})}
    flt = {"with_stock": {**base, "libre": {"$gt": 0}}, "no_stock": {**base, "libre": 0}}.get(view, base)
    cur = items_coll.find(flt, {"_id": 0, **{f: 1 for f in _ITEM_FIELDS}}).sort(order) \
        .skip((page - 1) * page_size).limit(page_size)
    page_items = [{f: d.get(f) for f in _ITEM_FIELDS} for d in cur]
    resp = page_response(page_items, view_counts[view], page, page_size)
    return {"snapshot": _snapshot_view(snap), **resp, "view_counts": view_counts, **labels}
