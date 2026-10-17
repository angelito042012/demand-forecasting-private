"""T07: pronostico RF por categoria (h=1..21) distribuido a SKU, promedio_28, costos y evaluacion predictiva.

Todas las funciones reciben matrices TRUNCADAS en el origen (ultima columna = origen): lo posterior
no existe para ellas. La categoria de cada fila y el universo vienen fijados por el llamador.
"""
from __future__ import annotations

import warnings
from datetime import date, timedelta

import numpy as np

from .features import (
    FEATURE_VERSION,
    SeriesContext,
    Vocab,
    build_training,
    training_origins,
)
from .metrics import add_stats, finalize, new_stats, stats
from .models import fit_bundle, predict_block

HORIZON = 21
METHODS_SKU = ("cero", "promedio_28", "referencia_fija_0531", "rf_distribuido")
METHODS_CAT = ("cero", "promedio_28", "rf_categoria")


def aggregate_categories(values: np.ndarray, cats: list[str]) -> tuple[list[str], np.ndarray]:
    """Serie diaria por categoria: suma de las filas de la categoria; NaN si TODAS sus filas son NaN ese dia
    (antes de su primera venta, dia enmascarado o sin registros)."""
    names = sorted(set(cats))
    pos = {c: i for i, c in enumerate(names)}
    out = np.full((len(names), values.shape[1]), np.nan)
    idx = np.array([pos[c] for c in cats])
    for k in range(len(names)):
        block = values[idx == k]
        anyv = (~np.isnan(block)).any(axis=0)
        out[k] = np.where(anyv, np.nansum(block, axis=0), np.nan)
    return names, out


def mean_window(values: np.ndarray, window: int = 28) -> np.ndarray:
    """Media de observaciones utilizables de los ultimos `window` dias (NaN si no hay ninguna)."""
    win = values[:, max(0, values.shape[1] - window):]
    usable = (~np.isnan(win)).sum(axis=1)
    return np.where(usable > 0, np.nansum(win, axis=1) / np.maximum(usable, 1), np.nan)


def allocation_weights(values: np.ndarray, cats: list[str], names: list[str]) -> tuple[np.ndarray, dict]:
    """Pesos SKU dentro de su categoria: unidades positivas de 28 dias; fallback historico; fallback uniforme."""
    n, T = values.shape
    pos = np.nan_to_num(values, nan=0.0).clip(min=0)
    w28 = pos[:, max(0, T - 28):].sum(axis=1)
    hist = pos.sum(axis=1)
    idx = np.array([names.index(c) for c in cats])
    w = np.zeros(n)
    counts = {"categorias_peso_28d": 0, "categorias_fallback_historico": 0, "categorias_fallback_uniforme": 0}
    for k in range(len(names)):
        m = idx == k
        if w28[m].sum() > 0:
            w[m] = w28[m] / w28[m].sum()
            counts["categorias_peso_28d"] += 1
        elif hist[m].sum() > 0:
            w[m] = hist[m] / hist[m].sum()
            counts["categorias_fallback_historico"] += 1
        else:
            w[m] = 1.0 / m.sum()
            counts["categorias_fallback_uniforme"] += 1
    return w, counts


def forecast_origin_t07(values: np.ndarray, start: date, cats: list[str], almacenes: list[str], rf_cfg: dict,
                        config_sha: str, horizon: int = HORIZON) -> dict:
    """Pronosticos al origen = ultima columna de `values` (n SKU x T). Entrena un RF global por categoria
    con etiquetas <= origen y distribuye a SKU. No lee nada posterior al origen."""
    T = values.shape[1]
    names, cvals = aggregate_categories(values, cats)
    vocab = Vocab.fit(names, almacenes)
    ctx = SeriesContext(cvals, start, np.array([vocab.cat(c) for c in names]),
                        np.zeros(len(names), dtype=int), cvals, vocab.id())
    tr = rf_cfg["origenes_entrenamiento"]
    origins = training_origins(T, step=tr["paso_dias"], min_origin=tr["origen_minimo_indice"], horizon=horizon)
    X, y, _ = build_training(ctx, origins, horizon)
    corte = (start + timedelta(days=T - 1)).isoformat()
    bundle = fit_bundle("random_forest", rf_cfg["parametros"], X, y, nivel="categoria", corte=corte, vocab=vocab,
                        config_sha256=config_sha, inicio=start.isoformat(), meta={"origenes": len(origins)},
                        horizonte=horizon)
    cat_pred, clipped = predict_block(bundle, ctx, horizon)            # (k, horizon); NaN si la categoria no tiene historia
    w, wcounts = allocation_weights(values, cats, names)
    idx = np.array([names.index(c) for c in cats])
    dist = np.where(np.isnan(cat_pred[idx]), np.nan, w[:, None] * cat_pred[idx])
    # conservacion categoria -> SKU
    err = 0.0
    for k in range(len(names)):
        if not np.isnan(cat_pred[k]).any():
            err = max(err, float(np.abs(dist[idx == k].sum(axis=0) - cat_pred[k]).max()))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        mean28 = mean_window(values)
        cat_mean28 = mean_window(cvals)
    return {"names": names, "cat_values": cvals, "cat_pred": cat_pred, "rf_dist": dist, "weights": w,
            "weight_counts": wcounts, "mean28": mean28, "cat_mean28": cat_mean28,
            "conservacion_max_abs_error": err, "negativos_recortados": clipped,
            "entrenamiento": {**bundle.entrenamiento, "origen": corte, "feature_version": FEATURE_VERSION},
            "bundle": bundle, "ctx": ctx}


def unit_costs(sales_rows, skus: list[str], cat_of: dict, factor: float = 0.65) -> tuple[np.ndarray, dict]:
    """Costo unitario supuesto = factor x mediana de precio base positivo (PRECIO/EQUIVALENCIA) conocido en las
    filas dadas (solo <= 31/05). Fallbacks: mediana de medianas de la categoria; luego global. Cuenta fallbacks."""
    by_sku: dict = {}
    for r in sales_rows:
        p, eq = r.get("precio_unitario_original"), r.get("equivalencia")
        if p is None or not eq or eq <= 0:
            continue
        price = float(p.to_decimal()) / float(eq)
        if price > 0:
            by_sku.setdefault(r["sku"], []).append(price)
    med = {s: float(np.median(v)) for s, v in by_sku.items()}
    by_cat: dict = {}
    for s, m in med.items():
        by_cat.setdefault(cat_of.get(s), []).append(m)
    cat_med = {c: float(np.median(v)) for c, v in by_cat.items()}
    glob = float(np.median(list(med.values()))) if med else 0.0
    out, counts = np.zeros(len(skus)), {"propio": 0, "categoria": 0, "global": 0}
    for i, s in enumerate(skus):
        if s in med:
            out[i], counts["propio"] = med[s], counts["propio"] + 1
        elif cat_of.get(s) in cat_med:
            out[i], counts["categoria"] = cat_med[cat_of[s]], counts["categoria"] + 1
        else:
            out[i], counts["global"] = glob, counts["global"] + 1
    return out * factor, counts


# ----------------------------------------------------------------- evaluacion predictiva
def _cum(a: np.ndarray, p: np.ndarray, eval_days: np.ndarray, H: int):
    ev = eval_days[:H]
    if not ev.any():
        return None
    return a[:, :H][:, ev].sum(axis=1), p[:, :H][:, ev].sum(axis=1)


def eval_fold_predictions(actual: np.ndarray, preds: dict, eval_days: np.ndarray, masks: dict,
                          horizons=(10, 14, 21), core=None) -> dict:
    """Estadisticos por cohorte/metodo/vista. Universo comun = entidades donde existen TODOS los metodos `core`
    (por defecto todos). Un metodo no-core (p. ej. referencia fija, que no existe para SKU posteriores al 31/05)
    se evalua en el comun ∩ su propia disponibilidad y su cobertura se informa."""
    core = tuple(preds) if core is None else tuple(core)
    out = {}
    for cohort, mask in masks.items():
        ok_all = mask.copy()
        for m in core:
            ok_all &= ~np.isnan(preds[m]).any(axis=1)
        out[(cohort, "cobertura")] = {"entidades": int(mask.sum()), "comunes": int(ok_all.sum()),
                                      "dias_evaluables_21": int(eval_days.sum())}
        for m, p in preds.items():
            ok = ok_all & ~np.isnan(p).any(axis=1)
            if m not in core:
                out[(cohort, m, "cobertura")] = {"entidades_con_prediccion": int(ok.sum()), "comunes": int(ok_all.sum())}
            rows = ok[:, None] & eval_days[None, :]
            out[(cohort, m, "diaria")] = stats(actual[rows], p[rows]) if rows.any() else new_stats()
            for H in horizons:
                c = _cum(actual[ok], p[ok], eval_days, H)
                out[(cohort, m, f"acum{H}")] = stats(*c) if c is not None else new_stats()
    return out


def summarize(stats_by_fold: dict, folds: list[str], r2_min_n: int = 30) -> list[dict]:
    """Registros finalizados por fold y agregados (suma de estadisticos; bloques solapados, no unidades unicas)."""
    recs, pooled = [], {}
    for f in folds:
        for key, st in stats_by_fold[f].items():
            if "cobertura" in key:
                continue
            recs.append({"fold": f, "cohorte": key[0], "metodo": key[1], "vista": key[2], **finalize(st, r2_min_n=r2_min_n)})
            pooled[key] = add_stats(pooled[key], st) if key in pooled else dict(st)
    for key, st in pooled.items():
        recs.append({"fold": "AGREGADO", "cohorte": key[0], "metodo": key[1], "vista": key[2], **finalize(st, r2_min_n=r2_min_n)})
    return recs


def select_candidate(recs: list[dict], rule: dict, folds: list[str]) -> dict:
    c = rule["criterio_primario"]
    view = f"acum{c['H']}"

    def g(fold, m, key="WAPE"):
        r = next((x for x in recs if (x["fold"], x["cohorte"], x["metodo"], x["vista"]) == (fold, c["cohorte"], m, view)), None)
        return None if r is None else r.get(key)

    cand, ref = "rf_distribuido", rule["comparador"]
    wc, wr = g("AGREGADO", cand), g("AGREGADO", ref)
    rel = None if (wc is None or not wr) else (wr - wc) / wr
    fav = [f for f in folds if g(f, cand) is not None and g(f, ref) is not None and g(f, cand) < g(f, ref)]
    obs, bias = g("AGREGADO", cand, "unidades_observadas"), g("AGREGADO", cand, "sesgo_acumulado")
    brel = None if not obs else bias / obs
    ok = (rel is not None and brel is not None and rel >= rule["mejora_relativa_minima"]
          and len(fav) >= rule["folds_favorables_minimos"] and abs(brel) <= rule["sesgo_relativo_maximo_abs"])
    return {"vista": view, "WAPE_candidato": wc, "WAPE_comparador": wr, "mejora_relativa": rel, "folds_favorables": fav,
            "sesgo_relativo": brel, "cumple_regla": bool(ok) if rel is not None else None,
            "nota": "no evaluable (denominador cero)" if rel is None else
            ("cumple la regla provisional en desarrollo" if ok else "no cumple la regla provisional")}
