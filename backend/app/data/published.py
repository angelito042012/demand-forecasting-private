"""Repositorios de lectura de documentos PUBLICADOS (runs, forecasts, recommendations, backtests).

Solo leen corridas `completed`; nunca reentrenan ni simulan. Sin rutas locales ni binarios.
"""
from __future__ import annotations

from datetime import date

from backend.app.errors import ApiError, page_response

from .common import (
    FINAL_UNAVAILABLE_REASON,
    SIM_LABEL,
    active_run_id,
    check_dates,
    check_dates_for_run,
    check_sort,
    child_key,
    completed_run,
    invalid,
    is_final,
    iso_utc,
    relabel,
    run_header,
    sim_labels,
    validation_status,
)

_INTERNAL_RUN_FIELDS = {"_id": 0, "idempotency_key": 0, "lease_expires_at": 0, "attempts": 0}
FORECAST_SORTS = {
    "target_date": [("target_date", 1), ("entity_id", 1)], "-target_date": [("target_date", -1), ("entity_id", 1)],
    "entity_id": [("entity_id", 1), ("target_date", 1)], "-entity_id": [("entity_id", -1), ("target_date", 1)],
    "pred_chosen": [("pred.promedio_28", 1), ("entity_id", 1), ("target_date", 1)],
    "-pred_chosen": [("pred.promedio_28", -1), ("entity_id", 1), ("target_date", 1)],
}
REC_SORTS = {
    "sku": [("sku", 1), ("almacen", 1)], "categoria": [("categoria", 1), ("sku", 1)],
    "order_qty": [("order_qty", 1), ("sku", 1)], "-order_qty": [("order_qty", -1), ("sku", 1)],
}


def _page(coll, query: dict, sort: list, page: int, page_size: int, projection: dict) -> tuple[list, int]:
    total = coll.count_documents(query)
    cur = (coll.find(query, projection).sort(sort).skip((page - 1) * page_size).limit(page_size)
           .allow_disk_use(True))
    return list(cur), total


def _final_package(run: dict) -> dict | None:
    """Resumen publico del paquete T12 (sello, fases, auditoria, correcciones); nada de rutas ni binarios."""
    fp = run.get("final_package")
    if not isinstance(fp, dict):
        return None
    seal = str(fp.get("seal_sha256") or "")
    return {"seal_sha256": seal or None, "seal_short": seal[:12] or None,
            "frozen_selection_sha256": fp.get("frozen_selection_sha256"),
            "phases": fp.get("phases") or {}, "corrections": fp.get("corrections") or [],
            "audit_ok": fp.get("audit_ok")}


def public_run(db, run: dict, *, detail: bool) -> dict:
    out = {**run_header(db, run), "final_package": _final_package(run),
           "origin": run.get("origin"), "target_start": run.get("target_start"),
           "target_end": run.get("target_end"), "horizon_days": run.get("horizon_days"),
           "evaluation_period": run.get("evaluation_period"), "method": run.get("method"),
           "counts": run.get("counts"), "coverage": run.get("coverage"), **sim_labels()}
    if detail:
        out.update({
            "config": run.get("config"), "sources": run.get("sources"),
            "artifacts": [{"name": a["name"], "sha256": a["sha256"], "size_bytes": a["size_bytes"]}
                          for a in run.get("artifacts", [])],
            "code": run.get("code"), "provenance_notes": run.get("provenance_notes"),
            "publisher": run.get("publisher"),
            "fingerprint_short": str(run.get("fingerprint", ""))[:12]})
    return out


def list_runs(db, page: int, page_size: int, status: str | None = None) -> dict:
    flt = {"status": status} if status else {"status": {"$in": ["completed", "superseded"]}}
    items, total = _page(db.runs, flt, [("published_at", -1), ("run_id", 1)],
                         page, page_size, _INTERNAL_RUN_FIELDS)
    return page_response([public_run(db, r, detail=False) for r in items], total, page, page_size)


def get_run(db, run_id: str) -> dict:
    return public_run(db, completed_run(db, run_id), detail=True)


def list_forecasts(db, *, run_id, level, sku, categoria, cohorte, frm: date | None, to: date | None,
                   sort, page, page_size) -> dict:
    order = check_sort(sort, FORECAST_SORTS, "target_date")
    try:
        run = completed_run(db, run_id)
    except ApiError:
        check_dates(frm, to)   # sin corrida resuelta rige la barrera general (agosto reservado)
        raise
    check_dates_for_run(run, frm, to)
    q: dict = {"run_id": child_key(run), "level": level}
    if sku:
        q["sku"] = sku
    if categoria:
        q["categoria"] = categoria
    if cohorte:
        q["cohorte"] = cohorte
    if frm or to:
        q["target_date"] = {**({"$gte": frm.isoformat()} if frm else {}),
                            **({"$lte": to.isoformat()} if to else {})}
    docs, total = _page(db.forecasts, q, order, page, page_size,
                        {"_id": 0, "schema_version": 0})
    resp = page_response(relabel(docs, run), total, page, page_size)
    resp.update({"run": run_header(db, run), "unit": "unidad base", "provenance": "OBSERVED_EXCEL"})
    if is_final(run):
        resp["warnings"] = run_header(db, run)["warnings"]
    return resp


def _rec_public(d: dict) -> dict:
    return d


def list_recommendations(db, *, run_id, categoria, sku, status, only_orders: bool, sort, page, page_size,
                         no_orders: bool = False) -> dict:
    order = check_sort(sort, REC_SORTS, "sku")
    run = completed_run(db, run_id)
    if is_final(run):
        # T11 §2: la evaluacion final no crea pedidos; no se usa el snapshot de otro dia.
        resp = page_response([], 0, page, page_size)
        resp.update({"run": run_header(db, run), "validation_status": validation_status(run), **sim_labels(),
                     "unavailable_reason": FINAL_UNAVAILABLE_REASON,
                     "see_run": active_run_id(db) or run.get("see_run"),
                     "nota": "La evaluación final no genera recomendaciones de compra; "
                             "consulte la demostración histórica."})
        return resp
    q: dict = {"run_id": child_key(run)}
    if categoria:
        q["categoria"] = categoria
    if sku:
        q["sku"] = sku
    if status:
        q["status"] = status
    if only_orders and no_orders:
        raise invalid("Elija solo una de las vistas con pedido o sin pedido.")
    if only_orders:
        q["order_qty"] = {"$gt": 0}
    if no_orders:
        # UX01: SKU con inventario simulado cuyo pedido sugerido es 0 (los sin snapshot tienen pedido null y no entran).
        q["order_qty"] = 0
    docs, total = _page(db.recommendations, q, order, page, page_size, {"_id": 0, "schema_version": 0})
    vs = validation_status(run)
    for d in docs:
        d["validation_status"] = vs
    resp = page_response(relabel(docs, run), total, page, page_size)
    resp.update({"run": run_header(db, run), "validation_status": vs, **sim_labels(),
                 "nota": "Sugerencia hipotética de vista previa; no es un pedido ejecutado."})
    return resp


def get_recommendation(db, sku: str, run_id, almacen: str) -> dict:
    run = completed_run(db, run_id)
    if is_final(run):
        raise ApiError(404, "NO_ENCONTRADO", "La evaluación final no genera recomendaciones.")
    doc = db.recommendations.find_one({"run_id": child_key(run), "sku": sku, "almacen": almacen},
                                      {"_id": 0, "schema_version": 0})
    if doc is None:
        raise ApiError(404, "NO_ENCONTRADO", "Recomendación no encontrada.")
    relabel([doc], run)
    doc["explanation"] = "\n".join(doc.get("explanation_steps", []))
    return {**doc, "validation_status": validation_status(run), "run": run_header(db, run), "disclaimer": SIM_LABEL}


def _bt_meta(db, bt: dict, run: dict) -> dict:
    # id publico estable = "bt-<run_id publico>" (el documento guarda el id del intento que lo escribio)
    return {"backtest_id": f"bt-{run['run_id']}", "kind": bt["kind"], "label": bt.get("label"),
            "folds": bt.get("folds"), "created": iso_utc(bt.get("created")), "run_id": run["run_id"],
            "scenario_id": bt.get("scenario_id"), "provenance": bt["provenance"], "disclaimer": bt["disclaimer"],
            "run": run_header(db, run)}


def list_backtests(db, run_id: str | None, page: int, page_size: int) -> dict:
    if run_id:
        run = completed_run(db, run_id)
        runs = {child_key(run): run}
    else:
        runs = {child_key(r): r for r in db.runs.find({"status": {"$in": ["completed", "superseded"]}}, {"_id": 0})}
    if not runs:
        return page_response([], 0, page, page_size)
    docs, total = _page(db.backtests, {"run_id": {"$in": list(runs)}}, [("created", -1), ("backtest_id", 1)],
                        page, page_size, {"_id": 0, "backtest_id": 1, "kind": 1, "label": 1, "folds": 1,
                                          "created": 1, "run_id": 1, "scenario_id": 1, "provenance": 1,
                                          "disclaimer": 1})
    return page_response([_bt_meta(db, d, runs[d["run_id"]]) for d in docs], total, page, page_size)


def get_backtest(db, backtest_id: str, view: str) -> dict:
    if not backtest_id.startswith("bt-"):
        raise ApiError(404, "NO_ENCONTRADO", "Backtest no encontrado.")
    run = db.runs.find_one({"run_id": backtest_id[3:], "status": {"$in": ["completed", "superseded"]}}, {"_id": 0})
    bt = db.backtests.find_one({"run_id": child_key(run)}, {"_id": 0}) if run else None
    if bt is None or run is None:
        raise ApiError(404, "NO_ENCONTRADO", "Backtest no encontrado.")
    out = _bt_meta(db, bt, run)
    out["view"] = view
    out["run_label"] = out["run"]["run_label"]
    if view in ("predictive", "all"):
        out.update({"predictive": bt["predictive"], "selection": bt["selection"], "coverage": bt["coverage"]})
    if view in ("simulation", "all"):
        out.update({"simulation": bt["simulation"], "simulation_differences": bt.get("simulation_differences", []),
                    "assumptions": bt["assumptions"]})
    return out


def has_active(db) -> bool:
    return active_run_id(db) is not None
