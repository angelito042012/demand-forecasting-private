"""Subidas en GridFS (DF_UPLOADS_STORE=mongo): API y worker con directorios distintos, reinicio y manipulacion."""
from __future__ import annotations

import hashlib
import shutil

import gridfs
import pytest

from pipeline.jobs import upload_store
from pipeline.jobs.keys import import_key
from tests.backend import test_t10_api as t10
from tests.jobs.jobs_support import enqueue_import, month_rows, run_job, store_upload
from tests.publish.helpers import temp_db

pytestmark = pytest.mark.mongo

db, settings, users, policy, app, admin_s = t10.db, t10.settings, t10.users, t10.policy, t10.app, t10.admin_s


@pytest.fixture
def mongo_mode(monkeypatch):
    monkeypatch.setenv("DF_UPLOADS_STORE", "mongo")


@pytest.fixture
def tdb():
    with temp_db() as d:
        yield d


def test_api_stores_in_gridfs_and_worker_with_another_dir_imports_even_after_restart(mongo_mode, admin_s, db, policy, tmp_path):
    data = t10.make_xlsx()
    sha = hashlib.sha256(data).hexdigest()
    r = admin_s.upload(data)
    assert r.status_code == 202, r.text
    files = list(db["uploads.files"].find({"filename": f"{sha}.xlsx"}))
    assert len(files) == 1 and files[0]["length"] == len(data) and files[0]["metadata"]["sha256"] == sha
    assert set(files[0]["metadata"]) == {"sha256", "size_bytes", "kind"}                 # sin datos personales
    assert admin_s.upload(data).status_code == 202 and db["uploads.files"].count_documents({}) == 1   # idempotente
    worker_dir = tmp_path / "worker_uploads"                                              # NO es el de la API
    assert worker_dir != policy.directory and not worker_dir.exists()
    done = run_job(db, worker_dir)
    assert done["status"] == "completed", done.get("error")
    assert (worker_dir / f"{sha}.xlsx").read_bytes() == data
    shutil.rmtree(worker_dir)                                                             # reinicio: el disco se pierde
    shutil.rmtree(policy.directory)
    enqueue_import(db, sha, len(data), "2026-06", key=import_key(sha) + ":otra")
    again = run_job(db, worker_dir)
    assert again["status"] == "completed" and (worker_dir / f"{sha}.xlsx").is_file()


def test_without_the_variable_nothing_goes_to_gridfs(admin_s, db):
    assert admin_s.upload(t10.make_xlsx()).status_code == 202
    assert db["uploads.files"].count_documents({}) == 0


def test_missing_in_gridfs_is_archivo_no_disponible(mongo_mode, tdb, tmp_path):
    sha = "a" * 64
    enqueue_import(tdb, sha, 10, "2026-06")
    done = run_job(tdb, tmp_path / "w")
    assert done["status"] == "failed" and done["error"]["code"] == "ARCHIVO_NO_DISPONIBLE"


def test_tampered_gridfs_content_is_rejected_and_not_written(mongo_mode, tdb, tmp_path):
    sha, size = store_upload(tmp_path / "src", tmp_path, month_rows(3, n_sales=4, n_credit=0, bad_currency=0), "a.xlsx")
    src = tmp_path / "src" / f"{sha}.xlsx"
    bad = b"PK\x03\x04" + b"manipulado" * 5
    gridfs.GridFSBucket(tdb, bucket_name="uploads").upload_from_stream(f"{sha}.xlsx", bad, metadata={"sha256": sha})
    assert src.is_file()
    enqueue_import(tdb, sha, size, "2026-03")
    w = tmp_path / "w"
    done = run_job(tdb, w)
    assert done["status"] == "failed" and done["error"]["code"] == "ARCHIVO_NO_DISPONIBLE"
    assert not (w / f"{sha}.xlsx").exists() and not list(w.glob(".dl-*"))
    assert tdb.sales.count_documents({}) == 0


def test_persist_checks_hash_and_size_and_is_idempotent(tdb, tmp_path):
    f = tmp_path / "x.xlsx"
    f.write_bytes(b"contenido")
    sha = hashlib.sha256(b"contenido").hexdigest()
    with pytest.raises(upload_store.UploadStoreError):
        upload_store.persist(tdb, f, "0" * 64, 9)
    with pytest.raises(upload_store.UploadStoreError):
        upload_store.persist(tdb, f, sha, 8)
    assert tdb["uploads.files"].count_documents({}) == 0
    upload_store.persist(tdb, f, sha, 9)
    upload_store.persist(tdb, f, sha, 9)
    assert tdb["uploads.files"].count_documents({}) == 1
    out = upload_store.fetch(tdb, sha, tmp_path / "d")
    assert out.read_bytes() == b"contenido" and upload_store.fetch(tdb, "b" * 64, tmp_path / "d") is None
    assert upload_store.fetch(tdb, "no-es-hash", tmp_path / "d") is None


def test_local_mode_keeps_the_previous_behaviour(tdb, tmp_path):
    sha = "c" * 64
    enqueue_import(tdb, sha, 10, "2026-06")
    done = run_job(tdb, tmp_path / "w")
    assert done["status"] == "failed" and done["error"]["code"] == "ARCHIVO_NO_DISPONIBLE"
    assert not upload_store.mongo_mode()
