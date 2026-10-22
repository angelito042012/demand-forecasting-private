"""Almacen de subidas en GridFS (bucket `uploads`) para entornos sin disco compartido API/worker.

Activo solo con DF_UPLOADS_STORE=mongo; sin la variable el comportamiento por archivos no cambia. El nombre del archivo es
`<sha256>.xlsx`; el contenido se verifica contra ese hash al guardar y al descargar. Metadatos sin datos personales.
"""
from __future__ import annotations

import hashlib
import os
import re
import tempfile
from pathlib import Path

import gridfs

BUCKET = "uploads"
_SHA = re.compile(r"^[0-9a-f]{64}$")


class UploadStoreError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


def mongo_mode() -> bool:
    return os.environ.get("DF_UPLOADS_STORE", "").strip().lower() == "mongo"


def _sha_file(path: Path) -> tuple[str, int]:
    h, n = hashlib.sha256(), 0
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
            n += len(block)
    return h.hexdigest(), n


def persist(db, path: Path, sha256: str, size: int) -> None:
    """Guarda el archivo final en GridFS (idempotente por sha256). Verifica hash y tamano antes de escribir."""
    got, n = _sha_file(path)
    if got != sha256 or n != size:
        raise UploadStoreError("ARCHIVO_INCONSISTENTE", "El archivo no coincide con su hash o tamaño declarado.")
    name = f"{sha256}.xlsx"
    if db[f"{BUCKET}.files"].find_one({"filename": name, "metadata.sha256": sha256, "length": size}, {"_id": 1}):
        return
    fs = gridfs.GridFSBucket(db, bucket_name=BUCKET)
    with path.open("rb") as fh:
        fs.upload_from_stream(name, fh, metadata={"sha256": sha256, "size_bytes": size, "kind": "xlsx_upload"})


def fetch(db, sha256: str, dest_dir: Path) -> Path | None:
    """Descarga `<sha256>.xlsx` a `dest_dir` de forma atomica verificando el hash. None si no esta en GridFS."""
    if not _SHA.match(sha256):
        return None
    name = f"{sha256}.xlsx"
    fs = gridfs.GridFSBucket(db, bucket_name=BUCKET)
    docs = list(db[f"{BUCKET}.files"].find({"filename": name}, {"_id": 1}).sort("uploadDate", -1))
    if not docs:
        return None
    dest_dir.mkdir(parents=True, exist_ok=True)
    for doc in docs:                                   # un registro alterado no impide usar otro integro
        fd, tmp_name = tempfile.mkstemp(prefix=".dl-", dir=dest_dir)
        tmp = Path(tmp_name)
        try:
            with os.fdopen(fd, "wb") as out:
                fs.download_to_stream(doc["_id"], out)
            if _sha_file(tmp)[0] == sha256:
                final = dest_dir / name
                os.replace(tmp, final)
                return final
        except gridfs.errors.GridFSError:
            pass
        finally:
            tmp.unlink(missing_ok=True)
    raise UploadStoreError("ARCHIVO_INCONSISTENTE", "El archivo almacenado no coincide con su sha256.")
