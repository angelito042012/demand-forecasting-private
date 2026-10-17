"""T06: entrenamiento de modelos globales por nivel/fold y seleccion preregistrada.

Reutiliza run_fold/evaluate_level de T05 para que targets, cohortes, mascaras y cobertura sean
identicos; los modelos solo anaden columnas de prediccion emitidas al origen del fold.
"""
from __future__ import annotations

import time
from datetime import date
from pathlib import Path

import numpy as np

from pipeline.data.catalog import lookup

from .features import SeriesContext, Vocab, build_training, training_origins
from .models import fit_bundle, predict_block, save_bundle
from .t05 import _wide

ML_MODELS = ("random_forest", "xgboost")
BASELINES = ("cero", "ultimo_dia", "naive_semanal", "promedio_28")


def build_context(level: str, index: list, values: np.ndarray, info: dict) -> tuple[SeriesContext, Vocab]:
    train, cal = info["train"], info["cal"]
    start = date.fromisoformat(cal[0])
    almacenes = sorted(set(info["pairs"]["almacen"]))
    if level == "sku":
        cidx, cvals = _wide(info["cats"], "categoria_corte", "cantidad_base_suma_heterogenea", cal)
        pos = {c: i for i, c in enumerate(cidx)}
        cats = [lookup(train.catalog, sku) for sku, _ in index]
        vocab = Vocab.fit(train.catalog.values(), almacenes)
        cat_values = np.vstack([cvals[pos[c]] if c in pos else np.full(values.shape[1], np.nan) for c in cats])
        alm_codes = np.array([vocab.alm(a) for _, a in index])
    else:
        cats = list(index)
        vocab = Vocab.fit(index, almacenes)
        cat_values = values
        alm_codes = np.zeros(len(index), dtype=int)
    cat_codes = np.array([vocab.cat(c) for c in cats])
    return SeriesContext(values, start, cat_codes, alm_codes, cat_values, vocab.id()), vocab


def make_extras_fn(cfg6: dict, config_sha256: str, models_dir: Path, log: list):
    """Devuelve la funcion que run_fold llama por nivel: entrena RF y XGB con el fold y predice al origen."""
    models_dir.mkdir(parents=True, exist_ok=True)

    def extras(level, index, values, info) -> dict:
        ctx, vocab = build_context(level, index, values, info)
        tr = cfg6["origenes_entrenamiento"]
        origins = training_origins(values.shape[1], step=tr["paso_dias"], min_origin=tr["origen_minimo_indice"])
        t0 = time.perf_counter()
        X, y, _ = build_training(ctx, origins)
        t_feat = time.perf_counter() - t0
        out = {}
        for name in ML_MODELS:
            bundle = fit_bundle(name, cfg6["modelos"][name]["parametros"], X, y, nivel=level,
                                corte=info["fold"]["corte"], vocab=vocab, config_sha256=config_sha256,
                                inicio=info["cal"][0], meta={"origenes": len(origins), "paso_dias": tr["paso_dias"],
                                                             "segundos_features": round(t_feat, 2)})
            t1 = time.perf_counter()
            pred, clipped = predict_block(bundle, ctx)
            bundle.entrenamiento["segundos_prediccion"] = round(time.perf_counter() - t1, 2)
            bundle.entrenamiento["negativos_recortados"] = clipped
            save_bundle(bundle, models_dir / f"{info['fold']['id']}_{level}_{name}.joblib")
            log.append({"fold": info["fold"]["id"], "nivel": level, "modelo": name, **bundle.entrenamiento})
            out[name] = pred
        return out

    return extras


def _get(records, fold, nivel, metodo, vista, key="WAPE", cohorte="primaria", universo="comun"):
    for r in records:
        if (r["fold"], r["nivel"], r["metodo"], r["vista"], r["cohorte"], r["universo"]) == (
                fold, nivel, metodo, vista, cohorte, universo):
            return r.get(key)
    return None


def select_models(records: list, cfg6: dict, folds: list[str]) -> dict:
    """Regla preregistrada (docs/T06_PROTOCOLO.md). No se declara ganador si no se cumple todo."""
    rule = cfg6["seleccion"]
    out = {}
    for nivel in ("sku", "categoria"):
        vista = rule[nivel]["vista"]
        base = {m: _get(records, "AGREGADO", nivel, m, vista) for m in BASELINES}
        best_ref = min((m for m in BASELINES if base[m] is not None), key=lambda m: base[m])
        best_nonzero = min((m for m in BASELINES if m != "cero" and base[m] is not None), key=lambda m: base[m])
        ml = {}
        for m in ML_MODELS:
            w = _get(records, "AGREGADO", nivel, m, vista)
            sesgo = _get(records, "AGREGADO", nivel, m, vista, key="sesgo_acumulado")
            obs = _get(records, "AGREGADO", nivel, m, vista, key="unidades_observadas")
            fav = [f for f in folds if (_get(records, f, nivel, m, vista) is not None
                                        and _get(records, f, nivel, best_ref, vista) is not None
                                        and _get(records, f, nivel, m, vista) < _get(records, f, nivel, best_ref, vista))]
            rel = None if w is None else (base[best_ref] - w) / base[best_ref]
            bias_rel = None if not obs else sesgo / obs
            ok = (w is not None and rel >= rule["mejora_relativa_minima"] and len(fav) >= rule["folds_favorables_minimos"]
                  and abs(bias_rel) <= rule["sesgo_relativo_maximo_abs"])
            ml[m] = {"WAPE": w, "mejora_relativa_vs_mejor_referencia": rel, "folds_favorables": fav,
                     "n_folds_favorables": len(fav), "sesgo_relativo": bias_rel, "cumple_regla": bool(ok)}
        passing = [m for m in ML_MODELS if ml[m]["cumple_regla"]]
        winner = min(passing, key=lambda m: ml[m]["WAPE"]) if passing else None
        out[nivel] = {"vista_primaria": vista, "wape_baselines": base, "mejor_referencia": best_ref,
                      "mejor_referencia_no_nula": best_nonzero, "ml": ml, "ganador_ml": winner,
                      "propuesta_para_simulacion": winner or best_nonzero,
                      "nota": ("ML supera la regla preregistrada en desarrollo" if winner else
                               "sin ventaja estable de ML en desarrollo: se propone el baseline no nulo mas solido; "
                               "el control cero se mantiene solo como referencia")}
    return out
