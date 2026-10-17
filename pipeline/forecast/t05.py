"""Orquestacion de T05: folds temporales, cohortes sin fuga, evaluacion de baselines.

Todo el conocimiento de un fold (ventas, fuentes, calendario, catalogo, series, poblacion)
sale de load_fold con el corte del fold. Solo marzo-julio: load_fold rechaza cortes de agosto
y este modulo nunca llama a load_final_test_sales.
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from pipeline.data import daily_series as ds
from pipeline.data.catalog import lookup
from pipeline.data.training_access import load_fold

from .baselines import METHODS, forecast_block, primary_mask
from .metrics import add_stats, finalize, new_stats, stats

COHORTS = ("primaria", "historia_corta")
LEVELS = ("sku", "categoria")


def _wide(frame: pd.DataFrame, keys, value: str, calendar: list[str]) -> tuple[list, np.ndarray]:
    wide = frame.pivot(index=keys, columns="fecha", values=value).reindex(columns=calendar)
    return list(wide.index), wide.to_numpy(dtype=float)


def _actual(index: list, sales: pd.DataFrame, key_cols: list[str], days: list[str]) -> tuple[np.ndarray, pd.DataFrame]:
    """Matriz real (n, H) para las entidades conocidas (0 si no vendio) y ventas de entidades no conocidas."""
    pos = {k: i for i, k in enumerate(index)}
    grouped = sales.groupby(key_cols + ["fecha"], as_index=False)["qty"].sum()
    out = np.zeros((len(index), len(days)))
    col = {d: j for j, d in enumerate(days)}
    unknown = []
    for row in grouped.itertuples(index=False):
        k = tuple(row[:-2]) if len(key_cols) > 1 else row[0]
        if k in pos:
            out[pos[k], col[row[-2]]] += row[-1]
        else:
            unknown.append(row)
    return out, pd.DataFrame(unknown, columns=key_cols + ["fecha", "qty"]) if unknown else grouped.iloc[0:0]


def evaluate_level(level, index, values, actual, eval_days, cfg, extra=None) -> dict:
    """Estadisticos y cobertura por cohorte/universo/metodo/vista para un nivel de un fold."""
    block = forecast_block(values, horizon=cfg["horizonte_dias"], window=cfg["ventana_promedio_dias"])
    cp = cfg["cohorte_primaria"]
    prim = primary_mask(block, min_history=cp["historia_minima_dias"],
                        min_usable=cp["observaciones_utilizables_minimas_en_28"])
    known = block.history_days > 0
    out: dict = {"stats": {}, "cobertura": {}, "n_entidades": {}, "naive_fallback_filas": {}, "antiguedad_ultimo_dia": {}}
    preds = {**block.forecasts, **(extra or {})}   # extra: predicciones adicionales (T06) sobre los mismos targets
    methods = tuple(preds)
    for cohort, mask in (("primaria", prim & known), ("historia_corta", known & ~prim)):
        out["n_entidades"][cohort] = int(mask.sum())
        rows = mask[:, None] & eval_days[None, :]
        avail = {m: rows & ~np.isnan(preds[m]) for m in methods}
        common = rows.copy()
        for m in methods:
            common &= ~np.isnan(preds[m])
        out["cobertura"][cohort] = {"filas_objetivo": int(rows.sum()), "filas_comunes": int(common.sum()),
                                    **{m: int(avail[m].sum()) for m in methods}}
        fb = block.naive_fallback & rows
        out["naive_fallback_filas"][cohort] = int(fb.sum())
        ages = block.last_day_age[mask & ~np.isnan(block.last_day_age)]
        out["antiguedad_ultimo_dia"][cohort] = ({"mediana": float(np.median(ages)), "p90": float(np.quantile(ages, .9)),
                                                 "max": float(ages.max())} if ages.size else None)
        for universe, sel in (("propio", avail), ("comun", {m: common for m in methods})):
            for m in methods:
                r = sel[m]
                out["stats"][(cohort, universe, m, "diaria")] = (
                    stats(actual[r], preds[m][r]) if r.any() else new_stats())
                # cantidad acumulada del bloque: solo dias evaluables; entidad sin prediccion completa no entra
                ev = eval_days[None, :] & np.ones_like(r)
                ok_ent = mask & (r | ~ev).all(axis=1) & (ev.sum(axis=1) > 0)
                if ok_ent.any():
                    a_sum = np.where(ev, actual, 0).sum(axis=1)[ok_ent]
                    p_sum = np.where(ev, preds[m], 0).sum(axis=1)[ok_ent]
                    out["stats"][(cohort, universe, m, "bloque7")] = stats(a_sum, p_sum)
                else:
                    out["stats"][(cohort, universe, m, "bloque7")] = new_stats()
    out["_block"] = block
    out["_preds"] = preds
    out["metodos"] = methods
    out["_primary"] = prim
    return out


def run_fold(db, fold_cfg: dict, cfg: dict, *, required_months=None, extras_fn=None) -> dict:
    cut = date.fromisoformat(fold_cfg["corte"])
    v0, v1 = (date.fromisoformat(x) for x in fold_cfg["validacion"])
    fold = load_fold(db, cut, v1, start=date.fromisoformat(cfg["inicio_entrenamiento"]),
                     required_months=required_months)
    train = fold.train
    if fold.validation_calendar[0] != v0:
        raise ValueError("la ventana de validacion no empieza el dia siguiente al corte")
    cal = [d.isoformat() for d in train.calendar]
    days = [d.isoformat() for d in fold.validation_calendar]
    vs = pd.DataFrame([(r["fecha"], r["sku"], r["almacen"], float(r["cantidad_base"])) for r in fold.validation_sales],
                      columns=["fecha", "sku", "almacen", "qty"])
    covered = set(vs["fecha"])
    masked = {d.isoformat() for d in fold.validation_excluded_days}
    eval_days = np.array([(d not in masked) and (d in covered) for d in days])
    pairs = ds.pair_daily(train)
    cats = ds.category_daily(pairs)
    res: dict = {"corte": fold_cfg["corte"], "fingerprint": train.fingerprint, "dias_validacion": days,
                 "dias_evaluables": int(eval_days.sum()),
                 "dias_no_evaluables": [d for d, e in zip(days, eval_days, strict=True) if not e],
                 "fuentes": list(fold.train.sources.manifest), "niveles": {}, "predicciones": []}
    # --- SKU
    idx, vals = _wide(pairs, ["sku", "almacen"], "cantidad_base", cal)
    act, new = _actual(idx, vs, ["sku", "almacen"], days)
    info = {"train": train, "pairs": pairs, "cats": cats, "cal": cal, "fold": fold_cfg}
    extra = extras_fn("sku", idx, vals, info) if extras_fn else None
    ev = evaluate_level("sku", idx, vals, act, eval_days, cfg, extra)
    new_ev = new[new["fecha"].isin([d for d, e in zip(days, eval_days, strict=True) if e])]
    ev["nuevos_en_validacion"] = {"entidades": int(new[["sku", "almacen"]].drop_duplicates().shape[0]),
                                  "unidades_evaluables": float(new_ev["qty"].sum()),
                                  "filas_objetivo_sin_prediccion": int(new[["sku", "almacen"]].drop_duplicates().shape[0]
                                                                       * eval_days.sum())}
    res["niveles"]["sku"] = ev
    res["predicciones"] += _prediction_rows("sku", idx, ev, act, days, eval_days)
    # --- categoria (definida al corte; SKU nuevo => DESCONOCIDA)
    vs_c = vs.assign(categoria_corte=[lookup(train.catalog, s) for s in vs["sku"]])
    cidx, cvals = _wide(cats, "categoria_corte", "cantidad_base_suma_heterogenea", cal)
    cact, cnew = _actual(cidx, vs_c, ["categoria_corte"], days)
    cextra = extras_fn("categoria", cidx, cvals, info) if extras_fn else None
    cev = evaluate_level("categoria", cidx, cvals, cact, eval_days, cfg, cextra)
    cnew_ev = cnew[cnew["fecha"].isin([d for d, e in zip(days, eval_days, strict=True) if e])]
    cev["nuevos_en_validacion"] = {"categorias": sorted(set(cnew["categoria_corte"])),
                                   "unidades_evaluables": float(cnew_ev["qty"].sum())}
    res["niveles"]["categoria"] = cev
    res["predicciones"] += _prediction_rows("categoria", cidx, cev, cact, days, eval_days)
    return res


def _prediction_rows(level, index, ev, actual, days, eval_days) -> list:
    block, prim = ev["_block"], ev["_primary"]
    rows = []
    for i, key in enumerate(index):
        if block.history_days[i] == 0:
            continue
        ent = "|".join(map(str, key)) if isinstance(key, tuple) else str(key)
        cohort = "primaria" if prim[i] else "historia_corta"
        for h, d in enumerate(days):
            rows.append((level, ent, cohort, d, h + 1, bool(eval_days[h]), actual[i, h],
                         *(ev["_preds"][m][i, h] for m in ev["metodos"]), bool(block.naive_fallback[i, h]),
                         block.last_day_age[i], int(block.history_days[i])))
    return rows


PRED_COLUMNS = ["nivel", "entidad", "cohorte", "fecha", "h", "evaluable", "real", *[f"pred_{m}" for m in METHODS],
                "naive_fallback", "antiguedad_ultimo_dia", "historia_dias"]


def pred_columns(methods) -> list:
    return ["nivel", "entidad", "cohorte", "fecha", "h", "evaluable", "real", *[f"pred_{m}" for m in methods],
            "naive_fallback", "antiguedad_ultimo_dia", "historia_dias"]


def run_all(db, cfg: dict, *, required_months=None, extras_fn=None, only_folds=None) -> dict:
    folds = {f["id"]: run_fold(db, f, cfg, required_months=required_months, extras_fn=extras_fn)
             for f in cfg["folds"] if only_folds is None or f["id"] in only_folds}
    methods = next(iter(folds.values()))["niveles"]["sku"]["metodos"]
    preds = pd.DataFrame([[fid, *r] for fid, fr in folds.items() for r in fr["predicciones"]],
                         columns=["fold", *pred_columns(methods)])
    records = []
    for lv in LEVELS:
        pooled: dict = {}
        for fid, fr in folds.items():
            for key, st in fr["niveles"][lv]["stats"].items():
                records.append({"fold": fid, "nivel": lv, "cohorte": key[0], "universo": key[1], "metodo": key[2],
                                "vista": key[3], **finalize(st, r2_min_n=cfg["r2_minimo_n"])})
                pooled[key] = add_stats(pooled[key], st) if key in pooled else dict(st)
        for key, st in pooled.items():
            records.append({"fold": "AGREGADO", "nivel": lv, "cohorte": key[0], "universo": key[1], "metodo": key[2],
                            "vista": key[3], **finalize(st, r2_min_n=cfg["r2_minimo_n"])})
    coverage = [{"fold": fid, "nivel": lv, "cohorte": c, "n_entidades": fr["niveles"][lv]["n_entidades"][c],
                 **fr["niveles"][lv]["cobertura"][c], "naive_fallback_filas": fr["niveles"][lv]["naive_fallback_filas"][c],
                 "antiguedad_ultimo_dia": fr["niveles"][lv]["antiguedad_ultimo_dia"][c]}
                for fid, fr in folds.items() for lv in LEVELS for c in COHORTS]
    return {"folds": folds, "predicciones": preds, "metricas": records, "cobertura": coverage,
            "referencia_t06": select_reference(records, cfg)}


def select_reference(records: list, cfg: dict) -> dict:
    rule = cfg["referencia_t06"]
    wape = {r["metodo"]: r["WAPE"] for r in records
            if r["fold"] == "AGREGADO" and r["nivel"] == "sku" and r["cohorte"] == "primaria"
            and r["universo"] == "comun" and r["vista"] == "diaria" and r["metodo"] in rule["candidatos"]}
    if len(wape) != len(rule["candidatos"]) or any(v is None for v in wape.values()):
        return {"seleccion": None, "motivo": "WAPE no disponible para todos los candidatos", "wape": wape}
    best = min(wape.values())
    near = [m for m in rule["desempate_orden"] if wape[m] <= best * (1 + rule["umbral_empate_relativo"])]
    return {"seleccion": near[0], "wape": wape, "empatados_dentro_del_umbral": near,
            "control_cero_wape": next((r["WAPE"] for r in records if r["fold"] == "AGREGADO" and r["nivel"] == "sku"
                                       and r["cohorte"] == "primaria" and r["universo"] == "comun"
                                       and r["vista"] == "diaria" and r["metodo"] == "cero"), None)}
