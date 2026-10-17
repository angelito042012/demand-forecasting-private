"""Aprobacion de fuentes para la ruta de datos de entrenamiento (R04).

Una venta persistida solo es elegible si al menos una de sus fuentes (`sources`)
esta APROBADA: existe una importacion `completed` (no no-op) de ese sha256 y no
quedan conflictos OPEN de esa fuente. Las lineas cuya unica fuente es una carga
fallida/parcial, no reconocida o con conflicto abierto NO entran en silencio:
`evaluate_sources` informa los problemas y `require_approved_sources` detiene la
construccion del dataset con SourceApprovalError. Un reintento completo agrega la
fuente aprobada a las mismas lineas (upsert por linea_id), de modo que cada linea
se usa una sola vez.

Solo se evaluan fuentes/meses <= mes del corte: registros o cargas fallidas
posteriores al corte no cambian un conjunto ya aprobado. Los meses requeridos
(por defecto marzo 2026 hasta el mes del corte) deben tener una fuente aprobada;
la ausencia de importaciones NUNCA cuenta como aprobacion.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .calendar import to_date

FIRST_REQUIRED_MONTH = "2026-03"


class SourceApprovalError(ValueError):
    """Fuentes incompletas, no aprobadas o con conflictos para el corte pedido."""

    def __init__(self, issues: list[dict]):
        self.issues = issues
        super().__init__("fuentes no aprobadas para el corte: " + "; ".join(
            f"{i['codigo']}({i.get('detalle', '')})" for i in issues[:6]))


@dataclass(frozen=True)
class SourceReport:
    cutoff: str
    required_months: tuple
    approved_shas: tuple      # ordenado
    manifest: tuple           # dicts (mes, archivo, sha256) ordenados por mes/sha
    issues: tuple             # dicts {codigo, detalle, ...}; vacio = aprobado

    @property
    def ok(self) -> bool:
        return not self.issues


def default_required_months(cutoff) -> tuple:
    last = to_date(cutoff)
    y, m = int(FIRST_REQUIRED_MONTH[:4]), int(FIRST_REQUIRED_MONTH[5:])
    out = []
    while (y, m) <= (last.year, last.month):
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return tuple(out)


def approved_sources(db) -> dict:
    """sha256 -> importacion completada, sin conflictos OPEN de esa fuente."""
    open_shas = set(db.import_conflicts.distinct("source_sha256", {"estado": "OPEN"}))
    out: dict = {}
    for imp in db.imports.find({"estado": "completed", "noop": {"$ne": True}}).sort("iniciado_utc", 1):
        if imp["sha256"] not in open_shas:
            out[imp["sha256"]] = imp
    return out


def evaluate_sources(db, cutoff, *, required_months=None, collection: str = "sales") -> SourceReport:
    last = to_date(cutoff)
    cutoff_iso, cutoff_month = last.isoformat(), last.strftime("%Y-%m")
    required = tuple(default_required_months(last) if required_months is None else required_months)
    approved = approved_sources(db)
    shas = tuple(sorted(approved))
    issues: list[dict] = []

    if not shas:
        issues.append({"codigo": "SIN_FUENTES_APROBADAS", "detalle": "ninguna importacion completada"})
    covered = {approved[s]["mes"] for s in shas}
    for m in required:
        if m not in covered:
            issues.append({"codigo": "MES_SIN_FUENTE_APROBADA", "detalle": m, "mes": m})

    seen = set()
    for imp in db.imports.find({"estado": {"$in": ["failed", "running", "completed_with_conflicts"]},
                                "noop": {"$ne": True}, "mes": {"$lte": cutoff_month}}):
        if imp["sha256"] in approved or imp["sha256"] in seen:
            continue
        seen.add(imp["sha256"])
        issues.append({"codigo": "CARGA_NO_COMPLETADA", "detalle": f"{imp['archivo']}:{imp['estado']}",
                       "mes": imp["mes"], "sha256": imp["sha256"], "estado": imp["estado"]})

    for c in db.import_conflicts.find({"estado": "OPEN", "coleccion": collection}):
        if any(x["fecha"] <= cutoff_iso for x in c.get("lineas_nuevas", [])):
            issues.append({"codigo": "CONFLICTO_ABIERTO", "detalle": c["conflict_id"][:12],
                           "sha256": c["source_sha256"]})

    n_bad = db[collection].count_documents(
        {"fecha": {"$lte": cutoff_iso}, "sources.source_sha256": {"$nin": list(shas)}})
    if n_bad:
        by_src = {g["_id"]: g["n"] for g in db[collection].aggregate([
            {"$match": {"fecha": {"$lte": cutoff_iso}, "sources.source_sha256": {"$nin": list(shas)}}},
            {"$group": {"_id": {"$ifNull": [{"$arrayElemAt": ["$sources.source_sha256", 0]}, "SIN_FUENTE"]},
                        "n": {"$sum": 1}}}])}
        issues.append({"codigo": "LINEAS_SIN_FUENTE_APROBADA", "detalle": f"{n_bad} lineas",
                       "n": n_bad, "por_fuente": by_src})

    manifest = tuple(sorted(({"mes": approved[s]["mes"], "archivo": approved[s]["archivo"], "sha256": s}
                             for s in shas if approved[s]["mes"] <= cutoff_month),
                            key=lambda d: (d["mes"], d["sha256"])))
    return SourceReport(cutoff=cutoff_iso, required_months=required, approved_shas=shas,
                        manifest=manifest, issues=tuple(issues))


def require_approved_sources(db, cutoff, *, required_months=None, collection: str = "sales") -> SourceReport:
    report = evaluate_sources(db, cutoff, required_months=required_months, collection=collection)
    if not report.ok:
        raise SourceApprovalError(list(report.issues))
    return report


def approved_filter(report: SourceReport) -> dict:
    """Fragmento de consulta MongoDB: solo lineas con alguna fuente aprobada."""
    return {"sources.source_sha256": {"$in": list(report.approved_shas)}}
