"""T11A: publica el paquete final T12 (corrida `final_evaluation`) en la base de publicacion. Separada del HTTP.

    python -m scripts.publish_final [--db demand_forecasting_pub] [--dry-run]

Lee solo `artifacts/private/final/` (verificado: 7 fases, auditoria, hashes), no ejecuta modelos, no lee agosto de MongoDB
y no mueve el puntero activo. Rechaza demand_forecasting_v2/_dev. Idempotente (segunda ejecucion = sin_cambios).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from pipeline.data.importer import get_client
from pipeline.publish.final_package import (
    FINAL_DIR,
    SEAL_COMMIT_SHORT,
    FinalPackageError,
    publish_final,
)
from pipeline.publish.protocol import PublishInProgressError, PublishValidationError
from pipeline.publish.schema import SchemaError

_DB = re.compile(r"^[A-Za-z0-9_]{1,63}$")
ROOT = Path(__file__).resolve().parents[1]


def _full_commit(short: str) -> str:
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--verify", short + "^{commit}"],
                             capture_output=True, text=True, timeout=15, check=False)
        got = out.stdout.strip()
        return got if out.returncode == 0 and len(got) == 40 else short
    except (OSError, subprocess.SubprocessError):
        return short


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Publica la evaluacion final T12 (kind final_evaluation)")
    ap.add_argument("--db", default="demand_forecasting_pub")
    ap.add_argument("--root", type=Path, default=FINAL_DIR)
    ap.add_argument("--dry-run", action="store_true", help="verifica, construye y estima la capacidad sin escribir")
    args = ap.parse_args(argv)
    if not _DB.match(args.db):
        print("Nombre de base invalido.", file=sys.stderr)
        return 2
    client = get_client()
    try:
        res = publish_final(client[args.db], args.root, dry_run=args.dry_run, seal_commit=_full_commit(SEAL_COMMIT_SHORT))
    except (FinalPackageError, PublishValidationError, PublishInProgressError, SchemaError) as exc:
        print(f"Publicacion rechazada: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 - mensaje generico, sin URI ni rutas
        print(f"Publicacion fallida ({type(exc).__name__}); revise la corrida en estado failed.", file=sys.stderr)
        return 1
    finally:
        client.close()
    print(json.dumps(res, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
