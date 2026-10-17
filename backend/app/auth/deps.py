"""Dependencias de autenticacion/autorizacion (contrato: docs/T08_CONTRATO.md §2).

INTERFAZ ACORDADA entre agentes. Implementa el agente backend/auth; las rutas de datos solo importan
`CurrentUser`, `require_user` y `require_admin`. En pruebas de rutas de datos se sustituyen con
`app.dependency_overrides[require_user] = lambda: CurrentUser("lector1", "lector", "csrf")`.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CurrentUser:
    username: str
    role: str            # "admin" | "lector"
    csrf_token_hash: str = ""


def require_user() -> CurrentUser:           # sera reemplazada por la implementacion real
    raise NotImplementedError("pendiente de implementar por el agente de autenticacion")


def require_admin() -> CurrentUser:
    raise NotImplementedError("pendiente de implementar por el agente de autenticacion")
