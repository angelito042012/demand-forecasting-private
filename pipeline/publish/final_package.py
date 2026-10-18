"""T11A: publicacion del paquete final T12 (corrida `final_evaluation`) con el protocolo T10R.

Lee SOLO artefactos ya validados de `artifacts/private/final/` (siete fases completas, auditoria aprobada, hashes del
sello y de cada artefacto) y construye los documentos del contrato T11 §2 SIN ejecutar modelos, SIN consultar agosto en
MongoDB y SIN reentrenar: el `.joblib` solo se hashea (bytes); los NPZ se cargan con `allow_pickle=False`.

Regla de datos: nada se inventa. Un dia sin ningun registro del archivo queda `evaluable=false` y `observed=None`
(no es una venta cero). Los SKU nuevos (primera venta posterior al 31/07) no son filas: se resumen en `coverage`.
Inventario simulado con supuestos; no corresponde al inventario real de la empresa.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

import bson
import numpy as np
import pandas as pd

from .builders import CHOSEN, build_forecasts, clean_json
from .protocol import PublishValidationError
from .publisher import publish_prepared
from .schema import (
    FINAL_KIND,
    PROVENANCE_OBS,
    PROVENANCE_SIM,
    SCHEMA_VERSION,
    SIM_LABEL,
    ensure_schema,
    validate_doc,
)
from .source import PROJECT_ROOT

FINAL_DIR = PROJECT_ROOT / "artifacts" / "private" / "final"
SEAL_DOC = PROJECT_ROOT / "docs" / "T12_SELLO.json"
PHASES = ("verificacion", "preparacion", "lectura_agosto", "evaluacion_predictiva", "simulacion", "auditoria", "reporte")
RUN_LABEL = "Evaluación final de agosto (origen 31/07/2026, bloque 01–21/08/2026)"
ORIGIN, BLOCK_START, BLOCK_END = "2026-07-31", "2026-08-01", "2026-08-21"
HORIZON = 21
FORBIDDEN_DBS = frozenset({"demand_forecasting_v2", "demand_forecasting_dev", "admin", "local", "config"})
SEAL_COMMIT_SHORT = "86325a7"
_SHA = re.compile(r"^[0-9a-f]{64}$")
INDEX_FACTOR = 0.10    # indices/datos de `forecasts` medidos en v2 (26,1 MB / 267 MB); solo estimacion previa
WARNINGS = [
    "WAPE no es exactitud: 0,78 = error absoluto equivalente al 78 % del volumen observado.",
    "Categoría = suma de unidades base heterogéneas.",
    "Un solo bloque (origen 31/07, 01–21/08): no permite declarar ganador ni generalizar.",
    SIM_LABEL + ".",
]
DISCLAIMER = (SIM_LABEL + ". Evaluación final sobre un único bloque ya observado; no demuestra impacto en la empresa "
              "ni autoriza compras. Las revisiones de la simulación secuencial no son predicciones fijas.")


class FinalPackageError(RuntimeError):
    """Paquete T12 incompleto, alterado o incoherente: no se publica."""


# ------------------------------------------------------------------ utilidades (copias exactas de pipeline.final.*)
def sha_bytes(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical(obj) -> bytes:
    """Igual que `pipeline.final.runner.canonical` (una prueba lo compara)."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")


def logical_signature(arrays: dict) -> str:
    """Igual que `pipeline.final.core.logical_signature` (una prueba lo compara). Se duplica para no importar
    scikit-learn/t07 en el publicador."""
    h = hashlib.sha256()
    for name in sorted(arrays):
        a = np.ascontiguousarray(np.asarray(arrays[name]))
        h.update(f"{name}|{a.dtype.str}|{a.shape}\n".encode())
        h.update(a.tobytes() if a.dtype.kind != "O" else "\n".join(map(str, a.ravel())).encode())
    return h.hexdigest()


def _load_npz(path: Path) -> dict:
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


def _json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise FinalPackageError(f"{path.name} ausente o ilegible") from exc


def _need(cond: bool, msg: str) -> None:
    if not cond:
        raise FinalPackageError(msg)


# ------------------------------------------------------------------ verificacion
def verify_final_package(root: Path | None = None, *, seal_doc: Path | None = SEAL_DOC) -> dict:
    """Verifica el paquete y devuelve los objetos cargados. Lanza FinalPackageError ante cualquier incoherencia."""
    root = Path(root or FINAL_DIR)
    state = _json(root / "estado.json")
    _need(state.get("completa") is True, "estado.json: la ejecucion no esta completa (completa != true)")
    fases = state.get("fases", {})
    for p in PHASES:
        _need(fases.get(p, {}).get("estado") == "completa" and "error" not in fases.get(p, {}),
              f"estado.json: la fase '{p}' no esta completa")
    aud = _json(root / "auditoria.json")
    _need(aud.get("ok") is True, "auditoria.json: la auditoria no aprobo")
    _need(sha_bytes(root / "auditoria.json") == fases["auditoria"].get("auditoria_sha256"),
          "auditoria.json no coincide con el hash registrado en estado.json")

    prep = root / "preparacion"
    man = _json(prep / "manifiesto_preparacion.json")
    base = {k: v for k, v in man.items() if k not in ("creado_lima", "sello_sha256")}
    _need(hashlib.sha256(canonical(base)).hexdigest() == man.get("sello_sha256"), "manifiesto de preparacion alterado (sello)")
    _need(man.get("agosto_consultado") is False and man.get("reference_v1_consultado") is False,
          "el manifiesto no declara agosto/reference_v1 sin consultar")
    arrays = {}
    for name, rec in man["archivos"].items():
        p = prep / name
        _need(p.is_file() and sha_bytes(p) == rec["bytes_sha256"], f"{name}: hash de bytes distinto del sellado")
        if name.endswith(".npz"):
            arrays[name] = _load_npz(p)
            _need(logical_signature(arrays[name]) == rec["logical_sha256"], f"{name}: contenido logico distinto del sellado")
    if seal_doc is not None and Path(seal_doc).is_file():
        _need(_json(Path(seal_doc)).get("sello_sha256") == man["sello_sha256"], "docs/T12_SELLO.json no coincide con el manifiesto")

    ev, sim = fases["evaluacion_predictiva"], fases["simulacion"]
    checks = {"predictivo.json": ev.get("predictivo_sha256"), "simulacion.json": sim.get("simulacion_sha256"),
              "reales_bloque.npz": (ev.get("reales") or {}).get("bytes_sha256"),
              "simulacion_series.npz": (sim.get("series") or {}).get("bytes_sha256"),
              "ventas_agosto_min.csv.gz": fases["lectura_agosto"].get("bytes_sha256")}
    for name, want in checks.items():
        _need(bool(want) and _SHA.match(str(want)) is not None, f"estado.json no registra el hash de {name}")
        _need((root / name).is_file() and sha_bytes(root / name) == want, f"{name}: hash distinto del registrado en estado.json")
    reales = _load_npz(root / "reales_bloque.npz")
    _need(logical_signature(reales) == ev["reales"]["logical_sha256"], "reales_bloque.npz: contenido logico distinto del registrado")
    for corr in state.get("correcciones", []):
        for rel, want in (corr.get("hashes_originales_conservados") or {}).items():
            _need((root / rel).is_file() and sha_bytes(root / rel) == want, f"{rel}: difiere del hash original conservado")
    pred, simj = _json(root / "predictivo.json"), _json(root / "simulacion.json")
    _need(len(simj.get("resultados", {})) == 27, "simulacion.json: no son las 27 combinaciones")
    sealed = arrays["predicciones_fijas.npz"]
    return {"root": root, "state": state, "audit": aud, "manifest": man, "sealed": sealed, "reales": reales,
            "predictive": pred, "simulation": simj}


# ------------------------------------------------------------------ construccion de documentos
def build_frame(pkg: dict) -> tuple[pd.DataFrame, dict]:
    """DataFrame con las columnas del CSV T07 (entidad, fecha, h, cohorte, real, evaluable, pred_*) y el catalogo
    sku->categoria AL 31/07 (sellado). Solo SKU conocidos; sin NaN (no se fabrican predicciones ni ceros)."""
    z, r = pkg["sealed"], pkg["reales"]
    keys = z["sku_keys"].astype(str)
    n = len(keys)
    days = [str(d) for d in r["dias"]]
    _need(len(set(keys.tolist())) == n, "sku_keys duplicadas")
    _need(days[0] == BLOCK_START and days[-1] == BLOCK_END and len(days) == HORIZON, "el bloque no es 2026-08-01..2026-08-21")
    p28, rf, act = z["pred_sku_promedio_28"], z["pred_sku_rf_distribuido"], r["act"]
    _need(p28.shape == rf.shape == act.shape == (n, HORIZON), "dimensiones de predicciones/reales incoherentes")
    known = z["sku_conocido"].astype(bool)
    _need(np.isfinite(p28[known]).all() and np.isfinite(rf[known]).all() and (p28[known] >= 0).all() and (rf[known] >= 0).all(),
          "predicciones no finitas o negativas en SKU conocidos")
    _need((act >= 0).all() and np.isfinite(act).all() and (act == np.floor(act)).all(), "reales negativos, no finitos o no enteros")
    ev = r["eval_days"].astype(bool)
    idx = np.flatnonzero(known)
    ent = np.repeat(keys[idx], HORIZON)
    frame = pd.DataFrame({
        "entidad": ent, "fecha": np.tile(days, len(idx)), "h": np.tile(np.arange(1, HORIZON + 1), len(idx)),
        "cohorte": np.repeat(np.where(z["sku_primaria"].astype(bool)[idx], "primaria", "historia_corta"), HORIZON),
        "real": act[idx].ravel().astype(int), "evaluable": np.tile(ev, len(idx)),
        "pred_promedio_28": p28[idx].ravel(), "pred_rf_distribuido": rf[idx].ravel()})
    catalog: dict = {}
    for k, c in zip(keys[idx], z["sku_cats"].astype(str)[idx], strict=True):
        sku = k.split("|")[0]
        _need(catalog.setdefault(sku, c) == c, f"categoria inconsistente para el SKU {sku}")
    return frame, catalog


def build_forecast_docs(pkg: dict) -> tuple[list, list, dict]:
    frame, catalog = build_frame(pkg)
    sku_docs, cat_docs, info = build_forecasts(None, catalog, "pendiente", frame=frame)
    for d in sku_docs + cat_docs:
        d["run_kind"] = FINAL_KIND
        if not d["evaluable"]:
            d["observed"] = None          # dia sin registros: ausente, NO cero
    # categoria del baseline operativo = suma de SKU: contraste con el arreglo sellado
    z = pkg["sealed"]
    names = [str(c) for c in z["cat_names"]]
    sealed_cat = {(names[i], d): float(z["pred_cat_promedio_28_suma_sku"][i, h])
                  for i in range(len(names)) for h, d in enumerate(str(x) for x in pkg["reales"]["dias"])}
    for c in cat_docs:
        want = sealed_cat.get((c["entity_id"], c["target_date"]))
        _need(want is not None and abs(want - c["pred"]["promedio_28"]) <= 1e-9 * max(1.0, abs(want)),
              f"categoria {c['entity_id']}: promedio_28 distinto de la suma sellada de SKU")
    return sku_docs, cat_docs, info


def _rec(recs, cohorte, metodo, vista):
    return next((r for r in recs if (r["cohorte"], r["metodo"], r["vista"]) == (cohorte, metodo, vista)), None)


def primary_selection(pred: dict) -> dict:
    g = lambda m, k="WAPE": (_rec(pred["sku"], "primaria", m, "acum14") or {}).get(k)
    wr, wc, w0 = g("promedio_28"), g("rf_distribuido"), g("cero")
    _need(wr is not None and wc is not None and w0 is not None, "predictivo.json: falta el criterio primario (WAPE H14 primaria)")
    obs_p, obs_r = g("promedio_28", "unidades_observadas"), g("rf_distribuido", "unidades_observadas")
    return {"WAPE_promedio_28": wr, "WAPE_rf_distribuido": wc, "WAPE_cero": w0,
            "mejora_relativa": (wr - wc) / wr if wr else None,
            "sesgo_relativo": {"promedio_28": (g("promedio_28", "sesgo_acumulado") / obs_p) if obs_p else None,
                               "rf_distribuido": (g("rf_distribuido", "sesgo_acumulado") / obs_r) if obs_r else None},
            "n": g("promedio_28", "n")}


def build_backtest_doc(pkg: dict, created: datetime) -> dict:
    pred, sj = pkg["predictive"], pkg["simulation"]
    rows, diffs = [], []
    for key, val in sj["resultados"].items():
        scen, policy = key.split("|")
        L, S = (int(x[1:]) for x in scen.split("_"))
        rows.append({"scenario_id": f"T12_L{L}_S{S}_R7_2026-08-01_2026-08-31", "L": L, "S": S, "R": 7, "policy": policy,
                     "total": val["total"], "primaria": val["primaria"], "historia_corta": val["historia_corta"],
                     "identidad_valor": val["identidad_valor"], "conservacion": val["conservacion"],
                     "provenance": PROVENANCE_SIM, "unit": "unidad base", "currency": "PEN"})
    for key, val in sj["diferencias"].items():
        scen, policy, vs, cohort = key.split("|")
        diffs.append({"scenario": scen, "policy": policy, "vs": vs.removeprefix("vs_"), "cohorte": cohort, "metrics": val})
    rep = sj.get("reporte", {})
    sim_report = {k: rep.get(k) for k in ("universo_skus", "primaria_inicial", "historia_corta_inicial", "excluidos_nuevos_skus",
                                          "excluidos_nuevos_unidades_proxy", "fallback_rf_a_promedio_filas", "dias",
                                          "dias_evaluables", "dias_sin_demanda_conocida", "segundos")}
    sim_report["revisiones"] = [{"dia": r.get("dia"), "hash_pronostico": r.get("hash_pronostico"),
                                 "conservacion_cat_a_sku": r.get("conservacion_cat_a_sku")} for r in rep.get("revisiones", [])]
    sel = primary_selection(pred)
    doc = {
        "backtest_id": "bt-pendiente", "run_id": "pendiente", "kind": FINAL_KIND,
        "label": "Evaluación final T12 (un bloque 01–21/08 desde el origen 31/07 y simulación secuencial 01–31/08)",
        "folds": ["FINAL"], "created": created, "scenario_id": "T12_simulacion_2026-08-01_2026-08-31",
        "provenance": PROVENANCE_SIM,
        "provenance_observed": PROVENANCE_OBS + " (predicciones fijas selladas y ventas observadas); la simulación es "
        + PROVENANCE_SIM,
        "predictive": {"sku": pred["sku"], "categoria": pred["categoria"], "nuevos_sku": pred["nuevos_sku"],
                       "dias_evaluables": pred["dias_evaluables"], "dias_no_evaluables": pred["dias_no_evaluables"],
                       "universo": pred["universo"],
                       "nota": "Un solo bloque; WAPE acumulado H=14 SKU primaria universo común es el criterio primario."},
        "selection": {"chosen": CHOSEN, "rf_declared_winner": False, "comparator": "rf_categoria_distribuido", "control": "cero",
                      "primary_criterion": "WAPE acumulado H=14, SKU-almacén, cohorte primaria, universo común",
                      "primary": sel,
                      "note": "Con un solo bloque no se aplica la regla de tres folds: el RF no puede declararse ganador; "
                              "se informan mejora relativa, sesgo y cobertura. El método operativo no cambia."},
        "coverage": pred["cobertura"], "simulation": rows, "simulation_differences": diffs, "simulation_report": sim_report,
        "assumptions": {"L": [3, 7, 14], "S": [0, 7, 14], "R": 7, "factor_costo_sobre_mediana_precio": 0.65,
                        "holding_anual": 0.20, "dias_anio": 365, "holding_diario": 0.20 / 365,
                        "escenario_principal": {"L": 7, "S": 7}, "moneda": "PEN", "unidad": "unidad base",
                        "demanda": "proxy: venta positiva observada, posiblemente censurada por stock real desconocido",
                        "limites": ["un solo bloque de evaluación", "costo y holding supuestos",
                                    "sin MOQ, proveedores ni plazos reales", "un almacén",
                                    "universo fijo al 31/07; los SKU nuevos no entran a la simulación",
                                    "las revisiones de la simulación no son predicciones fijas", "no autoriza compras"]},
        "disclaimer": DISCLAIMER, "run_label": RUN_LABEL, "schema_version": SCHEMA_VERSION}
    return clean_json(doc)


def _artifact_refs(root: Path) -> list:
    names = ["preparacion/predicciones_fijas.npz", "preparacion/inicializacion_sim.npz", "preparacion/rf_categoria_T12.joblib",
             "preparacion/manifiesto_preparacion.json", "reales_bloque.npz", "ventas_agosto_min.csv.gz", "predictivo.json",
             "simulacion.json", "simulacion_series.npz", "auditoria.json", "verificacion.json", "estado.json"]
    out = []
    for n in names:
        p = root / n
        if p.is_file():
            out.append({"name": n, "sha256": sha_bytes(p), "size_bytes": p.stat().st_size})
    return out


def _utc(iso: str) -> datetime:
    return datetime.fromisoformat(iso).astimezone(UTC).replace(microsecond=0)


def build_run_doc(pkg: dict, counts: dict, coverage: dict, *, see_run: str | None, august_excel_sha: str | None,
                  seal_commit: str = SEAL_COMMIT_SHORT) -> dict:
    man, state, root = pkg["manifest"], pkg["state"], pkg["root"]
    seal = man["sello_sha256"]
    ag = state["fases"]["lectura_agosto"]
    sources = [dict(s) for s in man["fuentes"]]
    if august_excel_sha:
        sources.append({"mes": "2026-08", "archivo": "agosto.xlsx", "sha256": august_excel_sha})
    else:
        sources.append({"mes": "2026-08", "archivo": "ventas_agosto_min.csv.gz", "sha256": ag["bytes_sha256"],
                        "nota": "extracto mínimo derivado del Excel de agosto; hash del Excel no disponible en esta base"})
    corr = [{"motivo": c.get("motivo"), "t": c.get("t"), "git_commit_base": c.get("git_commit_base"),
             "fases_registradas_a_posteriori": c.get("fases_registradas_a_posteriori"), "nota": c.get("nota")}
            for c in state.get("correcciones", [])]
    r11 = next((c["git_commit_base"] for c in state.get("correcciones", []) if c.get("git_commit_base")), None)
    run_id = f"final-20260731-{seal[:12]}"
    return clean_json({
        "run_id": run_id, "status": "staging", "kind": FINAL_KIND, "run_label": RUN_LABEL,
        "idempotency_key": f"final-eval:{seal}", "fingerprint": man["fingerprint_entrenamiento"],
        "cutoff": ORIGIN, "origin": ORIGIN, "target_start": BLOCK_START, "target_end": BLOCK_END, "horizon_days": HORIZON,
        "generated_at": _utc(state["fases"]["reporte"]["fin"]), "published_at": None,
        "evaluation_period": {"start": BLOCK_START, "end": BLOCK_END, "single_block": True, "days": HORIZON,
                              "evaluable_days": pkg["predictive"]["dias_evaluables"],
                              "excluded_days": pkg["predictive"]["dias_no_evaluables"]},
        "method": {"chosen": CHOSEN, "comparator": "rf_categoria_distribuido", "control": "cero", "rf_declared_winner": False,
                   "category_baseline": "suma de pronósticos SKU"},
        "sources": sources, "sources_fingerprint": man["fingerprint_entrenamiento"],
        "artifacts": _artifact_refs(root),
        "code": {"commit": man["git_commit"], "commit_codigo": man["git_commit"], "commit_sello": seal_commit,
                 "commit_reconciliacion_r11": r11},
        "final_package": {"seal_sha256": seal, "frozen_selection_sha256": man["seleccion_congelada_sha256"],
                          "phases": {p: state["fases"][p]["estado"] for p in PHASES},
                          "corrections": corr, "audit_ok": True},
        "counts": counts, "coverage": coverage,
        "recommendations_unavailable_reason": "RECOMENDACION_NO_VALIDADA_PARA_ESTE_ORIGEN", "see_run": see_run,
        "warnings": WARNINGS,
        "provenance_notes": [
            "Predicciones fijas selladas con datos hasta 31/07/2026, antes de leer agosto; ventas observadas: OBSERVED_EXCEL.",
            "Stock, tránsito, costos y pedidos de la simulación: SYNTHETIC_NOT_REAL_INVENTORY. " + SIM_LABEL + ".",
            "Corrida de evaluación final: no crea pedidos; no activa el puntero ni reemplaza a la histórica.",
            "Los faltantes de ventas por stock real son desconocidos; la demanda proxy es la venta observada."],
        "error": None, "schema_version": SCHEMA_VERSION})


def _coverage(pkg: dict, info: dict) -> dict:
    pred = pkg["predictive"]
    return {"skus_pronosticados": info["skus"], "categorias": info["categorias"],
            "universo": pred["universo"], "universo_comun": pred["cobertura"],
            "skus_nuevos": pred["nuevos_sku"], "dias_evaluables": pred["dias_evaluables"],
            "dias_no_evaluables": pred["dias_no_evaluables"],
            "nota": "Un solo bloque; los SKU nuevos (primera venta posterior al 31/07) se resumen aquí y no son filas."}


def estimate_capacity(prepared: dict[str, list]) -> dict:
    """Bytes BSON por coleccion ANTES de insertar (+ estimacion de indices con el factor medido en v2)."""
    per = {n: sum(len(bson.encode(d)) for d in docs) for n, docs in prepared.items()}
    data = sum(per.values())
    return {"docs": {n: len(d) for n, d in prepared.items()}, "bson_bytes": per, "bson_total_bytes": data,
            "bson_total_mb": round(data / 1048576, 2), "indices_estimados_mb": round(data * INDEX_FACTOR / 1048576, 2),
            "nota": f"indices estimados con factor {INDEX_FACTOR} (medido en v2); la medicion real se hace tras restaurar"}


# ------------------------------------------------------------------ validacion en la base
def validate_final(db, children_id: str, expected: dict) -> dict:
    f = db.forecasts
    got = {"forecasts_sku": f.count_documents({"run_id": children_id, "level": "sku"}),
           "forecasts_categoria": f.count_documents({"run_id": children_id, "level": "categoria"}),
           "recommendations": db.recommendations.count_documents({"run_id": children_id}),
           "backtests": db.backtests.count_documents({"run_id": children_id})}
    for k, v in got.items():
        if expected[k] != v:
            raise PublishValidationError(f"conteo {k}: esperado {expected[k]}, hallado {v}")
    if f.count_documents({"run_id": children_id, "$or": [{"target_date": {"$lt": BLOCK_START}}, {"target_date": {"$gt": BLOCK_END}}]}):
        raise PublishValidationError("fechas objetivo fuera de 2026-08-01..2026-08-21")
    if f.count_documents({"run_id": children_id, "evaluable": False, "observed": {"$ne": None}}):
        raise PublishValidationError("observed fabricado en un dia no evaluable")
    sums = {(g["_id"]["c"], g["_id"]["d"]): g for g in f.aggregate([
        {"$match": {"run_id": children_id, "level": "sku"}},
        {"$group": {"_id": {"c": "$categoria", "d": "$target_date"}, "p28": {"$sum": "$pred.promedio_28"},
                    "prf": {"$sum": "$pred.rf_categoria_distribuido"}, "obs": {"$sum": "$observed"},
                    "nobs": {"$sum": {"$cond": [{"$eq": ["$observed", None]}, 0, 1]}}}}], allowDiskUse=True)}
    seen = 0
    for c in f.find({"run_id": children_id, "level": "categoria"}):
        s = sums.get((c["entity_id"], c["target_date"]))
        close = lambda a, b: abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b))
        if s is None or not (close(s["p28"], c["pred"]["promedio_28"]) and close(s["prf"], c["pred"]["rf_categoria_distribuido"])):
            raise PublishValidationError("categoria no es la suma de sus SKU")
        if c["evaluable"] and s["obs"] != c["observed"]:
            raise PublishValidationError("observado de categoria distinto de la suma de SKU")
        if not c["evaluable"] and (c["observed"] is not None or s["nobs"] != 0):
            raise PublishValidationError("dia no evaluable con observado")
        seen += 1
    if seen != len(sums):
        raise PublishValidationError("categorias incompletas")
    return got


def _active_run(db) -> str | None:
    p = db.run_pointer.find_one({"_id": "active"}, {"run_id": 1})
    return (p or {}).get("run_id")


def prepare_package(root: Path | None = None, *, see_run: str | None = None, august_excel_sha: str | None = None,
                    seal_doc: Path | None = SEAL_DOC, seal_commit: str = SEAL_COMMIT_SHORT, now: datetime | None = None):
    """Verifica y construye (sin tocar MongoDB). Devuelve (run_doc, prepared, counts, coverage, capacidad)."""
    pkg = verify_final_package(root, seal_doc=seal_doc)
    sku_docs, cat_docs, info = build_forecast_docs(pkg)
    counts = {"forecasts_sku": len(sku_docs), "forecasts_categoria": len(cat_docs), "recommendations": 0, "backtests": 1}
    coverage = _coverage(pkg, info)
    bt = build_backtest_doc(pkg, (now or datetime.now(UTC)).replace(microsecond=0))
    run_doc = build_run_doc(pkg, counts, coverage, see_run=see_run, august_excel_sha=august_excel_sha, seal_commit=seal_commit)
    validate_doc("runs", run_doc)
    bt["run_id"] = run_doc["run_id"]
    bt["backtest_id"] = f"bt-{run_doc['run_id']}"
    validate_doc("backtests", bt)
    for d in (sku_docs[:1] + sku_docs[-1:] + cat_docs[:1] + cat_docs[-1:]):
        validate_doc("forecasts", d)
    prepared = {"forecasts": sku_docs + cat_docs, "recommendations": [], "backtests": [bt]}
    return run_doc, prepared, counts, coverage, estimate_capacity(prepared)


def publish_final(db, root: Path | None = None, *, see_run: str | None = None, dry_run: bool = False,
                  seal_doc: Path | None = SEAL_DOC, seal_commit: str = SEAL_COMMIT_SHORT,
                  now: datetime | None = None, stage_hook=None) -> dict:
    """Publica la corrida final en `db` (nunca v2/dev). Idempotente: la segunda ejecucion devuelve `sin_cambios`."""
    if db.name in FORBIDDEN_DBS:
        raise FinalPackageError(f"la base '{db.name}' no admite escritura de T11A")
    see = see_run or _active_run(db)
    ex = db.imports.find_one({"mes": "2026-08", "estado": "completed"}, {"sha256": 1})   # solo metadatos del Excel
    run_doc, prepared, counts, coverage, cap = prepare_package(
        root, see_run=see, august_excel_sha=(ex or {}).get("sha256"), seal_doc=seal_doc, seal_commit=seal_commit, now=now)
    out = {"run_id": run_doc["run_id"], "idempotency_key": run_doc["idempotency_key"], "counts": counts, "capacidad": cap,
           "see_run": see, "sello": run_doc["final_package"]["seal_sha256"]}
    if dry_run:
        return {**out, "estado": "dry_run"}
    ensure_schema(db)
    res = publish_prepared(db, run_doc, prepared, lambda d, cid: validate_final(d, cid, counts), counts, coverage,
                           activate_run=False, now=now, stage_hook=stage_hook)
    if res.status == "already_published":
        run = db.runs.find_one({"run_id": res.run_id}, {"children_ref": 1, "status": 1})
        validate_final(db, run.get("children_ref") or res.run_id, counts)    # la copia existente sigue entera
        return {**out, "estado": "sin_cambios"}
    return {**out, "estado": "publicado"}
