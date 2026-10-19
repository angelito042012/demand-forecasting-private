"""Re-normalizacion de los libros originales (copia fiel de scripts/prepare_academic_data.py, version academico_v1).

La imagen de produccion no incluye scripts/, por eso la logica se COPIA aqui (classify, text, number, currency,
registro_id, documento_id, ocurrencias/firmas, seleccion del grupo). La prueba de equivalencia contra los CSV reales
(tests/plan/test_dataset_real.py) acredita que ambas implementaciones producen los mismos registros. Dependencias:
stdlib + openpyxl. Funciones puras: leen libros en modo solo lectura y no escriben nada.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import openpyxl

VERSION = "academico_v1"
START = date(2026, 3, 1)
END = date(2026, 9, 30)
SELECTION_CUTOFF = date(2026, 7, 31)
EXCLUDED_FORECAST_DAYS = frozenset({date(2026, 4, 3), date(2026, 4, 12), date(2026, 6, 7)})
ZERO = Decimal(0)
TOL = Decimal("0.000001")
FIELDS = ["registro_id", "fecha", "producto_id", "producto", "categoria", "almacen",
          "unidad", "cantidad", "moneda", "importe", "tipo_documento", "documento_id",
          "clasificacion", "grupo_repeticion", "ocurrencia", "incluido_grupo",
          "dia_excluido_pronostico", "archivo", "hoja", "fila", "sha256_origen"]
SHEET = "Hoja1"


class NormalizationError(Exception):
    """Libro ilegible o con forma inesperada; `code` es estable y no incluye rutas."""

    def __init__(self, code: str, message: str):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


def number(value):
    if value is None or value == "" or isinstance(value, bool):
        return None
    try:
        n = Decimal(str(value))
        return n if n.is_finite() else None
    except InvalidOperation:
        return None


def text(value):
    if value is None:
        return ""
    if isinstance(value, (int, float, Decimal)):
        n = number(value)
        if n is not None and n == n.to_integral_value():
            return str(int(n))
    return str(value).strip()


def serialize(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, set):
        return sorted(value)
    raise TypeError(type(value).__name__)


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def currency(value):
    v = text(value).upper()
    if "S/" in v or "SOLES" in v:
        return "PEN"
    if "$" in v and "D" in v:
        return "USD"
    return v


def classify(kind, raw):
    """Disposicion de procesamiento, nunca una explicacion inventada del significado comercial."""
    qty, eq, base, amount = (number(raw.get(k)) for k in ("CANTIDAD", "EQUIVALENCIA", "CANTIDAD_UM_BASE", "TOTAL_LINEA"))
    d = raw.get("FECHA")
    if not isinstance(d, (date, datetime)):
        return "CUARENTENA", "FECHA_NO_VALIDA"
    if any(v is None for v in (qty, eq, base, amount)) or eq <= 0:
        return "CUARENTENA", "CANTIDADES_NO_VALIDAS"
    if abs(qty * eq - base) > TOL:
        return "CUARENTENA", "CONVERSION_NO_COINCIDE"
    status = text(raw.get("VEN_ESTADO" if kind == "ventas" else "ESTADO")).upper()
    if status != "ACTIVO" or not text(raw.get("ID_ARTICULO")) or not text(raw.get("ID_ALMACEN")) or not text(raw.get("UM_BASE")):
        return "CUARENTENA", "ESTADO_O_CLAVE_NO_VALIDOS"
    if kind == "ventas" and text(raw.get("TIPO_DOC")) == "7":
        return "CREDITO", "DOCUMENTO_FINANCIERO_SIN_RETORNO_FISICO_INFERIDO"
    if base <= 0:
        return "CUARENTENA", "CANTIDAD_NO_POSITIVA"
    if kind == "compras" and amount < 0:
        return "CUARENTENA", "IMPORTE_NEGATIVO_CON_CANTIDAD_POSITIVA"
    if kind == "ventas" and amount <= 0:
        return "CUARENTENA", "VENTA_SIN_IMPORTE_POSITIVO"
    if kind == "compras" and amount == 0:
        return "COMPRA_SIN_CARGO_REGISTRADO", "CANTIDAD_CONSERVADA_SIN_INFERIR_BONIFICACION"
    return ("VENTA" if kind == "ventas" else "COMPRA"), "CONSERVADO"


def kind_of(path) -> str:
    return "compras" if Path(path).stem.startswith("compra") else "ventas"


def normalize_book(path, digest: str, occurrence: Counter, window=(START, END)) -> tuple[list[dict], dict]:
    """Clasifica un libro. `occurrence` es el contador COMPARTIDO por todos los libros (orden de archivos del script).
    Devuelve (registros, resumen de la fuente). Registros con las claves de FIELDS mas `_kind`/`_signature`/`_reason`."""
    path = Path(path)
    kind = kind_of(path)
    start, end = window
    try:
        book = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except Exception:  # noqa: BLE001 - libro ilegible: sin detalles ni rutas
        raise NormalizationError("LIBRO_ILEGIBLE", f"No se puede leer {path.name} como libro .xlsx.") from None
    out: list[dict] = []
    counts: Counter = Counter()
    original_totals, classified_totals = defaultdict(lambda: ZERO), defaultdict(lambda: ZERO)
    try:
        if book.sheetnames != [SHEET]:
            raise NormalizationError("LIBRO_ESTRUCTURA", f"{path.name}: hojas inesperadas.")
        iterator = book[SHEET].iter_rows(min_row=2, values_only=True)
        try:
            headers = [text(v) for v in next(iterator)]
        except StopIteration:
            raise NormalizationError("LIBRO_ESTRUCTURA", f"{path.name}: sin encabezado en la fila 2.") from None
        for row_num, raw_values in enumerate(iterator, 3):
            if not any(v is not None for v in raw_values):
                continue
            raw = dict(zip(headers, raw_values, strict=False))
            status, reason = classify(kind, raw)
            doc_date = raw.get("FECHA")
            if not isinstance(doc_date, (date, datetime)):
                raise NormalizationError("FECHA_NO_VALIDA", f"{path.name} fila {row_num}: fecha no valida.")
            d = doc_date.date() if isinstance(doc_date, datetime) else doc_date
            if not start <= d <= end:
                raise NormalizationError("FECHA_FUERA_DE_VENTANA", f"{path.name} fila {row_num}: fecha fuera de la ventana declarada.")
            signature = hashlib.sha256(json.dumps(raw_values, ensure_ascii=False, default=serialize).encode()).hexdigest()
            repeat_key = (kind, signature)
            occurrence[repeat_key] += 1
            cur = currency(raw.get("MONEDA"))
            doc_id = hashlib.sha256((kind + "|" + text(raw.get("TIPO_DOC")) + "|" + text(raw.get("SERIE_NUMERO")) + "|"
                                     + text(raw.get("ID_PROVEEDOR")) + "|" + text(raw.get("ID_PEDIDO"))).encode()).hexdigest()[:24]
            r = {"registro_id": hashlib.sha256(f"{digest}:{SHEET}:{row_num}".encode()).hexdigest()[:24],
                 "fecha": d, "producto_id": text(raw.get("ID_ARTICULO")), "producto": text(raw.get("ARTICULO")),
                 "categoria": text(raw.get("GRUPO")), "almacen": text(raw.get("ID_ALMACEN")),
                 "unidad": text(raw.get("UM_BASE")).upper(), "cantidad": number(raw.get("CANTIDAD_UM_BASE")),
                 "moneda": cur, "importe": number(raw.get("TOTAL_LINEA")), "tipo_documento": text(raw.get("TIPO_DOC")),
                 "documento_id": doc_id, "clasificacion": status, "grupo_repeticion": "",
                 "ocurrencia": occurrence[repeat_key], "incluido_grupo": False,
                 "dia_excluido_pronostico": d in EXCLUDED_FORECAST_DAYS,
                 "archivo": path.name, "hoja": SHEET, "fila": row_num, "sha256_origen": digest,
                 "_kind": kind, "_signature": repeat_key, "_reason": reason}
            out.append(r)
            counts[status] += 1
            original_totals[cur] += number(raw.get("TOTAL_LINEA")) or ZERO
            classified_totals[cur] += r["importe"] or ZERO
    finally:
        book.close()
    if original_totals != classified_totals:
        raise NormalizationError("IMPORTES_NO_RECONCILIAN", f"{path.name}: importes por moneda no reconcilian.")
    summary = {"archivo": path.name, "tipo": kind, "sha256": digest, "filas": sum(counts.values()),
               "clasificaciones": dict(counts), "importes_por_moneda": dict(original_totals)}
    return out, summary


def choose_group(records, size):
    """Misma regla de seleccion que el script (cinco meses de venta, >=2 de compra al corte, UND, rango). Devuelve (claves, n_elegibles)."""
    profiles = defaultdict(lambda: {"sale_months": set(), "purchase_months": set(), "sale_days": set(), "sale_units": ZERO})
    for r in records:
        if r["fecha"] > SELECTION_CUTOFF or r["clasificacion"] not in {"VENTA", "COMPRA", "COMPRA_SIN_CARGO_REGISTRADO"}:
            continue
        p = profiles[(r["producto_id"], r["almacen"], r["unidad"])]
        if r["clasificacion"] == "VENTA":
            p["sale_months"].add(r["fecha"].month)
            p["sale_days"].add(r["fecha"])
            p["sale_units"] += r["cantidad"]
        else:
            p["purchase_months"].add(r["fecha"].month)
    eligible = [key for key, p in profiles.items() if len(p["sale_months"]) == 5 and len(p["purchase_months"]) >= 2 and key[2] == "UND"]
    ranked = sorted(eligible, key=lambda key: (-len(profiles[key]["sale_days"]), -profiles[key]["sale_units"], key))
    selected = ranked[:size]
    if len(selected) < size:
        raise NormalizationError("GRUPO_INSUFICIENTE", f"Solo {len(selected)} productos elegibles de {size}.")
    return set(selected), len(eligible)


def normalize_all(paths, digests: dict, group_size: int, window=(START, END)) -> tuple[list[dict], list[dict], int]:
    """Re-normaliza TODOS los libros (en el orden dado, que debe ser sorted() como en el script) y completa
    grupo_repeticion e incluido_grupo. Devuelve (registros, resumenes por fuente, productos elegibles)."""
    rows: list[dict] = []
    sources: list[dict] = []
    occurrence: Counter = Counter()
    for p in paths:
        recs, summary = normalize_book(p, digests[Path(p).name], occurrence, window)
        rows.extend(recs)
        sources.append(summary)
    for r in rows:
        if occurrence[r["_signature"]] > 1:
            r["grupo_repeticion"] = r["_signature"][1][:24]
    selected, eligible = choose_group(rows, group_size)
    for r in rows:
        r["incluido_grupo"] = (r["producto_id"], r["almacen"], r["unidad"]) in selected
    return rows, sources, eligible
