"""Pruebas de sesion, CSRF, permisos y rate limit contra una base Mongo temporal aislada."""
# ruff: noqa: F401, F811  (fixtures importadas de test_auth_common)
from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend.app.config import Settings
from tests.backend.test_auth_common import (
    JSON,
    ORIGIN,
    PASSWORD,
    app,
    build_app,
    client,
    db,
    login,
    mut_headers,
    settings,
    users,
)

pytestmark = pytest.mark.mongo
ME = "/api/v1/auth/me"


def code(resp):
    return resp.json()["error"]["code"]


def test_login_ok_me_and_cookie_attributes(client):
    r = login(client)
    assert r.status_code == 200
    body = r.json()
    assert body["username"] == "ana" and body["role"] == "admin"
    assert len(body["csrf_token"]) == 64 and body["expires_at"].endswith("Z")
    sc = r.headers["set-cookie"].lower()
    assert sc.startswith("df_session=") and "httponly" in sc and "samesite=strict" in sc and "path=/" in sc
    assert "secure" not in sc.replace("samesite", "")  # development + cookie_secure=False
    me = client.get(ME)
    assert me.status_code == 200
    assert me.json()["csrf_token"] == body["csrf_token"]
    assert set(me.json()) == {"username", "role", "csrf_token", "expires_at", "idle_expires_at"}


def test_cookie_is_secure_by_default(db, users):
    s = Settings(_env_file=None, allowed_origins=ORIGIN)  # cookie_secure=True por defecto
    assert s.cookie_secure is True
    with TestClient(build_app(db, s)) as c:
        r = login(c)
    assert r.status_code == 200
    assert "; secure" in r.headers["set-cookie"].lower()


def test_secure_forced_outside_development(db, users):
    s = Settings(_env_file=None, allowed_origins=ORIGIN, cookie_secure=False, app_env="production")
    with TestClient(build_app(db, s)) as c:
        r = login(c)
    assert "; secure" in r.headers["set-cookie"].lower()


def test_wrong_password_nonexistent_and_inactive_are_identical(client):
    responses = [login(client, "ana", "incorrecta-123456"), login(client, "fantasma", "incorrecta-123456"),
                 login(client, "inactivo", PASSWORD)]
    for r in responses:
        assert r.status_code == 401
        assert "set-cookie" not in r.headers
    assert responses[0].json() == responses[1].json() == responses[2].json()
    assert code(responses[0]) == "NO_AUTENTICADO"


def test_no_cookie_and_invented_token_are_no_autenticado(client):
    assert code(client.get(ME)) == "NO_AUTENTICADO"
    client.cookies.set("df_session", "token-inventado-que-no-existe")
    r = client.get(ME)
    assert r.status_code == 401 and code(r) == "NO_AUTENTICADO"


def test_absolute_expiry(client, db):
    login(client)
    db["sessions"].update_many({}, {"$set": {"expires_at": datetime.now(UTC) - timedelta(seconds=1)}})
    r = client.get(ME)
    assert r.status_code == 401 and code(r) == "SESION_EXPIRADA"


def test_idle_expiry_and_sliding(client, db):
    login(client)
    before = db["sessions"].find_one()["idle_expires_at"]
    assert client.get(ME).status_code == 200
    assert db["sessions"].find_one()["idle_expires_at"] >= before
    db["sessions"].update_many({}, {"$set": {"idle_expires_at": datetime.now(UTC) - timedelta(seconds=1)}})
    r = client.get(ME)
    assert r.status_code == 401 and code(r) == "SESION_EXPIRADA"


def test_idle_never_exceeds_absolute(client, db):
    login(client)
    soon = datetime.now(UTC) + timedelta(seconds=30)
    db["sessions"].update_many({}, {"$set": {"expires_at": soon}})
    assert client.get(ME).status_code == 200
    assert db["sessions"].find_one()["idle_expires_at"].replace(tzinfo=UTC) <= soon.replace(microsecond=(
        soon.microsecond // 1000) * 1000)


def test_logout_revokes_and_clears_cookie(client, db):
    csrf = login(client).json()["csrf_token"]
    token = client.cookies.get("df_session")
    r = client.post("/api/v1/auth/logout", headers=mut_headers(csrf))
    assert r.status_code == 204
    assert "df_session=" in r.headers["set-cookie"] and "max-age=0" in r.headers["set-cookie"].lower()
    assert db["sessions"].find_one()["revoked_at"] is not None
    client.cookies.set("df_session", token)  # un atacante reutiliza el token anterior
    r = client.get(ME)
    assert r.status_code == 401 and code(r) == "NO_AUTENTICADO"


def test_logout_requires_csrf_origin_and_json(client):
    csrf = login(client).json()["csrf_token"]
    url = "/api/v1/auth/logout"
    r = client.post(url, headers={**JSON, "Origin": ORIGIN})
    assert r.status_code == 403 and code(r) == "CSRF_INVALIDO"
    r = client.post(url, headers=mut_headers("0" * 64))
    assert r.status_code == 403 and code(r) == "CSRF_INVALIDO"
    r = client.post(url, headers=mut_headers(csrf, origin="http://evil.example"))
    assert r.status_code == 403 and code(r) == "ORIGEN_NO_PERMITIDO"
    r = client.post(url, headers={"Origin": ORIGIN, "X-CSRF-Token": csrf, "Content-Type": "text/plain"}, content="x")
    assert r.status_code == 422 and code(r) == "ENTRADA_INVALIDA"
    assert client.get(ME).status_code == 200  # nada de lo anterior revoco la sesion


def test_missing_origin_and_referer_fallback(client):
    csrf = login(client).json()["csrf_token"]
    url = "/api/v1/_t/mutate"
    r = client.post(url, headers={**JSON, "X-CSRF-Token": csrf})
    assert code(r) == "ORIGEN_NO_PERMITIDO"
    ok = client.post(url, headers={**JSON, "X-CSRF-Token": csrf, "Referer": ORIGIN + "/pantalla"})
    assert ok.status_code == 200
    bad = client.post(url, headers={**JSON, "X-CSRF-Token": csrf, "Referer": "http://evil.example/x"})
    assert code(bad) == "ORIGEN_NO_PERMITIDO"


def test_login_origin_and_content_type(client):
    assert code(login(client, origin=None)) == "ORIGEN_NO_PERMITIDO"
    r = login(client, origin="http://evil.example")
    assert r.status_code == 403 and code(r) == "ORIGEN_NO_PERMITIDO"
    r = client.post("/api/v1/auth/login", content="username=ana&password=x",
                    headers={"Origin": ORIGIN, "Content-Type": "application/x-www-form-urlencoded"})
    assert r.status_code == 422 and code(r) == "ENTRADA_INVALIDA"


def test_admin_users_roles(client):
    login(client, "luis")
    r = client.get("/api/v1/admin/users")
    assert r.status_code == 403 and code(r) == "PROHIBIDO"


def test_admin_list_and_create_users(client, db):
    csrf = login(client, "ana").json()["csrf_token"]
    r = client.get("/api/v1/admin/users?page_size=2")
    assert r.status_code == 200
    j = r.json()
    assert j["total"] == 3 and len(j["items"]) == 2 and j["has_more"] is True and j["page"] == 1
    assert all(set(i) == {"username", "role", "active", "created_at"} for i in j["items"])
    assert "password" not in r.text and "scrypt" not in r.text
    url = "/api/v1/admin/users"
    new = {"username": "Nuevo.User", "role": "lector", "password": "otra-clave-larga-1"}
    assert client.post(url, json=new, headers={**JSON, "Origin": ORIGIN}).status_code == 403  # sin CSRF
    r = client.post(url, json=new, headers=mut_headers(csrf))
    assert r.status_code == 201 and r.json() == {"username": "nuevo.user", "role": "lector"}
    stored = db["users"].find_one({"username": "nuevo.user"})
    assert stored["password_hash"].startswith("scrypt$32768$8$1$") and stored["active"] is True
    assert client.post(url, json=new, headers=mut_headers(csrf)).status_code == 422  # duplicado
    short = {**new, "username": "otro", "password": "corta"}
    assert client.post(url, json=short, headers=mut_headers(csrf)).status_code == 422
    badrole = {**new, "username": "otro", "role": "superuser"}
    assert client.post(url, json=badrole, headers=mut_headers(csrf)).status_code == 422
    assert client.get(url + "?page_size=500").status_code == 422
    # el nuevo usuario puede iniciar sesion
    with TestClient(client.app) as c2:
        assert login(c2, "nuevo.user", "otra-clave-larga-1").status_code == 200


def test_lector_cannot_create_users_even_with_csrf(client, db):
    csrf = login(client, "luis").json()["csrf_token"]
    r = client.post("/api/v1/admin/users", json={"username": "x" * 5, "role": "admin", "password": "una-clave-larga-1"},
                    headers=mut_headers(csrf))
    assert r.status_code == 403 and code(r) == "PROHIBIDO"
    assert db["users"].count_documents({"username": "xxxxx"}) == 0


def test_rate_limit_user_ip_and_retry_after(client, db):
    for _ in range(5):
        assert login(client, "ana", "incorrecta-123456").status_code == 401
    r = login(client, "ana", "incorrecta-123456")
    assert r.status_code == 429 and code(r) == "DEMASIADOS_INTENTOS"
    assert 1 <= int(r.headers["retry-after"]) <= 15 * 60
    assert login(client, "ana", PASSWORD).status_code == 429  # ni con clave correcta mientras dure
    assert login(client, "luis", PASSWORD).status_code == 200  # otro usuario, misma IP, bajo el limite por IP
    # las claves no guardan usuario ni IP en claro
    dump = str(list(db["login_attempts"].find()))
    assert "ana" not in dump.replace("scope", "") and "testclient" not in dump


def test_rate_limit_per_ip(client, db):
    for i in range(20):
        assert login(client, f"fantasma{i}", "incorrecta-123456").status_code == 401
    assert login(client, "luis", PASSWORD).status_code == 429


def test_successful_login_resets_user_ip_counter(client, db):
    for _ in range(4):
        login(client, "ana", "incorrecta-123456")
    assert login(client, "ana", PASSWORD).status_code == 200
    for _ in range(4):
        assert login(client, "ana", "incorrecta-123456").status_code == 401


def test_session_rotation_on_login(client, db):
    first = login(client)
    t1 = client.cookies.get("df_session")
    second = login(client)  # presenta la cookie anterior
    t2 = client.cookies.get("df_session")
    assert t1 != t2 and first.json()["csrf_token"] != second.json()["csrf_token"]
    docs = list(db["sessions"].find().sort("created_at", 1))
    assert len(docs) == 2 and docs[0]["revoked_at"] is not None and docs[1]["revoked_at"] is None
    client.cookies.set("df_session", t1)
    assert code(client.get(ME)) == "NO_AUTENTICADO"
    client.cookies.set("df_session", t2)
    assert client.get(ME).status_code == 200


def test_database_never_stores_plain_token_or_csrf(client, db):
    r = login(client)
    token, csrf = client.cookies.get("df_session"), r.json()["csrf_token"]
    doc = db["sessions"].find_one()
    assert doc["token_hash"] == hashlib.sha256(token.encode()).hexdigest()
    assert doc["csrf_hash"] == hashlib.sha256(csrf.encode()).hexdigest()
    dump = str(list(db["sessions"].find()) + list(db["login_attempts"].find()) + list(db["users"].find()))
    assert token not in dump and csrf not in dump and PASSWORD not in dump
    assert len(token) >= 43  # 256 bits en base64 url-safe


def test_indexes_created_idempotently(client, db):
    login(client)
    login(client)
    idx = db["sessions"].index_information()
    assert any(v.get("unique") and v["key"] == [("token_hash", 1)] for v in idx.values())
    assert any(v.get("expireAfterSeconds") == 0 and v["key"] == [("expires_at", 1)] for v in idx.values())
    assert any(v.get("unique") for v in db["users"].index_information().values())
    assert any(v.get("expireAfterSeconds") == 900 for v in db["login_attempts"].index_information().values())


def test_no_default_credentials(db, settings):
    with TestClient(build_app(db, settings)) as c:
        for u in ("admin", "lector", "test", "root"):
            for p in ("admin", "password", "admin1234567", "changeme1234"):
                assert login(c, u, p).status_code == 401
    assert db["users"].count_documents({}) == 0


def test_require_user_and_admin_as_dependencies(client):
    assert code(client.get("/api/v1/_t/user")) == "NO_AUTENTICADO"
    login(client, "luis")
    assert client.get("/api/v1/_t/user").json() == {"username": "luis", "role": "lector"}
    assert code(client.get("/api/v1/_t/admin")) == "PROHIBIDO"
    with TestClient(client.app) as c2:
        login(c2, "ana")
        assert c2.get("/api/v1/_t/admin").status_code == 200


def test_require_csrf_dependency_on_other_routes(client):
    csrf = login(client).json()["csrf_token"]
    assert client.post("/api/v1/_t/mutate", headers=mut_headers(csrf)).json() == {"ok": True}
    assert code(client.post("/api/v1/_t/mutate", headers=mut_headers("x"))) == "CSRF_INVALIDO"


def test_deactivated_user_loses_session(client, db):
    login(client, "luis")
    db["users"].update_one({"username": "luis"}, {"$set": {"active": False}})
    assert code(client.get(ME)) == "NO_AUTENTICADO"


def test_error_bodies_leak_nothing(client):
    r = login(client, "ana", "incorrecta-123456")
    assert set(r.json()["error"]) == {"code", "message"}
    assert "scrypt" not in r.text and "Traceback" not in r.text
