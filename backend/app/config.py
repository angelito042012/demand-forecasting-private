import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PRODUCTION = "production"
# Bases de desarrollo que nunca deben usarse con APP_ENV=production (docs/T11_CONTRATO.md §4).
FORBIDDEN_PRODUCTION_DATABASES = {"demand_forecasting_v2", "demand_forecasting_dev"}
REQUIRED_IN_PRODUCTION = ("mongodb_uri", "mongodb_database", "auth_secret", "allowed_origins", "df_uploads_dir")


class ConfigurationError(RuntimeError):
    """Configuracion de produccion incompleta o insegura (el proceso no debe arrancar)."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_timezone: str = "America/Lima"
    mongodb_uri: str = "mongodb://127.0.0.1:27017"
    mongodb_database: str = "demand_forecasting_v2"
    allowed_origins: str = "http://localhost:4200,http://127.0.0.1:4200"
    # sesion (docs/T08_CONTRATO.md §2)
    cookie_secure: bool = True            # solo False con app_env=development (excepcion local explicita)
    session_absolute_hours: int = 8
    session_idle_minutes: int = 60
    auth_secret: str = ""                 # pimienta para claves de rate limit; obligatoria en produccion
    login_max_failures_user_ip: int = 5
    login_max_failures_ip: int = 20
    login_window_minutes: int = 15
    # produccion (docs/T11_PLAN_DESPLIEGUE.md)
    df_uploads_dir: str = ""              # directorio durable compartido API/worker (obligatorio en produccion)
    trusted_proxies: str = ""             # IP/CIDR del salto de proxy de confianza; vacio = no se confia en X-Forwarded-For
    frontend_dist_dir: str = ""           # Angular compilado; vacio = frontend/dist/frontend/browser (solo si existe)
    serve_frontend: bool = True
    max_body_bytes: int = 26214400 + 1048576   # 25 MiB (T10 tam_max_comprimido_bytes) + sobrecarga multipart
    max_json_body_bytes: int = 1048576

    @property
    def is_production(self) -> bool:
        return self.app_env == PRODUCTION

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def proxies(self) -> list[str]:
        return [p.strip() for p in self.trusted_proxies.split(",") if p.strip()]

    def validate_production(self) -> "Settings":
        """Falla con ConfigurationError si APP_ENV=production y la configuracion es incompleta o insegura."""
        if not self.is_production:
            return self
        problems = [f"falta {name.upper()}" for name in REQUIRED_IN_PRODUCTION if name not in self.model_fields_set
                    or not str(getattr(self, name)).strip()]
        if not problems:
            if len(self.auth_secret) < 32:
                problems.append("AUTH_SECRET debe tener al menos 32 caracteres")
            if self.mongodb_database in FORBIDDEN_PRODUCTION_DATABASES:
                problems.append("MONGODB_DATABASE no puede ser una base de desarrollo")
            if not self.cookie_secure:
                problems.append("COOKIE_SECURE debe ser true")
            if not self.origins or any(not o.startswith("https://") or o.endswith("/") for o in self.origins):
                problems.append("ALLOWED_ORIGINS debe listar origenes https exactos sin barra final")
            if not self.mongodb_uri.startswith(("mongodb://", "mongodb+srv://")):
                problems.append("MONGODB_URI invalida")
        if problems:
            # solo nombres de variables; nunca valores
            raise ConfigurationError("Configuracion de produccion invalida: " + "; ".join(problems))
        return self

    def frontend_dir(self) -> Path | None:
        path = Path(self.frontend_dist_dir) if self.frontend_dist_dir else (
            Path(__file__).resolve().parents[2] / "frontend" / "dist" / "frontend" / "browser")
        return path if self.serve_frontend and (path / "index.html").is_file() else None


@lru_cache
def get_settings() -> Settings:
    if os.environ.get("APP_ENV") == PRODUCTION:
        return Settings(_env_file=None).validate_production()   # solo variables inyectadas, nunca un .env local
    return Settings()


def require_production_env(environ=os.environ, *, uploads: bool = True) -> None:
    """Worker/temporizador: con APP_ENV=production exigen URI y base explicitas (sin valores por defecto)."""
    if environ.get("APP_ENV") != PRODUCTION:
        return
    missing = [n for n in ("MONGODB_URI", "MONGODB_DATABASE", *(("DF_UPLOADS_DIR",) if uploads else ())) if not environ.get(n, "").strip()]
    if missing:
        raise ConfigurationError("Configuracion de produccion invalida: falta " + ", ".join(missing))
    if environ["MONGODB_DATABASE"] in FORBIDDEN_PRODUCTION_DATABASES:
        raise ConfigurationError("Configuracion de produccion invalida: MONGODB_DATABASE no puede ser una base de desarrollo")
