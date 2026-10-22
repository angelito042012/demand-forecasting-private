"""T20 §3: GET /stock, GET /plans/{a}/compare/{b} y GET /plans/inputs con existencia reconstruida (bases df_test_*)."""
from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.config import get_settings
from backend.app.db import get_db
from backend.app.errors import install_error_handlers
from backend.app.routers import admin, auth, plan, stock
from pipeline.plan import store
from tests.backend import test_auth_common as common
from tests.backend.test_auth_common import login
from tests.plan import helpers_plan as h

pytestmark = pytest.mark.mongo

db, settings, users = common.db, common.settings, common.users


@pytest.fixture
def seeded(db):
    h.seed_all(db)
    h.seed_v2(db)
    return db


@pytest.fixture
def app(seeded, settings, users):
    application = FastAPI()
    install_error_handlers(application)
    for module in (auth, admin, plan, stock):
        application.include_router(module.router, prefix="/api/v1")
    application.dependency_overrides[get_db] = lambda: seeded
    application.dependency_overrides[get_settings] = lambda: settings
    return application


def _session(app, username):
    c = TestClient(app, base_url="http://testserver")
    assert login(c, username).status_code == 200
    return c


@pytest.fixture
def reader(app):
    with _session(app, "luis") as c:
        yield c


@pytest.fixture
def admin_c(app):
    with _session(app, "ana") as c:
        yield c


@pytest.fixture
def anon(app):
    with TestClient(app, base_url="http://testserver") as c:
        yield c


@pytest.fixture
def plans(seeded):
    v1 = store.generate_plan(seeded, h.RAW, dataset_id=h.DATASET_ID, snapshot_id=h.SNAPSHOT_ID)["plan_id"]
    v2 = store.generate_plan(seeded, h.RAW_V2)["plan_id"]
    return v1, v2


def code(r):
    return r.json()["error"]["code"]


# ------------------------------------------------------------------ /stock
def test_stock_requires_login_and_allows_reader_and_admin(anon, reader, admin_c):
    assert anon.get("/api/v1/stock").status_code == 401
    assert reader.get("/api/v1/stock").status_code == 200 and admin_c.get("/api/v1/stock").status_code == 200
    for method in ("post", "put", "patch", "delete"):
        assert getattr(admin_c, method)("/api/v1/stock").status_code in (403, 404, 405, 422)


def test_stock_default_shape_and_values(reader):
    b = reader.get("/api/v1/stock").json()
    sn = b["snapshot"]
    assert sn["snapshot_id"] == h.REC_SNAPSHOT_ID and sn["kind"] == "RECONSTRUIDO" and sn["as_of_local"] == h.REC_AS_OF
    assert sn["base_count"]["as_of_local"] == h.AS_OF and sn["movements"]["last_movement_local"] == h.LAST_MOVEMENT
    assert sn["counts"] == {"products": 7, "discrepancies": 1} and sn["warehouse"] == {"id": "1", "name": "Almacen 1"}
    assert [c["code"] for c in sn["confirmations"]] == ["COMPRAS_11452_11455", "DIFERENCIAS_INVENTARIO"]
    assert sn["confirmations"][1]["products"] == ["1000003"]
    assert (b["total"], b["page"], b["page_size"], b["has_more"]) == (7, 1, 50, False)
    assert b["view_counts"] == {"all": 7, "discrepancias": 1, "coinciden": 6} and b["provenance"] == "EXISTENCIA_RECONSTRUIDA"
    items = {i["producto_id"]: i for i in b["items"]}
    assert set(items["1000001"]) == {"producto_id", "producto", "categoria", "unidad_reporte", "unidad_descripcion", "libre",
                                     "base_count", "movements", "reconstructed_at_last_movement",
                                     "system_stock_at_last_movement", "system_reserved", "discrepancy"}
    assert items["1000001"]["libre"] == 40 and items["1000001"]["base_count"] == 37 and items["1000001"]["discrepancy"] is None
    assert items["1000003"]["discrepancy"] == {"difference": -3, "compared_at_local": h.LAST_MOVEMENT}
    assert items["1000003"]["system_stock_at_last_movement"] == 7 and items["1000003"]["reconstructed_at_last_movement"] == 10
    assert '"_id"' not in json.dumps(b)


def test_stock_pagination_views_search_and_sort(reader):
    url = "/api/v1/stock"
    p = reader.get(url, params={"page_size": 3, "page": 3}).json()
    assert [i["producto_id"] for i in p["items"]] == ["1000008"] and p["has_more"] is False and p["total"] == 7
    p1 = reader.get(url, params={"page_size": 3}).json()
    assert [i["producto_id"] for i in p1["items"]] == ["1000001", "1000002", "1000003"] and p1["has_more"] is True
    d = reader.get(url, params={"view": "discrepancias"}).json()
    assert [i["producto_id"] for i in d["items"]] == ["1000003"] and d["total"] == 1
    assert d["view_counts"] == {"all": 7, "discrepancias": 1, "coinciden": 6}
    assert reader.get(url, params={"q": "1000002"}).json()["total"] == 1
    assert reader.get(url, params={"q": "producto 1000004"}).json()["total"] == 1
    assert reader.get(url, params={"q": "1000002", "view": "discrepancias"}).json()["total"] == 0
    assert reader.get(url, params={"q": "1.*"}).json()["total"] == 0                       # literal, no regex
    assert [i["libre"] for i in reader.get(url, params={"sort": "-libre"}).json()["items"]][:2] == [500, 40]


@pytest.mark.parametrize("params", [{"view": "otro"}, {"sort": "categoria"}, {"x": "1"}, {"q": "$where"}, {"q": "{\"$ne\":1}"},
                                    {"page": "0"}, {"page_size": "201"}, {"snapshot_id": "a$b"}, {"$ne": "1"}])
def test_stock_invalid_params_are_422(reader, params):
    r = reader.get("/api/v1/stock", params=params)
    assert r.status_code == 422 and code(r) == "ENTRADA_INVALIDA"


def test_stock_404_unknown_snapshot_and_unavailable_without_one(reader, seeded):
    r = reader.get("/api/v1/stock", params={"snapshot_id": "invrec-no-existe"})
    assert r.status_code == 404 and code(r) == "NO_ENCONTRADO"
    assert reader.get("/api/v1/stock", params={"snapshot_id": h.SNAPSHOT_ID}).status_code == 404   # el informado no es existencia reconstruida
    seeded.inventory_reconstructed_snapshots.update_one({}, {"$set": {"status": "staging"}})
    assert reader.get("/api/v1/stock", params={"snapshot_id": h.REC_SNAPSHOT_ID}).status_code == 404
    b = reader.get("/api/v1/stock").json()
    assert b["snapshot"] is None and b["items"] == [] and b["unavailable_reason"] == "SIN_EXISTENCIA_RECONSTRUIDA" and b["total"] == 0


def test_stock_without_discrepancies_says_so(reader, seeded):
    seeded.inventory_reconstructed_items.update_many({}, {"$set": {"discrepancy": None}})
    b = reader.get("/api/v1/stock", params={"view": "discrepancias"}).json()
    assert b["items"] == [] and b["total"] == 0 and b["snapshot"]["confirmations"][1]["products"] == []


def test_reading_stock_leaves_collections_untouched(reader, seeded):
    before = h.fingerprint(seeded)
    reader.get("/api/v1/stock")
    reader.get("/api/v1/stock", params={"view": "discrepancias"})
    assert h.fingerprint(seeded) == before


# ------------------------------------------------------------------ /plans/inputs
def test_inputs_default_to_reconstructed_with_decision_day_after_count(reader, seeded):
    b = reader.get("/api/v1/plans/inputs").json()
    assert b["dataset"]["dataset_id"] == h.DATASET_V2_ID and b["dataset"]["sales_cutoff"] == "2026-10-20"
    assert b["dataset"]["base_dataset_id"] == h.DATASET_ID
    sn = b["snapshot"]
    assert sn["kind"] == "RECONSTRUIDO" and sn["snapshot_id"] == h.REC_SNAPSHOT_ID and sn["products"] == 7
    assert sn["last_movement_local"] == h.LAST_MOVEMENT and sn["discrepancy_products"] == ["1000003"]
    assert b["defaults"]["decision_date"] == "2026-10-21" and b["defaults"]["month"] == "2026-11"
    assert b["limits"]["decision_min"] == "2026-10-20" and b["limits"]["pending_arrival_min"] == "2026-10-21"
    assert "No hay pedidos adicionales por recibir registrados" in b["assumptions"][0]["text"]
    seeded.inventory_reconstructed_snapshots.delete_many({})
    b2 = reader.get("/api/v1/plans/inputs").json()
    assert b2["snapshot"]["kind"] == "INFORMADO" and b2["defaults"]["decision_date"] == "2026-10-18"


def test_inputs_informed_snapshot_unchanged_when_no_reconstructed(reader, seeded):
    seeded.inventory_reconstructed_snapshots.delete_many({})
    seeded.plan_datasets.update_one({"dataset_id": h.DATASET_ID}, {"$set": {"status": "current"}})
    seeded.plan_datasets.update_one({"dataset_id": h.DATASET_V2_ID}, {"$set": {"status": "superseded"}})
    b = reader.get("/api/v1/plans/inputs").json()
    assert b["snapshot"] == {"snapshot_id": h.SNAPSHOT_ID, "kind": "INFORMADO", "as_of_local": h.AS_OF,
                             "warehouse": {"id": "1", "name": "Almacen 1"}, "products": len(h.PRODUCTS)}
    assert b["defaults"]["decision_date"] == "2026-10-18"
    assert b["assumptions"][0]["text"].startswith("En este escenario no llegan otros pedidos")


# ------------------------------------------------------------------ plan y comparacion
def test_plan_endpoints_expose_kind_confirmations_and_stock_provenance(reader, plans):
    _v1, v2 = plans
    p = reader.get(f"/api/v1/plans/{v2}").json()
    assert p["snapshot"]["kind"] == "RECONSTRUIDO" and p["snapshot"]["discrepancy_products"] == ["1000003"]
    assert [c["code"] for c in p["confirmations"]] == ["COMPRAS_11452_11455", "DIFERENCIAS_INVENTARIO"]
    assert p["provenance"]["initial_stock"] == "EXISTENCIA_RECONSTRUIDA_CIERRE_2026-10-20"
    items = {i["producto_id"]: i for i in reader.get(f"/api/v1/plans/{v2}/results").json()["items"]}
    assert items["1000003"]["stock_provenance"]["discrepancy"]["difference"] == -3
    assert items["1000001"]["stock_provenance"]["discrepancy"] is None
    d = reader.get(f"/api/v1/plans/{v2}/results/1000003").json()
    assert d["stock_provenance"]["movements_net_to_closing"] == 3 and d["scenarios"]["7"]["series"][0]["fecha"] == "2026-10-21"
    assert d["scenarios"]["7"]["arrival_date"] == "2026-10-28" and d["scenarios"]["14"]["arrival_date"] == "2026-11-04"


def test_v1_plan_endpoints_have_no_v2_fields(reader, plans):
    v1, _v2 = plans
    p = reader.get(f"/api/v1/plans/{v1}").json()
    assert p["snapshot"]["kind"] == "INFORMADO" and "confirmations" not in p
    it = reader.get(f"/api/v1/plans/{v1}/results").json()["items"][0]
    assert "stock_provenance" not in it
    assert "stock_provenance" not in reader.get(f"/api/v1/plans/{v1}/results/1000001").json()


def test_compare_v1_v2_shape_and_hand_deltas(reader, plans):
    v1, v2 = plans
    r = reader.get(f"/api/v1/plans/{v1}/compare/{v2}")
    assert r.status_code == 200
    b = r.json()
    assert set(b) == {"base", "other", "summary", "items", "note", "label"}
    assert b["base"]["plan_id"] == v1 and b["base"]["snapshot_kind"] == "INFORMADO" and b["other"]["snapshot_kind"] == "RECONSTRUIDO"
    assert b["base"]["snapshot_as_of_local"] == h.AS_OF and b["other"]["snapshot_as_of_local"] == h.REC_AS_OF
    assert "fechas distintas" in b["note"]
    assert b["summary"]["products"] == 8 and b["summary"]["only_in_base"] == 1 and b["summary"]["only_in_other"] == 0
    assert b["summary"]["same_stock_date"] is False
    items = {i["producto_id"]: i for i in b["items"]}
    assert [i["producto_id"] for i in b["items"]] == sorted(items)
    x = items["1000003"]                                                        # v1: stock 10 al 18/10 => 88/74; v2: stock 10 al 20/10 => 82/68
    assert x["a"] == {"forecast_daily": "2", "month_total": "60", "libre": 10, "purchase": {"7": 88, "14": 74}, "status": "OK"}
    assert x["b"] == {"forecast_daily": "2", "month_total": "60", "libre": 10, "purchase": {"7": 82, "14": 68}, "status": "LLEGA_TARDE"}
    assert x["delta"] == {"daily": "0", "month_total": "0", "libre": 0, "purchase": {"7": -6, "14": -6}}
    y = items["1000001"]                                                        # v1 libre 40 => 60/60; v2 => 56/56
    assert y["delta"]["purchase"] == {"7": -4, "14": -4}
    gone = items["1000005"]                                                     # sin cantidad en v1; no existe en v2
    assert gone["b"] is None and gone["delta"] is None and gone["a"]["status"] == "NO_CALCULABLE"
    assert items["1000006"]["a"]["forecast_daily"] is None and items["1000006"]["delta"]["daily"] is None
    assert items["1000006"]["delta"]["purchase"] == {"7": None, "14": None}
    assert b["summary"]["purchase_changed_by_lead"]["7"] >= 2
    assert '"_id"' not in json.dumps(b)


def test_compare_same_plan_is_all_zero_and_same_date(reader, plans):
    v1, _ = plans
    b = reader.get(f"/api/v1/plans/{v1}/compare/{v1}").json()
    assert b["summary"]["same_stock_date"] is True and b["summary"]["purchase_changed_by_lead"] == {}
    assert "misma fecha" in b["note"]


def test_compare_permissions_404_and_param_validation(anon, reader, admin_c, plans, seeded):
    v1, v2 = plans
    assert anon.get(f"/api/v1/plans/{v1}/compare/{v2}").status_code == 401
    assert admin_c.get(f"/api/v1/plans/{v1}/compare/{v2}").status_code == 200
    r = reader.get(f"/api/v1/plans/{v1}/compare/plan-inexistente")
    assert r.status_code == 404 and code(r) == "NO_ENCONTRADO"
    assert reader.get(f"/api/v1/plans/plan-inexistente/compare/{v2}").status_code == 404
    seeded.plan_runs.insert_one({"plan_id": "plan-staging", "status": "staging", "month": "2026-11"})
    assert reader.get(f"/api/v1/plans/{v1}/compare/plan-staging").status_code == 404
    assert reader.get(f"/api/v1/plans/{v1}/compare/a$b").status_code == 422
    assert reader.get(f"/api/v1/plans/{v1}/compare/{v2}", params={"x": "1"}).status_code == 422
    assert reader.post(f"/api/v1/plans/{v1}/compare/{v2}").status_code in (403, 404, 405)


def test_compare_leaves_collections_untouched(reader, plans, seeded):
    before = h.fingerprint(seeded, ("plan_runs", "plan_results", *h.UNTOUCHED))
    v1, v2 = plans
    reader.get(f"/api/v1/plans/{v1}/compare/{v2}")
    assert h.fingerprint(seeded, ("plan_runs", "plan_results", *h.UNTOUCHED)) == before
