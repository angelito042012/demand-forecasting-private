"""Fixtures compartidas de las pruebas de autenticacion: base temporal aislada df_test_<uuid>."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from backend.app.auth.deps import CurrentUser, require_admin, require_csrf, require_user
from backend.app.auth.passwords import hash_password
from backend.app.config import Settings, get_settings
from backend.app.db import get_db
from backend.app.errors import install_error_handlers
from backend.app.routers import admin, auth

ORIGIN = "http://localhost:4200"
JSON = {"Content-Type": "application/json"}
PASSWORD = "clave-de-prueba-123"  # solo para bases temporales de prueba
_HASH = hash_password(PASSWORD)


def build_app(db, settings: Settings) -> FastAPI:
    """App minima (solo auth/admin + rutas de prueba) para no depender de routers ajenos."""
    app = FastAPI()
    install_error_handlers(app)
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(admin.router, prefix="/api/v1")

    @app.get("/api/v1/_t/user")
    def t_user(u: Annotated[CurrentUser, Depends(require_user)]):
        return {"username": u.username, "role": u.role}

    @app.get("/api/v1/_t/admin")
    def t_admin(u: Annotated[CurrentUser, Depends(require_admin)]):
        return {"username": u.username}

    @app.post("/api/v1/_t/mutate")
    def t_mutate(u: Annotated[CurrentUser, Depends(require_csrf)]):
        return {"ok": True}

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: settings
    return app


@pytest.fixture
def db():
    client = MongoClient("mongodb://127.0.0.1:27017", serverSelectionTimeoutMS=1500)
    try:
        client.admin.command("ping")
    except PyMongoError:
        client.close()
        pytest.skip("MongoDB local no disponible")
    name = f"df_test_{uuid.uuid4().hex}"
    database = client[name]
    yield database
    client.drop_database(name)
    client.close()


@pytest.fixture
def settings():
    return Settings(_env_file=None, app_env="development", cookie_secure=False, allowed_origins=ORIGIN,
                    auth_secret="pimienta-de-prueba")


@pytest.fixture
def users(db):
    now = datetime.now(UTC)
    for name, role, active in (("ana", "admin", True), ("luis", "lector", True), ("inactivo", "lector", False)):
        db["users"].insert_one({"username": name, "password_hash": _HASH, "role": role, "active": active,
                                "created_at": now, "schema_version": 1})


@pytest.fixture
def app(db, settings, users):
    return build_app(db, settings)


@pytest.fixture
def client(app):
    with TestClient(app, base_url="http://testserver") as c:
        yield c


def login(client, username="ana", password=PASSWORD, origin=ORIGIN, headers=None):
    h = {**JSON, **({"Origin": origin} if origin else {}), **(headers or {})}
    return client.post("/api/v1/auth/login", json={"username": username, "password": password}, headers=h)


def mut_headers(csrf, origin=ORIGIN):
    return {**JSON, "Origin": origin, "X-CSRF-Token": csrf}
