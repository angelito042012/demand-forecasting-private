"""Repositorios de lectura de documentos PUBLICADOS (runs, forecasts, recommendations, backtests).

Solo leen corridas `completed`; nunca reentrenan ni simulan. Sin rutas locales ni binarios.
"""
from __future__ import annotations

from datetime import date

from backend.app.errors import ApiError, page_response

from .common import (
    SIM_LABEL,
    active_run_id,
    check_dates,
    check_sort,
    completed_run,
    iso_utc,
    run_header,
    sim_labels,
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


def public_run(db, run: dict, *, detail: bool) -> dict:
    out = {**run_header(db, run), "kind": run.get("kind"), "status": run["status"],
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
            "fingerprint_short": str(run.get("fingerprint", ""))[:12]})
    return out


def list_runs(db, page: int, page_size: int) -> dict:
    items, total = _page(db.runs, {"status": "completed"}, [("published_at", -1), ("run_id", 1)],
                         page, page_size, _INTERNAL_RUN_FIELDS)
    return page_response([public_run(db, r, detail=False) for r in items], total, page, page_size)


def get_run(db, run_id: str) -> dict:
    return public_run(db, completed_run(db, run_id), detail=True)


def list_forecasts(db, *, run_id, level, sku, categoria, cohorte, frm: date | None, to: date | None,
                   sort, page, page_size) -> dict:
    check_dates(frm, to)
    order = check_sort(sort, FORECAST_SORTS, "target_date")
    run = completed_run(db, run_id)
    q: dict = {"run_id": run["run_id"], "level": level}
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
    resp = page_response(docs, total, page, page_size)
    resp.update({"run": run_header(db, run), "unit": "unidad base", "provenance": "OBSERVED_EXCEL"})
    return resp


def _rec_public(d: dict) -> dict:
    return d


def list_recommendations(db, *, run_id, categoria, sku, status, only_orders: bool, sort, page, page_size) -> dict:
    order = check_sort(sort, REC_SORTS, "sku")
    run = completed_run(db, run_id)
    q: dict = {"run_id": run["run_id"]}
    if categoria:
        q["categoria"] = categoria
    if sku:
        q["sku"] = sku
    if status:
        q["status"] = status
    if only_orders:
        q["order_qty"] = {"$gt": 0}
    docs, total = _page(db.recommendations, q, order, page, page_size, {"_id": 0, "schema_version": 0})
    resp = page_response(docs, total, page, page_size)
    resp.update({"run": run_header(db, run), **sim_labels(),
                 "nota": "Sugerencia hipotética de vista previa; no es un pedido ejecutado."})
    return resp


def get_recommendation(db, sku: str, run_id, almacen: str) -> dict:
    run = completed_run(db, run_id)
    doc = db.recommendations.find_one({"run_id": run["run_id"], "sku": sku, "almacen": almacen},
                                      {"_id": 0, "schema_version": 0})
    if doc is None:
        raise ApiError(404, "NO_ENCONTRADO", "Recomendación no encontrada.")
    doc["explanation"] = "\n".join(doc.get("explanation_steps", []))
    return {**doc, "run": run_header(db, run), "disclaimer": SIM_LABEL}


def _bt_meta(db, bt: dict, run: dict) -> dict:
    return {"backtest_id": bt["backtest_id"], "kind": bt["kind"], "label": bt.get("label"),
            "folds": bt.get("folds"), "created": iso_utc(bt.get("created")), "run_id": bt["run_id"],
            "scenario_id": bt["scenario_id"], "provenance": bt["provenance"], "disclaimer": bt["disclaimer"],
            "run": run_header(db, run)}


def list_backtests(db, run_id: str | None, page: int, page_size: int) -> dict:
    if run_id:
        runs = {completed_run(db, run_id)["run_id"]: completed_run(db, run_id)}
    else:
        runs = {r["run_id"]: r for r in db.runs.find({"status": "completed"}, {"_id": 0})}
    if not runs:
        return page_response([], 0, page, page_size)
    docs, total = _page(db.backtests, {"run_id": {"$in": list(runs)}}, [("created", -1), ("backtest_id", 1)],
                        page, page_size, {"_id": 0, "backtest_id": 1, "kind": 1, "label": 1, "folds": 1,
                                          "created": 1, "run_id": 1, "scenario_id": 1, "provenance": 1,
                                          "disclaimer": 1})
    return page_response([_bt_meta(db, d, runs[d["run_id"]]) for d in docs], total, page, page_size)


def get_backtest(db, backtest_id: str, view: str) -> dict:
    bt = db.backtests.find_one({"backtest_id": backtest_id}, {"_id": 0})
    run = db.runs.find_one({"run_id": bt["run_id"], "status": "completed"}, {"_id": 0}) if bt else None
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
