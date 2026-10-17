"""CLI privilegiada de publicacion de corridas (T08 §4). Separada del HTTP.

    python -m scripts.publish_run --manifest t07 [--db NOMBRE]

Solo acepta nombres de la lista cerrada config/t08_publish.json; nunca rutas ni modelos.
Lee artefactos existentes, los verifica y publica en MongoDB. No reentrena ni lee agosto.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date

from pipeline.data.importer import get_client
from pipeline.data.training_access import load_training_data
from pipeline.publish.publisher import (
    PublishInProgressError,
    PublishValidationError,
    publish,
)
from pipeline.publish.source import (
    SourceVerificationError,
    load_publish_config,
    resolve_entry,
    verify_and_load,
)

_DB = re.compile(r"^[A-Za-z0-9_]{1,63}$")


def main(argv=None) -> int:
    cfg = load_publish_config()
    ap = argparse.ArgumentParser(description="Publica una corrida historica verificada")
    ap.add_argument("--manifest", required=True, choices=sorted(cfg["manifests"]))
    ap.add_argument("--db", default=os.environ.get("MONGODB_DATABASE", "demand_forecasting_v2"))
    ap.add_argument("--no-activate", action="store_true", help="no mover el puntero activo")
    args = ap.parse_args(argv)
    if not _DB.match(args.db):
        print("Nombre de base invalido.", file=sys.stderr)
        return 2
    try:
        entry = resolve_entry(args.manifest, cfg)
        src = verify_and_load(entry)
        db = get_client()[args.db]
        td = load_training_data(db, date.fromisoformat(entry["cutoff"]))
        res = publish(db, src, dict(td.catalog), td.fingerprint, activate_run=not args.no_activate)
    except (SourceVerificationError, PublishValidationError, PublishInProgressError) as exc:
        print(f"Publicacion rechazada: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 - mensaje generico, sin URI ni rutas
        print(f"Publicacion fallida ({type(exc).__name__}); revise la corrida en estado failed.", file=sys.stderr)
        return 1
    print(json.dumps({"run_id": res.run_id, "status": res.status, "activated": res.activated,
                      "counts": res.counts}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
