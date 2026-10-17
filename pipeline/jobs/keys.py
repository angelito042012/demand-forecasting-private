"""Claves de idempotencia ESTANDAR de los trabajos (T10 §2). La API y el temporizador usan estas mismas funciones.

`gen:<origen>:<horizonte>:<metodo>:<generador>:<digest de fuentes aprobadas con mes <= mes del origen>` y, si el
administrador envia `Idempotency-Key`, se une como sufijo `:k=<clave saneada>`. Entradas distintas nunca comparten
clave; una fuente aprobada nueva cambia el digest.
"""
from __future__ import annotations

import hashlib
import re
from datetime import date
from functools import lru_cache

from pipeline.data.sources import approved_sources
from pipeline.generate.config import load_t10_config

_IDEM_BAD = re.compile(r"[^A-Za-z0-9._-]+")


@lru_cache(maxsize=1)
def generator_version() -> str:
    return str(load_t10_config()["generador"]["version"])


def sources_digest(db, origin: date) -> str:
    """sha256 de los sha256 ordenados de las fuentes aprobadas con mes <= mes del origen."""
    month = origin.strftime("%Y-%m")
    shas = sorted(sha for sha, imp in approved_sources(db).items() if str(imp.get("mes", "9999-99")) <= month)
    return hashlib.sha256("\n".join(shas).encode("ascii")).hexdigest()


def clean_idempotency_key(raw: str | None) -> str | None:
    if not raw:
        return None
    cleaned = _IDEM_BAD.sub("", raw)[:40]
    return cleaned or None


def generate_run_key(db, origin: date, horizon: int, method: str, idempotency_header: str | None = None,
                     generator: str | None = None) -> str:
    key = f"gen:{origin.isoformat()}:{int(horizon)}:{method}:{generator or generator_version()}:" \
          f"{sources_digest(db, origin)}"
    extra = clean_idempotency_key(idempotency_header)
    return f"{key}:k={extra}" if extra else key


def import_key(sha256: str) -> str:
    return f"import:{sha256}"
