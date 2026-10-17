"""T08R: senales exactas (R05), identidad, reemplazo de corridas, anclaje de referencia y fuentes."""
from __future__ import annotations

import json
import shutil
from datetime import date, timedelta
from fractions import Fraction

import pytest
from bson.decimal128 import Decimal128
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.auth.deps import CurrentUser, require_user
from backend.app.db import get_db
from backend.app.errors import install_error_handlers
from backend.app.routers import recommendations, runs
from pipeline.data import daily_series as ds
from pipeline.data.calendar import EXCLUDED_DATES
from pipeline.data.training_access import TrainingData
from pipeline.publish import builders
from pipeline.publish.publisher import (
    PublishValidationError,
    publish,
    run_identity,
    supersede,
)
from pipeline.publish.signals import (
    Signals,
    compute_signals,
    exact_target,
    fingerprint_signals,
    to_fraction,
)
from pipeline.publish.source import (
    PROJECT_ROOT,
    SourceVerificationError,
    verify_and_load,
    verify_training_match,
)

from .helpers import (
    ENTRY,
    kids,
    make_catalog,
    make_signals,
    needs_artifacts,
    real_source,
    temp_db,
)

pytestmark = [pytest.mark.mongo]


# ------------------------------------------------------------------ aritmetica exacta (sin Mongo)
@pytest.mark.parametrize(("total", "days", "target"), [
    (Fraction(1), 7, 3),            # 1/7 por dia: 21*(1/7) = 3 exacto (con floats puede quedar 3.0000000000000004)
    (Fraction(3), 7, 9),            # 3/7: 21*(3/7) = 9 exacto
    (Fraction(12), 28, 9),          # caso Codex 12040025
    (Fraction(4), 28, 3),           # caso Codex 12010025
    (Fraction(20), 21, 20),         # 21*20/21 = 20 exacto
    (Fraction(20), 22, 20),         # 19.09 -> 20
    (Fraction(20), 20, 21),         # 21 exacto
    (Fraction(2999, 1000), 1, 63),  # 62.979 -> 63 (por debajo de un entero)
    (Fraction(3001, 1000), 1, 64),  # 63.021 -> 64 (por encima)
    (Fraction(0), 28, 0),           # sin ventas: objetivo 0
    (Fraction(5, 2), 10, 6),        # cantidades fraccionarias: 5.25 -> 6
])
def test_exact_target_matrix(total, days, target):
    raw, got = exact_target(total, days, 14, 7)
    assert got == target and raw == 21 * total / days


def test_days_must_be_positive_and_fraction_conversion_is_decimal_not_binary():
    with pytest.raises(ValueError):
        exact_target(Fraction(1), 0, 14, 7)
    assert to_fraction(0.1) == Fraction(1, 10) and to_fraction(3) == 3 and to_fraction(2.0) == 2


def test_recompute_matches_exact_formula_and_never_negative():
    c = builders.recompute_recommendation(5, 2, Fraction(10), 28, 42.25)
    assert (c["target"], c["position"], c["order_qty"]) == (8, 7, 1) and c["target_raw_exact"] == "15/2"
    assert builders.recompute_recommendation(100, 0, Fraction(10), 28, 1.0)["order_qty"] == 0


# ------------------------------------------------------------------ compute_signals (ventana, ausentes, ceros)
def _train(rows, first=date(2026, 6, 1), last=date(2026, 7, 10), masked=(), skip_cover=()):
    cal = tuple(first + timedelta(days=i) for i in range((last - first).days + 1))
    mask0 = set(masked)
    rows = list(rows) + [(d.isoformat(), "Z", 1) for d in cal if d not in mask0 and d.isoformat() not in skip_cover]
    sales = tuple({"linea_id": f"l{i}", "fecha": f, "sku": sku, "cantidad_base": q, "importe": Decimal128(str(q * 5)),
                   "categoria_original": "C", "almacen": "1", "unidad_base": "UND"} for i, (f, sku, q) in enumerate(rows))
    return TrainingData(cutoff=last, sales=sales, calendar=cal, excluded_days=frozenset(mask0),
                        catalog={"A": "C", "Z": "C"}, fingerprint="fp")


def test_signals_window_uses_valid_zeros_and_excludes_masked_and_uncovered_days():
    # ventana 13/06..10/07 (28 dias); A vende 3 dias; 20/06 enmascarado; 25/06 sin registros en toda la tienda
    rows = [("2026-06-01", "A", 9), ("2026-06-14", "A", 2), ("2026-06-30", "A", 4), ("2026-07-10", "A", 1)]
    t = _train(rows, masked=(date(2026, 6, 20),), skip_cover=("2026-06-25",))
    sig = compute_signals(t, date(2026, 7, 10))
    total, days = sig.per_sku[("A", "1")]
    assert total == 7 and days == 26                       # 28 - mascara - dia sin registros; 01/06 queda fuera de la ventana
    assert sig.window_start == "2026-06-13" and sig.window_end == "2026-07-10"
    assert sig.per_sku[("Z", "1")] == (Fraction(26), 26)
    assert sig.fingerprint == compute_signals(t, date(2026, 7, 10)).fingerprint     # determinista


def test_signals_product_with_short_history_uses_available_days_not_28():
    rows = [("2026-07-05", "N", 3), ("2026-07-08", "N", 3)]
    sig = compute_signals(_train(rows), date(2026, 7, 10))
    total, days = sig.per_sku[("N", "1")]
    assert total == 6 and days == 6                       # 05..10/07 : no se asume denominador 28
    assert exact_target(total, days, 14, 7)[1] == 21


def test_signals_reject_wrong_origin():
    with pytest.raises(ValueError):
        compute_signals(_train([("2026-07-10", "A", 1)]), date(2026, 7, 9))


def test_product_first_seen_on_the_origin_has_one_useful_day():
    sig = compute_signals(_train([("2026-07-10", "A", 1)]), date(2026, 7, 10))
    assert sig.per_sku[("A", "1")] == (Fraction(1), 1)      # la serie empieza en su primera venta: sin ceros previos


# ------------------------------------------------------------------ publicacion: identidad, reemplazo, fallos
@pytest.fixture(scope="module")
def src():
    return real_source()


@needs_artifacts
def test_identity_is_stable_for_same_inputs_and_changes_with_signals_or_version(src):
    _cat, fp = make_catalog(src)
    s1, s2 = make_signals(src), make_signals(src, "-b")
    a = run_identity(src, fp, s1.fingerprint)
    assert a == run_identity(src, fp, s1.fingerprint)               # reintento: misma identidad
    assert a[0] != run_identity(src, fp, s2.fingerprint)[0]         # otras senales: otra corrida
    assert a[2] != run_identity(src, fp + "x", s1.fingerprint)[2]
    assert src.source_fingerprint and "t08r" in json.dumps({"v": "t08r-1"})


@needs_artifacts
def test_rejects_signals_that_contradict_the_historical_csv_before_writing(src):
    cat, fp = make_catalog(src)
    sig = make_signals(src)
    key = next(iter(sig.per_sku))
    bad = dict(sig.per_sku)
    bad[key] = (bad[key][0] + 5, 28)
    broken = Signals(sig.origin, sig.window_start, sig.window_end, bad, sig.training_fingerprint,
                     fingerprint_signals(sig.origin, sig.window_start, sig.window_end, bad, sig.training_fingerprint))
    with temp_db() as db:
        with pytest.raises(PublishValidationError):
            publish(db, src, cat, fp, broken)
        assert db.runs.count_documents({"status": "completed"}) == 0 and db.recommendations.count_documents({}) == 0


@needs_artifacts
def test_changed_training_fingerprint_or_sources_fail_before_any_write(src):
    cat, fp = make_catalog(src)
    fold = src.manifest["folds_predictivos"][src.entry["fold"]]
    with temp_db() as db:
        with pytest.raises(SourceVerificationError):
            publish(db, src, cat, fp + "-cambiado", make_signals(src))
        other = [dict(s) for s in fold["fuentes"]]
        other[0]["sha256"] = "0" * 64
        with pytest.raises(SourceVerificationError):
            publish(db, src, cat, fp, make_signals(src), sources=other)
        assert db.runs.count_documents({}) == 0 and db.list_collection_names() == []
    verify_training_match(src, fp, fold["fuentes"])                  # el caso valido pasa


@pytest.fixture
def copy_root(tmp_path):
    for rel in (ENTRY["manifest"], ENTRY["metrics"]):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(PROJECT_ROOT / rel, tmp_path / rel)
    d = tmp_path / ENTRY["artifacts_dir"]
    d.mkdir(parents=True, exist_ok=True)
    for n in ENTRY["artifacts"]:
        shutil.copy(PROJECT_ROOT / ENTRY["artifacts_dir"] / n, d / n)
    return tmp_path


@needs_artifacts
def test_altered_metrics_or_manifest_fail_the_approved_reference_even_if_rehashed(copy_root):
    mp = copy_root / ENTRY["metrics"]
    m = json.loads(mp.read_text(encoding="utf-8"))
    m["predictivo"]["seleccion"]["cumple_regla"] = True        # alteracion silenciosa de un resultado desfavorable
    mp.write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    with pytest.raises(SourceVerificationError, match="referencia aprobada"):
        verify_and_load(ENTRY, copy_root)


@needs_artifacts
def test_reference_must_be_configured(copy_root):
    entry = {k: v for k, v in ENTRY.items() if k != "approved_reference"}
    with pytest.raises(SourceVerificationError, match="approved_reference"):
        verify_and_load(entry, copy_root)


@needs_artifacts
def test_corrected_run_supersedes_previous_keeps_history_and_readers_flag_it(src):
    cat, fp = make_catalog(src)
    with temp_db() as db:
        old = publish(db, src, cat, fp, make_signals(src, "-antigua"))
        sig2 = make_signals(src)
        new = publish(db, src, cat, fp, sig2, supersede_runs=[old.run_id])
        assert new.run_id != old.run_id and new.status == "published"
        o = db.runs.find_one({"run_id": old.run_id})
        assert o["status"] == "superseded" and o["superseded_by"] == new.run_id
        assert o["quality_issue"]["code"] == "R05_PRECISION_RECOMENDACIONES"
        assert db.recommendations.count_documents({"run_id": kids(db, old.run_id)}) == 3647      # historial intacto
        assert db.run_pointer.find_one({"_id": "active"})["run_id"] == new.run_id
        # reintento idempotente de la version nueva: mismo run_id, sin duplicar, sustitucion idempotente
        again = publish(db, src, cat, fp, sig2, supersede_runs=[old.run_id])
        assert again.status == "already_published" and again.run_id == new.run_id
        assert db.runs.count_documents({}) == 2 and db.recommendations.count_documents({"run_id": kids(db, new.run_id)}) == 3647
        # API: la corrida antigua se puede ver, pero marcada como sustituida
        app = FastAPI()
        install_error_handlers(app)
        app.include_router(runs.router, prefix="/api/v1")
        app.include_router(recommendations.router, prefix="/api/v1")
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_user] = lambda: CurrentUser("lector1", "lector", "x")
        c = TestClient(app)
        listing = c.get("/api/v1/runs").json()
        states = {i["run_id"]: i["status"] for i in listing["items"]}
        assert states == {old.run_id: "superseded", new.run_id: "completed"}
        r_old = c.get(f"/api/v1/recommendations?run_id={old.run_id}&page_size=2").json()
        assert r_old["validation_status"] == "superseded_precision_error"
        assert r_old["run"]["quality_issue"]["superseded_by"] == new.run_id
        assert all(i["validation_status"] == "superseded_precision_error" for i in r_old["items"])
        r_new = c.get("/api/v1/recommendations?page_size=2").json()           # por defecto: la activa y valida
        assert r_new["run"]["run_id"] == new.run_id and r_new["validation_status"] == "valid"
        det = c.get(f"/api/v1/recommendations/12040025?run_id={new.run_id}").json()
        assert det["sum_28"] == "12" and det["days_28"] == 28 and det["mean_28_exact"] == "3/7"
        assert (det["target"], det["order_qty"]) == (9, 0)
        assert c.get(f"/api/v1/runs/{old.run_id}").json()["quality_issue"]["code"] == "R05_PRECISION_RECOMENDACIONES"


@needs_artifacts
def test_failed_new_publication_keeps_last_valid_active_and_does_not_supersede(src):
    cat, fp = make_catalog(src)
    with temp_db() as db:
        old = publish(db, src, cat, fp, make_signals(src, "-antigua"))

        def boom(stage):
            if stage == "validacion":
                raise RuntimeError("fallo simulado")

        with pytest.raises(RuntimeError):
            publish(db, src, cat, fp, make_signals(src), supersede_runs=[old.run_id], stage_hook=boom)
        assert db.run_pointer.find_one({"_id": "active"})["run_id"] == old.run_id
        assert db.runs.find_one({"run_id": old.run_id})["status"] == "completed"
        assert db.runs.count_documents({"status": "failed"}) == 1


def test_supersede_validations(src=None):
    with temp_db() as db:
        db.runs.insert_one({"run_id": "a", "status": "completed"})
        db.runs.insert_one({"run_id": "b", "status": "staging"})
        with pytest.raises(PublishValidationError):
            supersede(db, "a", "b", "R05_PRECISION_RECOMENDACIONES")      # la sustituta no esta completed
        with pytest.raises(PublishValidationError):
            supersede(db, "a", "a", "R05_PRECISION_RECOMENDACIONES")
        with pytest.raises(PublishValidationError):
            supersede(db, "a", "b", "OTRA")


def test_excluded_dates_constant_is_not_part_of_signals_identity():
    assert len(EXCLUDED_DATES) == 3 and ds.VENTA == "VENTA_OBSERVADA"
