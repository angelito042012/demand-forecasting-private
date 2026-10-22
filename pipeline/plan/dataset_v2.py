"""Dataset v2 (T20 §1): 14 libros (v1) + octubre 01-20 verificado contra SQL + parcial del 21/10 en coleccion aparte.

    python -m pipeline.plan.dataset_v2 --package <datos_preparados_v1> --october <octubre.xlsx> --sql-report <informe.json>
        --partial-csv <ventas_20261021_parcial_sql.csv> --db <base> [--audit <audit.json>] [--dry-run]

Antes de escribir: (1) dataset.prepare (14 libros, contraste registro a registro); (2) octubre.xlsx normalizado con las
mismas reglas (ventana 01-20/10, contador de ocurrencias nuevo); (3) SHA-256 del libro == informe.json, el informe declara
que Excel y SQL coinciden y sus lineas son las filas normalizadas; (4) el CSV parcial solo trae el 21/10.
El parcial va a `plan_sales_partial` y NUNCA a `plan_sales`: no se usa para pronosticar. Importacion idempotente y versionada
con las mismas reglas que v1 (el v1 vigente pasa a `superseded`; los planes v1 lo siguen leyendo por id).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from collections import Counter
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from pipeline.plan import dataset as ds
from pipeline.plan.dataset import (
    COLLECTIONS,
    PROTECTED_DBS,
    ImportRejected,
    Prepared,
    _dec_text,
    _partition_fingerprint,
    write_dataset,
)
from pipeline.plan.normalize import NormalizationError, normalize_book, sha256_file

SCHEMA_TAG = "v2"
OCTOBER_NAME = "octubre.xlsx"
OCTOBER_WINDOW = (date(2026, 10, 1), date(2026, 10, 20))
CUTOFF = OCTOBER_WINDOW[1]
PARTIAL_DATE = "2026-10-21"
PARTIAL_COLL = "plan_sales_partial"
PARTIAL_COLS = ["fecha", "hora_documento", "tipo_documento", "documento", "producto_id_sql", "almacen", "unidad", "cantidad",
                "equivalencia", "total"]
PARTIAL_FIELDS = ["linea", "fecha", "hora_documento", "tipo_documento", "documento", "producto_id", "almacen", "unidad",
                  "cantidad", "total"]


def _sha_hex(v) -> bool:
    return isinstance(v, str) and len(v) == 64 and all(c in "0123456789abcdef" for c in v)


def _json(path: Path, what: str) -> dict:
    return ds._read_json(Path(path), what)


def _dec(raw, what: str) -> Decimal:
    try:
        d = Decimal((raw or "").strip())
    except InvalidOperation:
        raise ImportRejected("PARCIAL_INVALIDO", f"{what} no es un numero.") from None
    if not d.is_finite():
        raise ImportRejected("PARCIAL_INVALIDO", f"{what} no es finito.")
    return d


def _plain(d: Decimal) -> str:
    return format(d.normalize(), "f") if d != 0 else "0"


def _code(raw: str) -> str:
    """Codigo SQL (con ceros a la izquierda) -> codigo original, conservado como texto de digitos sin ceros iniciales."""
    v = (raw or "").strip()
    if not v.isdigit():
        raise ImportRejected("PARCIAL_INVALIDO", "producto_id_sql no es un codigo numerico.")
    return v.lstrip("0") or "0"


def verify_october(october: Path, report: dict, rows: list[dict]) -> dict:
    """Exige que el informe SQL corresponda a ESTE libro y a estas filas; devuelve la verificacion para la cabecera."""
    sha = sha256_file(october)
    libros = report.get("libros")
    if not isinstance(libros, dict) or libros.get(OCTOBER_NAME) != sha:
        raise ImportRejected("FUENTE_ALTERADA", "El SHA-256 de octubre.xlsx no coincide con el informe de conciliacion SQL.")
    comp = (report.get("ventas_excel_vs_sql") or {}).get(OCTOBER_NAME)
    if not isinstance(comp, dict) or comp.get("coincide") is not True:
        raise ImportRejected("SQL_NO_COINCIDE", "El informe no declara que octubre.xlsx coincide con SQL.")
    if comp.get("lineas_excel") != len(rows) or comp.get("lineas_sql") != len(rows):
        raise ImportRejected("SQL_NO_COINCIDE", "Las lineas del informe no son las filas normalizadas del libro.")
    if comp.get("solo_excel") != 0 or comp.get("solo_sql") != 0:
        raise ImportRejected("SQL_NO_COINCIDE", "El informe declara registros presentes en solo uno de los orígenes.")
    if comp.get("ultimo_dia") != CUTOFF.isoformat() or report.get("ultimo_dia_completo") != CUTOFF.isoformat():
        raise ImportRejected("SQL_NO_COINCIDE", "El informe no declara el 20/10 como ultimo dia completo.")
    if max(r["fecha"] for r in rows) > CUTOFF:
        raise ImportRejected("FECHA_FUERA_DE_VENTANA", "Hay ventas posteriores al corte del 20/10.")
    docs = len({r["documento_id"] for r in rows})
    prep = (report.get("datos_preparados") or {}).get("octubre_normalizado")
    if isinstance(prep, dict) and (prep.get("sha256") != sha or prep.get("filas") != len(rows)):
        raise ImportRejected("SQL_NO_COINCIDE", "La normalizacion declarada en el informe no es la de este libro.")
    return {"sql_report_sha256": None, "lines": len(rows), "documents": comp.get("documentos_excel", docs), "sql_match": True}


def load_partial(path: Path, report: dict) -> tuple[list[dict], dict]:
    path = Path(path)
    if not path.is_file():
        raise ImportRejected("ARCHIVO_FALTANTE", "Falta el CSV del parcial del 21/10.")
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or list(reader.fieldnames) != PARTIAL_COLS:
            raise ImportRejected("CSV_ESTRUCTURA_INVALIDA", "Columnas inesperadas en el CSV parcial.")
        raw = list(reader)
    docs, times = [], []
    for i, r in enumerate(raw, 1):
        if (r["fecha"] or "").strip() != PARTIAL_DATE:
            raise ImportRejected("PARCIAL_INVALIDO", f"La linea {i} del parcial no es del {PARTIAL_DATE}.")
        try:
            t = datetime.strptime((r["hora_documento"] or "").strip(), "%H:%M:%S").time()
        except ValueError:
            raise ImportRejected("PARCIAL_INVALIDO", f"La hora de la linea {i} no es valida.") from None
        times.append(t)
        qty, tot = _dec(r["cantidad"], f"cantidad de la linea {i}"), _dec(r["total"], f"total de la linea {i}")
        docs.append({"linea": i, "fecha": PARTIAL_DATE, "hora_documento": t.isoformat(), "tipo_documento": (r["tipo_documento"] or "").strip(),
                     "documento": (r["documento"] or "").strip(), "producto_id": _code(r["producto_id_sql"]),
                     "almacen": (r["almacen"] or "").strip().lstrip("0") or "0", "unidad": (r["unidad"] or "").strip().upper(),
                     "cantidad": _plain(qty), "total": _plain(tot)})
    h = hashlib.sha256()
    for d in docs:
        h.update(json.dumps([d[k] for k in PARTIAL_FIELDS], ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        h.update(b"\n")
    last = max(times).isoformat() if times else None
    dp = (report.get("datos_preparados") or {})
    if "parcial_21_lineas" in dp and dp["parcial_21_lineas"] != len(docs):
        raise ImportRejected("PARCIAL_INVALIDO", "Las lineas del parcial no son las que declara el informe.")
    if "parcial_21_ultima_hora_documento" in dp and dp["parcial_21_ultima_hora_documento"] != last:
        raise ImportRejected("PARCIAL_INVALIDO", "La ultima hora del parcial no es la que declara el informe.")
    return docs, {"date": PARTIAL_DATE, "lines": len(docs), "last_document_time": last, "collection": PARTIAL_COLL,
                  "sha256": h.hexdigest(), "used_for_forecast": False}


def prepare(package: Path, october: Path, sql_report: Path, partial_csv: Path, audit_path: Path | None = None) -> Prepared:
    base = ds.prepare(Path(package), audit_path)             # verifica los 14 libros y el derivado
    october, sql_report = Path(october), Path(sql_report)
    if not october.is_file():
        raise ImportRejected("ARCHIVO_FALTANTE", "Falta octubre.xlsx.")
    report = _json(sql_report, "informe.json")
    digest = sha256_file(october)
    try:
        rows, summary = normalize_book(october, digest, Counter(), OCTOBER_WINDOW)
    except NormalizationError as exc:
        raise ImportRejected("FUENTE_ALTERADA" if exc.code == "LIBRO_ILEGIBLE" else "DERIVADO_NO_COINCIDE", exc.message) from None
    if len({r["registro_id"] for r in rows}) != len(rows):
        raise ds._mismatch("hay registro_id repetidos en octubre")
    if any(r["_kind"] != "ventas" for r in rows):
        raise ds._mismatch("octubre no es un libro de ventas")
    verification = verify_october(october, report, rows)
    verification["sql_report_sha256"] = sha256_file(sql_report)
    partial, partial_head = load_partial(partial_csv, report)

    occ = Counter(r["_signature"] for r in rows)
    docs = {c: list(v) for c, v in base.docs.items()}
    for r in rows:
        doc = {k: r[k] for k in ds.DOC_FIELDS if k not in ("clase", "cantidad", "importe", "fecha")}
        doc.update(fecha=r["fecha"].isoformat(), cantidad=_dec_text(r["cantidad"]), importe=_dec_text(r["importe"]),
                   clase=r["clasificacion"],
                   grupo_repeticion=r["_signature"][1][:24] if occ[r["_signature"]] > 1 else "")
        docs[COLLECTIONS[ds.CLASS_PARTITION[r["clasificacion"]]]].append(doc)

    bh = base.header
    classes = Counter(bh["counts"])
    classes.update(r["clasificacion"] for r in rows)
    partitions, content = {}, hashlib.sha256()
    content.update(f"schema:{SCHEMA_TAG}\nbase:{bh['dataset_id']}:{bh['content_sha256']}\nbook:{OCTOBER_NAME}:{digest}\n".encode())
    for part, coll in COLLECTIONS.items():
        fp, amounts = _partition_fingerprint(docs[coll])
        partitions[part] = {"collection": coll, "count": len(docs[coll]), "sha256": fp, "importes_por_moneda": amounts,
                            "clases": dict(Counter(d["clase"] for d in docs[coll]))}
        content.update(f"part:{part}:{len(docs[coll])}:{fp}\n".encode())
    content.update(f"partial:{partial_head['date']}:{partial_head['lines']}:{partial_head['sha256']}\n".encode())
    content_sha = content.hexdigest()
    sales_dates = [d["fecha"] for d in docs[COLLECTIONS["sales"]]]
    if max(sales_dates) > CUTOFF.isoformat():
        raise ds._mismatch("hay ventas posteriores al corte")
    derived = dict(bh["derived_files"])
    derived["informe.json"] = verification["sql_report_sha256"]
    derived["ventas_parcial_csv"] = sha256_file(partial_csv)
    header = {
        **bh, "dataset_id": f"plds-{content_sha[:12]}", "content_sha256": content_sha, "base_dataset_id": bh["dataset_id"],
        "window_end": CUTOFF.isoformat(), "sales_cutoff": CUTOFF.isoformat(), "source_rows": bh["source_rows"] + len(rows),
        "counts": dict(classes), "partitions": partitions,
        "repeated_extra_rows": sum(1 for c in COLLECTIONS.values() for d in docs[c] if d["ocurrencia"] > 1),
        "repeated_extra_rows_marked": sum(1 for d in docs[COLLECTIONS["purchases"]] if d["ocurrencia"] > 1),
        "sources": [*bh["sources"], {"archivo": OCTOBER_NAME, "tipo": "ventas", "sha256": digest, "filas": summary["filas"]}],
        "derived_files": derived, "currencies": sorted({d["moneda"] for c in docs.values() for d in c}),
        "october_verification": verification, "partial": partial_head, "dataset_kind": SCHEMA_TAG,
    }
    if len(header["sources"]) != 15:
        raise ds._mismatch("el dataset v2 debe listar 15 fuentes")
    return Prepared(header, docs, {PARTIAL_COLL: partial})


def run(package, october, sql_report, partial_csv, db, audit_path=None, dry_run: bool = False) -> dict:
    if db.name in PROTECTED_DBS:
        raise ImportRejected("BASE_PROTEGIDA", "No se escribe en bases de desarrollo, v2 ni publicadas.")
    return write_dataset(db, prepare(package, october, sql_report, partial_csv, audit_path), dry_run)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Verifica, sella e importa el dataset v2 (14 libros + octubre + parcial 21/10)")
    ap.add_argument("--package", required=True)
    ap.add_argument("--october", required=True)
    ap.add_argument("--sql-report", required=True)
    ap.add_argument("--partial-csv", required=True)
    ap.add_argument("--db", required=True)
    ap.add_argument("--audit", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    if not ds._DB_RE.match(args.db):
        print("Nombre de base invalido.", file=sys.stderr)
        return 2
    if args.db in PROTECTED_DBS:
        print("Importacion rechazada [BASE_PROTEGIDA]: no se escribe en bases protegidas.", file=sys.stderr)
        return 1
    try:
        if args.audit and not Path(args.audit).is_file():
            raise ImportRejected("ARCHIVO_FALTANTE", "Falta audit.json indicado.")
        audit = Path(args.audit) if args.audit else ds.default_audit(Path(args.package))
        prep = prepare(Path(args.package), Path(args.october), Path(args.sql_report), Path(args.partial_csv), audit)
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
