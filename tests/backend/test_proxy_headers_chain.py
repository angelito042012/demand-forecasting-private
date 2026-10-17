"""R06 (REVISION_CODEX_07): la cadena REAL (Uvicorn + middleware de proxy) y el limite de login.

Un TestClient directo de FastAPI omite el middleware de cabeceras de proxy de Uvicorn, asi que no
cubre este defecto: aqui se levanta un servidor Uvicorn real en un puerto efimero."""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

import httpx
import pytest
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from backend.app.auth.store import create_user

pytestmark = pytest.mark.mongo
ROOT = Path(__file__).resolve().parents[2]
ORIGIN = "http://localhost:4200"
PASSWORD = "clave-de-prueba-123"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def mongo_db():
    uri = os.environ.get("MONGODB_URI", "mongodb://127.0.0.1:27017")
    client = MongoClient(uri, serverSelectionTimeoutMS=1500)
    try:
        client.admin.command("ping")
    except PyMongoError:
        client.close()
        pytest.skip("MongoDB no disponible")
    name = f"df_test_{uuid.uuid4().hex[:12]}"
    db = client[name]
    create_user(db, "usuario_prueba", "lector", PASSWORD)
    yield name
    client.drop_database(name)
    client.close()


def _serve(db_name: str, *flags: str):
    port = _free_port()
    env = {**os.environ, "APP_ENV": "development", "COOKIE_SECURE": "false", "MONGODB_DATABASE": db_name}
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1",
                             "--port", str(port), *flags], cwd=ROOT, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            if httpx.get(url + "/api/v1/health", timeout=1).status_code == 200:
                return proc, url
        except httpx.HTTPError:
            time.sleep(0.2)
    proc.kill()
    raise RuntimeError("uvicorn no arranco")


def _fail_logins(url: str, n: int, xff: bool) -> list[int]:
    codes = []
    with httpx.Client(base_url=url, timeout=15) as c:
        for i in range(n):
            headers = {"Origin": ORIGIN, "Content-Type": "application/json"}
            if xff:
                headers["X-Forwarded-For"] = f"198.51.100.{10 + i}"   # una IP "distinta" en cada intento
            r = c.post("/api/v1/auth/login", json={"username": "usuario_prueba", "password": "incorrecta-xxx"},
                       headers=headers)
            codes.append(r.status_code)
    return codes


def test_no_proxy_headers_variando_xff_sigue_llegando_al_limite(mongo_db):
    proc, url = _serve(mongo_db, "--no-proxy-headers")
    try:
        codes = _fail_logins(url, 8, xff=True)
        assert codes[:5] == [401] * 5 and set(codes[5:]) == {429}, codes
        # la contrasena correcta tampoco entra mientras dure el bloqueo, aunque cambie XFF
        with httpx.Client(base_url=url, timeout=15) as c:
            r = c.post("/api/v1/auth/login", json={"username": "usuario_prueba", "password": PASSWORD},
                       headers={"Origin": ORIGIN, "X-Forwarded-For": "203.0.113.99"})
            assert r.status_code == 429 and "Retry-After" in r.headers
    finally:
        proc.kill()


def test_control_con_cabeceras_de_proxy_activas_el_limite_se_elude(mongo_db):
    """Documenta el defecto original: con proxy_headers activo (valor por defecto de Uvicorn) cada XFF
    distinto parece otro cliente y el limite nunca se alcanza. Es la razon de --no-proxy-headers."""
    proc, url = _serve(mongo_db, "--proxy-headers", "--forwarded-allow-ips", "127.0.0.1")
    try:
        codes = _fail_logins(url, 8, xff=True)
        assert 429 not in codes, codes
    finally:
        proc.kill()


def test_sin_xff_el_limite_funciona_igual_y_csrf_y_roles_no_cambian(mongo_db):
    proc, url = _serve(mongo_db, "--no-proxy-headers")
    try:
        assert _fail_logins(url, 6, xff=False)[-1] == 429
        with httpx.Client(base_url=url, timeout=15) as c:
            assert c.post("/api/v1/auth/logout", json={}, headers={"Origin": ORIGIN}).status_code == 401
            assert c.get("/api/v1/admin/users").status_code == 401
    finally:
        proc.kill()


def test_scripts_de_inicio_desactivan_proxy_headers():
    text = (ROOT / "scripts" / "start-local.ps1").read_text(encoding="utf-8")
    assert "--no-proxy-headers" in text and "uvicorn" in text
