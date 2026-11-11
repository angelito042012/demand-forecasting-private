"""Configuracion de politica del SERVIDOR (config/t10_config.json) y errores de generacion."""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
T10_CONFIG_PATH = PROJECT_ROOT / "config" / "t10_config.json"
T05_CONFIG_PATH = PROJECT_ROOT / "config" / "t05_config.json"


class GenerationError(Exception):
    """Error de generacion con codigo estable y mensaje apto para el usuario (sin rutas ni URI)."""

    def __init__(self, code: str, message: str, *, retryable: bool = False):
        self.code, self.message, self.retryable = code, message, retryable
        super().__init__(message)


def load_t10_config(path: Path | None = None) -> dict:
    return json.loads((path or T10_CONFIG_PATH).read_text(encoding="utf-8"))


def cohort_rule() -> dict:
    """Regla de cohorte primaria de T05 (historia >= 56 dias y >= 21 observaciones utiles en 28)."""
    cp = json.loads(T05_CONFIG_PATH.read_text(encoding="utf-8"))["cohorte_primaria"]
    return {"historia_minima_dias": int(cp["historia_minima_dias"]),
            "observaciones_utilizables_minimas_en_28": int(cp["observaciones_utilizables_minimas_en_28"])}


def check_policy(origin: date, horizon: int, method: str, cfg: dict) -> None:
    """Politica de desarrollo: origen en [origen_minimo, origen_maximo], horizonte <= maximo, metodo permitido."""
    pol = cfg["politica_desarrollo"]
    lo, hi = date.fromisoformat(pol["origen_minimo"]), date.fromisoformat(pol["origen_maximo"])
    if not lo <= origin <= hi:
        raise GenerationError("CORTE_FUERA_DE_RANGO",
                              f"El origen debe estar entre {lo:%d/%m/%Y} y {hi:%d/%m/%Y}.")
    if not 1 <= horizon <= int(pol["horizonte_maximo"]):
        raise GenerationError("CORTE_FUERA_DE_RANGO", f"El horizonte debe estar entre 1 y {pol['horizonte_maximo']} días.")
    if method not in pol["metodos_permitidos"]:
        raise GenerationError("METODO_NO_PERMITIDO", "El método solicitado no está permitido.")
    last = date.fromisoformat(pol["ultimo_dia_de_datos"])
    if origin + timedelta(days=horizon) > last:
        raise GenerationError("CORTE_FUERA_DE_RANGO",
                              f"Los días objetivo exceden el {last:%d/%m/%Y}.")
