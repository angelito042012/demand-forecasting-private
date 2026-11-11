"""Repositorios de lectura de ventas observadas e importaciones (T08 §3).

- Ventas: solo fecha <= 2026-09-30 y fuentes aprobadas (pipeline.data.sources); los dias de
  la mascara (03/04, 12/04, 07/06) no se suman ni se convierten en ceros: se listan aparte.
- Importaciones: sin filas ni datos de clientes; rechazos solo como conteos por motivo.
"""
from __future__ import annotations

import os
from datetime import date
from decimal import Decimal

from bson.decimal128 import Decimal128

from backend.app.errors import ApiError, page_response
from pipeline.data.calendar import EXCLUDED_DATES
from pipeline.data.sources import approved_sources

from .common import LAST_ALLOWED_DATE, check_dates, iso_utc

RESERVED_FROM_MONTH = "2026-10"
_COUNT_FIELDS = ("filas_leidas", "ventas_aceptadas", "notas_credito", "rechazadas", "insertadas",
                 "ya_existentes", "en_conflicto")
DEFAULT_FROM = date(2026, 1, 1)


def _list_item(d: dict) -> dict:
    reserved = d["mes"] >= RESERVED_FROM_MONTH
    item = {"import_id": d["import_id"], "archivo": os.path.basename(str(d.get("archivo", ""))),
            "mes": d["mes"], "estado": d["estado"],
            **{f: (None if reserved else d.get(f)) for f in _COUNT_FIELDS},
            "iniciado_utc": iso_utc(d.get("iniciado_utc")), "finalizado_utc": iso_utc(d.get("finalizado_utc")),
            "reservado_prueba_final": reserved}
    return item


_VISIBLE = {"noop": {"$ne": True}, "dry_run": {"$ne": True}}


def list_imports(db, mes: str | None, page: int, page_size: int) -> dict:
    q: dict = {**_VISIBLE}
    if mes:
        q["mes"] = mes
    total = db.imports.count_documents(q)
    docs = list(db.imports.find(q, {"_id": 0}).sort([("mes", 1), ("iniciado_utc", 1)])
                .skip((page - 1) * page_size).limit(page_size))
    return page_response([_list_item(d) for d in docs], total, page, page_size)


def get_import(db, import_id: str) -> dict:
    d = db.imports.find_one({"import_id": import_id, **_VISIBLE}, {"_id": 0})
    if d is None:
        raise ApiError(404, "NO_ENCONTRADO", "Importación no encontrada.")
    out = _list_item(d)
    reserved = out["reservado_prueba_final"]
    sha = str(d.get("sha256", ""))
    by_reason = {} if reserved else {str(k): int(v) for k, v in (d.get("rechazos_por_motivo") or {}).items()}
    if not reserved and not by_reason and d.get("rechazadas"):
        by_reason = {str(g["_id"]): int(g["n"]) for g in db.import_rejects.aggregate([
            {"$match": {"source_sha256": sha}}, {"$group": {"_id": "$motivo", "n": {"$sum": 1}}}])}
    open_conf = 0 if reserved else db.import_conflicts.count_documents({"source_sha256": sha, "estado": "OPEN"})
    incid = [{"codigo": f"RECHAZO_{k}", "n": v} for k, v in sorted(by_reason.items())]
    if open_conf:
        incid.append({"codigo": "CONFLICTO_ABIERTO", "n": open_conf})
    if d.get("estado") != "completed":
        incid.append({"codigo": f"ESTADO_{str(d.get('estado')).upper()}", "n": 1})
    out.update({"rechazos_por_motivo": by_reason, "conflictos_abiertos": open_conf,
                "sha256_abreviado": sha[:12], "incidencias": incid})
    return out


def _num(v) -> float:
    if isinstance(v, Decimal128):
        v = v.to_decimal()
    if isinstance(v, Decimal):
        return float(round(v, 2))
    return round(float(v or 0), 2)


def sales_summary(db, frm: date | None, to: date | None, group_by: str, categoria: str | None) -> dict:
    check_dates(frm, to)
    frm = frm or DEFAULT_FROM
    to = to or LAST_ALLOWED_DATE
    if frm > to:
        raise ApiError(422, "ENTRADA_INVALIDA", "El rango de fechas es inválido (from > to).")
    if (to - frm).days > 400:
        raise ApiError(422, "ENTRADA_INVALIDA", "El rango máximo es de 400 días.")
    shas = sorted(approved_sources(db))
    approved = {"sources.source_sha256": {"$in": shas}}   # mismo criterio que sources.approved_filter
    excluded = sorted(d.isoformat() for d in EXCLUDED_DATES if frm <= d <= to)
    match: dict = {"fecha": {"$gte": frm.isoformat(), "$lte": to.isoformat(), "$nin": excluded}, **approved}
    if categoria:
        match["categoria_original"] = categoria
    key = {"day": "$fecha", "month": {"$substrBytes": ["$fecha", 0, 7]},
           "category": "$categoria_original"}[group_by]
    rows = list(db.sales.aggregate([
        {"$match": match},
        {"$group": {"_id": key, "lineas": {"$sum": 1}, "unidades": {"$sum": "$cantidad_base"},
                    "importe": {"$sum": "$importe"}}},
        {"$sort": {"_id": 1}}], allowDiskUse=True))
    cn_match = {**match}
    cn = list(db.credit_notes.aggregate([
        {"$match": cn_match}, {"$group": {"_id": None, "lineas": {"$sum": 1}, "importe": {"$sum": "$importe"}}}]))
    return {
        "provenance": "OBSERVED_EXCEL", "unit": "unidad base", "currency": "PEN",
        "from": frm.isoformat(), "to": to.isoformat(), "group_by": group_by,
        "items": [{"key": str(r["_id"]), "lineas_venta": int(r["lineas"]), "unidades": _num(r["unidades"]),
                   "importe_pen": _num(r["importe"])} for r in rows],
        "notas_credito": {"lineas": int(cn[0]["lineas"]) if cn else 0,
                          "importe_pen": _num(cn[0]["importe"]) if cn else 0.0,
                          "nota": "Se informan aparte, con el signo almacenado; no se restan de las ventas."},
        "excluded_days": [{"fecha": d, "motivo": "excluido del entrenamiento y métricas; no se informa como venta cero"}
                          for d in excluded],
        "fuentes_aprobadas": len(shas),
    }
