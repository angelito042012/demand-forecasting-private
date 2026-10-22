"""Paquete de referencia T07 en GridFS (bucket `runtime_reference`) para entornos sin disco persistente.

    python -m pipeline.publish.reference_store push --dir <paquete> [--db NOMBRE]
    python -m pipeline.publish.reference_store materialize --dest <dir> [--db NOMBRE]

Lee MONGODB_URI / MONGODB_DATABASE del entorno; nunca imprime la URI. `push` valida los sha256 declarados en
manifest_referencia.json; `materialize` descarga a un temporal, verifica cada hash y mueve de forma atomica.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path, PurePosixPath

import gridfs

BUCKET = "runtime_reference"
INDEX_NAME = "manifest_referencia.json"
_HEX = set("0123456789abcdef")


class ReferenceStoreError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


def safe_rel(rel: str) -> str:
    p = PurePosixPath(rel)
    if not isinstance(rel, str) or not rel or "\\" in rel or p.is_absolute() or ".." in p.parts or ":" in rel:
        raise ReferenceStoreError("RUTA_INSEGURA", "Ruta relativa no permitida en el paquete de referencia.")
    return p.as_posix()


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _declared(index: dict) -> dict[str, str]:
    files = index.get("files") if isinstance(index, dict) else None
    if not isinstance(files, dict) or not files:
        raise ReferenceStoreError("MANIFIESTO_INVALIDO", "El manifiesto de referencia no declara archivos.")
    out = {}
    for rel, sha in files.items():
        if not (isinstance(sha, str) and len(sha) == 64 and set(sha) <= _HEX):
            raise ReferenceStoreError("MANIFIESTO_INVALIDO", "Hash declarado inválido en el manifiesto de referencia.")
        out[safe_rel(rel)] = sha
    return out


def push(src: Path, db) -> int:
    """Sube el paquete (validando hashes) y reemplaza el anterior solo despues de subir todo."""
    root = Path(src).resolve()
    try:
        index_bytes = (root / INDEX_NAME).read_bytes()
        declared = _declared(json.loads(index_bytes))
    except (OSError, ValueError):
        raise ReferenceStoreError("MANIFIESTO_INVALIDO", "manifest_referencia.json ilegible.") from None
    for rel, sha in declared.items():
        p = (root / rel).resolve()
        if not p.is_relative_to(root) or not p.is_file() or _sha(p) != sha:
            raise ReferenceStoreError("ARCHIVO_ALTERADO", f"Archivo ausente o con sha256 distinto al declarado: {rel}")
    fs = gridfs.GridFSBucket(db, bucket_name=BUCKET)
    new_ids = []
    try:
        new_ids.append(fs.upload_from_stream(INDEX_NAME, io.BytesIO(index_bytes),
                                             metadata={"sha256": hashlib.sha256(index_bytes).hexdigest()}))
        for rel, sha in declared.items():
            with (root / rel).open("rb") as fh:
                new_ids.append(fs.upload_from_stream(rel, fh, metadata={"sha256": sha}))
    except BaseException:
        for i in new_ids:
            fs.delete(i)
        raise
    keep = set(new_ids)
    for f in list(db[f"{BUCKET}.files"].find({}, {"_id": 1})):
        if f["_id"] not in keep:
            fs.delete(f["_id"])
    return len(declared)


def _download(fs, db, rel: str, dest: Path) -> str:
    doc = db[f"{BUCKET}.files"].find_one({"filename": rel}, {"_id": 1}, sort=[("uploadDate", -1)])
    if doc is None:
        raise ReferenceStoreError("REFERENCIA_NO_DISPONIBLE", f"Falta en Mongo un archivo de la referencia: {rel}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as out:
        fs.download_to_stream(doc["_id"], out)
    return _sha(dest)


def materialize(db, dest: Path) -> int:
    dest = Path(dest)
    fs = gridfs.GridFSBucket(db, bucket_name=BUCKET)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=".ref-", dir=dest.parent))
    try:
        _download(fs, db, INDEX_NAME, tmp / INDEX_NAME)
        declared = _declared(json.loads((tmp / INDEX_NAME).read_text(encoding="utf-8")))
        for rel, sha in declared.items():
            if _download(fs, db, rel, tmp / rel) != sha:
                raise ReferenceStoreError("ARCHIVO_ALTERADO", f"sha256 distinto al declarado: {rel}")
        if dest.exists():
            shutil.rmtree(dest)
        os.replace(tmp, dest)
        return len(declared)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def is_complete(directory: Path) -> bool:
    """El directorio tiene el indice y todos los archivos declarados (comprobacion barata, sin hashes)."""
    try:
        declared = _declared(json.loads((Path(directory) / INDEX_NAME).read_text(encoding="utf-8")))
    except (OSError, ValueError, ReferenceStoreError):
        return False
    return all((Path(directory) / rel).is_file() for rel in declared)


def main(argv=None) -> int:
    from pipeline.data.importer import get_client
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=["push", "materialize"])
    ap.add_argument("--dir", type=Path)
    ap.add_argument("--dest", type=Path)
    ap.add_argument("--db", default=os.environ.get("MONGODB_DATABASE"))
    a = ap.parse_args(argv)
    if not a.db:
        print("Falta --db o MONGODB_DATABASE.", file=sys.stderr)
        return 2
    path = a.dir if a.action == "push" else a.dest
    if not path:
        print("Falta --dir (push) o --dest (materialize).", file=sys.stderr)
        return 2
    client = get_client()
    try:
        if a.action == "push":
            print(f"Referencia subida: {push(path, client[a.db])} archivos.")
        else:
            print(f"Referencia materializada: {materialize(client[a.db], path)} archivos.")
    except ReferenceStoreError as exc:
        print(f"[{exc.code}] {exc.message}", file=sys.stderr)
        return 1
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
