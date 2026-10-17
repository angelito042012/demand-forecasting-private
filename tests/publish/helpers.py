"""Ayudas compartidas: base temporal aislada, fuente real verificada y catalogo de prueba."""
from __future__ import annotations

import contextlib
import os
import uuid
from functools import lru_cache

import pytest
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from pipeline.publish.source import (
    PROJECT_ROOT,
    load_publish_config,
    resolve_entry,
    verify_and_load,
)

ENTRY = resolve_entry("t07", load_publish_config())
ARTIFACTS_OK = all((PROJECT_ROOT / ENTRY["artifacts_dir"] / n).is_file() for n in ENTRY["artifacts"])
needs_artifacts = pytest.mark.skipif(not ARTIFACTS_OK, reason="artefactos T07 reales no disponibles")


@lru_cache(maxsize=1)
def real_source():
    return verify_and_load(ENTRY)


def make_catalog(src) -> tuple[dict, str]:
    """Catalogo de prueba derivado de los SKU del fold: 1 de cada 100 queda sin categoria."""
    skus = sorted(set(src.forecasts["entidad"].str.split("|").str[0]))
    cat = {s: f"CAT{int(s) % 7}" for i, s in enumerate(skus) if i % 100 != 99}
    return cat, "catalogo-prueba-v1"


@contextlib.contextmanager
def temp_db():
    uri = os.environ.get("MONGODB_URI", "mongodb://127.0.0.1:27017")
    client = MongoClient(uri, serverSelectionTimeoutMS=1500)
    try:
        client.admin.command("ping")
    except PyMongoError:
        client.close()
        pytest.skip("MongoDB no disponible")
    name = f"df_test_{uuid.uuid4().hex[:12]}"
    try:
        yield client[name]
    finally:
        client.drop_database(name)
        client.close()
