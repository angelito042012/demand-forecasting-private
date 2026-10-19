"""T19 §8: comprobacion descriptiva de septiembre con promedio_28 (origenes 31/08 y 31/07). Solo lectura.

    python -m scripts.t19_descriptive_check --out artifacts/private/t19/descriptivo_septiembre.json
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from pathlib import Path

from pipeline.plan.descriptive import evaluate, read_sales

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "artifacts" / "private" / "datos_preparados_v1"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", type=Path, default=PKG)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    with (a.package / "02_grupo" / "productos.csv").open(encoding="utf-8-sig", newline="") as f:
        products = {r["producto_id"] for r in csv.DictReader(f) if r["seleccionado"] == "True"}
    sales = read_sales(a.package / "01_normalizados" / "ventas.csv", products)
    first, last = date(2026, 9, 1), date(2026, 9, 30)
    res = {"nota": "Descriptivo, no es T12 ni validacion de noviembre; septiembre ya fue inspeccionado; sin conteo de octubre; "
                   "los reales de septiembre solo evaluan. Catalogo: los 50 productos del grupo (seleccion al 31/07).",
           "productos": len(products),
           "origen_31_08": evaluate(sales, date(2026, 8, 31), first, last),
           "origen_31_07": evaluate(sales, date(2026, 7, 31), first, last)}
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
