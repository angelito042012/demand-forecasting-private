"""T11A: crea la base NUEVA de publicacion copiando (solo lectura del origen) lo permitido por config/t11_publication.json.

    python -m scripts.build_publication_db [--source demand_forecasting_v2] [--target demand_forecasting_pub]
                                           [--out artifacts/private/t11a] [--overwrite] [--no-dump-children]

* Copia: sales, credit_notes, imports, import_conflicts, import_rejects, month_reservations, las corridas historicas
  indicadas con sus hijos (mismos _id/run_id/children_ref) y un puntero activo nuevo hacia la historica activa.
* No copia: sessions, users, login_*, jobs, scheduler_ticks, run_pointer del origen, corridas generadas ni fallidas.
  Las corridas omitidas se ARCHIVAN fuera de MongoDB (carpeta privada con manifiesto sha256; no se borran del origen).
* Crea indices (ensure_schema + importer.ensure_indexes), se niega a sobrescribir una base existente sin --overwrite y
  verifica conteos y hash de contenido por coleccion (origen vs copia). El origen solo se lee.
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from bson import json_util

from pipeline.data.importer import ensure_indexes, get_client
from pipeline.publish.archive import (
    CHILD_COLLECTIONS,
    FORBIDDEN_DBS,
    JSON_OPTS,
    SECRET_COLLECTIONS,
    ArchiveError,
    ContentHash,
    check_runs,
    collection_hash,
    index_specs,
    measure,
    now_iso,
    quota_use,
    sha256_file,
)
from pipeline.publish.schema import SCHEMA_VERSION, ensure_schema

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "t11_publication.json"
BATCH = 4000
RUN_FIELDS = ("run_id", "status", "kind", "cutoff", "children_ref", "counts", "published_at", "error")


def _copy(src, dst, flt: dict | None = None) -> dict:
    """Copia documentos tal cual (mismo _id y orden de campos) y devuelve el hash de lo LEIDO en el origen."""
    h, buf = ContentHash(), []
    for doc in src.find(flt or {}, batch_size=BATCH):
        h.add(doc)
        buf.append(doc)
        if len(buf) >= BATCH:
            dst.insert_many(buf, ordered=False)
            buf = []
    if buf:
        dst.insert_many(buf, ordered=False)
    return h.result()


def _children_id(run: dict) -> str:
    return run.get("children_ref") or run["run_id"]


def _dump_run(sdb, run: dict, out: Path) -> dict:
    """Archiva el documento de la corrida y sus hijos (NDJSON.gz) fuera de MongoDB; devuelve entradas con sha256."""
    cid, files, hashes = _children_id(run), [], {}
    rp = out / f"{run['run_id']}.run.json"
    rp.write_text(json_util.dumps(run, json_options=JSON_OPTS, indent=1) + "\n", encoding="utf-8")
    files.append(rp)
    for name in CHILD_COLLECTIONS:
        h = ContentHash()
        n = sdb[name].count_documents({"run_id": cid})
        path = out / f"{cid.replace('~', '_')}.{name}.ndjson.gz"
        if n:
            with gzip.open(path, "wt", encoding="utf-8", newline="\n", compresslevel=6) as fh:
                for d in sdb[name].find({"run_id": cid}, batch_size=BATCH):
                    h.add(d)
                    fh.write(json_util.dumps(d, json_options=JSON_OPTS) + "\n")
            files.append(path)
        hashes[name] = h.result()
    return {"run_id": run["run_id"], "children_id": cid, "hijos": hashes,
            "archivos": [{"name": f.name, "sha256": sha256_file(f), "size_bytes": f.stat().st_size} for f in files]}


def _hash_children_only(sdb, run: dict) -> dict:
    cid = _children_id(run)
    return {"run_id": run["run_id"], "children_id": cid,
            "hijos": {n: collection_hash(sdb[n], {"run_id": cid}) for n in CHILD_COLLECTIONS}, "archivos": []}


def build_publication(client, cfg: dict, *, source: str | None = None, target: str | None = None, out_dir: Path,
                      overwrite: bool = False, dump_children: bool = True, artifacts_dir: Path | None = None) -> dict:
    source, target = source or cfg["base_origen_solo_lectura"], target or cfg["base_publicacion"]
    if target in FORBIDDEN_DBS or target == source:
        raise ArchiveError(f"la base destino '{target}' esta protegida o es el origen")
    if source not in client.list_database_names():
        raise ArchiveError("la base origen no existe")
    sdb, tdb = client[source], client[target]
    existing = target in client.list_database_names() and bool(tdb.list_collection_names())
    if existing and not overwrite:
        raise ArchiveError(f"la base '{target}' ya existe: se rechaza la sobrescritura (use --overwrite explicito)")
    t0 = time.perf_counter()
    hist = list(cfg["corridas_historicas"])
    active = cfg["puntero_activo"]
    if active not in hist:
        raise ArchiveError("el puntero activo debe ser una de las corridas historicas")
    runs = {r["run_id"]: r for r in sdb.runs.find({})}
    for rid in hist:
        if rid not in runs or runs[rid]["status"] not in ("completed", "superseded"):
            raise ArchiveError(f"la corrida historica {rid} no esta legible en el origen")
    if runs[active]["status"] != "completed":
        raise ArchiveError("la corrida activa debe estar completed")
    if existing:
        client.drop_database(target)
    tdb = client[target]
    src_hash: dict = {}
    for name in cfg["copiar_colecciones"]:
        if name in sdb.list_collection_names():
            src_hash[name] = _copy(sdb[name], tdb[name])
    # corridas historicas y sus hijos (mismos ids; children_ref se conserva tal cual)
    src_hash["runs"] = _copy(sdb.runs, tdb.runs, {"run_id": {"$in": hist}})
    for name in CHILD_COLLECTIONS:
        h = ContentHash()
        for rid in hist:
            part = _copy(sdb[name], tdb[name], {"run_id": _children_id(runs[rid])})
            h.count += part["count"]
            h._acc = (h._acc + int(part["content_sha256"], 16)) & ((1 << 256) - 1)
        src_hash[name] = h.result()
    now = datetime.now(UTC).replace(microsecond=0)
    tdb.run_pointer.insert_one({"_id": "active", "run_id": active, "published_at": runs[active]["published_at"], "updated_at": now})
    ensure_schema(tdb)
    ensure_indexes(tdb)
    # verificacion independiente: se relee la copia
    verif, problems = {}, []
    for name, want in src_hash.items():
        got = collection_hash(tdb[name])
        ok = got == want
        verif[name] = {"origen": want, "copia": got, "ok": ok}
        if not ok:
            problems.append(f"{name}: conteo/hash distinto entre origen y copia")
    chk = check_runs(tdb)
    problems += chk["problemas"]
    leaked = sorted(set(SECRET_COLLECTIONS) & set(tdb.list_collection_names()))
    if leaked:
        problems.append(f"colecciones secretas copiadas: {leaked}")
    # exclusiones y archivo
    out_dir = Path(out_dir)
    arch_dir = out_dir / "archivo"
    arch_dir.mkdir(parents=True, exist_ok=True)
    omitted_runs = [r for rid, r in sorted(runs.items()) if rid not in hist]
    archived = []
    for r in omitted_runs:
        entry = (_dump_run(sdb, r, arch_dir) if dump_children else _hash_children_only(sdb, r))
        entry.update({k: r.get(k) for k in ("status", "kind", "cutoff", "counts")})
        archived.append(entry)
    copied = set(cfg["copiar_colecciones"]) | {"runs", "run_pointer", *CHILD_COLLECTIONS}
    excluded_colls = {n: {"count": sdb[n].count_documents({}), "motivo": "secreta u operativa" if n in SECRET_COLLECTIONS
                          else "fuera de la politica"}
                      for n in sorted(sdb.list_collection_names()) if n not in copied}
    excluded_colls["run_pointer(origen)"] = {"count": sdb.run_pointer.count_documents({}),
                                             "motivo": "se crea un puntero nuevo hacia la historica activa"}
    big = []
    if artifacts_dir and Path(artifacts_dir).is_dir():
        big = [{"name": p.relative_to(artifacts_dir).as_posix(), "sha256": sha256_file(p), "size_bytes": p.stat().st_size}
               for p in sorted(Path(artifacts_dir).rglob("*")) if p.is_file() and not p.name.endswith(".tmp")]
    med = measure(tdb)
    manifest = {
        "version": cfg["version"], "creado_utc": now_iso(), "base_origen": source, "base_publicacion": target,
        "schema_version": SCHEMA_VERSION, "etiqueta": cfg["etiqueta"],
        "colecciones": {n: {"count": v["copia"]["count"], "content_sha256": v["copia"]["content_sha256"],
                            "verificada_contra_origen": v["ok"]} for n, v in verif.items()},
        "indices": {n: [s["name"] for s in index_specs(tdb[n])] for n in sorted(tdb.list_collection_names())},
        "corridas_copiadas": [{k: (str(r.get(k)) if k == "published_at" else r.get(k)) for k in RUN_FIELDS}
                              for rid in hist for r in [runs[rid]]],
        "puntero_activo": chk["pointer"], "corridas_verificadas": chk["runs"],
        "exclusiones": {"colecciones": excluded_colls,
                        "corridas_omitidas": [{k: e.get(k) for k in ("run_id", "status", "kind", "cutoff", "counts", "hijos")}
                                              for e in archived]},
        "archivo_privado": {"carpeta": "artifacts/private/t11a/archivo", "corridas": archived,
                            "artefactos_grandes_por_hash": big,
                            "nota": "las corridas omitidas siguen en el origen (no se borran); modelos .joblib, NPZ de "
                                    "simulacion, CSV minimos y logs quedan fuera de MongoDB, referenciados por hash"},
        "medicion": {"data_mb": med["data_mb"], "index_mb": med["index_mb"], "data_plus_index_mb": med["data_plus_index_mb"],
                     "storage_plus_index_mb": med["storage_plus_index_mb"],
                     "nota": "medicion directa sobre la base recien copiada; la definitiva es la de la base restaurada"},
        "cuota": quota_use(med["data_plus_index_mb"], cfg["cuota_atlas_free_mb"], cfg["objetivo_uso_maximo_fraccion"]),
        "problemas": problems, "ok": not problems, "segundos": round(time.perf_counter() - t0, 2),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "manifiesto_publicacion.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    (arch_dir / "manifiesto_archivo.json").write_text(json.dumps(
        {"creado_utc": manifest["creado_utc"], "corridas": archived, "artefactos_grandes_por_hash": big},
        ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    docs = {k: manifest[k] for k in ("version", "creado_utc", "base_origen", "base_publicacion", "schema_version", "etiqueta",
                                     "colecciones", "indices", "puntero_activo", "medicion", "cuota", "ok", "segundos")}
    docs["corridas_copiadas"] = [{k: r[k] for k in ("run_id", "status", "kind", "cutoff", "counts")}
                                 for r in manifest["corridas_copiadas"]]
    docs["exclusiones"] = {"colecciones": excluded_colls,
                           "corridas_omitidas": [{k: e.get(k) for k in ("run_id", "status", "kind", "cutoff", "counts")}
                                                 for e in archived]}
    docs["archivo"] = {"archivos": sum(len(e["archivos"]) for e in archived),
                       "bytes": sum(a["size_bytes"] for e in archived for a in e["archivos"]),
                       "artefactos_grandes_por_hash": len(big)}
    (out_dir / "manifiesto_publicacion_docs.json").write_text(
        json.dumps(docs, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    return manifest


def main(argv=None) -> int:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    ap = argparse.ArgumentParser(description="Crea la base de publicacion (T11A)")
    ap.add_argument("--source", default=cfg["base_origen_solo_lectura"])
    ap.add_argument("--target", default=cfg["base_publicacion"])
    ap.add_argument("--out", type=Path, default=ROOT / "artifacts" / "private" / "t11a")
    ap.add_argument("--artifacts-dir", type=Path, default=ROOT / "artifacts" / "private" / "final")
    ap.add_argument("--overwrite", action="store_true", help="elimina y recrea la base destino si ya existe")
    ap.add_argument("--no-dump-children", action="store_true", help="solo hash de los hijos de corridas omitidas")
    args = ap.parse_args(argv)
    client = get_client()
    try:
        man = build_publication(client, cfg, source=args.source, target=args.target, out_dir=args.out,
                                overwrite=args.overwrite, dump_children=not args.no_dump_children,
                                artifacts_dir=args.artifacts_dir)
    except ArchiveError as exc:
        print(f"Rechazado: {exc}", file=sys.stderr)
        return 1
    finally:
        client.close()
    print(json.dumps({"ok": man["ok"], "problemas": man["problemas"], "colecciones": {k: v["count"] for k, v in man["colecciones"].items()},
                      "medicion": man["medicion"], "cuota": man["cuota"], "segundos": man["segundos"]}, ensure_ascii=False))
    return 0 if man["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
