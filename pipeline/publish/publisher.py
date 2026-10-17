"""Publicador (T08 §4, reforzado en T10 §1): staging -> completed -> puntero activo con PROPIEDAD POR INTENTO.

La logica de concurrencia (claim con CAS, generation/fencing, lease renovable, hijos aislados por intento,
promocion atomica por CAS y puntero monotono) vive en `protocol.py`; aqui se arman los documentos de la
corrida historica T07 y se validan conteos/coherencia. Ante cualquier fallo la corrida del intento queda
`failed`, el puntero no cambia y los lectores solo ven corridas completed/superseded.
"""
from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from . import builders as b
from .protocol import (
    BATCH,  # noqa: F401  (reexportado)
    Attempt,
    LostOwnership,
    PublishInProgressError,
    PublishValidationError,
    activate_monotonic,
    claim_run,
    complete_run,
    delete_own_children,
    fail_attempt,
    guard,
    insert_children,
    purge_orphans,  # noqa: F401  (reexportado)
    stamp,
)
from .schema import QUALITY_ISSUES, ensure_schema, validate_doc
from .signals import Signals, parse_fraction
from .source import (
    PUBLISHER_VERSION,
    SourceVerificationError,
    VerifiedSource,
    verify_training_match,
)

__all__ = [
    "Attempt",
    "LostOwnership",
    "PublishInProgressError",
    "PublishResult",
    "PublishValidationError",
    "publish",
    "publish_prepared",
    "run_identity",
    "supersede",
    "validate_published",
]


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


def run_identity(src: VerifiedSource, catalog_fingerprint: str, signals_fingerprint: str) -> tuple[str, str, str]:
    """Identidad estable: mismos datos + codigo/config + version del publicador + senales exactas => misma corrida.
    Cambiar el algoritmo (PUBLISHER_VERSION) o las senales cambia la identidad; un reintento no."""
    import hashlib
    fp = hashlib.sha256(
        f"{PUBLISHER_VERSION}|{src.source_fingerprint}|{catalog_fingerprint}|{signals_fingerprint}".encode()).hexdigest()
    e = src.entry
    key = f"hist-dev:{e['fold']}:{e['cutoff']}:{fp[:24]}"
    run_id = f"hist-{e['cutoff'].replace('-', '')}-{fp[:12]}"
    return run_id, key, fp


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
        calc = b.recompute_recommendation(d["on_hand"], d["in_transit"], parse_fraction(d["sum_28"]), d["days_28"],
                                          d["unit_cost_assumed"])
        if (calc["target"] != d["target"] or calc["position"] != d["position"]
                or calc["order_qty"] != d["order_qty"] or d["in_transit"] < 0 or d["on_hand"] < 0
                or calc["target_raw_exact"] != d["target_raw_exact"]
                or not _close(calc["safety"], d["safety"]) or not _close(calc["mean_28"], d["mean_28"])):
            raise PublishValidationError(f"recomendacion no recalculable: {d['sku']}")
    if r.count_documents({"run_id": run_id, "status": "sin_snapshot",
                          "$or": [{f: {"$ne": None}} for f in b.NUM_FIELDS]}):
        raise PublishValidationError("sin_snapshot con campos numericos")
    return got


def supersede(db, old_run_id: str, new_run_id: str, issue_code: str, now: datetime | None = None) -> bool:
    """Marca una corrida anterior como SUSTITUIDA por un defecto de calidad. No borra ni altera sus hijos:
    los lectores derivan `validation_status` del estado de la corrida. Idempotente."""
    if issue_code not in QUALITY_ISSUES:
        raise PublishValidationError("codigo de incidencia de calidad desconocido")
    if old_run_id == new_run_id:
        raise PublishValidationError("una corrida no puede sustituirse a si misma")
    if db.runs.find_one({"run_id": new_run_id, "status": "completed"}, {"_id": 1}) is None:
        raise PublishValidationError("la corrida sustituta debe estar completed")
    res = db.runs.update_one({"run_id": old_run_id, "status": {"$in": ["completed", "superseded"]}}, {"$set": {
        "status": "superseded", "superseded_by": new_run_id, "superseded_at": now or _utcnow(),
        "quality_issue": {"code": issue_code, "message": QUALITY_ISSUES[issue_code],
                          "superseded_by": new_run_id}}})
    return res.matched_count == 1


def publish_prepared(db, run_doc: dict, prepared: dict, validate_fn: Callable, counts: dict, coverage: dict, *,
                     extra_guard: Callable[[], None] | None = None, activate_run: bool = True,
                     supersede_runs: list[str] | None = None, issue_code: str = "R05_PRECISION_RECOMENDACIONES",
                     now: datetime | None = None, stage_hook: Callable[[str], None] | None = None) -> PublishResult:
    """Publicacion generica con propiedad por intento (usada por la corrida historica y por las generadas).

    `prepared` = {coleccion: [docs]} construido con un run_id provisional (se re-etiqueta con el espacio del
    intento). `validate_fn(db, children_id)` valida conteos/coherencia sobre los hijos del intento."""
    hook = stage_hook or (lambda _stage: None)
    now = now or _utcnow()
    state, got = claim_run(db, run_doc, now)
    if state == "existing":
        if activate_run:
            activate_monotonic(db, got["run_id"], got.get("published_at") or now, now)
        for old in supersede_runs or []:
            supersede(db, old, got["run_id"], issue_code, now)
        return PublishResult(got["run_id"], "already_published", activate_run, got.get("counts", {}))
    attempt: Attempt = got
    stage = "preparar"

    def g() -> None:
        guard(db, attempt, extra=extra_guard)

    names = {"forecasts": "forecasts_sku"}
    try:
        g()
        stamp(attempt, prepared)
        stage = "hijos"
        insert_children(db, attempt, prepared, g, hook=lambda n: hook(names.get(n, n)))
        stage = "validacion"
        g()
        validate_fn(db, attempt.children_id)
        hook("validacion")
        stage = "completar"
        g()
        published_at = complete_run(db, attempt, {"counts": counts, "coverage": coverage}, now)
        hook("antes_puntero")
        if activate_run:
            activate_monotonic(db, attempt.run_id, published_at, now)
        for old in supersede_runs or []:
            supersede(db, old, attempt.run_id, issue_code, now)
    except LostOwnership:
        try:
            delete_own_children(db, attempt)       # solo su propio espacio
        except Exception:  # noqa: BLE001, S110
            pass
        raise
    except Exception as exc:
        done = db.runs.find_one({"run_id": attempt.run_id, "status": "completed", "children_ref": attempt.children_id},
                                {"_id": 1})
        if done is None:
            fail_attempt(db, attempt, stage, exc, now)
        raise
    return PublishResult(attempt.run_id, "published", activate_run, counts)


def publish(db, src: VerifiedSource, catalog: dict, catalog_fingerprint: str, signals: Signals, *,
            sources: list | None = None, now: datetime | None = None, activate_run: bool = True,
            supersede_runs: list[str] | None = None, issue_code: str = "R05_PRECISION_RECOMENDACIONES",
            extra_guard: Callable[[], None] | None = None,
            stage_hook: Callable[[str], None] | None = None) -> PublishResult:
    """Publica la corrida historica T07. `stage_hook(etapa)` solo se usa en pruebas para simular fallos.

    Antes de escribir se exige que fingerprint de entrenamiento, fuentes (si se pasan) y senales
    correspondan al fold aceptado del manifiesto; si cambian, falla sin tocar la base."""
    now = now or _utcnow()
    fold = src.manifest["folds_predictivos"][src.entry["fold"]]
    if catalog_fingerprint != fold["fingerprint"] or signals.training_fingerprint != fold["fingerprint"]:
        raise SourceVerificationError("catalogo/senales no corresponden al fingerprint del fold aceptado")
    if sources is not None:
        verify_training_match(src, catalog_fingerprint, sources)
    if signals.origin != src.entry["cutoff"]:
        raise SourceVerificationError("el origen de las senales no es el corte de la corrida")
    ensure_schema(db)
    run_id, key, fp = run_identity(src, catalog_fingerprint, signals.fingerprint)
    try:
        sku_docs, cat_docs, info = b.build_forecasts(src, catalog, "pendiente")
        recs = b.build_recommendations(src, catalog, "pendiente", signals)
        backtest = b.build_backtest(src, "pendiente", now)
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
    run_doc = b.build_run_doc(src, run_id, key, fp, _generated_at(src), coverage, counts, signals)
    validate_doc("runs", run_doc)
    validate_doc("backtests", backtest)
    prepared = {"forecasts": sku_docs + cat_docs, "recommendations": recs, "backtests": [backtest]}
    return publish_prepared(db, run_doc, prepared, lambda d, cid: validate_published(d, cid, counts), counts,
                            coverage, extra_guard=extra_guard, activate_run=activate_run,
                            supersede_runs=supersede_runs, issue_code=issue_code, now=now, stage_hook=stage_hook)
