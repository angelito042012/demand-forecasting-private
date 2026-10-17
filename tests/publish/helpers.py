"""Ayudas compartidas: base temporal aislada, fuente real verificada y catalogo de prueba."""
from __future__ import annotations

import contextlib
import os
import uuid
from fractions import Fraction
from functools import lru_cache

import pytest
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from pipeline.publish.signals import Signals, fingerprint_signals
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
    return cat, src.manifest["folds_predictivos"][src.entry["fold"]]["fingerprint"]


def make_signals(src, variant: str = "") -> Signals:
    """Senales de PRUEBA coherentes con el CSV (suma = media*28, 28 dias utiles). En produccion las calcula
    compute_signals desde la historia aprobada; este helper solo evita depender de Mongo con ventas reales."""
    fold = src.manifest["folds_predictivos"][src.entry["fold"]]
    per = {}
    g = src.forecasts.groupby("entidad")["pred_promedio_28"].first()
    for ent, mean in g.items():
        sku, alm = ent.split("|")
        per[(sku, alm)] = (Fraction(round(float(mean) * 28)), 28)
    start = f"2026-06-13{variant}"
    return Signals(origin=src.entry["cutoff"], window_start=start, window_end=src.entry["cutoff"], per_sku=per,
                   training_fingerprint=fold["fingerprint"],
                   fingerprint=fingerprint_signals(src.entry["cutoff"], start, src.entry["cutoff"], per,
                                                   fold["fingerprint"]))


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


def kids(db, run_id: str) -> str:
    """run_id bajo el que estan los hijos visibles de una corrida (children_ref, o el propio run_id)."""
    run = db.runs.find_one({"run_id": run_id}, {"children_ref": 1})
    return (run or {}).get("children_ref") or run_id
