"""T11A: exportacion y restauracion verificada de una base de publicacion (solo MongoDB local, sin red externa).

    python -m scripts.backup_restore export  --db demand_forecasting_pub --out artifacts/private/t11a/backup
    python -m scripts.backup_restore restore --from artifacts/private/t11a/backup --db df_restore_t11a_<ts>
    python -m scripts.backup_restore verify  --from artifacts/private/t11a/backup --db df_restore_t11a_<ts>

El export excluye sessions/users/login_*/jobs/scheduler_ticks, escribe <coleccion>.ndjson.gz, indices.json y
manifiesto.json (conteos, hash de contenido, hash de archivos, corridas, artefactos privados con sha256). La
restauracion exige una base destino DIFERENTE y vacia, y verifica conteos, hash de contenido, indices, estado de
corridas, children_ref y hijos. Nunca escribe en demand_forecasting_v2/_dev.

T11B (R13) - recuperacion integral (Mongo + bundle privado de artefactos), con ventana de mantenimiento impuesta:

    python -m scripts.backup_restore export-all  --db demand_forecasting_pub --out artifacts/private/t11b/respaldo --maintenance-confirmed
    python -m scripts.backup_restore restore-all --from artifacts/private/t11b/respaldo --db df_restore_t11b_<ts> --dest artifacts/private/t11b/restaurado_<ts>

`export-all` exige --maintenance-confirmed, ausencia de escritores y hash de contenido igual antes/durante/despues; un
respaldo parcial (archivo de la lista cerrada ausente) falla salvo --allow-partial y queda con integro=false.
`restore-all` informa por separado mongo_ok, artefactos_ok y recuperacion_integral_ok (solo true si ambos).
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from pathlib import Path

from pipeline.data.importer import get_client
from pipeline.publish import private_bundle as pb
from pipeline.publish.archive import (
    ArchiveError,
    check_maintenance,
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


def export_all(client, db_name: str, out: Path, *, root: Path = ROOT, cfg: dict | None = None,
               maintenance_confirmed: bool = False, allow_partial: bool = False) -> dict:
    """Export Mongo (consistencia fuerte) + bundle privado en `out` (nuevo y vacio): out/mongo, out/bundle,
    out/recuperacion.json. Si falla, retira lo creado en `out`."""
    out = Path(out)
    t0 = time.perf_counter()
    db = client[db_name]
    mant = check_maintenance(db, confirmed=maintenance_confirmed)
    cfg = cfg or pb.load_config()
    pl = pb.plan(root, cfg)
    if pl["faltantes"] and not allow_partial:
        raise pb.BundleError("respaldo parcial: faltan " + ", ".join(pl["faltantes"]))
    created = not out.exists()
    if not created and any(out.iterdir()):
        raise pb.BundleError("el directorio de respaldo no esta vacio")
    out.mkdir(parents=True, exist_ok=True)
    try:
        mongo = export_db(db, out / "mongo", artifacts=[], strict_content=True)
        bundle = pb.export_bundle(root, out / "bundle", cfg, allow_partial=allow_partial)
        mant_after = check_maintenance(db, confirmed=maintenance_confirmed)
        rec = {"version": "t11b-recuperacion-1", "base_origen": db_name, "ventana_mantenimiento": mant,
               "ventana_mantenimiento_despues": mant_after,
               "mongo_manifiesto_sha256": sha256_file(out / "mongo" / "manifiesto.json"),
               "bundle_manifiesto_sha256": sha256_file(out / "bundle" / pb.MANIFEST_NAME), "bundle_integro": bundle["integro"],
               "bundle_faltantes": bundle["faltantes"], "mongo_bytes_comprimidos": mongo["bytes_comprimidos"],
               "bundle_bytes": bundle["bytes_total"], "bundle_archivos": bundle["n_archivos"],
               "segundos_mongo": mongo["segundos_export"], "segundos_bundle": bundle["segundos_export"],
               "segundos_total": round(time.perf_counter() - t0, 2), "consistencia_mongo": mongo["consistencia"]}
        (out / "recuperacion.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        return rec
    except BaseException:
        if created:
            shutil.rmtree(out, ignore_errors=True)
        else:
            for child in out.iterdir():
                shutil.rmtree(child, ignore_errors=True) if child.is_dir() else child.unlink()
        raise


def restore_all(client, src: Path, db_name: str, dest: Path, *, root: Path = ROOT, cfg: dict | None = None,
                git_repo: Path | None = None) -> dict:
    """Restaura Mongo en `db_name` (nueva) y el bundle en `dest` (nueva y vacia). Informa mongo_ok y artefactos_ok."""
    src = Path(src)
    rec = json.loads((src / "recuperacion.json").read_text(encoding="utf-8"))
    out = {"mongo_ok": False, "artefactos_ok": False, "recuperacion_integral_ok": False, "errores": []}
    try:
        if sha256_file(src / "mongo" / "manifiesto.json") != rec["mongo_manifiesto_sha256"]:
            raise ArchiveError("manifiesto Mongo alterado respecto de recuperacion.json")
        rep = restore_db(src / "mongo", client[db_name])
        out["mongo"] = {"ok": rep["ok"], "problemas": rep["problemas"], "segundos_restauracion": rep["segundos_restauracion"],
                        "data_plus_index_mb": rep["medicion"]["data_plus_index_mb"], "objetos": rep["medicion"]["objects"],
                        "colecciones": {k: v["count"] for k, v in rep["colecciones"].items()}}
        out["mongo_ok"] = bool(rep["ok"])
    except (ArchiveError, OSError, KeyError, ValueError) as exc:
        out["errores"].append(f"mongo: {exc}")
    try:
        brep = pb.restore_bundle(src / "bundle", dest, root=root, cfg=cfg, git_repo=git_repo,
                                 expected_manifest_sha256=rec["bundle_manifiesto_sha256"])
        out["bundle"] = {k: v for k, v in brep.items() if k != "funcional"}
        out["funcional"] = brep.get("funcional")
        out["artefactos_ok"] = bool(brep["artefactos_ok"])
    except (pb.BundleError, OSError, KeyError, ValueError) as exc:
        out["errores"].append(f"bundle: {exc}")
    out["recuperacion_integral_ok"] = out["mongo_ok"] and out["artefactos_ok"]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Export/restauracion verificada (T11A/T11B)")
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
    ea = sub.add_parser("export-all")
    ea.add_argument("--db", required=True)
    ea.add_argument("--out", required=True, type=Path)
    ea.add_argument("--maintenance-confirmed", action="store_true")
    ea.add_argument("--allow-partial", action="store_true")
    ra = sub.add_parser("restore-all")
    ra.add_argument("--from", dest="src", required=True, type=Path)
    ra.add_argument("--db", required=True)
    ra.add_argument("--dest", required=True, type=Path)
    ra.add_argument("--report", type=Path)
    args = ap.parse_args(argv)
    if not _DB.match(args.db):
        print("Nombre de base invalido.", file=sys.stderr)
        return 2
    client = get_client()
    try:
        if args.cmd == "export-all":
            rec = export_all(client, args.db, args.out, maintenance_confirmed=args.maintenance_confirmed,
                             allow_partial=args.allow_partial)
            print(json.dumps(rec, ensure_ascii=False))
            return 0 if rec["bundle_integro"] else 1
        if args.cmd == "restore-all":
            res = restore_all(client, args.src, args.db, args.dest)
            if args.report:
                Path(args.report).write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            print(json.dumps({k: res[k] for k in ("mongo_ok", "artefactos_ok", "recuperacion_integral_ok", "errores")},
                             ensure_ascii=False))
            return 0 if res["recuperacion_integral_ok"] else 1
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
    except (ArchiveError, pb.BundleError) as exc:
        print(f"Rechazado: {exc}", file=sys.stderr)
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
