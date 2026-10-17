"""Catalogo de categoria por SKU versionado por fecha de corte (DECISIONES_DATOS.md).

Regla: categoria mas reciente conocida con fecha <= corte (solo ventas de
entrenamiento); empate de fecha -> mayor frecuencia (<= corte) -> orden alfabetico.
categoria_original de cada transaccion no se modifica.
"""
from __future__ import annotations

from .calendar import to_date

UNKNOWN_CATEGORY = "DESCONOCIDA"


def build_category_catalog(db, cutoff_date, *, source_filter: dict | None = None, start=None,
                           excluded_dates=()) -> dict[str, str]:
    """`source_filter` (sources.approved_filter) aplica a las categorias la misma seleccion
    de fuentes aprobadas que a las ventas (R04)."""
    cutoff = to_date(cutoff_date).isoformat()
    dates = {"$lte": cutoff}
    if start is not None:
        dates["$gte"] = to_date(start).isoformat()
    if excluded_dates:  # misma mascara que la seleccion de ventas: un dia excluido no aporta categoria
        dates["$nin"] = sorted(to_date(d).isoformat() for d in excluded_dates)
    match = {"fecha": dates, "categoria_original": {"$ne": ""}, **(source_filter or {})}
    pipeline = [
        {"$match": match},
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
