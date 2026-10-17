# ruff: noqa: ISC004
"""Ejecuta T06 (Random Forest y XGBoost frente a baselines, cinco folds, solo marzo-julio).

Uso: python -m scripts.run_t06 [--db demand_forecasting_v2] [--out artifacts/private/t06]
Privado: predicciones y modelos. Versionado: docs/T06_METRICAS.json, T06_RESULTADOS.md, T06_MANIFIESTO.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import sklearn
import xgboost

from pipeline.data import daily_series as ds
from pipeline.data.importer import get_client, sha256_file
from pipeline.forecast.t05 import run_all
from pipeline.forecast.t06 import BASELINES, ML_MODELS, make_extras_fn, select_models
from scripts.run_t05 import _git

CFG5, CFG6 = Path("config/t05_config.json"), Path("config/t06_config.json")
CODE = ["pipeline/forecast/baselines.py", "pipeline/forecast/metrics.py", "pipeline/forecast/t05.py",
        "pipeline/forecast/features.py", "pipeline/forecast/models.py", "pipeline/forecast/t06.py",
        "pipeline/data/training_access.py", "pipeline/data/sources.py", "pipeline/data/catalog.py",
        "pipeline/data/daily_series.py", "pipeline/data/calendar.py", "scripts/run_t06.py"]
METHODS = (*BASELINES, *ML_MODELS)
DOCS = Path("docs")


def code_hash() -> str:
    h = hashlib.sha256()
    for f in CODE:
        h.update(f.encode() + b"\0" + Path(f).read_bytes().replace(b"\r\n", b"\n") + b"\0")
    return h.hexdigest()


def _f(v, nd=3):
    return "-" if v is None else (f"{v:.{nd}f}" if isinstance(v, float) else str(v))


def table(rec, **flt):
    rows = {r["metodo"]: r for r in rec if all(r[k] == v for k, v in flt.items())}
    out = ["| Método | n | MAE | RMSE | WAPE (razón) | Sesgo (pred−obs) | Sub / Sobre / Exacto | MAPE razón (cobertura; ceros excl.) | R² |",
           "|---|---|---|---|---|---|---|---|---|"]
    for m in METHODS:
        r = rows.get(m)
        if not r or r["n"] == 0:
            continue
        out.append(f"| {m} | {r['n']} | {_f(r['MAE'])} | {_f(r['RMSE'])} | {_f(r['WAPE'], 4)} | {_f(r['sesgo_acumulado'], 1)} | "
                   f"{r['prop_subpronostico']:.3f} / {r['prop_sobrepronostico']:.3f} / {r['prop_exacto']:.3f} | "
                   f"{_f(r['MAPE'])} ({r['MAPE_cobertura_reales_positivos']:.3f}; {r['MAPE_ceros_excluidos']}) | {_f(r['R2'])} |")
    return out


def render(res, sel, log, man, folds) -> str:
    rec = res["metricas"]
    L = ["# T06 Resultados: ML frente a baselines (marzo-julio 2026, desarrollo)", "",
         f"Generado el {man['generado_lima']} (America/Lima). Protocolo congelado en {man['commit_protocolo']} (config sha256 "
         f"`{man['config_t06_sha256'][:12]}`). Solo marzo-julio; agosto no se leyó. **Estos folds son de desarrollo: los baselines de T05 ya "
         "se habían observado; no es una prueba final independiente.** WAPE y MAPE son razones (1,00 = 100 %). "
         "No se declara mejora de inventario.", ""]
    L += ["## Resumen de selección (regla preregistrada)", ""]
    for nivel, s in sel.items():
        L += [f"### {nivel} (criterio primario: WAPE {s['vista_primaria']}, cohorte primaria, universo común, agregado de 5 folds)", "",
              "| Método | WAPE | Mejora relativa vs mejor referencia | Folds favorables | Sesgo/obs. | Cumple regla |", "|---|---|---|---|---|---|"]
        for m in BASELINES:
            L.append(f"| {m} (baseline) | {_f(s['wape_baselines'][m], 4)} | - | - | - | - |")
        for m, d in s["ml"].items():
            L.append(f"| {m} | {_f(d['WAPE'], 4)} | {_f(d['mejora_relativa_vs_mejor_referencia'], 4)} | "
                     f"{d['n_folds_favorables']}/{len(folds)} ({', '.join(d['folds_favorables']) or '-'}) | "
                     f"{_f(d['sesgo_relativo'], 3)} | {'sí' if d['cumple_regla'] else 'no'} |")
        L += ["", f"- Mejor referencia (incluye cero): **{s['mejor_referencia']}**; mejor referencia no nula: **{s['mejor_referencia_no_nula']}**.",
              f"- Ganador ML: **{s['ganador_ml'] or 'ninguno'}**. Propuesta provisional para la simulación: **{s['propuesta_para_simulacion']}**. {s['nota']}.", ""]
    for nivel, title in (("sku", "SKU-almacén"), ("categoria", "Categoría (productos conocidos al corte)")):
        for view, vt in (("bloque7", "cantidad acumulada a 7 días"), ("diaria", "error diario")):
            L += [f"## {title}: cohorte primaria, universo común, {vt}, agregado de 5 folds", ""]
            L += table(rec, fold="AGREGADO", nivel=nivel, cohorte="primaria", universo="comun", vista=view) + [""]
    for nivel, view in (("sku", "bloque7"), ("categoria", "diaria")):
        L += [f"## WAPE por fold ({nivel}, {view}, primaria, común)", "", "| Fold | " + " | ".join(METHODS) + " |",
              "|---|" + "---|" * len(METHODS)]
        for f in folds:
            cells = []
            for m in METHODS:
                r = next((x for x in rec if (x["fold"], x["nivel"], x["metodo"], x["vista"], x["cohorte"], x["universo"])
                          == (f, nivel, m, view, "primaria", "comun")), None)
                cells.append(_f(r and r.get("WAPE"), 3))
            L.append(f"| {f} | " + " | ".join(cells) + " |")
        L.append("")
    L += ["## SKU historia corta (universo propio, error diario, agregado)", ""]
    L += table(rec, fold="AGREGADO", nivel="sku", cohorte="historia_corta", universo="propio", vista="diaria") + [""]
    L += ["## Cómputo y entrenamiento", "", "| Fold | Nivel | Modelo | Filas | Features | Orígenes | Ajuste (s) | Matriz (MB) | Negativos recortados |",
          "|---|---|---|---|---|---|---|---|---|"]
    for e in log:
        L.append(f"| {e['fold']} | {e['nivel']} | {e['modelo']} | {e['filas']} | {e['caracteristicas']} | {e['origenes']} | "
                 f"{e['segundos_ajuste']} | {e['memoria_matriz_mb']} | {e['negativos_recortados']} |")
    L += ["", f"Tiempo total de la ejecución completa: {man['segundos_totales']:.0f} s. Repetición de F1 equivalente (tolerancia 1e-9): {man['repeticion_f1_identica']} (diferencia máxima {man['repeticion_f1_diferencia_maxima']:.2e}). "
          f"Baselines idénticos a T05: {man['baselines_identicos_a_t05']}.", "",
          "## Limitaciones", "",
          "- Folds de desarrollo ya observados; la apertura de agosto y la selección final se deciden tras la revisión.",
          "- Sin feature de precio (no incorporado). Un almacén, una unidad base, ventas posiblemente censuradas por stock.",
          "- Horizonte de 7 días: la simulación puede necesitar lead time + revisión mayores; no se extrapola a 14 días.",
          "- Categoría = productos conocidos al corte; las unidades de SKU nuevos quedan fuera (ver T05)."]
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="demand_forecasting_v2")
    ap.add_argument("--out", type=Path, default=Path("artifacts/private/t06"))
    ap.add_argument("--commit-protocolo", default="286017d")
    args = ap.parse_args(argv)
    cfg5, cfg6 = json.loads(CFG5.read_text(encoding="utf-8")), json.loads(CFG6.read_text(encoding="utf-8"))
    sha6 = sha256_file(CFG6)
    args.out.mkdir(parents=True, exist_ok=True)
    db = get_client()[args.db]
    t0 = time.perf_counter()
    log: list = []
    res = run_all(db, cfg5, extras_fn=make_extras_fn(cfg6, sha6, args.out / "modelos", log))
    folds = [f["id"] for f in cfg5["folds"]]
    # repeticion determinista del fold F1
    log_rep: list = []
    rep = run_all(db, cfg5, extras_fn=make_extras_fn(cfg6, sha6, args.out / "modelos_repeticion", log_rep), only_folds={"F1"})
    a = res["predicciones"][res["predicciones"]["fold"] == "F1"].reset_index(drop=True)
    b = rep["predicciones"].reset_index(drop=True)
    num = [c for c in a.columns if a[c].dtype.kind == "f"]
    max_diff = float(np.nanmax(np.abs(a[num].to_numpy() - b[num].to_numpy()))) if len(a) else 0.0
    same_f1 = bool(a.drop(columns=num).equals(b.drop(columns=num)) and max_diff <= cfg6["computo"]["repeticion_tolerancia_abs"]
                   and np.array_equal(np.isnan(a[num].to_numpy()), np.isnan(b[num].to_numpy())))
    # identidad de los baselines con T05
    t05 = json.loads(Path("docs/T05_METRICAS.json").read_text(encoding="utf-8"))["metricas"]
    key = lambda r: (r["fold"], r["nivel"], r["cohorte"], r["universo"], r["metodo"], r["vista"])
    mine = {key(r): r for r in res["metricas"] if r["metodo"] in BASELINES}
    ident = all(k in mine and mine[k]["n"] == r["n"] and all(
        (mine[k].get(m) is None and r.get(m) is None) or (mine[k].get(m) is not None and r.get(m) is not None
                                                          and abs(mine[k][m] - r[m]) < 1e-9)
        for m in ("MAE", "WAPE", "sesgo_acumulado", "RMSE")) for k, r in ((key(x), x) for x in t05))
    sel = select_models(res["metricas"], cfg6, folds)
    pred_path = args.out / "predicciones.csv.gz"
    pred_path.write_bytes(ds.to_csv_gz_bytes(res["predicciones"]))
    man = {
        "generado_lima": datetime.now(ZoneInfo("America/Lima")).strftime("%Y-%m-%d %H:%M"),
        "base_de_datos": args.db, "config_t05_sha256": sha256_file(CFG5), "config_t06_sha256": sha6,
        "commit_protocolo": args.commit_protocolo, "codigo_sha256": code_hash(), "codigo_archivos": CODE,
        "git_commit": _git("rev-parse", "HEAD"),
        "git_sucio": bool(_git("status", "--porcelain", "--", "pipeline", "scripts", "config")),
        "agosto_usado": False, "repeticion_f1_identica": same_f1, "repeticion_f1_diferencia_maxima": max_diff, "baselines_identicos_a_t05": bool(ident),
        "segundos_totales": time.perf_counter() - t0, "semillas": 20261017,
        "predicciones": {"filas": len(res["predicciones"]), "sha256_archivo": sha256_file(pred_path)},
        "folds": {fid: {"corte": f["corte"], "fingerprint": f["fingerprint"], "fuentes": f["fuentes"]}
                  for fid, f in res["folds"].items()},
        "modelos_guardados": sorted(p.name for p in (args.out / "modelos").glob("*.joblib")),
        "entrenamiento": log, "negativos_recortados_total": sum(e["negativos_recortados"] for e in log),
        "versiones": {"python": sys.version.split()[0], "pandas": pd.__version__, "numpy": np.__version__,
                      "scikit-learn": sklearn.__version__, "xgboost": xgboost.__version__},
    }
    DOCS.joinpath("T06_METRICAS.json").write_text(json.dumps(
        {"metricas": res["metricas"], "cobertura": res["cobertura"], "seleccion": sel}, ensure_ascii=False, indent=1,
        default=str) + "\n", encoding="utf-8")
    DOCS.joinpath("T06_MANIFIESTO.json").write_text(json.dumps(man, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    DOCS.joinpath("T06_RESULTADOS.md").write_text(render(res, sel, log, man, folds), encoding="utf-8")
    print(json.dumps({"repeticion_f1": same_f1, "baselines_identicos_a_t05": bool(ident),
                      "seleccion": {k: {"ganador_ml": v["ganador_ml"], "propuesta": v["propuesta_para_simulacion"]}
                                    for k, v in sel.items()}, "segundos": round(man["segundos_totales"])}, indent=1))
    return 0 if same_f1 and ident else 1


if __name__ == "__main__":
    sys.exit(main())
