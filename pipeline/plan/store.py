"""T19 — Persistencia del plan: identidad, staging -> completed, idempotencia y recuperacion (contrato §5).

Colecciones propias `plan_runs` (cabecera) y `plan_results` (un documento por plan x producto). Solo LEE `plan_sales`,
`plan_datasets` e `inventory_reported_*`; no escribe en `recommendations`, `runs`, `inventory_snapshot` ni en T12.
Un resultado incompleto (staging) nunca es visible; un fallo conserva el ultimo plan completado.
"""
from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from pymongo.errors import DuplicateKeyError

from pipeline.plan import engine, sales
from pipeline.plan.engine import PlanParams, PlanRejected

RUNS = "plan_runs"
RESULTS = "plan_results"
SNAP_COLL = "inventory_reported_snapshots"
ITEM_COLL = "inventory_reported_items"
PROTECTED_DBS = frozenset({"demand_forecasting_dev", "demand_forecasting_v2", "demand_forecasting_pub"})
SCHEMA_VERSION = 1
BATCH = 25
LABEL = "Plan de compra bajo supuestos"


def ensure_indexes(db) -> None:
    db[RUNS].create_index([("plan_id", 1)], name="plan_id_unique", unique=True)
    db[RUNS].create_index([("status", 1), ("month", 1), ("created_at", -1)], name="status_month_created")
    db[RESULTS].create_index([("plan_id", 1), ("producto_id", 1)], name="plan_product_unique", unique=True)


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None, microsecond=0)


# ------------------------------------------------------------------ entradas
def get_snapshot(db, snapshot_id: str | None = None) -> dict | None:
    """Snapshot T18: el `current` mas reciente, o el indicado (current/superseded). Solo lectura."""
    coll = db[SNAP_COLL]
    if snapshot_id:
        return coll.find_one({"snapshot_id": snapshot_id, "status": {"$in": ["current", "superseded"]}}, {"_id": 0})
    return coll.find_one({"status": "current"}, {"_id": 0}, sort=[("as_of_utc", -1), ("version", -1)])


def snapshot_items(db, snapshot_id: str) -> list[dict]:
    return list(db[ITEM_COLL].find({"snapshot_id": snapshot_id}, {"_id": 0}).sort("producto_id", 1))


def count_date_of(snapshot: dict) -> date:
    return date.fromisoformat(str(snapshot["as_of_local"])[:10])


def identity_of(params: PlanParams, dataset: dict, snapshot: dict) -> dict:
    src = snapshot.get("source", {})
    return engine.identity(params, dataset_id=dataset["dataset_id"], sales_cutoff=str(dataset["sales_cutoff"])[:10],
                           snapshot_id=snapshot["snapshot_id"], snapshot_sha256=str(src.get("sha256", "")),
                           snapshot_csv_sha256=str(src.get("csv_sha256", "")))


def resolve(db, raw_params, dataset_id: str | None = None, snapshot_id: str | None = None):
    """(params validados, plan_id, dataset, snapshot, items). Lanza PlanRejected."""
    dataset = sales.get_dataset(db, dataset_id)
    if dataset is None:
        raise PlanRejected("DATASET_NO_DISPONIBLE", "No hay un dataset de ventas cargado para planificar.")
    snapshot = get_snapshot(db, snapshot_id)
    if snapshot is None:
        raise PlanRejected("INVENTARIO_NO_DISPONIBLE", "No hay un conteo de inventario informado para planificar.")
    items = snapshot_items(db, snapshot["snapshot_id"])
    cutoff = sales.cutoff_of(dataset)
    params = engine.validate_params(raw_params, count_date=count_date_of(snapshot), sales_cutoff=cutoff,
                                    group_ids=[i["producto_id"] for i in items])
    return params, engine.plan_id_for(params, identity_of(params, dataset, snapshot)), dataset, snapshot, items


# ------------------------------------------------------------------ cabecera
ASSUMPTIONS = [
    ("SIN_MOVIMIENTOS_TRAS_CONTEO", "No hay movimientos después del conteo del 18/10 a las 17:00; la simulación empieza el día siguiente."),
    ("DEMANDA_CONSTANTE", "La demanda diaria prevista es constante e igual a la media de los últimos 28 días con ventas; sin estacionalidad."),
    ("VENTAS_OBSERVADAS", "La previsión estima ventas observadas, que pueden haber estado limitadas por disponibilidad."),
    ("FALTANTE_NO_SE_REPONE", "Lo que no se puede atender es venta perdida: no se arrastra ni se repone con la orden nueva."),
    ("ORDEN_UNICA", "Una sola orden por producto en la fecha de decisión; no es un pedido ejecutado."),
    ("RESERVA", "La reserva son días de ventas previstas; no es una garantía estadística de servicio."),
]


def _assumptions(params: PlanParams) -> list[dict]:
    out = [{"code": c, "text": t, "nature": "SUPUESTO"} for c, t in ASSUMPTIONS]
    if params.pending:
        out.insert(0, {"code": "PEDIDOS_PENDIENTES", "nature": "DECLARADO",
                       "text": f"Pedidos por recibir declarados: {len(params.pending)} (con fecha de llegada y naturaleza)."})
    else:
        out.insert(0, {"code": "PEDIDOS_PENDIENTES", "nature": "SUPUESTO",
                       "text": "En este escenario no llegan otros pedidos (0 asumido; no es un dato informado por la empresa)."})
    out += [{"code": "PLAZOS", "nature": "SUPUESTO",
             "text": f"Plazos de entrega supuestos en días naturales: {', '.join(str(x) for x in params.lead_days)}."},
            {"code": "MINIMO_MULTIPLO", "nature": "SUPUESTO",
             "text": f"Mínimo {params.min_order} y múltiplo {params.order_multiple} (unidades de reporte)."}]
    return out


def _header(plan_id, params, dataset, snapshot, token, job_id, version, ident) -> dict:
    cutoff, count = sales.cutoff_of(dataset), count_date_of(snapshot)
    ms, me = engine.month_bounds(params.month)
    src = snapshot.get("source", {})
    return {
        "plan_id": plan_id, "status": "staging", "attempt": token, "label": LABEL, "version": version,
        "month": params.month, "method": engine.METHOD, "engine_version": engine.ENGINE_VERSION,
        "contract_version": engine.CONTRACT_VERSION, "schema_version": SCHEMA_VERSION, "job_id": job_id,
        "created_at": _now(), "completed_at": None, "identity": ident,
        "dataset": {"dataset_id": dataset["dataset_id"], "version": dataset.get("version"), "sales_cutoff": cutoff.isoformat(),
                    "source_rows": dataset.get("source_rows"), "classes": dict(dataset.get("counts", {})),
                    "imported_at": dataset.get("imported_at")},
        "snapshot": {"snapshot_id": snapshot["snapshot_id"], "version": snapshot.get("version"),
                     "as_of_local": snapshot["as_of_local"], "warehouse": dict(snapshot.get("warehouse", {})),
                     "sha256_short": str(src.get("sha256", ""))[:12], "csv_sha256_short": str(src.get("csv_sha256", ""))[:12]},
        "dates": {"sales_cutoff": cutoff.isoformat(), "count_date": count.isoformat(),
                  "count_as_of_local": snapshot["as_of_local"], "decision_date": params.decision_date.isoformat(),
                  "month_start": ms.isoformat(), "month_end": me.isoformat(),
                  "window_start": sales.window_of(cutoff)[0].isoformat()},
        "distances": {"cutoff_to_count": (count - cutoff).days, "cutoff_to_month_start": (ms - cutoff).days,
                      "cutoff_to_month_end": (me - cutoff).days, "count_to_decision": (params.decision_date - count).days,
                      "horizon_limit_days": engine.HORIZON_DAYS},
        "params": params.to_dict(), "assumptions": _assumptions(params),
        "warnings": [("Planificación con información desactualizada: las ventas reales terminan el "
                      f"{cutoff.isoformat()}; el período entre ese corte y el mes objetivo es desconocido, no cero."),
                     "Plan de compra bajo supuestos; no es un pedido ejecutado ni una mejora comprobada."],
        "provenance": {"sales": f"VENTAS_REALES_HASTA_{cutoff.isoformat()}",
                       "initial_stock": f"CONTEO_REPORTADO_{snapshot['as_of_local']}",
                       "projection": "CALCULADA_PROMEDIO_28", "parameters": "SUPUESTO_EDITABLE"},
        "counts": None}


def _product_doc(plan_id, item, params, count_date, cutoff, ps, pending, as_of_local) -> dict:
    res = engine.compute_product(params=params, count_date=count_date, sales_cutoff=cutoff, libre=item.get("libre"),
                                 unidad_reporte=item.get("unidad_reporte"), by_day=ps.by_day,
                                 window_units=ps.window_units, history_units=ps.history_units,
                                 history_rows=ps.history_rows, pending=pending)
    sortkeys = {"libre": item.get("libre"),
                "forecast": float(engine.parse_exact(res["forecast"]["month_total_exact"])) if res["forecast"] else None}
    for lead, sc in res["scenarios"].items():
        sortkeys[f"purchase_{lead}"] = sc["purchase_qty"]
    return {"plan_id": plan_id, "producto_id": item["producto_id"], "producto": item["producto"],
            "categoria": item.get("categoria", ""), "unidad_reporte": item.get("unidad_reporte"),
            "unidad_descripcion": item.get("unidad_descripcion", ""), "status": res["status"],
            "statuses": res["statuses"], "reason": res["reason"], "forecast": res["forecast"],
            "count_stock": {"libre": item.get("libre"), "as_of_local": as_of_local},
            "pending_orders": [{"arrival_date": d.isoformat(), "units": int(q)} for d, q in sorted((pending or {}).items())],
            "scenarios": res["scenarios"], "sortkeys": sortkeys}


def _counts(docs: list[dict], leads) -> dict:
    by = {s: 0 for s in engine.STATUSES}
    for d in docs:
        by[d["status"]] += 1
    per_lead = {str(lead): {s: 0 for s in engine.STATUSES} for lead in leads}
    for d in docs:
        for lead, sc in d["scenarios"].items():
            per_lead[lead][sc["status"]] += 1
    return {"products": len(docs), "by_status": by, "by_scenario": per_lead}


def clean_attempt(db, plan_id: str) -> None:
    """Limpia el intento previo (staging/failed) de ESTE plan_id; nunca toca otros planes ni uno completado."""
    db[RESULTS].delete_many({"plan_id": plan_id})
    db[RUNS].delete_many({"plan_id": plan_id, "status": {"$in": ["staging", "failed"]}})


def generate_plan(db, raw_params, *, dataset_id: str | None = None, snapshot_id: str | None = None,
                  expected_plan_id: str | None = None, job_id: str | None = None, guard=None, progress=None) -> dict:
    """Genera (o reutiliza) el plan. `guard()` se llama antes de cada escritura (fencing del trabajo)."""
    if db.name in PROTECTED_DBS:
        raise PlanRejected("BASE_PROTEGIDA", "No se escribe en bases de desarrollo, v2 ni publicadas.")
    guard = guard or (lambda: None)
    params, plan_id, dataset, snapshot, items = resolve(db, raw_params, dataset_id, snapshot_id)
    if expected_plan_id and expected_plan_id != plan_id:
        raise PlanRejected("IDENTIDAD_NO_COINCIDE", "Las entradas del trabajo no producen el plan solicitado.")
    ensure_indexes(db)
    cur = db[RUNS].find_one({"plan_id": plan_id}, {"_id": 0})
    if cur and cur["status"] == "completed":
        if db[RESULTS].count_documents({"plan_id": plan_id}) == cur["counts"]["products"]:
            return {"action": "reused", "plan_id": plan_id, "counts": cur["counts"], "version": cur["version"]}
        db[RUNS].update_one({"plan_id": plan_id, "status": "completed"}, {"$set": {"status": "failed"}})   # danado: se rehace
    cutoff, count = sales.cutoff_of(dataset), count_date_of(snapshot)
    sales.check_coverage(dataset, cutoff)
    if progress:
        progress("leyendo ventas", {"productos": len(items)})
    sdata = sales.load_sales(db, dataset["dataset_id"], [i["producto_id"] for i in items], cutoff)
    pend = params.pending_by_product()
    docs = [_product_doc(plan_id, it, params, count, cutoff, sdata[it["producto_id"]], pend.get(it["producto_id"]),
                         snapshot["as_of_local"]) for it in items]
    counts = _counts(docs, params.lead_days)
    guard()
    clean_attempt(db, plan_id)
    token = uuid.uuid4().hex
    prior = db[RUNS].count_documents({"status": "completed", "month": params.month})
    ident = identity_of(params, dataset, snapshot)
    head = _header(plan_id, params, dataset, snapshot, token, job_id, prior + 1, ident)
    try:
        db[RUNS].insert_one(dict(head))
    except DuplicateKeyError:
        raise PlanRejected("PLAN_EN_CURSO", "Otro intento está generando este mismo plan; se reintentará.") from None
    try:
        for i in range(0, len(docs), BATCH):
            guard()
            if progress:
                progress("guardando resultados", {"productos": min(i + BATCH, len(docs)), "total": len(docs)})
            db[RESULTS].insert_many(docs[i:i + BATCH])
        if db[RESULTS].count_documents({"plan_id": plan_id}) != len(docs):
            raise PlanRejected("ESCRITURA_INCOMPLETA", "El número de resultados escritos no coincide.")
        guard()
        done = db[RUNS].update_one({"plan_id": plan_id, "status": "staging", "attempt": token},
                                   {"$set": {"status": "completed", "counts": counts, "completed_at": _now()}})
        if done.matched_count != 1:
            raise PlanRejected("ESCRITURA_INCOMPLETA", "El intento perdió su cabecera; no se publicó.")
    except BaseException as exc:
        # fallo: se descartan los resultados de ESTE intento y se deja `failed`; los demas planes no se tocan
        try:
            db[RESULTS].delete_many({"plan_id": plan_id})
            db[RUNS].update_one({"plan_id": plan_id, "attempt": token, "status": "staging"},
                                {"$set": {"status": "failed", "error": {"code": getattr(exc, "code", type(exc).__name__)}}})
        except Exception:                      # noqa: BLE001, S110 - la limpieza se repite al reintentar por plan_id
            pass
        raise
    return {"action": "created", "plan_id": plan_id, "counts": counts, "version": prior + 1}

