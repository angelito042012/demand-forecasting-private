"""T11A: modo produccion (docs/T11_CONTRATO.md §5, docs/T11_PLAN_DESPLIEGUE.md). Mongo temporal df_test_<uuid>;
sin Docker, sin red externa, sin datos reales."""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from backend.app import config as cfg_module
from backend.app.auth.store import create_user
from backend.app.config import ConfigurationError, Settings, get_settings
from backend.app.db import get_db
from backend.app.hardening import TrustedProxyMiddleware

ORIGIN = "https://df.example.test"
PASSWORD = "clave-de-prueba-123"  # solo bases temporales de prueba
SECRET = "s" * 40
PROXY = "10.20.0.2"


def prod_settings(**over) -> Settings:
    values = {"app_env": "production", "mongodb_uri": "mongodb://127.0.0.1:27017", "mongodb_database": "df_test_prod",
              "auth_secret": SECRET, "allowed_origins": ORIGIN, "df_uploads_dir": "/tmp/df_uploads", "_env_file": None}
    values.update(over)
    return Settings(**values).validate_production()


@pytest.fixture
def dist(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html><body>SPA-INDEX</body></html>", encoding="utf-8")
    (tmp_path / "main-ABC123.js").write_text("console.log(1)", encoding="utf-8")
    (tmp_path.parent / "secreto.txt").write_text("fuera", encoding="utf-8")
    return tmp_path


@pytest.fixture
def mongo_db():
    client = MongoClient("mongodb://127.0.0.1:27017", serverSelectionTimeoutMS=1500)
    try:
        client.admin.command("ping")
    except PyMongoError:
        client.close()
        pytest.skip("MongoDB local no disponible")
    database = client[f"df_test_{uuid.uuid4().hex}"]
    create_user(database, "usuario_prueba", "lector", PASSWORD)
    yield database
    client.drop_database(database.name)
    client.close()


def make_client(monkeypatch, settings: Settings, db=None, peer=("203.0.113.5", 50000), **kw) -> TestClient:
    from backend.app import main
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    app = main.create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    if db is not None:
        app.dependency_overrides[get_db] = lambda: db
    return TestClient(app, client=peer, base_url="https://df.example.test", raise_server_exceptions=False, **kw)


# ---------------------------------------------------------------- configuracion

@pytest.mark.parametrize("missing", ["mongodb_uri", "mongodb_database", "auth_secret", "allowed_origins", "df_uploads_dir"])
def test_production_exige_variables_explicitas(missing):
    values = {"app_env": "production", "mongodb_uri": "mongodb://h:27017", "mongodb_database": "df_pub",
              "auth_secret": SECRET, "allowed_origins": ORIGIN, "df_uploads_dir": "/data/uploads"}
    del values[missing]
    with pytest.raises(ConfigurationError) as err:
        Settings(**values, _env_file=None).validate_production()
    assert missing.upper() in str(err.value) and SECRET not in str(err.value)


@pytest.mark.parametrize("over", [
    {"auth_secret": "corto"}, {"mongodb_database": "demand_forecasting_v2"}, {"mongodb_database": "demand_forecasting_dev"},
    {"cookie_secure": False}, {"allowed_origins": "http://df.example.test"}, {"allowed_origins": ORIGIN + "/"},
    {"mongodb_uri": "http://x"},
])
def test_production_rechaza_valores_inseguros(over):
    with pytest.raises(ConfigurationError):
        prod_settings(**over)


def test_production_valida_y_desarrollo_no_cambia():
    assert prod_settings().is_production
    dev = Settings(app_env="development", _env_file=None)
    assert dev.mongodb_database == "demand_forecasting_v2" and not dev.is_production


def test_get_settings_en_produccion_ignora_dotenv_y_falla_sin_variables(monkeypatch):
    for name in ("MONGODB_URI", "MONGODB_DATABASE", "AUTH_SECRET", "ALLOWED_ORIGINS", "DF_UPLOADS_DIR"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    try:
        with pytest.raises(ConfigurationError):
            get_settings()
    finally:
        get_settings.cache_clear()


def test_worker_y_scheduler_exigen_base_explicita_en_produccion(monkeypatch, capsys):
    from pipeline.jobs import handlers, scheduler, worker
    for name in ("MONGODB_URI", "MONGODB_DATABASE", "DF_UPLOADS_DIR"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    assert worker.main(["--once"]) == 2
    assert "MONGODB_URI" in capsys.readouterr().err
    assert scheduler.main(["--once"]) == 2
    monkeypatch.setenv("MONGODB_URI", "mongodb://127.0.0.1:27017")
    monkeypatch.setenv("MONGODB_DATABASE", "demand_forecasting_v2")
    assert worker.main(["--once"]) == 2           # base de desarrollo prohibida en produccion
    monkeypatch.setenv("MONGODB_DATABASE", "df_test_x")
    assert worker.main(["--once"]) == 2           # falta DF_UPLOADS_DIR
    with pytest.raises(ConfigurationError):
        handlers.default_uploads_dir()
    monkeypatch.setenv("DF_UPLOADS_DIR", "/data/uploads")
    assert str(handlers.default_uploads_dir()).replace("\\", "/") == "/data/uploads"
    cfg_module.require_production_env()           # completo: no lanza


def test_worker_y_api_comparten_la_variable_de_subidas(monkeypatch, tmp_path):
    from backend.app.uploads import get_upload_policy
    from pipeline.jobs.handlers import default_uploads_dir
    monkeypatch.setenv("DF_UPLOADS_DIR", str(tmp_path))
    assert get_upload_policy().directory == default_uploads_dir() == tmp_path


# ---------------------------------------------------------------- app: mismo origen, SPA, errores

def test_spa_fallback_y_api_desconocida_devuelve_json(monkeypatch, dist):
    client = make_client(monkeypatch, prod_settings(frontend_dist_dir=str(dist)))
    for route in ("/", "/corridas", "/pronosticos", "/recomendaciones/x"):
        r = client.get(route)
        assert r.status_code == 200 and "SPA-INDEX" in r.text, route
        assert r.headers["cache-control"] == "no-cache"
    assert "SPA-INDEX" not in client.get("/main-ABC123.js").text
    assert "immutable" in client.get("/main-ABC123.js").headers["cache-control"]
    for route in ("/api/v1/no-existe", "/api/otra", "/api", "/api/v1/runs/../x"):
        r = client.get(route)
        assert r.status_code == 404 and r.headers["content-type"].startswith("application/json"), route
        assert r.json()["error"]["code"] == "NO_ENCONTRADO" and "SPA-INDEX" not in r.text
    assert client.get("/falta-chunk.js").status_code == 404
    assert client.post("/api/v1/no-existe").json()["error"]["code"] in {"ERROR", "NO_ENCONTRADO"}
    assert "SPA-INDEX" not in client.post("/api/v1/no-existe").text


def test_fallback_no_sirve_archivos_fuera_del_directorio(monkeypatch, dist):
    client = make_client(monkeypatch, prod_settings(frontend_dist_dir=str(dist)))
    for route in ("/..%2fsecreto.txt", "/%2e%2e/secreto.txt", "/../secreto.txt"):
        assert "fuera" not in client.get(route).text, route


def test_health_intacto_y_sin_docs(monkeypatch, dist):
    class Ok:
        def __init__(self, *a, **k):
            self.admin = self

        def command(self, name):
            return {"ok": 1}

        def close(self):
            pass
    monkeypatch.setattr("backend.app.main.MongoClient", Ok)
    client = make_client(monkeypatch, prod_settings(frontend_dist_dir=str(dist)))
    body = client.get("/api/v1/health").json()
    assert body["status"] == "ok" and body["environment"] == "production" and "mongodb" not in str(body).lower()
    assert client.get("/openapi.json").status_code == 404
    assert "swagger" not in client.get("/docs").text.lower()


def test_production_sin_angular_compilado_no_arranca(monkeypatch, tmp_path):
    with pytest.raises(RuntimeError):
        make_client(monkeypatch, prod_settings(frontend_dist_dir=str(tmp_path / "vacio")))


def test_cabeceras_de_seguridad_y_sin_cors(monkeypatch, dist):
    client = make_client(monkeypatch, prod_settings(frontend_dist_dir=str(dist)))
    r = client.get("/", headers={"Origin": "https://evil.example"})
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
    assert r.headers["strict-transport-security"].startswith("max-age=")
    assert "access-control-allow-origin" not in r.headers
    pre = client.options("/api/v1/health", headers={"Origin": ORIGIN, "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in pre.headers          # mismo origen: no hay CORS
    assert client.get("/api/v1/no-existe").headers["cache-control"] == "no-store"


def test_error_interno_saneado(monkeypatch, dist):
    def boom():
        raise RuntimeError("detalle interno C:\\secreto\\ruta mongodb://u:p@h")
    client = make_client(monkeypatch, prod_settings(frontend_dist_dir=str(dist)))
    client.app.dependency_overrides[get_db] = boom
    r = client.get("/api/v1/auth/me", cookies={"df_session": "x"})
    assert r.status_code == 500 and r.json() == {"error": {"code": "ERROR_INTERNO", "message": "Error interno."}}
    assert "secreto" not in r.text and "Traceback" not in r.text


def test_limites_de_cuerpo(monkeypatch, dist):
    client = make_client(monkeypatch, prod_settings(frontend_dist_dir=str(dist)))
    big_json = client.post("/api/v1/auth/login", content=b"x" * (2 << 20), headers={"Content-Type": "application/json"})
    assert big_json.status_code == 413 and big_json.json()["error"]["code"] == "ARCHIVO_DEMASIADO_GRANDE"
    over = (25 << 20) + (2 << 20)
    r = client.post("/api/v1/imports", content=b"0" * over, headers={"Content-Type": "multipart/form-data; boundary=x"})
    assert r.status_code == 413
    # sin Content-Length (cuerpo troceado) tambien se corta
    def chunks():
        for _ in range(3):
            yield b"1" * (512 << 10)
    r = client.post("/api/v1/auth/login", content=chunks(), headers={"Content-Type": "application/json"})
    assert r.status_code == 413


def test_sin_registro_publico(monkeypatch, dist):
    client = make_client(monkeypatch, prod_settings(frontend_dist_dir=str(dist)))
    paths = [getattr(route, "path", "") for route in client.app.routes]
    assert not [p for p in paths if "regist" in p.lower() or "signup" in p.lower() or "sign-up" in p.lower()]
    for route in ("/api/v1/auth/register", "/api/v1/auth/signup", "/api/v1/users"):
        assert client.post(route, json={"username": "x", "password": "y" * 14}).status_code in {404, 405, 401, 403}


# ---------------------------------------------------------------- login: cookie y X-Forwarded-For

def login(client, password=PASSWORD, **headers):
    return client.post("/api/v1/auth/login", json={"username": "usuario_prueba", "password": password},
                       headers={"Origin": ORIGIN, **headers})


def test_cookie_secure_httponly_samesite_strict(monkeypatch, dist, mongo_db):
    client = make_client(monkeypatch, prod_settings(frontend_dist_dir=str(dist)), mongo_db)
    r = login(client)
    assert r.status_code == 200
    cookie = r.headers["set-cookie"].lower()
    assert "secure" in cookie and "httponly" in cookie and "samesite=strict" in cookie
    assert r.headers["cache-control"] == "no-store"


def test_xff_variable_no_evita_el_limite_sin_proxy_de_confianza(monkeypatch, dist, mongo_db):
    client = make_client(monkeypatch, prod_settings(frontend_dist_dir=str(dist)), mongo_db)
    codes = [login(client, "incorrecta-xxx", **{"X-Forwarded-For": f"198.51.100.{10 + i}"}).status_code
             for i in range(8)]
    assert codes[:5] == [401] * 5 and set(codes[5:]) == {429}, codes
    assert login(client, **{"X-Forwarded-For": "203.0.113.99"}).status_code == 429


def test_xff_desde_el_proxy_de_confianza_usa_la_ip_real_y_no_se_falsifica(monkeypatch, dist, mongo_db):
    settings = prod_settings(frontend_dist_dir=str(dist), trusted_proxies=PROXY)
    client = make_client(monkeypatch, settings, mongo_db, peer=(PROXY, 40000))
    # el proxy anade la IP real a la derecha; el cliente antepone valores falsos distintos en cada intento
    codes = [login(client, "incorrecta-xxx", **{"X-Forwarded-For": f"198.51.100.{10 + i}, 192.0.2.7"}).status_code
             for i in range(8)]
    assert codes[:5] == [401] * 5 and set(codes[5:]) == {429}, codes
    # otro cliente real detras del mismo proxy no queda bloqueado
    assert login(client, **{"X-Forwarded-For": "192.0.2.99"}).status_code == 200


def test_middleware_proxy_unidad():
    seen = []

    async def app(scope, receive, send):
        seen.append(scope["client"][0])

    mw = TrustedProxyMiddleware(app, [PROXY, "10.30.0.0/16"])

    async def run(peer, xff):
        scope = {"type": "http", "client": (peer, 1), "headers": [(b"x-forwarded-for", xff.encode())] if xff else []}
        await mw(scope, None, None)

    import asyncio
    asyncio.run(run("203.0.113.5", "1.2.3.4"))                     # par no confiable: se ignora
    asyncio.run(run(PROXY, "1.2.3.4, 192.0.2.7"))                   # derecha = cliente real
    asyncio.run(run(PROXY, "192.0.2.7, 10.30.1.1"))                 # salta proxies encadenados de confianza
    asyncio.run(run(PROXY, "no-es-ip"))                             # basura: conserva el par
    asyncio.run(run(PROXY, ""))                                      # sin cabecera
    assert seen == ["203.0.113.5", "192.0.2.7", "192.0.2.7", PROXY, PROXY]
    assert TrustedProxyMiddleware(app, []).nets == []
    with pytest.raises(ValueError):
        TrustedProxyMiddleware(app, ["*"])
