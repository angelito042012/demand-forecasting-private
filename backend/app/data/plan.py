"""T19 §6 — Lectura y encolado del plan de compra. Lee `plan_runs`/`plan_results`; solo encola `generate_plan`.

La API nunca calcula el plan: el trabajo lo ejecuta el worker. Solo se muestran planes `completed` (staging y failed son
invisibles). Las cantidades se guardan exactas ("p" o "p/q") y se muestran como texto decimal de hasta 3 decimales;
el detalle anade la forma exacta.
"""
from __future__ import annotations

import re
from datetime import timedelta

from backend.app.errors import ApiError, page_response
from pipeline.jobs import queue
from pipeline.plan import engine, sales, store
from pipeline.plan.engine import PlanRejected

from .common import check_sort, invalid, iso_utc

LABEL = store.LABEL
UNAVAILABLE = "SIN_PLAN"
SORT_RE = re.compile(r"^-?(producto_id|producto|forecast|libre|status|purchase_\d{1,2})$")
SCENARIO_QTY = ("stock_at_arrival", "stock_month_start", "shortage_before_month", "shortage_month", "served_month",
                "demand_before_arrival_in_month", "end_stock", "consumed_before_arrival", "shortage_before_arrival",
                "reserve_qty", "qty_unrounded")
BREAKDOWN_QTY = ("stock_count", "consumed_before_arrival", "shortage_before_arrival", "other_receipts_until_arrival",
                 "stock_at_arrival", "bridge_demand", "month_demand", "reserve", "total_need", "pending_after_arrival",
                 "final_need", "prefix_need", "qty_unrounded")
SERIES_QTY = ("inicio", "recepciones", "disponible", "demanda", "atendida", "faltante", "fin")
HEAVY = ("breakdown", "explanation", "events", "series")
PLAN_ASSUMPTION_DEFAULTS = [{"code": c, "text": t, "nature": "SUPUESTO"} for c, t in store.ASSUMPTIONS]


def _d(x) -> str | None:
    return None if x is None else engine.dec(engine.parse_exact(x))


def _scenario(sc: dict, detail: bool) -> dict:
    out = {k: v for k, v in sc.items() if detail or k not in HEAVY}
    for k in SCENARIO_QTY:
        if sc.get(k) is not None:
            out[k] = _d(sc[k])
            if detail:
                out[k + "_exact"] = sc[k]
    if detail:
        bd = sc.get("breakdown")
        if bd:
            nb = dict(bd)
            for k in BREAKDOWN_QTY:
                if bd.get(k) is not None:
                    nb[k] = _d(bd[k])
                    nb[k + "_exact"] = bd[k]
            out["breakdown"] = nb
        out["explanation"] = [dict(s) for s in sc.get("explanation", [])]
        out["events"] = [{**e, "units": _d(e["units"]), "units_exact": e["units"]} for e in sc.get("events", [])]
        out["series"] = [{**r, **{k: _d(r[k]) for k in SERIES_QTY}} for r in sc.get("series", [])]
    return out


def _forecast(fc: dict | None, detail: bool) -> dict | None:
    if fc is None:
        return None
    out = {k: v for k, v in fc.items() if detail or k not in ("month_total_exact", "note", "masked_days")}
    out["sum_28"] = _d(fc["sum_28"])
    if detail:
        out["sum_28_exact"] = fc["sum_28"]
    return out


def _item(d: dict, detail: bool) -> dict:
    out = {"producto_id": d["producto_id"], "producto": d["producto"], "categoria": d.get("categoria", ""),
           "unidad_descripcion": d.get("unidad_descripcion", ""), "unidad_reporte": d.get("unidad_reporte"),
           "status": d["status"], "reason": d.get("reason"), "forecast": _forecast(d.get("forecast"), detail),
           "count_stock": d["count_stock"],
           "scenarios": {k: _scenario(v, detail) for k, v in d["scenarios"].items()}}
    if detail:
        out.update(plan_id=d["plan_id"], pending_orders=d.get("pending_orders", []), statuses=d.get("statuses", []))
    return out


def _readable_plan(db, plan_id: str) -> dict:
    p = db[store.RUNS].find_one({"plan_id": plan_id, "status": "completed"}, {"_id": 0})
    if p is None:
        raise ApiError(404, "NO_ENCONTRADO", "Plan no encontrado.")
    return p


def _plan_summary(p: dict) -> dict:
    return {"plan_id": p["plan_id"], "month": p["month"], "decision_date": p["params"]["decision_date"],
            "lead_days": p["params"]["lead_days"], "status": p["status"], "created_at": iso_utc(p.get("created_at")),
            "dataset_id": p["dataset"]["dataset_id"], "snapshot_id": p["snapshot"]["snapshot_id"], "counts": p["counts"],
            "version": p.get("version"), "label": p.get("label", LABEL)}


def list_plans(db, month: str | None, page: int, page_size: int) -> dict:
    flt: dict = {"status": "completed"}
    if month:
        flt["month"] = month
    total = db[store.RUNS].count_documents(flt)
    cur = db[store.RUNS].find(flt, {"_id": 0}).sort([("created_at", -1), ("plan_id", 1)]) \
        .skip((page - 1) * page_size).limit(page_size)
    out = page_response([_plan_summary(p) for p in cur], total, page, page_size)
    if total == 0:
        out["unavailable_reason"] = UNAVAILABLE
    return out


def get_plan(db, plan_id: str) -> dict:
    p = _readable_plan(db, plan_id)
    out = _plan_summary(p)
    out.update(dates=p["dates"], distances=p["distances"], params=p["params"], dataset={**p["dataset"],
               "imported_at": iso_utc(p["dataset"].get("imported_at"))}, snapshot=p["snapshot"],
               method=p["method"], engine_version=p["engine_version"], contract_version=p["contract_version"],
               assumptions=p["assumptions"], warnings=p["warnings"], provenance=p["provenance"],
               completed_at=iso_utc(p.get("completed_at")))
    return out


def _filter(plan: dict, q: str | None) -> dict:
    """Resultados PUBLICADOS del plan (R19: solo los del intento `children_ref`) y busqueda opcional."""
    base: dict = store.children_filter(plan)
    if q:
        rx = re.escape(q)
        base["$or"] = [{"producto_id": {"$regex": f"^{rx}"}}, {"producto": {"$regex": rx, "$options": "i"}}]
    return base


def get_results(db, plan_id: str, *, q: str | None, status: str | None, sort: str | None, page: int,
                page_size: int) -> dict:
    plan = _readable_plan(db, plan_id)
    leads = plan["params"]["lead_days"]
    if sort is not None and not SORT_RE.match(sort):
        raise invalid("Campo de orden no permitido.", [{"campo": "sort", "motivo": "fuera de la lista"}])
    allowed = {"producto_id": [("producto_id", 1)], "-producto_id": [("producto_id", -1)],
               "producto": [("producto", 1), ("producto_id", 1)], "-producto": [("producto", -1), ("producto_id", 1)],
               "forecast": [("sortkeys.forecast", 1), ("producto_id", 1)],
               "-forecast": [("sortkeys.forecast", -1), ("producto_id", 1)],
               "libre": [("sortkeys.libre", 1), ("producto_id", 1)], "-libre": [("sortkeys.libre", -1), ("producto_id", 1)],
               "status": [("status", 1), ("producto_id", 1)], "-status": [("status", -1), ("producto_id", 1)]}
    for lead in leads:
        allowed[f"purchase_{lead}"] = [(f"sortkeys.purchase_{lead}", 1), ("producto_id", 1)]
        allowed[f"-purchase_{lead}"] = [(f"sortkeys.purchase_{lead}", -1), ("producto_id", 1)]
    order = check_sort(sort, allowed, "producto_id")
    base = _filter(plan, q)
    coll = db[store.RESULTS]
    counts = {s: coll.count_documents({**base, "status": s}) for s in engine.STATUSES}
    by_lead = {str(lead): {s: coll.count_documents({**base, f"scenarios.{lead}.status": s}) for s in engine.STATUSES}
               for lead in leads}
    total_all = sum(counts.values())
    flt = {**base, "status": status} if status else base
    proj = {"_id": 0, "sortkeys": 0, "statuses": 0, "pending_orders": 0, "attempt": 0}
    for lead in leads:
        for h in HEAVY:
            proj[f"scenarios.{lead}.{h}"] = 0
    cur = coll.find(flt, proj).sort(order).skip((page - 1) * page_size).limit(page_size)
    items = [_item(d, False) for d in cur]
    resp = page_response(items, counts[status] if status else total_all, page, page_size)
    return {"plan": _plan_summary(plan), **resp, "status_counts": {"all": total_all, **counts},
            "scenario_status_counts": by_lead, "label": LABEL,
            "note": "Cantidades en la presentación de cada producto; no se suman productos distintos."}


def get_result(db, plan_id: str, producto_id: str) -> dict:
    plan = _readable_plan(db, plan_id)
    d = db[store.RESULTS].find_one({**store.children_filter(plan), "producto_id": producto_id}, {"_id": 0, "sortkeys": 0, "attempt": 0})
    if d is None:
        raise ApiError(404, "NO_ENCONTRADO", "Producto no encontrado en el plan.")
    return {**_item(d, True), "label": LABEL}


# ------------------------------------------------------------------ entradas disponibles
def inputs(db) -> dict:
    ds, sn = sales.get_dataset(db), store.get_snapshot(db)
    reason = None
    if ds is None:
        reason = "SIN_DATASET"
    elif sn is None:
        reason = "SIN_INVENTARIO_INFORMADO"
    dataset = None if ds is None else {
        "dataset_id": ds["dataset_id"], "sales_cutoff": str(ds["sales_cutoff"])[:10], "source_rows": ds.get("source_rows"),
        "classes": dict(ds.get("counts", {})), "imported_at": iso_utc(ds.get("imported_at"))}
    snapshot = None if sn is None else {
        "snapshot_id": sn["snapshot_id"], "as_of_local": sn["as_of_local"],
        "warehouse": {"id": sn["warehouse"]["id"], "name": sn["warehouse"]["name"]},
        "products": db[store.ITEM_COLL].count_documents({"snapshot_id": sn["snapshot_id"]})}
    out = {"label": LABEL, "dataset": dataset, "snapshot": snapshot,
           "defaults": {"month": "2026-11", "decision_date": "2026-10-18", "lead_days": [7, 14], "reserve_days": 7,
                        "min_order": 1, "order_multiple": 1, "pending_orders": []},
           "assumptions": [{"code": "PEDIDOS_PENDIENTES", "nature": "SUPUESTO",
                            "text": "En este escenario no llegan otros pedidos (0 asumido; no es un dato informado por la empresa)."},
                           *PLAN_ASSUMPTION_DEFAULTS]}
    if reason:
        out["unavailable_reason"] = reason
        out["limits"] = {"months": [], "lead_min": engine.LEAD_MIN, "lead_max": engine.LEAD_MAX,
                         "max_leads": engine.MAX_LEADS, "horizon_days": engine.HORIZON_DAYS, "decision_min": None,
                         "decision_max": None}
        return out
    cutoff, count = sales.cutoff_of(ds), store.count_date_of(sn)
    months = engine.allowed_months(count, cutoff)
    detail = []
    for m in months:
        s, e = engine.month_bounds(m)
        detail.append({"month": m, "start": s.isoformat(), "end": e.isoformat(), "decision_max": e.isoformat(),
                       "extrapolation_days_to_start": (s - cutoff).days, "extrapolation_days_to_end": (e - cutoff).days})
    out["defaults"]["decision_date"] = count.isoformat()
    if months:
        out["defaults"]["month"] = months[0]
    out["limits"] = {"decision_min": count.isoformat(), "decision_max": detail[-1]["decision_max"] if detail else None,
                     "months": months, "months_detail": detail, "lead_min": engine.LEAD_MIN, "lead_max": engine.LEAD_MAX,
                     "max_leads": engine.MAX_LEADS, "reserve_min": 0, "reserve_max": engine.RESERVE_MAX,
                     "horizon_days": engine.HORIZON_DAYS, "horizon_last_day": (cutoff + timedelta(days=engine.HORIZON_DAYS)).isoformat(),
                     "pending_arrival_min": (count + timedelta(days=1)).isoformat()}
    out["distances"] = {"cutoff_to_count": (count - cutoff).days}
    return out


# ------------------------------------------------------------------ encolado
def create_plan(db, raw: dict, created_by: str) -> dict:
    """Valida, calcula la identidad y encola `generate_plan` (o devuelve el plan ya completado)."""
    try:
        params, plan_id, ds, sn, _items = store.resolve(db, raw)
    except PlanRejected as exc:
        status = 409 if exc.code in ("DATASET_NO_DISPONIBLE", "INVENTARIO_NO_DISPONIBLE") else 422
        raise ApiError(status, exc.code, exc.message,
                       [{"campo": exc.field, "motivo": exc.message}] if exc.field else None) from None
    done = db[store.RUNS].find_one({"plan_id": plan_id, "status": "completed"}, {"job_id": 1, "_id": 0})
    if done is not None:
        return {"plan_id": plan_id, "job_id": done.get("job_id"), "status": "completed", "reused": True}
    queue.ensure_indexes(db)
    job_input = {"plan_id": plan_id, "dataset_id": ds["dataset_id"], "snapshot_id": sn["snapshot_id"],
                 "params": params.to_dict()}
    public = {"plan_id": plan_id, "month": params.month, "decision_date": params.decision_date.isoformat(),
              "lead_days": list(params.lead_days)}
    for n in range(20):          # un trabajo fallido de forma permanente no bloquea un reintento explicito
        key = f"plan:{plan_id}" + (f":r{n}" if n else "")
        job, created = queue.enqueue(db, "generate_plan", job_input, key, created_by, public=public)
        if created or job["status"] != "failed":
            return {"plan_id": plan_id, "job_id": job["job_id"], "status": job["status"], "reused": not created}
    raise ApiError(409, "REINTENTOS_AGOTADOS", "El plan falló repetidamente; revise los trabajos.")


__all__ = ["create_plan", "get_plan", "get_result", "get_results", "inputs", "list_plans"]
