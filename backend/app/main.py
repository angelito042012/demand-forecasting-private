from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from backend.app.config import get_settings
from backend.app.errors import install_error_handlers
from backend.app.hardening import (
    BodyLimitMiddleware,
    SecurityHeadersMiddleware,
    TrustedProxyMiddleware,
    install_frontend,
)
from backend.app.routers import (
    admin,
    auth,
    backtests,
    forecasts,
    imports,
    jobs,
    recommendations,
    runs,
    sales,
)

API_VERSION = "0.1.0"


def create_app() -> FastAPI:
    settings = get_settings().validate_production()
    prod = settings.is_production
    app = FastAPI(title="Demand Forecasting API", version=API_VERSION,
                  docs_url=None if prod else "/docs", redoc_url=None if prod else "/redoc",
                  openapi_url=None if prod else "/openapi.json")
    if not prod:     # produccion: mismo origen, sin CORS
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.origins,
            allow_credentials=True,
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type", "X-CSRF-Token"],
        )
    # el ultimo agregado es el mas externo: cabeceras > proxy de confianza > limite de cuerpo
    app.add_middleware(BodyLimitMiddleware, max_body=settings.max_body_bytes, max_json=settings.max_json_body_bytes)
    app.add_middleware(TrustedProxyMiddleware, trusted=settings.proxies)
    app.add_middleware(SecurityHeadersMiddleware, hsts=prod)
    install_error_handlers(app)
    for module in (auth, admin, imports, sales, runs, jobs, forecasts, recommendations, backtests):
        app.include_router(module.router, prefix="/api/v1")

    @app.get("/api/v1/health")
    def health() -> dict:
        """Estado del servicio y de la base; no expone URI, credenciales ni datos."""
        client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=1500)
        try:
            client.admin.command("ping")
            database = "ok"
        except PyMongoError:
            database = "unavailable"
        finally:
            client.close()
        return {
            "status": "ok" if database == "ok" else "degraded",
            "database": database,
            "version": API_VERSION,
            "environment": settings.app_env,
            "timezone": settings.app_timezone,
        }

    dist = settings.frontend_dir()
    if prod and settings.serve_frontend and dist is None:
        raise RuntimeError("Falta el Angular compilado (FRONTEND_DIST_DIR/index.html) con APP_ENV=production.")
    if prod and dist is not None:      # registrado al final: nunca oculta una ruta /api real
        install_frontend(app, dist)
    return app


app = create_app()
