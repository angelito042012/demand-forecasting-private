"""T12: auditoria SEPARADA, sin reentrenar y sin MongoDB.

Recomputa con numpy plano (no con `metrics.py`/`t07.py`) las metricas predictivas primarias a partir de las predicciones
SELLADAS y los reales guardados, y no desde el JSON de metricas; cuenta universo/cobertura, revisa el orden temporal
(sello anterior a la lectura de agosto), el contenido de las ventas minimas de agosto y re-verifica todos los balances
de las 27 combinaciones de la simulacion desde sus arreglos.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from pipeline.final import core
from pipeline.final.runner import StateFile, _load_npz, sha_bytes

POLICIES = core.POLICIES
TOL = 1e-9


def _close(a, b, tol=TOL) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return math.isclose(float(a), float(b), rel_tol=tol, abs_tol=tol)


def _recompute_stats(a: np.ndarray, p: np.ndarray) -> dict:
    e = p - a
    pos = a > 0
    sa = float(a.sum())
    return {"n": int(a.size), "unidades_observadas": sa, "MAE": float(np.abs(e).mean()) if a.size else None,
            "RMSE": float(np.sqrt((e * e).mean())) if a.size else None,
            "WAPE": float(np.abs(e).sum() / sa) if sa > 0 else None, "sesgo_acumulado": float(p.sum() - sa),
            "MAPE": float((np.abs(e[pos]) / a[pos]).mean()) if pos.any() else None,
            "prop_sub": float((p < a).mean()) if a.size else None, "prop_sobre": float((p > a).mean()) if a.size else None}


def audit_predictive(out: Path, pred_json: dict) -> dict:
    sealed = _load_npz(out / "preparacion" / "predicciones_fijas.npz")
    real = _load_npz(out / "reales_bloque.npz")
    act, ev = real["act"], real["eval_days"].astype(bool)
    prim, known = sealed["sku_primaria"], sealed["sku_conocido"]
    methods = {"cero": sealed["pred_sku_cero"], "promedio_28": sealed["pred_sku_promedio_28"],
               "rf_distribuido": sealed["pred_sku_rf_distribuido"]}
    checks, detail = [], {}
    for cohort, mask in (("primaria", prim & known), ("historia_corta", known & ~prim)):
        common = mask.copy()
        for p in methods.values():
            common &= ~np.isnan(p).any(axis=1)
        detail[f"universo_{cohort}"] = {"entidades": int(mask.sum()), "comunes": int(common.sum()),
                                        "excluidas_por_no_disponible": int(mask.sum() - common.sum())}
        for name, p in methods.items():
            for H in (10, 14, 21):
                cols = ev[:H]
                if not cols.any() or not common.any():
                    continue
                a = act[common][:, :H][:, cols].sum(axis=1)
                q = p[common][:, :H][:, cols].sum(axis=1)
                mine = _recompute_stats(a, q)
                stored = next((r for r in pred_json["sku"] if (r["cohorte"], r["metodo"], r["vista"])
                               == (cohort, name, f"acum{H}")), None)
                ok = stored is not None and all(_close(mine[k], stored.get(k)) for k in ("WAPE", "MAE", "RMSE", "sesgo_acumulado"))
                checks.append({"cohorte": cohort, "metodo": name, "vista": f"acum{H}", "ok": bool(ok), "WAPE_recomputado": mine["WAPE"],
                               "n": mine["n"]})
            rows = common[:, None] & ev[None, :]
            if rows.any():
                mine = _recompute_stats(act[rows], p[rows])
                stored = next((r for r in pred_json["sku"] if (r["cohorte"], r["metodo"], r["vista"])
                               == (cohort, name, "diaria")), None)
                checks.append({"cohorte": cohort, "metodo": name, "vista": "diaria",
                               "ok": bool(stored is not None and _close(mine["WAPE"], stored.get("WAPE"))
                                          and _close(mine["MAE"], stored.get("MAE"))), "WAPE_recomputado": mine["WAPE"], "n": mine["n"]})
    # categorias = suma SKU y conservacion RF categoria -> SKU
    cidx = real["cat_idx"]
    names = list(sealed["cat_names"])
    sum_sku = np.zeros((len(names), core.HORIZON))
    np.add.at(sum_sku, cidx, np.nan_to_num(sealed["pred_sku_promedio_28"]))
    cat_ok = bool(np.allclose(sum_sku, sealed["pred_cat_promedio_28_suma_sku"], rtol=0, atol=1e-9))
    rf_sum = np.zeros((len(names), core.HORIZON))
    np.add.at(rf_sum, cidx, np.nan_to_num(sealed["pred_sku_rf_distribuido"]))
    valid = ~np.isnan(sealed["pred_cat_rf_categoria"]).any(axis=1)
    cons = float(np.abs(rf_sum[valid] - sealed["pred_cat_rf_categoria"][valid]).max()) if valid.any() else 0.0
    cact = np.zeros((len(names), core.HORIZON))
    np.add.at(cact, cidx, act)
    return {"checks": checks, "ok": bool(all(c["ok"] for c in checks) and cat_ok and cons < 1e-6),
            "categorias_igual_suma_sku": cat_ok, "conservacion_rf_categoria_a_sku_max_abs": cons,
            "reales_categoria_igual_suma_sku": bool(np.allclose(cact.sum(), act.sum())), "universo": detail,
            "dias_evaluables": int(ev.sum())}


def audit_simulation(out: Path, sim_json: dict) -> dict:
    z = _load_npz(out / "simulacion_series.npz")
    demand = z["demanda"]
    known = ~np.isnan(demand)
    dem = np.where(known, demand, 0).astype(np.int64)
    cost = z["costo"]
    res, bad = [], []
    stock_by_L: dict = {}
    for key in sim_json["resultados"]:
        L, S, pol = key.split("|")[0].split("_")[0], key.split("|")[0].split("_")[1], key.split("|")[1]
        pre = f"L{L[1:]}_S{S[1:]}_{pol}__"
        on_hand, served, lost = z[pre + "on_hand"], z[pre + "served"], z[pre + "lost"]
        received, ordered, pipe, stock0 = z[pre + "received"], z[pre + "ordered"], z[pre + "pipeline_end"], z[pre + "stock0"]
        checks = {
            "saldo_final": bool((stock0 + received.sum(0) - served.sum(0) - on_hand[-1] == 0).all()),
            "saldo_diario": bool((stock0[None, :] + np.cumsum(received - served, axis=0) == on_hand).all()),
            "demanda": bool((served + lost == dem.T).all()),
            "pedidos": bool((ordered.sum(0) == received.sum(0) + pipe).all()),
            "no_negativos": bool((on_hand >= 0).all() and (pipe >= 0).all()),
            "sin_faltante_en_dias_sin_demanda": bool((lost[~known.T] == 0).all()),
        }
        total = sim_json["resultados"][key]["total"]
        elig = float(dem.sum())
        checks["fill_rate"] = _close(float(served.sum()) / elig if elig > 0 else None, total["fill_rate"])
        value = (float((ordered.sum(0) * cost).sum()) + float((stock0 * cost).sum()) - float((served.sum(0) * cost).sum())
                 - float((on_hand[-1] * cost).sum()) - float((pipe * cost).sum()))
        checks["identidad_valor"] = abs(value) < 1e-6
        checks["compras"] = _close(float((ordered.sum(0) * cost).sum()), total["compras_desembolsadas_supuesto"])
        stock_by_L.setdefault(L, []).append(stock0.tobytes())
        ok = all(checks.values())
        res.append({"clave": key, "ok": ok, **checks})
        if not ok:
            bad.append(key)
    same_start = all(len(set(v)) == 1 for v in stock_by_L.values())
    return {"combinaciones": len(res), "ok": bool(not bad and same_start and len(res) == 27), "malas": bad,
            "mismo_stock_inicial_entre_politicas": same_start, "detalle": res}


def run_audit(out: Path) -> dict:
    """Fase `auditoria`: registra inicio/fin/error; si no aprueba, la fase queda en error y `completa=false`."""
    out = Path(out)
    store = StateFile(out)
    store._begin("auditoria")
    try:
        res = _run_audit(out)
    except BaseException as exc:
        store._fail("auditoria", exc)
        raise
    if res["ok"]:
        store._end("auditoria", auditoria_sha256=sha_bytes(out / "auditoria.json"), combinaciones=res["simulacion"]["combinaciones"])
    else:
        store._fail("auditoria", "la auditoria no aprobo; ver auditoria.json")
    return res


def _run_audit(out: Path) -> dict:
    out = Path(out)
    state = json.loads((out / "estado.json").read_text(encoding="utf-8"))
    man = json.loads((out / "preparacion" / "manifiesto_preparacion.json").read_text(encoding="utf-8"))
    pred = json.loads((out / "predictivo.json").read_text(encoding="utf-8"))
    sim = json.loads((out / "simulacion.json").read_text(encoding="utf-8"))
    integ = {}
    for name, rec in man["archivos"].items():
        integ[name] = sha_bytes(out / "preparacion" / name) == rec["bytes_sha256"]
    for name in ("predicciones_fijas.npz", "inicializacion_sim.npz"):
        integ[name + ":logico"] = core.logical_signature(_load_npz(out / "preparacion" / name)) == man["archivos"][name]["logical_sha256"]
    f = state["fases"]
    from datetime import datetime
    sealed_before = (datetime.fromisoformat(man["creado_lima"]) <= datetime.fromisoformat(f["lectura_agosto"]["inicio"]))
    import gzip

    import pandas as pd
    csv = out / "ventas_agosto_min.csv.gz"
    with gzip.open(csv, "rt", encoding="utf-8") as fh:
        aug = pd.read_csv(fh, dtype={"sku": str, "almacen": str})
    aug_ok = bool(len(aug) == f["lectura_agosto"]["filas"] and sha_bytes(csv) == f["lectura_agosto"]["bytes_sha256"]
                  and (aug["fecha"].min() >= "2026-08-01" and aug["fecha"].max() <= "2026-08-31"))
    ap = audit_predictive(out, pred)
    asim = audit_simulation(out, sim)
    res = {"integridad_sellado": integ, "sello_anterior_a_lectura_agosto": bool(sealed_before),
           "ventas_agosto_minimas_ok": aug_ok, "fingerprint_entrenamiento": man["fingerprint_entrenamiento"],
           "predictivo": ap, "simulacion": asim,
           "ok": bool(all(integ.values()) and sealed_before and aug_ok and ap["ok"] and asim["ok"])}
    (out / "auditoria.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    return res
