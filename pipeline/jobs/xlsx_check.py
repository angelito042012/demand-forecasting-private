"""Validacion estructural LIGERA de un .xlsx subido (T10 §3). Reutilizable por la API y por el worker.

No descomprime el libro a memoria: mide el ZIP con el directorio central (tamanos declarados), lee con tope
solo las partes pequenas de metadatos y, con openpyxl en modo lectura, solo las primeras filas. No ejecuta el
importador. Los mensajes no incluyen rutas.
"""
from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from datetime import date, datetime

import openpyxl

from pipeline.data.importer import REQUIRED_HEADERS, normalize_header_row

ZIP_SIGNATURES = (b"PK\x03\x04",)
MAX_RATIO = 200            # relacion de compresion maxima por entrada (un xlsx real ronda 5-30)
RATIO_MIN_BYTES = 1 << 20  # la relacion solo se evalua en entradas declaradas de mas de 1 MiB
META_READ_CAP = 1 << 20    # tope de lectura de partes de metadatos (.rels, [Content_Types].xml)
SAMPLE_ROWS = 200          # filas de datos inspeccionadas para detectar el mes
HEADER_SCAN_ROWS = 20
_EXTERNAL = re.compile(rb"targetmode\s*=\s*[\"']external[\"']", re.IGNORECASE)


class XlsxRejected(Exception):
    """Rechazo con estado HTTP y codigo del contrato; `message` es apto para el usuario (sin rutas)."""

    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message
        super().__init__(message)


@dataclass(frozen=True)
class XlsxInfo:
    month: str            # 'YYYY-MM'
    entries: int
    declared_bytes: int


def has_zip_signature(path) -> bool:
    with open(path, "rb") as fh:
        return fh.read(4) in ZIP_SIGNATURES


def _read_capped(zf: zipfile.ZipFile, info: zipfile.ZipInfo) -> bytes:
    with zf.open(info) as fh:
        return fh.read(META_READ_CAP)


def _check_zip(path, *, max_entries: int, max_expanded: int) -> tuple[int, int]:
    try:
        zf = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError, ValueError, EOFError):
        raise XlsxRejected(422, "ARCHIVO_CORRUPTO", "El archivo está dañado o incompleto y no se puede leer.") from None
    with zf:
        infos = zf.infolist()
        if len(infos) > max_entries:
            raise XlsxRejected(422, "ZIP_INSEGURO", "El archivo contiene demasiadas entradas internas.")
        declared = sum(i.file_size for i in infos)
        if declared > max_expanded:
            raise XlsxRejected(422, "ZIP_INSEGURO", "El contenido expandido declarado excede el límite permitido.")
        names = set()
        for i in infos:
            low = i.filename.replace("\\", "/").lower()
            parts = low.split("/")
            if low.startswith("/") or ".." in parts or ":" in parts[0]:
                raise XlsxRejected(422, "ZIP_INSEGURO", "El archivo contiene entradas con nombres no permitidos.")
            if i.flag_bits & 0x1:
                raise XlsxRejected(422, "ARCHIVO_CIFRADO", "El libro está protegido con contraseña.")
            if i.file_size > RATIO_MIN_BYTES and i.file_size / max(i.compress_size, 1) > MAX_RATIO:
                raise XlsxRejected(422, "ZIP_INSEGURO", "La relación de compresión del archivo no es razonable.")
            if low.endswith(("vbaproject.bin", "vbaprojectsignature.bin")) or "/vbadata" in low:
                raise XlsxRejected(422, "MACROS_NO_PERMITIDAS", "El libro contiene macros, que no se aceptan.")
            if low.startswith("xl/externallinks/"):
                raise XlsxRejected(422, "ENLACES_EXTERNOS", "El libro contiene vínculos a archivos externos.")
            names.add(low)
        if "xl/workbook.xml" not in names:
            raise XlsxRejected(422, "NO_ES_XLSX", "El archivo no tiene la estructura de un libro de Excel (.xlsx).")
        for i in infos:
            low = i.filename.lower()
            try:
                if low == "[content_types].xml":
                    if b"macroenabled" in _read_capped(zf, i).lower():
                        raise XlsxRejected(422, "MACROS_NO_PERMITIDAS", "El libro admite macros, que no se aceptan.")
                elif low.endswith(".rels") and _EXTERNAL.search(_read_capped(zf, i)):
                    raise XlsxRejected(422, "ENLACES_EXTERNOS", "El libro contiene vínculos a recursos externos.")
            except XlsxRejected:
                raise
            except Exception:  # noqa: BLE001 - contenido no confiable: cualquier fallo es un rechazo
                raise XlsxRejected(422, "ARCHIVO_CORRUPTO", "El archivo está dañado y no se puede leer.") from None
        return len(infos), declared


def _as_date(v) -> date | None:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return None


def _check_sheet(path, *, allowed_months: tuple[str, ...], max_rows: int) -> str:
    with open(path, "rb") as handle:     # por objeto de archivo: openpyxl no depende de la extension del temporal
        return _check_sheet_handle(handle, allowed_months=allowed_months, max_rows=max_rows)


def _check_sheet_handle(handle, *, allowed_months: tuple[str, ...], max_rows: int) -> str:
    try:
        book = openpyxl.load_workbook(handle, read_only=True, data_only=True)
    except Exception:  # noqa: BLE001 - contenido no confiable: cualquier fallo es un rechazo
        raise XlsxRejected(422, "NO_ES_XLSX", "No se pudo abrir el libro de Excel.") from None
    try:
        if not book.worksheets:
            raise XlsxRejected(422, "NO_ES_XLSX", "El libro no tiene hojas.")
        sheet = book["Hoja1"] if "Hoja1" in book.sheetnames else book.worksheets[0]
        declared_rows = getattr(sheet, "max_row", None)
        if isinstance(declared_rows, int) and declared_rows > max_rows:
            raise XlsxRejected(422, "HOJA_DEMASIADO_GRANDE", "La hoja excede el número de filas permitido.")
        headers, months, seen = None, set(), 0
        try:
            for n, row in enumerate(sheet.iter_rows(values_only=True), 1):
                if headers is None:
                    if n > HEADER_SCAN_ROWS:
                        break
                    normalized = normalize_header_row(row)
                    if normalized is not None:
                        headers = normalized
                        missing = [c for c in REQUIRED_HEADERS if c not in headers]
                        if missing:
                            raise XlsxRejected(422, "ENCABEZADOS_INVALIDOS",
                                               "Faltan columnas requeridas: " + ", ".join(missing[:8]) + ".")
                    continue
                if not any(v is not None and str(v).strip() != "" for v in row):
                    continue
                d = _as_date(dict(zip(headers, row, strict=False)).get("FECHA"))
                if d is not None:
                    months.add(f"{d.year:04d}-{d.month:02d}")
                seen += 1
                if seen >= SAMPLE_ROWS:
                    break
        except XlsxRejected:
            raise
        except Exception:  # noqa: BLE001 - contenido no confiable: cualquier fallo es un rechazo
            raise XlsxRejected(422, "ARCHIVO_CORRUPTO", "El contenido de la hoja está dañado o es ilegible.") from None
        if headers is None:
            raise XlsxRejected(422, "ENCABEZADOS_INVALIDOS", "No se encontraron los encabezados esperados.")
        if not months:
            raise XlsxRejected(422, "FECHAS_NO_DETECTADAS", "No se detectaron fechas válidas en las primeras filas.")
        if len(months) > 1:
            raise XlsxRejected(422, "MES_AMBIGUO", "Las primeras filas contienen fechas de más de un mes.")
        month = next(iter(months))
        if month not in allowed_months:
            raise XlsxRejected(422, "MES_FUERA_DE_ALCANCE", f"El mes detectado ({month}) no está en los meses permitidos.")
        return month
    finally:
        book.close()


def inspect_xlsx(path, *, max_entries: int = 200, max_expanded: int = 262144000, max_rows: int = 200000,
                 allowed_months: tuple[str, ...] = ("2026-03", "2026-04", "2026-05", "2026-06", "2026-07")) -> XlsxInfo:
    """Valida el archivo ya guardado; lanza XlsxRejected(415/422). No lee el libro completo."""
    if not has_zip_signature(path):
        raise XlsxRejected(415, "FORMATO_NO_SOPORTADO", "El archivo no es un libro .xlsx válido (firma ZIP ausente).")
    entries, declared = _check_zip(path, max_entries=max_entries, max_expanded=max_expanded)
    month = _check_sheet(path, allowed_months=allowed_months, max_rows=max_rows)
    return XlsxInfo(month=month, entries=entries, declared_bytes=declared)
