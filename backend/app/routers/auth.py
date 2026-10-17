"""Login, sesion actual y logout (docs/T08_CONTRATO.md §2). Nunca se registran contrasenas ni tokens."""
from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field
from pymongo.database import Database

from backend.app.auth.budget import ensure_indexes as ensure_budget_indexes
from backend.app.auth.budget import refund, reserve
from backend.app.auth.deps import (
    COOKIE_NAME,
    CurrentUser,
    DbDep,
    SettingsDep,
    check_login_request,
    cookie_secure,
    require_csrf,
    require_user,
)
from backend.app.auth.passwords import dummy_verify, normalize_username, verify_password
from backend.app.auth.store import (
    csrf_from_session_token,
    ensure_indexes,
    iso_z,
    sha256_hex,
    utcnow,
)
from backend.app.config import Settings
from backend.app.errors import ApiError

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


def _key(settings: Settings, *parts: str) -> str:
    """Clave opaca (sha256 con pimienta) para no guardar usuario/IP en claro."""
    return hashlib.sha256("\x1f".join((settings.auth_secret, *parts)).encode("utf-8")).hexdigest()


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "desconocida"  # no se confia en X-Forwarded-For


def _bad_credentials() -> ApiError:
    return ApiError(401, "NO_AUTENTICADO", "Usuario o contrasena incorrectos.")


def _reserve_or_429(db: Database, settings: Settings, k_user_ip: str, k_ip: str) -> None:
    """Reserva atomica de cupos ANTES de verificar la contrasena (backend/app/auth/budget.py)."""
    window = settings.login_window_minutes * 60
    user_slot = reserve(db, k_user_ip, settings.login_max_failures_user_ip, window)
    if not user_slot.allowed:
        raise ApiError(429, "DEMASIADOS_INTENTOS", "Demasiados intentos; reintente mas tarde.",
                       headers={"Retry-After": str(user_slot.retry_after)})
    ip_slot = reserve(db, k_ip, settings.login_max_failures_ip, window)
    if not ip_slot.allowed:
        refund(db, k_user_ip)              # el intento no llego a evaluarse: se devuelve el cupo
        raise ApiError(429, "DEMASIADOS_INTENTOS", "Demasiados intentos; reintente mas tarde.",
                       headers={"Retry-After": str(ip_slot.retry_after)})


@router.post("/login", dependencies=[Depends(check_login_request)])
def login(body: LoginIn, request: Request, response: Response, db: DbDep, settings: SettingsDep) -> dict:
    ensure_indexes(db, settings.login_window_minutes)
    ensure_budget_indexes(db)
    username = normalize_username(body.username)
    ip = _client_ip(request)
    k_user_ip, k_ip = _key(settings, "u", username, ip), _key(settings, "ip", ip)
    _reserve_or_429(db, settings, k_user_ip, k_ip)    # un cupo por intento; solo el exito lo devuelve

    user = db["users"].find_one({"username": username})
    if user is not None and user.get("active", False) and verify_password(body.password, user["password_hash"]):
        ok = True
    else:
        ok = False
        if user is None or not user.get("active", False):
            dummy_verify(body.password)  # iguala el tiempo
    if not ok:
        raise _bad_credentials()                       # el fallo conserva su cupo reservado

    refund(db, k_user_ip, reset=True)                  # login correcto: devuelve los cupos
    refund(db, k_ip)
    # rotacion: la sesion presentada (si la hay) se revoca y se crea una nueva
    old = request.cookies.get(COOKIE_NAME)
    now = utcnow()
    if old and len(old) <= 200:
        db["sessions"].update_one({"token_hash": sha256_hex(old), "revoked_at": None}, {"$set": {"revoked_at": now}})
    token = secrets.token_urlsafe(32)
    csrf = csrf_from_session_token(token)
    expires_at = now + timedelta(hours=settings.session_absolute_hours)
    idle_at = min(now + timedelta(minutes=settings.session_idle_minutes), expires_at)
    db["sessions"].insert_one({
        "token_hash": sha256_hex(token), "csrf_hash": sha256_hex(csrf), "username": user["username"],
        "created_at": now, "last_seen_at": now, "expires_at": expires_at, "idle_expires_at": idle_at,
        "revoked_at": None, "schema_version": 1,
    })
    response.set_cookie(COOKIE_NAME, token, max_age=int((expires_at - now).total_seconds()), path="/",
                        httponly=True, samesite="strict", secure=cookie_secure(settings))
    response.headers["Cache-Control"] = "no-store"
    return {"username": user["username"], "role": user["role"], "csrf_token": csrf,
            "expires_at": iso_z(expires_at)}


@router.get("/me")
def me(request: Request, response: Response, user: Annotated[CurrentUser, Depends(require_user)]) -> dict:
    response.headers["Cache-Control"] = "no-store"
    token = request.cookies[COOKIE_NAME]
    return {"username": user.username, "role": user.role, "csrf_token": csrf_from_session_token(token),
            "expires_at": iso_z(user.expires_at), "idle_expires_at": iso_z(user.idle_expires_at)}


@router.post("/logout", status_code=204)
def logout(request: Request, db: DbDep, settings: SettingsDep,
           _: Annotated[CurrentUser, Depends(require_csrf)]) -> Response:
    token = request.cookies[COOKIE_NAME]
    db["sessions"].update_one({"token_hash": sha256_hex(token), "revoked_at": None},
                              {"$set": {"revoked_at": utcnow()}})
    resp = Response(status_code=204)
    resp.delete_cookie(COOKIE_NAME, path="/", httponly=True, samesite="strict", secure=cookie_secure(settings))
    return resp
