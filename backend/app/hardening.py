"""Endurecimiento de produccion (docs/T11_PLAN_DESPLIEGUE.md): proxy de confianza, limite de cuerpo,
cabeceras de seguridad y servicio del Angular compilado del mismo origen. ASGI puro, sin estado."""
from __future__ import annotations

import ipaddress
import json
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, Response

from backend.app.errors import ApiError, body

CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
       "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")


def parse_networks(items: list[str]) -> list:
    # ValueError si la lista es invalida: el proceso no arranca
    return [ipaddress.ip_network(item, strict=False) for item in items]


def _in(nets: list, text: str) -> bool:
    try:
        ip = ipaddress.ip_address(text.strip())
    except ValueError:
        return False
    return any(ip in n for n in nets)


class TrustedProxyMiddleware:
    """Confia en X-Forwarded-For SOLO si el par TCP directo esta en la lista de proxies de confianza.

    Recorre la cadena de derecha a izquierda saltando proxies de confianza; la primera IP no confiable es el
    cliente. Los valores que el cliente antepone (a la izquierda) nunca se usan. Lista vacia: no hace nada."""

    def __init__(self, app, trusted: list[str]):
        self.app, self.nets = app, parse_networks(trusted)

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket") and self.nets and scope.get("client"):
            peer = scope["client"][0]
            if _in(self.nets, peer):
                raw = b",".join(v for k, v in scope["headers"] if k == b"x-forwarded-for").decode("latin-1")
                chain = [p.strip() for p in raw.split(",") if p.strip()]
                client = None
                for entry in reversed(chain):
                    try:
                        ipaddress.ip_address(entry)
                    except ValueError:
                        client = None
                        break
                    client = entry
                    if not _in(self.nets, entry):
                        break
                if client:
                    scope = {**scope, "client": (client, 0)}
        await self.app(scope, receive, send)


class _TooLarge(Exception):
    pass


class BodyLimitMiddleware:
    """413 JSON si Content-Length o los bytes recibidos superan el limite (multipart: 25 MiB + sobrecarga)."""

    def __init__(self, app, max_body: int, max_json: int):
        self.app, self.max_body, self.max_json = app, max_body, max_json

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope["headers"])
        multipart = headers.get(b"content-type", b"").lower().startswith(b"multipart/form-data")
        limit = self.max_body if multipart else self.max_json
        declared = headers.get(b"content-length")
        if declared is not None and (not declared.isdigit() or int(declared) > limit):
            return await self._reject(send)
        seen = 0
        exceeded = False
        replied = False

        async def counting():
            nonlocal seen, exceeded
            message = await receive()
            if message["type"] == "http.request":
                seen += len(message.get("body", b""))
                if seen > limit:
                    exceeded = True        # FastAPI puede capturar excepciones del lector: se sustituye la respuesta
                    raise _TooLarge
            return message

        async def guarded_send(message):
            nonlocal replied
            if exceeded:
                if not replied:
                    replied = True
                    await self._reject(send)
                return
            await send(message)

        try:
            await self.app(scope, counting, guarded_send)
        except _TooLarge:
            if not replied:
                await self._reject(send)

    @staticmethod
    async def _reject(send):
        payload = json.dumps(body("ARCHIVO_DEMASIADO_GRANDE", "El cuerpo de la peticion supera el tamano permitido.")).encode()
        await send({"type": "http.response.start", "status": 413,
                    "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(payload)).encode())]})
        await send({"type": "http.response.body", "body": payload})


class SecurityHeadersMiddleware:
    def __init__(self, app, hsts: bool):
        self.app, self.hsts = app, hsts

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        api = scope["path"].startswith("/api")

        async def wrapped(message):
            if message["type"] == "http.response.start":
                names = {k.lower() for k, _ in message["headers"]}
                extra = [(b"x-content-type-options", b"nosniff"), (b"x-frame-options", b"DENY"),
                         (b"referrer-policy", b"no-referrer"), (b"content-security-policy", CSP.encode()),
                         (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
                         (b"cross-origin-opener-policy", b"same-origin")]
                if self.hsts:
                    extra.append((b"strict-transport-security", b"max-age=31536000"))
                if api:
                    extra.append((b"cache-control", b"no-store"))
                message = {**message, "headers": [*message["headers"], *[e for e in extra if e[0] not in names]]}
            await send(message)

        await self.app(scope, receive, wrapped)


def install_frontend(app: FastAPI, dist: Path) -> None:
    """Sirve el Angular compilado y un fallback SPA. Toda ruta /api desconocida devuelve el JSON de errores."""
    root = dist.resolve()
    index = root / "index.html"

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str, request: Request) -> Response:
        if full_path == "api" or full_path.startswith("api/"):
            raise ApiError(404, "NO_ENCONTRADO", "Recurso no encontrado.")
        if full_path:
            candidate = (root / full_path).resolve()
            if candidate.is_file() and candidate.is_relative_to(root):
                immutable = {"Cache-Control": "public, max-age=31536000, immutable"} if "-" in candidate.stem else {}
                return FileResponse(candidate, headers=immutable)
            if Path(full_path).suffix:        # un recurso con extension inexistente es 404, no la SPA
                raise ApiError(404, "NO_ENCONTRADO", "Recurso no encontrado.")
        return FileResponse(index, media_type="text/html", headers={"Cache-Control": "no-cache"})
