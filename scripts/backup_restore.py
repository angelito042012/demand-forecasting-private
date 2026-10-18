"""T11A: exportacion y restauracion verificada de una base de publicacion (solo MongoDB local, sin red externa).

    python -m scripts.backup_restore export  --db demand_forecasting_pub --out artifacts/private/t11a/backup
    python -m scripts.backup_restore restore --from artifacts/private/t11a/backup --db df_restore_t11a_<ts>
    python -m scripts.backup_restore verify  --from artifacts/private/t11a/backup --db df_restore_t11a_<ts>

El export excluye sessions/users/login_*/jobs/scheduler_ticks, escribe <coleccion>.ndjson.gz, indices.json y
manifiesto.json (conteos, hash de contenido, hash de archivos, corridas, artefactos privados con sha256). La
restauracion exige una base destino DIFERENTE y vacia, y verifica conteos, hash de contenido, indices, estado de
corridas, children_ref y hijos. Nunca escribe en demand_forecasting_v2/_dev.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from pipeline.data.importer import get_client
from pipeline.publish.archive import (
    ArchiveError,
    export_db,
    load_manifest,
    measure,
    quota_use,
    restore_db,
    sha256_file,
    verify_export_files,
    verify_restored,
)

ROOT = Path(__file__).resolve().parents[1]
_DB = re.compile(r"^[A-Za-z0-9_]{1,63}$")


def private_artifacts(folder: Path | None) -> list[dict]:
    """Manifiesto de artefactos privados (nombre relativo + sha256 + tamano); no se copian a la base ni al export."""
    if folder is None or not Path(folder).is_dir():
        return []
    folder = Path(folder)
    return [{"name": p.relative_to(folder).as_posix(), "sha256": sha256_file(p), "size_bytes": p.stat().st_size}
            for p in sorted(folder.rglob("*")) if p.is_file() and not p.name.endswith(".tmp")]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Export/restauracion verificada (T11A)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("--db", required=True)
    e.add_argument("--out", required=True, type=Path)
    e.add_argument("--artifacts-dir", type=Path, default=ROOT / "artifacts" / "private" / "final")
    e.add_argument("--allow-staging", action="store_true")
    r = sub.add_parser("restore")
    r.add_argument("--from", dest="src", required=True, type=Path)
    r.add_argument("--db", required=True)
    v = sub.add_parser("verify")
    v.add_argument("--from", dest="src", required=True, type=Path)
    v.add_argument("--db", required=True)
    args = ap.parse_args(argv)
    if not _DB.match(args.db):
        print("Nombre de base invalido.", file=sys.stderr)
        return 2
    client = get_client()
    try:
        if args.cmd == "export":
            man = export_db(client[args.db], args.out, artifacts=private_artifacts(args.artifacts_dir),
                            allow_staging=args.allow_staging)
            print(json.dumps({"colecciones": {k: v["count"] for k, v in man["colecciones"].items()},
                              "excluidas": man["excluidas"], "segundos": man["segundos_export"],
                              "bytes_comprimidos": man["bytes_comprimidos"]}, ensure_ascii=False))
            return 0
        if args.cmd == "restore":
            rep = restore_db(args.src, client[args.db])
        else:
            bad = verify_export_files(args.src)
            rep = verify_restored(client[args.db], load_manifest(args.src), args.src)
            rep["problemas"] = bad + rep["problemas"]
            rep["ok"] = not rep["problemas"]
            rep["medicion"] = measure(client[args.db])
        rep["cuota"] = quota_use(rep["medicion"]["data_plus_index_mb"])
        print(json.dumps({k: rep[k] for k in ("ok", "problemas", "puntero", "cuota") if k in rep}
                         | {"segundos_restauracion": rep.get("segundos_restauracion"),
                            "data_plus_index_mb": rep["medicion"]["data_plus_index_mb"]}, ensure_ascii=False))
        return 0 if rep["ok"] else 1
    except ArchiveError as exc:
        print(f"Rechazado: {exc}", file=sys.stderr)
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
