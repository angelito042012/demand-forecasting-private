"""Importador idempotente de los Excel de ventas a MongoDB (T03).

Clasificacion por fila (ver classify_row):
  venta            TIPO_DOC != 7, TOTAL_LINEA > 0, cantidad > 0     -> sales
  nota de credito  TIPO_DOC == 7 y TOTAL_LINEA < 0                  -> credit_notes
  otro                                                              -> import_rejects (motivo codificado)

Identidad de linea (linea_id, esquema v2); el export no trae ID de linea:
  sha256("v2|kind|doc_hash|pedido|fecha|sku|almacen|cantidad|cantidad_base|precio|importe|k")
    kind = S (venta) o N (nota de credito); doc_hash = sha256(tipo_doc|serie_numero);
    numeros normalizados (Decimal sin ceros finales); k = ocurrencia (0,1,2..) de esa
    misma tupla dentro del archivo, en orden de fila. No incluye nombre de archivo,
    fila ni sha: la PROCEDENCIA se guarda aparte en `sources` (cada vez que una
    fuente reconocida ve la linea se anade con $addToSet).
      - lineas legitimas identicas dentro de un archivo NO se fusionan (k distinto);
      - recargar, renombrar, reordenar o solapar archivos no duplica ni pierde lineas.
    Limite: si un archivo solapado trae solo parte de un grupo de lineas identicas,
    se asume que son las primeras k.
  Conflicto (nunca se adivina): si un documento (doc_hash) ya existe en la base,
  cargado primero por OTRA fuente, y el archivo trae lineas nuevas de ese mismo
  documento (documento corregido o dividido), esas lineas NO se insertan: se
  registran en `import_conflicts` (estado OPEN) y la importacion queda
  completed_with_conflicts. Requiere resolucion manual.
  Esquema: schema_version=2. Una base con documentos de esquema anterior (claves v1)
  se rechaza (IncompatibleSchemaError); ver docs/ESTRATEGIA_CLAVES.md.
  rechazo: unico por (source_sha256, source_row).

Importes: Decimal128 (exacto y sumable con $sum en MongoDB; evita error binario
de float). Se construye desde repr(float) del Excel (<= 2 decimales observados).

No se guardan CLIENTE, ID_CLIENTE, VENDEDOR, ubicacion ni SERIE_NUMERO en claro
(solo doc_hash). No se exportan filas a archivos.
filas_leidas = filas no vacias de datos (debajo del encabezado).
"""
from __future__ import annotations

import argparse
import contextvars
import hashlib
import json
import os
import re
import sys
import time
import uuid
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import openpyxl
from bson.decimal128 import Decimal128
from pymongo import ASCENDING, MongoClient, UpdateOne
from pymongo.errors import BulkWriteError

SCHEMA_VERSION = 2
PROVENANCE = "OBSERVED_EXCEL"
DEFAULT_URI = "mongodb://127.0.0.1:27017"
ACCEPTED_CURRENCIES = {"SOLES (S/)", "PEN"}  # unico valor real observado: 'SOLES (S/)'
ACCEPTED_STATUS = {"ACTIVO"}                  # unico valor real observado
CREDIT_NOTE_DOC = 7
QTY_TOL = 1e-6
MONTHS = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
          "julio": 7, "agosto": 8, "setiembre": 9, "septiembre": 9, "octubre": 10,
          "noviembre": 11, "diciembre": 12}
DEFAULT_YEAR = 2026
SIX_FILES = ["marzo", "abril", "mayo", "junio", "julio", "agosto"]
REQUIRED_HEADERS = ["ID_PEDIDO", "TIPO_DOC", "SERIE_NUMERO", "FECHA", "MONEDA", "ID_ARTICULO",
                    "ID_ALMACEN", "CANTIDAD", "PRECIO", "TOTAL_LINEA", "ID_UM", "EQUIVALENCIA",
                    "UM_BASE", "CANTIDAD_UM_BASE", "GRUPO", "VEN_ESTADO"]


class ImportInvariantError(RuntimeError):
    pass


class ImportWriteError(RuntimeError):
    """Error de escritura no recuperable (validacion, permisos, write concern...)."""


class IncompatibleSchemaError(RuntimeError):
    """La base contiene documentos de un esquema/clave anterior; no mezclar."""


@dataclass
class ImportReport:
    import_id: str
    archivo: str
    sha256: str
    mes: str | None
    estado: str = "running"
    noop: bool = False
    dry_run: bool = False
    filas_leidas: int = 0
    ventas_aceptadas: int = 0
    notas_credito: int = 0
    rechazadas: int = 0
    insertadas: int = 0
    ya_existentes: int = 0
    en_conflicto: int = 0
    rechazos_por_motivo: dict = field(default_factory=dict)
    segundos: float = 0.0
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    def check_invariant(self) -> None:
        if self.filas_leidas != self.ventas_aceptadas + self.notas_credito + self.rechazadas:
            raise ImportInvariantError(
                f"filas_leidas={self.filas_leidas} != ventas({self.ventas_aceptadas}) + "
                f"notas_credito({self.notas_credito}) + rechazadas({self.rechazadas})")
        if sum(self.rechazos_por_motivo.values()) != self.rechazadas:
            raise ImportInvariantError("suma de rechazos por motivo != rechazadas")

    def check_persistence(self) -> None:
        if self.insertadas + self.ya_existentes + self.en_conflicto != self.ventas_aceptadas + self.notas_credito:
            raise ImportInvariantError("insertadas + ya_existentes + en_conflicto != aceptadas")


# ---------------------------------------------------------------- utilidades
def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _h(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _num(v) -> bool:
    return isinstance(v, (int, float, Decimal)) and not isinstance(v, bool)


def _d128(v) -> Decimal128:
    return Decimal128(Decimal(repr(v)) if isinstance(v, float) else Decimal(v))


def _text(v) -> str:
    return "" if v is None else str(v).strip()


def infer_month(path):
    stem = Path(path).stem.lower()
    return (DEFAULT_YEAR, MONTHS[stem]) if stem in MONTHS else None


def _norm_month(expected_month):
    if expected_month is None:
        return None
    if isinstance(expected_month, str):
        m = re.fullmatch(r"(\d{4})-(\d{2})", expected_month)
        if not m:
            raise ValueError("expected_month debe ser 'YYYY-MM' o (anio, mes)")
        return (int(m[1]), int(m[2]))
    return (int(expected_month[0]), int(expected_month[1]))


# ---------------------------------------------------------------- lectura
def read_rows(path):
    """Devuelve [(fila_excel, dict)] omitiendo filas totalmente vacias (solo lectura)."""
    book = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        sheet = book["Hoja1"] if "Hoja1" in book.sheetnames else book.worksheets[0]
        headers, out = None, []
        for n, row in enumerate(sheet.iter_rows(values_only=True), 1):
            if headers is None:
                if n > 20:
                    break
                if "ID_PEDIDO" in row and "FECHA" in row:
                    headers = [str(v).strip() if v is not None else "" for v in row]
                continue
            if not any(v is not None and str(v).strip() != "" for v in row):
                continue
            out.append((n, dict(zip(headers, row))))
        if headers is None:
            raise ValueError(f"Encabezados no encontrados en {Path(path).name}")
        missing = [c for c in REQUIRED_HEADERS if c not in headers]
        if missing:
            raise ValueError(f"Columnas faltantes en {Path(path).name}: {missing}")
        return out
    finally:
        book.close()


# ---------------------------------------------------------------- clasificacion
def classify_row(rec: dict, month: tuple):
    """Retorna ('sale'|'credit', campos) o ('reject', (motivo, valores_minimos))."""
    def rej(code):
        f = rec.get("FECHA")
        td = rec.get("TIPO_DOC")
        return "reject", (code, {
            "tipo_doc": td if _num(td) else (_text(td) or None),
            "fecha_raw": f.isoformat() if isinstance(f, (datetime, date)) else (_text(f)[:40] or None),
            "sku": _text(rec.get("ID_ARTICULO")) or None,
            "cantidad_raw": _text(rec.get("CANTIDAD"))[:40] or None,
            "importe_raw": _text(rec.get("TOTAL_LINEA"))[:40] or None,
        })

    fecha = rec.get("FECHA")
    if not isinstance(fecha, (datetime, date)):
        return rej("FECHA_INVALIDA")
    fd = fecha.date() if isinstance(fecha, datetime) else fecha
    if (fd.year, fd.month) != month:
        return rej("FECHA_FUERA_DE_MES")
    sku = _text(rec.get("ID_ARTICULO"))
    if not sku:
        return rej("SKU_FALTANTE")
    if _text(rec.get("ID_ALMACEN")) == "":
        return rej("ALMACEN_FALTANTE")
    qty = rec.get("CANTIDAD")
    if _text(qty) == "":
        return rej("CANTIDAD_FALTANTE")
    if not _num(qty):
        return rej("CANTIDAD_NO_NUMERICA")
    amount = rec.get("TOTAL_LINEA")
    if not _num(amount):
        return rej("IMPORTE_NO_NUMERICO")
    tipo = rec.get("TIPO_DOC")
    if not _num(tipo) or int(tipo) != tipo:
        return rej("TIPO_DOC_INVALIDO")
    tipo = int(tipo)
    if _text(rec.get("MONEDA")).upper() not in ACCEPTED_CURRENCIES:
        return rej("MONEDA_NO_PEN")
    if _text(rec.get("VEN_ESTADO")).upper() not in ACCEPTED_STATUS:
        return rej("ESTADO_NO_ACTIVO")
    eq, base = rec.get("EQUIVALENCIA"), rec.get("CANTIDAD_UM_BASE")
    if not _num(eq) or eq <= 0:
        return rej("EQUIVALENCIA_INVALIDA")
    if not _num(base):
        return rej("CANTIDAD_BASE_FALTANTE")
    if abs(qty * eq - base) > QTY_TOL:
        return rej("EQUIVALENCIA_INCONSISTENTE")
    if tipo == CREDIT_NOTE_DOC:
        if amount >= 0:
            return rej("TIPO7_IMPORTE_NO_NEGATIVO")
        kind = "credit"
    else:
        if amount < 0:
            return rej("IMPORTE_NEGATIVO_NO_TIPO7")
        if amount == 0:
            return rej("IMPORTE_CERO")
        if qty <= 0 or base <= 0:
            return rej("CANTIDAD_NO_POSITIVA_EN_VENTA")
        kind = "sale"
    pedido = rec.get("ID_PEDIDO")
    return kind, {
        "fd": fd, "pedido_id": int(pedido) if _num(pedido) else None, "sku": sku,
        "categoria_original": _text(rec.get("GRUPO")), "cantidad_original": qty,
        "unidad_original": _text(rec.get("ID_UM")), "um_base_original": _text(rec.get("UM_BASE")),
        "equivalencia": eq, "cantidad_base": base, "precio": rec.get("PRECIO"), "importe": amount,
        "almacen": _text(rec.get("ID_ALMACEN")), "tipo_doc": tipo,
        "doc_hash": _h(f"{tipo}|{_text(rec.get('SERIE_NUMERO'))}"),
    }


def _canon(v) -> str:
    """Numero normalizado e independiente del tipo Excel (5, 5.0 y 5.00 son iguales)."""
    if not _num(v):
        return ""
    d = Decimal(repr(v)) if isinstance(v, float) else Decimal(v)
    return format(d.normalize(), "f") if d != 0 else "0"


def _line_key(kind: str, f: dict, k: int) -> str:
    return _h("|".join(["v2", kind, f["doc_hash"], str(f["pedido_id"]), f["fd"].isoformat(), f["sku"],
                        f["almacen"], _canon(f["cantidad_original"]), _canon(f["cantidad_base"]),
                        _canon(f["precio"]), _canon(f["importe"]), str(k)]))


def _document(f: dict, linea_id: str, meta: dict, row: int) -> dict:
    fd: date = f["fd"]
    precio = f["precio"]
    return {
        "linea_id": linea_id,
        "fecha": fd.isoformat(),
        "fecha_dt": datetime(fd.year, fd.month, fd.day),
        "mes": f"{fd.year:04d}-{fd.month:02d}",
        "pedido_id": f["pedido_id"], "sku": f["sku"], "categoria_original": f["categoria_original"],
        "cantidad_original": f["cantidad_original"], "unidad_original": f["unidad_original"],
        "um_base_original": f["um_base_original"], "unidad_base": f["um_base_original"].upper(),
        "equivalencia": f["equivalencia"], "cantidad_base": f["cantidad_base"],
        "precio_unitario_original": _d128(precio) if _num(precio) else None,
        "importe": _d128(f["importe"]), "moneda": "PEN", "almacen": f["almacen"],
        "tipo_doc": f["tipo_doc"], "doc_hash": f["doc_hash"],
        "source_file": meta["archivo"], "source_sha256": meta["sha256"], "source_row": row,
        "sources": [{"source_file": meta["archivo"], "source_sha256": meta["sha256"], "source_row": row}],
        "import_id": meta["import_id"], "schema_version": SCHEMA_VERSION, "provenance": PROVENANCE,
    }


# ---------------------------------------------------------------- persistencia
def ensure_indexes(db) -> None:
    for coll in (db.sales, db.credit_notes):
        coll.create_index([("linea_id", ASCENDING)], unique=True, name="uq_linea_id")
        coll.create_index([("doc_hash", ASCENDING)], name="ix_doc_hash")
        coll.create_index([("sources.source_sha256", ASCENDING)], name="ix_source_sha")
    db.sales.create_index([("fecha", ASCENDING), ("sku", ASCENDING)], name="ix_fecha_sku")
    db.sales.create_index([("sku", ASCENDING), ("fecha", ASCENDING)], name="ix_sku_fecha")
    db.credit_notes.create_index([("fecha", ASCENDING)], name="ix_fecha")
    db.import_rejects.create_index([("source_sha256", ASCENDING), ("source_row", ASCENDING)],
                                   unique=True, name="uq_sha_row")
    db.import_conflicts.create_index([("conflict_id", ASCENDING)], unique=True, name="uq_conflict_id")
    db.imports.create_index([("import_id", ASCENDING)], unique=True, name="uq_import_id")
    db.imports.create_index([("sha256", ASCENDING), ("estado", ASCENDING)], name="ix_sha_estado")


def check_schema(db) -> None:
    for name in ("sales", "credit_notes"):
        if db[name].find_one({"schema_version": {"$ne": SCHEMA_VERSION}}, {"_id": 1}) is not None:
            raise IncompatibleSchemaError(
                f"{db.name}.{name} contiene documentos con schema_version != {SCHEMA_VERSION}; "
                "no importar encima. Ver docs/ESTRATEGIA_CLAVES.md (reconstruir en una base nueva).")


def _run_bulk(coll, ops) -> int:
    """bulk_write sin ocultar errores. Solo la clave duplicada (11000) de una carrera de
    upsert es recuperable: esa operacion se reintenta (ahora el documento existe).
    Validacion (121), permisos, write concern u otros se propagan. Retorna insertados."""
    try:
        return coll.bulk_write(ops, ordered=False).upserted_count
    except BulkWriteError as exc:
        det = exc.details or {}
        if det.get("writeConcernErrors"):
            raise ImportWriteError(f"write concern: {det['writeConcernErrors'][:1]}") from exc
        errors = det.get("writeErrors") or []
        codes = sorted({e.get("code") for e in errors})
        if not errors or codes != [11000]:
            raise ImportWriteError(f"error de escritura no recuperable, codigos {codes or 'desconocidos'}: "
                                   f"{str(errors[:1])[:300]}") from exc
        inserted = det.get("nUpserted", 0)
        try:
            inserted += coll.bulk_write([ops[e["index"]] for e in errors], ordered=False).upserted_count
        except BulkWriteError as exc2:
            raise ImportWriteError("clave duplicada persistente tras reintento") from exc2
        return inserted


_FENCE: contextvars.ContextVar = contextvars.ContextVar("import_fence", default=None)


def _fence_check(write: bool = True) -> None:
    """T10R R09: si la importacion corre bajo una valla (reserva del mes), se renueva/verifica antes de escribir.
    Un dueno desplazado recibe LostReservation y no escribe mas."""
    fence = _FENCE.get()
    if fence is not None:
        fence.check(write=write)


def _upsert_all(coll, docs, batch_size, *, filt, verify):
    """Upsert $setOnInsert (+ $addToSet de procedencia). Verifica que cada lote quedo
    persistido. Retorna (insertadas, ya_existentes)."""
    ins = 0
    for i in range(0, len(docs), batch_size):
        _fence_check()
        chunk = docs[i:i + batch_size]
        ops = []
        for d in chunk:
            update = {"$setOnInsert": {k: v for k, v in d.items() if k != "sources"}}
            if "sources" in d:
                update["$addToSet"] = {"sources": {"$each": d["sources"]}}
            ops.append(UpdateOne(filt(d), update, upsert=True))
        ins += _run_bulk(coll, ops)
        found = coll.count_documents(verify(chunk))
        if found != len(chunk):
            raise ImportWriteError(f"{coll.name}: lote de {len(chunk)} verificado con {found} persistidos")
    return ins, len(docs) - ins


def _bulk(coll, docs, batch_size):
    return _upsert_all(coll, docs, batch_size, filt=lambda d: {"linea_id": d["linea_id"]},
                       verify=lambda ch: {"linea_id": {"$in": [d["linea_id"] for d in ch]}})


def _bulk_rejects(coll, docs, batch_size):
    return _upsert_all(coll, docs, batch_size,
                       filt=lambda d: {"source_sha256": d["source_sha256"], "source_row": d["source_row"]},
                       verify=lambda ch: {"source_sha256": ch[0]["source_sha256"],
                                          "source_row": {"$in": [d["source_row"] for d in ch]}})


def _screen_conflicts(db, coll_name, docs, meta):
    """Separa lineas de documentos ya cargados por otra fuente con contenido distinto."""
    by_doc = defaultdict(list)
    for d in docs:
        by_doc[d["doc_hash"]].append(d)
    foreign = defaultdict(set)
    hashes = list(by_doc)
    for i in range(0, len(hashes), 1000):
        for e in db[coll_name].find({"doc_hash": {"$in": hashes[i:i + 1000]},
                                     "source_sha256": {"$ne": meta["sha256"]}},
                                    {"doc_hash": 1, "linea_id": 1}):
            foreign[e["doc_hash"]].add(e["linea_id"])
    ok, conflicts = [], []
    for h, lines in by_doc.items():
        known = foreign.get(h)
        new = [d for d in lines if d["linea_id"] not in known] if known else []
        if not new:
            ok.extend(lines)
            continue
        ok.extend(d for d in lines if d["linea_id"] in known)
        conflicts.append({
            "conflict_id": _h(f"{coll_name}|{h}|{meta['sha256']}"), "coleccion": coll_name,
            "doc_hash": h, "tipo_doc": new[0]["tipo_doc"],
            "motivo": "DOCUMENTO_EXISTENTE_CON_CONTENIDO_DISTINTO", "estado": "OPEN",
            "source_file": meta["archivo"], "source_sha256": meta["sha256"],
            "lineas_nuevas": [{"linea_id": d["linea_id"], "source_row": d["source_row"], "fecha": d["fecha"],
                               "sku": d["sku"], "cantidad_base": d["cantidad_base"],
                               "importe": d["importe"]} for d in new],
            "lineas_existentes": sorted(known), "schema_version": SCHEMA_VERSION,
        })
    return ok, conflicts


def _write_conflicts(db, conflicts):
    for c in conflicts:
        _fence_check()
        db.import_conflicts.update_one({"conflict_id": c["conflict_id"]}, {"$setOnInsert": c}, upsert=True)
        if db.import_conflicts.count_documents({"conflict_id": c["conflict_id"]}) != 1:
            raise ImportWriteError("conflicto no persistido")


def _write_batches(db, sales, notes, rejects, batch_size):
    """Punto unico de escritura (los tests lo sustituyen para simular fallos)."""
    s_ins, s_dup = _bulk(db.sales, sales, batch_size)
    n_ins, n_dup = _bulk(db.credit_notes, notes, batch_size)
    _bulk_rejects(db.import_rejects, rejects, batch_size)
    return s_ins + n_ins, s_dup + n_dup


def _now():
    return datetime.now(UTC)


def import_workbook(path, db, *, expected_month=None, dry_run: bool = False,
                    batch_size: int = 2000, fence=None) -> ImportReport:
    """`fence` (T10R R09, opcional): valla de la reserva del mes (`month_lock.Fence`). Se consulta antes de cada lote
    de escritura y antes de finalizar; si otro intento retomo el mes, lanza LostReservation y no escribe ni aprueba."""
    token = _FENCE.set(None if dry_run else fence)
    try:
        return _import_workbook(path, db, expected_month=expected_month, dry_run=dry_run, batch_size=batch_size,
                                fence=None if dry_run else fence)
    finally:
        _FENCE.reset(token)


def _import_workbook(path, db, *, expected_month, dry_run, batch_size, fence) -> ImportReport:
    path = Path(path)
    t0 = time.perf_counter()
    month = _norm_month(expected_month) or infer_month(path)
    if month is None:
        raise ValueError(f"No se pudo inferir el mes de {path.name}; indique expected_month")
    digest = sha256_file(path)
    rep = ImportReport(import_id=uuid.uuid4().hex, archivo=path.name, sha256=digest,
                       mes=f"{month[0]:04d}-{month[1]:02d}", dry_run=dry_run)

    if not dry_run:
        check_schema(db)
        ensure_indexes(db)
        prev = db.imports.find_one({"sha256": digest, "estado": "completed", "noop": {"$ne": True}})
        if prev is not None:  # mismo contenido ya cargado: no-op registrado
            for k in ("filas_leidas", "ventas_aceptadas", "notas_credito", "rechazadas",
                      "rechazos_por_motivo"):
                setattr(rep, k, prev[k])
            rep.en_conflicto = prev.get("en_conflicto", 0)
            rep.noop = True
            rep.ya_existentes = rep.ventas_aceptadas + rep.notas_credito
            rep.estado = "completed"
            rep.segundos = round(time.perf_counter() - t0, 3)
            rep.check_invariant()
            db.imports.insert_one({**rep.to_dict(), "iniciado_utc": _now(),
                                   "schema_version": SCHEMA_VERSION})
            return rep
        db.imports.insert_one({**rep.to_dict(), "iniciado_utc": _now(),
                               "schema_version": SCHEMA_VERSION})

    try:
        rows = read_rows(path)
        meta = {"archivo": path.name, "sha256": digest, "import_id": rep.import_id}
        sales, notes, rejects = [], [], []
        occ: Counter = Counter()
        reasons: Counter = Counter()
        for n, rec in rows:
            kind, payload = classify_row(rec, month)
            if kind == "reject":
                code, minimal = payload
                reasons[code] += 1
                rejects.append({"source_file": path.name, "source_sha256": digest, "source_row": n,
                                "mes_archivo": rep.mes, "motivo": code, "valores": minimal,
                                "import_id": rep.import_id, "schema_version": SCHEMA_VERSION})
            elif kind == "sale":
                base = _line_key("S", payload, 0)
                k = occ[base]
                occ[base] += 1
                sales.append(_document(payload, base if k == 0 else _line_key("S", payload, k), meta, n))
            else:
                base = _line_key("N", payload, 0)
                k = occ[base]
                occ[base] += 1
                notes.append(_document(payload, base if k == 0 else _line_key("N", payload, k), meta, n))
        rep.filas_leidas = len(rows)
        rep.ventas_aceptadas, rep.notas_credito = len(sales), len(notes)
        rep.rechazadas = len(rejects)
        rep.rechazos_por_motivo = dict(reasons)
        rep.check_invariant()
        if not dry_run:
            sales, c_sales = _screen_conflicts(db, "sales", sales, meta)
            notes, c_notes = _screen_conflicts(db, "credit_notes", notes, meta)
            conflicts = c_sales + c_notes
            rep.en_conflicto = sum(len(c["lineas_nuevas"]) for c in conflicts)
            _write_conflicts(db, conflicts)
            rep.insertadas, rep.ya_existentes = _write_batches(db, sales, notes, rejects, batch_size)
            rep.check_persistence()
            _fence_check(write=False)                    # sigue siendo el dueno del mes antes de dar por completada
        rep.estado = "completed_with_conflicts" if rep.en_conflicto else "completed"
    except BaseException as exc:
        rep.estado = "failed"
        rep.error = f"{type(exc).__name__}: {exc}"[:500]
        rep.segundos = round(time.perf_counter() - t0, 3)
        if not dry_run:
            db.imports.update_one({"import_id": rep.import_id},
                                  {"$set": {**rep.to_dict(), "finalizado_utc": _now()}})
        raise
    rep.segundos = round(time.perf_counter() - t0, 3)
    if not dry_run:
        if fence is not None:
            fence.check()                                # ultima comprobacion: un dueno obsoleto no finaliza/aprueba
        db.imports.update_one({"import_id": rep.import_id},
                              {"$set": {**rep.to_dict(), "finalizado_utc": _now()}})
    return rep


def import_folder(folder, db, *, dry_run=False) -> list:
    reports = []
    for name in SIX_FILES:
        p = Path(folder) / f"{name}.xlsx"
        if p.exists():
            reports.append(import_workbook(p, db, dry_run=dry_run))
    return reports


def get_client(uri: str | None = None) -> MongoClient:
    return MongoClient(uri or os.environ.get("MONGODB_URI") or DEFAULT_URI,
                       serverSelectionTimeoutMS=3000)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Importa los Excel de ventas a MongoDB (idempotente)")
    ap.add_argument("--source", required=True, type=Path)
    ap.add_argument("--db", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    reports = import_folder(args.source, get_client()[args.db], dry_run=args.dry_run)
    for r in reports:
        print(json.dumps(r.to_dict(), ensure_ascii=False))
    if reports and all(r.estado == "completed" for r in reports):
        return 0
    return 2 if any(r.estado == "completed_with_conflicts" for r in reports) else 1


if __name__ == "__main__":
    sys.exit(main())
