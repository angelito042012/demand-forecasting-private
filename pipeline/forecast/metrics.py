"""Estadisticos suficientes y metricas de T05. Los agregados se obtienen SUMANDO estadisticos
(ponderacion por conteos/unidades), nunca promediando porcentajes."""
from __future__ import annotations

import math

import numpy as np

KEYS = ("n", "sum_a", "sum_a2", "sum_p", "sum_abs", "sum_sq", "n_under", "n_over", "n_exact",
        "n_pos", "sum_ape", "n_zero")


def new_stats() -> dict:
    return dict.fromkeys(KEYS, 0.0)


def stats(actual, pred) -> dict:
    a, p = np.asarray(actual, float).ravel(), np.asarray(pred, float).ravel()
    if np.isnan(a).any() or np.isnan(p).any():
        raise ValueError("stats exige valores finitos; filtrar no disponibles/no evaluables antes")
    e = p - a
    pos = a > 0
    return {"n": float(a.size), "sum_a": float(a.sum()), "sum_a2": float((a * a).sum()),
            "sum_p": float(p.sum()), "sum_abs": float(np.abs(e).sum()), "sum_sq": float((e * e).sum()),
            "n_under": float((p < a).sum()), "n_over": float((p > a).sum()), "n_exact": float((p == a).sum()),
            "n_pos": float(pos.sum()), "sum_ape": float((np.abs(e[pos]) / a[pos]).sum()),
            "n_zero": float((~pos).sum())}


def add_stats(*items: dict) -> dict:
    out = new_stats()
    for it in items:
        for k in KEYS:
            out[k] += it[k]
    return out


def finalize(s: dict, *, r2_min_n: int = 30) -> dict:
    n = s["n"]
    if n == 0:
        return {"n": 0}
    sst = s["sum_a2"] - s["sum_a"] ** 2 / n
    r2_ok = n >= r2_min_n and sst > 1e-12
    return {
        "n": int(n), "unidades_observadas": s["sum_a"], "unidades_predichas": s["sum_p"],
        "MAE": s["sum_abs"] / n, "RMSE": math.sqrt(s["sum_sq"] / n),
        "WAPE": s["sum_abs"] / s["sum_a"] if s["sum_a"] > 0 else None,
        "sesgo_acumulado": s["sum_p"] - s["sum_a"],
        "prop_subpronostico": s["n_under"] / n, "prop_sobrepronostico": s["n_over"] / n,
        "prop_exacto": s["n_exact"] / n,
        "MAPE": s["sum_ape"] / s["n_pos"] if s["n_pos"] > 0 else None,
        "MAPE_cobertura_reales_positivos": s["n_pos"] / n, "MAPE_ceros_excluidos": int(s["n_zero"]),
        "R2": (1 - s["sum_sq"] / sst) if r2_ok else None,
        "R2_nota": None if r2_ok else "indefinido (n insuficiente o varianza nula)",
    }
