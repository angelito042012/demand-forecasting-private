"""Persistencia del plan T19: identidad, idempotencia, versiones, fallo, recuperacion y aislamiento (bases df_test_*)."""
from __future__ import annotations

from datetime import date

import pytest
from pymongo import MongoClient

from pipeline.plan import engine, store
from pipeline.plan.engine import PlanRejected
from tests.plan import helpers_plan as h
from tests.publish.helpers import temp_db

pytestmark = pytest.mark.mongo


@pytest.fixture()
def db():
    with temp_db() as database:
        h.seed_all(database)
        yield database


def gen(db, **kw):
    raw = {**h.RAW, **kw.pop("raw", {})}
    return store.generate_plan(db, raw, **kw)


def res(db, plan_id, pid):
    return db.plan_results.find_one({"plan_id": plan_id, "producto_id": pid}, {"_id": 0})


def test_creates_completed_plan_with_every_product_and_hand_calculated_values(db):
    out = gen(db)
    pid = out["plan_id"]
    head = db.plan_runs.find_one({"plan_id": pid}, {"_id": 0})
    assert out["action"] == "created" and head["status"] == "completed" and head["version"] == 1
    assert db.plan_results.count_documents({"plan_id": pid}) == len(h.PRODUCTS) == head["counts"]["products"]
    assert head["engine_version"] == engine.ENGINE_VERSION and head["method"] == "promedio_28"
    assert head["dates"]["sales_cutoff"] == "2026-09-30" and head["dates"]["count_date"] == "2026-10-18"
    assert head["distances"]["cutoff_to_month_start"] == 32 and head["distances"]["cutoff_to_month_end"] == 61
    assert head["distances"]["cutoff_to_count"] == 18
    assert head["dataset"]["dataset_id"] == h.DATASET_ID and head["snapshot"]["snapshot_id"] == h.SNAPSHOT_ID
    assert pid == store.resolve(db, h.RAW)[1]
    # ejemplos del contrato con datos sembrados (m = 56/28 = 2; el ruido fuera de ventana/posterior no cuenta)
    a = res(db, pid, "1000001")
    assert a["forecast"]["daily_exact"] == "2" and a["forecast"]["sum_28"] == "56" and a["forecast"]["days_valid"] == 28
    assert a["forecast"]["month_total"] == "60" and a["forecast"]["window_start"] == "2026-09-03"
    assert a["scenarios"]["7"]["purchase_qty"] == 60 and a["scenarios"]["14"]["purchase_qty"] == 60
    assert res(db, pid, "1000002")["scenarios"]["7"]["purchase_qty"] == 0
    c = res(db, pid, "1000003")
    assert (c["scenarios"]["7"]["purchase_qty"], c["scenarios"]["14"]["purchase_qty"]) == (88, 74)
    assert (c["scenarios"]["7"]["shortage_before_arrival"], c["scenarios"]["14"]["shortage_before_arrival"]) == ("2", "16")
    d0 = res(db, pid, "1000004")                                    # libre 0 informado: 6 dias sin stock antes de A
    assert d0["scenarios"]["7"]["shortage_before_arrival"] == "12" and d0["scenarios"]["7"]["purchase_qty"] == 88
    for pid_, reason in (("1000005", "SIN_CONTEO"), ("1000006", "SIN_SENAL"), ("1000008", "UNIDAD_INCOMPATIBLE")):
        r = res(db, pid, pid_)
        assert r["status"] == "NO_CALCULABLE" and r["reason"] == reason
        assert all(s["purchase_qty"] is None for s in r["scenarios"].values())
    g = res(db, pid, "1000007")                                    # historia solo en agosto: 0 explicado, no NO_CALCULABLE
    assert g["status"] == "OK" and g["forecast"]["zero_reason"] == "SIN_VENTAS_EN_VENTANA"
    assert g["scenarios"]["7"]["purchase_qty"] == 0
    assert head["counts"]["by_status"] == {"OK": 5, "LLEGA_TARDE": 0, "NO_LLEGA_A_TIEMPO": 0, "NO_CALCULABLE": 3}
    assert head["counts"]["by_scenario"]["7"]["NO_CALCULABLE"] == 3


def test_same_inputs_reuse_the_plan_without_rewriting(db):
    first = gen(db)
    ids = sorted(str(d["_id"]) for d in db.plan_results.find({}, {"_id": 1}))
    head = db.plan_runs.find_one({"plan_id": first["plan_id"]})
    again = gen(db, raw={"lead_days": [14, 7]})              # el orden de los plazos no cambia la identidad
    assert again["action"] == "reused" and again["plan_id"] == first["plan_id"]
    assert ids == sorted(str(d["_id"]) for d in db.plan_results.find({}, {"_id": 1}))
    assert db.plan_runs.count_documents({}) == 1 and db.plan_runs.find_one({"plan_id": first["plan_id"]}) == head


@pytest.mark.parametrize("change", [{"reserve_days": 8}, {"min_order": 2}, {"order_multiple": 12}, {"lead_days": [7]},
                                    {"decision_date": "2026-10-19"}, {"month": "2026-12"},
                                    {"pending_orders": [{"producto_id": "1000001", "units": 30, "arrival_date": "2026-11-05",
                                                         "nature": "ASUMIDA"}]}])
def test_changed_inputs_create_a_new_version_and_keep_the_old_one(db, change):
    first = gen(db)
    before = db.plan_results.find({"plan_id": first["plan_id"]}, {"_id": 0}).to_list()
    second = gen(db, raw=change)
    assert second["action"] == "created" and second["plan_id"] != first["plan_id"]
    heads = {p["plan_id"]: p for p in db.plan_runs.find({}, {"_id": 0})}
    assert set(heads) == {first["plan_id"], second["plan_id"]} and all(p["status"] == "completed" for p in heads.values())
    assert db.plan_results.find({"plan_id": first["plan_id"]}, {"_id": 0}).to_list() == before
    assert heads[first["plan_id"]]["version"] == 1
    assert heads[second["plan_id"]]["version"] == (1 if "month" in change else 2)       # version por mes objetivo


def test_pending_order_with_date_changes_only_that_product_as_hand_calculated(db):
    pid = gen(db, raw={"pending_orders": [{"producto_id": "1000001", "units": 30, "arrival_date": "2026-11-05",
                                           "nature": "REPORTADA"}]})["plan_id"]
    a = res(db, pid, "1000001")
    assert a["scenarios"]["7"]["purchase_qty"] == 30            # 74 + 14 - 28 - 30
    assert a["scenarios"]["14"]["purchase_qty"] == 30           # 60 + 14 - 14 - 30
    assert a["scenarios"]["7"]["breakdown"]["pending_after_arrival"] == "30"
    assert a["pending_orders"] == [{"arrival_date": "2026-11-05", "units": 30}]
    assert res(db, pid, "1000003")["scenarios"]["7"]["purchase_qty"] == 88          # otros productos no cambian
    inc = next(r for r in a["scenarios"]["7"]["series"] if r["fecha"] == "2026-11-05")
    assert inc["recepciones"] == "30"


def test_new_snapshot_version_or_dataset_changes_the_identity(db):
    first = gen(db)["plan_id"]
    h.seed_snapshot(db, "invrep-20261018T1700-a1-aaaaaaaaaaaa", version=2, sha="a" * 64,
                    libres={"1000001": 100})
    db.inventory_reported_snapshots.update_one({"snapshot_id": h.SNAPSHOT_ID}, {"$set": {"status": "superseded"}})
    second = gen(db)
    assert second["plan_id"] != first and res(db, second["plan_id"], "1000001")["count_stock"]["libre"] == 100
    # el plan anterior sigue consultable y con su snapshot
    assert res(db, first, "1000001")["count_stock"]["libre"] == 40
    pinned = gen(db, snapshot_id=h.SNAPSHOT_ID)
    assert pinned["action"] == "reused" and pinned["plan_id"] == first        # por snapshot fijado se reproduce el mismo plan


@pytest.mark.parametrize("fail_at", [1, 2, 3])
def test_failure_keeps_the_last_valid_plan_and_leaves_no_visible_partial_result(db, fail_at):
    good = gen(db)
    snap = h.fingerprint(db, ("plan_results",))
    calls = []

    def guard():
        calls.append(1)
        if len(calls) == fail_at:
            raise RuntimeError("caida simulada")

    with pytest.raises(RuntimeError):
        gen(db, raw={"reserve_days": 9}, guard=guard)
    heads = {p["plan_id"]: p["status"] for p in db.plan_runs.find({}, {"_id": 0, "plan_id": 1, "status": 1})}
    assert heads[good["plan_id"]] == "completed"
    failed = [k for k, v in heads.items() if k != good["plan_id"]]
    assert all(heads[k] in ("failed",) for k in failed)
    assert db.plan_results.count_documents({"plan_id": {"$ne": good["plan_id"]}}) == 0
    assert h.fingerprint(db, ("plan_results",)) == snap
    # el reintento del mismo plan lo completa limpiando el intento fallido por su propio plan_id
    again = gen(db, raw={"reserve_days": 9})
    assert again["action"] == "created" and db.plan_runs.count_documents({"plan_id": again["plan_id"]}) == 1
    assert db.plan_runs.find_one({"plan_id": again["plan_id"]})["status"] == "completed"
    assert db.plan_results.count_documents({"plan_id": again["plan_id"]}) == len(h.PRODUCTS)


def test_interrupted_staging_attempt_is_cleaned_by_its_own_plan_id(db):
    good = gen(db)
    raw = {**h.RAW, "reserve_days": 5}
    _params, pid, *_ = store.resolve(db, raw)
    # restos de un worker muerto: cabecera staging + resultados parciales (incluso duplicando un producto)
    db.plan_runs.insert_one({"plan_id": pid, "status": "staging", "attempt": "viejo", "month": "2026-11"})
    db.plan_results.insert_many([{"plan_id": pid, "producto_id": "1000001", "status": "OK", "basura": True},
                                 {"plan_id": pid, "producto_id": "9999999", "status": "OK", "basura": True}])
    other = db.plan_results.count_documents({"plan_id": good["plan_id"]})
    out = store.generate_plan(db, raw)
    assert out["action"] == "created" and out["plan_id"] == pid
    assert db.plan_results.count_documents({"plan_id": pid}) == len(h.PRODUCTS)
    assert db.plan_results.count_documents({"plan_id": pid, "basura": True}) == 0
    assert db.plan_runs.find_one({"plan_id": pid})["status"] == "completed"
    assert db.plan_results.count_documents({"plan_id": good["plan_id"]}) == other


def test_data_after_the_cutoff_does_not_change_an_earlier_plan(db):
    first = gen(db)
    before = db.plan_results.find({"plan_id": first["plan_id"]}, {"_id": 0}).to_list()
    # ventas de octubre y una venta enorme tras el corte, en el MISMO dataset: fuera de la ventana y del corte
    db.plan_sales.insert_many([h._sale(h.DATASET_ID, 9000 + i, "1000001", date(2026, 10, 1 + i), "5000") for i in range(10)])
    db.plan_runs.delete_many({})
    db.plan_results.delete_many({})
    again = gen(db)
    assert again["action"] == "created" and again["plan_id"] == first["plan_id"]
    after = db.plan_results.find({"plan_id": first["plan_id"]}, {"_id": 0}).to_list()
    key = lambda d: d["producto_id"]
    assert sorted(after, key=key) == sorted(before, key=key)
    assert res(db, first["plan_id"], "1000001")["forecast"]["daily_exact"] == "2"


def test_count_after_the_decision_is_rejected_and_nothing_is_written(db):
    with pytest.raises(PlanRejected) as ex:
        gen(db, raw={"decision_date": "2026-10-17"})
    assert ex.value.code == "DECISION_ANTERIOR_AL_CONTEO"
    assert db.plan_runs.count_documents({}) == 0 and db.plan_results.count_documents({}) == 0


def test_horizon_and_input_availability_are_enforced(db):
    for raw, code in (({"month": "2027-01"}, "HORIZONTE_EXCEDIDO"), ({"month": "2026-10"}, "MES_NO_POSTERIOR_AL_CONTEO"),
                      ({"pending_orders": [{"producto_id": "0000", "units": 1, "arrival_date": "2026-11-02",
                                            "nature": "ASUMIDA"}]}, "PENDIENTE_INVALIDO")):
        with pytest.raises(PlanRejected) as ex:
            gen(db, raw=raw)
        assert ex.value.code == code
    with pytest.raises(PlanRejected) as ex:
        gen(db, dataset_id="plds-inexistente")
    assert ex.value.code == "DATASET_NO_DISPONIBLE"
    db.inventory_reported_snapshots.update_many({}, {"$set": {"status": "staging"}})
    with pytest.raises(PlanRejected) as ex:
        gen(db)
    assert ex.value.code == "INVENTARIO_NO_DISPONIBLE"
    assert db.plan_runs.count_documents({}) == 0


def test_window_without_coverage_is_rejected_not_filled_with_zeros(db):
    db.plan_datasets.update_one({}, {"$set": {"window_start": "2026-09-10"}})
    with pytest.raises(PlanRejected) as ex:
        gen(db)
    assert ex.value.code == "VENTANA_SIN_COBERTURA"
    assert db.plan_results.count_documents({}) == 0


def test_identity_mismatch_between_job_and_inputs_is_rejected(db):
    with pytest.raises(PlanRejected) as ex:
        gen(db, expected_plan_id="plan-2026-11-d20261018-000000000000")
    assert ex.value.code == "IDENTIDAD_NO_COINCIDE"
    assert db.plan_runs.count_documents({}) == 0


def test_generation_does_not_touch_any_other_collection(db):
    before = h.fingerprint(db)
    gen(db)
    gen(db, raw={"reserve_days": 3})
    assert h.fingerprint(db) == before
    names = set(db.list_collection_names())
    assert {"plan_runs", "plan_results"} <= names


def test_protected_database_names_are_refused_before_any_io():
    client = MongoClient("mongodb://127.0.0.1:1", serverSelectionTimeoutMS=50)
    try:
        with pytest.raises(PlanRejected) as ex:
            store.generate_plan(client["demand_forecasting_dev"], h.RAW)
        assert ex.value.code == "BASE_PROTEGIDA"
    finally:
        client.close()
