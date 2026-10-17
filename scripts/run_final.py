"""T12: evaluacion final bajo la seleccion congelada. Fases idempotentes con checkpoints.

    python -m scripts.run_final verify   [--out artifacts/private/final]
    python -m scripts.run_final prepare  [--db demand_forecasting_v2] [--out ...]     # solo datos <= 31/07; emite docs/T12_SELLO.json
    python -m scripts.run_final evaluate --confirm-frozen-selection [--db ...]       # lee agosto SOLO con el sello commiteado
    python -m scripts.run_final audit    [--out ...]                                 # sin MongoDB ni reentrenamiento
    python -m scripts.run_final report   [--out ...]                                 # docs/T12_RESULTADOS.md, T12_METRICAS.json, T12_MANIFIESTO.json
    python -m scripts.run_final status   [--out ...]

La base se usa en SOLO LECTURA. No toca la base v1/v2, los Excel, las cargas ni el puntero historico.
Inventario simulado con supuestos; no corresponde al inventario real de la empresa.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pipeline.data.importer import get_client
from pipeline.final.audit import run_audit
from pipeline.final.frozen import FreezeError
from pipeline.final.report import write_report
from pipeline.final.runner import FinalGateError, FinalRun

DEFAULT_OUT = Path("artifacts/private/final")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("fase", choices=["verify", "prepare", "evaluate", "audit", "report", "status"])
    ap.add_argument("--db", default="demand_forecasting_v2")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--confirm-frozen-selection", action="store_true", help="solo evaluate: confirma la seleccion congelada")
    ap.add_argument("--no-require-commit", action="store_true", help="SOLO pruebas: no exige el sello commiteado")
    args = ap.parse_args(argv)
    if args.fase == "status":
        p = args.out / "estado.json"
        print(p.read_text(encoding="utf-8") if p.exists() else json.dumps({"fases": {}, "completa": False}))
        return 0
    try:
        if args.fase == "audit":
            res = run_audit(args.out)
            print(json.dumps({"ok": res["ok"], "predictivo_ok": res["predictivo"]["ok"], "simulacion_ok": res["simulacion"]["ok"]}))
            return 0 if res["ok"] else 1
        if args.fase == "report":
            write_report(args.out)
            print("reporte escrito en docs/T12_RESULTADOS.md, T12_METRICAS.json y T12_MANIFIESTO.json")
            return 0
        client = get_client()
        try:
            run = FinalRun(client[args.db], args.out, require_commit=not args.no_require_commit)
            if args.fase == "verify":
                rep = run.verify()
                print(json.dumps({"ok": rep["ok"], "no_coinciden_vivo": list(rep["no_coinciden_vivo_y_motivo"])}))
            elif args.fase == "prepare":
                man = run.prepare()
                print(json.dumps({"sello_sha256": man["sello_sha256"], "agosto_consultado": man["agosto_consultado"]}))
            else:
                run.evaluate(confirm_frozen=args.confirm_frozen_selection)
                print(json.dumps({k: v.get("estado") for k, v in run.state["fases"].items()}))
        finally:
            client.close()
        return 0
    except (FinalGateError, FreezeError) as exc:
        print(f"BLOQUEADO: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
