"""T11A: publicacion del paquete final T12 con datos SINTETICOS en bases temporales df_test_<uuid>."""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

import numpy as np
import pytest
from pymongo import MongoClient, monitoring
from pymongo.errors import PyMongoError

from pipeline.publish import final_package as fp
from pipeline.publish.schema import SchemaError, validate_doc
from pipeline.publish.source import PROJECT_ROOT

DAYS = [f"2026-08-{d:02d}" for d in range(1, 22)]
CATS = ["CAT A", "CAT A", "CAT B", "CAT B", "CAT B", "CAT C"]
KEYS = ["9100000|1", "9100001|1", "9100002|1", "9100003|1", "9100004|1", "9100005|1"]
PHASES = fp.PHASES


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _w(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def make_package(root: Path, *, drop_day: int | None = None) -> Path:
    """Paquete T12 sintetico minimo pero estructuralmente identico (sin ejecutar T12). `drop_day` = indice 0..20 de un
    dia sin ningun registro (evaluable=false)."""
    prep = root / "preparacion"
    prep.mkdir(parents=True, exist_ok=True)
    n = len(KEYS)
    rng = np.random.default_rng(7)
    p28 = np.repeat(rng.uniform(0.5, 4.0, n)[:, None], 21, axis=1)
    rfd = np.clip(p28 * rng.uniform(0.7, 1.3, (n, 21)), 0, None)
    names = sorted(set(CATS))
    cidx = np.array([names.index(c) for c in CATS])
    cat28 = np.zeros((len(names), 21))
    np.add.at(cat28, cidx, p28)
    catrf = np.zeros((len(names), 21))
    np.add.at(catrf, cidx, rfd)
    sealed = {"sku_keys": np.array(KEYS), "sku_cats": np.array(CATS), "sku_primaria": np.array([1, 1, 1, 1, 1, 0], bool),
              "sku_conocido": np.ones(n, bool), "pred_sku_promedio_28": p28, "pred_sku_rf_distribuido": rfd,
              "pred_sku_cero": np.zeros((n, 21)), "cat_names": np.array(names), "cat_primaria": np.ones(len(names), bool),
              "cat_conocida": np.ones(len(names), bool), "pred_cat_promedio_28_suma_sku": cat28,
              "pred_cat_rf_categoria": catrf, "pred_cat_cero": np.zeros((len(names), 21))}
    init = {"sim_keys": np.array(KEYS), "sim_costo_unitario": np.ones(n)}
    act = rng.integers(0, 6, (n, 21)).astype(float)
    ev = np.ones(21, bool)
    if drop_day is not None:
        ev[drop_day] = False
    reales = {"act": act, "eval_days": ev, "cat_idx": cidx, "dias": np.array(DAYS)}
    np.savez(prep / "predicciones_fijas.npz", **sealed)
    np.savez(prep / "inicializacion_sim.npz", **init)
    np.savez(root / "reales_bloque.npz", **reales)
    np.savez(root / "simulacion_series.npz", x=np.arange(3))
    (prep / "rf_categoria_T12.joblib").write_bytes(b"NO-ES-UN-MODELO-REAL")
    (root / "ventas_agosto_min.csv.gz").write_bytes(b"csv-sintetico")
    (root / "verificacion.json").write_text("{}", encoding="utf-8")
    man = {"version": "t12-1", "creado_lima": "2026-10-17T17:52:53-05:00", "git_commit": "a" * 40, "origen": "2026-07-31",
           "agosto_consultado": False, "reference_v1_consultado": False, "fingerprint_entrenamiento": "f" * 64,
           "fuentes": [{"mes": f"2026-0{m}", "archivo": f"m{m}.xlsx", "sha256": hashlib.sha256(bytes([m])).hexdigest()}
                       for m in range(3, 8)],
           "seleccion_congelada_sha256": "b" * 64,
           "archivos": {"predicciones_fijas.npz": {"bytes_sha256": _sha(prep / "predicciones_fijas.npz"),
                                                    "logical_sha256": fp.logical_signature(sealed)},
                        "inicializacion_sim.npz": {"bytes_sha256": _sha(prep / "inicializacion_sim.npz"),
                                                    "logical_sha256": fp.logical_signature(init)},
                        "rf_categoria_T12.joblib": {"bytes_sha256": _sha(prep / "rf_categoria_T12.joblib")}}}
    man["sello_sha256"] = hashlib.sha256(fp.canonical({k: v for k, v in man.items() if k != "creado_lima"})).hexdigest()
    _w(prep / "manifiesto_preparacion.json", man)

    def stat(metodo, wape):
        return {"fold": "FINAL", "cohorte": "primaria", "metodo": metodo, "vista": "acum14", "n": 5, "unidades_observadas": 100.0,
                "WAPE": wape, "sesgo_acumulado": 3.0}
    pred = {"sku": [stat("cero", 1.0), stat("promedio_28", 0.78), stat("rf_distribuido", 0.79)], "categoria": [],
            "cobertura": {"sku": [], "categoria": []},
            "nuevos_sku": {"skus_nuevos_con_venta_en_bloque": 2, "unidades_nuevos_evaluables": 3.0,
                           "unidades_conocidos_evaluables": 50.0, "cobertura_unidades_universo_conocido": 0.94},
            "dias_evaluables": int(ev.sum()), "dias_no_evaluables": [d for d, e in zip(DAYS, ev, strict=True) if not e],
            "universo": {"sku_conocidos": n, "primaria": 5, "categorias": len(names)}}
    _w(root / "predictivo.json", pred)
    block = {"fill_rate": 0.9}
    res = {f"L{L}_S{S}|{p}": {"total": block, "primaria": block, "historia_corta": block, "identidad_valor": 0.0,
                              "conservacion": {"ok": True}}
           for L in (3, 7, 14) for S in (0, 7, 14) for p in ("referencia_fija", "promedio_28", "rf_categoria_distribuido")}
    diffs = {f"L{L}_S{S}|{p}|vs_{r}|{c}": {"fill_rate": {"abs": 0.01, "rel": 0.01}}
             for L in (3, 7, 14) for S in (0, 7, 14) for p, r in (("promedio_28", "referencia_fija"),
                                                                   ("rf_categoria_distribuido", "referencia_fija"),
                                                                   ("rf_categoria_distribuido", "promedio_28"),
                                                                   ("referencia_fija", "promedio_28"))
             for c in ("total", "primaria", "historia_corta")}
    _w(root / "simulacion.json", {"resultados": res, "diferencias": diffs, "identidad_valor_max_abs": 0.0,
                                  "reporte": {"universo_skus": n, "dias": 31, "revisiones": [
                                      {"dia": "2026-08-01", "hash_pronostico": "h", "conservacion_cat_a_sku": 0.0,
                                       "pesos": {"x": 1}}]}})
    _w(root / "auditoria.json", {"ok": True})
    fases = {p: {"estado": "completa", "inicio": "2026-10-17T17:00:00-05:00", "fin": "2026-10-17T17:01:00-05:00"} for p in PHASES}
    fases["evaluacion_predictiva"].update({"predictivo_sha256": _sha(root / "predictivo.json"),
                                           "reales": {"bytes_sha256": _sha(root / "reales_bloque.npz"),
                                                      "logical_sha256": fp.logical_signature(reales)}})
    fases["simulacion"].update({"simulacion_sha256": _sha(root / "simulacion.json"),
                                "series": {"bytes_sha256": _sha(root / "simulacion_series.npz")}})
    fases["lectura_agosto"].update({"bytes_sha256": _sha(root / "ventas_agosto_min.csv.gz"), "filas": 3})
    fases["auditoria"].update({"auditoria_sha256": _sha(root / "auditoria.json")})
    fases["reporte"]["fin"] = "2026-10-17T18:12:24-05:00"
    _w(root / "estado.json", {"version": "t12-1", "fases": fases, "eventos": [], "completa": True,
                              "correcciones": [{"t": "x", "git_commit_base": "c" * 40, "motivo": "R11",
                                                "hashes_originales_conservados": {
                                                    "predictivo.json": _sha(root / "predictivo.json")}}]})
    return root


@contextlib.contextmanager
def temp_mongo(listener=None):
    uri = os.environ.get("MONGODB_URI", "mongodb://127.0.0.1:27017")
    client = MongoClient(uri, serverSelectionTimeoutMS=1500, event_listeners=[listener] if listener else [])
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


@pytest.fixture
def pkg(tmp_path):
    return make_package(tmp_path / "f")


def _publish(db, root, **kw):
    return fp.publish_final(db, root, seal_doc=None, see_run="hist-x", **kw)


# ------------------------------------------------------------------ verificacion
def test_helpers_match_t12_implementation():
    from pipeline.final import core, runner
    a = {"x": np.arange(6).reshape(2, 3), "s": np.array(["a", "bb"])}
    assert fp.logical_signature(a) == core.logical_signature(a)
    o = {"b": 1, "a": [1.5, "é"]}
    assert fp.canonical(o) == runner.canonical(o)


def test_valid_package_verifies(pkg):
    v = fp.verify_final_package(pkg, seal_doc=None)
    assert v["manifest"]["sello_sha256"] and len(v["simulation"]["resultados"]) == 27


def test_incomplete_state_rejected(pkg):
    st = json.loads((pkg / "estado.json").read_text(encoding="utf-8"))
    st["completa"] = False
    _w(pkg / "estado.json", st)
    with pytest.raises(fp.FinalPackageError, match="completa"):
        fp.verify_final_package(pkg, seal_doc=None)


def test_missing_phase_rejected(pkg):
    st = json.loads((pkg / "estado.json").read_text(encoding="utf-8"))
    st["fases"]["reporte"]["estado"] = "en_curso"
    _w(pkg / "estado.json", st)
    with pytest.raises(fp.FinalPackageError, match="reporte"):
        fp.verify_final_package(pkg, seal_doc=None)


def test_audit_not_ok_rejected(pkg):
    _w(pkg / "auditoria.json", {"ok": False})
    with pytest.raises(fp.FinalPackageError, match="auditoria"):
        fp.verify_final_package(pkg, seal_doc=None)


@pytest.mark.parametrize("victim", ["predictivo.json", "simulacion.json", "reales_bloque.npz", "ventas_agosto_min.csv.gz",
                                    "preparacion/rf_categoria_T12.joblib", "preparacion/predicciones_fijas.npz"])
def test_altered_artifact_rejected(pkg, victim):
    p = pkg / victim
    p.write_bytes(p.read_bytes() + b" ")
    with pytest.raises(fp.FinalPackageError):
        fp.verify_final_package(pkg, seal_doc=None)


def test_altered_manifest_rejected(pkg):
    p = pkg / "preparacion" / "manifiesto_preparacion.json"
    m = json.loads(p.read_text(encoding="utf-8"))
    m["fingerprint_entrenamiento"] = "0" * 64
    _w(p, m)
    with pytest.raises(fp.FinalPackageError, match="sello"):
        fp.verify_final_package(pkg, seal_doc=None)


def test_seal_document_mismatch_rejected(pkg, tmp_path):
    _w(tmp_path / "sello.json", {"sello_sha256": "0" * 64})
    with pytest.raises(fp.FinalPackageError, match="SELLO"):
        fp.verify_final_package(pkg, seal_doc=tmp_path / "sello.json")


# ------------------------------------------------------------------ documentos y publicacion
def test_publish_idempotent_and_documents(pkg):
    with temp_mongo() as db:
        db.run_pointer.insert_one({"_id": "active", "run_id": "hist-x", "published_at": fp.datetime(2026, 1, 1)})
        r1 = _publish(db, pkg)
        assert r1["estado"] == "publicado" and r1["counts"] == {"forecasts_sku": 6 * 21, "forecasts_categoria": 3 * 21,
                                                                 "recommendations": 0, "backtests": 1}
        assert r1["capacidad"]["bson_total_bytes"] > 0
        n_f, n_r = db.forecasts.count_documents({}), db.runs.count_documents({})
        r2 = _publish(db, pkg)
        assert r2["estado"] == "sin_cambios" and r2["run_id"] == r1["run_id"]
        assert (db.forecasts.count_documents({}), db.runs.count_documents({}), db.backtests.count_documents({})) == (n_f, n_r, 1)
        run = db.runs.find_one({"run_id": r1["run_id"]})
        seal = json.loads((pkg / "preparacion" / "manifiesto_preparacion.json").read_text(encoding="utf-8"))["sello_sha256"]
        assert run["status"] == "completed" and run["kind"] == "final_evaluation" and run["run_id"] == f"final-20260731-{seal[:12]}"
        assert run["idempotency_key"] == f"final-eval:{seal}" and run["children_ref"].endswith("~g1")
        assert run["method"]["rf_declared_winner"] is False and run["method"]["chosen"] == "promedio_28"
        assert run["counts"]["recommendations"] == 0 and run["see_run"] == "hist-x"
        assert run["target_end"] == "2026-08-21" and run["evaluation_period"]["single_block"] is True
        assert db.recommendations.count_documents({}) == 0
        # no activa el puntero
        assert db.run_pointer.find_one({"_id": "active"})["run_id"] == "hist-x"
        # sin rutas privadas ni binarios en los documentos
        blob = (json.dumps(run, default=str, ensure_ascii=False)
                + json.dumps(db.backtests.find_one({}, {"_id": 0}), default=str, ensure_ascii=False))
        assert str(PROJECT_ROOT) not in blob and "artifacts/private" not in blob and "\\" not in blob
        assert all(set(a) == {"name", "sha256", "size_bytes"} for a in run["artifacts"])
        bt = db.backtests.find_one({"run_id": run["children_ref"]})
        assert bt["kind"] == "final_evaluation" and bt["selection"]["rf_declared_winner"] is False
        assert bt["selection"]["chosen"] == "promedio_28" and len(bt["simulation"]) == 27 and len(bt["simulation_differences"]) == 108
        assert bt["selection"]["primary"]["WAPE_promedio_28"] == 0.78
        assert bt["provenance"] == "SYNTHETIC_NOT_REAL_INVENTORY"


def test_category_equals_sku_sum_and_dates(pkg):
    with temp_mongo() as db:
        res = _publish(db, pkg)
        cid = db.runs.find_one({"run_id": res["run_id"]})["children_ref"]
        skus = list(db.forecasts.find({"run_id": cid, "level": "sku"}))
        cats = list(db.forecasts.find({"run_id": cid, "level": "categoria"}))
        for c in cats:
            mem = [s for s in skus if s["categoria"] == c["entity_id"] and s["target_date"] == c["target_date"]]
            assert c["pred"]["promedio_28"] == pytest.approx(sum(s["pred"]["promedio_28"] for s in mem))
            assert c["pred"]["rf_categoria_distribuido"] == pytest.approx(sum(s["pred"]["rf_categoria_distribuido"] for s in mem))
            assert c["observed"] == sum(s["observed"] for s in mem)
        dates = {d["target_date"] for d in skus + cats}
        assert min(dates) == "2026-08-01" and max(dates) == "2026-08-21"
        assert all(d["run_kind"] == "final_evaluation" for d in skus + cats)
        assert {d["cohorte"] for d in skus} == {"primaria", "historia_corta"}


def test_non_evaluable_day_has_no_fabricated_observed(tmp_path):
    root = make_package(tmp_path / "f", drop_day=9)
    with temp_mongo() as db:
        res = _publish(db, root)
        cid = db.runs.find_one({"run_id": res["run_id"]})["children_ref"]
        bad = list(db.forecasts.find({"run_id": cid, "target_date": "2026-08-10"}))
        assert bad and all(d["evaluable"] is False and d["observed"] is None for d in bad)
        good = list(db.forecasts.find({"run_id": cid, "target_date": "2026-08-11"}))
        assert all(d["evaluable"] is True and isinstance(d["observed"], int) for d in good)
        run = db.runs.find_one({"run_id": res["run_id"]})
        assert run["evaluation_period"]["excluded_days"] == ["2026-08-10"]


def test_nan_prediction_is_not_published_as_zero(tmp_path):
    root = make_package(tmp_path / "f")
    z = dict(np.load(root / "preparacion" / "predicciones_fijas.npz"))
    z["pred_sku_rf_distribuido"][2, 3] = np.nan
    pkg = fp.verify_final_package(root, seal_doc=None)
    pkg["sealed"] = z
    with pytest.raises(fp.FinalPackageError, match="no finitas"):
        fp.build_frame(pkg)


def test_date_limit_only_for_final_kind():
    base = {"run_id": "r", "level": "sku", "entity_id": "1|1", "categoria": "C", "target_date": "2026-10-22", "h": 1,
            "pred": {"promedio_28": 1.0, "rf_categoria_distribuido": 1.0, "cero": 0.0}, "evaluable": True,
            "provenance": "OBSERVED_EXCEL", "schema_version": 1}
    with pytest.raises(SchemaError):
        validate_doc("forecasts", base)                                       # historica: limitada a 2026-10-21
    with pytest.raises(SchemaError):
        validate_doc("forecasts", {**base, "run_kind": "generated_baseline", "observed": None, "evaluable": False})
    validate_doc("forecasts", {**base, "run_kind": "final_evaluation", "target_date": "2026-08-05"})
    validate_doc("forecasts", {**base, "run_kind": "final_evaluation", "target_date": "2026-08-21"})
    with pytest.raises(SchemaError):
        validate_doc("forecasts", {**base, "run_kind": "final_evaluation", "target_date": "2026-08-22"})
    with pytest.raises(SchemaError):
        validate_doc("forecasts", {**base, "run_kind": "final_evaluation", "target_date": "2026-07-31"})
    validate_doc("forecasts", {**base, "target_date": "2026-10-21"})


def test_protected_databases_refused(pkg):
    client = MongoClient("mongodb://127.0.0.1:27017", serverSelectionTimeoutMS=500)
    for name in ("demand_forecasting_v2", "demand_forecasting_dev"):
        with pytest.raises(fp.FinalPackageError, match="no admite escritura"):
            fp.publish_final(client[name], pkg, seal_doc=None)
    client.close()


def test_dry_run_writes_nothing(pkg):
    with temp_mongo() as db:
        res = fp.publish_final(db, pkg, seal_doc=None, dry_run=True)
        assert res["estado"] == "dry_run" and res["capacidad"]["bson_total_mb"] > 0
        assert db.list_collection_names() == []


class _Rec(monitoring.CommandListener):
    def __init__(self):
        self.colls: set[str] = set()

    def started(self, event):
        for k in ("find", "insert", "update", "aggregate", "count", "distinct", "delete", "findAndModify", "createIndexes"):
            if k in event.command:
                self.colls.add(str(event.command[k]))

    def succeeded(self, event):
        pass

    def failed(self, event):
        pass


def test_publisher_never_reads_sales_or_august_from_mongo(pkg):
    rec = _Rec()
    with temp_mongo(rec) as db:
        _publish(db, pkg)
    assert "sales" not in rec.colls and "credit_notes" not in rec.colls
    assert rec.colls <= {"runs", "forecasts", "backtests", "recommendations", "imports", "run_pointer"}


def test_publisher_does_not_load_models_or_training_access(pkg):
    """Proceso limpio: preparar el paquete no importa sklearn/joblib/pipeline.final/forecast ni llama a la barrera de datos."""
    code = "\n".join([
        f"import sys; sys.path.insert(0, {str(PROJECT_ROOT)!r})",
        "from pipeline.publish import final_package as fp",
        "import pipeline.data.training_access as ta",
        "def boom(*a, **k): raise AssertionError('acceso a datos de entrenamiento/agosto')",
        "ta.load_final_test_sales = boom; ta.load_training_data = boom",
        f"fp.prepare_package({str(pkg)!r}, seal_doc=None)",
        "bad = [m for m in ('sklearn', 'joblib', 'pipeline.final', 'pipeline.forecast') if m in sys.modules]",
        "print('BAD:' + ','.join(bad))"])
    out = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, timeout=120, check=False)
    assert out.returncode == 0, out.stderr[-500:]
    assert out.stdout.strip().endswith("BAD:"), out.stdout
