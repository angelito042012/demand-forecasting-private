"""Importador del conteo fisico reportado (T18 §2-§3). Depende de stdlib, pymongo y openpyxl (lectura del Excel).

    python -m pipeline.inventory.reported_count --count-dir <carpeta v2> --group <productos.csv> --db <base>
        [--sales-history-end 2026-09-30] [--dry-run]

Lee la fuente (solo lectura), la valida completa y, solo si todo es correcto, escribe en las colecciones
`inventory_reported_snapshots` / `inventory_reported_items` (staging -> current). No toca `recommendations`,
`runs` ni `inventory_snapshot`. Vacio = no informado = null (nunca 0). Las presentaciones no se multiplican.

R18: el CSV es un DERIVADO del Excel revisado; antes de escribir se contrasta cada registro con las celdas del Excel
(codigo/fila, producto, unidad, presentacion, cantidades, total, observaciones, fecha/hora y almacen) y review.json con la
cabecera del Excel. Las confirmaciones humanas (almacen 1, sin ventas durante el conteo) no estan en el Excel: se verifican
aparte en el CSV y en review.json. Una fuente modificada legitimamente requiere su revision y una version nueva.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import unicodedata
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

SCHEMA_VERSION = 1
SNAP_COLL = "inventory_reported_snapshots"
ITEM_COLL = "inventory_reported_items"
PROTECTED_DBS = frozenset({"demand_forecasting_dev", "demand_forecasting_v2", "demand_forecasting_pub"})
TZ_NAME = "America/Lima"
LIMA_OFFSET = timedelta(hours=-5)
NATURE = "CONTEO_FISICO_REPORTADO_POR_USUARIO"
USE_STATE = "APTO_COMO_SNAPSHOT_FECHADO"
EXCEL_NAME_MAX = 120
_DB_RE = re.compile(r"^[A-Za-z0-9_]{1,63}$")
_UINT = re.compile(r"^\d{1,12}$")
_CODE = re.compile(r"^\d{1,20}$")
REQUIRED_COLUMNS = (
    "producto_id", "producto", "unidad_reporte", "unidad_descripcion_reportada", "cantidad_libre_reportada",
    "cantidad_reservada_reportada", "cantidad_no_vendible_reportada", "cantidad_fisica_total_reportada",
    "fecha_hora_reportada", "zona_horaria", "almacen_nombre_reportado", "almacen_id_confirmado",
    "corte_sin_ventas_confirmado", "naturaleza", "verificacion_independiente", "estado_uso", "archivo_origen",
    "hoja_origen", "fila_origen", "sha256_origen")
# Disposicion de la plantilla recibida (hoja de conteo): metadatos en C3/G3/C4/G4/C5/G5, encabezado en la fila 8, datos desde la 9.
EXCEL_LAYOUT_ID = "solicitud_conteo_50_v1"
EXCEL_HEADER_ROW, EXCEL_FIRST_ROW = 8, 9
EXCEL_HEADER_TOKENS = ("codigo original", "producto", "unidad en reporte", "representa", "libres", "reservadas", "vendibles", "observaciones")
DEFAULT_UNKNOWNS = [
    {"code": "BRECHA_OCTUBRE", "detail": "Las ventas y compras disponibles terminan el 30/09; los dias posteriores "
                                         "al corte son desconocidos, no cero."},
    {"code": "PEDIDOS_PENDIENTES", "detail": "El conteo no informa pedidos por recibir; desconocido, no cero."},
]


class ImportRejected(Exception):
    """Rechazo de la fuente o de la operacion; `code` es estable y no incluye rutas ni secretos."""

    def __init__(self, code: str, message: str):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


@dataclass
class Prepared:
    header: dict          # cabecera sin version/status/supersedes
    items: list[dict]
    csv_sha256: str


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_csv(path: Path, what: str) -> list[dict]:
    if not path.is_file():
        raise ImportRejected("ARCHIVO_FALTANTE", f"Falta {what}.")
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _qty(raw: str | None, field: str, code: str, required: bool) -> int | None:
    v = (raw or "").strip()
    if v == "":
        if required:
            raise ImportRejected("CANTIDAD_INVALIDA", f"{field} vacia en el producto {code}.")
        return None
    if not _UINT.match(v):
        raise ImportRejected("CANTIDAD_INVALIDA", f"{field} del producto {code} no es un entero no negativo.")
    return int(v)


def _flag(raw: str | None) -> bool | None:
    v = (raw or "").strip().lower()
    return True if v == "true" else False if v == "false" else None


def _parse_when(rows: list[dict]) -> tuple[datetime, str]:
    raws = {(r.get("fecha_hora_reportada") or "").strip() for r in rows}
    if len(raws) != 1 or "" in raws:
        raise ImportRejected("FECHA_ZONA_INVALIDA", "La fecha y hora reportada es inconsistente entre filas.")
    raw = raws.pop()
    try:
        local = datetime.fromisoformat(raw)
    except ValueError:
        raise ImportRejected("FECHA_ZONA_INVALIDA", "La fecha y hora reportada no es valida.") from None
    if local.tzinfo is None:
        raise ImportRejected("FECHA_ZONA_INVALIDA", "La fecha y hora reportada no indica zona horaria.")
    if {(r.get("zona_horaria") or "").strip() for r in rows} != {TZ_NAME}:
        raise ImportRejected("FECHA_ZONA_INVALIDA", f"La zona horaria debe ser {TZ_NAME}.")
    expected = local.replace(tzinfo=ZoneInfo(TZ_NAME)).utcoffset()
    if local.utcoffset() != LIMA_OFFSET or expected != LIMA_OFFSET:
        raise ImportRejected("FECHA_ZONA_INVALIDA", "El desfase de la fecha debe ser UTC-05:00 (America/Lima).")
    return local.astimezone(UTC).replace(tzinfo=None), raw


def _norm(text) -> str:
    t = unicodedata.normalize("NFKD", str(text if text is not None else "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", t).strip().lower()


def _mismatch(what: str) -> ImportRejected:
    return ImportRejected("DERIVADO_NO_COINCIDE", f"El CSV derivado no coincide con el Excel revisado: {what}.")


def _cell_qty(v, where: str) -> str:
    """Celda de cantidad del Excel como texto canonico: vacio => ''; entero => '96'. Texto, fraccion o formula no se aceptan."""
    if v is None or (isinstance(v, str) and v.strip() == ""):
        return ""
    if isinstance(v, (bool, str)):
        raise _mismatch(f"{where} no es un numero entero")
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    if not isinstance(v, int):
        raise _mismatch(f"{where} no es un numero entero")
    return str(v)


def _cell_text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, str) and v.lstrip().startswith("="):
        raise _mismatch("hay una formula en una celda de texto")
    return str(v).strip()


def verify_against_excel(xlsx: Path, sheet: str, rows: list[dict], as_of_local: str, wh_name: str, review: dict) -> dict:
    """Contrasta CADA registro del CSV, la fecha/hora/almacen y review.json con las celdas del Excel (solo lectura).
    Devuelve los metadatos leidos del Excel; lanza ImportRejected(DERIVADO_NO_COINCIDE) ante cualquier diferencia."""
    try:
        from openpyxl import load_workbook
        wb = load_workbook(xlsx, read_only=True, data_only=False)
    except Exception:  # noqa: BLE001 - archivo ilegible: no se confia en el derivado
        raise ImportRejected("FUENTE_ALTERADA", "El Excel de origen no se puede leer como libro .xlsx.") from None
    try:
        if sheet not in wb.sheetnames:
            raise _mismatch("la hoja de origen no existe")
        grid = [list(r) for r in wb[sheet].iter_rows(values_only=True)]
    finally:
        wb.close()

    def cell(r: int, c: int):                      # r, c base 1
        return grid[r - 1][c - 1] if r - 1 < len(grid) and c - 1 < len(grid[r - 1]) else None

    header = [_norm(cell(EXCEL_HEADER_ROW, c)) for c in range(1, 9)]
    if not all(tok in h for tok, h in zip(EXCEL_HEADER_TOKENS, header, strict=True)):
        raise _mismatch("el encabezado de la hoja no corresponde a la plantilla de conteo")
    # --- metadatos (fecha, hora, almacen, responsable, alcance, movimientos)
    d, t = cell(3, 3), cell(3, 7)
    if isinstance(d, datetime):
        d = d.date()
    if not isinstance(d, date) or not hasattr(t, "hour"):
        raise _mismatch("fecha u hora del conteo no son valores de fecha/hora")
    hh, mm = t.hour, t.minute
    xl_local = datetime(d.year, d.month, d.day, hh, mm, tzinfo=timezone(LIMA_OFFSET)).isoformat()
    if xl_local != as_of_local:
        raise _mismatch("la fecha y hora del CSV no son las del documento")
    xl_wh = _cell_text(cell(4, 3))
    if xl_wh != wh_name:
        raise _mismatch("el almacen del CSV no es el del documento")
    meta = {"warehouse_name": xl_wh, "responsible": _cell_text(cell(4, 7)), "scope": _cell_text(cell(5, 3)),
            "movement_statement": _cell_text(cell(5, 7))}
    rmeta = review.get("metadata")
    if not isinstance(rmeta, dict):
        raise _mismatch("review.json no trae los metadatos del documento")
    for k, v in meta.items():
        if str(rmeta.get(k, "")).strip() != v:
            raise _mismatch(f"review.json difiere del documento en {k}")
    if str(rmeta.get("count_date", ""))[:10] != d.isoformat() or str(rmeta.get("count_time", ""))[:5] != f"{hh:02d}:{mm:02d}":
        raise _mismatch("review.json difiere del documento en la fecha u hora del conteo")
    # --- filas de datos: correspondencia exacta registro a registro
    xl_rows = {r for r in range(EXCEL_FIRST_ROW, len(grid) + 1) if _cell_text(cell(r, 1)) != ""}
    by_row = {}
    for rec in rows:
        try:
            n = int(rec["fila_origen"])
        except ValueError:
            raise ImportRejected("CSV_ESTRUCTURA_INVALIDA", "fila_origen invalida.") from None
        if n in by_row:
            raise _mismatch("dos registros citan la misma fila del documento")
        by_row[n] = rec
    if set(by_row) != xl_rows:
        raise _mismatch("las filas del CSV no son exactamente las filas de datos del documento")
    for n, rec in by_row.items():
        raw = cell(n, 1)
        if isinstance(raw, bool) or not isinstance(raw, (str, int)) or _cell_text(raw) != rec["producto_id"]:
            raise _mismatch(f"el codigo de la fila {n} no coincide")
        if _cell_text(cell(n, 2)) != (rec["producto"] or "").strip():
            raise _mismatch(f"el producto de la fila {n} no coincide")
        if _cell_text(cell(n, 3)) != (rec["unidad_reporte"] or "").strip():
            raise _mismatch(f"la unidad de la fila {n} no coincide")
        if _cell_text(cell(n, 4)) != (rec["unidad_descripcion_reportada"] or "").strip():
            raise _mismatch(f"la presentacion de la fila {n} no coincide")
        q = [_cell_qty(cell(n, c), f"la cantidad de la fila {n}") for c in (5, 6, 7)]
        fields = ("cantidad_libre_reportada", "cantidad_reservada_reportada", "cantidad_no_vendible_reportada")
        for got, field in zip(q, fields, strict=True):
            if got != (rec[field] or "").strip():
                raise _mismatch(f"{field} de la fila {n} no coincide")
        expected_total = str(sum(int(x) for x in q)) if all(x != "" for x in q) else ""
        if (rec["cantidad_fisica_total_reportada"] or "").strip() != expected_total:
            raise _mismatch(f"el total de la fila {n} no se deriva de las celdas del documento")
        if _cell_text(cell(n, 8)) != (rec.get("observaciones") or "").strip():
            raise _mismatch(f"las observaciones de la fila {n} no coinciden")
    return {"layout": EXCEL_LAYOUT_ID, "metadata": meta, "rows_verified": len(by_row)}


def prepare(count_dir: Path, group_csv: Path, sales_history_end: str = "2026-09-30") -> Prepared:
    try:
        date.fromisoformat(sales_history_end)
    except ValueError:
        raise ImportRejected("FECHA_ZONA_INVALIDA", "sales-history-end debe ser una fecha AAAA-MM-DD.") from None
    count_dir, group_csv = Path(count_dir), Path(group_csv)
    csv_path = count_dir / "conteo_reportado.csv"
    review_path = count_dir / "review.json"
    rows = _read_csv(csv_path, "conteo_reportado.csv")
    if not review_path.is_file():
        raise ImportRejected("ARCHIVO_FALTANTE", "Falta review.json.")
    try:
        review = json.loads(review_path.read_text(encoding="utf-8-sig"))
    except ValueError:
        raise ImportRejected("FUENTE_ALTERADA", "review.json no es JSON valido.") from None
    if not rows:
        raise ImportRejected("CSV_ESTRUCTURA_INVALIDA", "El CSV no tiene filas.")
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in rows[0]]
    if missing_cols:
        raise ImportRejected("CSV_ESTRUCTURA_INVALIDA", f"Faltan columnas: {', '.join(missing_cols)}.")

    # --- huella del Excel contra CSV (todas las filas) y review.json
    names = {(r["archivo_origen"] or "").strip() for r in rows}
    if len(names) != 1:
        raise ImportRejected("FUENTE_ALTERADA", "El CSV cita mas de un archivo de origen.")
    xlsx_name = names.pop()
    if not xlsx_name or Path(xlsx_name).name != xlsx_name or len(xlsx_name) > EXCEL_NAME_MAX:
        raise ImportRejected("FUENTE_ALTERADA", "Nombre de archivo de origen no valido.")
    xlsx = count_dir / xlsx_name
    if not xlsx.is_file():
        raise ImportRejected("ARCHIVO_FALTANTE", "Falta el Excel de origen.")
    xlsx_sha = _sha256_file(xlsx)
    csv_shas = {(r["sha256_origen"] or "").strip().lower() for r in rows}
    if csv_shas != {xlsx_sha} or review.get("source_sha256") != xlsx_sha or review.get("source_unchanged") is not True:
        raise ImportRejected("FUENTE_ALTERADA", "El SHA-256 del Excel no coincide con el CSV y review.json.")
    sheets = {(r["hoja_origen"] or "").strip() for r in rows}
    if len(sheets) != 1 or "" in sheets:
        raise ImportRejected("FUENTE_ALTERADA", "El CSV cita mas de una hoja de origen.")

    # --- confirmaciones y naturaleza
    for r in rows:
        # la fuente real marca la confirmacion como "True" y el id en almacen_id_candidato; se admite tambien "1"
        conf = (r["almacen_id_confirmado"] or "").strip().lower()
        cand = (r.get("almacen_id_candidato") or "1").strip()
        if conf not in ("true", "1") or cand != "1":
            raise ImportRejected("ALMACEN_NO_CONFIRMADO", "El almacen 1 no esta confirmado en todas las filas.")
        if _flag(r["corte_sin_ventas_confirmado"]) is not True:
            raise ImportRejected("CORTE_NO_CONFIRMADO", "No esta confirmado el conteo sin ventas simultaneas.")
        if (r["estado_uso"] or "").strip() != USE_STATE:
            raise ImportRejected("ESTADO_NO_APTO", f"estado_uso debe ser {USE_STATE}.")
        if (r["naturaleza"] or "").strip() != NATURE:
            raise ImportRejected("NATURALEZA_INVALIDA", f"naturaleza debe ser {NATURE}.")
        if _flag(r["verificacion_independiente"]) is not False:
            raise ImportRejected("VERIFICACION_INVALIDA", "verificacion_independiente debe ser falso.")
    wh_names = {(r["almacen_nombre_reportado"] or "").strip() for r in rows}
    if len(wh_names) != 1 or "" in wh_names:
        raise ImportRejected("ALMACEN_NO_CONFIRMADO", "El nombre de almacen es inconsistente o vacio.")
    as_of_utc, as_of_local = _parse_when(rows)
    uc0 = review.get("user_confirmation")
    if not isinstance(uc0, dict) or str(uc0.get("warehouse_id", "")).strip() != "1" or uc0.get("no_sales_during_count") is not True:
        raise ImportRejected("CORTE_NO_CONFIRMADO", "review.json no registra las confirmaciones humanas (almacen 1, sin ventas durante el conteo).")

    # --- catalogo del grupo: conjunto exacto de codigos
    group_rows = _read_csv(group_csv, "el catalogo del grupo")
    catalog = {}
    for g in group_rows:
        if (g.get("seleccionado") or "True").strip().lower() == "true":
            catalog[(g.get("producto_id") or "").strip()] = g
    codes = [(r["producto_id"] or "") for r in rows]
    for c in codes:
        if not _CODE.match(c):
            raise ImportRejected("CODIGO_INVALIDO", "Hay un producto_id que no es texto de digitos conservado tal cual.")
    seen, dup = set(), set()
    for c in codes:
        (dup if c in seen else seen).add(c)
    if dup:
        raise ImportRejected("CODIGO_REPETIDO", f"Codigos repetidos: {', '.join(sorted(dup)[:5])}.")
    extra, absent = sorted(seen - set(catalog)), sorted(set(catalog) - seen)
    if absent:
        raise ImportRejected("CODIGOS_FALTANTES", f"Faltan {len(absent)} codigos del grupo: {', '.join(absent[:5])}.")
    if extra:
        raise ImportRejected("CODIGOS_SOBRANTES", f"Sobran {len(extra)} codigos fuera del grupo: {', '.join(extra[:5])}.")

    # --- filas
    items = []
    for r in rows:
        code, cat = r["producto_id"], catalog[r["producto_id"]]
        if (r["producto"] or "").strip() != (cat.get("producto") or "").strip():
            raise ImportRejected("NOMBRE_NO_COINCIDE", f"El nombre del producto {code} no coincide con el catalogo.")
        unit = (r["unidad_reporte"] or "").strip()
        if unit != (cat.get("unidad") or "").strip() or unit != "UND":
            raise ImportRejected("UNIDAD_NO_COINCIDE", f"La unidad del producto {code} no coincide con el catalogo.")
        desc = (r["unidad_descripcion_reportada"] or "").strip()
        if not desc:
            raise ImportRejected("PRESENTACION_FALTANTE", f"Falta la descripcion de presentacion del producto {code}.")
        libre = _qty(r["cantidad_libre_reportada"], "cantidad_libre_reportada", code, True)
        res = _qty(r["cantidad_reservada_reportada"], "cantidad_reservada_reportada", code, False)
        nov = _qty(r["cantidad_no_vendible_reportada"], "cantidad_no_vendible_reportada", code, False)
        tot = _qty(r["cantidad_fisica_total_reportada"], "cantidad_fisica_total_reportada", code, False)
        if None not in (res, nov, tot) and tot != libre + res + nov:
            raise ImportRejected("TOTAL_INCONSISTENTE", f"El total del producto {code} no es libre+reservada+no vendible.")
        try:
            src_row = int(r["fila_origen"])
        except ValueError:
            raise ImportRejected("CSV_ESTRUCTURA_INVALIDA", f"fila_origen invalida en el producto {code}.") from None
        items.append({"producto_id": code, "producto": cat["producto"].strip(),
                      "categoria": (cat.get("categoria") or "").strip(), "unidad_reporte": unit,
                      "unidad_descripcion": desc, "libre": libre, "reservada": res, "no_vendible": nov,
                      "fisica_total": tot, "source_row": src_row})
    # R18: ultima barrera antes de escribir: cada registro del derivado debe corresponder a las celdas del Excel revisado
    excel_check = verify_against_excel(xlsx, next(iter(sheets)), rows, as_of_local, next(iter(wh_names)), review)
    items.sort(key=lambda i: i["producto_id"])

    local_dt = datetime.fromisoformat(as_of_local)
    wh_id = "1"
    sid = f"invrep-{local_dt:%Y%m%d}T{local_dt:%H%M}-a{wh_id}-{xlsx_sha[:12]}"
    pend = review.get("pending_questions")
    unknowns = []
    if isinstance(pend, list):
        unknowns = [{"code": str(p["code"]), "detail": str(p["detail"])} for p in pend
                    if isinstance(p, dict) and p.get("code") and p.get("detail")]
    ucodes = {u["code"] for u in unknowns}
    unknowns += [u for u in DEFAULT_UNKNOWNS if u["code"] not in ucodes]
    uc = review.get("user_confirmation") if isinstance(review.get("user_confirmation"), dict) else {}
    with_stock = sum(1 for i in items if i["libre"] > 0)
    header = {
        "snapshot_id": sid, "as_of_utc": as_of_utc, "as_of_local": local_dt.isoformat(), "timezone": TZ_NAME,
        "warehouse": {"id": wh_id, "name": wh_names.pop()}, "nature": NATURE, "independent_verification": False,
        "source": {"file": xlsx_name, "sheet": sheets.pop(), "sha256": xlsx_sha, "csv_sha256": _sha256_file(csv_path),
                   "verified_against_excel": True, "excel_layout": excel_check["layout"], "excel_rows_verified": excel_check["rows_verified"]},
        "confirmations": {"warehouse_id_confirmed": "1", "no_sales_during_count": True,
                          "evidence": str(uc.get("evidence", ""))[:200]},
        "coverage": {"expected": len(catalog), "items": len(items), "group_file": group_csv.name,
                     "group_sha256": _sha256_file(group_csv)},
        "counts": {"items": len(items), "with_stock": with_stock, "no_stock": len(items) - with_stock},
        "declared_unknowns": unknowns, "context": {"sales_history_end": sales_history_end},
        "schema_version": SCHEMA_VERSION,
    }
    return Prepared(header, items, header["source"]["csv_sha256"])


def ensure_indexes(db) -> None:
    db[SNAP_COLL].create_index([("snapshot_id", 1)], name="snapshot_id_unique", unique=True)
    db[SNAP_COLL].create_index([("warehouse.id", 1), ("as_of_utc", 1), ("version", 1)],
                               name="wh_asof_version_unique", unique=True)
    db[ITEM_COLL].create_index([("snapshot_id", 1), ("producto_id", 1)], name="snapshot_product_unique", unique=True)


def _result(action: str, header: dict, version: int, items: list[dict]) -> dict:
    c = header["counts"]
    return {"action": action, "snapshot_id": header["snapshot_id"], "version": version, "items": len(items),
            "con_existencia": c["with_stock"], "sin_existencia": c["no_stock"]}


def write_snapshot(db, prep: Prepared, dry_run: bool = False) -> dict:
    if db.name in PROTECTED_DBS:
        raise ImportRejected("BASE_PROTEGIDA", "No se escribe en bases de desarrollo, v2 ni publicadas.")
    h, snaps = prep.header, db[SNAP_COLL]
    sid, wh, asof = h["snapshot_id"], h["warehouse"]["id"], h["as_of_utc"]
    same = snaps.find_one({"snapshot_id": sid}, {"_id": 0})
    if same and same["status"] == "current":
        if same["source"].get("csv_sha256") != prep.csv_sha256:
            raise ImportRejected("FUENTE_ALTERADA", "Mismo Excel con un CSV derivado distinto; no se reemplaza.")
        return _result("unchanged", h, same["version"], prep.items)
    if same and same["status"] == "superseded":
        raise ImportRejected("VERSION_SUSTITUIDA", "Esa fuente ya fue sustituida por una version posterior.")
    cur = snaps.find_one({"warehouse.id": wh, "as_of_utc": asof, "status": "current"}, {"_id": 0})
    last = snaps.find_one({"warehouse.id": wh, "as_of_utc": asof, "snapshot_id": {"$ne": sid}}, {"version": 1},
                          sort=[("version", -1)])
    version = (last["version"] if last else 0) + 1
    action = "created" if last is None else "new_version"
    if dry_run:
        return _result("would_" + action, h, version, prep.items)
    ensure_indexes(db)
    # intento interrumpido de este mismo snapshot: se limpia por su propio id (nunca otros)
    db[ITEM_COLL].delete_many({"snapshot_id": sid})
    snaps.delete_many({"snapshot_id": sid, "status": "staging"})
    imported_at = datetime.now(UTC).replace(tzinfo=None, microsecond=0)
    doc = {**h, "version": version, "status": "staging", "supersedes": cur["snapshot_id"] if cur else None,
           "imported_at": imported_at}
    snaps.insert_one(dict(doc))
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
    return _result(action, h, version, prep.items)


def run(count_dir, group_csv, db, sales_history_end: str = "2026-09-30", dry_run: bool = False) -> dict:
    if db.name in PROTECTED_DBS:
        raise ImportRejected("BASE_PROTEGIDA", "No se escribe en bases de desarrollo, v2 ni publicadas.")
    return write_snapshot(db, prepare(Path(count_dir), Path(group_csv), sales_history_end), dry_run)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Importa el conteo fisico reportado como snapshot fechado")
    ap.add_argument("--count-dir", required=True)
    ap.add_argument("--group", required=True)
    ap.add_argument("--db", required=True)
    ap.add_argument("--sales-history-end", default="2026-09-30")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    if not _DB_RE.match(args.db):
        print("Nombre de base invalido.", file=sys.stderr)
        return 2
    if args.db in PROTECTED_DBS:
        print("Importacion rechazada [BASE_PROTEGIDA]: no se escribe en bases protegidas.", file=sys.stderr)
        return 1
    try:
        prep = prepare(Path(args.count_dir), Path(args.group), args.sales_history_end)
        from pymongo import MongoClient
        client = MongoClient(os.environ.get("MONGODB_URI", "mongodb://127.0.0.1:27017"),
                             serverSelectionTimeoutMS=3000)
        try:
            res = write_snapshot(client[args.db], prep, args.dry_run)
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
