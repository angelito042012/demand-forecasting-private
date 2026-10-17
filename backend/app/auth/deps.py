"""Dependencias de autenticacion/autorizacion (contrato: docs/T08_CONTRATO.md §2).

Interfaz estable para las rutas de datos: `CurrentUser`, `require_user`, `require_admin`
(y `require_csrf` para mutaciones). Las pruebas de otras rutas pueden sustituirlas con
`app.dependency_overrides[require_user] = lambda: CurrentUser("lector1", "lector", "csrf")`.
"""
from __future__ import annotations

import hmac
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import Depends, Request
from pymongo.database import Database

from backend.app.auth.store import as_utc, ensure_indexes, sha256_hex, utcnow
from backend.app.config import Settings, get_settings
from backend.app.db import get_db
from backend.app.errors import ApiError

DbDep = Annotated[Database, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
COOKIE_NAME = "df_session"
CSRF_HEADER = "X-CSRF-Token"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


@dataclass(frozen=True)
class CurrentUser:
    username: str
    role: str            # "admin" | "lector"
    csrf_token_hash: str = ""
    expires_at: datetime | None = None
    idle_expires_at: datetime | None = None


def cookie_secure(settings: Settings) -> bool:
    """Secure siempre, salvo excepcion local explicita (COOKIE_SECURE=false y APP_ENV=development)."""
    return bool(settings.cookie_secure) or settings.app_env != "development"


def request_origin(request: Request) -> str | None:
    origin = request.headers.get("origin")
    if origin and origin != "null":
        return origin
    referer = request.headers.get("referer")
    if referer:
        parts = urlsplit(referer)
        if parts.scheme and parts.netloc:
            return f"{parts.scheme}://{parts.netloc}"
    return None


def check_origin(request: Request, settings: Settings) -> None:
    origin = request_origin(request)
    if origin is None or origin not in settings.origins:
        raise ApiError(403, "ORIGEN_NO_PERMITIDO", "Origen no permitido.")


def check_json_content_type(request: Request) -> None:
    media = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if media != "application/json":
        raise ApiError(422, "ENTRADA_INVALIDA", "Se requiere Content-Type application/json.")


def check_login_request(request: Request, settings: SettingsDep) -> None:
    """Dependencia del login (sin sesion): Origin permitido y JSON."""
    check_origin(request, settings)
    check_json_content_type(request)


def require_user(
    request: Request,
    db: DbDep,
    settings: SettingsDep,
) -> CurrentUser:
    token = request.cookies.get(COOKIE_NAME)
    if not token or len(token) > 200:
        raise ApiError(401, "NO_AUTENTICADO", "Autenticacion requerida.")
    ensure_indexes(db, settings.login_window_minutes)
    now = utcnow()
    session = db["sessions"].find_one({"token_hash": sha256_hex(token)})
    if session is None or session.get("revoked_at") is not None:
        raise ApiError(401, "NO_AUTENTICADO", "Autenticacion requerida.")
    expires_at, idle_at = as_utc(session["expires_at"]), as_utc(session["idle_expires_at"])
    if now >= expires_at or now >= idle_at:
        raise ApiError(401, "SESION_EXPIRADA", "La sesion vencio; inicie sesion nuevamente.")
    user = db["users"].find_one({"username": session["username"]})
    if user is None or not user.get("active", False):
        raise ApiError(401, "NO_AUTENTICADO", "Autenticacion requerida.")
    new_idle = min(now + timedelta(minutes=settings.session_idle_minutes), expires_at)
    db["sessions"].update_one({"_id": session["_id"]}, {"$set": {"last_seen_at": now, "idle_expires_at": new_idle}})
    return CurrentUser(user["username"], user["role"], session["csrf_hash"], expires_at, new_idle)


def require_admin(user: Annotated[CurrentUser, Depends(require_user)]) -> CurrentUser:
    if user.role != "admin":
        raise ApiError(403, "PROHIBIDO", "No tiene permiso para esta operacion.")
    return user


def require_csrf(
    request: Request,
    user: Annotated[CurrentUser, Depends(require_user)],
    settings: SettingsDep,
) -> CurrentUser:
    """Mutaciones: Origin/Referer permitido, JSON y cabecera X-CSRF-Token valida. No-op en GET/HEAD/OPTIONS."""
    if request.method in SAFE_METHODS:
        return user
    check_origin(request, settings)
    check_json_content_type(request)
    supplied = request.headers.get(CSRF_HEADER, "")
    if not supplied or not user.csrf_token_hash or not hmac.compare_digest(
            sha256_hex(supplied), user.csrf_token_hash):
        raise ApiError(403, "CSRF_INVALIDO", "Token CSRF ausente o invalido.")
    return user
