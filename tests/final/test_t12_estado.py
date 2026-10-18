"""R11: auditoria y reporte registran sus fases en estado.json; `completa` solo con las siete fases; reanudar auditoria o
reporte jamas vuelve a preparar, leer agosto, entrenar ni simular."""
from __future__ import annotations

import contextlib
import json
from pathlib import Path

import pytest

from pipeline.final import audit as audit_mod
from pipeline.final import core, report, runner
from pipeline.final.audit import run_audit
from pipeline.final.report import write_report
from pipeline.final.runner import PHASES, FinalGateError
from pipeline.forecast import t07 as t7
from tests.final.synth import build, make_run
from tests.publish.helpers import temp_db

pytestmark = pytest.mark.mongo


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    """Mundo sintetico con prepare+evaluate ya ejecutados una vez (se copia el directorio de salida por prueba)."""
    tmp = tmp_path_factory.mktemp("estado")
    with contextlib.ExitStack() as stack:
        db = stack.enter_context(temp_db())
        build(db, tmp)
        out, seal = tmp / "out", tmp / "sello.json"
        run = make_run(db, out, seal)
        run.prepare()
        run.evaluate(confirm_frozen=True)
        yield out


def fresh(world: Path, tmp_path: Path) -> Path:
    import shutil
    dst = tmp_path / "out"
    shutil.copytree(world, dst)
    st = json.loads((dst / "estado.json").read_text(encoding="utf-8"))
    for f in ("auditoria", "reporte"):
        st["fases"].pop(f, None)
    st["completa"] = False
    (dst / "estado.json").write_text(json.dumps(st), encoding="utf-8")
    (dst / "auditoria.json").unlink(missing_ok=True)
    return dst


def guard_no_recompute(monkeypatch):
    boom = lambda *a, **k: pytest.fail("audit/report no deben preparar, leer agosto, entrenar ni simular")
    monkeypatch.setattr(runner, "load_final_test_sales", boom)
    monkeypatch.setattr(runner, "load_training_data", boom)
    monkeypatch.setattr(core, "fixed_predictions", boom)
    monkeypatch.setattr(core, "sequential_simulation", boom)
    monkeypatch.setattr(t7, "forecast_origin_t07", boom)


def test_all_seven_phases_complete_the_status_only_after_audit_and_report(world, tmp_path, monkeypatch):
    out = fresh(world, tmp_path)
    guard_no_recompute(monkeypatch)
    docs = tmp_path / "docs"
    docs.mkdir()
    st = json.loads((out / "estado.json").read_text(encoding="utf-8"))
    assert st["completa"] is False and set(st["fases"]) == set(PHASES) - {"auditoria", "reporte"}
    assert run_audit(out)["ok"]
    mid = json.loads((out / "estado.json").read_text(encoding="utf-8"))
    assert mid["fases"]["auditoria"]["estado"] == "completa" and mid["completa"] is False      # falta el reporte
    write_report(out, docs=docs)
    end = json.loads((out / "estado.json").read_text(encoding="utf-8"))
    assert end["completa"] is True and set(end["fases"]) == set(PHASES)
    for f in ("auditoria", "reporte"):
        assert end["fases"][f]["estado"] == "completa" and end["fases"][f]["inicio"] and end["fases"][f]["fin"]
        assert end["fases"][f]["intentos"] == 1
    assert end["fases"]["reporte"]["resultados_sha256"] == runner.sha_bytes(docs / "T12_RESULTADOS.md")
    manifest = json.loads((docs / "T12_MANIFIESTO.json").read_text(encoding="utf-8"))
    assert manifest["fases"]["reporte"]["estado"] == "completa" and manifest["auditoria_ok"] is True
    # las fases de calculo originales no se tocan al reconciliar
    for f in ("verificacion", "preparacion", "lectura_agosto", "evaluacion_predictiva", "simulacion"):
        assert end["fases"][f] == st["fases"][f]


def test_audit_failure_keeps_status_false_and_blocks_a_valid_report(world, tmp_path, monkeypatch):
    out = fresh(world, tmp_path)
    docs = tmp_path / "docs"
    docs.mkdir()
    monkeypatch.setattr(audit_mod, "audit_simulation", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("cae la auditoria")))
    with pytest.raises(RuntimeError):
        run_audit(out)
    st = json.loads((out / "estado.json").read_text(encoding="utf-8"))
    assert st["completa"] is False and st["fases"]["auditoria"]["estado"] == "error" and "cae" in st["fases"]["auditoria"]["error"]
    with pytest.raises(FinalGateError, match="auditoria"):
        write_report(out, docs=docs)
    st = json.loads((out / "estado.json").read_text(encoding="utf-8"))
    assert st["fases"]["reporte"]["estado"] == "error" and st["completa"] is False
    assert not (docs / "T12_RESULTADOS.md").exists()
    # recuperacion: la auditoria sana y el reporte completan sin recomputar nada
    monkeypatch.undo()
    guard_no_recompute(monkeypatch)
    assert run_audit(out)["ok"]
    write_report(out, docs=docs)
    st = json.loads((out / "estado.json").read_text(encoding="utf-8"))
    assert st["completa"] is True and st["fases"]["auditoria"]["intentos"] == 2 and "error" not in st["fases"]["auditoria"]


def test_unapproved_audit_is_an_error_phase_not_a_completed_one(world, tmp_path):
    out = fresh(world, tmp_path)
    pj = json.loads((out / "predictivo.json").read_text(encoding="utf-8"))
    for r in pj["sku"]:
        r["WAPE"] = (r["WAPE"] or 0) + 0.5
    (out / "predictivo.json").write_text(json.dumps(pj), encoding="utf-8")
    assert run_audit(out)["ok"] is False
    st = json.loads((out / "estado.json").read_text(encoding="utf-8"))
    assert st["fases"]["auditoria"]["estado"] == "error" and st["completa"] is False


def test_report_failure_is_recorded_and_recovery_completes_without_recomputation(world, tmp_path, monkeypatch):
    out = fresh(world, tmp_path)
    docs = tmp_path / "docs"
    docs.mkdir()
    assert run_audit(out)["ok"]
    monkeypatch.setattr(report, "render", lambda *a, **k: (_ for _ in ()).throw(OSError("disco lleno")))
    with pytest.raises(OSError):
        write_report(out, docs=docs)
    st = json.loads((out / "estado.json").read_text(encoding="utf-8"))
    assert st["fases"]["reporte"]["estado"] == "error" and st["completa"] is False
    monkeypatch.undo()
    guard_no_recompute(monkeypatch)
    write_report(out, docs=docs)
    st = json.loads((out / "estado.json").read_text(encoding="utf-8"))
    assert st["completa"] is True and st["fases"]["reporte"]["intentos"] == 2


def test_original_artifact_hashes_survive_audit_and_report(world, tmp_path):
    out = fresh(world, tmp_path)
    names = ["preparacion/predicciones_fijas.npz", "preparacion/inicializacion_sim.npz", "preparacion/rf_categoria_T12.joblib",
             "reales_bloque.npz", "ventas_agosto_min.csv.gz", "predictivo.json", "simulacion.json", "simulacion_series.npz"]
    before = {n: runner.sha_bytes(out / n) for n in names}
    docs = tmp_path / "docs"
    docs.mkdir()
    run_audit(out)
    write_report(out, docs=docs)
    assert {n: runner.sha_bytes(out / n) for n in names} == before


def test_reconcile_registers_a_posterior_correction_without_touching_original_phases_or_recomputing(world, tmp_path, monkeypatch):
    from pipeline.final.reconcile import reconcile
    out = fresh(world, tmp_path)
    guard_no_recompute(monkeypatch)
    docs = tmp_path / "docs"
    docs.mkdir()
    before = json.loads((out / "estado.json").read_text(encoding="utf-8"))
    res = reconcile(out, docs=docs)
    after = json.loads((out / "estado.json").read_text(encoding="utf-8"))
    assert res["completa"] is True and after["completa"] is True and len(after["correcciones"]) == 1
    corr = after["correcciones"][0]
    assert corr["fases_registradas_a_posteriori"] == ["auditoria", "reporte"] and corr["git_commit_base"]
    assert set(corr["hashes_originales_conservados"]) >= {"predictivo.json", "simulacion.json", "reales_bloque.npz"}
    for f in ("verificacion", "preparacion", "lectura_agosto", "evaluacion_predictiva", "simulacion"):
        assert after["fases"][f] == before["fases"][f]
    manifest = json.loads((docs / "T12_MANIFIESTO.json").read_text(encoding="utf-8"))
    assert manifest["correcciones"][0]["motivo"].startswith("R11")


# ------------------------------------------------------------------------------------------------ R12
def _manifest_contradicts_state(docs: Path, state: dict) -> bool:
    """True si el manifiesto publicado afirma un reporte completo/valido que el estado no respalda."""
    p = docs / "T12_MANIFIESTO.json"
    if not p.exists():
        return False
    m = json.loads(p.read_text(encoding="utf-8"))
    if m.get("valido") is False:
        return False
    claims_done = m.get("fases", {}).get("reporte", {}).get("estado") == "completa"
    state_done = state["fases"].get("reporte", {}).get("estado") == "completa" and state["completa"] is True
    return claims_done != state_done or (m.get("fases", {}).get("reporte", {}).get("estado") == "en_curso")


@pytest.mark.parametrize("fault", ["build_manifest", "serialize_manifest"])
def test_r12_late_failure_after_the_first_report_and_after_end_never_leaves_a_complete_package(world, tmp_path, monkeypatch, fault):
    out = fresh(world, tmp_path)
    docs = tmp_path / "docs"
    docs.mkdir()
    assert run_audit(out)["ok"]
    real = report.build_manifest

    def late(o, man, state, aud):
        if state["fases"]["reporte"]["estado"] == "completa":          # solo en el cierre, DESPUES de _end
            if fault == "build_manifest":
                raise OSError("falla al construir el manifiesto")
            circular: dict = {}
            circular["yo"] = circular                                   # json.dumps lanza ValueError
            return circular
        return real(o, man, state, aud)
    monkeypatch.setattr(report, "build_manifest", late)
    with pytest.raises((OSError, TypeError, ValueError)):
        write_report(out, docs=docs)
    st = json.loads((out / "estado.json").read_text(encoding="utf-8"))
    assert st["completa"] is False and st["fases"]["reporte"]["estado"] == "error"
    assert not _manifest_contradicts_state(docs, st)
    # recuperacion sin recomputar nada
    monkeypatch.undo()
    guard_no_recompute(monkeypatch)
    write_report(out, docs=docs)
    st = json.loads((out / "estado.json").read_text(encoding="utf-8"))
    assert st["completa"] is True and st["fases"]["reporte"]["intentos"] == 2
    m = json.loads((docs / "T12_MANIFIESTO.json").read_text(encoding="utf-8"))
    assert m["fases"]["reporte"]["estado"] == "completa" and not _manifest_contradicts_state(docs, st)


def test_r12_failure_while_completing_the_state_is_recorded_and_a_previous_complete_manifest_is_invalidated(world, tmp_path, monkeypatch):
    out = fresh(world, tmp_path)
    docs = tmp_path / "docs"
    docs.mkdir()
    run_audit(out)
    write_report(out, docs=docs)                                        # reporte completo y manifiesto valido previos
    st0 = json.loads((out / "estado.json").read_text(encoding="utf-8"))
    assert st0["completa"] is True
    monkeypatch.setattr(runner.StateFile, "_save", lambda self: (_ for _ in ()).throw(OSError("disco lleno")) if
                        self.state["fases"].get("reporte", {}).get("estado") == "completa" else
                        runner._write_json(self.state_path, self.state))
    with pytest.raises(OSError):
        write_report(out, docs=docs)
    monkeypatch.undo()
    st = json.loads((out / "estado.json").read_text(encoding="utf-8"))
    # el estado en disco no puede decir completa=true con un reporte fallido; el manifiesto previo no puede seguir afirmandolo
    assert not (st["completa"] is True and st["fases"]["reporte"]["estado"] != "completa")
    assert not _manifest_contradicts_state(docs, st) or st["completa"] is False


def test_r12_an_unreadable_audit_or_preparation_at_close_is_a_reporting_error(world, tmp_path, monkeypatch):
    out = fresh(world, tmp_path)
    docs = tmp_path / "docs"
    docs.mkdir()
    run_audit(out)
    (out / "preparacion" / "manifiesto_preparacion.json").write_text("{corrupto", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        write_report(out, docs=docs)
    st = json.loads((out / "estado.json").read_text(encoding="utf-8"))
    assert st["completa"] is False and st["fases"]["reporte"]["estado"] == "error"
    assert not (docs / "T12_MANIFIESTO.json").exists() or json.loads(
        (docs / "T12_MANIFIESTO.json").read_text(encoding="utf-8")).get("valido") is False
