"""T12: calculos de la evaluacion final bajo la seleccion congelada (funciones puras sobre matrices).

Nada aqui lee MongoDB ni agosto: el runner (`pipeline/final/runner.py`) entrega las entradas. Reutiliza SIN
modificarlas las funciones experimentales congeladas (t05/t07/baselines/metrics/daily_series) y el motor de simulacion
exacto del commit e5466413 (`frozen.load_frozen_engine`).

Reglas: matrices fisicamente truncadas en cada origen; NaN = dia no utilizable (antes de la primera venta, enmascarado o
sin registros); un cero observado es 0.0; categorias del baseline operativo = SUMA de los pronosticos SKU.
Inventario simulado con supuestos; no corresponde al inventario real de la empresa.
"""
from __future__ import annotations

import hashlib
import warnings
from collections.abc import Callable
from datetime import date, timedelta

import numpy as np
import pandas as pd

from pipeline.data import daily_series as ds
from pipeline.data.catalog import lookup
from pipeline.forecast import t07 as t7
from pipeline.forecast.baselines import forecast_block, primary_mask
from pipeline.forecast.t05 import _actual, _wide

START = date(2026, 3, 1)
ORIGIN = date(2026, 7, 31)
BLOCK_START = date(2026, 8, 1)
BLOCK_END = date(2026, 8, 21)
SIM_START = date(2026, 8, 1)
SIM_END = date(2026, 8, 31)
HORIZON = t7.HORIZON
POLICIES = ("referencia_fija", "promedio_28", "rf_categoria_distribuido")
SKU_METHODS = ("cero", "promedio_28", "rf_distribuido")
CAT_METHODS = ("cero", "promedio_28", "rf_categoria")
LABEL = "Inventario simulado con supuestos; no corresponde al inventario real de la empresa"


def iso(d: date) -> str:
    return d.isoformat()


def block_days() -> list[str]:
    return [iso(BLOCK_START + timedelta(days=i)) for i in range((BLOCK_END - BLOCK_START).days + 1)]


# ------------------------------------------------------------------------------------------------ firmas
def logical_signature(arrays: dict) -> str:
    """Firma del CONTENIDO logico de un conjunto de arreglos (independiente de metadatos de ZIP/NPZ)."""
    h = hashlib.sha256()
    for name in sorted(arrays):
        a = np.ascontiguousarray(np.asarray(arrays[name]))
        h.update(f"{name}|{a.dtype.str}|{a.shape}\n".encode())
        h.update(a.tobytes() if a.dtype.kind != "O" else "\n".join(map(str, a.ravel())).encode())
    return h.hexdigest()


# ------------------------------------------------------------------------------------------------ mundo <= 31/07
def history_world(D) -> dict:
    """Matriz diaria (sku, almacen) x dia desde 01/03 hasta el corte, categorias del catalogo AL CORTE."""
    pairs = ds.pair_daily(D)
    cal = [iso(d) for d in D.calendar]
    keys, W = _wide(pairs, ["sku", "almacen"], "cantidad_base", cal)
    cats = [lookup(D.catalog, k[0]) for k in keys]
    return {"cal": cal, "keys": keys, "W": W, "cats": cats}


def sales_frame(rows) -> pd.DataFrame:
    return pd.DataFrame([(r["fecha"], r["sku"], r["almacen"], float(r["cantidad_base"])) for r in rows],
                        columns=["fecha", "sku", "almacen", "qty"])


# ------------------------------------------------------------------------------------------------ prediccion fija
def fixed_predictions(world: dict, rf_cfg: dict, cohort: dict, config_sha: str) -> dict:
    """Pronosticos emitidos UNA vez en el origen 31/07 con datos <= 31/07. Devuelve arreglos (sellables) y el bundle RF.

    SKU: cero, promedio_28 (constante h=1..21) y RF por categoria distribuido (parametros/features/pesos T07).
    Categoria: cero, promedio_28 operativo = SUMA de los pronosticos SKU, y RF por categoria."""
    W, keys, cats = world["W"], world["keys"], world["cats"]
    alms = sorted({k[1] for k in keys})
    fc = t7.forecast_origin_t07(W, START, cats, alms, rf_cfg, config_sha)
    blk = forecast_block(W)
    prim = primary_mask(blk, min_history=cohort["historia_minima_dias"],
                        min_usable=cohort["observaciones_utilizables_minimas_en_28"])
    known = blk.history_days > 0
    names = fc["names"]
    cpos = {c: i for i, c in enumerate(names)}
    cidx = np.array([cpos[c] for c in cats])
    mean28 = fc["mean28"]
    cat_op = np.zeros(len(names))
    np.add.at(cat_op, cidx, np.nan_to_num(mean28))                      # suma de pronosticos SKU (NaN = sin pronostico)
    cblk = forecast_block(fc["cat_values"])
    cprim = primary_mask(cblk, min_history=cohort["historia_minima_dias"],
                         min_usable=cohort["observaciones_utilizables_minimas_en_28"])
    cknown = cblk.history_days > 0
    arrays = {
        "sku_keys": np.array([f"{k[0]}|{k[1]}" for k in keys]), "sku_cats": np.array(cats),
        "sku_primaria": prim, "sku_conocido": known, "sku_history_days": blk.history_days,
        "sku_usable_28": blk.usable_28, "pred_sku_promedio_28": np.repeat(mean28[:, None], HORIZON, axis=1),
        "pred_sku_rf_distribuido": fc["rf_dist"], "pred_sku_cero": np.zeros((len(keys), HORIZON)),
        "cat_names": np.array(names), "cat_primaria": cprim, "cat_conocida": cknown,
        "pred_cat_promedio_28_suma_sku": np.repeat(cat_op[:, None], HORIZON, axis=1),
        "pred_cat_rf_categoria": fc["cat_pred"], "pred_cat_cero": np.zeros((len(names), HORIZON)),
        "pesos_asignacion": fc["weights"],
    }
    info = {"weight_counts": fc["weight_counts"], "conservacion_max_abs_error": fc["conservacion_max_abs_error"],
            "negativos_recortados": fc["negativos_recortados"], "entrenamiento": fc["entrenamiento"],
            "n_sku": len(keys), "n_primaria": int(prim.sum()), "n_conocidos": int(known.sum()),
            "n_categorias": len(names)}
    return {"arrays": arrays, "bundle": fc["bundle"], "info": info}


def sealed_inputs_for_sim(world: dict, D, sim_cfg: dict, cohort: dict) -> dict:
    """Inicializacion de la simulacion: SOLO datos <= 31/07 (universo, media inicial, cohorte inicial, costos)."""
    W, keys, cats = world["W"], world["keys"], world["cats"]
    skus = [k[0] for k in keys]
    mean_init = np.nan_to_num(t7.mean_window(W))
    blk0 = forecast_block(W)
    prim0 = primary_mask(blk0, min_history=cohort["historia_minima_dias"],
                         min_usable=cohort["observaciones_utilizables_minimas_en_28"])
    cat_of = dict(zip(skus, cats, strict=True))
    cost, cost_counts = t7.unit_costs(D.sales, skus, cat_of, sim_cfg["costo_unitario"]["factor_sobre_mediana_precio_base"])
    arrays = {"sim_keys": np.array([f"{k[0]}|{k[1]}" for k in keys]), "sim_cats": np.array(cats),
              "sim_media_inicial": mean_init, "sim_primaria_inicial": prim0, "sim_costo_unitario": cost}
    return {"arrays": arrays, "cost_counts": cost_counts}


# ------------------------------------------------------------------------------------------------ evaluacion predictiva
def block_actuals(keys: list, rows, days: list[str]) -> tuple[np.ndarray, pd.DataFrame]:
    """Reales (n, 21) de las entidades conocidas (0 si no vendio) y ventas de entidades NUEVAS en el bloque."""
    sales = sales_frame(rows)
    block = sales[sales["fecha"].isin(days)]
    act, new = _actual(keys, block, ["sku", "almacen"], days)
    return act, new


def evaluable_days(days: list[str], covered: set[str], masked: set[str]) -> np.ndarray:
    """Un dia es evaluable si no esta enmascarado y tiene al menos una linea de venta (cobertura del archivo)."""
    return np.array([(d not in masked) and (d in covered) for d in days])


def evaluate_predictive(sealed: dict, act: np.ndarray, eval_days: np.ndarray, cat_idx: np.ndarray) -> dict:
    """Estadisticos y registros SKU y categoria sobre las predicciones SELLADAS y los reales del bloque."""
    prim, known = sealed["sku_primaria"], sealed["sku_conocido"]
    preds = {"cero": sealed["pred_sku_cero"], "promedio_28": sealed["pred_sku_promedio_28"],
             "rf_distribuido": sealed["pred_sku_rf_distribuido"]}
    masks = {"primaria": prim & known, "historia_corta": known & ~prim}
    sku_stats = t7.eval_fold_predictions(act, preds, eval_days, masks, core=SKU_METHODS)
    ncat = len(sealed["cat_names"])
    cact = np.zeros((ncat, HORIZON))
    np.add.at(cact, cat_idx, act)
    cpreds = {"cero": sealed["pred_cat_cero"], "promedio_28": sealed["pred_cat_promedio_28_suma_sku"],
              "rf_categoria": sealed["pred_cat_rf_categoria"]}
    cmasks = {"primaria": sealed["cat_primaria"] & sealed["cat_conocida"],
              "historia_corta": sealed["cat_conocida"] & ~sealed["cat_primaria"]}
    cat_stats = t7.eval_fold_predictions(cact, cpreds, eval_days, cmasks)
    sku_recs = t7.summarize({"FINAL": sku_stats}, ["FINAL"], 30)
    cat_recs = t7.summarize({"FINAL": cat_stats}, ["FINAL"], 30)
    return {"sku": [r for r in sku_recs if r["fold"] == "FINAL"], "categoria": [r for r in cat_recs if r["fold"] == "FINAL"],
            "cobertura": {"sku": t7.coverage_records({"FINAL": sku_stats}, ["FINAL"]),
                          "categoria": t7.coverage_records({"FINAL": cat_stats}, ["FINAL"])},
            "cact": cact}


def new_sku_report(new: pd.DataFrame, eval_days: list[str], known_units: float) -> dict:
    """SKU cuya primera venta es posterior al 31/07: aparte, sin historia, categoria ni stock inventados."""
    ev = new[new["fecha"].isin(eval_days)] if len(new) else new
    n = int(ev[["sku", "almacen"]].drop_duplicates().shape[0]) if len(ev) else 0
    units = float(ev["qty"].sum()) if len(ev) else 0.0
    tot = units + known_units
    return {"skus_nuevos_con_venta_en_bloque": n, "unidades_nuevos_evaluables": units,
            "unidades_conocidos_evaluables": known_units,
            "cobertura_unidades_universo_conocido": (known_units / tot) if tot > 0 else None}


# ------------------------------------------------------------------------------------------------ simulacion secuencial
def sequential_simulation(*, W: np.ndarray, col0: int, n_days: int, cats: list[str], alms: list[str], cost: np.ndarray,
                          mean_init: np.ndarray, prim0: np.ndarray, rf_cfg: dict, sim_cfg: dict, config_sha: str, eng,
                          forecast_fn: Callable = t7.forecast_origin_t07, progress: Callable | None = None) -> dict:
    """Simulacion de n_days dias a partir de la columna col0 de W (universo conocido al corte).

    En cada revision (final de los dias 1, 8, 15, 22, 29) el pronostico recibe una matriz FISICAMENTE truncada
    W[:, :col0+j+1]: nada posterior existe para el. Referencia fija: media inicial congelada. Mismas condiciones y
    demanda proxy exogena para las tres politicas y las nueve combinaciones (L, S)."""
    demand = W[:, col0:col0 + n_days]
    review = eng.review_indices(n_days, 7)
    forecasts: dict = {}
    for j in review:
        trunc = np.array(W[:, :col0 + j + 1], copy=True)
        trunc.setflags(write=False)
        fc = forecast_fn(trunc, START, cats, alms, rf_cfg, config_sha)
        forecasts[j] = {"mean28": np.nan_to_num(fc["mean28"]), "rf_dist": fc["rf_dist"], "pesos": fc["weight_counts"],
                        "conservacion": fc["conservacion_max_abs_error"], "origen_columna": col0 + j,
                        "entrenamiento": fc["entrenamiento"],
                        "hash": hashlib.sha256(np.nan_to_num(fc["mean28"]).tobytes()
                                               + np.nan_to_num(fc["rf_dist"]).tobytes()).hexdigest()}
        if progress:
            progress(j, forecasts[j])
    R = sim_cfg["matriz"]["R"]
    results, arrays, fallback_rf = {}, {}, 0
    for L in sim_cfg["matriz"]["L"]:
        for S in sim_cfg["matriz"]["S"]:
            H = L + R
            stock0 = eng.ceil_stable(mean_init * (L + R))
            tg = {"referencia_fija": {j: eng.ceil_stable(mean_init * (L + R + S)) for j in review},
                  "promedio_28": {j: eng.ceil_stable(forecasts[j]["mean28"] * H + S * forecasts[j]["mean28"]) for j in review},
                  "rf_categoria_distribuido": {}}
            for j in review:
                f = forecasts[j]
                rf_sum = f["rf_dist"][:, :H].sum(axis=1)
                bad = np.isnan(rf_sum)
                fallback_rf += int(bad.sum())
                rf_sum = np.where(bad, f["mean28"] * H, rf_sum)               # categoria sin historia: promedio_28 (contado)
                tg["rf_categoria_distribuido"][j] = eng.ceil_stable(rf_sum + S * f["mean28"])
            for pol in POLICIES:
                res = eng.simulate(demand, review, tg[pol], L, stock0, cost, sim_cfg["holding_anual"], sim_cfg["dias_anio"])
                cons = eng.check_conservation(res, demand)
                mt = {"total": eng.metrics(res, demand, cost), "primaria": eng.metrics(res, demand, cost, prim0),
                      "historia_corta": eng.metrics(res, demand, cost, ~prim0)}
                mt["identidad_valor"] = eng.value_identity(mt["total"])
                mt["conservacion"] = cons
                results[(L, S, pol)] = mt
                arrays[f"L{L}_S{S}_{pol}"] = res
    return {"results": results, "arrays": arrays, "forecasts": forecasts, "demand": demand, "review": review,
            "fallback_rf_filas": fallback_rf}


def policy_diffs(results: dict, metric_names) -> dict:
    """Diferencias absolutas y relativas frente a referencia_fija y promedio_28 (denominador cero => None)."""
    from pipeline.final.frozen import load_frozen_engine
    eng = load_frozen_engine()
    out = {}
    for (L, S, pol), mt in results.items():
        for ref in ("referencia_fija", "promedio_28"):
            if pol == ref:
                continue
            for part in ("total", "primaria", "historia_corta"):
                base, cur = results[(L, S, ref)][part], mt[part]
                out[f"L{L}_S{S}|{pol}|vs_{ref}|{part}"] = {
                    m: {"abs": (None if cur[m] is None or base[m] is None else cur[m] - base[m]),
                        "rel": eng.rel_diff(cur[m], base[m])} for m in metric_names}
    return out


KEY_METRICS = ["fill_rate", "perdidas_unidades", "tasa_dias_sku_con_faltante", "stock_medio_unidades_por_dia",
               "stock_final_unidades", "pedidos_unidades", "compras_desembolsadas_supuesto", "costo_consumido_supuesto",
               "holding_supuesto", "valor_stock_final_supuesto", "transito_final_unidades"]


def quiet_warnings() -> None:
    warnings.filterwarnings("ignore", category=RuntimeWarning)
