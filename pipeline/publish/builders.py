"""Construccion de documentos publicables a partir de artefactos verificados (T08 §4-§5).

Funciones puras (sin I/O): reciben VerifiedSource y el catalogo <= corte.
"""
from __future__ import annotations

import math
from fractions import Fraction

import numpy as np

from .schema import (
    PROVENANCE_OBS,
    PROVENANCE_SIM,
    RUN_LABEL,
    SCHEMA_VERSION,
    SIM_LABEL,
)
from .signals import Signals, exact_target, fraction_text
from .source import PUBLISHER_VERSION, VerifiedSource

UNKNOWN = "DESCONOCIDA"
CHOSEN = "promedio_28"
LEAD, REVIEW, SAFETY_DAYS, HORIZON_REC = 7, 7, 7, 14
SIN_SNAPSHOT_REASON = ("SIN_INVENTARIO_SIMULADO_AL_10_07: producto conocido despues del 31/05; "
                       "no se supone stock cero")
NUM_FIELDS = ("on_hand", "in_transit", "position", "mean_28", "forecast_14d", "safety", "target",
              "order_qty", "unit_cost_assumed", "order_value_assumed")
NULL_EXTRA = ("sum_28", "days_28", "mean_28_exact", "target_raw_exact", "signals")


def ceil_stable(x: float, decimals: int = 9) -> int:
    """Techo tras redondear a 9 decimales (idem pipeline.sim.engine.ceil_stable). Solo para valores en coma
    flotante del motor T07; las recomendaciones usan aritmetica racional exacta (ver signals.py)."""
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


def recompute_recommendation(on_hand: int, in_transit: int, sum_28: Fraction, days_28: int,
                             unit_cost: float) -> dict:
    """Calculo EXACTO del contrato §5 con aritmetica racional: media = suma_28/dias_28; pronostico a
    14 dias = 14*media; seguridad = 7*media; objetivo = techo(pronostico + seguridad) sin epsilon."""
    mean = Fraction(sum_28) / days_28
    raw, target = exact_target(Fraction(sum_28), days_28, HORIZON_REC, SAFETY_DAYS)
    position = on_hand + in_transit
    order_qty = max(0, target - position)
    return {"mean_28": float(mean), "forecast_14d": float(HORIZON_REC * mean), "safety": float(SAFETY_DAYS * mean),
            "target_raw_exact": fraction_text(raw), "target": target, "position": position,
            "order_qty": order_qty, "order_value_assumed": order_qty * unit_cost}


def _steps_ok(d: dict, ordered: int, received: int) -> list[str]:
    n = "unidades base"
    return [
        (f"1. Origen: cierre del 10/07/2026 de la trayectoria simulada {d['scenario_id']} "
         "(plazo 7 días, revisión cada 7, seguridad 7 días)."),
        f"2. Saldo simulado en mano al cierre del 10/07: {d['on_hand']} {n}.",
        (f"3. En tránsito al 10/07 = pedidos emitidos hasta esa fecha ({ordered}) menos recepciones hasta "
         f"esa fecha ({received}) = {d['in_transit']} {n}."),
        f"4. Posición = {d['on_hand']} + {d['in_transit']} = {d['position']} {n}.",
        (f"5. Promedio diario de 28 días conocido al 10/07 = {d['sum_28']} {n} en {d['days_28']} días útiles "
         f"= {d['mean_28_exact']} por día (≈ {d['mean_28']:.4f})."),
        f"6. Pronóstico de 14 días (11/07 a 24/07) = 14 × {d['mean_28_exact']} ≈ {d['forecast_14d']:.3f} {n}.",
        f"7. Seguridad = 7 × {d['mean_28_exact']} ≈ {d['safety']:.3f} {n}.",
        (f"8. Objetivo = techo(21 × {d['mean_28_exact']}) = techo({d['target_raw_exact']}) = {d['target']} {n} "
         "(aritmética racional exacta, sin redondeo previo)."),
        f"9. Pedido sugerido = máx(0, {d['target']} - {d['position']}) = {d['order_qty']} {n}.",
        (f"10. Costo unitario supuesto (65 % de la mediana de precio base hasta el 31/05) = PEN "
         f"{d['unit_cost_assumed']:.4f}; valor supuesto del pedido = PEN {d['order_value_assumed']:.2f}."),
        ("Sugerencia hipotética de vista previa; no es un pedido ejecutado. "
         f"{SIM_LABEL}. La demanda es la venta observada: los faltantes por stock real son desconocidos."),
    ]


def build_recommendations(src: VerifiedSource, catalog: dict, run_id: str, signals: Signals) -> list:
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
                   **{f: None for f in NUM_FIELDS}, **dict.fromkeys(NULL_EXTRA), "transit_breakdown": None,
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
        sig = signals.per_sku.get((sku, almacen))
        if sig is None or sig[1] <= 0:
            raise ValueError(f"sin señal exacta de 28 dias para {sku}|{almacen}")
        total, days = sig
        cost = float(sim["costo"][i])
        calc = recompute_recommendation(on_hand, in_transit, total, days, cost)
        csv_mean = float(pred[0])
        # coherencia con el CSV historico (10 cifras significativas): sirve de control, NUNCA de entrada
        if abs(calc["mean_28"] - csv_mean) > 1e-9 * max(1.0, abs(csv_mean)):
            raise ValueError(f"senal exacta incoherente con el pronostico historico de {sku}|{almacen}")
        doc = {**base, "status": "ok", "reason": None, "on_hand": on_hand, "in_transit": in_transit,
               "sum_28": fraction_text(total), "days_28": int(days),
               "mean_28_exact": fraction_text(Fraction(total) / days), "unit_cost_assumed": cost, **calc,
               "signals": {"version": signals.version, "window": [signals.window_start, signals.window_end],
                           "training_fingerprint": signals.training_fingerprint, "csv_mean_28": csv_mean,
                           "nota": "media exacta recalculada desde historia aprobada <= origen; el CSV T07 "
                                   "(10 cifras) solo se usa como control de coherencia"},
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
                  coverage: dict, counts: dict, signals: Signals | None = None) -> dict:
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
        "publisher": {"version": PUBLISHER_VERSION, "signals_version": signals.version if signals else None,
                      "signals_fingerprint": signals.fingerprint if signals else None,
                      "signals_window": [signals.window_start, signals.window_end] if signals else None,
                      "signals_skus": len(signals.per_sku) if signals else None,
                      "reference": src.entry.get("approved_reference", {}).get("commit")},
        "provenance_notes": [
            "Ventas observadas: OBSERVED_EXCEL (Excel de la empresa, marzo a julio de 2026).",
            "Stock, tránsito, costos y pedidos: SYNTHETIC_NOT_REAL_INVENTORY. " + SIM_LABEL + ".",
            "Corrida histórica de desarrollo; las recomendaciones son sugerencias hipotéticas de vista previa.",
            "Los faltantes de ventas por stock real son desconocidos; la demanda proxy es la venta observada."],
        "error": None, "schema_version": SCHEMA_VERSION})
