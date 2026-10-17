"""Administracion de usuarios (solo admin; docs/T08_CONTRATO.md §2). Nunca devuelve hashes."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from backend.app.auth.deps import DbDep, require_admin, require_csrf
from backend.app.auth.passwords import (
    normalize_username,
    validate_password,
    validate_username,
)
from backend.app.auth.store import create_user, iso_z
from backend.app.errors import ApiError, page_response

router = APIRouter(prefix="/admin", tags=["admin"])


class UserIn(BaseModel):
    username: str
    role: Literal["admin", "lector"]
    password: str


@router.get("/users", dependencies=[Depends(require_admin)])
def list_users(db: DbDep, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200)) -> dict:
    total = db["users"].count_documents({})
    cursor = db["users"].find({}, {"password_hash": 0}).sort("username", 1).skip((page - 1) * page_size).limit(page_size)
    items = [{"username": u["username"], "role": u["role"], "active": bool(u.get("active", False)),
              "created_at": iso_z(u["created_at"])} for u in cursor]
    return page_response(items, total, page, page_size)


@router.post("/users", status_code=201, dependencies=[Depends(require_admin), Depends(require_csrf)])
def add_user(body: UserIn, db: DbDep) -> dict:
    username = normalize_username(body.username)
    problem = validate_username(username) or validate_password(body.password)
    if problem:
        raise ApiError(422, "ENTRADA_INVALIDA", problem)
    if not create_user(db, username, body.role, body.password):
        raise ApiError(422, "ENTRADA_INVALIDA", "El usuario ya existe.")
    return {"username": username, "role": body.role}
