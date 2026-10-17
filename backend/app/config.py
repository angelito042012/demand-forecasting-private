from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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
    auth_secret: str = ""                 # pimienta para claves de rate limit; opcional
    login_max_failures_user_ip: int = 5
    login_max_failures_ip: int = 20
    login_window_minutes: int = 15

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
