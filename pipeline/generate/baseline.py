"""Generador de corridas `generated_baseline` con el metodo operativo promedio_28 (T10 §4).

Entrada de datos: SOLO historia aprobada <= origen (`load_training_data(db, origen, start=2026-03-01)`: fuentes
aprobadas, mascara de dias excluidos, catalogo al origen). Nunca se leen ventas posteriores al origen: los
valores futuros no son cero, son desconocidos (`observed = None`, `evaluable = False`).

  * pronostico por (sku, almacen) = media de las observaciones utiles de los ultimos 28 dias (señales exactas de
    `pipeline.publish.signals`), constante para h = 1..H (fechas naturales origen+1..origen+H);
  * categorias = suma de los SKU del catalogo al origen (SKU sin categoria -> DESCONOCIDA);
  * cohortes con la regla T05 al origen; control `cero` derivado;
  * `rf_categoria_distribuido` solo si el origen es el del fold G4 y la huella de entrenamiento coincide con la del
    manifiesto T07 verificado; en otro caso `None` y la corrida declara «comparador no disponible»;
  * recomendaciones hipoteticas: snapshot T07 `L7_S7_promedio_28` al cierre del origen (si el NPZ verificado
    existe); en otro caso se publican los pronosticos y la razon ARTEFACTO_SIMULACION_NO_DISPONIBLE.
No reentrena RF/XGBoost ni repite folds.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from fractions import Fraction

import numpy as np
import pandas as pd

from pipeline.data import daily_series as ds
from pipeline.data.sources import SourceApprovalError
from pipeline.data.training_access import TrainingData, load_training_data
from pipeline.forecast.baselines import forecast_block, primary_mask
from pipeline.publish import builders as b
from pipeline.publish.publisher import PublishResult, publish_prepared
from pipeline.publish.schema import (
    GENERATED_KIND,
    GENERATED_LABEL,
    PROVENANCE_OBS,
    SCHEMA_VERSION,
    SIM_LABEL,
    ensure_schema,
    validate_doc,
)
from pipeline.publish.signals import Signals, compute_signals
from pipeline.publish.source import (
    PROJECT_ROOT,
    SourceVerificationError,
    VerifiedSource,
    load_publish_config,
    load_snapshot,
    resolve_entry,
    verify_and_load,
    verify_training_match,
)

from .config import GenerationError, check_policy, cohort_rule, load_t10_config
from .validate import validate_generated

TRAIN_START = date(2026, 3, 1)
NO_SIM = "ARTEFACTO_SIMULACION_NO_DISPONIBLE"
GENERATOR_FILES = ("pipeline/generate/__init__.py", "pipeline/generate/baseline.py", "pipeline/generate/config.py",
                   "pipeline/generate/validate.py", "pipeline/publish/builders.py", "pipeline/publish/schema.py",
                   "pipeline/publish/signals.py")
Progress = Callable[[str, dict], None]


@dataclass
class Inputs:
    """Resultado de la fase 1 (lectura y calculo); nada se ha escrito todavia."""
    origin: date
    horizon: int
    method: str
    cfg: dict
    train: TrainingData
    signals: Signals
    entities: list                     # [(sku, almacen)] con señal util, ordenado
    cohort: dict                       # (sku, almacen) -> 'primaria' | 'historia_corta'
    sin_senal: int                     # pares conocidos sin dia util en la ventana (sin pronostico, no cero)
    src: VerifiedSource | None
    rf: dict | None                    # (entidad, fecha) -> pred rf, o None
    rf_note: str
    snapshot: dict | None
    snapshot_ref: dict
    identity: dict = field(default_factory=dict)


def generator_code_info() -> dict:
    """Hash del codigo del generador (normalizado a LF) y commit actual (best-effort; no entra en la identidad)."""
    h = hashlib.sha256()
    for rel in GENERATOR_FILES:
        h.update(rel.encode() + b"\0" + (PROJECT_ROOT / rel).read_bytes().replace(b"\r\n", b"\n") + b"\0")
    commit = "desconocido"
    try:
        out = subprocess.run(["git", "-C", str(PROJECT_ROOT), "rev-parse", "HEAD"], capture_output=True,
                             timeout=15, check=False)
        text = out.stdout.decode().strip()
        if out.returncode == 0 and len(text) == 40:
            commit = text
    except (OSError, subprocess.SubprocessError):
        pass
    return {"commit": commit, "codigo_sha256": h.hexdigest(), "files": list(GENERATOR_FILES)}


def _cohorts(train: TrainingData, rule: dict) -> tuple[dict, dict]:
    """Cohorte T05 al origen y media de control (baseline T05), por (sku, almacen)."""
    pairs = ds.pair_daily(train)
    cal = [d.isoformat() for d in train.calendar]
    wide = pairs.pivot(index=["sku", "almacen"], columns="fecha", values="cantidad_base").reindex(columns=cal)
    keys = list(wide.index)
    block = forecast_block(wide.to_numpy(dtype=float), horizon=7, window=28)
    prim = primary_mask(block, min_history=rule["historia_minima_dias"],
                        min_usable=rule["observaciones_utilizables_minimas_en_28"])
    cohort = {k: ("primaria" if p else "historia_corta") for k, p in zip(keys, prim, strict=True)}
    mean = {k: float(m) for k, m in zip(keys, block.forecasts["promedio_28"][:, 0], strict=True)}
    return cohort, mean


def _load_reference() -> tuple[VerifiedSource | None, str]:
    """Artefactos T07 verificados (checksum, codigo y referencia aprobada) o None con el motivo."""
    try:
        return verify_and_load(resolve_entry("t07", load_publish_config())), ""
    except (SourceVerificationError, OSError, KeyError, ValueError) as exc:
        return None, f"artefactos T07 no verificados ({type(exc).__name__})"


def collect_inputs(db, origin: date, horizon: int, method: str, *, cfg: dict | None = None,
                   progress: Progress | None = None) -> Inputs:
    """Fase 1: politica, entrenamiento <= origen, señales exactas, cohortes, comparador y snapshot (solo lectura)."""
    cfg = cfg or load_t10_config()
    note = progress or (lambda _s, _p: None)
    check_policy(origin, horizon, method, cfg)
    note("cargando historia aprobada", {})
    try:
        train = load_training_data(db, origin, start=TRAIN_START)
    except SourceApprovalError as exc:
        codes = ", ".join(sorted({str(i.get("codigo")) for i in exc.issues}))[:150]
        raise GenerationError("FUENTES_NO_APROBADAS",
                              f"Las fuentes aprobadas no cubren el origen pedido ({codes}).") from exc
    note("calculando señales exactas", {"filas_entrenamiento": len(train.sales)})
    signals = compute_signals(train, origin)
    cohort, ctrl_mean = _cohorts(train, cohort_rule())
    entities = sorted(signals.per_sku)
    if not entities:
        raise GenerationError("SIN_DATOS_UTILES", "No hay productos con ventas útiles en los últimos 28 días del origen.")
    for k in entities:                                  # control cruzado: señal exacta == media del baseline T05
        total, days = signals.per_sku[k]
        exact = float(Fraction(total) / days)
        if k not in cohort or abs(exact - ctrl_mean[k]) > 1e-9 * max(1.0, abs(exact)):
            raise GenerationError("SENAL_INCOHERENTE", "La señal exacta no coincide con el baseline de control.")
    sin_senal = len(cohort) - len(entities)

    note("verificando artefactos T07", {})
    src, why_src = _load_reference()
    rf, rf_note = None, ""
    if src is None:
        rf_note = f"comparador no disponible: {why_src}"
    elif origin != date.fromisoformat(src.entry["cutoff"]):
        rf_note = ("comparador no disponible: solo existe resultado del RF distribuido para el origen "
                   f"{date.fromisoformat(src.entry['cutoff']):%d/%m/%Y}")
    else:
        try:
            verify_training_match(src, train.fingerprint, list(train.sources.manifest))
            csv = src.forecasts
            if set(csv["entidad"]) != {f"{s}|{a}" for s, a in entities}:
                raise SourceVerificationError("universo de entidades distinto del fold G4")
            rf = {(r.entidad, r.fecha): float(r.pred_rf_distribuido) for r in csv.itertuples(index=False)}
        except SourceVerificationError as exc:
            rf_note = f"comparador no disponible: {str(exc)[:160]}"

    snapshot, snap_ref = None, {"disponible": False, "razon": NO_SIM}
    if src is not None:
        try:
            snapshot = load_snapshot(src, origin)
            npz = next(a for a in src.artifacts if a["name"] == "simulacion_series.npz")
            t07 = {(s["mes"], s["sha256"])
                   for s in src.manifest["folds_predictivos"][src.entry["fold"]]["fuentes"]}
            match = all((s["mes"], s["sha256"]) in t07 for s in train.sources.manifest)
            snap_ref = {"disponible": True, "scenario_id": f"T07_L7_S7_promedio_28_{origin.isoformat()}",
                        "escenario": src.entry["scenario_key"], "indice": snapshot["index"],
                        "npz_sha256": npz["sha256"], "universo_skus": len(snapshot["skus"]),
                        "fuentes_coinciden_con_t07": bool(match)}
        except (SourceVerificationError, OSError, KeyError, ValueError, StopIteration):
            snapshot, snap_ref = None, {"disponible": False, "razon": NO_SIM}
    rf_ref: dict = {"disponible": rf is not None}
    if rf is not None and src is not None:
        rf_ref["csv_sha256"] = next(a["sha256"] for a in src.artifacts if a["name"] == "predicciones_folds.csv.gz")
    gen = cfg["generador"]
    payload = {"tipo": GENERATED_KIND, "origen": origin.isoformat(), "horizonte": horizon, "metodo": method,
               "parametros": {"ventana_dias": gen["ventana_dias"], "cohorte": cohort_rule(),
                              "recomendacion": gen["recomendacion"]},
               "generador": gen["version"], "entrenamiento": train.fingerprint, "senales": signals.fingerprint,
               "snapshot": snap_ref, "comparador": rf_ref}
    fp = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    ident = {"payload": payload, "fingerprint": fp, "run_id": f"gen-{origin:%Y%m%d}-{fp[:12]}",
             "idempotency_key": f"gen-run:{origin.isoformat()}:{fp[:24]}"}
    return Inputs(origin, horizon, method, cfg, train, signals, entities, cohort, sin_senal, src, rf, rf_note,
                  snapshot, snap_ref, ident)


def _frame(inp: Inputs) -> pd.DataFrame:
    rows = []
    for sku, alm in inp.entities:
        total, days = inp.signals.per_sku[(sku, alm)]
        mean = float(Fraction(total) / days)
        ent = f"{sku}|{alm}"
        for h in range(1, inp.horizon + 1):
            d = (inp.origin + timedelta(days=h)).isoformat()
            rf = inp.rf[(ent, d)] if inp.rf is not None else np.nan
            rows.append((ent, inp.cohort[(sku, alm)], d, h, mean, rf))
    return pd.DataFrame(rows, columns=["entidad", "cohorte", "fecha", "h", "pred_promedio_28", "pred_rf_distribuido"])


@dataclass
class Generated:
    run_doc: dict
    prepared: dict
    counts: dict
    coverage: dict
    inputs: Inputs


def build(inp: Inputs, *, now: datetime | None = None) -> Generated:
    """Fase 2: documentos publicables (funciones puras sobre las entradas de la fase 1)."""
    now = (now or datetime.now(UTC)).replace(microsecond=0)
    ident, origin, horizon = inp.identity, inp.origin, inp.horizon
    sku_docs, cat_docs, info = b.build_forecasts(None, inp.train.catalog, "pendiente", frame=_frame(inp),
                                                 generated=True)
    recs: list = []
    if inp.snapshot is not None:
        entities = [(f"{s}|{a}", float(Fraction(inp.signals.per_sku[(s, a)][0]) / inp.signals.per_sku[(s, a)][1]))
                    for s, a in inp.entities]
        recs = b.build_recommendations(None, inp.train.catalog, "pendiente", inp.signals, entities=entities,
                                       snapshot=inp.snapshot, origin=origin,
                                       scenario_id=inp.snapshot_ref["scenario_id"])
    n_ok = sum(1 for d in recs if d["status"] == "ok")
    counts = {"forecasts_sku": len(sku_docs), "forecasts_categoria": len(cat_docs), "recommendations": len(recs),
              "recommendations_ok": n_ok, "recommendations_sin_snapshot": len(recs) - n_ok,
              "recommendations_con_pedido": sum(1 for d in recs if d["status"] == "ok" and d["order_qty"] > 0),
              "backtests": 0}
    prim = sum(1 for k in inp.entities if inp.cohort[k] == "primaria")
    coverage = {"skus_pronosticados": info["skus"], "categorias": info["categorias"],
                "skus_categoria_desconocida": info["skus_categoria_desconocida"],
                "skus_con_recomendacion": n_ok, "skus_sin_snapshot": len(recs) - n_ok,
                "skus_sin_senal_28d": inp.sin_senal, "cohorte_primaria": prim,
                "cohorte_historia_corta": len(inp.entities) - prim,
                "recomendaciones_disponibles": inp.snapshot is not None,
                "recomendaciones_razon_ausencia": None if inp.snapshot is not None else NO_SIM,
                "comparador_disponible": inp.rf is not None}
    code = generator_code_info()
    sources = [dict(s) for s in inp.train.sources.manifest]
    artifacts: list = []
    if inp.src is not None:
        used = ({"simulacion_series.npz"} if inp.snapshot is not None else set()) | (
            {"predicciones_folds.csv.gz"} if inp.rf is not None else set())
        artifacts = [dict(a) for a in inp.src.artifacts if a["name"] in used]
    notes = [
        "Ventas observadas: OBSERVED_EXCEL (Excel de la empresa, marzo a julio de 2026), solo hasta el origen.",
        (f"Pronóstico hacia adelante con promedio_28 desde el {origin:%d/%m/%Y}: no hay observaciones futuras; "
         "los valores futuros no son cero y la corrida no es evaluable."),
        ("Stock, tránsito, costos y pedidos: SYNTHETIC_NOT_REAL_INVENTORY. " + SIM_LABEL + "."
         if inp.snapshot is not None else
         "Sin recomendaciones numéricas: " + NO_SIM + " (no se supone stock cero)."),
        inp.rf_note or "El comparador RF distribuido proviene del resultado histórico G4 verificado (mismo origen "
                       "y misma huella de entrenamiento).",
        "Los faltantes de ventas por stock real son desconocidos; la demanda proxy es la venta observada."]
    if inp.snapshot_ref.get("disponible") and not inp.snapshot_ref.get("fuentes_coinciden_con_t07"):
        notes.append("Atención: las fuentes aprobadas difieren de las usadas por T07; el inventario simulado puede "
                     "no corresponder exactamente a estos datos.")
    gen = inp.cfg["generador"]
    manifest = {"entrenamiento_fingerprint": inp.train.fingerprint,
                "fuentes_sha256": [s["sha256"] for s in sources], "codigo": code,
                "config_t10": inp.cfg["version"],
                "senales": {"version": inp.signals.version, "fingerprint": inp.signals.fingerprint,
                            "ventana": [inp.signals.window_start, inp.signals.window_end],
                            "skus": len(inp.signals.per_sku)},
                "snapshot": inp.snapshot_ref, "comparador": ident["payload"]["comparador"]}
    start, end = origin + timedelta(days=1), origin + timedelta(days=horizon)
    run_doc = b.clean_json({
        "run_id": ident["run_id"], "status": "staging", "kind": GENERATED_KIND,
        "run_label": GENERATED_LABEL.format(origin=origin.strftime("%d/%m/%Y")),
        "idempotency_key": ident["idempotency_key"], "fingerprint": ident["fingerprint"],
        "cutoff": origin.isoformat(), "origin": origin.isoformat(),
        "target_start": start.isoformat(), "target_end": end.isoformat(),
        "horizon_days": horizon, "generated_at": now, "published_at": None,
        "evaluation_period": {"start": start.isoformat(), "end": end.isoformat(), "days": horizon,
                              "evaluable_days": 0,
                              "note": "pronóstico generado sin observaciones: no evaluable (los datos futuros no "
                                      "son cero)"},
        "method": {"chosen": b.CHOSEN, "comparator": "rf_categoria_distribuido",
                   "comparator_available": inp.rf is not None,
                   "comparator_note": inp.rf_note or None, "control": "cero",
                   "note": "Método operativo promedio_28. Control 'cero' = pronóstico 0 (derivado)."},
        "config": {"version": inp.cfg["version"], "generador": gen, "ventana_promedio_dias": gen["ventana_dias"],
                   "cohorte_primaria": cohort_rule(), "politica_desarrollo": inp.cfg["politica_desarrollo"]},
        "sources": sources, "sources_fingerprint": inp.train.fingerprint, "artifacts": artifacts,
        "code": {"commit": code["commit"], "codigo_sha256": code["codigo_sha256"]},
        "counts": counts, "coverage": coverage, "manifest": manifest,
        "publisher": {"version": "t10-gen", "generator_version": gen["version"],
                      "signals_version": inp.signals.version, "signals_fingerprint": inp.signals.fingerprint,
                      "signals_window": [inp.signals.window_start, inp.signals.window_end],
                      "signals_skus": len(inp.signals.per_sku)},
        "provenance": PROVENANCE_OBS, "provenance_notes": notes, "error": None, "schema_version": SCHEMA_VERSION})
    validate_doc("runs", run_doc)
    return Generated(run_doc, {"forecasts": sku_docs + cat_docs, "recommendations": recs, "backtests": []},
                     counts, coverage, inp)


def _result(outcome: str, run_id: str, status: str, counts: dict, coverage: dict, inp: Inputs) -> dict:
    return {"outcome": outcome, "run_id": run_id, "publish_status": status, "origin": inp.origin.isoformat(),
            "horizon_days": inp.horizon, "method": inp.method, "counts": counts, "coverage": coverage,
            "comparator_available": inp.rf is not None, "comparator_note": inp.rf_note or None,
            "recommendations_available": inp.snapshot is not None,
            "recommendations_reason": None if inp.snapshot is not None else NO_SIM}


def generate_and_publish(db, origin: date, horizon: int, method: str, *, cfg: dict | None = None,
                         extra_guard: Callable[[], None] | None = None, progress: Progress | None = None,
                         stage_hook: Callable[[str], None] | None = None, activate_run: bool = False,
                         now: datetime | None = None) -> dict:
    """Genera y publica (o reconoce) la corrida. `activate_run=False` por defecto: la corrida generada no
    desplaza a la historica como corrida activa. Devuelve el resultado publico (sin rutas)."""
    note = progress or (lambda _s, _p: None)
    inp = collect_inputs(db, origin, horizon, method, cfg=cfg, progress=note)
    ensure_schema(db)
    done = db.runs.find_one({"idempotency_key": inp.identity["idempotency_key"],
                             "status": {"$in": ["completed", "superseded"]}})
    if done is not None:
        return _result("sin_cambios", done["run_id"], "already_published", done.get("counts", {}),
                       done.get("coverage", {}), inp)
    note("construyendo documentos", {"skus": len(inp.entities)})
    gen = build(inp, now=now)
    if extra_guard:
        extra_guard()
    note("publicando", gen.counts)

    def hook(stage: str) -> None:
        note(f"publicando: {stage}", gen.counts)
        if stage_hook:
            stage_hook(stage)

    res: PublishResult = publish_prepared(
        db, gen.run_doc, gen.prepared,
        lambda d, cid: validate_generated(d, cid, gen.counts, origin=origin, horizon=horizon,
                                          comparator=inp.rf is not None, recommendations=inp.snapshot is not None),
        gen.counts, gen.coverage, extra_guard=extra_guard, activate_run=activate_run, supersede_runs=[],
        now=now, stage_hook=hook)
    outcome = "sin_cambios" if res.status == "already_published" else "generada"
    return _result(outcome, res.run_id, res.status, res.counts, gen.coverage, inp)
