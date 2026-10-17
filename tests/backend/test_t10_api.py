"""T10: POST /imports, POST /runs, GET /runs/options, GET /jobs. Bases temporales df_test_<uuid>; sin ejecutar
ningun trabajo (los jobs quedan `queued`). Datos sinteticos minimos creados con openpyxl."""
from __future__ import annotations

import hashlib
import io
import zipfile
from dataclasses import replace
from datetime import date, datetime

import openpyxl
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app import uploads
from backend.app.config import get_settings
from backend.app.db import get_db
from backend.app.errors import install_error_handlers
from backend.app.routers import admin, auth, imports, jobs, runs
from pipeline.data.importer import REQUIRED_HEADERS
from tests.backend import test_auth_common as common
from tests.backend.test_auth_common import ORIGIN, login

pytestmark = pytest.mark.mongo

db, settings, users = common.db, common.settings, common.users      # fixtures reutilizadas (base df_test_<uuid>)


# ---------------------------------------------------------------- utilidades
def make_xlsx(rows_date=date(2026, 6, 10), headers=None, n=3) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Hoja1"
    ws.append(list(headers if headers is not None else REQUIRED_HEADERS))
    for i in range(n):
        rec = {h: "x" for h in REQUIRED_HEADERS}
        rec.update({"ID_PEDIDO": i + 1, "TIPO_DOC": 1, "FECHA": datetime(rows_date.year, rows_date.month, rows_date.day),
                    "CANTIDAD": 1, "TOTAL_LINEA": 10.0})
        ws.append([rec.get(h) for h in (headers if headers is not None else REQUIRED_HEADERS)])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def with_extra_entries(data: bytes, extra: dict[str, bytes]) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(data)) as zin, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            zout.writestr(item, zin.read(item.filename))
        for name, content in extra.items():
            zout.writestr(name, content)
    return out.getvalue()


@pytest.fixture
def policy(tmp_path):
    return replace(uploads.get_upload_policy(), directory=tmp_path / "uploads")


@pytest.fixture
def app(db, settings, users, policy):
    application = FastAPI()
    install_error_handlers(application)
    for module in (auth, admin, imports, runs, jobs):
        application.include_router(module.router, prefix="/api/v1")
    application.dependency_overrides[get_db] = lambda: db
    application.dependency_overrides[get_settings] = lambda: settings
    application.dependency_overrides[uploads.get_upload_policy] = lambda: policy
    return application


class Session:
    def __init__(self, app, username):
        self.http = TestClient(app, base_url="http://testserver")
        r = login(self.http, username)
        assert r.status_code == 200
        self.csrf = r.json()["csrf_token"]

    def h(self, origin=ORIGIN, csrf=True, json=True):
        out = {"Origin": origin}
        if csrf:
            out["X-CSRF-Token"] = self.csrf
        if json:
            out["Content-Type"] = "application/json"
        return out

    def upload(self, data, name="junio.xlsx", **kw):
        return self.http.post("/api/v1/imports", files={"file": (name, data, "application/octet-stream")},
                              headers=self.h(json=False, **kw))

    def run(self, body, **kw):
        return self.http.post("/api/v1/runs", json=body, headers=self.h(**kw))


@pytest.fixture
def admin_s(app):
    s = Session(app, "ana")
    yield s
    s.http.close()


@pytest.fixture
def reader_s(app):
    s = Session(app, "luis")
    yield s
    s.http.close()


@pytest.fixture
def anon(app):
    with TestClient(app, base_url="http://testserver") as c:
        yield c


def code(r):
    return r.json()["error"]["code"]


# ---------------------------------------------------------------- permisos y CSRF
def test_upload_permissions_and_csrf(admin_s, reader_s, anon, db):
    data = make_xlsx()
    files = {"file": ("a.xlsx", data, "application/octet-stream")}
    assert anon.post("/api/v1/imports", files=files, headers={"Origin": ORIGIN}).status_code == 401
    r = reader_s.upload(data)
    assert r.status_code == 403 and code(r) == "PROHIBIDO"
    r = admin_s.upload(data, csrf=False)
    assert r.status_code == 403 and code(r) == "CSRF_INVALIDO"
    r = admin_s.upload(data, origin="http://evil.example")
    assert r.status_code == 403 and code(r) == "ORIGEN_NO_PERMITIDO"
    assert db.jobs.count_documents({}) == 0


def test_upload_requires_multipart_content_type(admin_s):
    r = admin_s.http.post("/api/v1/imports", json={"file": "x"}, headers=admin_s.h())
    assert r.status_code == 415


def test_runs_permissions_and_csrf(admin_s, reader_s, anon, db):
    body = {"origin": "2026-07-10"}
    assert anon.post("/api/v1/runs", json=body, headers={"Origin": ORIGIN}).status_code == 401
    assert reader_s.run(body).status_code == 403
    r = admin_s.run(body, csrf=False)
    assert r.status_code == 403 and code(r) == "CSRF_INVALIDO"
    assert admin_s.run(body, origin="http://evil.example").status_code == 403
    assert db.jobs.count_documents({}) == 0


def test_jobs_admin_only(admin_s, reader_s, anon):
    assert anon.get("/api/v1/jobs").status_code == 401
    assert reader_s.http.get("/api/v1/jobs").status_code == 403
    assert reader_s.http.get("/api/v1/jobs/" + "a" * 32).status_code == 403
    assert admin_s.http.get("/api/v1/jobs").status_code == 200


# ---------------------------------------------------------------- subida valida y duplicado
def test_valid_upload_queues_without_executing(admin_s, db, policy):
    data = make_xlsx()
    sha = hashlib.sha256(data).hexdigest()
    r = admin_s.upload(data, name="Ventas Junio.xlsx")
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["status"] == "queued" and body["reused"] is False
    assert body["upload"] == {"sha256_short": sha[:12], "size_bytes": len(data), "month": "2026-06",
                              "label": "Ventas Junio"}
    assert (policy.directory / f"{sha}.xlsx").read_bytes() == data
    assert [p.name for p in policy.directory.iterdir()] == [f"{sha}.xlsx"]        # sin temporales
    job = db.jobs.find_one({"job_id": body["job_id"]})
    assert job["status"] == "queued" and job["attempts"] == 0 and job["type"] == "import_excel"
    assert job["idempotency_key"] == f"import:{sha}"
    assert job["input"] == {"upload_sha256": sha, "upload_path": f"{sha}.xlsx", "size_bytes": len(data),
                            "month": "2026-06", "label": "Ventas Junio"}
    assert not list(db.imports.find()) and db.sales.count_documents({}) == 0      # no se importo nada


def test_duplicate_upload_same_job(admin_s, db):
    data = make_xlsx()
    a = admin_s.upload(data, name="uno.xlsx").json()
    b = admin_s.upload(data, name="otro nombre.xlsx").json()
    assert b["job_id"] == a["job_id"] and b["reused"] is True
    assert db.jobs.count_documents({}) == 1
    c = admin_s.upload(make_xlsx(n=4)).json()
    assert c["job_id"] != a["job_id"] and db.jobs.count_documents({}) == 2


# ---------------------------------------------------------------- rechazos de subida
def test_truncated_zip(admin_s, db, policy):
    data = make_xlsx()
    r = admin_s.upload(data[: len(data) // 2])
    assert r.status_code == 422 and code(r) == "ARCHIVO_CORRUPTO"
    assert db.jobs.count_documents({}) == 0 and list(policy.directory.iterdir()) == []


def test_not_a_zip_renamed(admin_s, db):
    r = admin_s.upload(b"esto no es un libro de excel" * 20, name="falso.xlsx")
    assert r.status_code == 415 and code(r) == "FORMATO_NO_SOPORTADO"
    assert db.jobs.count_documents({}) == 0


def test_wrong_extension(admin_s):
    r = admin_s.upload(make_xlsx(), name="datos.xls")
    assert r.status_code == 415
    r = admin_s.upload(make_xlsx(), name="datos.xlsm")
    assert r.status_code == 415


def test_zip_without_workbook(admin_s):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("hola.txt", "hola")
    r = admin_s.upload(buf.getvalue())
    assert r.status_code == 422 and code(r) == "NO_ES_XLSX"


def test_zip_bomb_declared_sizes(admin_s, db):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("xl/workbook.xml", "<workbook/>")
        z.writestr("xl/worksheets/sheet1.xml", b"0" * 1000)
        z.filelist[-1].file_size = 10 ** 11          # tamano declarado enorme (central directory)
    r = admin_s.upload(buf.getvalue())
    assert r.status_code == 422 and code(r) == "ZIP_INSEGURO"
    assert db.jobs.count_documents({}) == 0


def test_zip_bomb_compression_ratio(admin_s):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("xl/workbook.xml", "<workbook/>")
        z.writestr("xl/worksheets/sheet1.xml", b"\0" * (4 << 20))     # 4 MiB de ceros ~ 4 KiB comprimidos
    r = admin_s.upload(buf.getvalue())
    assert r.status_code == 422 and code(r) == "ZIP_INSEGURO"


def test_zip_too_many_entries(admin_s):
    data = with_extra_entries(make_xlsx(), {f"relleno/{i}.txt": b"x" for i in range(201)})
    r = admin_s.upload(data)
    assert r.status_code == 422 and code(r) == "ZIP_INSEGURO"


def test_expanded_limit_from_policy(admin_s, app, policy):
    app.dependency_overrides[uploads.get_upload_policy] = lambda: replace(policy, max_expanded=500)
    r = admin_s.upload(make_xlsx())
    assert r.status_code == 422 and code(r) == "ZIP_INSEGURO"


def test_macros_rejected(admin_s, db):
    r = admin_s.upload(with_extra_entries(make_xlsx(), {"xl/vbaProject.bin": b"\xd0\xcf\x11\xe0"}))
    assert r.status_code == 422 and code(r) == "MACROS_NO_PERMITIDAS"
    assert db.jobs.count_documents({}) == 0


def test_external_links_rejected(admin_s):
    r = admin_s.upload(with_extra_entries(make_xlsx(), {"xl/externalLinks/externalLink1.xml": b"<x/>"}))
    assert r.status_code == 422 and code(r) == "ENLACES_EXTERNOS"
    rels = (b'<Relationships><Relationship Id="r1" Target="http://x.example/a" TargetMode="External"/>'
            b"</Relationships>")
    r = admin_s.upload(with_extra_entries(make_xlsx(), {"xl/worksheets/_rels/sheet1.xml.rels": rels}))
    assert r.status_code == 422 and code(r) == "ENLACES_EXTERNOS"


def test_wrong_headers(admin_s, db):
    r = admin_s.upload(make_xlsx(headers=[h for h in REQUIRED_HEADERS if h != "CANTIDAD"]))
    assert r.status_code == 422 and code(r) == "ENCABEZADOS_INVALIDOS" and "CANTIDAD" in r.json()["error"]["message"]
    r = admin_s.upload(make_xlsx(headers=["A", "B", "C"]))
    assert r.status_code == 422 and code(r) == "ENCABEZADOS_INVALIDOS"
    assert db.jobs.count_documents({}) == 0


def test_august_and_out_of_range_months(admin_s, db):
    r = admin_s.upload(make_xlsx(date(2026, 8, 5)))
    assert r.status_code == 422 and code(r) == "AGOSTO_RESERVADO"
    r = admin_s.upload(make_xlsx(date(2026, 2, 5)))
    assert r.status_code == 422 and code(r) == "MES_FUERA_DE_ALCANCE"
    r = admin_s.upload(make_xlsx(date(2025, 6, 5)))
    assert r.status_code == 422 and code(r) == "MES_FUERA_DE_ALCANCE"
    assert db.jobs.count_documents({}) == 0


def test_oversize_streamed_413(admin_s, app, policy, db):
    app.dependency_overrides[uploads.get_upload_policy] = lambda: replace(policy, max_bytes=3000)
    data = make_xlsx(n=400)
    assert len(data) > 3000
    r = admin_s.upload(data)
    assert r.status_code == 413 and code(r) == "ARCHIVO_DEMASIADO_GRANDE"
    assert db.jobs.count_documents({}) == 0
    assert not policy.directory.exists() or list(policy.directory.iterdir()) == []


def test_oversize_by_content_length_before_reading(admin_s, app, policy):
    app.dependency_overrides[uploads.get_upload_policy] = lambda: replace(policy, max_bytes=1000)
    r = admin_s.upload(b"PK\x03\x04" + b"0" * (3 << 20))
    assert r.status_code == 413


@pytest.mark.parametrize("name", ["../../x.xlsx", 'a"b\'c;rm -rf.xlsx', "..\\..\\Windows\\sys.xlsx",
                                  "/etc/passwd.xlsx", "x" * 300 + ".xlsx", "\u202e\x00evil.xlsx"])
def test_malicious_client_name_never_touches_path(admin_s, db, policy, tmp_path, name):
    data = make_xlsx()
    sha = hashlib.sha256(data).hexdigest()
    r = admin_s.upload(data, name=name)
    assert r.status_code == 202, r.text
    label = r.json()["upload"]["label"]
    assert 1 <= len(label) <= 80 and all(c.isalnum() or c in "._ -" for c in label)
    assert [p.name for p in policy.directory.iterdir()] == [f"{sha}.xlsx"]
    assert not (tmp_path / "x.xlsx").exists()
    text = str(r.json())
    assert str(policy.directory) not in text and "upload_path" not in text


def test_sanitize_label_cases():
    assert uploads.sanitize_label("../../x.xlsx") == "x"
    assert uploads.sanitize_label('a"b.xlsx') == "a_b"
    assert uploads.sanitize_label(None) == "archivo"
    assert uploads.sanitize_label("....xlsx") == "archivo"
    assert len(uploads.sanitize_label("y" * 500)) == 80


# ---------------------------------------------------------------- runs
def test_run_options(admin_s, reader_s, anon):
    assert anon.get("/api/v1/runs/options").status_code == 401
    for s in (admin_s, reader_s):
        r = s.http.get("/api/v1/runs/options")
        assert r.status_code == 200
        assert r.json() == {"origin_min": "2026-06-01", "origin_max": "2026-07-10", "origin_default": "2026-07-10",
                            "horizon_max": 21, "methods": ["promedio_28"], "development_policy": True}


def test_run_valid_queues_only(admin_s, db):
    r = admin_s.run({"origin": "2026-07-10"})
    assert r.status_code == 202, r.text
    b = r.json()
    assert b["status"] == "queued" and b["origin"] == "2026-07-10" and b["horizon_days"] == 21
    assert b["method"] == "promedio_28"
    job = db.jobs.find_one({"job_id": b["job_id"]})
    assert job["type"] == "generate_run" and job["status"] == "queued" and job["attempts"] == 0
    assert job["input"] == {"origin": "2026-07-10", "horizon_days": 21, "method": "promedio_28"}
    assert job["idempotency_key"].startswith("gen:2026-07-10:21:promedio_28:gen-promedio28-1:")
    assert db.runs.count_documents({}) == 0


@pytest.mark.parametrize("body", [{"origin": "2026-05-31"}, {"origin": "2026-07-11"}, {"origin": "2026-08-01"},
                                  {"origin": "2026-07-10", "horizon_days": 22},
                                  {"origin": "2026-07-10", "horizon_days": 0}])
def test_run_out_of_range(admin_s, db, body):
    r = admin_s.run(body)
    assert r.status_code == 422 and code(r) == "CORTE_FUERA_DE_RANGO"
    assert db.jobs.count_documents({}) == 0


@pytest.mark.parametrize("body", [{"origin": "2026-07-10", "extra": 1}, {"origin": "2026-07-10", "method": "rf"},
                                  {"origin": "no-fecha"}, {}, {"origin": "2026-07-10", "horizon_days": "x"},
                                  {"origin": "2026-07-10", "path": "/etc/passwd"}])
def test_run_invalid_body(admin_s, db, body):
    r = admin_s.run(body)
    assert r.status_code == 422 and code(r) == "ENTRADA_INVALIDA"
    assert db.jobs.count_documents({}) == 0


def test_run_idempotency_and_source_digest(admin_s, db):
    a = admin_s.run({"origin": "2026-07-10"}).json()
    b = admin_s.run({"origin": "2026-07-10", "horizon_days": 21}).json()
    assert a["job_id"] == b["job_id"] and b["reused"] is True and db.jobs.count_documents({}) == 1
    c = admin_s.run({"origin": "2026-07-09"}).json()
    d = admin_s.run({"origin": "2026-07-10", "horizon_days": 14}).json()
    assert len({a["job_id"], c["job_id"], d["job_id"]}) == 3
    # Idempotency-Key saneada distingue entradas por lo demas iguales
    h = {**admin_s.h(), "Idempotency-Key": "reintento ../1;"}
    e = admin_s.http.post("/api/v1/runs", json={"origin": "2026-07-10"}, headers=h).json()
    assert e["job_id"] != a["job_id"]
    assert db.jobs.find_one({"job_id": e["job_id"]})["idempotency_key"].endswith(":k=reintento..1")
    # una fuente aprobada nueva (mes <= origen) cambia el digest => otro trabajo
    db.imports.insert_one({"import_id": "1" * 32, "sha256": "f" * 64, "mes": "2026-06", "estado": "completed",
                           "noop": False, "iniciado_utc": datetime(2026, 7, 1)})
    f = admin_s.run({"origin": "2026-07-10"}).json()
    assert f["job_id"] != a["job_id"]
    # una fuente de un mes posterior al origen no cambia la clave
    db.imports.insert_one({"import_id": "2" * 32, "sha256": "e" * 64, "mes": "2026-07", "estado": "completed",
                           "noop": False, "iniciado_utc": datetime(2026, 8, 1)})
    g = admin_s.run({"origin": "2026-06-20"}).json()
    db.imports.delete_one({"sha256": "e" * 64})
    g2 = admin_s.run({"origin": "2026-06-20"}).json()
    assert g["job_id"] == g2["job_id"]


# ---------------------------------------------------------------- jobs
def test_jobs_listing_without_leaks(admin_s, db, policy):
    data = make_xlsx()
    sha = hashlib.sha256(data).hexdigest()
    imp = admin_s.upload(data, name="ventas.xlsx").json()
    run = admin_s.run({"origin": "2026-07-10"}).json()
    r = admin_s.http.get("/api/v1/jobs")
    assert r.status_code == 200
    page = r.json()
    assert page["total"] == 2 and page["page"] == 1 and page["has_more"] is False
    assert {i["job_id"] for i in page["items"]} == {imp["job_id"], run["job_id"]}
    text = r.text
    for secret in (sha, str(policy.directory), "upload_path", "upload_sha256", '"input"', '"owner"',
                   "idempotency_key", "lease", "worker_id", "generation"):
        assert secret not in text, secret
    item = next(i for i in page["items"] if i["job_id"] == imp["job_id"])
    assert item["public"] == {"label": "ventas", "size_bytes": len(data), "sha256_short": sha[:12], "month": "2026-06"}
    assert item["created_at"].endswith("Z") and item["links"] == {}
    one = admin_s.http.get(f"/api/v1/jobs/{imp['job_id']}")
    assert one.status_code == 200 and one.json()["job_id"] == imp["job_id"]
    assert sha not in one.text and "owner" not in one.text


def test_jobs_filters_pagination_and_links(admin_s, db):
    a = admin_s.upload(make_xlsx()).json()["job_id"]
    admin_s.upload(make_xlsx(n=5))
    admin_s.run({"origin": "2026-07-10"})
    db.jobs.update_one({"job_id": a}, {"$set": {"status": "completed", "owner": "secreto", "result": {
        "outcome": "importado", "import_id": "3" * 32}}})
    g = admin_s.http.get
    assert g("/api/v1/jobs?type=generate_run").json()["total"] == 1
    assert g("/api/v1/jobs?status=completed").json()["total"] == 1
    assert g("/api/v1/jobs?status=queued&type=import_excel").json()["total"] == 1
    p = g("/api/v1/jobs?page_size=2&page=1").json()
    assert len(p["items"]) == 2 and p["has_more"] is True and p["total"] == 3
    assert len(g("/api/v1/jobs?page_size=2&page=2").json()["items"]) == 1
    done = g(f"/api/v1/jobs/{a}")
    assert done.json()["links"] == {"import": "/imports/" + "3" * 32}
    assert "secreto" not in done.text
    db.jobs.update_one({"job_id": a}, {"$set": {"result": {"run_id": "gen-20260710-abcdef012345"}}})
    assert g(f"/api/v1/jobs/{a}").json()["links"] == {"run": "/runs/gen-20260710-abcdef012345"}
    for bad in ("status=otro", "type=otro", "sort=x", "status=queued&status=failed", "page=0"):
        assert g("/api/v1/jobs?" + bad).status_code == 422, bad
    assert g("/api/v1/jobs/" + "0" * 32).status_code == 404
    assert g("/api/v1/jobs/no-es-hex").status_code == 422


def test_existing_read_routes_still_routed(reader_s):
    assert reader_s.http.get("/api/v1/runs/options").status_code == 200       # no capturada por /runs/{run_id}
    assert reader_s.http.get("/api/v1/runs?status=bad").status_code == 422
