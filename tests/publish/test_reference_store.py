"""Paquete de referencia T07 en GridFS: push/materialize, manipulacion, rutas inseguras y arranque del worker."""
from __future__ import annotations

import hashlib
import json

import gridfs
import pytest

from pipeline.jobs.worker import ensure_runtime_reference
from pipeline.publish import reference_store as rs
from tests.publish.helpers import temp_db

pytestmark = pytest.mark.mongo


@pytest.fixture
def db():
    with temp_db() as d:
        yield d


def make_pkg(root, files=None):
    files = files or {"artifacts/a.bin": b"AAA", "files/docs/m.json": b"{}", "files/code/x.py": b"print(1)\n"}
    for rel, data in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(data)
    index = {"schema": "df-runtime-reference-1", "files": {r: hashlib.sha256(d).hexdigest() for r, d in files.items()}}
    (root / rs.INDEX_NAME).write_text(json.dumps(index), encoding="utf-8")
    return root


def test_push_materialize_roundtrip_and_idempotent_replacement(db, tmp_path):
    pkg = make_pkg(tmp_path / "pkg")
    assert rs.push(pkg, db) == 3
    assert rs.push(pkg, db) == 3                                         # idempotente: no duplica
    assert db[f"{rs.BUCKET}.files"].count_documents({}) == 4             # 3 archivos + indice
    dest = tmp_path / "out" / "ref"
    assert rs.materialize(db, dest) == 3
    for rel in ("artifacts/a.bin", "files/docs/m.json", "files/code/x.py", rs.INDEX_NAME):
        assert (dest / rel).read_bytes() == (pkg / rel).read_bytes()
    assert rs.is_complete(dest)
    assert rs.materialize(db, dest) == 3                                 # reemplaza un destino existente
    (dest / "artifacts/a.bin").unlink()
    assert not rs.is_complete(dest)
    pkg2 = make_pkg(tmp_path / "pkg2", {"artifacts/n.bin": b"NEW"})
    rs.push(pkg2, db)                                                    # reemplazo: solo queda el nuevo paquete
    assert db[f"{rs.BUCKET}.files"].count_documents({}) == 2


def test_push_rejects_altered_missing_and_unsafe(db, tmp_path):
    pkg = make_pkg(tmp_path / "pkg")
    (pkg / "artifacts/a.bin").write_bytes(b"ZZZ")
    with pytest.raises(rs.ReferenceStoreError) as e:
        rs.push(pkg, db)
    assert e.value.code == "ARCHIVO_ALTERADO" and db[f"{rs.BUCKET}.files"].count_documents({}) == 0
    for bad in ("../x", "/abs", "a/../../b", "a\\b", "C:/x"):
        pkg3 = make_pkg(tmp_path / f"p{abs(hash(bad))}")
        idx = json.loads((pkg3 / rs.INDEX_NAME).read_text())
        idx["files"][bad] = "0" * 64
        (pkg3 / rs.INDEX_NAME).write_text(json.dumps(idx))
        with pytest.raises(rs.ReferenceStoreError) as e:
            rs.push(pkg3, db)
        assert e.value.code == "RUTA_INSEGURA"
    with pytest.raises(rs.ReferenceStoreError):
        rs.push(tmp_path / "no-existe", db)


def test_materialize_rejects_tampered_file_and_unsafe_path_and_leaves_no_residue(db, tmp_path):
    pkg = make_pkg(tmp_path / "pkg")
    rs.push(pkg, db)
    doc = db[f"{rs.BUCKET}.files"].find_one({"filename": "artifacts/a.bin"})
    fs = gridfs.GridFSBucket(db, bucket_name=rs.BUCKET)
    fs.delete(doc["_id"])
    fs.upload_from_stream("artifacts/a.bin", b"MANIPULADO", metadata={"sha256": "x"})
    dest = tmp_path / "out" / "ref"
    with pytest.raises(rs.ReferenceStoreError) as e:
        rs.materialize(db, dest)
    assert e.value.code == "ARCHIVO_ALTERADO" and not dest.exists() and list((tmp_path / "out").iterdir()) == []
    # indice con ruta '..' subido a mano
    idx = json.dumps({"files": {"../fuera.txt": "0" * 64}}).encode()
    db[f"{rs.BUCKET}.files"].delete_many({})
    db[f"{rs.BUCKET}.chunks"].delete_many({})
    fs.upload_from_stream(rs.INDEX_NAME, idx)
    with pytest.raises(rs.ReferenceStoreError) as e:
        rs.materialize(db, dest)
    assert e.value.code == "RUTA_INSEGURA" and not (tmp_path / "out" / "fuera.txt").exists() and not (tmp_path / "fuera.txt").exists()


def test_materialize_without_reference_in_mongo_fails_clearly(db, tmp_path):
    with pytest.raises(rs.ReferenceStoreError) as e:
        rs.materialize(db, tmp_path / "ref")
    assert e.value.code == "REFERENCIA_NO_DISPONIBLE" and not (tmp_path / "ref").exists()


def test_worker_startup_materializes_only_in_mongo_mode_when_missing_or_incomplete(db, tmp_path, monkeypatch):
    rs.push(make_pkg(tmp_path / "pkg"), db)
    target = tmp_path / "runtime" / "ref"
    monkeypatch.setenv("DF_RUNTIME_REFERENCE_DIR", str(target))
    monkeypatch.delenv("DF_RUNTIME_REFERENCE_STORE", raising=False)
    assert ensure_runtime_reference(db) is False and not target.exists()        # modo local: no hace nada
    monkeypatch.setenv("DF_RUNTIME_REFERENCE_STORE", "mongo")
    assert ensure_runtime_reference(db) is True and rs.is_complete(target)
    assert ensure_runtime_reference(db) is False                                # ya completo
    (target / "files/code/x.py").unlink()
    assert ensure_runtime_reference(db) is True and rs.is_complete(target)      # incompleto: se rehace
    monkeypatch.delenv("DF_RUNTIME_REFERENCE_DIR")
    assert ensure_runtime_reference(db) is False


def test_worker_starts_without_reference_in_mongo(db, tmp_path, monkeypatch):
    monkeypatch.setenv("DF_RUNTIME_REFERENCE_DIR", str(tmp_path / "ref"))
    monkeypatch.setenv("DF_RUNTIME_REFERENCE_STORE", "mongo")
    assert ensure_runtime_reference(db) is False and not (tmp_path / "ref").exists()   # no lanza


def test_generate_run_fails_with_a_clear_code_when_the_reference_is_absent(db, tmp_path, monkeypatch):
    from datetime import date

    from tests.jobs.jobs_support import enqueue_generate, run_job
    monkeypatch.setenv("DF_RUNTIME_REFERENCE_DIR", str(tmp_path / "no-hay"))
    enqueue_generate(db, date(2026, 7, 31), max_attempts=1)
    done = run_job(db, tmp_path / "u")
    assert done["status"] == "failed" and done["error"]["code"] not in (None, "ERROR_INTERNO"), done.get("error")
