from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from backend.app.config import get_settings
from backend.app.errors import install_error_handlers
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
    settings = get_settings()
    app = FastAPI(title="Demand Forecasting API", version=API_VERSION)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-CSRF-Token"],
    )
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

    return app


app = create_app()
