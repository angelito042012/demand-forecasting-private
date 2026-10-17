# ruff: noqa: ISC004
"""Ejecuta T05 (baselines, cinco folds, solo marzo-julio) y escribe evidencia.

Uso: python -m scripts.run_t05 [--db demand_forecasting_v2] [--out artifacts/private/t05]
Privado (ignorado por Git): predicciones fila a fila. Versionado: docs/T05_METRICAS.json,
docs/T05_RESULTADOS.md y docs/T05_MANIFIESTO.json (agregados, hashes, versiones).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from pipeline.data.importer import get_client, sha256_file
from pipeline.forecast.baselines import METHODS
from pipeline.forecast.t05 import run_all

CONFIG = Path("config/t05_config.json")
CODE_FILES = ["pipeline/forecast/baselines.py", "pipeline/forecast/metrics.py", "pipeline/forecast/t05.py",
              "pipeline/data/training_access.py", "pipeline/data/sources.py", "pipeline/data/catalog.py",
              "pipeline/data/daily_series.py", "pipeline/data/calendar.py", "scripts/run_t05.py"]
DOCS = Path("docs")


def _git(*a) -> str:
    try:
        return subprocess.run(["git", *a], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "desconocido"


def code_hash() -> str:
    h = hashlib.sha256()
    for f in CODE_FILES:
        h.update(f.encode() + b"\0" + Path(f).read_bytes().replace(b"\r\n", b"\n") + b"\0")
    return h.hexdigest()


def _fmt(v, nd=3):
    return "-" if v is None else (f"{v:.{nd}f}" if isinstance(v, float) else str(v))


def _table(records, **flt) -> list[str]:
    rows = [r for r in records if all(r[k] == v for k, v in flt.items())]
    order = {m: i for i, m in enumerate(METHODS)}
    rows.sort(key=lambda r: order[r["metodo"]])
    out = ["| Método | n filas | MAE | RMSE | WAPE | Sesgo (pred−obs) | Sub / Sobre / Exacto | MAPE (cobertura; ceros excl.) | R² |",
           "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if r["n"] == 0:
            out.append(f"| {r['metodo']} | 0 | - | - | - | - | - | - | - |")
            continue
        out.append(f"| {r['metodo']} | {r['n']} | {_fmt(r['MAE'])} | {_fmt(r['RMSE'])} | {_fmt(r['WAPE'])} | "
                   f"{_fmt(r['sesgo_acumulado'], 1)} | {r['prop_subpronostico']:.3f} / {r['prop_sobrepronostico']:.3f} / "
                   f"{r['prop_exacto']:.3f} | {_fmt(r['MAPE'])} ({r['MAPE_cobertura_reales_positivos']:.3f}; "
                   f"{r['MAPE_ceros_excluidos']}) | {_fmt(r['R2'])} |")
    return out


def render(res: dict, cfg: dict, man: dict) -> str:
    rec = res["metricas"]
    L = ["# T05 Resultados de baselines (marzo-julio 2026)", "",
         f"Generado el {man['generado_lima']} (America/Lima) con el protocolo congelado (config sha256 "
         f"`{man['config_sha256'][:12]}`, commit del protocolo {man['commit_protocolo']}). Solo marzo-julio; "
         "agosto no se leyó. Cifras agregadas por scripts/run_t05.py; predicciones fila a fila en artifacts/private/t05/.", "",
         "Advertencia: el control `cero` puede parecer competitivo por la abundancia de ceros; ganar una métrica no demuestra buena "
         "reposición ni mejora de inventario. Unidades de categoría = suma de unidades base heterogéneas.", "",
         "## Folds y días evaluables", "", "| Fold | Corte | Validación | Días evaluables | No evaluables | Fingerprint |", "|---|---|---|---|---|---|"]
    for fid, f in res["folds"].items():
        L.append(f"| {fid} | {f['corte']} | {f['dias_validacion'][0]}…{f['dias_validacion'][-1]} | {f['dias_evaluables']}/7 | "
                 f"{f['dias_no_evaluables'] or '-'} | `{f['fingerprint'][:12]}` |")
    for lv, title in (("sku", "SKU-almacén"), ("categoria", "Categoría")):
        for view, vt in (("diaria", "error diario"), ("bloque7", "cantidad acumulada a 7 días (por entidad, días evaluables)")):
            L += ["", f"## {title}: cohorte primaria, universo común, {vt}, agregado de los 5 folds", ""]
            L += _table(rec, fold="AGREGADO", nivel=lv, cohorte="primaria", universo="comun", vista=view)
    L += ["", "## WAPE diario SKU primaria (universo común) por fold", "", "| Fold | " + " | ".join(METHODS) + " |",
          "|---|" + "---|" * len(METHODS)]
    for fid in res["folds"]:
        cells = []
        for m in METHODS:
            r = next(x for x in rec if x["fold"] == fid and x["nivel"] == "sku" and x["cohorte"] == "primaria"
                     and x["universo"] == "comun" and x["vista"] == "diaria" and x["metodo"] == m)
            cells.append(_fmt(r.get("WAPE")))
        L.append(f"| {fid} | " + " | ".join(cells) + " |")
    L += ["", "## SKU: historia corta (universo propio, error diario, agregado)", ""]
    L += _table(rec, fold="AGREGADO", nivel="sku", cohorte="historia_corta", universo="propio", vista="diaria")
    L += ["", "## Cobertura por fold", "",
          "| Fold | Nivel | Cohorte | Entidades | Filas objetivo | Filas comunes | Fallback naive (filas) | Antigüedad último día (mediana/p90/max) |",
          "|---|---|---|---|---|---|---|---|"]
    for c in res["cobertura"]:
        a = c["antiguedad_ultimo_dia"]
        L.append(f"| {c['fold']} | {c['nivel']} | {c['cohorte']} | {c['n_entidades']} | {c['filas_objetivo']} | "
                 f"{c['filas_comunes']} | {c['naive_fallback_filas']} | "
                 f"{'-' if not a else f'{a['mediana']:.0f}/{a['p90']:.0f}/{a['max']:.0f}'} |")
    L += ["", "## Nuevos en validación (sin historia al origen; sin predicción)", "",
          "| Fold | SKU-almacén nuevos | Unidades evaluables | Categorías no conocidas | Unidades (categoría) |", "|---|---|---|---|---|"]
    for fid, f in res["folds"].items():
        n, c = f["niveles"]["sku"]["nuevos_en_validacion"], f["niveles"]["categoria"]["nuevos_en_validacion"]
        L.append(f"| {fid} | {n['entidades']} | {n['unidades_evaluables']:.0f} | {c['categorias'] or '-'} | {c['unidades_evaluables']:.0f} |")
    ref = res["referencia_t06"]
    L += ["", "## Referencia para T06 (regla fijada en el protocolo)", "",
          f"- Selección: **{ref['seleccion']}**; WAPE agregado (SKU, primaria, común, diario): {ref['wape']}; control cero: "
          f"{ref.get('control_cero_wape')}; dentro del umbral de empate: {ref.get('empatados_dentro_del_umbral')}.",
          "- Límites: cinco semanas de validación, un solo almacén, ventas posiblemente censuradas por stock, WAPE diario dominado "
          "por intermitencia. No confirma mejora del inventario; sirve solo como referencia mínima para comparar ML en T06."]
    L += ["", "## Lectura automática frente al control cero (WAPE agregado, primaria, universo común)", ""]
    for lv in ("sku", "categoria"):
        for view in ("diaria", "bloque7"):
            w = {r["metodo"]: r["WAPE"] for r in rec if r["fold"] == "AGREGADO" and r["nivel"] == lv
                 and r["cohorte"] == "primaria" and r["universo"] == "comun" and r["vista"] == view}
            better = [m for m in METHODS if m != "cero" and w.get(m) is not None and w[m] < w["cero"]]
            L.append(f"- {lv}, {view}: métodos con WAPE menor que el control cero: {better or 'ninguno'} "
                     f"(WAPE: { {m: round(v, 3) for m, v in w.items() if v is not None} }).")
    L.append("- La cohorte primaria cuenta los ceros observados como observaciones utilizables (definición del protocolo); "
             "por eso la antigüedad del último día utilizable es casi siempre 0 y la cohorte incluye productos que venden pocos días.")
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="demand_forecasting_v2")
    ap.add_argument("--out", type=Path, default=Path("artifacts/private/t05"))
    ap.add_argument("--commit-protocolo", default="d763bed")
    args = ap.parse_args(argv)
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    db = get_client()[args.db]
    res = run_all(db, cfg)
    res2 = run_all(db, cfg)   # repeticion: debe reproducir predicciones y metricas exactamente
    same = res["predicciones"].equals(res2["predicciones"]) and res["metricas"] == res2["metricas"]
    args.out.mkdir(parents=True, exist_ok=True)
    pred_path = args.out / "predicciones.csv.gz"
    pred_path.write_bytes(__import__("pipeline.data.daily_series", fromlist=["x"]).to_csv_gz_bytes(res["predicciones"]))
    man = {
        "generado_lima": datetime.now(ZoneInfo("America/Lima")).strftime("%Y-%m-%d %H:%M"),
        "base_de_datos": args.db, "config_sha256": sha256_file(CONFIG), "commit_protocolo": args.commit_protocolo,
        "codigo_sha256": code_hash(), "codigo_archivos": CODE_FILES, "git_commit": _git("rev-parse", "HEAD"),
        "git_sucio": bool(_git("status", "--porcelain", "--", "pipeline", "scripts", "config")),
        "repeticion_identica": bool(same), "agosto_usado": False,
        "predicciones": {"filas": len(res["predicciones"]), "sha256_archivo": sha256_file(pred_path),
                         "sha256_contenido": hashlib.sha256(res["predicciones"].to_csv(
                             index=False, lineterminator="\n", float_format="%.10g").encode()).hexdigest()},
        "folds": {fid: {"corte": f["corte"], "fingerprint": f["fingerprint"], "fuentes": f["fuentes"],
                        "dias_evaluables": f["dias_evaluables"], "dias_no_evaluables": f["dias_no_evaluables"]}
                  for fid, f in res["folds"].items()},
        "versiones": {"python": sys.version.split()[0], "pandas": pd.__version__, "numpy": np.__version__},
    }
    DOCS.joinpath("T05_METRICAS.json").write_text(json.dumps(
        {"metricas": res["metricas"], "cobertura": res["cobertura"], "referencia_t06": res["referencia_t06"]},
        ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    DOCS.joinpath("T05_MANIFIESTO.json").write_text(json.dumps(man, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    DOCS.joinpath("T05_RESULTADOS.md").write_text(render(res, cfg, man), encoding="utf-8")
    print(json.dumps({"repeticion_identica": same, "referencia": res["referencia_t06"]}, indent=1, default=str))
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())
