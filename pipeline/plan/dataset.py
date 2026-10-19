"""Dataset de las 14 fuentes para planificacion (T19 §1/§5): verificacion, sellado e importacion idempotente.

    python -m pipeline.plan.dataset --package <carpeta datos_preparados_v1> --db <base> [--audit <audit.json>] [--dry-run]

Antes de cualquier escritura: SHA-256 de los 14 libros == manifest.sources (== audit.json si existe) y re-normalizacion de los
libros con las reglas del script academico (pipeline.plan.normalize) contrastada REGISTRO A REGISTRO, campo a campo, con los CSV
derivados; cualquier diferencia => ImportRejected. Despues se sella el manifiesto (dataset_id = plds-<sha12 del contenido
canonico>) y se importa a colecciones separadas (plan_sales/plan_purchases/plan_credits/plan_quarantine + cabecera
plan_datasets) en staging -> current. No toca otras colecciones; no importa saldos_calculados ni balance_diario.
Dependencias: stdlib, openpyxl y pymongo (la imagen de produccion no incluye scripts/).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from pipeline.plan.normalize import (
    FIELDS,
    START,
    NormalizationError,
    normalize_all,
    sha256_file,
)

SCHEMA_VERSION = 1
HEADER_COLL = "plan_datasets"
COLLECTIONS = {"sales": "plan_sales", "purchases": "plan_purchases", "credits": "plan_credits", "quarantine": "plan_quarantine"}
CLASS_PARTITION = {"VENTA": "sales", "COMPRA": "purchases", "COMPRA_SIN_CARGO_REGISTRADO": "purchases",
                   "CREDITO": "credits", "CUARENTENA": "quarantine"}
CSV_FILES = {"sales": "ventas.csv", "purchases": "compras.csv", "credits": "creditos.csv", "quarantine": "cuarentena.csv"}
PROTECTED_DBS = frozenset({"demand_forecasting_dev", "demand_forecasting_v2", "demand_forecasting_pub"})
_DB_RE = re.compile(r"^[A-Za-z0-9_]{1,63}$")
BATCH = 5000
# campos del documento (sin dataset_id), en orden canonico
DOC_FIELDS = ["registro_id", "fecha", "producto_id", "producto", "categoria", "almacen", "unidad", "cantidad", "moneda",
              "importe", "tipo_documento", "documento_id", "clase", "grupo_repeticion", "ocurrencia",
              "dia_excluido_pronostico", "archivo", "hoja", "fila", "sha256_origen"]
_INTS = {"ocurrencia", "fila"}


class ImportRejected(Exception):
    """Rechazo de la fuente o de la operacion; `code` es estable y no incluye rutas ni secretos."""

    def __init__(self, code: str, message: str):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


@dataclass
class Prepared:
    header: dict                                   # cabecera sellada sin version/status/supersedes/imported_at
    docs: dict[str, list[dict]] = field(default_factory=dict)   # coleccion -> documentos (sin dataset_id)


def _mismatch(what: str) -> ImportRejected:
    return ImportRejected("DERIVADO_NO_COINCIDE", f"El derivado no coincide con los libros originales: {what}.")


def _dec_text(d: Decimal | None) -> str | None:
    return None if d is None else format(d, "f")


def _read_json(path: Path, what: str) -> dict:
    if not path.is_file():
        raise ImportRejected("ARCHIVO_FALTANTE", f"Falta {what}.")
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except ValueError:
        raise ImportRejected("MANIFIESTO_INVALIDO", f"{what} no es JSON valido.") from None
    if not isinstance(data, dict):
        raise ImportRejected("MANIFIESTO_INVALIDO", f"{what} no tiene la estructura esperada.")
    return data


def _load_derived(path: Path, what: str, expected_cols: list[str]) -> list[dict]:
    if not path.is_file():
        raise ImportRejected("ARCHIVO_FALTANTE", f"Falta {what}.")
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or list(reader.fieldnames) != expected_cols:
            raise ImportRejected("CSV_ESTRUCTURA_INVALIDA", f"Columnas inesperadas en {what}.")
        return list(reader)


def _dec_equal(a: Decimal | None, raw: str | None) -> bool:
    raw = (raw or "").strip()
    if a is None:
        return raw == ""
    try:
        return Decimal(raw) == a
    except InvalidOperation:
        return False


def _field_equal(name: str, rec: dict, raw: str | None) -> bool:
    v = rec[name]
    if name in ("cantidad", "importe"):
        return _dec_equal(v, raw)
    if name == "fecha":
        return (raw or "") == v.isoformat()
    if name in _INTS:
        return (raw or "").strip() == str(v)
    if isinstance(v, bool):
        return (raw or "") == str(v)
    return (raw or "") == v


def _audit_digests(audit_path: Path | None, names: set[str]) -> dict[str, str] | None:
    if audit_path is None or not Path(audit_path).is_file():
        return None
    audit = _read_json(Path(audit_path), "audit.json")
    files = audit.get("files")
    if not isinstance(files, list):
        raise ImportRejected("MANIFIESTO_INVALIDO", "audit.json no lista los archivos.")
    got = {f.get("file"): f.get("sha256") for f in files if isinstance(f, dict)}
    if set(got) != names:
        raise ImportRejected("FUENTE_ALTERADA", "audit.json no lista exactamente los 14 libros del manifiesto.")
    return got


def _canon_line(doc: dict) -> bytes:
    return json.dumps([doc[k] for k in DOC_FIELDS], ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _partition_fingerprint(docs: list[dict]) -> tuple[str, dict]:
    h = hashlib.sha256()
    amounts: dict[str, Decimal] = defaultdict(Decimal)
    for d in sorted(docs, key=lambda x: x["registro_id"]):
        h.update(_canon_line(d))
        h.update(b"\n")
        if d["importe"] is not None:
            amounts[d["moneda"]] += Decimal(d["importe"])
    return h.hexdigest(), {m: format(v, "f") for m, v in sorted(amounts.items())}


def prepare(package: Path, audit_path: Path | None = None) -> Prepared:
    """Verifica el paquete completo (sin escribir nada) y devuelve documentos y cabecera selladas."""
    package = Path(package)
    manifest = _read_json(package / "manifest.json", "manifest.json")
    sources = manifest.get("sources")
    if not isinstance(sources, list) or len(sources) != 14 or not all(isinstance(s, dict) for s in sources):
        raise ImportRejected("MANIFIESTO_INVALIDO", "El manifiesto debe listar exactamente 14 fuentes.")
    by_name = {s.get("archivo"): s for s in sources}
    if len(by_name) != 14:
        raise ImportRejected("MANIFIESTO_INVALIDO", "El manifiesto repite o no nombra alguna fuente.")
    try:
        window = (date.fromisoformat(manifest["window_start"]), date.fromisoformat(manifest["window_end"]))
        group_size = int(manifest["group_size"])
    except (KeyError, ValueError, TypeError):
        raise ImportRejected("MANIFIESTO_INVALIDO", "El manifiesto no declara ventana de fechas y tamano del grupo.") from None
    if window[0] != START:
        raise ImportRejected("MANIFIESTO_INVALIDO", "window_start del manifiesto no es el esperado.")

    # --- 1. huellas de los 14 libros: archivos == manifiesto == auditoria
    orig_dir = package / "00_originales"
    files = sorted(orig_dir.glob("*.xlsx")) if orig_dir.is_dir() else []
    if len(files) != 14 or {p.name for p in files} != set(by_name):
        raise ImportRejected("FUENTE_ALTERADA", "00_originales no contiene exactamente los 14 libros del manifiesto.")
    audit = _audit_digests(audit_path, set(by_name))
    digests: dict[str, str] = {}
    for p in files:
        digests[p.name] = sha256_file(p)
        if digests[p.name] != by_name[p.name].get("sha256"):
            raise ImportRejected("FUENTE_ALTERADA", f"El SHA-256 del libro {p.name} no coincide con el manifiesto.")
        if audit is not None and audit[p.name] != digests[p.name]:
            raise ImportRejected("FUENTE_ALTERADA", f"El SHA-256 del libro {p.name} no coincide con la auditoria.")

    # --- 2. re-normalizacion de los libros con las reglas del script academico
    try:
        rows, summaries, eligible = normalize_all(files, digests, group_size, window)
    except NormalizationError as exc:
        raise ImportRejected("FUENTE_ALTERADA" if exc.code == "LIBRO_ILEGIBLE" else "DERIVADO_NO_COINCIDE", exc.message) from None
    classes = Counter(r["clasificacion"] for r in rows)
    if len({r["registro_id"] for r in rows}) != len(rows):
        raise _mismatch("hay registro_id repetidos al re-normalizar")
    if manifest.get("source_rows") != len(rows) or manifest.get("class_counts") != dict(classes):
        raise _mismatch("el manifiesto declara otras filas o clases que los libros")
    if manifest.get("eligible_products") != eligible:
        raise _mismatch("el manifiesto declara otros productos elegibles")
    for s in summaries:
        m = by_name[s["archivo"]]
        declared = {k: Decimal(v) for k, v in (m.get("importes_por_moneda") or {}).items()}
        if (m.get("filas") != s["filas"] or m.get("clasificaciones") != s["clasificaciones"] or m.get("tipo") != s["tipo"]
                or declared != s["importes_por_moneda"]):
            raise _mismatch(f"filas, clases o importes del manifiesto no corresponden al libro {s['archivo']}")

    # --- 3. contraste registro a registro con los CSV derivados (todos los campos)
    expected = {r["registro_id"]: r for r in rows}
    seen: set[str] = set()
    for part, fname in CSV_FILES.items():
        derived = _load_derived(package / "01_normalizados" / fname, fname, FIELDS)
        for csv_row in derived:
            rid = csv_row["registro_id"]
            if rid in seen:
                raise _mismatch(f"registro duplicado en el derivado ({rid})")
            seen.add(rid)
            rec = expected.get(rid)
            if rec is None:
                raise _mismatch(f"registro sobrante en el derivado ({rid})")
            if CLASS_PARTITION[rec["clasificacion"]] != part:
                raise _mismatch(f"el registro {rid} esta en {fname} pero se clasifica {rec['clasificacion']}")
            for name in FIELDS:
                if not _field_equal(name, rec, csv_row.get(name)):
                    raise _mismatch(f"campo '{name}' del registro {rid} ({rec['archivo']} fila {rec['fila']})")
    if seen != set(expected):
        raise _mismatch(f"faltan {len(set(expected) - seen)} registros en el derivado")

    # --- 4. catalogo del grupo: el conjunto de productos coincide con la seleccion re-calculada
    group_csv = package / "02_grupo" / "productos.csv"
    gcols = ["producto_id", "almacen", "unidad", "seleccionado"]
    if not group_csv.is_file():
        raise ImportRejected("ARCHIVO_FALTANTE", "Falta productos.csv del grupo.")
    with group_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or any(c not in reader.fieldnames for c in gcols):
            raise ImportRejected("CSV_ESTRUCTURA_INVALIDA", "Columnas inesperadas en productos.csv.")
        chosen = {(g["producto_id"], g["almacen"], g["unidad"]) for g in reader if g["seleccionado"].strip().lower() == "true"}
    recomputed = {(r["producto_id"], r["almacen"], r["unidad"]) for r in rows if r["incluido_grupo"]}
    if chosen != recomputed or len(chosen) != group_size:
        raise _mismatch("productos.csv no coincide con la seleccion re-calculada")

    # --- 5. sellado
    docs: dict[str, list[dict]] = {c: [] for c in COLLECTIONS.values()}
    for r in rows:
        doc = {k: r[k] for k in DOC_FIELDS if k not in ("clase", "cantidad", "importe", "fecha")}
        doc.update(fecha=r["fecha"].isoformat(), cantidad=_dec_text(r["cantidad"]), importe=_dec_text(r["importe"]),
                   clase=r["clasificacion"])
        docs[COLLECTIONS[CLASS_PARTITION[r["clasificacion"]]]].append(doc)
    partitions, content = {}, hashlib.sha256()
    content.update(f"schema:{SCHEMA_VERSION}\n".encode())
    for fname in sorted(digests):
        content.update(f"book:{fname}:{digests[fname]}\n".encode())
    for part, coll in COLLECTIONS.items():
        fp, amounts = _partition_fingerprint(docs[coll])
        partitions[part] = {"collection": coll, "count": len(docs[coll]), "sha256": fp, "importes_por_moneda": amounts,
                            "clases": dict(Counter(d["clase"] for d in docs[coll]))}
        content.update(f"part:{part}:{len(docs[coll])}:{fp}\n".encode())
    content_sha = content.hexdigest()
    sales_dates = [d["fecha"] for d in docs[COLLECTIONS["sales"]]]
    if not sales_dates:
        raise _mismatch("no hay ventas")
    derived_files = {fname: sha256_file(package / "01_normalizados" / fname) for fname in CSV_FILES.values()}
    derived_files["productos.csv"] = sha256_file(group_csv)
    derived_files["manifest.json"] = sha256_file(package / "manifest.json")
    header = {
        "dataset_id": f"plds-{content_sha[:12]}", "content_sha256": content_sha, "schema_version": SCHEMA_VERSION,
        "window_start": window[0].isoformat(), "window_end": window[1].isoformat(), "sales_cutoff": max(sales_dates),
        "source_rows": len(rows), "counts": dict(classes), "partitions": partitions,
        "repeated_extra_rows": sum(1 for r in rows if r["ocurrencia"] > 1),
        "repeated_extra_rows_marked": sum(1 for d in docs[COLLECTIONS["purchases"]] if d["ocurrencia"] > 1),
        "sources": [{"archivo": s["archivo"], "tipo": s["tipo"], "sha256": s["sha256"], "filas": s["filas"]} for s in summaries],
        "derived_files": derived_files, "group": {"size": group_size, "eligible_products": eligible},
        "audit_checked": audit is not None, "normalization_version": manifest.get("version"),
        "currencies": sorted({r["moneda"] for r in rows}),
    }
    return Prepared(header, docs)


def ensure_indexes(db) -> None:
    db[HEADER_COLL].create_index([("dataset_id", 1)], name="dataset_id_unique", unique=True)
    db[HEADER_COLL].create_index([("status", 1), ("version", -1)], name="status_version")
    for coll in COLLECTIONS.values():
        db[coll].create_index([("dataset_id", 1), ("registro_id", 1)], name="dataset_registro_unique", unique=True)
        db[coll].create_index([("dataset_id", 1), ("producto_id", 1), ("fecha", 1)], name="dataset_producto_fecha")


def _result(action: str, header: dict, version: int | None) -> dict:
    return {"action": action, "dataset_id": header["dataset_id"], "version": version, "source_rows": header["source_rows"],
            "counts": header["counts"], "collections": {p["collection"]: p["count"] for p in header["partitions"].values()},
            "sales_cutoff": header["sales_cutoff"], "audit_checked": header["audit_checked"]}


def _cleanup(db, dataset_id: str) -> None:
    for coll in COLLECTIONS.values():
        db[coll].delete_many({"dataset_id": dataset_id})
    db[HEADER_COLL].delete_many({"dataset_id": dataset_id, "status": "staging"})


def write_dataset(db, prep: Prepared, dry_run: bool = False) -> dict:
    if db.name in PROTECTED_DBS:
        raise ImportRejected("BASE_PROTEGIDA", "No se escribe en bases de desarrollo, v2 ni publicadas.")
    h, heads = prep.header, db[HEADER_COLL]
    did = h["dataset_id"]
    same = heads.find_one({"dataset_id": did}, {"_id": 0})
    if same and same["status"] == "current":
        return _result("unchanged", h, same["version"])
    if same and same["status"] == "superseded":
        raise ImportRejected("VERSION_SUSTITUIDA", "Ese contenido ya fue sustituido por una version posterior.")
    cur = heads.find_one({"status": "current"}, {"_id": 0}, sort=[("version", -1)])
    last = heads.find_one({"dataset_id": {"$ne": did}}, {"version": 1}, sort=[("version", -1)])
    version = (last["version"] if last else 0) + 1
    action = "created" if last is None else "new_version"
    if dry_run:
        return _result("would_" + action, h, version)
    ensure_indexes(db)
    _cleanup(db, did)               # intento interrumpido de este mismo dataset: se limpia por su propio id (nunca otros)
    imported_at = datetime.now(UTC).replace(tzinfo=None, microsecond=0)
    heads.insert_one({**h, "version": version, "status": "staging", "supersedes": cur["dataset_id"] if cur else None,
                      "imported_at": imported_at})
    try:
        for part in COLLECTIONS.values():
            docs = prep.docs[part]
            for i in range(0, len(docs), BATCH):
                db[part].insert_many([{"dataset_id": did, **d} for d in docs[i:i + BATCH]], ordered=False)
            if db[part].count_documents({"dataset_id": did}) != len(docs):
                raise ImportRejected("ESCRITURA_INCOMPLETA", "El numero de documentos escritos no coincide.")
    except BaseException:
        _cleanup(db, did)
        raise
    heads.update_one({"dataset_id": did, "status": "staging"}, {"$set": {"status": "current"}})
    if cur:
        heads.update_one({"dataset_id": cur["dataset_id"], "status": "current"}, {"$set": {"status": "superseded"}})
    return _result(action, h, version)


def default_audit(package: Path) -> Path:
    return Path(package).resolve().parent / "auditoria_14_excel" / "audit.json"


def run(package, db, audit_path=None, dry_run: bool = False) -> dict:
    if db.name in PROTECTED_DBS:
        raise ImportRejected("BASE_PROTEGIDA", "No se escribe en bases de desarrollo, v2 ni publicadas.")
    return write_dataset(db, prepare(Path(package), audit_path), dry_run)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Verifica, sella e importa el dataset de 14 fuentes para planificacion")
    ap.add_argument("--package", required=True)
    ap.add_argument("--db", required=True)
    ap.add_argument("--audit", default=None, help="audit.json; por defecto el hermano auditoria_14_excel/ si existe")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    if not _DB_RE.match(args.db):
        print("Nombre de base invalido.", file=sys.stderr)
        return 2
    if args.db in PROTECTED_DBS:
        print("Importacion rechazada [BASE_PROTEGIDA]: no se escribe en bases protegidas.", file=sys.stderr)
        return 1
    try:
        if args.audit and not Path(args.audit).is_file():
            raise ImportRejected("ARCHIVO_FALTANTE", "Falta audit.json indicado.")
        audit = Path(args.audit) if args.audit else default_audit(Path(args.package))
        prep = prepare(Path(args.package), audit)
        from pymongo import MongoClient
        client = MongoClient(os.environ.get("MONGODB_URI", "mongodb://127.0.0.1:27017"), serverSelectionTimeoutMS=3000)
        try:
            res = write_dataset(client[args.db], prep, args.dry_run)
        finally:
            client.close()
    except ImportRejected as exc:
        print(f"Importacion rechazada {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 - sin URI ni rutas
        print(f"Importacion fallida ({type(exc).__name__}).", file=sys.stderr)
        return 1
    print(json.dumps(res, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
