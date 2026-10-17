"""T10 §1: propiedad por intento, fencing y toma de control con intercalados DETERMINISTAS (hilos + eventos)."""
from __future__ import annotations

import copy
import threading
from datetime import UTC, datetime, timedelta

import pytest

from pipeline.publish import protocol
from pipeline.publish.protocol import (
    LostOwnership,
    PublishInProgressError,
    purge_orphans,
)
from pipeline.publish.publisher import publish_prepared
from pipeline.publish.schema import ensure_schema

from .helpers import temp_db

pytestmark = pytest.mark.mongo
NUM = ("on_hand", "in_transit", "position", "mean_28", "forecast_14d", "safety", "target", "order_qty",
       "unit_cost_assumed", "order_value_assumed", "sum_28", "days_28", "mean_28_exact", "target_raw_exact", "signals")


def run_doc(run_id="gen-test", key="k1"):
    return {"run_id": run_id, "status": "staging", "kind": "generated_baseline", "run_label": "t", "idempotency_key": key,
            "fingerprint": "f", "cutoff": "2026-07-10", "origin": "2026-07-10", "target_start": "2026-07-11",
            "target_end": "2026-07-31", "horizon_days": 21, "method": {}, "sources": [], "artifacts": [], "code": {},
            "schema_version": 1}


def prepared(n=30, tag="x"):
    f = [{"run_id": "p", "level": "sku", "entity_id": f"{i}|1", "sku": str(i), "almacen": "1", "categoria": "C",
          "cohorte": "primaria", "target_date": "2026-07-11", "h": 1,
          "pred": {"promedio_28": 1.0, "rf_categoria_distribuido": 1.0, "cero": 0.0}, "observed": 0, "evaluable": True,
          "chosen_method": "promedio_28", "provenance": "OBSERVED_EXCEL", "schema_version": 1, "tag": tag}
         for i in range(n)]
    r = [{"run_id": "p", "scenario_id": "s", "provenance": "SYNTHETIC_NOT_REAL_INVENTORY", "sku": str(i), "almacen": "1",
          "status": "sin_snapshot", "categoria": "C", "explanation_steps": [], "schema_version": 1,
          **dict.fromkeys(NUM)} for i in range(n)]
    b = [{"backtest_id": "p", "run_id": "p", "kind": "t", "predictive": {}, "simulation": [], "selection": {},
          "coverage": {}, "assumptions": {}, "disclaimer": "d", "scenario_id": "s",
          "provenance": "SYNTHETIC_NOT_REAL_INVENTORY", "schema_version": 1}]
    return {"forecasts": f, "recommendations": r, "backtests": b}


def validator(n=30):
    def _v(db, cid):
        if db.forecasts.count_documents({"run_id": cid}) != n or db.recommendations.count_documents({"run_id": cid}) != n:
            raise protocol.PublishValidationError("conteo")
    return _v


def counts(n=30):
    return {"forecasts_sku": n, "recommendations": n}


def run(db, **kw):
    return publish_prepared(db, run_doc(), kw.pop("prepared", None) or prepared(), validator(), counts(), {}, **kw)


def kids(db, rid="gen-test"):
    return db.runs.find_one({"run_id": rid}).get("children_ref")


def test_takeover_stale_worker_cannot_complete_activate_or_delete_the_new_owner_children():
    """A se detiene tras sus pronosticos; su lease vence y B toma el control y completa; A vuelve tarde."""
    with temp_db() as db:
        ensure_schema(db)
        a_at_hook, a_go = threading.Event(), threading.Event()
        errors = {}

        def hook_a(stage):
            if stage == "forecasts_sku":
                a_at_hook.set()
                assert a_go.wait(30)

        def worker_a():
            try:
                run(db, prepared=prepared(tag="A"), stage_hook=hook_a)
            except Exception as exc:  # noqa: BLE001
                errors["a"] = exc

        ta = threading.Thread(target=worker_a)
        ta.start()
        assert a_at_hook.wait(30)
        late = datetime.now(UTC) + timedelta(hours=1)               # el lease de A ya vencio para B
        res_b = run(db, prepared=prepared(tag="B"), now=late)       # B toma el control, completa y activa
        assert res_b.status == "published"
        cid_b = kids(db)
        assert cid_b.endswith("~g2") and db.forecasts.count_documents({"run_id": cid_b}) == 30
        a_go.set()
        ta.join(30)
        assert isinstance(errors.get("a"), LostOwnership)           # A se detiene: no completa, no activa, no limpia lo ajeno
        assert db.runs.find_one({"run_id": "gen-test"})["children_ref"] == cid_b
        assert db.forecasts.count_documents({"run_id": cid_b, "tag": "B"}) == 30      # hijos de B intactos
        assert db.forecasts.count_documents({"run_id": "gen-test~g1"}) == 0           # A limpio solo su espacio
        assert db.run_pointer.find_one({"_id": "active"})["run_id"] == "gen-test"
        assert db.runs.count_documents({}) == 1 and db.runs.find_one({})["generation"] == 2


def test_stale_worker_returns_at_validation_and_completion_after_takeover():
    with temp_db() as db:
        ensure_schema(db)
        a_at, a_go = threading.Event(), threading.Event()
        errors = {}

        def hook_a(stage):
            if stage == "validacion":                               # A ya valido; se detiene justo antes de completar
                a_at.set()
                assert a_go.wait(30)

        def worker_a():
            try:
                run(db, prepared=prepared(tag="A"), stage_hook=hook_a)
            except Exception as exc:  # noqa: BLE001
                errors["a"] = exc

        t = threading.Thread(target=worker_a)
        t.start()
        assert a_at.wait(30)
        run(db, prepared=prepared(tag="B"), now=datetime.now(UTC) + timedelta(hours=1))
        a_go.set()
        t.join(30)
        assert isinstance(errors.get("a"), LostOwnership)
        doc = db.runs.find_one({"run_id": "gen-test"})
        assert doc["status"] == "completed" and doc["children_ref"].endswith("~g2")
        assert db.forecasts.count_documents({"run_id": doc["children_ref"], "tag": "B"}) == 30


def test_old_worker_wakes_while_new_owner_is_still_staging_and_touches_nothing_of_it():
    with temp_db() as db:
        ensure_schema(db)
        a_at, a_go, b_at, b_go = (threading.Event() for _ in range(4))
        out = {}

        def hook_a(stage):
            if stage == "forecasts_sku":
                a_at.set()
                assert a_go.wait(30)

        def hook_b(stage):
            if stage == "forecasts_sku":
                b_at.set()
                assert b_go.wait(30)

        def wa():
            try:
                run(db, prepared=prepared(tag="A"), stage_hook=hook_a)
            except Exception as exc:  # noqa: BLE001
                out["a"] = exc

        def wb():
            try:
                out["b"] = run(db, prepared=prepared(tag="B"), now=datetime.now(UTC) + timedelta(hours=1),
                               stage_hook=hook_b)
            except Exception as exc:  # noqa: BLE001
                out["b"] = exc

        ta, tb = threading.Thread(target=wa), threading.Thread(target=wb)
        ta.start()
        assert a_at.wait(30)
        tb.start()
        assert b_at.wait(30)                                         # B es dueno y esta a mitad de su publicacion
        a_go.set()
        ta.join(30)
        assert isinstance(out["a"], LostOwnership)
        cur = db.runs.find_one({"run_id": "gen-test"})
        assert cur["status"] == "staging" and cur["generation"] == 2     # A no la marco failed ni la completo
        assert db.forecasts.count_documents({"run_id": "gen-test~g2"}) == 30   # hijos de B intactos
        b_go.set()
        tb.join(30)
        assert out["b"].status == "published" and kids(db) == "gen-test~g2"


def test_failed_cleanup_leaves_orphans_that_purge_removes_without_touching_the_valid_run(monkeypatch):
    with temp_db() as db:
        ensure_schema(db)
        a_at, a_go = threading.Event(), threading.Event()
        errors = {}

        def hook_a(stage):
            if stage == "forecasts_sku":
                a_at.set()
                assert a_go.wait(30)

        def boom(*_a, **_k):
            raise RuntimeError("limpieza fallida")

        def wa():
            try:
                run(db, prepared=prepared(tag="A"), stage_hook=hook_a)
            except Exception as exc:  # noqa: BLE001
                errors["a"] = exc

        t = threading.Thread(target=wa)
        t.start()
        assert a_at.wait(30)
        monkeypatch.setattr("pipeline.publish.publisher.delete_own_children", boom)    # la limpieza de A fallara
        run(db, prepared=prepared(tag="B"), now=datetime.now(UTC) + timedelta(hours=1))
        a_go.set()
        t.join(30)
        assert isinstance(errors["a"], LostOwnership)
        assert db.forecasts.count_documents({"run_id": "gen-test~g1"}) > 0           # huerfanos de A (invisibles)
        removed = purge_orphans(db)
        assert removed.get("forecasts", 0) > 0 and db.forecasts.count_documents({"run_id": "gen-test~g1"}) == 0
        assert db.forecasts.count_documents({"run_id": kids(db)}) == 30              # la corrida valida no se toca


def test_dead_worker_is_recovered_and_its_partial_children_do_not_leak_into_the_result():
    with temp_db() as db:
        ensure_schema(db)
        past = datetime.now(UTC) - timedelta(hours=2)
        state, att = protocol.claim_run(db, run_doc(), now=past)                      # A muere tras escribir una parte
        assert state == "claimed"
        part = prepared(10, "A")
        protocol.stamp(att, part)
        db.forecasts.insert_many(part["forecasts"][:5])
        res = run(db, prepared=prepared(tag="B"))
        assert res.status == "published"
        cid = kids(db)
        assert cid != att.children_id and db.forecasts.count_documents({"run_id": cid}) == 30
        assert db.forecasts.count_documents({"run_id": att.children_id}) == 5          # huerfano invisible
        purge_orphans(db)
        assert db.forecasts.count_documents({"run_id": att.children_id}) == 0


def test_live_lease_blocks_second_publisher_and_completed_is_returned_idempotently():
    with temp_db() as db:
        ensure_schema(db)
        state, _att = protocol.claim_run(db, run_doc())
        assert state == "claimed"
        with pytest.raises(PublishInProgressError):
            run(db)
        db.runs.delete_many({})
        first = run(db)
        again = run(db)
        assert first.status == "published" and again.status == "already_published" and first.run_id == again.run_id
        assert db.forecasts.count_documents({}) == 30 and db.runs.count_documents({}) == 1


def test_two_real_threads_same_key_produce_exactly_one_completed_run_and_no_duplicates():
    with temp_db() as db:
        ensure_schema(db)
        results, errs = [], []

        def go():
            try:
                results.append(run(db))
            except Exception as exc:  # noqa: BLE001
                errs.append(exc)

        ts = [threading.Thread(target=go) for _ in range(6)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(60)
        assert db.runs.count_documents({"status": "completed"}) == 1 and db.runs.count_documents({}) == 1
        cid = kids(db)
        assert db.forecasts.count_documents({"run_id": cid}) == 30
        assert all(isinstance(e, PublishInProgressError | LostOwnership) for e in errs), errs
        assert len(results) + len(errs) == 6 and results


def test_pointer_is_monotonic_and_never_moves_back():
    with temp_db() as db:
        ensure_schema(db)
        t1, t2 = datetime(2026, 7, 1, tzinfo=UTC), datetime(2026, 7, 2, tzinfo=UTC)
        db.runs.insert_many([{"run_id": "a", "status": "completed", "idempotency_key": "ka"},
                             {"run_id": "b", "status": "completed", "idempotency_key": "kb"}])
        assert protocol.activate_monotonic(db, "b", t2)
        assert not protocol.activate_monotonic(db, "a", t1)                      # mas antigua: no retrocede
        assert db.run_pointer.find_one({"_id": "active"})["run_id"] == "b"
        db.runs.insert_one({"run_id": "c", "status": "staging", "idempotency_key": "kc"})
        with pytest.raises(protocol.PublishValidationError):
            protocol.activate_monotonic(db, "c", t2)


def test_failure_before_completion_marks_failed_only_for_the_owner_and_keeps_last_valid():
    with temp_db() as db:
        ensure_schema(db)
        ok = run(db)
        other = copy.deepcopy(run_doc("gen-other", "k2"))

        def boom(stage):
            if stage == "backtests":
                raise RuntimeError("fallo")

        with pytest.raises(RuntimeError):
            publish_prepared(db, other, prepared(), validator(), counts(), {}, stage_hook=boom)
        assert db.runs.find_one({"run_id": "gen-other"})["status"] == "failed"
        assert db.forecasts.count_documents({"run_id": {"$regex": "^gen-other"}}) == 0
        assert db.run_pointer.find_one({"_id": "active"})["run_id"] == ok.run_id
        retry = publish_prepared(db, copy.deepcopy(other), prepared(), validator(), counts(), {})   # reintento: sin duplicar
        assert retry.status == "published" and db.runs.count_documents({"run_id": "gen-other"}) == 1
