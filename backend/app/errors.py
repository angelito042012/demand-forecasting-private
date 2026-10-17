"""Errores uniformes de la API (docs/T08_CONTRATO.md §1). Sin trazas ni detalles internos."""
from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError
from starlette.exceptions import HTTPException as StarletteHTTPException

CODES = {401: "NO_AUTENTICADO", 403: "PROHIBIDO", 404: "NO_ENCONTRADO", 422: "ENTRADA_INVALIDA",
         429: "DEMASIADOS_INTENTOS", 503: "SERVICIO_NO_DISPONIBLE"}


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details: list | None = None,
                 headers: dict | None = None):
        self.status, self.code, self.message, self.details, self.headers = status, code, message, details, headers or {}
        super().__init__(message)


def body(code: str, message: str, details: list | None = None) -> dict:
    out = {"error": {"code": code, "message": message}}
    if details:
        out["error"]["details"] = details
    return out


@dataclass
class PageParams:
    page: int = 1
    page_size: int = 50
    skip: int = field(init=False)

    def __post_init__(self):
        self.skip = (self.page - 1) * self.page_size


def page_response(items: list, total: int, page: int, page_size: int) -> dict:
    return {"items": items, "page": page, "page_size": page_size, "total": total,
            "has_more": page * page_size < total}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api(_: Request, exc: ApiError):
        return JSONResponse(body(exc.code, exc.message, exc.details), status_code=exc.status, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        details = [{"campo": ".".join(str(p) for p in e.get("loc", ()) if p != "query"), "motivo": e.get("msg", "invalido")}
                   for e in exc.errors()][:10]
        return JSONResponse(body("ENTRADA_INVALIDA", "Parametros o cuerpo invalidos.", details), status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        code = CODES.get(exc.status_code, "ERROR")
        msg = {404: "Recurso no encontrado.", 405: "Metodo no permitido."}.get(exc.status_code, "Solicitud no valida.")
        return JSONResponse(body(code, msg), status_code=exc.status_code)

    @app.exception_handler(PyMongoError)
    async def _mongo(_: Request, exc: PyMongoError):
        return JSONResponse(body("SERVICIO_NO_DISPONIBLE", "Servicio no disponible, reintente en unos minutos."),
                            status_code=503)

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        return JSONResponse(body("ERROR_INTERNO", "Error interno."), status_code=500)
