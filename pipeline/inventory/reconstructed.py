"""Importador de la existencia reconstruida al cierre del 20/10 (T20 §2). Depende de stdlib y pymongo.

    python -m pipeline.inventory.reconstructed --package <carpeta existencias_reconstruidas_20261020> --db <base>
        [--sql-report <informe.json>] [--dry-run]

El paquete (existencias.csv + manifest.json) lo genera scripts/sql21_prepare.py desde el conteo del 18/10 17:00 y el kardex.
Se verifica TODA la aritmetica y la identidad con el conteo base antes de escribir; el resultado es una existencia
RECONSTRUIDA (no un conteo fisico). Escribe en `inventory_reconstructed_snapshots` / `inventory_reconstructed_items`
(staging -> current); no toca `inventory_reported_*` ni ninguna otra coleccion.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

SCHEMA_VERSION = 1
SNAP_COLL = "inventory_reconstructed_snapshots"
ITEM_COLL = "inventory_reconstructed_items"
BASE_SNAP_COLL = "inventory_reported_snapshots"
BASE_ITEM_COLL = "inventory_reported_items"
PROTECTED_DBS = frozenset({"demand_forecasting_dev", "demand_forecasting_v2", "demand_forecasting_pub"})
KIND = "EXISTENCIA_RECONSTRUIDA"
AS_OF_LOCAL = "2026-10-20T23:59:59-05:00"
BASE_AS_OF_LOCAL = "2026-10-18T17:00:00-05:00"
LIMA = timedelta(hours=-5)
_DB_RE = re.compile(r"^[A-Za-z0-9_]{1,63}$")
_CODE = re.compile(r"^\d{1,20}$")
_INT = re.compile(r"^-?\d{1,12}$")
COLUMNS = ["producto_id", "producto", "unidad_reporte", "unidad_descripcion", "conteo_libre", "entradas_hasta_cierre",
           "salidas_hasta_cierre", "existencia_cierre_20_10", "entradas_hasta_ultimo_mov", "salidas_hasta_ultimo_mov",
           "existencia_ultimo_mov", "stock_sistema_ultimo_mov", "reservado_sistema", "diferencia", "estado"]
NON_NEG = ["conteo_libre", "entradas_hasta_cierre", "salidas_hasta_cierre", "existencia_cierre_20_10", "entradas_hasta_ultimo_mov",
           "salidas_hasta_ultimo_mov", "existencia_ultimo_mov", "stock_sistema_ultimo_mov", "reservado_sistema"]


class ImportRejected(Exception):
    """Rechazo de la fuente o de la operacion; `code` es estable y no incluye rutas ni secretos."""

    def __init__(self, code: str, message: str):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


@dataclass
class Prepared:
    header: dict          # sin version/status/supersedes/imported_at
    items: list[dict]
    csv_sha256: str


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _when(raw, what: str) -> datetime:
    try:
        t = datetime.fromisoformat(str(raw))
    except ValueError:
        raise ImportRejected("FECHA_ZONA_INVALIDA", f"{what} no es una fecha valida.") from None
    if t.tzinfo is None or t.utcoffset() != LIMA:
        raise ImportRejected("FECHA_ZONA_INVALIDA", f"{what} debe indicar UTC-05:00 (America/Lima).")
    return t


def _int(raw, what: str, code: str, *, signed: bool = False) -> int:
    v = (raw or "").strip()
    if not _INT.match(v):
        raise ImportRejected("CANTIDAD_INVALIDA", f"{what} del producto {code} no es un entero.")
    n = int(v)
    if n < 0 and not signed:
        raise ImportRejected("CANTIDAD_NEGATIVA", f"{what} del producto {code} es negativa.")
    return n


def load_base(db, base_ref: dict, *, base_as_of_local: str = BASE_AS_OF_LOCAL):
    """Snapshot T18 base de la base de datos (o None si no existe): (cabecera, {producto_id: item}). Rechaza una referencia que no cuadra."""
    sid, csv_sha = base_ref.get("snapshot_id"), base_ref.get("csv_sha256")
    snaps = db[BASE_SNAP_COLL]
    found = None
    if sid:
        found = snaps.find_one({"snapshot_id": sid}, {"_id": 0})
    if found is None and _sha_ok(csv_sha):
        found = snaps.find_one({"source.csv_sha256": csv_sha}, {"_id": 0}, sort=[("version", -1)])
    if found is None:
        other = snaps.find_one({"status": "current", "as_of_local": base_as_of_local}, {"_id": 0})
        if other is not None:
            raise ImportRejected("CONTEO_BASE_DISTINTO", "El conteo base del paquete no es el conteo vigente de la base.")
        return None
    if found.get("as_of_local") != base_as_of_local or found.get("source", {}).get("csv_sha256") != csv_sha:
        raise ImportRejected("CONTEO_BASE_DISTINTO", "El conteo base del paquete no coincide con el snapshot base de la base.")
    if sid and found["snapshot_id"] != sid:
        raise ImportRejected("CONTEO_BASE_DISTINTO", "El snapshot base citado no coincide.")
    items = {i["producto_id"]: i for i in db[BASE_ITEM_COLL].find({"snapshot_id": found["snapshot_id"]}, {"_id": 0})}
    return found, items


def _sha_ok(v) -> bool:
    return isinstance(v, str) and len(v) == 64 and all(c in "0123456789abcdef" for c in v)


def prepare(package: Path, db=None, sql_report: Path | None = None, *,
            as_of_local: str = AS_OF_LOCAL, base_as_of_local: str = BASE_AS_OF_LOCAL) -> Prepared:
    package = Path(package)
    mpath, cpath = package / "manifest.json", package / "existencias.csv"
    if not mpath.is_file() or not cpath.is_file():
        raise ImportRejected("ARCHIVO_FALTANTE", "Falta existencias.csv o manifest.json.")
    try:
        man = json.loads(mpath.read_text(encoding="utf-8-sig"))
    except ValueError:
        raise ImportRejected("MANIFIESTO_INVALIDO", "manifest.json no es JSON valido.") from None
    if not isinstance(man, dict) or man.get("kind") != KIND:
        raise ImportRejected("MANIFIESTO_INVALIDO", f"El manifiesto no es de tipo {KIND}.")
    csv_sha = _sha256_file(cpath)
    if man.get("csv_sha256") != csv_sha:
        raise ImportRejected("FUENTE_ALTERADA", "El SHA-256 de existencias.csv no coincide con el manifiesto.")
    rep_sha = man.get("sql_report_sha256")
    if not _sha_ok(rep_sha):
        raise ImportRejected("MANIFIESTO_INVALIDO", "El manifiesto no trae el SHA-256 del informe SQL.")
    if sql_report is not None and (not Path(sql_report).is_file() or _sha256_file(Path(sql_report)) != rep_sha):
        raise ImportRejected("FUENTE_ALTERADA", "El SHA-256 del informe SQL no coincide con el manifiesto.")
    wh = man.get("warehouse")
    if not isinstance(wh, dict) or str(wh.get("id")) != "1" or not str(wh.get("name") or "").strip():
        raise ImportRejected("ALMACEN_NO_CONFIRMADO", "El manifiesto debe indicar el almacen 1.")
    asof = _when(man.get("as_of_local"), "as_of_local")
    if asof.isoformat() != as_of_local:
        raise ImportRejected("FECHA_ZONA_INVALIDA", f"La existencia debe estar fechada al {as_of_local}.")
    base_ref = man.get("base_count")
    mv = man.get("movements")
    if not isinstance(base_ref, dict) or not isinstance(mv, dict):
        raise ImportRejected("MANIFIESTO_INVALIDO", "El manifiesto no describe el conteo base y los movimientos.")
    if _when(base_ref.get("as_of_local"), "base_count.as_of_local").isoformat() != base_as_of_local or not _sha_ok(base_ref.get("csv_sha256")):
        raise ImportRejected("CONTEO_BASE_DISTINTO", f"El conteo base debe estar fechado al {base_as_of_local} con su SHA-256.")
    base_from, closing = _when(mv.get("from_local"), "movements.from_local"), _when(mv.get("closing_local"), "movements.closing_local")
    last = _when(mv.get("last_movement_local"), "movements.last_movement_local")
    if base_from.isoformat() != base_as_of_local or closing != asof or last < closing:
        raise ImportRejected("FECHA_ZONA_INVALIDA", "Los movimientos deben ir del conteo base al cierre y hasta un ultimo movimiento posterior.")
    if not str(man.get("rule") or "").strip():
        raise ImportRejected("MANIFIESTO_INVALIDO", "El manifiesto no declara la regla de reconstruccion.")

    with cpath.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or list(reader.fieldnames) != COLUMNS:
            raise ImportRejected("CSV_ESTRUCTURA_INVALIDA", "Columnas inesperadas en existencias.csv.")
        rows = list(reader)
    if not rows:
        raise ImportRejected("CSV_ESTRUCTURA_INVALIDA", "existencias.csv no tiene filas.")

    base = load_base(db, base_ref, base_as_of_local=base_as_of_local) if db is not None else None
    items, seen = [], set()
    for r in rows:
        code = (r["producto_id"] or "").strip()
        if not _CODE.match(code):
            raise ImportRejected("CODIGO_INVALIDO", "Hay un producto_id que no es texto de digitos.")
        if code in seen:
            raise ImportRejected("CODIGO_REPETIDO", f"Codigo repetido: {code}.")
        seen.add(code)
        if not (r["producto"] or "").strip() or not (r["unidad_reporte"] or "").strip():
            raise ImportRejected("CSV_ESTRUCTURA_INVALIDA", f"Faltan producto o unidad en el producto {code}.")
        n = {c: _int(r[c], c, code) for c in NON_NEG}
        diff = _int(r["diferencia"], "diferencia", code, signed=True)
        if n["existencia_cierre_20_10"] != n["conteo_libre"] + n["entradas_hasta_cierre"] - n["salidas_hasta_cierre"]:
            raise ImportRejected("ARITMETICA_INVALIDA", f"La existencia al cierre del producto {code} no es conteo + entradas - salidas.")
        if n["existencia_ultimo_mov"] != n["conteo_libre"] + n["entradas_hasta_ultimo_mov"] - n["salidas_hasta_ultimo_mov"]:
            raise ImportRejected("ARITMETICA_INVALIDA", f"La existencia al ultimo movimiento del producto {code} no es conteo + entradas - salidas.")
        if diff != n["stock_sistema_ultimo_mov"] - n["existencia_ultimo_mov"]:
            raise ImportRejected("ARITMETICA_INVALIDA", f"La diferencia del producto {code} no es stock del sistema - existencia reconstruida.")
        if r["estado"] != ("COINCIDE" if diff == 0 else "DISCREPANTE"):
            raise ImportRejected("ARITMETICA_INVALIDA", f"El estado del producto {code} no corresponde a su diferencia.")
        if n["entradas_hasta_cierre"] > n["entradas_hasta_ultimo_mov"] or n["salidas_hasta_cierre"] > n["salidas_hasta_ultimo_mov"]:
            raise ImportRejected("ARITMETICA_INVALIDA", f"Los movimientos al cierre del producto {code} exceden los del ultimo movimiento.")
        cat = ""
        if base is not None:
            bi = base[1].get(code)
            if bi is None:
                raise ImportRejected("CODIGOS_SOBRANTES", f"El producto {code} no esta en el conteo base.")
            if bi.get("libre") != n["conteo_libre"]:
                raise ImportRejected("CONTEO_BASE_DISTINTO", f"El conteo libre del producto {code} no es el del conteo base.")
            cat = bi.get("categoria") or ""
        items.append({"producto_id": code, "producto": r["producto"].strip(), "categoria": cat,
                      "unidad_reporte": r["unidad_reporte"].strip(), "unidad_descripcion": (r["unidad_descripcion"] or "").strip(),
                      "libre": n["existencia_cierre_20_10"], "base_count": n["conteo_libre"],
                      "movements": {"entradas_cierre": n["entradas_hasta_cierre"], "salidas_cierre": n["salidas_hasta_cierre"],
                                    "entradas_ultimo_mov": n["entradas_hasta_ultimo_mov"], "salidas_ultimo_mov": n["salidas_hasta_ultimo_mov"]},
                      "reconstructed_at_last_movement": n["existencia_ultimo_mov"],
                      "system_stock_at_last_movement": n["stock_sistema_ultimo_mov"], "system_reserved": n["reservado_sistema"],
                      "discrepancy": None if diff == 0 else {"difference": diff, "compared_at_local": last.isoformat()}})
    if base is not None:
        absent = sorted(set(base[1]) - seen)
        if absent:
            raise ImportRejected("CODIGOS_FALTANTES", f"Faltan {len(absent)} productos del conteo base: {', '.join(absent[:5])}.")
    items.sort(key=lambda i: i["producto_id"])
    disc = sum(1 for i in items if i["discrepancy"])
    if man.get("products", len(items)) != len(items) or man.get("discrepancies", disc) != disc:
        raise ImportRejected("MANIFIESTO_INVALIDO", "Los conteos del manifiesto no corresponden al CSV.")

    ident = hashlib.sha256("\n".join([f"csv:{csv_sha}", f"report:{rep_sha}", f"base:{base_ref['csv_sha256']}",
                                      f"asof:{asof.isoformat()}", f"last:{last.isoformat()}"]).encode()).hexdigest()
    base_block = {"snapshot_id": base[0]["snapshot_id"] if base else base_ref.get("snapshot_id"),
                  "as_of_local": base_as_of_local, "csv_sha256": base_ref["csv_sha256"]}
    header = {
        "snapshot_id": f"invrec-{asof:%Y%m%d}-{ident[:12]}", "kind": KIND, "as_of_local": asof.isoformat(),
        "as_of_utc": asof.astimezone(UTC).replace(tzinfo=None), "timezone": "America/Lima",
        "warehouse": {"id": "1", "name": str(wh["name"]).strip()},
        "source": {"sha256": ident, "csv_sha256": csv_sha, "sql_report_sha256": rep_sha, "verified_against_base_count": base is not None},
        "base_count": base_block, "movements": {"from_local": base_from.isoformat(), "closing_local": closing.isoformat(),
                                                "last_movement_local": last.isoformat()},
        "counts": {"products": len(items), "discrepancies": disc}, "rule": str(man["rule"]).strip(),
        "generated_at": man.get("generated_at"), "schema_version": SCHEMA_VERSION,
    }
    return Prepared(header, items, csv_sha)


def ensure_indexes(db) -> None:
    db[SNAP_COLL].create_index([("snapshot_id", 1)], name="snapshot_id_unique", unique=True)
    db[SNAP_COLL].create_index([("warehouse.id", 1), ("as_of_utc", 1), ("version", 1)], name="wh_asof_version_unique", unique=True)
    db[ITEM_COLL].create_index([("snapshot_id", 1), ("producto_id", 1)], name="snapshot_product_unique", unique=True)


def _result(action: str, header: dict, version: int) -> dict:
    return {"action": action, "snapshot_id": header["snapshot_id"], "version": version,
            "items": header["counts"]["products"], "discrepancias": header["counts"]["discrepancies"]}


def write_snapshot(db, prep: Prepared, dry_run: bool = False) -> dict:
    if db.name in PROTECTED_DBS:
        raise ImportRejected("BASE_PROTEGIDA", "No se escribe en bases de desarrollo, v2 ni publicadas.")
    h, snaps = prep.header, db[SNAP_COLL]
    sid, wh, asof = h["snapshot_id"], h["warehouse"]["id"], h["as_of_utc"]
    same = snaps.find_one({"snapshot_id": sid}, {"_id": 0})
    if same and same["status"] == "current":
        return _result("unchanged", h, same["version"])
    if same and same["status"] == "superseded":
        raise ImportRejected("VERSION_SUSTITUIDA", "Esa existencia ya fue sustituida por una version posterior.")
    cur = snaps.find_one({"warehouse.id": wh, "as_of_utc": asof, "status": "current"}, {"_id": 0})
    last = snaps.find_one({"warehouse.id": wh, "as_of_utc": asof, "snapshot_id": {"$ne": sid}}, {"version": 1}, sort=[("version", -1)])
    version = (last["version"] if last else 0) + 1
    action = "created" if last is None else "new_version"
    if dry_run:
        return _result("would_" + action, h, version)
    ensure_indexes(db)
    db[ITEM_COLL].delete_many({"snapshot_id": sid})
    snaps.delete_many({"snapshot_id": sid, "status": "staging"})
    imported_at = datetime.now(UTC).replace(tzinfo=None, microsecond=0)
    snaps.insert_one({**h, "version": version, "status": "staging", "supersedes": cur["snapshot_id"] if cur else None,
                      "imported_at": imported_at})
    try:
        db[ITEM_COLL].insert_many([{"snapshot_id": sid, **i} for i in prep.items])
        if db[ITEM_COLL].count_documents({"snapshot_id": sid}) != len(prep.items):
            raise ImportRejected("ESCRITURA_INCOMPLETA", "El numero de filas escritas no coincide.")
    except BaseException:
        db[ITEM_COLL].delete_many({"snapshot_id": sid})
        snaps.delete_many({"snapshot_id": sid, "status": "staging"})
        raise
    snaps.update_one({"snapshot_id": sid, "status": "staging"}, {"$set": {"status": "current"}})
    if cur:
        snaps.update_one({"snapshot_id": cur["snapshot_id"], "status": "current"}, {"$set": {"status": "superseded"}})
    return _result(action, h, version)


def run(package, db, sql_report=None, dry_run: bool = False, *,
        as_of_local: str = AS_OF_LOCAL, base_as_of_local: str = BASE_AS_OF_LOCAL) -> dict:
    if db.name in PROTECTED_DBS:
        raise ImportRejected("BASE_PROTEGIDA", "No se escribe en bases de desarrollo, v2 ni publicadas.")
    return write_snapshot(db, prepare(Path(package), db, Path(sql_report) if sql_report else None,
                                      as_of_local=as_of_local, base_as_of_local=base_as_of_local), dry_run)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Importa la existencia reconstruida")
    ap.add_argument("--package", required=True)
    ap.add_argument("--db", required=True)
    ap.add_argument("--sql-report", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--as-of-local", default=AS_OF_LOCAL, help="Fecha/hora de cierre (ISO 8601 con zona)")
    ap.add_argument("--base-as-of-local", default=BASE_AS_OF_LOCAL, help="Fecha/hora del conteo base (ISO 8601 con zona)")
    args = ap.parse_args(argv)
    if not _DB_RE.match(args.db):
        print("Nombre de base invalido.", file=sys.stderr)
        return 2
    if args.db in PROTECTED_DBS:
        print("Importacion rechazada [BASE_PROTEGIDA]: no se escribe en bases protegidas.", file=sys.stderr)
        return 1
    try:
        from pymongo import MongoClient
        client = MongoClient(os.environ.get("MONGODB_URI", "mongodb://127.0.0.1:27017"), serverSelectionTimeoutMS=3000)
        try:
            res = run(args.package, client[args.db], args.sql_report, args.dry_run,
                      as_of_local=args.as_of_local, base_as_of_local=args.base_as_of_local)
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
