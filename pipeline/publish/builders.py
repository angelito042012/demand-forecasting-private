"""Construccion de documentos publicables a partir de artefactos verificados (T08 §4-§5).

Funciones puras (sin I/O): reciben VerifiedSource y el catalogo <= corte.
"""
from __future__ import annotations

import math

import numpy as np

from .schema import (
    PROVENANCE_OBS,
    PROVENANCE_SIM,
    RUN_LABEL,
    SCHEMA_VERSION,
    SIM_LABEL,
)
from .source import VerifiedSource

UNKNOWN = "DESCONOCIDA"
CHOSEN = "promedio_28"
LEAD, REVIEW, SAFETY_DAYS, HORIZON_REC = 7, 7, 7, 14
SIN_SNAPSHOT_REASON = ("SIN_INVENTARIO_SIMULADO_AL_10_07: producto conocido despues del 31/05; "
                       "no se supone stock cero")
NUM_FIELDS = ("on_hand", "in_transit", "position", "mean_28", "forecast_14d", "safety", "target",
              "order_qty", "unit_cost_assumed", "order_value_assumed")


def ceil_stable(x: float, decimals: int = 9) -> int:
    """Techo tras redondear a 9 decimales (idem pipeline.sim.engine.ceil_stable)."""
    return int(np.ceil(np.round(np.asarray(x, dtype=float), decimals)))


def clean_json(obj):
    """Sustituye NaN/inf por None (JSON valido) y normaliza tipos numpy."""
    if isinstance(obj, dict):
        return {str(k): clean_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean_json(v) for v in obj]
    if isinstance(obj, (np.floating, float)):
        f = float(obj)
        return f if math.isfinite(f) else None
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    return obj


def _fc_base(run_id: str) -> dict:
    return {"run_id": run_id, "chosen_method": CHOSEN, "provenance": PROVENANCE_OBS,
            "schema_version": SCHEMA_VERSION}


def build_forecasts(src: VerifiedSource, catalog: dict, run_id: str) -> tuple[list, list, dict]:
    """(docs_sku, docs_categoria, info). Categorias = suma de los SKU del catalogo; SKU sin
    categoria -> DESCONOCIDA (se informa, no se mezcla con otra categoria)."""
    df = src.forecasts.copy()
    parts = df["entidad"].str.split("|", expand=True)
    df["sku"], df["almacen"] = parts[0], parts[1]
    df["categoria"] = df["sku"].map(lambda s: catalog.get(s) or UNKNOWN)
    base = _fc_base(run_id)
    sku_docs = []
    for r in df.itertuples(index=False):
        sku_docs.append({
            **base, "level": "sku", "entity_id": r.entidad, "sku": r.sku, "almacen": r.almacen,
            "categoria": r.categoria, "cohorte": r.cohorte, "target_date": r.fecha, "h": int(r.h),
            "pred": {"promedio_28": float(r.pred_promedio_28),
                     "rf_categoria_distribuido": float(r.pred_rf_distribuido), "cero": 0.0},
            "observed": int(r.real), "evaluable": bool(r.evaluable)})
    g = df.groupby(["categoria", "fecha"], sort=True).agg(
        p28=("pred_promedio_28", "sum"), prf=("pred_rf_distribuido", "sum"), real=("real", "sum"),
        h=("h", "first"), ev=("evaluable", "all"), n=("sku", "nunique")).reset_index()
    cat_docs = [{
        **base, "level": "categoria", "entity_id": r.categoria, "sku": None, "almacen": None,
        "categoria": r.categoria, "cohorte": None, "target_date": r.fecha, "h": int(r.h),
        "pred": {"promedio_28": float(r.p28), "rf_categoria_distribuido": float(r.prf), "cero": 0.0},
        "observed": int(r.real), "evaluable": bool(r.ev)} for r in g.itertuples(index=False)]
    unknown = sorted(df.loc[df["categoria"] == UNKNOWN, "sku"].unique().tolist())
    info = {"skus": int(df["sku"].nunique()), "categorias": int(g["categoria"].nunique()),
            "skus_categoria_desconocida": len(unknown)}
    return sku_docs, cat_docs, info


def recompute_recommendation(on_hand: int, in_transit: int, mean_28: float, forecast_14d: float,
                             unit_cost: float) -> dict:
    """Calculo EXACTO del contrato §5 (reutilizado por la validacion post-insercion)."""
    safety = SAFETY_DAYS * mean_28
    target = ceil_stable(forecast_14d + safety)
    position = on_hand + in_transit
    order_qty = max(0, target - position)
    return {"safety": safety, "target": target, "position": position, "order_qty": order_qty,
            "order_value_assumed": order_qty * unit_cost}


def _steps_ok(d: dict, ordered: int, received: int) -> list[str]:
    n = "unidades base"
    return [
        (f"1. Origen: cierre del 10/07/2026 de la trayectoria simulada {d['scenario_id']} "
         "(plazo 7 días, revisión cada 7, seguridad 7 días)."),
        f"2. Saldo simulado en mano al cierre del 10/07: {d['on_hand']} {n}.",
        (f"3. En tránsito al 10/07 = pedidos emitidos hasta esa fecha ({ordered}) menos recepciones hasta "
         f"esa fecha ({received}) = {d['in_transit']} {n}."),
        f"4. Posición = {d['on_hand']} + {d['in_transit']} = {d['position']} {n}.",
        f"5. Promedio diario de 28 días conocido al 10/07 = {d['mean_28']:.6f} {n}/día.",
        f"6. Pronóstico de 14 días (11/07 a 24/07) = {d['forecast_14d']:.6f} {n}.",
        f"7. Seguridad = 7 × {d['mean_28']:.6f} = {d['safety']:.6f} {n}.",
        (f"8. Objetivo = techo(redondeo a 9 decimales de {d['forecast_14d'] + d['safety']:.9f}) "
         f"= {d['target']} {n}."),
        f"9. Pedido sugerido = máx(0, {d['target']} - {d['position']}) = {d['order_qty']} {n}.",
        (f"10. Costo unitario supuesto (65 % de la mediana de precio base hasta el 31/05) = PEN "
         f"{d['unit_cost_assumed']:.4f}; valor supuesto del pedido = PEN {d['order_value_assumed']:.2f}."),
        ("Sugerencia hipotética de vista previa; no es un pedido ejecutado. "
         f"{SIM_LABEL}. La demanda es la venta observada: los faltantes por stock real son desconocidos."),
    ]


def build_recommendations(src: VerifiedSource, catalog: dict, run_id: str) -> list:
    entry, sim = src.entry, src.sim
    index = {s: i for i, s in enumerate(sim["skus"].tolist())}
    df = src.forecasts
    first = df.sort_values(["entidad", "h"]).groupby("entidad", sort=True)
    docs = []
    for ent, grp in first:
        sku, almacen = ent.split("|")
        pred = grp["pred_promedio_28"].to_numpy(float)
        base = {
            "run_id": run_id, "scenario_id": entry["scenario_id"], "provenance": PROVENANCE_SIM,
            "snapshot_date": entry["cutoff"], "sku": sku, "almacen": almacen,
            "categoria": catalog.get(sku) or UNKNOWN, "horizon_days": HORIZON_REC,
            "lead_time_days": LEAD, "review_days": REVIEW, "safety_days": SAFETY_DAYS,
            "currency": "PEN", "unit": "unidad base", "origin": entry["cutoff"],
            "forecast_from": entry["target_start"], "forecast_to": "2026-07-24", "model": CHOSEN,
            "schema_version": SCHEMA_VERSION}
        if sku not in index:
            doc = {**base, "status": "sin_snapshot", "reason": SIN_SNAPSHOT_REASON,
                   **{f: None for f in NUM_FIELDS}, "transit_breakdown": None,
                   "explanation_steps": [
                       "No hay inventario simulado al 10/07 para este producto: " + SIN_SNAPSHOT_REASON + ".",
                       "No se calcula posición ni pedido; el pronóstico sigue disponible en /forecasts.",
                       SIM_LABEL + "."]}
            docs.append(doc)
            continue
        i = index[sku]
        on_hand = int(sim["on_hand"][i])
        ordered, received = int(sim["ordered_cum"][i]), int(sim["received_cum"][i])
        in_transit = ordered - received
        mean_28 = float(pred[0])
        forecast_14d = float(pred[:14].sum())
        cost = float(sim["costo"][i])
        calc = recompute_recommendation(on_hand, in_transit, mean_28, forecast_14d, cost)
        doc = {**base, "status": "ok", "reason": None, "on_hand": on_hand, "in_transit": in_transit,
               "mean_28": mean_28, "forecast_14d": forecast_14d, "unit_cost_assumed": cost, **calc,
               "transit_breakdown": {"ordered_until_snapshot": ordered, "received_until_snapshot": received}}
        doc["explanation_steps"] = _steps_ok(doc, ordered, received)
        docs.append(doc)
    return docs


def build_backtest(src: VerifiedSource, run_id: str, created) -> dict:
    m = src.metrics
    sim_rows, diff_rows = [], []
    for key, val in m["simulacion"].items():
        scen, policy = key.split("|")
        L, S = (int(x[1:]) for x in scen.split("_"))
        sim_rows.append({
            "scenario_id": f"T07_L{L}_S{S}_R7_2026-06-01_2026-07-31", "L": L, "S": S, "R": 7,
            "policy": policy, "total": val["total"], "primaria": val["primaria"],
            "historia_corta": val["historia_corta"], "identidad_valor": val["identidad_valor"],
            "conservacion": val["conservacion"], "provenance": PROVENANCE_SIM, "unit": "unidad base",
            "currency": "PEN"})
    for key, val in m["diferencias"].items():
        scen, policy, vs, cohort = key.split("|")
        diff_rows.append({"scenario": scen, "policy": policy, "vs": vs.removeprefix("vs_"),
                          "cohorte": cohort, "metrics": val})
    pred = m["predictivo"]
    doc = {
        "backtest_id": f"bt-{run_id}", "run_id": run_id, "kind": "T07_desarrollo",
        "label": "Backtest de desarrollo T07 (4 folds solapados y simulación 01/06 a 31/07)",
        "folds": ["G1", "G2", "G3", "G4"], "created": created,
        "scenario_id": "T07_simulacion_2026-06-01_2026-07-31", "provenance": PROVENANCE_SIM,
        "predictive": {"sku": pred["sku"], "categoria": pred["categoria"],
                       "nota": "La fila fold=AGREGADO suma bloques de origen distinto y solapados; "
                               "no son unidades únicas ni admite pruebas de significación."},
        "selection": {**pred["seleccion"], "metodo_elegido": CHOSEN,
                      "comparador": "rf_categoria_distribuido", "control": "cero"},
        "coverage": pred["cobertura"],
        "simulation": sim_rows, "simulation_differences": diff_rows,
        "assumptions": {"L": [3, 7, 14], "S": [0, 7, 14], "R": 7, "factor_costo_sobre_mediana_precio": 0.65,
                        "holding_anual": 0.20, "dias_anio": 365, "holding_diario": 0.20 / 365,
                        "escenario_principal": {"L": 7, "S": 7}, "moneda": "PEN",
                        "unidad": "unidad base", "demanda": "proxy: venta positiva observada, "
                        "posiblemente censurada por stock real desconocido",
                        "limites": ["cuatro folds solapados de desarrollo", "costo y holding supuestos",
                                    "sin MOQ, proveedores ni plazos reales", "un almacén",
                                    "universo fijo sin SKU nuevos", "no autoriza compras"]},
        "disclaimer": SIM_LABEL + ". Resultados de desarrollo sobre meses ya conocidos; no demuestran "
                      "impacto en la empresa ni autorizan compras.",
        "run_label": RUN_LABEL, "schema_version": SCHEMA_VERSION}
    return clean_json(doc)


def build_run_doc(src: VerifiedSource, run_id: str, key: str, fingerprint: str, generated_at,
                  coverage: dict, counts: dict) -> dict:
    e, man, cfg = src.entry, src.manifest, src.config_t07
    fold = man["folds_predictivos"][e["fold"]]
    return clean_json({
        "run_id": run_id, "status": "staging", "kind": "historical_development", "run_label": RUN_LABEL,
        "idempotency_key": key, "fingerprint": fingerprint, "cutoff": e["cutoff"], "origin": e["cutoff"],
        "target_start": e["target_start"], "target_end": e["target_end"], "horizon_days": 21,
        "generated_at": generated_at, "published_at": None,
        "evaluation_period": {"start": e["target_start"], "end": e["target_end"], "days": 21,
                              "evaluable_days": fold["dias_evaluables"],
                              "excluded_days": fold["no_evaluables"], "note": "backtest histórico: "
                              "'observed' es la venta real ya ocurrida; agosto no se usó"},
        "method": {"chosen": CHOSEN, "comparator": "rf_categoria_distribuido", "control": "cero",
                   "note": "La regla provisional de T07 no se cumplió para el RF distribuido; se mantiene "
                           "promedio_28. Control 'cero' = pronóstico 0 (derivado)."},
        "config": {"version": cfg.get("version"), "ventana_promedio_dias": cfg.get("ventana_promedio_dias"),
                   "horizontes": cfg.get("horizontes"), "rf_categoria": cfg.get("rf_categoria"),
                   "folds_predictivos": cfg.get("folds_predictivos"),
                   "config_sha256": man["config_sha256"], "semilla_rf": man.get("semilla_rf")},
        "sources": fold["fuentes"], "sources_fingerprint": fold["fingerprint"],
        "artifacts": src.artifacts,
        "code": {"commit": src.code["commit"], "codigo_sha256": src.code["codigo_sha256"],
                 "commit_protocolo": man.get("commit_protocolo")},
        "counts": counts, "coverage": coverage,
        "provenance_notes": [
            "Ventas observadas: OBSERVED_EXCEL (Excel de la empresa, marzo a julio de 2026).",
            "Stock, tránsito, costos y pedidos: SYNTHETIC_NOT_REAL_INVENTORY. " + SIM_LABEL + ".",
            "Corrida histórica de desarrollo; las recomendaciones son sugerencias hipotéticas de vista previa.",
            "Los faltantes de ventas por stock real son desconocidos; la demanda proxy es la venta observada."],
        "error": None, "schema_version": SCHEMA_VERSION})
