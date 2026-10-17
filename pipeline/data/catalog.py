"""Catalogo de categoria por SKU versionado por fecha de corte (DECISIONES_DATOS.md).

Regla: categoria mas reciente conocida con fecha <= corte (solo ventas de
entrenamiento); empate de fecha -> mayor frecuencia (<= corte) -> orden alfabetico.
categoria_original de cada transaccion no se modifica.
"""
from __future__ import annotations

from .calendar import to_date

UNKNOWN_CATEGORY = "DESCONOCIDA"


def build_category_catalog(db, cutoff_date) -> dict[str, str]:
    cutoff = to_date(cutoff_date).isoformat()
    pipeline = [
        {"$match": {"fecha": {"$lte": cutoff}, "categoria_original": {"$ne": ""}}},
        {"$group": {"_id": {"sku": "$sku", "cat": "$categoria_original"},
                    "ultima": {"$max": "$fecha"}, "n": {"$sum": 1}}},
    ]
    best: dict[str, tuple] = {}
    for g in db.sales.aggregate(pipeline, allowDiskUse=True):
        sku, cat = g["_id"]["sku"], g["_id"]["cat"]
        # mayor fecha, luego mayor frecuencia, luego menor alfabetico
        rank = (g["ultima"], g["n"], _inv(cat))
        if sku not in best or rank > best[sku][0]:
            best[sku] = (rank, cat)
    return {sku: v[1] for sku, v in best.items()}


def _inv(text: str):
    # invierte el orden alfabetico para poder usar la comparacion mayor-gana
    return tuple(-ord(c) for c in text) + (1,)


def lookup(catalog: dict[str, str], sku: str) -> str:
    """SKU sin categoria entrenada -> DESCONOCIDA (sin reentrenar con el test)."""
    return catalog.get(str(sku), UNKNOWN_CATEGORY)
