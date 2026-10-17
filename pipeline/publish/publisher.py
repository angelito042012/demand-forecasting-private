"""Publicador con staging -> completed -> puntero activo (T08 §4).

Sin transacciones multidocumento: los hijos se insertan con un run_id propio, se validan
conteos y coherencia y solo entonces la corrida pasa a `completed` y se mueve el puntero.
Ante cualquier fallo la corrida queda `failed` (error generico), el puntero no cambia y los
lectores ignoran todo lo que no sea `completed`.
"""
from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from pymongo.errors import DuplicateKeyError

from . import builders as b
from .schema import SCHEMA_VERSION, ensure_schema, validate_doc
from .source import VerifiedSource

LEASE_MINUTES = 15
BATCH = 5000
CHILD_COLLECTIONS = ("forecasts", "recommendations", "backtests")


class PublishInProgressError(RuntimeError):
    """Otra publicacion con la misma clave sigue en staging con lease vigente."""


class PublishValidationError(RuntimeError):
    """La validacion de conteos/coherencia fallo antes de completar."""


@dataclass
class PublishResult:
    run_id: str
    status: str                  # "published" | "already_published"
    activated: bool
    counts: dict = field(default_factory=dict)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _generated_at(src: VerifiedSource) -> datetime:
    lima = datetime.strptime(src.manifest["generado_lima"], "%Y-%m-%d %H:%M").replace(
        tzinfo=ZoneInfo("America/Lima"))
    return lima.astimezone(UTC)


def run_identity(src: VerifiedSource, catalog_fingerprint: str) -> tuple[str, str, str]:
    import hashlib
    fp = hashlib.sha256(f"{src.source_fingerprint}|{catalog_fingerprint}".encode()).hexdigest()
    e = src.entry
    key = f"hist-dev:{e['fold']}:{e['cutoff']}:{fp[:24]}"
    run_id = f"hist-{e['cutoff'].replace('-', '')}-{fp[:12]}"
    return run_id, key, fp


def _insert_many(coll, docs: list, kind: str) -> None:
    for i in range(0, len(docs), BATCH):
        chunk = docs[i:i + BATCH]
        for d in chunk[:1] + chunk[-1:]:
            validate_doc(kind, d)
        coll.insert_many(chunk, ordered=False)


def delete_children(db, run_id: str) -> None:
    """Borra SOLO los hijos de este run_id."""
    for name in CHILD_COLLECTIONS:
        db[name].delete_many({"run_id": run_id})


def activate(db, run_id: str, now: datetime | None = None) -> None:
    run = db.runs.find_one({"run_id": run_id, "status": "completed"}, {"_id": 1})
    if run is None:
        raise PublishValidationError("solo una corrida completed puede ser activa")
    db.run_pointer.update_one({"_id": "active"}, {"$set": {"run_id": run_id, "updated_at": now or _utcnow()}},
                              upsert=True)


def _claim(db, doc: dict, now: datetime):
    """Reserva el idempotency_key. Devuelve ('existing', run) si ya esta completed, o ('claimed', None)."""
    key = doc["idempotency_key"]
    lease = now + timedelta(minutes=LEASE_MINUTES)
    for _ in range(3):
        cur = db.runs.find_one({"idempotency_key": key})
        if cur is None:
            try:
                db.runs.insert_one({**doc, "lease_expires_at": lease, "attempts": 1})
                return "claimed", None
            except DuplicateKeyError:
                continue
        if cur["status"] == "completed":
            return "existing", cur
        reusable = cur["status"] == "failed" or (cur["status"] == "staging"
                                                  and cur.get("lease_expires_at", now) <= now)
        if not reusable:
            raise PublishInProgressError("hay una publicacion en curso con la misma clave")
        got = db.runs.find_one_and_update(
            {"_id": cur["_id"], "status": cur["status"], "attempts": cur.get("attempts", 1)},
            {"$set": {**{k: v for k, v in doc.items() if k != "run_id"}, "lease_expires_at": lease},
             "$inc": {"attempts": 1}})
        if got is not None:
            delete_children(db, cur["run_id"])   # solo hijos de esa corrida
            return "claimed", None
    raise PublishInProgressError("no se pudo reservar la corrida")


def _fail(db, run_id: str, stage: str, exc: Exception, now: datetime) -> None:
    try:
        delete_children(db, run_id)
    except Exception:  # noqa: BLE001, S110 - limpieza best-effort; el reintento vuelve a limpiar
        pass
    db.runs.update_one({"run_id": run_id, "status": "staging"}, {"$set": {
        "status": "failed", "error": {"code": "PUBLICACION_FALLIDA", "stage": stage,
                                      "type": type(exc).__name__, "at": now}}})


def _close(a: float, b2: float) -> bool:
    return math.isclose(a, b2, rel_tol=1e-9, abs_tol=1e-9)


def validate_published(db, run_id: str, expected: dict) -> dict:
    """Paso 4 del contrato: conteos, categorias = suma de SKU, recomendaciones recalculables."""
    f, r = db.forecasts, db.recommendations
    n_sku = f.count_documents({"run_id": run_id, "level": "sku"})
    n_cat = f.count_documents({"run_id": run_id, "level": "categoria"})
    n_rec = r.count_documents({"run_id": run_id})
    n_ok = r.count_documents({"run_id": run_id, "status": "ok"})
    n_bt = db.backtests.count_documents({"run_id": run_id})
    got = {"forecasts_sku": n_sku, "forecasts_categoria": n_cat, "recommendations": n_rec,
           "recommendations_ok": n_ok, "backtests": n_bt}
    for k, v in got.items():
        if expected[k] != v:
            raise PublishValidationError(f"conteo {k}: esperado {expected[k]}, hallado {v}")
    skus_f = set(f.distinct("sku", {"run_id": run_id, "level": "sku"}))
    skus_r = set(r.distinct("sku", {"run_id": run_id}))
    if skus_f != skus_r:
        raise PublishValidationError("SKU con pronostico distintos de SKU con recomendacion")
    sums = {(g["_id"]["c"], g["_id"]["d"]): g for g in f.aggregate([
        {"$match": {"run_id": run_id, "level": "sku"}},
        {"$group": {"_id": {"c": "$categoria", "d": "$target_date"},
                    "p28": {"$sum": "$pred.promedio_28"}, "prf": {"$sum": "$pred.rf_categoria_distribuido"},
                    "obs": {"$sum": "$observed"}}}], allowDiskUse=True)}
    seen = 0
    for c in f.find({"run_id": run_id, "level": "categoria"}):
        s = sums.get((c["entity_id"], c["target_date"]))
        if s is None or not (_close(s["p28"], c["pred"]["promedio_28"])
                             and _close(s["prf"], c["pred"]["rf_categoria_distribuido"])
                             and s["obs"] == c["observed"]):
            raise PublishValidationError("categoria no es la suma de sus SKU")
        seen += 1
    if seen != len(sums):
        raise PublishValidationError("categorias incompletas")
    for d in r.find({"run_id": run_id, "status": "ok"}):
        calc = b.recompute_recommendation(d["on_hand"], d["in_transit"], d["mean_28"], d["forecast_14d"],
                                          d["unit_cost_assumed"])
        if (calc["target"] != d["target"] or calc["position"] != d["position"]
                or calc["order_qty"] != d["order_qty"] or d["in_transit"] < 0 or d["on_hand"] < 0
                or not _close(calc["safety"], d["safety"])):
            raise PublishValidationError(f"recomendacion no recalculable: {d['sku']}")
    if r.count_documents({"run_id": run_id, "status": "sin_snapshot",
                          "$or": [{f: {"$ne": None}} for f in b.NUM_FIELDS]}):
        raise PublishValidationError("sin_snapshot con campos numericos")
    return got


def publish(db, src: VerifiedSource, catalog: dict, catalog_fingerprint: str, *,
            now: datetime | None = None, activate_run: bool = True,
            stage_hook: Callable[[str], None] | None = None) -> PublishResult:
    """Publica la corrida. `stage_hook(etapa)` solo se usa en pruebas para simular fallos."""
    hook = stage_hook or (lambda _stage: None)
    now = now or _utcnow()
    ensure_schema(db)
    run_id, key, fp = run_identity(src, catalog_fingerprint)
    stage = "preparar"
    try:
        sku_docs, cat_docs, info = b.build_forecasts(src, catalog, run_id)
        recs = b.build_recommendations(src, catalog, run_id)
        backtest = b.build_backtest(src, run_id, now)
    except Exception as exc:
        raise PublishValidationError("no se pudieron construir los documentos") from exc
    n_ok = sum(1 for d in recs if d["status"] == "ok")
    counts = {"forecasts_sku": len(sku_docs), "forecasts_categoria": len(cat_docs),
              "recommendations": len(recs), "recommendations_ok": n_ok,
              "recommendations_sin_snapshot": len(recs) - n_ok,
              "recommendations_con_pedido": sum(1 for d in recs if d["status"] == "ok" and d["order_qty"] > 0),
              "backtests": 1}
    coverage = {"skus_pronosticados": info["skus"], "skus_con_recomendacion": n_ok,
                "skus_sin_snapshot": len(recs) - n_ok, "categorias": info["categorias"],
                "skus_categoria_desconocida": info["skus_categoria_desconocida"]}
    run_doc = b.build_run_doc(src, run_id, key, fp, _generated_at(src), coverage, counts)
    validate_doc("runs", run_doc)
    validate_doc("backtests", backtest)

    state, existing = _claim(db, run_doc, now)
    if state == "existing":
        if activate_run:
            activate(db, existing["run_id"], now)
        return PublishResult(existing["run_id"], "already_published", activate_run, existing.get("counts", {}))
    try:
        stage = "forecasts"
        _insert_many(db.forecasts, sku_docs, "forecasts")
        hook("forecasts_sku")
        _insert_many(db.forecasts, cat_docs, "forecasts")
        stage = "recomendaciones"
        _insert_many(db.recommendations, recs, "recommendations")
        hook("recommendations")
        stage = "backtests"
        db.backtests.insert_one(backtest)
        hook("backtests")
        stage = "validacion"
        validate_published(db, run_id, counts)
        hook("validacion")
        stage = "completar"
        db.runs.update_one({"run_id": run_id, "status": "staging"}, {"$set": {
            "status": "completed", "published_at": _utcnow(), "counts": counts, "coverage": coverage,
            "error": None, "schema_version": SCHEMA_VERSION}, "$unset": {"lease_expires_at": ""}})
        if db.runs.count_documents({"run_id": run_id, "status": "completed"}) != 1:
            raise PublishValidationError("no se pudo completar la corrida")
        hook("antes_puntero")
        if activate_run:
            activate(db, run_id, now)
    except Exception as exc:
        done = db.runs.find_one({"run_id": run_id, "status": "completed"}, {"_id": 1})
        if done is None:
            _fail(db, run_id, stage, exc, now)
        raise
    return PublishResult(run_id, "published", activate_run, counts)
