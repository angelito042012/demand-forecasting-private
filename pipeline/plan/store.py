"""T19 — Persistencia del plan: identidad, staging -> completed, idempotencia y recuperacion (contrato §5).

Colecciones propias `plan_runs` (cabecera) y `plan_results` (un documento por plan x producto). Solo LEE `plan_sales`,
`plan_datasets` e `inventory_reported_*`; no escribe en `recommendations`, `runs`, `inventory_snapshot` ni en T12.
Un resultado incompleto (staging) nunca es visible; un fallo conserva el ultimo plan completado.

R19 (REVISION_CODEX_19): PROPIEDAD POR INTENTO con fencing, como el publicador historico (`pipeline/publish/protocol.py`):
* la cabecera lleva `attempt` (token), `generation` (solo crece) y `lease_expires_at`; `claim_attempt` crea la cabecera o
  toma una `failed`/abandonada con CAS sobre (status, generation) de forma atomica ANTES de escribir o limpiar nada;
* los resultados de un intento se escriben con su `attempt` (su propio espacio) y el indice unico incluye `attempt`: un
  intento obsoleto nunca pisa ni borra los de otro; su limpieza solo borra `{plan_id, attempt: <su token>}`;
* antes de cada escritura se renueva el lease con CAS (`renew`): si el intento perdio la propiedad lanza
  `LostPlanOwnership` y se detiene sin escribir ni borrar nada ajeno (tampoco la cabecera);
* la publicacion es un CAS que pasa la cabecera a `completed` y fija `children_ref = attempt`: los lectores consultan solo
  los resultados cuyo `attempt == children_ref`; un intento obsoleto no puede completar, asi que sus filas son invisibles
  y luego `purge_orphans` las elimina (nunca las de `children_ref`).
"""
from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

from pymongo.errors import DuplicateKeyError

from pipeline.jobs.queue import LostOwnership
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
LEASE_SECONDS = 60


class LostPlanOwnership(LostOwnership):
    """Este intento ya no es el dueno del plan (lo tomo otro): se detiene sin escribir ni limpiar nada ajeno."""


def ensure_indexes(db) -> None:
    db[RUNS].create_index([("plan_id", 1)], name="plan_id_unique", unique=True)
    db[RUNS].create_index([("status", 1), ("month", 1), ("created_at", -1)], name="status_month_created")
    try:                                             # R19: el indice unico antiguo (sin `attempt`) impediria aislar intentos
        db[RESULTS].drop_index("plan_product_unique")
    except Exception:                                # noqa: BLE001, S110 - no existe (base nueva) o ya se migro
        pass
    db[RESULTS].create_index([("plan_id", 1), ("attempt", 1), ("producto_id", 1)], name="plan_attempt_product_unique", unique=True)


def children_filter(run: dict) -> dict:
    """Filtro de los resultados PUBLICADOS de un plan completado: los del intento `children_ref`. Los planes anteriores a R19
    (sin `children_ref`) tienen resultados sin campo `attempt`."""
    ref = run.get("children_ref")
    return {"plan_id": run["plan_id"], "attempt": ref} if ref else {"plan_id": run["plan_id"], "attempt": {"$exists": False}}


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


class Attempt:
    """Propiedad de un intento de generar un plan: (token, generation)."""

    def __init__(self, plan_id: str, token: str, generation: int, prior: str | None = None):
        # `prior` = token del intento abandonado/fallido que este toma (sus filas son las unicas que puede limpiar al empezar)
        self.plan_id, self.token, self.generation, self.prior = plan_id, token, generation, prior

    def owned(self) -> dict:
        return {"plan_id": self.plan_id, "status": "staging", "attempt": self.token, "generation": self.generation}


def _gen_filter(cur: dict) -> dict:
    """CAS sobre la generacion leida (o sobre su ausencia, en cabeceras anteriores a R19)."""
    return {"generation": cur["generation"]} if "generation" in cur else {"generation": {"$exists": False}}


def claim_attempt(db, head: dict) -> Attempt:
    """Crea la cabecera `staging` o toma una `failed`/abandonada (lease vencido) con CAS atomico. Si otro intento vigente la
    tiene => PLAN_EN_CURSO. No escribe resultados ni borra nada ajeno."""
    pid, token = head["plan_id"], head["attempt"]
    fresh = {**head, "generation": 1, "lease_expires_at": _now() + timedelta(seconds=LEASE_SECONDS)}
    for _ in range(4):
        try:
            db[RUNS].insert_one(dict(fresh))
            return Attempt(pid, token, 1)
        except DuplicateKeyError:
            pass
        cur = db[RUNS].find_one({"plan_id": pid}, {"_id": 0})
        if cur is None:
            continue
        lease = cur.get("lease_expires_at")
        if cur["status"] == "completed" or (cur["status"] == "staging" and lease is not None and lease > _now()):
            raise PlanRejected("PLAN_EN_CURSO", "Otro intento está generando este mismo plan; se reintentará.")
        gen = int(cur.get("generation", 0))
        won = db[RUNS].find_one_and_update(
            {"plan_id": pid, "status": cur["status"], **_gen_filter(cur)},
            {"$set": {**{k: v for k, v in head.items() if k != "plan_id"}, "status": "staging", "generation": gen + 1,
                      "lease_expires_at": _now() + timedelta(seconds=LEASE_SECONDS)},
             "$unset": {"error": "", "children_ref": ""}}, return_document=True)
        if won is not None:
            return Attempt(pid, token, gen + 1, prior=cur.get("attempt"))
    raise PlanRejected("PLAN_EN_CURSO", "Otro intento está generando este mismo plan; se reintentará.")


def renew(db, att: Attempt) -> None:
    """Renueva el lease con CAS sobre (attempt, generation, staging): si se perdio => LostPlanOwnership (sin escribir mas)."""
    r = db[RUNS].update_one(att.owned(), {"$set": {"lease_expires_at": _now() + timedelta(seconds=LEASE_SECONDS)}})
    if r.matched_count != 1:
        raise LostPlanOwnership(att.plan_id)


def purge_prior(db, att: Attempt) -> None:
    """Al empezar: borra SOLO las filas del intento abandonado que este tomo (token conocido y ya sin propiedad: no puede
    publicar). Nunca borra por `!=`: un sucesor posterior (o el plan publicado) tiene otro token y no se toca."""
    if att.prior and att.prior != att.token:
        db[RESULTS].delete_many({"plan_id": att.plan_id, "attempt": att.prior})


def purge_orphans(db, plan_id: str) -> None:
    """Mantenimiento seguro: solo si el plan YA esta `completed`, elimina las filas de intentos que no son `children_ref`
    (un plan completado ya no puede cambiar de intento publicado, asi que esas filas son definitivamente invisibles)."""
    run = db[RUNS].find_one({"plan_id": plan_id, "status": "completed"}, {"children_ref": 1, "_id": 0})
    if run and run.get("children_ref"):
        db[RESULTS].delete_many({"plan_id": plan_id, "attempt": {"$ne": run["children_ref"]}})


def generate_plan(db, raw_params, *, dataset_id: str | None = None, snapshot_id: str | None = None,
                  expected_plan_id: str | None = None, job_id: str | None = None, guard=None, progress=None) -> dict:
    """Genera (o reutiliza) el plan. `guard()` es el fencing del TRABAJO; ademas cada escritura renueva la propiedad del INTENTO."""
    if db.name in PROTECTED_DBS:
        raise PlanRejected("BASE_PROTEGIDA", "No se escribe en bases de desarrollo, v2 ni publicadas.")
    guard = guard or (lambda: None)
    params, plan_id, dataset, snapshot, items = resolve(db, raw_params, dataset_id, snapshot_id)
    if expected_plan_id and expected_plan_id != plan_id:
        raise PlanRejected("IDENTIDAD_NO_COINCIDE", "Las entradas del trabajo no producen el plan solicitado.")
    ensure_indexes(db)
    cur = db[RUNS].find_one({"plan_id": plan_id}, {"_id": 0})
    if cur and cur["status"] == "completed":
        if db[RESULTS].count_documents(children_filter(cur)) == cur["counts"]["products"]:
            return {"action": "reused", "plan_id": plan_id, "counts": cur["counts"], "version": cur["version"]}
        # danado: se rehace con CAS sobre su generacion (si otro lo rehace a la vez, uno gana)
        db[RUNS].update_one({"plan_id": plan_id, "status": "completed", **_gen_filter(cur)},
                            {"$set": {"status": "failed"}, "$unset": {"children_ref": ""}})
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
    token = uuid.uuid4().hex
    prior = db[RUNS].count_documents({"status": "completed", "month": params.month})
    ident = identity_of(params, dataset, snapshot)
    head = _header(plan_id, params, dataset, snapshot, token, job_id, prior + 1, ident)
    att = claim_attempt(db, head)                     # reclamacion atomica ANTES de limpiar o escribir
    try:
        renew(db, att)
        purge_prior(db, att)                          # solo las filas del intento abandonado que tomamos
        for i in range(0, len(docs), BATCH):
            guard()
            renew(db, att)
            if progress:
                progress("guardando resultados", {"productos": min(i + BATCH, len(docs)), "total": len(docs)})
            db[RESULTS].insert_many([{**d, "attempt": token} for d in docs[i:i + BATCH]])
        if db[RESULTS].count_documents({"plan_id": plan_id, "attempt": token}) != len(docs):
            raise PlanRejected("ESCRITURA_INCOMPLETA", "El número de resultados escritos no coincide.")
        guard()
        renew(db, att)
        done = db[RUNS].update_one(att.owned(), {"$set": {"status": "completed", "children_ref": token, "counts": counts,
                                                          "completed_at": _now()}, "$unset": {"lease_expires_at": ""}})
        if done.matched_count != 1:
            raise LostPlanOwnership(plan_id)          # perdio la propiedad justo al publicar: sus filas quedan invisibles
    except LostOwnership:
        _drop_own_results(db, plan_id, token)         # solo las de ESTE intento; cabecera y filas del sucesor intactas
        raise
    except BaseException as exc:
        # R19 (adenda 2): un error puede ser AMBIGUO (el servidor aplico la publicacion y se perdio la respuesta). Solo el intento
        # que logra pasar SU cabecera staging -> failed por CAS puede limpiar sus filas; si ya completo, o no se puede confirmar
        # el estado, se conservan (invisibles si no se publicaron; el siguiente intento las purga por su token).
        try:
            failed = db[RUNS].update_one(att.owned(), {"$set": {"status": "failed", "error": {"code": getattr(exc, "code", type(exc).__name__)}},
                                                       "$unset": {"lease_expires_at": ""}})
            if failed.matched_count == 1:
                _drop_own_results(db, plan_id, token)
        except Exception:                             # noqa: BLE001, S110 - estado incierto: no se borra nada por inferencia
            pass
        raise
    # R19 (adenda): a partir de aqui el plan YA esta publicado; nada puede deshacerlo. La purga de filas de intentos abandonados
    # es mantenimiento de mejor esfuerzo fuera del manejador de errores: si falla, esas filas siguen invisibles (children_ref).
    try:
        purge_orphans(db, plan_id)
    except Exception:                                 # noqa: BLE001, S110 - se purgaran en una ejecucion posterior
        pass
    return {"action": "created", "plan_id": plan_id, "counts": counts, "version": prior + 1}


def _drop_own_results(db, plan_id: str, token: str) -> None:
    try:
        db[RESULTS].delete_many({"plan_id": plan_id, "attempt": token})
    except Exception:                                 # noqa: BLE001, S110 - quedaran invisibles y se purgan despues
        pass
