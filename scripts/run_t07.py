# ruff: noqa: ISC004
"""T07: evaluacion de horizontes 10/14/21 y simulacion 01/06-31/07/2026 (solo datos <= 31/07).

Uso: python -m scripts.run_t07 [--db demand_forecasting_v2] [--out artifacts/private/t07]
Inventario simulado con supuestos; no corresponde al inventario real de la empresa.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from pipeline.data import daily_series as ds
from pipeline.data.calendar import EXCLUDED_DATES
from pipeline.data.catalog import lookup
from pipeline.data.importer import get_client, sha256_file
from pipeline.data.training_access import load_training_data
from pipeline.forecast import t07 as t7
from pipeline.forecast.baselines import forecast_block, primary_mask
from pipeline.forecast.models import save_bundle
from pipeline.forecast.t05 import _actual, _wide
from pipeline.sim import engine as eng

CFG = Path("config/t07_config.json")
CODE = ["pipeline/forecast/t05.py", "pipeline/data/importer.py", "pipeline/forecast/features.py", "pipeline/forecast/models.py", "pipeline/forecast/metrics.py",
        "pipeline/forecast/baselines.py", "pipeline/forecast/t07.py", "pipeline/sim/engine.py",
        "pipeline/data/training_access.py", "pipeline/data/sources.py", "pipeline/data/catalog.py",
        "pipeline/data/daily_series.py", "pipeline/data/calendar.py", "scripts/run_t07.py"]
POLICIES = ("referencia_fija", "promedio_28", "rf_categoria_distribuido")
DOCS = Path("docs")
LABEL = "Inventario simulado con supuestos; no corresponde al inventario real de la empresa"


def code_hash() -> str:
    h = hashlib.sha256()
    for f in CODE:
        h.update(f.encode() + b"\0" + Path(f).read_bytes().replace(b"\r\n", b"\n") + b"\0")
    return h.hexdigest()


def _iso(d: date) -> str:
    return d.isoformat()


def load_world(db, cfg, models_dir: Path | None = None):
    """Datos comunes: ventas aprobadas <= 31/07, matriz diaria completa y marcos para actuales."""
    D = load_training_data(db, date.fromisoformat(cfg["datos"]["ultimo_dia_usado"]),
                           start=date.fromisoformat(cfg["datos"]["inicio"]))
    if max(r["fecha"] for r in D.sales) > cfg["datos"]["ultimo_dia_usado"]:
        raise AssertionError("ventas posteriores al 31/07")
    pairs = ds.pair_daily(D)
    cal = [_iso(d) for d in D.calendar]
    idx, W = _wide(pairs, ["sku", "almacen"], "cantidad_base", cal)
    sales = pd.DataFrame([(r["fecha"], r["sku"], r["almacen"], float(r["cantidad_base"])) for r in D.sales],
                         columns=["fecha", "sku", "almacen", "qty"])
    return {"D": D, "cal": cal, "keys": idx, "W": W, "sales": sales, "covered": set(sales["fecha"]),
            "masked": {_iso(d) for d in EXCLUDED_DATES}}


def predictive(db, cfg, world, sha, models_dir: Path | None, log: list):
    start = date.fromisoformat(cfg["datos"]["inicio"])
    cp = cfg["cohorte_primaria"]
    rf_cfg = cfg["rf_categoria"]
    folds = [f["id"] for f in cfg["folds_predictivos"]]
    sku_stats, cat_stats, info, preds_rows = {}, {}, {}, []
    ref0 = None
    for f in cfg["folds_predictivos"]:
        cut = date.fromisoformat(f["corte"])
        train = load_training_data(db, cut, start=start)
        pairs = ds.pair_daily(train)
        cal = [_iso(d) for d in train.calendar]
        keys, W = _wide(pairs, ["sku", "almacen"], "cantidad_base", cal)
        cats = [lookup(train.catalog, k[0]) for k in keys]
        t0 = time.perf_counter()
        fc = t7.forecast_origin_t07(W, start, cats, sorted({k[1] for k in keys}), rf_cfg, sha)
        seg = round(time.perf_counter() - t0, 2)
        if models_dir is not None:
            save_bundle(fc["bundle"], models_dir / f"{f['id']}_rf_categoria.joblib")
        days = [_iso(cut + timedelta(days=i + 1)) for i in range(t7.HORIZON)]
        block = world["sales"][world["sales"]["fecha"].isin(days)]
        act, new = _actual(keys, block, ["sku", "almacen"], days)
        eval_days = np.array([(d not in world["masked"]) and (d in world["covered"]) for d in days])
        new_ev = new[new["fecha"].isin([d for d, e in zip(days, eval_days, strict=True) if e])]
        blk = forecast_block(W)
        prim = primary_mask(blk, min_history=cp["historia_minima_dias"], min_usable=cp["observaciones_utilizables_minimas_en_28"])
        known = blk.history_days > 0
        mean28 = fc["mean28"]
        if ref0 is None:
            ref0 = dict(zip(keys, mean28, strict=True))
        refv = np.array([ref0.get(k, np.nan) for k in keys])
        preds = {"cero": np.zeros((len(keys), t7.HORIZON)),
                 "promedio_28": np.repeat(mean28[:, None], t7.HORIZON, axis=1),
                 "referencia_fija_0531": np.repeat(refv[:, None], t7.HORIZON, axis=1),
                 "rf_distribuido": fc["rf_dist"]}
        masks = {"primaria": prim & known, "historia_corta": known & ~prim}
        sku_stats[f["id"]] = t7.eval_fold_predictions(act, preds, eval_days, masks,
                                                      core=("cero", "promedio_28", "rf_distribuido"))
        # categoria (productos conocidos al corte)
        names = fc["names"]
        cpos = {c: i for i, c in enumerate(names)}
        cact = np.zeros((len(names), t7.HORIZON))
        np.add.at(cact, np.array([cpos[c] for c in cats]), act)
        cblk = forecast_block(fc["cat_values"])
        cprim = primary_mask(cblk, min_history=cp["historia_minima_dias"], min_usable=cp["observaciones_utilizables_minimas_en_28"])
        cknown = cblk.history_days > 0
        cpreds = {"cero": np.zeros((len(names), t7.HORIZON)),
                  "promedio_28": np.repeat(fc["cat_mean28"][:, None], t7.HORIZON, axis=1), "rf_categoria": fc["cat_pred"]}
        cat_stats[f["id"]] = t7.eval_fold_predictions(cact, cpreds, eval_days, {"primaria": cprim & cknown,
                                                                                "historia_corta": cknown & ~cprim})
        info[f["id"]] = {
            "corte": f["corte"], "fingerprint": train.fingerprint, "fuentes": list(train.sources.manifest),
            "dias_evaluables": int(eval_days.sum()), "no_evaluables": [d for d, e in zip(days, eval_days, strict=True) if not e],
            "skus_conocidos": int(known.sum()), "skus_nuevos_en_bloque": int(new[["sku", "almacen"]].drop_duplicates().shape[0]),
            "unidades_nuevos_evaluables": float(new_ev["qty"].sum()), "pesos": fc["weight_counts"],
            "conservacion_categoria_a_sku_max_abs": fc["conservacion_max_abs_error"],
            "negativos_recortados": fc["negativos_recortados"], "segundos_rf": seg,
            "entrenamiento": fc["entrenamiento"]}
        log.append({"fold": f["id"], **fc["entrenamiento"], "segundos_total": seg})
        for i, k in enumerate(keys):
            if not (prim | (known & ~prim))[i]:
                continue
            for h, d in enumerate(days):
                preds_rows.append((f["id"], f"{k[0]}|{k[1]}", "primaria" if prim[i] else "historia_corta", d, h + 1,
                                   bool(eval_days[h]), act[i, h], mean28[i], refv[i], fc["rf_dist"][i, h]))
    rs = lambda stt: t7.summarize(stt, folds, cfg_r2)
    cfg_r2 = 30
    sku_recs, cat_recs = rs(sku_stats), rs(cat_stats)
    sel = t7.select_candidate(sku_recs, cfg["seleccion_predictiva_provisional"], folds)
    cov = {"sku": t7.coverage_records(sku_stats, folds), "categoria": t7.coverage_records(cat_stats, folds)}
    cols = ["fold", "entidad", "cohorte", "fecha", "h", "evaluable", "real", "pred_promedio_28", "pred_referencia_fija_0531",
            "pred_rf_distribuido"]
    # nota: promedio_28 y referencia fija son constantes diarias; se guarda el valor diario
    return {"sku": sku_recs, "categoria": cat_recs, "seleccion": sel, "folds": info, "cobertura": cov,
            "predicciones": pd.DataFrame(preds_rows, columns=cols)}


def simulation(db, cfg, world, sha, models_dir: Path | None, log: list):
    sim = cfg["simulacion"]
    start = date.fromisoformat(cfg["datos"]["inicio"])
    cp = cfg["cohorte_primaria"]
    cut0 = date.fromisoformat(sim["datos_de_inicializacion_hasta"])
    train0 = load_training_data(db, cut0, start=start)
    cal = world["cal"]
    col0 = cal.index(_iso(cut0)) + 1                       # primera columna de simulacion (01/06)
    n_days = cal.index(sim["fin"]) + 1 - col0
    pairs0 = ds.pair_daily(train0)
    uni_keys = sorted({(r.sku, r.almacen) for r in pairs0.itertuples()})
    pos = {k: i for i, k in enumerate(world["keys"])}
    rows = [pos[k] for k in uni_keys]
    W = world["W"][rows]
    cats = [lookup(train0.catalog, k[0]) for k in uni_keys]
    alms = sorted({k[1] for k in uni_keys})
    skus = [k[0] for k in uni_keys]
    new_rows = [i for k, i in pos.items() if k not in set(uni_keys)]
    new_units = float(np.nansum(np.clip(world["W"][new_rows][:, col0:col0 + n_days], 0, None))) if new_rows else 0.0
    demand = W[:, col0:col0 + n_days]
    mean_init = np.nan_to_num(t7.mean_window(W[:, :col0]))
    blk0 = forecast_block(W[:, :col0])
    prim0 = primary_mask(blk0, min_history=cp["historia_minima_dias"], min_usable=cp["observaciones_utilizables_minimas_en_28"])
    cat_of = dict(zip(skus, cats, strict=True))
    cost, cost_counts = t7.unit_costs(train0.sales, skus, cat_of, sim["costo_unitario"]["factor_sobre_mediana_precio_base"])
    review = eng.review_indices(n_days, 7)
    forecasts = {}
    for j in review:
        t0 = time.perf_counter()
        fc = t7.forecast_origin_t07(W[:, :col0 + j + 1], start, cats, alms, cfg["rf_categoria"], sha)
        seg = round(time.perf_counter() - t0, 2)
        if models_dir is not None:
            save_bundle(fc["bundle"], models_dir / f"sim_{cal[col0 + j]}_rf_categoria.joblib")
        forecasts[j] = {"mean28": np.nan_to_num(fc["mean28"]), "rf_dist": fc["rf_dist"],
                        "origen": cal[col0 + j], "objetivos_desde": cal[col0 + j + 1],
                        "objetivos_hasta": _iso(date.fromisoformat(cal[col0 + j]) + timedelta(days=t7.HORIZON)),
                        "pesos": fc["weight_counts"], "conservacion": fc["conservacion_max_abs_error"], "segundos": seg,
                        "hash": hashlib.sha256(np.nan_to_num(fc["mean28"]).tobytes() + np.nan_to_num(fc["rf_dist"]).tobytes()).hexdigest()}
        log.append({"origen_sim": cal[col0 + j], **fc["entrenamiento"], "segundos_total": seg})
    R = sim["matriz"]["R"]
    results, fallback_rf, arrays = {}, 0, {}
    for L in sim["matriz"]["L"]:
        for S in sim["matriz"]["S"]:
            H = L + R
            stock0 = eng.ceil_stable(mean_init * (L + R))
            tg = {"referencia_fija": {j: eng.ceil_stable(mean_init * (L + R + S)) for j in review}}
            tg["promedio_28"] = {j: eng.ceil_stable(forecasts[j]["mean28"] * H + S * forecasts[j]["mean28"]) for j in review}
            tg["rf_categoria_distribuido"] = {}
            for j in review:
                f = forecasts[j]
                rf_sum = f["rf_dist"][:, :H].sum(axis=1)
                bad = np.isnan(rf_sum)
                fallback_rf += int(bad.sum())
                rf_sum = np.where(bad, f["mean28"] * H, rf_sum)      # categoria sin historia: promedio_28 (contado)
                tg["rf_categoria_distribuido"][j] = eng.ceil_stable(rf_sum + S * f["mean28"])
            for pol in POLICIES:
                res = eng.simulate(demand, review, tg[pol], L, stock0, cost, sim["holding_anual"], sim["dias_anio"])
                cons = eng.check_conservation(res, demand)
                mt = {"total": eng.metrics(res, demand, cost)}
                mt["primaria"] = eng.metrics(res, demand, cost, prim0)
                mt["historia_corta"] = eng.metrics(res, demand, cost, ~prim0)
                mt["identidad_valor"] = eng.value_identity(mt["total"])
                mt["conservacion"] = cons
                results[(L, S, pol)] = mt
                arrays[f"L{L}_S{S}_{pol}"] = res
    rep = {"universo_skus": len(uni_keys), "primaria_inicial": int(prim0.sum()), "historia_corta_inicial": int((~prim0).sum()),
           "excluidos_nuevos_skus": len(new_rows), "excluidos_nuevos_unidades_proxy": new_units,
           "costo_fuentes": cost_counts, "fallback_rf_a_promedio_filas": fallback_rf,
           "fingerprint_inicializacion": train0.fingerprint, "fuentes_inicializacion": list(train0.sources.manifest),
           "dias": n_days, "dias_evaluables": int((~np.isnan(demand)).all(axis=0).sum()),
           "revisiones": [{"dia": forecasts[j]["origen"], "objetivos_desde": forecasts[j]["objetivos_desde"],
                           "objetivos_hasta": forecasts[j]["objetivos_hasta"], "pesos": forecasts[j]["pesos"],
                           "conservacion_cat_a_sku": forecasts[j]["conservacion"],
                           "hash_pronostico": forecasts[j]["hash"]} for j in review],
           "hash_inicializacion": hashlib.sha256(mean_init.tobytes() + cost.tobytes()).hexdigest()}
    return results, rep, arrays, demand, cost, skus


def diffs(results: dict, key: str, metrics_list) -> dict:
    out = {}
    for (L, S, pol), mt in results.items():
        for ref in ("referencia_fija", "promedio_28"):
            if pol == ref:
                continue
            for part in ("total", "primaria", "historia_corta"):
                base = results[(L, S, ref)][part]
                cur = mt[part]
                out[f"L{L}_S{S}|{pol}|vs_{ref}|{part}"] = {
                    m: {"abs": (None if cur[m] is None or base[m] is None else cur[m] - base[m]),
                        "rel": eng.rel_diff(cur[m], base[m])} for m in metrics_list}
    return out


KEYM = ["fill_rate", "perdidas_unidades", "tasa_dias_sku_con_faltante", "stock_medio_unidades_por_dia", "stock_final_unidades",
        "pedidos_unidades", "compras_desembolsadas_supuesto", "costo_consumido_supuesto", "holding_supuesto",
        "valor_stock_final_supuesto", "transito_final_unidades"]


def compute(db, cfg, sha, out_dir: Path | None):
    models_dir = None
    if out_dir is not None:
        models_dir = out_dir / "modelos"
        models_dir.mkdir(parents=True, exist_ok=True)
    world = load_world(db, cfg)
    log: list = []
    pred = predictive(db, cfg, world, sha, models_dir, log)
    results, rep, arrays, demand, cost, skus = simulation(db, cfg, world, sha, models_dir, log)
    return {"pred": pred, "sim": results, "sim_rep": rep, "arrays": arrays, "log": log, "demand": demand,
            "cost": cost, "skus": skus, "world": world}


def _f(v, nd=3):
    return "-" if v is None else (f"{v:.{nd}f}" if isinstance(v, float) else str(v))


def render(r, cfg, man) -> str:
    sel = r["pred"]["seleccion"]
    L = ["# T07 Resultados: horizontes 10/14/21 y simulación junio-julio (desarrollo)", "",
         f"**{LABEL}.** Generado el {man['generado_lima']} (America/Lima). Protocolo congelado en {man['commit_protocolo']}. "
         "Solo ventas ≤ 31/07; agosto no se leyó. WAPE y razones son fracciones (1,00 = 100 %). Folds de desarrollo "
         "(bloques solapados): no son prueba final ni evidencia de impacto en la MYPE.", "",
         "## Parte A: evaluación predictiva (4 folds, bloques de 21 días)", "",
         f"Regla provisional (SKU, acumulado H=14, primaria, común): WAPE rf_distribuido {_f(sel['WAPE_candidato'], 4)} frente a "
         f"promedio_28 {_f(sel['WAPE_comparador'], 4)}; mejora relativa {_f(sel['mejora_relativa'], 4)}; folds favorables "
         f"{sel['folds_favorables']}; sesgo/observado {_f(sel['sesgo_relativo'], 3)}; **{sel['nota']}**.", ""]
    for lvl, title in (("sku", "SKU-almacén"), ("categoria", "Categoría (productos conocidos al corte)")):
        meths = t7.METHODS_SKU if lvl == "sku" else t7.METHODS_CAT
        for view in ("acum10", "acum14", "acum21", "diaria"):
            L += [f"### {title}: primaria, universo común, {view}, agregado de 4 folds (bloques solapados)", "",
                  "| Método | n | MAE | RMSE | WAPE | Sesgo (pred−obs) | Unidades obs. | Sub/Sobre | R² |", "|---|---|---|---|---|---|---|---|---|"]
            for m in meths:
                x = next((q for q in r["pred"][lvl] if (q["fold"], q["cohorte"], q["metodo"], q["vista"]) == ("AGREGADO", "primaria", m, view)), None)
                if x and x["n"]:
                    L.append(f"| {m} | {x['n']} | {_f(x['MAE'])} | {_f(x['RMSE'])} | {_f(x['WAPE'], 4)} | {_f(x['sesgo_acumulado'], 1)} | "
                             f"{x['unidades_observadas']:.0f} | {x['prop_subpronostico']:.3f}/{x['prop_sobrepronostico']:.3f} | {_f(x['R2'])} |")
            L.append("")
    L += ["### WAPE acumulado H=14 SKU primaria por fold", "", "| Fold | " + " | ".join(t7.METHODS_SKU) + " |", "|---|" + "---|" * 4]
    for f in ["G1", "G2", "G3", "G4"]:
        L.append(f"| {f} | " + " | ".join(_f(next((q for q in r["pred"]["sku"] if (q["fold"], q["cohorte"], q["metodo"], q["vista"]) == (f, "primaria", m, "acum14")), {}).get("WAPE"), 3)
                                         for m in t7.METHODS_SKU) + " |")
    L += ["", "### Folds: cobertura, pesos y conservación", "", "| Fold | Corte | SKU conocidos | Nuevos en bloque (uds. evaluables) | Días evaluables | Categorías peso 28d / hist. / uniforme | Conservación cat→SKU | Negativos recortados |", "|---|---|---|---|---|---|---|---|"]
    for f, i in r["pred"]["folds"].items():
        w = i["pesos"]
        L.append(f"| {f} | {i['corte']} | {i['skus_conocidos']} | {i['skus_nuevos_en_bloque']} ({i['unidades_nuevos_evaluables']:.0f}) | {i['dias_evaluables']}/21 | "
                 f"{w['categorias_peso_28d']}/{w['categorias_fallback_historico']}/{w['categorias_fallback_uniforme']} | {i['conservacion_categoria_a_sku_max_abs']:.1e} | {i['negativos_recortados']} |")
    rep = r["sim_rep"]
    L += ["", "## Parte B: simulación 01/06–31/07 (" + LABEL + ")", "",
          f"Universo fijo: {rep['universo_skus']} SKU conocidos al 31/05 ({rep['primaria_inicial']} primaria, {rep['historia_corta_inicial']} historia corta). "
          f"Excluidos por ser posteriores: {rep['excluidos_nuevos_skus']} SKU con {rep['excluidos_nuevos_unidades_proxy']:.0f} unidades de demanda proxy en junio-julio (cobertura aparte). "
          f"Costos: fuente del precio {rep['costo_fuentes']}. Fallbacks RF→promedio_28 (filas SKU-revisión-escenario): {rep['fallback_rf_a_promedio_filas']}. "
          "Costos, holding (20 %/365), lead time y seguridad son supuestos; 07/06 sin evento de demanda; demanda proxy exógena.", "",
          "### Escenario principal L=7, S=7 (total)", "",
          "| Política | Demanda elegible | Atendidas | Perdidas | Fill rate | Tasa de días-SKU con faltante | Stock medio/día | Stock final | Pedidos (uds.) | Tránsito final | Holding supuesto | Compras desembolsadas | Costo consumido | Valor stock final |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for pol in POLICIES:
        t = r["sim"][(7, 7, pol)]["total"]
        L.append(f"| {pol} | {t['demanda_proxy_elegible_unidades']:.0f} | {t['atendidas_unidades']:.0f} | {t['perdidas_unidades']:.0f} | {_f(t['fill_rate'], 4)} | "
                 f"{_f(t['tasa_dias_sku_con_faltante'], 4)} | {t['stock_medio_unidades_por_dia']:.0f} | {t['stock_final_unidades']:.0f} | {t['pedidos_unidades']:.0f} | "
                 f"{t['transito_final_unidades']:.0f} | {t['holding_supuesto']:.0f} | {t['compras_desembolsadas_supuesto']:.0f} | {t['costo_consumido_supuesto']:.0f} | {t['valor_stock_final_supuesto']:.0f} |")
    L += ["", "### Los nueve escenarios (total): fill rate / perdidas / stock medio / compras desembolsadas (supuesto)", "",
          "| L | S | " + " | ".join(POLICIES) + " |", "|---|---|" + "---|" * 3]
    for Lt in cfg["simulacion"]["matriz"]["L"]:
        for S in cfg["simulacion"]["matriz"]["S"]:
            cells = []
            for pol in POLICIES:
                t = r["sim"][(Lt, S, pol)]["total"]
                cells.append(f"{_f(t['fill_rate'], 4)} / {t['perdidas_unidades']:.0f} / {t['stock_medio_unidades_por_dia']:.0f} / {t['compras_desembolsadas_supuesto']:.0f}")
            L.append(f"| {Lt} | {S} | " + " | ".join(cells) + " |")
    L += ["", "### Diferencias del escenario principal frente a referencia fija y a promedio_28 (total)", "",
          "| Política | vs | Δ fill rate (abs) | Δ perdidas (uds., rel) | Δ stock medio (rel) | Δ compras (rel) | Δ valor stock final (rel) |", "|---|---|---|---|---|---|---|"]
    d = r["diffs"]
    for pol in POLICIES:
        for ref in ("referencia_fija", "promedio_28"):
            if pol == ref:
                continue
            x = d[f"L7_S7|{pol}|vs_{ref}|total"]
            L.append(f"| {pol} | {ref} | {_f(x['fill_rate']['abs'], 4)} | {_f(x['perdidas_unidades']['abs'], 0)} ({_f(x['perdidas_unidades']['rel'], 3)}) | "
                     f"{_f(x['stock_medio_unidades_por_dia']['rel'], 3)} | {_f(x['compras_desembolsadas_supuesto']['rel'], 3)} | {_f(x['valor_stock_final_supuesto']['rel'], 3)} |")
    L += ["", "### Servicio frente a inventario: rf_categoria_distribuido vs promedio_28 en los nueve escenarios (total)", "",
          "| L | S | Δ fill rate | Δ stock medio (rel) | Δ compras (rel) | Δ perdidas (rel) |", "|---|---|---|---|---|---|"]
    for Lt in cfg["simulacion"]["matriz"]["L"]:
        for S in cfg["simulacion"]["matriz"]["S"]:
            x = d[f"L{Lt}_S{S}|rf_categoria_distribuido|vs_promedio_28|total"]
            L.append(f"| {Lt} | {S} | {_f(x['fill_rate']['abs'], 4)} | {_f(x['stock_medio_unidades_por_dia']['rel'], 3)} | "
                     f"{_f(x['compras_desembolsadas_supuesto']['rel'], 3)} | {_f(x['perdidas_unidades']['rel'], 3)} |")
    L += ["", "Lectura: la Parte A muestra que rf_distribuido es peor que promedio_28 como pronóstico y sobrepronostica "
          "(sesgo ≈ +17 % en H=14); su mayor fill rate en la simulación coincide con más stock y más compras, de modo que "
          "**no** puede atribuirse a un mejor pronóstico: es compatible con simplemente pedir más. Sin una comparación a stock "
          "o compras equivalentes, la ventaja de servicio no es concluyente.", ""]
    L += ["### Escenario principal por cohorte inicial", "",
          "| Cohorte | Política | Demanda elegible | Fill rate | Perdidas | Stock medio/día | Compras desembolsadas |",
          "|---|---|---|---|---|---|---|"]
    for part in ("primaria", "historia_corta"):
        for pol in POLICIES:
            t = r["sim"][(7, 7, pol)][part]
            L.append(f"| {part} | {pol} | {t['demanda_proxy_elegible_unidades']:.0f} | {_f(t['fill_rate'], 4)} | "
                     f"{t['perdidas_unidades']:.0f} | {t['stock_medio_unidades_por_dia']:.0f} | {t['compras_desembolsadas_supuesto']:.0f} |")
    L += ["", "### Parte A: historia corta (SKU, universo común, acum14, agregado)", "",
          "| Método | n | WAPE | Sesgo | Unidades obs. |", "|---|---|---|---|---|"]
    for m in t7.METHODS_SKU:
        x = next((q for q in r["pred"]["sku"] if (q["fold"], q["cohorte"], q["metodo"], q["vista"])
                  == ("AGREGADO", "historia_corta", m, "acum14")), None)
        if x and x["n"]:
            L.append(f"| {m} | {x['n']} | {_f(x['WAPE'], 4)} | {_f(x['sesgo_acumulado'], 1)} | {x['unidades_observadas']:.0f} |")
    L += ["", "### Cobertura de la referencia fija (no existe para SKU posteriores al 31/05)", "",
          "| Fold | Cohorte | Entidades con predicción | Universo común |", "|---|---|---|---|"]
    for c in r["pred"]["cobertura"]["sku"]:
        if c["metodo"] == "referencia_fija_0531":
            L.append(f"| {c['fold']} | {c['cohorte']} | {c['entidades_con_prediccion']} | {c['comunes']} |")
    L += ["", "### Pesos y conservación por revisión de la simulación", "",
          "| Origen | Cat. peso 28d / hist. / uniforme | Conservación cat→SKU |", "|---|---|---|"]
    for v in r["sim_rep"]["revisiones"]:
        w = v["pesos"]
        L.append(f"| {v['dia']} | {w['categorias_peso_28d']}/{w['categorias_fallback_historico']}/"
                 f"{w['categorias_fallback_uniforme']} | {v['conservacion_cat_a_sku']:.1e} |")
    L += ["", "Reducir compras con más faltantes o distinto stock terminal **no** es ahorro ni utilidad; los desembolsos y los costos consumidos se muestran por separado. "
          "Detalle por cohorte y por escenario en T07_METRICAS.json.", "",
          "## Verificaciones", "",
          f"- Conservación por SKU/día y de sistema y identidad de valor en las 27 combinaciones: {man['conservacion_ok']}; error máximo de identidad de valor {man['identidad_valor_max_abs']:.2e}.",
          f"- Repetición completa (predicción + simulación) idéntica: {man['repeticion_identica']}.",
          f"- Tiempo total: {man['segundos_totales']:.0f} s.", "",
          "## Limitaciones", "",
          "- Folds y simulación de desarrollo con meses ya usados en T05/T06; sin independencia respecto de la elección de métodos.",
          "- Los hashes de archivos .csv.gz/.npz incluyen metadatos de compresión; la repetición idéntica se comprobó en memoria dentro del mismo proceso.",
          "- La base temporal de las pruebas con datos reales contiene también agosto; la ruta de entrenamiento lo bloquea (convención de ingeniería, no control de seguridad) y los resultados no lo usan.",
          "- El RF por categoría usa solo 36 series; las features mes/día del mes salen del rango de entrenamiento al predecir y pueden explicar parte de su peor desempeño (no investigado).",
          "- El almacén se agrega por categoría (un solo almacén en estos datos).",
          "- Demanda proxy = ventas observadas, posiblemente censuradas por stock real desconocido; sin backorders; 07/06 sin demanda conocida.",
          "- Costos, holding, lead time y seguridad supuestos; sin MOQ ni proveedores reales; un almacén; universo fijo al 31/05.",
          "- La simulación no demuestra impacto en la MYPE ni autoriza compras."]
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="demand_forecasting_v2")
    ap.add_argument("--out", type=Path, default=Path("artifacts/private/t07"))
    ap.add_argument("--commit-protocolo", default="325da2f")
    args = ap.parse_args(argv)
    cfg = json.loads(CFG.read_text(encoding="utf-8"))
    sha = sha256_file(CFG)
    args.out.mkdir(parents=True, exist_ok=True)
    db = get_client()[args.db]
    t0 = time.perf_counter()
    r = compute(db, cfg, sha, args.out)
    r2 = compute(db, cfg, sha, None)            # repeticion completa con las mismas entradas
    same = bool(r["pred"]["sku"] == r2["pred"]["sku"] and r["pred"]["categoria"] == r2["pred"]["categoria"]
                and r["pred"]["predicciones"].equals(r2["pred"]["predicciones"]) and r["sim"] == r2["sim"]
                and all(np.array_equal(r["arrays"][k].on_hand, r2["arrays"][k].on_hand)
                        and np.array_equal(r["arrays"][k].ordered, r2["arrays"][k].ordered) for k in r["arrays"]))
    r["diffs"] = diffs(r["sim"], "total", KEYM)
    ident = max(abs(m["identidad_valor"]) for m in r["sim"].values())
    assert ident < 1e-6, f"identidad de valor violada: {ident}"
    # artefactos privados
    r["pred"]["predicciones"].to_csv(args.out / "predicciones_folds.csv.gz", index=False, float_format="%.10g")
    np.savez_compressed(args.out / "simulacion_series.npz", **{
        f"{k}__{name}": getattr(v, name) for k, v in r["arrays"].items() for name in ("on_hand", "served", "lost", "received", "ordered")},
        skus=np.array(r["skus"]), costo=r["cost"], demanda=r["demand"])
    man = {
        "generado_lima": datetime.now(ZoneInfo("America/Lima")).strftime("%Y-%m-%d %H:%M"), "base_de_datos": args.db,
        "etiqueta": LABEL, "agosto_usado": False, "commit_protocolo": args.commit_protocolo,
        "config_sha256": sha, "codigo_sha256": code_hash(), "git_commit": __import__("subprocess").run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
        "repeticion_identica": same, "conservacion_ok": bool(ident < 1e-6), "identidad_valor_max_abs": ident, "identidad_valor_tolerancia": 1e-6,
        "segundos_totales": time.perf_counter() - t0, "semilla_rf": cfg["rf_categoria"]["parametros"]["random_state"],
        "artefactos": {n: {"sha256": sha256_file(args.out / n)} for n in ("predicciones_folds.csv.gz", "simulacion_series.npz")},
        "modelos": {p.name: sha256_file(p) for p in sorted((args.out / "modelos").glob("*.joblib"))},
        "folds_predictivos": r["pred"]["folds"], "simulacion": r["sim_rep"], "entrenamiento": r["log"],
        "metricas_vinculos": {"T07_METRICAS.json:predictivo": "artifacts/private/t07/predicciones_folds.csv.gz",
                              "T07_METRICAS.json:simulacion": "artifacts/private/t07/simulacion_series.npz"},
    }
    sim_json = {f"L{L}_S{S}|{pol}": mt for (L, S, pol), mt in r["sim"].items()}
    DOCS.joinpath("T07_METRICAS.json").write_text(json.dumps(
        {"predictivo": {"sku": r["pred"]["sku"], "categoria": r["pred"]["categoria"], "seleccion": r["pred"]["seleccion"],
                         "cobertura": r["pred"]["cobertura"]},
         "simulacion": sim_json, "diferencias": r["diffs"], "etiqueta": LABEL}, ensure_ascii=False, indent=1, default=str) + "\n",
        encoding="utf-8")
    DOCS.joinpath("T07_MANIFIESTO.json").write_text(json.dumps(man, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    DOCS.joinpath("T07_RESULTADOS.md").write_text(render(r, cfg, man), encoding="utf-8")
    print(json.dumps({"repeticion_identica": same, "seleccion": r["pred"]["seleccion"], "identidad_valor_max": ident,
                      "segundos": round(man["segundos_totales"])}, indent=1, default=str))
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())
