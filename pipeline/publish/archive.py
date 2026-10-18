"""T11A: utilidades de copia, exportacion, restauracion y verificacion de bases de publicacion (solo MongoDB local).

* Hash de contenido por coleccion: suma modular (mod 2^256) de los sha256 de `bson.encode(doc)` de cada documento
  (independiente del orden de los documentos; sensible a tipos, campos y valores). Se recalcula igual desde la base
  origen, la copia, el export NDJSON.gz y la restauracion.
* El export excluye SIEMPRE las colecciones secretas/operativas (`sessions`, `users`, `login_*`, `jobs`,
  `scheduler_ticks`) y las bases protegidas nunca se sobrescriben.
* Consistencia del export: snapshot LOGICO documentado = sin corridas en `staging` (no hay escritores activos),
  conteos iguales antes y despues de leer cada coleccion; si cambian, el export se aborta.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import time
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

import bson
from bson import json_util

from .schema import SCHEMA_VERSION

FORBIDDEN_DBS = frozenset({"demand_forecasting_v2", "demand_forecasting_dev", "admin", "local", "config"})
SECRET_COLLECTIONS = ("sessions", "users", "login_attempts", "login_budget", "jobs", "scheduler_ticks")
CHILD_COLLECTIONS = ("forecasts", "recommendations", "backtests")
READABLE = ("completed", "superseded")
EXPORT_VERSION = "t11a-backup-1"
_MASK = (1 << 256) - 1
JSON_OPTS = json_util.CANONICAL_JSON_OPTIONS


class ArchiveError(RuntimeError):
    """Operacion de copia/export/restauracion rechazada o verificacion fallida."""


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------ hash de contenido
class ContentHash:
    """Acumulador conmutativo de documentos (multiconjunto)."""

    def __init__(self) -> None:
        self.count, self._acc = 0, 0

    def add(self, doc: dict) -> None:
        self._acc = (self._acc + int.from_bytes(hashlib.sha256(bson.encode(doc)).digest(), "big")) & _MASK
        self.count += 1

    def hexdigest(self) -> str:
        return f"{self._acc:064x}"

    def result(self) -> dict:
        return {"count": self.count, "content_sha256": self.hexdigest()}


def content_hash(docs: Iterable[dict]) -> dict:
    h = ContentHash()
    for d in docs:
        h.add(d)
    return h.result()


def collection_hash(coll, flt: dict | None = None) -> dict:
    return content_hash(coll.find(flt or {}, batch_size=2000))


# ------------------------------------------------------------------ indices y estadisticas
def index_specs(coll) -> list[dict]:
    out = []
    for ix in coll.list_indexes():
        if ix["name"] == "_id_":
            continue
        spec = {"name": ix["name"], "key": [[k, v] for k, v in ix["key"].items()]}
        for opt in ("unique", "sparse", "expireAfterSeconds", "partialFilterExpression"):
            if opt in ix:
                spec[opt] = ix[opt]
        out.append(spec)
    return sorted(out, key=lambda s: s["name"])


def create_indexes(coll, specs: list[dict]) -> None:
    for s in specs:
        opts = {k: s[k] for k in ("unique", "sparse", "expireAfterSeconds", "partialFilterExpression") if k in s}
        coll.create_index([(k, v) for k, v in s["key"]], name=s["name"], **opts)


def measure(db) -> dict:
    """Tamanos REALES de la base: datos (dataSize) + indices (indexSize); storageSize como dato complementario."""
    st = db.command("dbstats")
    per = {}
    for name in sorted(db.list_collection_names()):
        c = db.command("collstats", name)
        per[name] = {"count": c["count"], "data_bytes": c["size"], "storage_bytes": c["storageSize"],
                     "index_bytes": c["totalIndexSize"]}
    mb = lambda b: round(b / 1048576, 3)
    return {"collections": per, "data_mb": mb(st["dataSize"]), "index_mb": mb(st["indexSize"]),
            "data_plus_index_mb": mb(st["dataSize"] + st["indexSize"]), "storage_mb": mb(st["storageSize"]),
            "storage_plus_index_mb": mb(st["storageSize"] + st["indexSize"]), "objects": st["objects"]}


def quota_use(measured_mb: float, quota_mb: float = 512.0, target: float = 0.6) -> dict:
    return {"cuota_mb": quota_mb, "uso_mb": measured_mb, "uso_fraccion": round(measured_mb / quota_mb, 4),
            "objetivo_fraccion": target, "cumple_objetivo": measured_mb <= quota_mb * target}


# ------------------------------------------------------------------ comprobaciones de corridas
def check_runs(db) -> dict:
    """Corridas legibles con sus hijos (children_ref o run_id), sin hijos huerfanos y puntero valido."""
    problems, runs_out, referenced = [], [], set()
    for run in db.runs.find({}):
        cid = run.get("children_ref") or run["run_id"]
        entry = {"run_id": run["run_id"], "status": run["status"], "kind": run.get("kind"),
                 "children_ref": run.get("children_ref"), "counts": run.get("counts")}
        if run["status"] in READABLE:
            referenced.add(cid)
            c = run.get("counts") or {}
            got = {"forecasts_sku": db.forecasts.count_documents({"run_id": cid, "level": "sku"}),
                   "forecasts_categoria": db.forecasts.count_documents({"run_id": cid, "level": "categoria"}),
                   "recommendations": db.recommendations.count_documents({"run_id": cid}),
                   "backtests": db.backtests.count_documents({"run_id": cid})}
            entry["children"] = got
            if not c:
                problems.append(f"{run['run_id']}: sin counts")
            for k, v in got.items():
                if c.get(k) != v:
                    problems.append(f"{run['run_id']}: {k} esperado {c.get(k)}, hallado {v}")
        runs_out.append(entry)
    for name in CHILD_COLLECTIONS:
        orphans = set(db[name].distinct("run_id")) - referenced
        if orphans:
            problems.append(f"{name}: hijos huerfanos de {sorted(orphans)[:3]}")
    ptr = db.run_pointer.find_one({"_id": "active"})
    if ptr is not None:
        tgt = db.runs.find_one({"run_id": ptr["run_id"]}, {"status": 1})
        if tgt is None or tgt["status"] not in READABLE:
            problems.append("puntero activo apunta a una corrida inexistente o no legible")
    return {"runs": sorted(runs_out, key=lambda r: r["run_id"]), "pointer": (ptr or {}).get("run_id"),
            "problemas": problems, "ok": not problems}


def _guard_target(name: str, *, restore: bool = False) -> None:
    if name in FORBIDDEN_DBS:
        raise ArchiveError(f"la base '{name}' esta protegida: T11A no escribe en ella")


# ------------------------------------------------------------------ export
def _dump_collection(coll, path: Path) -> dict:
    h = ContentHash()
    with gzip.open(path, "wt", encoding="utf-8", newline="\n", compresslevel=6) as fh:
        for doc in coll.find({}, batch_size=2000):
            h.add(doc)
            fh.write(json_util.dumps(doc, json_options=JSON_OPTS) + "\n")
    return {**h.result(), "file": path.name, "file_sha256": sha256_file(path), "file_bytes": path.stat().st_size}


def export_db(db, out_dir: Path, *, exclude: Iterable[str] = SECRET_COLLECTIONS, artifacts: list[dict] | None = None,
              allow_staging: bool = False, only: Iterable[str] | None = None) -> dict:
    """Exporta `db` a `out_dir`: <coleccion>.ndjson.gz + indices.json + manifiesto.json. Devuelve el manifiesto."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if any(out_dir.iterdir()):
        raise ArchiveError("el directorio de export no esta vacio")
    t0 = time.perf_counter()
    exclude = set(exclude)
    if not allow_staging and db.runs.count_documents({"status": "staging"}):
        raise ArchiveError("hay corridas en staging (escritores activos): detenga la publicacion antes de exportar")
    names = [n for n in sorted(db.list_collection_names()) if n not in exclude and not n.startswith("system.")
             and (only is None or n in set(only))]
    cols, idx = {}, {}
    for n in names:
        before = db[n].count_documents({})
        info = _dump_collection(db[n], out_dir / f"{n}.ndjson.gz")
        if db[n].count_documents({}) != before or info["count"] != before:
            raise ArchiveError(f"{n}: la coleccion cambio durante el export (snapshot logico roto)")
        cols[n] = info
        idx[n] = index_specs(db[n])
    (out_dir / "indices.json").write_text(json.dumps(idx, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    chk = check_runs(db)
    man = {"version": EXPORT_VERSION, "creado_utc": now_iso(), "base_origen": db.name, "schema_version": SCHEMA_VERSION,
           "colecciones": cols, "indices_sha256": sha256_file(out_dir / "indices.json"),
           "excluidas": sorted(exclude & set(db.list_collection_names())), "corridas": chk["runs"], "puntero_activo": chk["pointer"],
           "consistencia": "snapshot logico: sin corridas en staging; conteos iguales antes/despues de cada coleccion",
           "artefactos_privados": artifacts or [], "segundos_export": round(time.perf_counter() - t0, 2),
           "bytes_comprimidos": sum(c["file_bytes"] for c in cols.values())}
    (out_dir / "manifiesto.json").write_text(json.dumps(man, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    return man


def load_manifest(export_dir: Path) -> dict:
    p = Path(export_dir) / "manifiesto.json"
    if not p.is_file():
        raise ArchiveError("export sin manifiesto.json")
    man = json.loads(p.read_text(encoding="utf-8"))
    if man.get("version") != EXPORT_VERSION:
        raise ArchiveError("version de export desconocida")
    if set(man["colecciones"]) & set(SECRET_COLLECTIONS):
        raise ArchiveError("el export contiene colecciones secretas: se rechaza")
    return man


def verify_export_files(export_dir: Path) -> list[str]:
    """Hash de cada archivo del export contra el manifiesto (detecta alteraciones antes de restaurar)."""
    export_dir = Path(export_dir)
    man = load_manifest(export_dir)
    bad = []
    for n, c in man["colecciones"].items():
        p = export_dir / c["file"]
        if not p.is_file() or sha256_file(p) != c["file_sha256"]:
            bad.append(f"{n}: archivo alterado o ausente")
    ix = export_dir / "indices.json"
    if not ix.is_file() or sha256_file(ix) != man["indices_sha256"]:
        bad.append("indices.json alterado o ausente")
    return bad


# ------------------------------------------------------------------ restauracion y verificacion
def _read_ndjson(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json_util.loads(line, json_options=JSON_OPTS)


def restore_db(export_dir: Path, db, *, batch: int = 2000, verify_files: bool = True) -> dict:
    """Restaura en `db` (que debe estar VACIA e inexistente) y verifica todo. Devuelve el reporte."""
    export_dir = Path(export_dir)
    _guard_target(db.name, restore=True)
    man = load_manifest(export_dir)
    if db.name == man.get("base_origen"):
        raise ArchiveError("la restauracion debe ir a una base DIFERENTE de la base de origen")
    if db.name in db.client.list_database_names() and db.list_collection_names():
        raise ArchiveError(f"la base destino '{db.name}' ya existe y no esta vacia")
    if verify_files:
        bad = verify_export_files(export_dir)
        if bad:
            raise ArchiveError("export alterado: " + "; ".join(bad))
    t0 = time.perf_counter()
    idx = json.loads((export_dir / "indices.json").read_text(encoding="utf-8"))
    for n, c in man["colecciones"].items():
        buf = []
        for doc in _read_ndjson(export_dir / c["file"]):
            buf.append(doc)
            if len(buf) >= batch:
                db[n].insert_many(buf, ordered=False)
                buf = []
        if buf:
            db[n].insert_many(buf, ordered=False)
        create_indexes(db[n], idx.get(n, []))
    seg = round(time.perf_counter() - t0, 2)
    rep = verify_restored(db, man, export_dir)
    rep["segundos_restauracion"] = seg
    rep["bytes_comprimidos"] = man.get("bytes_comprimidos")
    rep["medicion"] = measure(db)
    return rep


def verify_restored(db, man: dict, export_dir: Path | None = None) -> dict:
    """Conteos, hash de contenido por coleccion, indices, estado de corridas, children_ref y puntero. No lanza: devuelve
    `ok` y la lista de `problemas`."""
    problems, per = [], {}
    names = set(db.list_collection_names())
    for n in sorted(set(man["colecciones"]) | names):
        want = man["colecciones"].get(n)
        if want is None:
            problems.append(f"{n}: coleccion no esperada")
            continue
        if n not in names:
            problems.append(f"{n}: ausente")
            continue
        got = collection_hash(db[n])
        ok = got["count"] == want["count"] and got["content_sha256"] == want["content_sha256"]
        per[n] = {"count": got["count"], "esperado": want["count"], "content_sha256": got["content_sha256"], "ok": ok}
        if not ok:
            problems.append(f"{n}: conteo/hash de contenido distinto del manifiesto")
    if export_dir is not None:
        idx = json.loads((Path(export_dir) / "indices.json").read_text(encoding="utf-8"))
        for n in man["colecciones"]:
            if n in names and index_specs(db[n]) != sorted(idx.get(n, []), key=lambda s: s["name"]):
                problems.append(f"{n}: indices distintos de los exportados")
    chk = check_runs(db)
    problems += chk["problemas"]
    want_runs = {r["run_id"]: r["status"] for r in man.get("corridas", [])}
    got_runs = {r["run_id"]: r["status"] for r in chk["runs"]}
    if want_runs != got_runs:
        problems.append("estado de las corridas distinto del manifiesto")
    if chk["pointer"] != man.get("puntero_activo"):
        problems.append("puntero activo distinto del manifiesto")
    leaked = sorted(set(SECRET_COLLECTIONS) & names)
    if leaked:
        problems.append(f"colecciones secretas presentes: {leaked}")
    return {"ok": not problems, "problemas": problems, "colecciones": per, "corridas": chk["runs"],
            "puntero": chk["pointer"], "base": db.name}
