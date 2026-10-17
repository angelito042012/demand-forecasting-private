"""Publicacion T08: artefactos REALES de T07 en bases temporales aisladas (df_test_<uuid>)."""
from __future__ import annotations

import csv
import gzip
import json
import shutil

import numpy as np
import pytest

from pipeline.publish import builders
from pipeline.publish.publisher import (
    PublishValidationError,
    publish,
    validate_published,
)
from pipeline.publish.schema import INDEXES, SchemaError, ensure_schema, validate_doc
from pipeline.publish.source import (
    PROJECT_ROOT,
    SourceVerificationError,
    load_publish_config,
    resolve_entry,
    sha256_file,
    verify_and_load,
)
from tests.publish.helpers import (
    ENTRY,
    make_catalog,
    make_signals,
    needs_artifacts,
    real_source,
    temp_db,
)

pytestmark = [pytest.mark.mongo, pytest.mark.realdata, needs_artifacts]


@pytest.fixture(scope="module")
def published():
    src = real_source()
    cat, fp = make_catalog(src)
    with temp_db() as db:
        res = publish(db, src, cat, fp, make_signals(src))
        yield db, res, src, cat, fp


def test_full_publication_counts_and_pointer(published):
    db, res, *_ = published
    assert res.status == "published" and res.activated
    run = db.runs.find_one({"run_id": res.run_id})
    assert run["status"] == "completed" and run["cutoff"] == "2026-07-10" and run["horizon_days"] == 21
    assert db.run_pointer.find_one({"_id": "active"})["run_id"] == res.run_id
    assert db.forecasts.count_documents({"level": "sku"}) == 76587
    assert db.recommendations.count_documents({}) == 3647
    assert db.recommendations.count_documents({"status": "ok"}) == 3347
    assert db.recommendations.count_documents({"status": "sin_snapshot"}) == 300
    assert db.backtests.count_documents({}) == 1
    assert run["coverage"]["skus_pronosticados"] == 3647 and run["coverage"]["skus_sin_snapshot"] == 300
    assert run["method"]["chosen"] == "promedio_28" and run["method"]["control"] == "cero"
    assert all(set(a) == {"name", "sha256", "size_bytes"} for a in run["artifacts"])
    bt = db.backtests.find_one({})
    assert len(bt["simulation"]) == 27 and bt["provenance"] == "SYNTHETIC_NOT_REAL_INVENTORY"
    assert bt["disclaimer"].startswith("Inventario simulado")
    assert max(d["target_date"] for d in db.forecasts.find({}, {"target_date": 1})) <= "2026-07-31"


def test_categories_are_sum_of_skus_and_unknown_is_separate(published):
    db, *_ = published
    cats = {c["entity_id"] for c in db.forecasts.find({"level": "categoria"}, {"entity_id": 1})}
    assert "DESCONOCIDA" in cats and len(cats) == 8
    c = db.forecasts.find_one({"level": "categoria", "entity_id": "CAT3", "target_date": "2026-07-15"})
    members = list(db.forecasts.find({"level": "sku", "categoria": "CAT3", "target_date": "2026-07-15"}))
    assert c["pred"]["promedio_28"] == pytest.approx(sum(m["pred"]["promedio_28"] for m in members))
    assert c["observed"] == sum(m["observed"] for m in members)
    assert c["pred"]["cero"] == 0.0 and c["provenance"] == "OBSERVED_EXCEL"


def _csv_preds(sku: str):
    """Lee el CSV real a mano (sin pandas): (h, pred_promedio_28) del SKU en el fold G4."""
    path = PROJECT_ROOT / ENTRY["artifacts_dir"] / "predicciones_folds.csv.gz"
    vals = []
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["fold"] == "G4" and row["entidad"] == f"{sku}|1":
                vals.append((int(row["h"]), float(row["pred_promedio_28"])))
    vals.sort()
    return vals


def test_manual_recommendation_matches_npz(published):
    db, *_ = published
    z = np.load(PROJECT_ROOT / ENTRY["artifacts_dir"] / "simulacion_series.npz", allow_pickle=False)
    skus = z["skus"].tolist()
    k = "L7_S7_promedio_28__"
    on_hand, ordered, received = z[k + "on_hand"], z[k + "ordered"], z[k + "received"]
    sku = None
    for cand in skus[:600]:
        i = skus.index(cand)
        if ordered[:40, i].sum() - received[:40, i].sum() != ordered[:, i].sum() - received[:, i].sum():
            sku = cand
            break
    assert sku is not None, "debe existir un SKU con transito al origen distinto del final"
    i = skus.index(sku)
    transit39 = int(ordered[:40, i].sum() - received[:40, i].sum())
    transit_final = int(ordered[:, i].sum() - received[:, i].sum())
    doc = db.recommendations.find_one({"sku": sku, "almacen": "1"})
    vals = _csv_preds(sku)
    assert [h for h, _ in vals] == list(range(1, 22))
    mean28 = vals[0][1]
    f14 = sum(v for _, v in vals[:14])
    sum28 = round(mean28 * 28)          # la media historica es suma/28 con 28 dias utiles
    on = int(on_hand[39, i])
    cost = float(z["costo"][i])
    target = -((-21 * sum28) // 28)        # techo exacto con enteros: ceil(21*suma/28)
    qty = max(0, target - (on + transit39))
    assert transit39 != transit_final
    assert doc["in_transit"] == transit39 and doc["in_transit"] != transit_final
    assert (doc["on_hand"], doc["position"], doc["target"], doc["order_qty"]) == (on, on + transit39, target, qty)
    assert doc["mean_28"] == pytest.approx(mean28) and doc["forecast_14d"] == pytest.approx(f14)
    assert doc["sum_28"] == str(sum28) and doc["days_28"] == 28
    assert doc["unit_cost_assumed"] == cost and doc["order_value_assumed"] == pytest.approx(qty * cost)
    assert doc["provenance"] == "SYNTHETIC_NOT_REAL_INVENTORY" and doc["currency"] == "PEN"
    assert doc["scenario_id"] == "T07_L7_S7_promedio_28_2026-07-10" and doc["forecast_to"] == "2026-07-24"
    assert any("Pedido sugerido" in s for s in doc["explanation_steps"])
    # SKU 1010004 (primero del NPZ), verificado a mano contra el saldo del dia 39
    d0 = db.recommendations.find_one({"sku": "1010004"})
    i0 = skus.index("1010004")
    assert d0["on_hand"] == int(on_hand[39, i0])
    assert d0["in_transit"] == int(ordered[:40, i0].sum() - received[:40, i0].sum())


def test_sku_without_snapshot_has_no_numbers(published):
    db, _, src, *_ = published
    npz = set(src.sim["skus"].tolist())
    sku = next(s for s in sorted(set(src.forecasts["entidad"].str.split("|").str[0])) if s not in npz)
    d = db.recommendations.find_one({"sku": sku})
    assert d["status"] == "sin_snapshot"
    assert d["reason"] == ("SIN_INVENTARIO_SIMULADO_AL_10_07: producto conocido despues del 31/05; "
                           "no se supone stock cero")
    assert all(d[f] is None for f in builders.NUM_FIELDS)
    assert db.forecasts.count_documents({"level": "sku", "sku": sku}) == 21   # el pronostico si existe


def test_republish_is_idempotent(published):
    db, res, src, cat, fp = published
    again = publish(db, src, cat, fp, make_signals(src))
    assert again.status == "already_published" and again.run_id == res.run_id
    assert db.runs.count_documents({}) == 1
    assert db.forecasts.count_documents({}) == 76587 + 168
    assert db.recommendations.count_documents({}) == 3647 and db.backtests.count_documents({}) == 1


def test_validation_detects_tampered_category(published):
    db, res, *_ = published
    one = db.forecasts.find_one({"run_id": res.run_id, "level": "categoria"})
    orig = one["pred"]["promedio_28"]
    db.forecasts.update_one({"_id": one["_id"]}, {"$set": {"pred.promedio_28": orig + 5}})
    try:
        with pytest.raises(PublishValidationError):
            validate_published(db, res.run_id, db.runs.find_one({"run_id": res.run_id})["counts"])
    finally:
        db.forecasts.update_one({"_id": one["_id"]}, {"$set": {"pred.promedio_28": orig}})


@pytest.mark.parametrize("stage", ["forecasts_sku", "recommendations", "backtests", "validacion"])
def test_mid_failure_then_retry_does_not_duplicate(stage):
    src = real_source()
    cat, fp = make_catalog(src)

    def boom(s):
        if s == stage:
            raise RuntimeError("fallo simulado")

    with temp_db() as db:
        with pytest.raises(RuntimeError):
            publish(db, src, cat, fp, make_signals(src), stage_hook=boom)
        run = db.runs.find_one({})
        assert run["status"] == "failed" and run["error"]["code"] == "PUBLICACION_FALLIDA"
        assert "fallo simulado" not in str(run["error"])
        assert db.run_pointer.count_documents({}) == 0
        assert db.forecasts.count_documents({}) == 0 and db.recommendations.count_documents({}) == 0
        res = publish(db, src, cat, fp, make_signals(src))
        assert res.status == "published" and res.run_id == run["run_id"]
        assert db.runs.count_documents({}) == 1
        assert db.forecasts.count_documents({}) == 76587 + 168
        assert db.recommendations.count_documents({}) == 3647 and db.backtests.count_documents({}) == 1
        assert db.runs.find_one({})["status"] == "completed"
        assert db.run_pointer.find_one({"_id": "active"})["run_id"] == res.run_id


def test_failed_second_run_keeps_last_complete_active():
    src = real_source()
    cat, fp = make_catalog(src)
    with temp_db() as db:
        a = publish(db, src, cat, fp, make_signals(src))

        def boom(s):
            if s == "recommendations":
                raise RuntimeError("x")

        with pytest.raises(RuntimeError):
            publish(db, src, cat, fp, make_signals(src, "-otra-version"), stage_hook=boom)
        assert db.runs.count_documents({}) == 2
        assert db.runs.count_documents({"status": "failed"}) == 1
        assert db.run_pointer.find_one({"_id": "active"})["run_id"] == a.run_id
        assert db.forecasts.count_documents({"run_id": a.run_id}) == 76587 + 168   # intactos
        failed = db.runs.find_one({"status": "failed"})
        assert db.forecasts.count_documents({"run_id": failed["run_id"]}) == 0


def test_schema_is_idempotent_and_validates():
    with temp_db() as db:
        n1 = ensure_schema(db)
        n2 = ensure_schema(db)
        assert n1 == n2 and len(n1) == sum(len(v) for v in INDEXES.values())
        assert db.runs.index_information()["uq_idempotency_key"]["unique"]
    with pytest.raises(SchemaError):
        validate_doc("recommendations", {"run_id": "r", "scenario_id": "s", "provenance": "OBSERVED_EXCEL",
                                         "sku": "1", "almacen": "1", "status": "ok", "categoria": "c",
                                         "explanation_steps": [], "schema_version": 1})


# ---- verificacion de artefactos -------------------------------------------------------
@pytest.fixture
def copy_root(tmp_path):
    for rel in (ENTRY["manifest"], ENTRY["metrics"]):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(PROJECT_ROOT / rel, tmp_path / rel)
    d = tmp_path / ENTRY["artifacts_dir"]
    d.mkdir(parents=True)
    for n in ENTRY["artifacts"]:
        shutil.copy(PROJECT_ROOT / ENTRY["artifacts_dir"] / n, d / n)
    return tmp_path


def test_copied_artifacts_verify(copy_root):
    assert verify_and_load(ENTRY, copy_root).source_fingerprint == real_source().source_fingerprint


def test_altered_checksum_is_rejected(copy_root):
    p = copy_root / ENTRY["artifacts_dir"] / "simulacion_series.npz"
    data = bytearray(p.read_bytes())
    data[len(data) // 2] ^= 0xFF
    p.write_bytes(bytes(data))
    with pytest.raises(SourceVerificationError, match="sha256"):
        verify_and_load(ENTRY, copy_root)


def test_altered_manifest_code_hash_is_rejected(copy_root):
    mp = copy_root / ENTRY["manifest"]
    m = json.loads(mp.read_text(encoding="utf-8"))
    m["codigo_sha256"] = "0" * 64
    mp.write_text(json.dumps(m), encoding="utf-8")
    with pytest.raises(SourceVerificationError, match="codigo_sha256|referencia aprobada"):
        verify_and_load(ENTRY, copy_root)


def test_missing_artifact_and_unlisted_manifest_are_rejected(copy_root):
    (copy_root / ENTRY["artifacts_dir"] / "predicciones_folds.csv.gz").unlink()
    with pytest.raises(SourceVerificationError):
        verify_and_load(ENTRY, copy_root)
    with pytest.raises(SourceVerificationError, match="lista cerrada"):
        resolve_entry("../../etc/passwd", load_publish_config())


def test_path_escape_in_entry_is_rejected(tmp_path):
    bad = {**ENTRY, "manifest": "../fuera.json"}
    with pytest.raises(SourceVerificationError):
        verify_and_load(bad, tmp_path)


def test_artifact_hash_matches_manifest():
    man = real_source().manifest
    for name in ENTRY["artifacts"]:
        assert sha256_file(PROJECT_ROOT / ENTRY["artifacts_dir"] / name) == man["artefactos"][name]["sha256"]


def test_cli_rejects_paths_and_bad_db_names():
    from scripts import publish_run
    with pytest.raises(SystemExit):
        publish_run.main(["--manifest", "docs/T07_MANIFIESTO.json"])
    assert publish_run.main(["--manifest", "t07", "--db", "bad name;drop"]) == 2


def test_cli_on_empty_db_fails_without_publishing(capsys):
    from scripts import publish_run
    with temp_db() as db:
        assert publish_run.main(["--manifest", "t07", "--db", db.name]) == 1
        assert db.runs.count_documents({}) == 0 and db.run_pointer.count_documents({}) == 0
    assert "mongodb://" not in capsys.readouterr().err
