"""R11: reconcilia el estado de un paquete T12 ya calculado ejecutando SOLO auditoria y reporte sobre los artefactos
guardados. No prepara, no lee agosto, no entrena ni simula. Registra una correccion tecnica POSTERIOR con el commit base
real y comprueba que los hashes de la ejecucion original no cambian (no se inventan fechas de fases ausentes)."""
from __future__ import annotations

from pathlib import Path

from pipeline.final.audit import run_audit
from pipeline.final.frozen import ROOT
from pipeline.final.report import write_report
from pipeline.final.runner import FinalGateError, StateFile, sha_bytes

ORIGINAL_ARTIFACTS = ("preparacion/predicciones_fijas.npz", "preparacion/inicializacion_sim.npz",
                      "preparacion/rf_categoria_T12.joblib", "preparacion/manifiesto_preparacion.json", "reales_bloque.npz",
                      "ventas_agosto_min.csv.gz", "predictivo.json", "simulacion.json", "simulacion_series.npz")


def reconcile(out: Path, docs: Path = ROOT / "docs", *, motivo: str = "R11: registrar las fases auditoria y reporte") -> dict:
    out = Path(out)
    store = StateFile(out)
    missing = [p for p in ("auditoria", "reporte") if store.done(p)]
    before = {n: sha_bytes(out / n) for n in ORIGINAL_ARTIFACTS}
    original_phases = {k: dict(v) for k, v in store.state["fases"].items() if k not in ("auditoria", "reporte")}
    store.correction(motivo, fases_registradas_a_posteriori=["auditoria", "reporte"],
                     ya_completas_antes=missing, hashes_originales_conservados=before,
                     nota="Correccion tecnica posterior: las fases originales conservan sus fechas e intentos; "
                          "no se repitieron prepare, lectura de agosto, evaluacion ni simulacion.")
    aud = run_audit(out)
    if not aud["ok"]:
        raise FinalGateError("la auditoria no aprobo durante la reconciliacion")
    write_report(out, docs=docs)
    after = {n: sha_bytes(out / n) for n in ORIGINAL_ARTIFACTS}
    if after != before:
        raise FinalGateError("los hashes originales cambiaron durante la reconciliacion")
    store = StateFile(out)
    if {k: v for k, v in store.state["fases"].items() if k in original_phases} != original_phases:
        raise FinalGateError("las fases originales fueron modificadas")
    store.event("reconciliacion", "auditoria y reporte registrados; hashes originales y fases de calculo sin cambios")
    return {"completa": store.state["completa"], "hashes_originales_iguales": True}
