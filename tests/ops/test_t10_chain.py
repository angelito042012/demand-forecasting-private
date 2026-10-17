"""T10: cadena REAL en procesos separados (Uvicorn + worker) sobre una base temporal aislada:
carga web -> cola -> worker -> importacion; duplicado, fuente conflictiva, corrupto, agosto, lector. Sin tocar datos reales."""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

import httpx
import pytest
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from backend.app.auth.store import create_user
from tests.data.conftest import make_row, write_xlsx

pytestmark = pytest.mark.mongo
ROOT = Path(__file__).resolve().parents[2]
ORIGIN = "http://localhost:4200"
PW = "clave-de-prueba-123"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _june_file(path: Path, sku: int = 100, n: int = 3) -> Path:
    rows = [make_row(ID_PEDIDO=1000 + i, SERIE_NUMERO=f"B{sku}-{i}", ID_ARTICULO=sku + i, FECHA=datetime(2026, 6, 2 + i),
                     CANTIDAD=2, CANTIDAD_UM_BASE=2, TOTAL_LINEA=11.0) for i in range(n)]
    rows.append(make_row(ID_PEDIDO=0, TIPO_DOC=7, SERIE_NUMERO=f"NC{sku}", FECHA=datetime(2026, 6, 9), CANTIDAD=-1,
                         CANTIDAD_UM_BASE=-1, TOTAL_LINEA=-5.5, ID_ARTICULO=sku))
    return write_xlsx(path, rows)


@pytest.fixture
def stack(tmp_path):
    uri = os.environ.get("MONGODB_URI", "mongodb://127.0.0.1:27017")
    client = MongoClient(uri, serverSelectionTimeoutMS=1500)
    try:
        client.admin.command("ping")
    except PyMongoError:
        client.close()
        pytest.skip("MongoDB no disponible")
    name = f"df_test_{uuid.uuid4().hex[:12]}"
    db = client[name]
    create_user(db, "admin_t", "admin", PW)
    create_user(db, "lector_t", "lector", PW)
    uploads = tmp_path / "uploads"
    env = {**os.environ, "APP_ENV": "development", "COOKIE_SECURE": "false", "MONGODB_DATABASE": name,
           "DF_UPLOADS_DIR": str(uploads)}
    port = _port()
    api = subprocess.Popen([sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port",
                            str(port), "--no-proxy-headers"], cwd=ROOT, env=env, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
    worker = subprocess.Popen([sys.executable, "-m", "pipeline.jobs.worker", "--db", name, "--uploads-dir", str(uploads),
                               "--poll-seconds", "0.5", "--worker-id", "chain-1"], cwd=ROOT, env=env,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            if httpx.get(url + "/api/v1/health", timeout=1).status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.2)
    else:
        api.kill()
        worker.kill()
        raise RuntimeError("uvicorn no arranco")
    yield url, db, tmp_path
    for p in (api, worker):
        p.kill()
    client.drop_database(name)
    client.close()


def _login(url: str, user: str) -> tuple[httpx.Client, str]:
    c = httpx.Client(base_url=url, timeout=60)
    r = c.post("/api/v1/auth/login", json={"username": user, "password": PW}, headers={"Origin": ORIGIN})
    assert r.status_code == 200, r.text
    return c, r.json()["csrf_token"]


def _upload(c: httpx.Client, csrf: str, path: Path, name: str | None = None):
    with open(path, "rb") as fh:
        return c.post("/api/v1/imports", files={"file": (name or path.name, fh, XLSX)},
                      headers={"X-CSRF-Token": csrf, "Origin": ORIGIN})


def _wait(c: httpx.Client, job_id: str, timeout: float = 90) -> dict:
    end = time.time() + timeout
    while time.time() < end:
        j = c.get(f"/api/v1/jobs/{job_id}").json()
        if j["status"] in ("completed", "failed"):
            return j
        time.sleep(0.5)
    raise AssertionError("el trabajo no termino")


def test_upload_import_duplicate_conflict_corrupt_august_and_reader_denied(stack):
    url, db, tmp = stack
    admin, csrf = _login(url, "admin_t")
    good = _june_file(tmp / "junio_a.xlsx")
    r = _upload(admin, csrf, good, "../../etc/passwd.xlsx")                       # nombre malicioso: solo etiqueta
    assert r.status_code == 202, r.text
    j1 = _wait(admin, r.json()["job_id"])
    assert j1["status"] == "completed" and j1["result"]["outcome"] == "importado", j1
    assert j1["result"]["ventas"] == 3 and j1["result"]["notas_credito"] == 1      # ventas y creditos separados
    assert db.sales.count_documents({}) == 3 and db.credit_notes.count_documents({}) == 1
    assert j1["links"]["import"].startswith("/imports/")
    # el mismo archivo: mismo trabajo, sin nuevas ventas
    r2 = _upload(admin, csrf, good, "otro-nombre.xlsx")
    assert r2.status_code == 202 and r2.json()["job_id"] == r["job_id"] if False else r2.json()["job_id"] == r.json()["job_id"]
    assert r2.json()["reused"] is True and db.sales.count_documents({}) == 3
    # otra fuente para un mes ya aprobado: cuarentena (no se importa ni se aprueba)
    other = _june_file(tmp / "junio_b.xlsx", sku=500, n=2)
    r3 = _upload(admin, csrf, other)
    assert r3.status_code == 202
    j3 = _wait(admin, r3.json()["job_id"])
    assert j3["status"] == "failed" and j3["error"]["code"] == "MES_CON_FUENTE_APROBADA" and not j3["error"]["retryable"]
    assert "REMEDIACION" in j3["error"]["message"].upper()
    assert db.sales.count_documents({}) == 3 and db.imports.count_documents({"estado": "completed", "noop": {"$ne": True}}) == 1
    # corrupto / agosto: rechazados en la peticion, sin encolar
    bad = tmp / "corrupto.xlsx"
    bad.write_bytes(good.read_bytes()[: len(good.read_bytes()) // 2])
    assert _upload(admin, csrf, bad).status_code in (415, 422)
    rows = [make_row(FECHA=datetime(2026, 8, 3))]
    aug = write_xlsx(tmp / "agosto_x.xlsx", rows)
    ra = _upload(admin, csrf, aug)
    assert ra.status_code == 422 and ra.json()["error"]["code"] == "AGOSTO_RESERVADO"
    assert db.jobs.count_documents({}) == 2
    # lector: sin escritura y sin ver trabajos
    reader, rcsrf = _login(url, "lector_t")
    assert _upload(reader, rcsrf, good).status_code == 403
    assert reader.get("/api/v1/jobs").status_code == 403
    # el cuerpo de un job nunca expone rutas ni el propietario
    text = admin.get(f"/api/v1/jobs/{j1['job_id']}").text
    assert str(tmp) not in text and "owner" not in text and "upload_path" not in text
