"""Acceso a las colecciones users/sessions/login_attempts (docs/T08_CONTRATO.md §2 y §4)."""
from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime

from pymongo.database import Database
from pymongo.errors import DuplicateKeyError, OperationFailure

from backend.app.auth.passwords import hash_password

_INDEXED: set[tuple[int, str]] = set()


def utcnow() -> datetime:
    return datetime.now(UTC)


def as_utc(value: datetime) -> datetime:
    """PyMongo devuelve fechas ingenuas (UTC) salvo tz_aware; se normalizan."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def iso_z(value: datetime) -> str:
    return as_utc(value).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def csrf_from_session_token(token: str) -> str:
    """csrf_token = HMAC-SHA256 con clave = token de sesion. Solo se guarda sha256(csrf) en Mongo."""
    return hmac.new(token.encode("utf-8"), b"df-csrf-v1", hashlib.sha256).hexdigest()


def ensure_indexes(db: Database, login_window_minutes: int = 15) -> None:
    key = (id(db.client), db.name)
    if key in _INDEXED:
        return
    db["users"].create_index("username", unique=True, name="username_unique")
    db["sessions"].create_index("token_hash", unique=True, name="token_hash_unique")
    db["sessions"].create_index("expires_at", expireAfterSeconds=0, name="expires_at_ttl")
    try:
        db["login_attempts"].create_index("at", expireAfterSeconds=login_window_minutes * 60, name="at_ttl")
    except OperationFailure:  # TTL ya creado con otro valor: no se altera de forma destructiva
        pass
    db["login_attempts"].create_index([("scope", 1), ("key", 1), ("at", 1)], name="scope_key_at")
    _INDEXED.add(key)


def create_user(db: Database, username: str, role: str, password: str) -> bool:
    """False si el usuario ya existe (no sobrescribe)."""
    ensure_indexes(db)
    try:
        db["users"].insert_one({
            "username": username, "password_hash": hash_password(password), "role": role,
            "active": True, "created_at": utcnow(), "schema_version": 1,
        })
    except DuplicateKeyError:
        return False
    return True
