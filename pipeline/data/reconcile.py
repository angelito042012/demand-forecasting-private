"""Conciliacion mensual de lo importado (T04).

Dos niveles que NO se mezclan:
  1. Por importacion (un archivo = un sha256; los no-op y las cargas fallidas no
     suman): leidas = aceptadas + rechazadas; aceptadas = insertadas + existentes
     + en_conflicto; y las lineas aceptadas sin conflicto tienen esa fuente en
     `sources` (persistencia verificada en la base).
  2. Conjunto logico unico del mes (ventas/creditos distintos en la base): su
     tamano debe estar entre el maximo y la suma de las lineas utiles de las
     importaciones del mes (el solapamiento de archivos lo reduce, nunca lo crea).
Nunca se compara la suma de filas de archivos solapados con entidades unicas.
Ventas, creditos, SKU y dias se calculan sobre sales/credit_notes. Los dias sin
registros se informan marcando los de EXCLUDED_DATES; nunca se rellenan con ceros.
"""
from __future__ import annotations

from decimal import Decimal

from .calendar import EXCLUDED_DATES, month_days

# Conteos de docs/AUDITORIA_DATOS.md (lineas positivas / negativas por mes).
AUDIT_EXPECTED = {
    "2026-03": {"ventas": 14456, "notas_credito": 89, "filas": 14545},
    "2026-04": {"ventas": 13907, "notas_credito": 72, "filas": 13979},
    "2026-05": {"ventas": 15380, "notas_credito": 78, "filas": 15458},
    "2026-06": {"ventas": 12510, "notas_credito": 81, "filas": 12591},
    "2026-07": {"ventas": 15678, "notas_credito": 112, "filas": 15790},
    "2026-08": {"ventas": 14946, "notas_credito": 128, "filas": 15074},
}


def _sum_dec(db, coll: str) -> dict:
    out = {}
    for g in db[coll].aggregate([{"$group": {"_id": "$mes", "s": {"$sum": "$importe"}}}]):
        out[g["_id"]] = g["s"].to_decimal()
    return out


def _persisted_by_source(db) -> dict:
    out: dict = {}
    for coll in ("sales", "credit_notes"):
        for g in db[coll].aggregate([{"$unwind": "$sources"},
                                     {"$group": {"_id": "$sources.source_sha256", "n": {"$sum": 1}}}],
                                    allowDiskUse=True):
            out[g["_id"]] = out.get(g["_id"], 0) + g["n"]
    return out


def reconcile(db) -> dict:
    months: dict[str, dict] = {}

    def slot(m):
        return months.setdefault(m, {"mes": m, "importaciones": [], "cargas_no_completadas": []})

    persisted = _persisted_by_source(db)
    done: dict[str, dict] = {}
    for imp in db.imports.find({"noop": {"$ne": True}}).sort("iniciado_utc", 1):
        if imp["estado"] in ("completed", "completed_with_conflicts"):
            done[imp["sha256"]] = imp  # la ultima ejecucion completada de cada fuente
    incompleto = {}
    for imp in db.imports.find({"estado": {"$in": ["failed", "running"]}, "noop": {"$ne": True}}):
        if imp["sha256"] not in done:
            incompleto[imp["sha256"]] = imp
    for imp in done.values():
        aceptadas = imp["ventas_aceptadas"] + imp["notas_credito"]
        conflicto = imp.get("en_conflicto", 0)
        util = aceptadas - conflicto
        slot(imp["mes"])["importaciones"].append({
            "archivo": imp["archivo"], "sha256": imp["sha256"], "estado": imp["estado"],
            "filas_leidas": imp["filas_leidas"], "ventas": imp["ventas_aceptadas"],
            "notas_credito": imp["notas_credito"], "rechazos": imp["rechazadas"],
            "rechazos_por_motivo": imp["rechazos_por_motivo"], "insertadas": imp["insertadas"],
            "ya_existentes": imp["ya_existentes"], "en_conflicto": conflicto,
            "lineas_utiles": util,
            "cuadra_lectura": imp["filas_leidas"] == aceptadas + imp["rechazadas"],
            "cuadra_escritura": imp["insertadas"] + imp["ya_existentes"] + conflicto == aceptadas,
            "persistidas_con_fuente": persisted.get(imp["sha256"], 0),
            "cuadra_persistencia": persisted.get(imp["sha256"], 0) == util,
        })
    for imp in incompleto.values():
        slot(imp["mes"])["cargas_no_completadas"].append(
            {"archivo": imp["archivo"], "sha256": imp["sha256"], "estado": imp["estado"],
             "error": imp.get("error")})

    sales_n, notes_n, skus, sale_days, note_days = {}, {}, {}, {}, {}
    for g in db.sales.aggregate([{"$group": {"_id": "$mes", "n": {"$sum": 1}, "d": {"$addToSet": "$fecha"},
                                             "s": {"$addToSet": "$sku"}}}], allowDiskUse=True):
        sales_n[g["_id"]], sale_days[g["_id"]], skus[g["_id"]] = g["n"], set(g["d"]), len(g["s"])
    for g in db.credit_notes.aggregate([{"$group": {"_id": "$mes", "n": {"$sum": 1},
                                                    "d": {"$addToSet": "$fecha"}}}]):
        notes_n[g["_id"]], note_days[g["_id"]] = g["n"], set(g["d"])
    sales_sum, notes_sum = _sum_dec(db, "sales"), _sum_dec(db, "credit_notes")
    excluded = {x.isoformat() for x in EXCLUDED_DATES}

    for m in set(months) | set(sales_n) | set(notes_n):
        s = slot(m)
        year, mon = int(m[:4]), int(m[5:])
        with_records = sale_days.get(m, set()) | note_days.get(m, set())
        cal = [d.isoformat() for d in month_days(year, mon)]
        missing = [d for d in cal if d not in with_records]
        vs, cs = sales_sum.get(m, Decimal(0)), notes_sum.get(m, Decimal(0))
        uniq = sales_n.get(m, 0) + notes_n.get(m, 0)
        utiles = [i["lineas_utiles"] for i in s["importaciones"]]
        s.update({
            "ventas": sales_n.get(m, 0), "notas_credito": notes_n.get(m, 0),
            "sku_con_ventas": skus.get(m, 0),
            "dias_calendario": len(cal), "dias_con_registros": len(with_records),
            "dias_sin_registros": missing,
            "dias_sin_registros_excluidos": [d for d in missing if d in excluded],
            "dias_sin_registros_no_excluidos": [d for d in missing if d not in excluded],
            "suma_importe_ventas": f"{vs:.2f}", "suma_importe_creditos": f"{cs:.2f}",
            "saldo_neto": f"{vs + cs:.2f}",  # creditos son negativos
            "cuadra_importaciones": bool(s["importaciones"]) and all(i["cuadra_lectura"] and i["cuadra_escritura"]
                                        and i["cuadra_persistencia"] for i in s["importaciones"]),
            "cuadra_conjunto_logico": bool(utiles) and max(utiles) <= uniq <= sum(utiles),
        })
    return {k: months[k] for k in sorted(months)}


def compare_with_audit(result: dict) -> dict:
    """Diferencias vs AUDIT_EXPECTED (vacio si coinciden). No fuerza conteos.

    Solo compara meses con una unica fuente; con varias fuentes la auditoria
    (un archivo por mes) no es aplicable y se informa 'multiples_fuentes'."""
    diffs = {}
    for m, exp in AUDIT_EXPECTED.items():
        imps = result.get(m, {}).get("importaciones", [])
        if len(imps) != 1:
            diffs[m] = {"fuentes": {"esperado": 1, "obtenido": len(imps)}}
            continue
        got = {"ventas": imps[0]["ventas"], "notas_credito": imps[0]["notas_credito"],
               "filas": imps[0]["filas_leidas"]}
        d = {k: {"esperado": v, "obtenido": got[k]} for k, v in exp.items() if got[k] != v}
        if d:
            diffs[m] = d
    return diffs
