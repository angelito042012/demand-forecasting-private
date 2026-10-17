"""T12: pruebas SINTETICAS de la evaluacion final (base temporal df_test_*; nunca datos reales ni agosto real)."""
from __future__ import annotations

import json
import shutil
from datetime import date

import numpy as np
import pytest

from pipeline.data.calendar import EXCLUDED_DATES
from pipeline.data.training_access import TrainingCutoffError, load_final_test_sales
from pipeline.final import core, frozen, runner
from pipeline.final.audit import run_audit
from pipeline.final.frozen import FreezeError, load_frozen_engine, verify_freeze
from pipeline.final.report import primary_reading, write_report
from pipeline.final.runner import FinalGateError, _load_npz
from pipeline.forecast import t07 as t7
from tests.final.synth import build, make_run
from tests.publish.helpers import temp_db

mongo = pytest.mark.mongo


# ------------------------------------------------------------------------------------------ congelacion
def test_freeze_verification_passes_on_the_committed_selection():
    rep = verify_freeze()
    assert rep["ok"] and not rep["errores"]
    assert set(rep["no_coinciden_vivo_y_motivo"]) <= {"pipeline/data/importer.py", "pipeline/sim/engine.py"}
    assert rep["comprobaciones"]["motor_congelado_copia"]["ok"]


def test_altered_frozen_json_or_engine_copy_blocks(tmp_path, monkeypatch):
    alt = tmp_path / "seleccion_congelada.json"
    alt.write_text(frozen.FROZEN_JSON.read_text(encoding="utf-8").replace("promedio_28", "otro_metodo", 1), encoding="utf-8")
    monkeypatch.setattr(frozen, "FROZEN_JSON", alt)
    with pytest.raises(FreezeError, match="json_congelado"):
        verify_freeze()
    monkeypatch.undo()
    bad_engine = tmp_path / "engine.py"
    bad_engine.write_text(frozen.FROZEN_ENGINE_COPY.read_text(encoding="utf-8") + "\n# alterado\n", encoding="utf-8")
    monkeypatch.setattr(frozen, "FROZEN_ENGINE_COPY", bad_engine)
    with pytest.raises(FreezeError):
        load_frozen_engine()


def test_frozen_engine_is_equation_equivalent_to_the_live_hardened_engine():
    """El motor vivo solo agrego validaciones: mismas ecuaciones y resultados que la copia congelada."""
    from pipeline.sim import engine as live
    frozen_engine = load_frozen_engine()
    rng = np.random.default_rng(7)
    demand = rng.integers(0, 6, size=(40, 31)).astype(float)
    demand[:, 9] = np.nan
    cost = rng.uniform(1, 9, 40)
    mean = rng.uniform(0, 4, 40)
    review = frozen_engine.review_indices(31, 7)
    for L in (3, 7, 14):
        stock0 = frozen_engine.ceil_stable(mean * (L + 7))
        tg = {j: frozen_engine.ceil_stable(mean * (L + 14) + j) for j in review}
        a = frozen_engine.simulate(demand, review, tg, L, stock0, cost, 0.2, 365)
        b = live.simulate(demand, review, tg, L, stock0, cost, 0.2, 365)
        for name in ("on_hand", "served", "lost", "received", "ordered", "pipeline_end", "stock0"):
            assert np.array_equal(getattr(a, name), getattr(b, name))
        assert frozen_engine.metrics(a, demand, cost) == live.metrics(b, demand, cost)


def test_load_final_test_sales_still_requires_explicit_confirmation():
    with pytest.raises(TrainingCutoffError):
        load_final_test_sales(None, frozen_selection_confirmed=False)
    with pytest.raises(TrainingCutoffError):
        load_final_test_sales(None, frozen_selection_confirmed="si")


# ------------------------------------------------------------------------------------------ puertas
@mongo
def test_evaluate_is_blocked_without_confirmation_without_preparation_and_without_committed_seal(tmp_path, monkeypatch):
    with temp_db() as db:
        build(db, tmp_path)
        monkeypatch.setattr(runner, "load_final_test_sales", lambda *a, **k: pytest.fail("no debe leer agosto"))
        run = make_run(db, tmp_path / "out", tmp_path / "sello.json")
        with pytest.raises(FinalGateError, match="confirmacion"):
            run.evaluate(confirm_frozen=False)
        with pytest.raises(FinalGateError, match="preparacion"):
            run.evaluate(confirm_frozen=True)
        run.prepare()                                         # el sello existe pero NO esta commiteado
        strict = runner.FinalRun(db, tmp_path / "out", seal_path=tmp_path / "sello.json", require_commit=True)
        with pytest.raises(FinalGateError):
            strict.evaluate(confirm_frozen=True)
        assert "lectura_agosto" not in strict.state["fases"] or strict.state["fases"]["lectura_agosto"].get("estado") != "completa"


@mongo
def test_tampered_seal_or_artifact_blocks_before_reading_august(tmp_path, monkeypatch):
    with temp_db() as db:
        build(db, tmp_path)
        run = make_run(db, tmp_path / "out", tmp_path / "sello.json")
        run.prepare()
        monkeypatch.setattr(runner, "load_final_test_sales", lambda *a, **k: pytest.fail("no debe leer agosto"))
        npz = tmp_path / "out" / "preparacion" / "predicciones_fijas.npz"
        arr = _load_npz(npz)
        arr["pred_sku_promedio_28"] = arr["pred_sku_promedio_28"] + 1.0         # alguien "retoca" la prediccion sellada
        np.savez(npz, **arr)
        with pytest.raises(FinalGateError, match="distinto del sellado"):
            make_run(db, tmp_path / "out", tmp_path / "sello.json").evaluate(confirm_frozen=True)


# ------------------------------------------------------------------------------------------ preparacion
@mongo
def test_future_data_does_not_change_the_sealed_package_and_prepare_never_reads_august(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "load_final_test_sales", lambda *a, **k: pytest.fail("prepare no debe leer agosto"))
    sigs = []
    for k, scale in enumerate((1, 9)):
        with temp_db() as db:
            d = tmp_path / f"w{k}"
            d.mkdir()
            build(db, d, aug_scale=scale)
            run = make_run(db, tmp_path / f"out{k}", tmp_path / f"sello{k}.json")
            man = run.prepare()
            assert man["agosto_consultado"] is False
            sigs.append((man["archivos"]["predicciones_fijas.npz"]["logical_sha256"],
                         man["archivos"]["inicializacion_sim.npz"]["logical_sha256"], man["info"],
                         man["filas_entrenamiento"]))
    # contenido logico identico (los xlsx difieren en bytes por metadatos de openpyxl, por eso no se compara el fingerprint
    # de fuentes): solo cambian las cantidades de agosto
    assert sigs[0] == sigs[1]


@mongo
def test_sealed_universe_catalog_and_cohorts_are_known_at_31_july(tmp_path):
    with temp_db() as db:
        build(db, tmp_path)
        run = make_run(db, tmp_path / "out", tmp_path / "sello.json")
        run.prepare()
        _, fixed, sim_in = run._load_sealed()
        keys = list(fixed["sku_keys"])
        assert "9100020|1" not in keys                          # SKU nuevo (1a venta 05/08): fuera del universo
        i12 = keys.index("9100012|1")
        assert fixed["sku_cats"][i12] == "CAT A"               # catalogo al 31/07: agosto no lo corrige a CAT C
        i10 = keys.index("9100010|1")
        assert fixed["sku_conocido"][i10] and not fixed["sku_primaria"][i10]        # historia corta
        assert fixed["sku_primaria"][keys.index("9100000|1")]
        assert list(sim_in["sim_keys"]) == keys
        assert fixed["pred_sku_promedio_28"].shape == (len(keys), 21)
        # el SKU que dejo de vender el 30/06 tiene ceros observados (media 0, no NaN) hasta el origen
        assert fixed["pred_sku_promedio_28"][keys.index("9100011|1"), 0] == 0.0
        # conservacion y suma
        names = list(fixed["cat_names"])
        cidx = np.array([names.index(c) for c in fixed["sku_cats"]])
        sums = np.zeros((len(names), 21))
        np.add.at(sums, cidx, np.nan_to_num(fixed["pred_sku_promedio_28"]))
        assert np.allclose(sums, fixed["pred_cat_promedio_28_suma_sku"])
        rf = np.zeros((len(names), 21))
        np.add.at(rf, cidx, np.nan_to_num(fixed["pred_sku_rf_distribuido"]))
        ok = ~np.isnan(fixed["pred_cat_rf_categoria"]).any(axis=1)
        assert np.abs(rf[ok] - fixed["pred_cat_rf_categoria"][ok]).max() < 1e-6


# ------------------------------------------------------------------------------------------ extremo a extremo
@mongo
def test_end_to_end_synthetic_evaluation_audit_and_report(tmp_path):
    with temp_db() as db:
        build(db, tmp_path)
        out, seal = tmp_path / "out", tmp_path / "sello.json"
        run = make_run(db, out, seal)
        man = run.prepare()
        sealed_before = {n: v["bytes_sha256"] for n, v in man["archivos"].items()}
        run.evaluate(confirm_frozen=True)
        assert run.done("evaluacion_predictiva") and run.done("simulacion")
        # el paquete sellado no cambia al evaluar
        assert {n: runner.sha_bytes(out / "preparacion" / n) for n in sealed_before} == sealed_before
        pred = json.loads((out / "predictivo.json").read_text(encoding="utf-8"))
        # dia sin ningun registro (10/08): no evaluable, no cero ficticio
        assert pred["dias_no_evaluables"] == ["2026-08-10"] and pred["dias_evaluables"] == 20
        # SKU nuevo aparte, con unidades y cobertura
        assert pred["nuevos_sku"]["skus_nuevos_con_venta_en_bloque"] == 1 and pred["nuevos_sku"]["unidades_nuevos_evaluables"] > 0
        assert 0 < pred["nuevos_sku"]["cobertura_unidades_universo_conocido"] < 1
        sim = json.loads((out / "simulacion.json").read_text(encoding="utf-8"))
        rep = sim["reporte"]
        assert rep["excluidos_nuevos_skus"] == 1 and rep["excluidos_nuevos_unidades_proxy"] > 0
        assert rep["dias_sin_demanda_conocida"] == ["2026-08-10"] and len(sim["resultados"]) == 27
        assert [r["dia"] for r in rep["revisiones"]] == ["2026-08-01", "2026-08-08", "2026-08-15", "2026-08-22", "2026-08-29"]
        # igualdad de condiciones: mismo stock inicial entre politicas, misma demanda elegible
        for L in (3, 7, 14):
            for S in (0, 7, 14):
                els = {sim["resultados"][f"L{L}_S{S}|{p}"]["total"]["demanda_proxy_elegible_unidades"] for p in core.POLICIES}
                st0 = {sim["resultados"][f"L{L}_S{S}|{p}"]["total"]["stock_inicial_unidades"] for p in core.POLICIES}
                assert len(els) == 1 and len(st0) == 1
        aud = run_audit(out)
        assert aud["ok"], json.dumps({k: v for k, v in aud.items() if k not in ("simulacion",)}, default=str)[:600]
        assert aud["simulacion"]["combinaciones"] == 27 and aud["sello_anterior_a_lectura_agosto"]
        docs = tmp_path / "docs"
        docs.mkdir()
        manifest = write_report(out, docs=docs)
        text = (docs / "T12_RESULTADOS.md").read_text(encoding="utf-8")
        assert core.LABEL in text and "Hallazgo primario" in text and manifest["publicado"] is False
        assert json.loads((docs / "T12_MANIFIESTO.json").read_text(encoding="utf-8"))["auditoria_ok"] is True
        # retomar: una segunda evaluacion no repite fases ni cambia artefactos
        before = {p.name: runner.sha_bytes(p) for p in (out / "predictivo.json", out / "simulacion.json")}
        again = make_run(db, out, seal)
        again.evaluate(confirm_frozen=True)
        assert {p.name: runner.sha_bytes(p) for p in (out / "predictivo.json", out / "simulacion.json")} == before


@mongo
def test_interrupted_run_records_the_error_and_is_never_marked_complete(tmp_path, monkeypatch):
    with temp_db() as db:
        build(db, tmp_path)
        out, seal = tmp_path / "out", tmp_path / "sello.json"
        run = make_run(db, out, seal)
        run.prepare()
        monkeypatch.setattr(core, "sequential_simulation", lambda **k: (_ for _ in ()).throw(RuntimeError("cae a mitad")))
        with pytest.raises(RuntimeError):
            run.evaluate(confirm_frozen=True)
        st = json.loads((out / "estado.json").read_text(encoding="utf-8"))
        assert st["fases"]["simulacion"]["estado"] == "error" and st["completa"] is False
        assert st["fases"]["evaluacion_predictiva"]["estado"] == "completa"      # lo valido se conserva
        monkeypatch.undo()
        pred_hash = runner.sha_bytes(out / "predictivo.json")
        make_run(db, out, seal).evaluate(confirm_frozen=True)                    # retoma solo la simulacion
        assert runner.sha_bytes(out / "predictivo.json") == pred_hash
        assert make_run(db, out, seal).done("simulacion")


@mongo
def test_audit_detects_a_tampered_prediction_or_balance(tmp_path):
    with temp_db() as db:
        build(db, tmp_path)
        out, seal = tmp_path / "out", tmp_path / "sello.json"
        run = make_run(db, out, seal)
        run.prepare()
        run.evaluate(confirm_frozen=True)
        assert run_audit(out)["ok"]
        saved = tmp_path / "copia"
        shutil.copytree(out, saved)
        z = _load_npz(out / "simulacion_series.npz")
        z["L7_S7_promedio_28__served"] = z["L7_S7_promedio_28__served"] + 1
        np.savez(out / "simulacion_series.npz", **z)
        assert not run_audit(out)["simulacion"]["ok"]
        shutil.rmtree(out)
        shutil.copytree(saved, out)
        pj = json.loads((out / "predictivo.json").read_text(encoding="utf-8"))
        for r in pj["sku"]:
            if (r["cohorte"], r["metodo"], r["vista"]) == ("primaria", "promedio_28", "acum14"):
                r["WAPE"] = (r["WAPE"] or 0) + 0.01
        (out / "predictivo.json").write_text(json.dumps(pj), encoding="utf-8")
        assert not run_audit(out)["predictivo"]["ok"]


# ------------------------------------------------------------------------------------------ simulacion: truncamiento
def _small_world(seed=3, n=16, days=75):
    rng = np.random.default_rng(seed)
    W = rng.integers(0, 5, size=(n, days)).astype(float)
    W[:, 20] = np.nan
    cats = [f"C{i % 4}" for i in range(n)]
    return W, cats


def test_each_review_receives_a_physically_truncated_matrix_and_future_data_cannot_change_earlier_reviews():
    eng = load_frozen_engine()
    cfg = json.loads((frozen.ROOT / "config" / "t07_config.json").read_text(encoding="utf-8"))
    W, cats = _small_world(days=125)
    col0, n_days = 80, 31
    seen, hashes = [], []

    def spy(values, start, cats_, alms, rf_cfg, sha):
        seen.append(values.shape[1])
        assert not values.flags.writeable                      # copia de solo lectura
        return t7.forecast_origin_t07(values, start, cats_, alms, rf_cfg, sha)
    mean_init = np.nan_to_num(t7.mean_window(W[:, :col0]))
    cost = np.full(len(cats), 2.0)
    prim0 = np.ones(len(cats), dtype=bool)
    kw = {"col0": col0, "n_days": n_days, "cats": cats, "alms": ["1"], "cost": cost, "mean_init": mean_init, "prim0": prim0,
          "rf_cfg": cfg["rf_categoria"], "sim_cfg": cfg["simulacion"], "config_sha": "x", "eng": eng, "forecast_fn": spy}
    a = core.sequential_simulation(W=W, **kw)
    assert seen == [col0 + j + 1 for j in (0, 7, 14, 21, 28)]
    W2 = W.copy()
    W2[:, col0 + 22:] += 5                                      # cambia lo posterior a la revision del dia 22 (indice 21)
    seen.clear()
    b = core.sequential_simulation(W=W2, **kw)
    for j in (0, 7, 14, 21):                                    # revisiones hasta la del dia 22 inclusive: identicas
        assert a["forecasts"][j]["hash"] == b["forecasts"][j]["hash"], j
    assert a["forecasts"][28]["hash"] != b["forecasts"][28]["hash"]
    assert all(m["conservacion"]["saldo_por_sku_ok"] for m in a["results"].values())
    del hashes


def test_metrics_with_zero_denominator_are_not_evaluable_and_never_nan_or_infinite():
    n, H = 3, 21
    sealed = {"sku_primaria": np.array([True, True, True]), "sku_conocido": np.array([True, True, True]),
              "pred_sku_cero": np.zeros((n, H)), "pred_sku_promedio_28": np.ones((n, H)),
              "pred_sku_rf_distribuido": np.full((n, H), 2.0), "cat_names": np.array(["A"]),
              "cat_primaria": np.array([True]), "cat_conocida": np.array([True]),
              "pred_cat_cero": np.zeros((1, H)), "pred_cat_promedio_28_suma_sku": np.full((1, H), 3.0),
              "pred_cat_rf_categoria": np.full((1, H), 6.0)}
    ev = core.evaluate_predictive(sealed, np.zeros((n, H)), np.ones(H, dtype=bool), np.zeros(n, dtype=int))
    rec = next(r for r in ev["sku"] if (r["cohorte"], r["metodo"], r["vista"]) == ("primaria", "promedio_28", "acum14"))
    assert rec["WAPE"] is None and rec["R2"] is None and rec["MAPE"] is None and rec["unidades_observadas"] == 0
    assert all(np.isfinite(v) for v in (rec["MAE"], rec["RMSE"]))
    pr = primary_reading({"sku": ev["sku"]}, {"sesgo_relativo_maximo_abs": 0.25})
    assert pr["mejora_relativa_rf_vs_promedio_28"] is None and pr["sesgo_relativo_rf"] is None


def test_excluded_days_are_not_evaluable_and_a_day_without_records_is_not_a_zero():
    days = core.block_days()
    covered = set(days) - {"2026-08-10"}
    ev = core.evaluable_days(days, covered, {"2026-08-03"})
    assert ev.sum() == 19 and not ev[days.index("2026-08-10")] and not ev[days.index("2026-08-03")]
    assert date(2026, 8, 1) not in EXCLUDED_DATES


def test_cli_blocks_evaluate_without_the_confirmation_flag(tmp_path, capsys):
    from scripts import run_final
    rc = run_final.main(["evaluate", "--db", "df_test_t12_cli_no_existe", "--out", str(tmp_path / "o")])
    assert rc == 3 and "BLOQUEADO" in capsys.readouterr().err


def test_cli_status_on_an_empty_directory_is_not_complete(tmp_path, capsys):
    from scripts import run_final
    assert run_final.main(["status", "--out", str(tmp_path / "vacio")]) == 0
    assert json.loads(capsys.readouterr().out)["completa"] is False
