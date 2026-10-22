"""Subida segura de libros .xlsx (T10 §3). La peticion NO ejecuta el importador: valida estructura ligera,
guarda el archivo en el directorio privado (`<sha256>.xlsx`, nunca servido) y encola `import_excel`.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from fastapi.concurrency import run_in_threadpool

from backend.app.errors import ApiError
from pipeline.jobs import upload_store
from pipeline.jobs.xlsx_check import XlsxRejected, has_zip_signature, inspect_xlsx

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "t10_config.json"
CHUNK = 1 << 20
MULTIPART_OVERHEAD = 1 << 20      # holgura de cabeceras multipart sobre el tamano del archivo
_LABEL_BAD = re.compile(r"[^A-Za-z0-9._ -]+")


@dataclass(frozen=True)
class UploadPolicy:
    max_bytes: int
    max_expanded: int
    max_entries: int
    max_rows: int
    directory: Path
    allowed_months: tuple[str, ...]
    extension: str = ".xlsx"


@lru_cache
def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def get_upload_policy() -> UploadPolicy:
    """Dependencia (sustituible en pruebas). Politica del SERVIDOR, nunca del cliente."""
    cfg = load_config()
    up = cfg["subidas"]
    return UploadPolicy(
        max_bytes=int(up["tam_max_comprimido_bytes"]), max_expanded=int(up["tam_max_expandido_bytes"]),
        max_entries=int(up["max_entradas_zip"]), max_rows=int(up["max_filas_hoja"]),
        directory=Path(os.environ["DF_UPLOADS_DIR"]) if os.environ.get("DF_UPLOADS_DIR") else ROOT / up["directorio_privado"],  # variable solo para pruebas/operacion
        allowed_months=tuple(cfg["politica_desarrollo"]["meses_permitidos_de_carga"]), extension=up["extension"])


def sanitize_label(filename: str | None) -> str:
    """Etiqueta de presentacion (<= 80 caracteres [A-Za-z0-9._ -]). Nunca participa en rutas."""
    base = re.split(r"[\\/]", filename or "")[-1]
    stem = base[:-5] if base.lower().endswith(".xlsx") else base
    stem = _LABEL_BAD.sub("_", stem).strip(" ._-")
    stem = re.sub(r"\.{2,}", ".", stem)
    return (stem[:80].strip(" ._-")) or "archivo"


def check_declared_length(content_length: str | None, policy: UploadPolicy) -> None:
    """Rechazo temprano por Content-Length, antes de leer el cuerpo."""
    if content_length is None:
        raise ApiError(411, "LONGITUD_REQUERIDA", "La subida requiere la cabecera Content-Length.")
    try:
        declared = int(content_length)
    except ValueError:
        raise ApiError(422, "ENTRADA_INVALIDA", "Content-Length invalido.") from None
    if declared > policy.max_bytes + MULTIPART_OVERHEAD:
        raise too_large(policy)


def too_large(policy: UploadPolicy) -> ApiError:
    mib = policy.max_bytes / (1 << 20)
    return ApiError(413, "ARCHIVO_DEMASIADO_GRANDE", f"El archivo supera el tamaño máximo de {mib:g} MiB.")


async def save_upload(upload, policy: UploadPolicy) -> tuple[Path, str, int]:
    """Copia por bloques (tope estricto) a un temporal privado, calculando sha256. Devuelve (tmp, sha256, bytes)."""
    policy.directory.mkdir(parents=True, exist_ok=True)
    tmp = policy.directory / f".tmp-{uuid.uuid4().hex}"
    digest, total = hashlib.sha256(), 0
    out = await run_in_threadpool(tmp.open, "wb")
    try:
        while True:
            block = await upload.read(CHUNK)
            if not block:
                break
            total += len(block)
            if total > policy.max_bytes:
                raise too_large(policy)
            digest.update(block)
            await run_in_threadpool(out.write, block)
    except BaseException:
        await run_in_threadpool(out.close)
        tmp.unlink(missing_ok=True)
        raise
    await run_in_threadpool(out.close)
    return tmp, digest.hexdigest(), total


def validate_and_store(tmp: Path, sha256: str, policy: UploadPolicy) -> tuple[Path, str]:
    """Valida el temporal y lo mueve de forma atomica a `<sha256>.xlsx`. Devuelve (ruta final, mes)."""
    try:
        if not has_zip_signature(tmp):
            raise XlsxRejected(415, "FORMATO_NO_SOPORTADO", "El archivo no es un libro .xlsx válido (firma ZIP ausente).")
        info = inspect_xlsx(tmp, max_entries=policy.max_entries, max_expanded=policy.max_expanded,
                            max_rows=policy.max_rows, allowed_months=policy.allowed_months)
    except XlsxRejected as exc:
        tmp.unlink(missing_ok=True)
        raise ApiError(exc.status, exc.code, exc.message) from None
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    final = policy.directory / f"{sha256}{policy.extension}"
    if final.exists():
        tmp.unlink(missing_ok=True)       # mismo contenido ya guardado: idempotente
    else:
        os.replace(tmp, final)            # atomico en el mismo volumen
    return final, info.month


def persist_to_store(db, final: Path, sha256: str, size: int) -> None:
    """Con DF_UPLOADS_STORE=mongo guarda los bytes finales en GridFS ANTES de encolar (el worker no comparte disco)."""
    if not upload_store.mongo_mode():
        return
    try:
        upload_store.persist(db, final, sha256, size)
    except upload_store.UploadStoreError as exc:
        final.unlink(missing_ok=True)
        raise ApiError(500, exc.code, exc.message) from None
    except Exception:  # noqa: BLE001 - cualquier fallo del almacen es 503 sin detalles
        raise ApiError(503, "ALMACEN_NO_DISPONIBLE", "No se pudo guardar el archivo en el almacén; reintente.") from None
