"""T19 §6: API del plan de compra + trabajo generate_plan ejecutado por el worker (bases temporales df_test_*)."""
from __future__ import annotations

import json
from datetime import date
from fractions import Fraction as F

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.config import get_settings
from backend.app.db import get_db
from backend.app.errors import install_error_handlers
from backend.app.routers import admin, auth, jobs, plan
from pipeline.jobs import queue
from pipeline.plan import engine
from tests.backend import test_auth_common as common
from tests.backend.test_auth_common import ORIGIN, login
from tests.jobs.jobs_support import run_job
from tests.plan import helpers_plan as h

pytestmark = pytest.mark.mongo

db, settings, users = common.db, common.settings, common.users
BASE = "/api/v1/plans"


@pytest.fixture
def seeded(db):
    h.seed_all(db)
    return db


@pytest.fixture
def app(seeded, settings, users):
    application = FastAPI()
    install_error_handlers(application)
    for module in (auth, admin, plan, jobs):
        application.include_router(module.router, prefix="/api/v1")
    application.dependency_overrides[get_db] = lambda: seeded
    application.dependency_overrides[get_settings] = lambda: settings
    return application


class Session:
    def __init__(self, app, username):
        self.http = TestClient(app, base_url="http://testserver")
        r = login(self.http, username)
        assert r.status_code == 200
        self.csrf = r.json()["csrf_token"]

    def post(self, body, csrf=True):
        hd = {"Origin": ORIGIN, "Content-Type": "application/json"}
        if csrf:
            hd["X-CSRF-Token"] = self.csrf
        return self.http.post(BASE, json=body, headers=hd)


@pytest.fixture
def admin_s(app):
    s = Session(app, "ana")
    yield s
    s.http.close()


@pytest.fixture
def reader_s(app):
    s = Session(app, "luis")
    yield s
    s.http.close()


@pytest.fixture
def anon(app):
    with TestClient(app, base_url="http://testserver") as c:
        yield c


def code(r):
    return r.json()["error"]["code"]


def worker(seeded, tmp_path):
    return run_job(seeded, tmp_path / "uploads")


@pytest.fixture
def plan_id(admin_s, seeded, tmp_path):
    r = admin_s.post(h.RAW)
    assert r.status_code == 202
    done = worker(seeded, tmp_path)
    assert done["status"] == "completed" and done["result"]["plan_id"] == r.json()["plan_id"]
    return r.json()["plan_id"]


# ------------------------------------------------------------------ permisos
def test_permissions_and_csrf(admin_s, reader_s, anon, seeded):
    assert anon.post(BASE, json=h.RAW, headers={"Origin": ORIGIN}).status_code == 401
    assert reader_s.post(h.RAW).status_code == 403 and code(reader_s.post(h.RAW)) == "PROHIBIDO"
    r = admin_s.post(h.RAW, csrf=False)
    assert r.status_code == 403 and code(r) == "CSRF_INVALIDO"
    assert seeded.jobs.count_documents({}) == 0 and seeded.plan_runs.count_documents({}) == 0
    for path in ("/inputs", "", "/plan-x", "/plan-x/results", "/plan-x/results/1000001"):
        assert anon.get(BASE + path).status_code == 401, path
    for path in ("/inputs", ""):
        assert reader_s.http.get(BASE + path).status_code == 200
        assert admin_s.http.get(BASE + path).status_code == 200
    for method in ("put", "patch", "delete"):
        assert getattr(admin_s.http, method)(BASE).status_code in (404, 405)


def test_inputs_defaults_limits_and_unavailable(admin_s, reader_s, seeded):
    b = reader_s.http.get(BASE + "/inputs").json()
    assert b["dataset"]["dataset_id"] == h.DATASET_ID and b["dataset"]["sales_cutoff"] == "2026-09-30"
    assert b["dataset"]["classes"]["VENTA"] == b["dataset"]["source_rows"]
    assert b["snapshot"] == {"snapshot_id": h.SNAPSHOT_ID, "as_of_local": h.AS_OF,
                             "warehouse": {"id": "1", "name": "Almacen 1"}, "products": len(h.PRODUCTS)}
    assert b["defaults"] == {"month": "2026-11", "decision_date": "2026-10-18", "lead_days": [7, 14], "reserve_days": 7,
                             "min_order": 1, "order_multiple": 1, "pending_orders": []}
    lim = b["limits"]
    assert lim["months"] == ["2026-11", "2026-12"] and lim["decision_min"] == "2026-10-18" and lim["decision_max"] == "2026-12-31"
    assert (lim["lead_min"], lim["lead_max"], lim["max_leads"], lim["horizon_days"]) == (1, 60, 4, 120)
    nov = lim["months_detail"][0]
    assert nov["extrapolation_days_to_start"] == 32 and nov["extrapolation_days_to_end"] == 61
    assert any(a["code"] == "PEDIDOS_PENDIENTES" and a["nature"] == "SUPUESTO" for a in b["assumptions"])
    seeded.inventory_reported_snapshots.delete_many({})
    b2 = admin_s.http.get(BASE + "/inputs").json()
    assert b2["snapshot"] is None and b2["unavailable_reason"] == "SIN_INVENTARIO_INFORMADO" and b2["dataset"] is not None
    seeded.plan_datasets.delete_many({})
    b3 = admin_s.http.get(BASE + "/inputs").json()
    assert b3["dataset"] is None and b3["unavailable_reason"] == "SIN_DATASET"


# ------------------------------------------------------------------ encolado y trabajo
def test_post_enqueues_a_job_and_the_request_does_not_compute(admin_s, reader_s, seeded, tmp_path):
    r = admin_s.post(h.RAW)
    b = r.json()
    assert r.status_code == 202 and set(b) == {"plan_id", "job_id", "status", "reused"}
    assert b["status"] == "queued" and b["reused"] is False and b["plan_id"].startswith("plan-2026-11-d20261018-")
    job = seeded.jobs.find_one({"job_id": b["job_id"]})
    assert job["type"] == "generate_plan" and job["status"] == "queued"
    assert seeded.plan_runs.count_documents({}) == 0 and seeded.plan_results.count_documents({}) == 0   # nada se calculo
    assert reader_s.http.get(f"{BASE}/{b['plan_id']}").status_code == 404
    lst = reader_s.http.get(BASE, params={"month": "2026-11"}).json()
    assert lst["items"] == [] and lst["unavailable_reason"] == "SIN_PLAN"
    assert admin_s.post(h.RAW).json() == {**b, "reused": True}                                   # mismo trabajo en cola
    assert seeded.jobs.count_documents({}) == 1
    done = worker(seeded, tmp_path)
    assert done["status"] == "completed" and done["result"]["outcome"] == "generado" and done["result"]["productos"] == 8
    assert done["result"]["estados"]["NO_CALCULABLE"] == 3
    assert admin_s.http.get(f"/api/v1/jobs/{b['job_id']}").json()["links"] == {"plan": f"/plans/{b['plan_id']}"}
    again = admin_s.post(h.RAW).json()
    assert again["reused"] is True and again["status"] == "completed" and again["job_id"] == b["job_id"]
    assert seeded.jobs.count_documents({}) == 1                                                  # no se vuelve a encolar
    new = admin_s.post({**h.RAW, "reserve_days": 9}).json()
    assert new["reused"] is False and new["plan_id"] != b["plan_id"]


def test_job_failure_is_permanent_and_keeps_the_last_valid_plan(admin_s, reader_s, seeded, tmp_path, plan_id):
    r = admin_s.post({**h.RAW, "reserve_days": 9}).json()
    seeded.plan_datasets.update_one({}, {"$set": {"window_start": "2026-09-20"}})         # la ventana deja de estar cubierta
    done = worker(seeded, tmp_path)
    assert done["status"] == "failed" and done["error"]["code"] == "VENTANA_SIN_COBERTURA" and done["attempts"] == 1
    assert reader_s.http.get(f"{BASE}/{r['plan_id']}").status_code == 404
    lst = reader_s.http.get(BASE, params={"month": "2026-11"}).json()
    assert [p["plan_id"] for p in lst["items"]] == [plan_id]                              # el ultimo plan valido se conserva
    assert reader_s.http.get(f"{BASE}/{plan_id}/results").json()["total"] == 8
    # un reintento explicito de la misma peticion, ya reparado el dato, crea otro trabajo
    seeded.plan_datasets.update_one({}, {"$set": {"window_start": "2026-03-01"}})
    retry = admin_s.post({**h.RAW, "reserve_days": 9}).json()
    assert retry["plan_id"] == r["plan_id"] and retry["job_id"] != r["job_id"] and retry["reused"] is False
    assert worker(seeded, tmp_path)["status"] == "completed"
    assert reader_s.http.get(f"{BASE}/{r['plan_id']}").status_code == 200


def test_job_with_foreign_identity_fails_permanently(seeded, tmp_path):
    queue.ensure_indexes(seeded)
    queue.enqueue(seeded, "generate_plan", {"plan_id": "plan-2026-11-d20261018-000000000000", "dataset_id": h.DATASET_ID,
                                            "snapshot_id": h.SNAPSHOT_ID, "params": h.RAW}, "plan:x", "admin")
    done = worker(seeded, tmp_path)
    assert done["status"] == "failed" and done["error"]["code"] == "IDENTIDAD_NO_COINCIDE" and done["error"]["retryable"] is False
    queue.enqueue(seeded, "generate_plan", {"plan_id": "p"}, "plan:y", "admin")
    assert worker(seeded, tmp_path)["error"]["code"] == "ENTRADA_INVALIDA"
    assert seeded.plan_runs.count_documents({}) == 0


# ------------------------------------------------------------------ validaciones 422
@pytest.mark.parametrize("change,expected", [
    ({"month": "2026-13"}, "MES_INVALIDO"), ({"month": "2026-10"}, "MES_NO_POSTERIOR_AL_CONTEO"),
    ({"month": "2027-01"}, "HORIZONTE_EXCEDIDO"), ({"decision_date": "2026-10-17"}, "DECISION_ANTERIOR_AL_CONTEO"),
    ({"decision_date": "2026-12-01"}, "DECISION_FUERA_DE_RANGO"), ({"decision_date": "hoy"}, "FECHA_INVALIDA"),
    ({"lead_days": [0]}, "PLAZOS_INVALIDOS"), ({"lead_days": [61]}, "PLAZOS_INVALIDOS"),
    ({"lead_days": [1, 2, 3, 4, 5]}, "PLAZOS_INVALIDOS"), ({"lead_days": []}, "PLAZOS_INVALIDOS"),
    ({"reserve_days": 31}, "RESERVA_INVALIDA"), ({"min_order": 0}, "MINIMO_INVALIDO"),
    ({"order_multiple": 0}, "MULTIPLO_INVALIDO"),
    ({"pending_orders": [{"producto_id": "1000001", "units": 5}]}, "PENDIENTE_SIN_FECHA"),
    ({"pending_orders": [{"producto_id": "1000001", "units": 5, "arrival_date": "2026-10-18"}]}, "PENDIENTE_INVALIDO"),
    ({"pending_orders": [{"producto_id": "5555555", "units": 5, "arrival_date": "2026-11-02"}]}, "PENDIENTE_INVALIDO"),
    ({"pending_orders": [{"producto_id": "1000001", "units": 5, "arrival_date": "2026-12-02"}]}, "PENDIENTE_INVALIDO"),
    ({"pending_orders": [{"producto_id": "1000001", "units": 5, "arrival_date": "2026-11-02", "nature": "X"}]}, "PENDIENTE_INVALIDO"),
])
def test_post_validation_codes_and_nothing_is_enqueued(admin_s, seeded, change, expected):
    r = admin_s.post({**h.RAW, **change})
    assert r.status_code == 422 and code(r) == expected, r.text
    assert seeded.jobs.count_documents({}) == 0


@pytest.mark.parametrize("body", [
    {**h.RAW, "extra": 1}, {k: v for k, v in h.RAW.items() if k != "month"}, {**h.RAW, "lead_days": ["7"]},
    {**h.RAW, "reserve_days": 7.5}, {**h.RAW, "reserve_days": True}, {**h.RAW, "min_order": "1"}, {**h.RAW, "lead_days": 7},
    {**h.RAW, "pending_orders": [{"producto_id": "1000001", "units": 2, "arrival_date": "2026-11-02", "x": 1}]}, [], "texto"])
def test_post_type_and_extra_field_errors_are_422(admin_s, seeded, body):
    r = admin_s.post(body)
    assert r.status_code == 422 and code(r) == "ENTRADA_INVALIDA"
    assert seeded.jobs.count_documents({}) == 0


def test_post_without_inputs_is_409(admin_s, seeded):
    seeded.inventory_reported_snapshots.delete_many({})
    r = admin_s.post(h.RAW)
    assert r.status_code == 409 and code(r) == "INVENTARIO_NO_DISPONIBLE"
    seeded.plan_datasets.delete_many({})
    assert code(admin_s.post(h.RAW)) == "DATASET_NO_DISPONIBLE"


# ------------------------------------------------------------------ lectura
def test_plan_header_and_list(reader_s, plan_id):
    p = reader_s.http.get(f"{BASE}/{plan_id}").json()
    assert p["plan_id"] == plan_id and p["status"] == "completed" and p["label"] == "Plan de compra bajo supuestos"
    assert p["dates"] == {"sales_cutoff": "2026-09-30", "count_date": "2026-10-18", "count_as_of_local": h.AS_OF,
                          "decision_date": "2026-10-18", "month_start": "2026-11-01", "month_end": "2026-11-30",
                          "window_start": "2026-09-03"}
    assert p["distances"]["cutoff_to_month_start"] == 32 and p["distances"]["cutoff_to_month_end"] == 61
    assert p["engine_version"] == engine.ENGINE_VERSION and p["method"] == "promedio_28"
    assert p["params"]["lead_days"] == [7, 14] and p["params"]["reserve_days"] == 7
    assert p["dataset"]["dataset_id"] == h.DATASET_ID and p["snapshot"]["sha256_short"] == "608d15a74a58"
    assert {a["code"] for a in p["assumptions"]} >= {"PEDIDOS_PENDIENTES", "FALTANTE_NO_SE_REPONE", "RESERVA"}
    assert all(a["nature"] in ("SUPUESTO", "DECLARADO") for a in p["assumptions"])
    assert p["provenance"]["parameters"] == "SUPUESTO_EDITABLE" and p["counts"]["products"] == 8
    assert any("desactualizada" in w for w in p["warnings"])
    assert '"_id"' not in json.dumps(p) and "credential" not in json.dumps(p)
    lst = reader_s.http.get(BASE).json()
    assert [i["plan_id"] for i in lst["items"]] == [plan_id] and lst["total"] == 1 and "unavailable_reason" not in lst
    assert set(lst["items"][0]) == {"plan_id", "month", "decision_date", "lead_days", "status", "created_at", "dataset_id",
                                    "snapshot_id", "counts", "version", "label"}
    other = reader_s.http.get(BASE, params={"month": "2026-12"}).json()
    assert other["items"] == [] and other["unavailable_reason"] == "SIN_PLAN"


def test_results_list_server_side_totals_filters_sort_and_pagination(reader_s, plan_id):
    url = f"{BASE}/{plan_id}/results"
    b = reader_s.http.get(url, params={"page_size": 3}).json()
    assert b["total"] == 8 and len(b["items"]) == 3 and b["has_more"] is True
    assert b["status_counts"] == {"all": 8, "OK": 5, "LLEGA_TARDE": 0, "NO_LLEGA_A_TIEMPO": 0, "NO_CALCULABLE": 3}
    assert b["scenario_status_counts"]["7"]["NO_CALCULABLE"] == 3 and "total_units" not in json.dumps(b)
    assert [i["producto_id"] for i in reader_s.http.get(url, params={"page_size": 3, "page": 3}).json()["items"]] == \
        ["1000007", "1000008"]
    nc = reader_s.http.get(url, params={"status": "NO_CALCULABLE"}).json()
    assert [i["producto_id"] for i in nc["items"]] == ["1000005", "1000006", "1000008"] and nc["total"] == 3
    assert nc["status_counts"]["all"] == 8                                   # totales por estado no dependen del filtro de estado
    q = reader_s.http.get(url, params={"q": "10000"}).json()
    assert q["total"] == 8
    assert [i["producto_id"] for i in reader_s.http.get(url, params={"q": "1000003"}).json()["items"]] == ["1000003"]
    assert reader_s.http.get(url, params={"q": "producto 1000002"}).json()["total"] == 1
    assert reader_s.http.get(url, params={"q": "1.*"}).json()["total"] == 0              # literal, no regex
    assert [i["producto_id"] for i in reader_s.http.get(url, params={"sort": "-producto_id", "page_size": 2}).json()["items"]] \
        == ["1000008", "1000007"]
    ordered = reader_s.http.get(url, params={"sort": "-purchase_7", "status": "OK"}).json()["items"]
    assert [i["scenarios"]["7"]["purchase_qty"] for i in ordered] == [88, 88, 60, 0, 0]
    assert ordered[0]["producto_id"] in ("1000003", "1000004")
    assert [i["count_stock"]["libre"] for i in reader_s.http.get(url, params={"sort": "libre", "status": "OK"}).json()["items"]] \
        == [0, 10, 30, 40, 500]
    assert reader_s.http.get(url, params={"sort": "forecast", "status": "OK"}).json()["items"][-1]["producto_id"] != "1000007"


def test_results_item_contract_and_values(reader_s, plan_id):
    items = {i["producto_id"]: i for i in reader_s.http.get(f"{BASE}/{plan_id}/results").json()["items"]}
    a = items["1000001"]
    assert set(a) == {"producto_id", "producto", "categoria", "unidad_descripcion", "unidad_reporte", "status", "reason",
                      "forecast", "count_stock", "scenarios"}
    assert a["forecast"] == {"daily": "2", "daily_exact": "2", "month_total": "60", "month_days": 30,
                             "window_start": "2026-09-03", "window_end": "2026-09-30", "sum_28": "56", "days_valid": 28,
                             "zero_reason": None}
    assert a["count_stock"] == {"libre": 40, "as_of_local": h.AS_OF} and set(a["scenarios"]) == {"7", "14"}
    s7 = a["scenarios"]["7"]
    assert s7["arrival_date"] == "2026-10-25" and s7["purchase_qty"] == 60 and s7["status"] == "OK"
    assert s7["stock_at_arrival"] == "28" and s7["stock_month_start"] == "74" and s7["end_stock"] == "14"
    assert s7["served_month"] == "60" and s7["shortage_month"] == "0" and s7["shortage_before_month"] == "0"
    assert not {"series", "events", "breakdown", "explanation"} & set(s7)           # la lista es liviana
    assert items["1000007"]["forecast"]["zero_reason"] == "SIN_VENTAS_EN_VENTANA"
    assert items["1000007"]["forecast"]["daily"] == "0" and items["1000007"]["scenarios"]["14"]["purchase_qty"] == 0
    nc = items["1000005"]
    assert nc["status"] == "NO_CALCULABLE" and nc["reason"] == "SIN_CONTEO" and nc["count_stock"]["libre"] is None
    assert nc["scenarios"]["7"]["purchase_qty"] is None
    assert items["1000006"]["forecast"] is None and items["1000008"]["reason"] == "UNIDAD_INCOMPATIBLE"
    assert items["1000003"]["scenarios"]["14"]["shortage_before_month"] == "16"


def test_detail_has_series_events_breakdown_and_explanation_that_reproduce_the_quantity(reader_s, plan_id):
    d = reader_s.http.get(f"{BASE}/{plan_id}/results/1000001").json()
    s = d["scenarios"]["7"]
    assert len(s["series"]) == 43 and s["series"][0]["fecha"] == "2026-10-19" and s["series"][-1]["fecha"] == "2026-11-30"
    first = s["series"][0]
    assert set(first) == {"fecha", "inicio", "recepciones", "disponible", "demanda", "atendida", "faltante", "fin"}
    assert first["inicio"] == "40" and first["fin"] == "38"
    arr = next(r for r in s["series"] if r["fecha"] == "2026-10-25")
    assert arr["inicio"] == "28" and arr["recepciones"] == "60" and arr["disponible"] == "88" and arr["fin"] == "86"
    for r in s["series"]:
        assert F(r["inicio"]) + F(r["recepciones"]) - F(r["atendida"]) == F(r["fin"])
        assert F(r["atendida"]) + F(r["faltante"]) == F(r["demanda"])
    assert [e_["type"] for e_ in s["events"]][:3] == ["CONTEO", "DECISION_ORDEN", "LLEGADA_ORDEN"]
    assert s["event_order"] == "recepciones(t) -> demanda(t)"
    bd = s["breakdown"]
    assert (bd["bridge_demand"], bd["month_demand"], bd["reserve"], bd["total_need"], bd["stock_at_arrival"]) \
        == ("14", "60", "14", "88", "28")
    assert bd["purchase_qty"] == 60 and bd["qty_unrounded_exact"] == "60" and bd["binding"] == "final"
    steps = {st["key"]: st for st in s["explanation"]}
    assert all(set(st) >= {"label", "text", "value"} for st in s["explanation"])
    need = F(steps["bridge_demand"]["exact"]) + F(steps["month_demand"]["exact"]) + F(steps["reserve"]["exact"])
    assert need == F(steps["total_need"]["exact"])
    assert need + F(steps["less_stock"]["exact"]) + F(steps["less_pending"]["exact"]) == F(steps["final_need"]["exact"]) == 60
    assert steps["purchase_qty"]["value"] == "60"
    assert d["forecast"]["sum_28_exact"] == "56" and d["forecast"]["daily_exact"] == "2"
    # cantidad fraccionaria: el detalle trae la forma exacta p/q ademas del decimal
    nc = reader_s.http.get(f"{BASE}/{plan_id}/results/1000005").json()
    assert nc["scenarios"]["7"]["series"] == [] and nc["scenarios"]["7"]["explanation"][0]["key"] == "no_calculable"


def test_fractional_quantities_show_decimal_and_exact(admin_s, reader_s, seeded, tmp_path):
    seeded.plan_sales.delete_many({"producto_id": "1000001"})
    seeded.plan_sales.insert_one(h._sale(h.DATASET_ID, 777, "1000001", date(2026, 9, 30), "1"))   # 1 unidad en 28 dias
    pid = admin_s.post(h.RAW).json()["plan_id"]
    assert worker(seeded, tmp_path)["status"] == "completed"
    d = reader_s.http.get(f"{BASE}/{pid}/results/1000001").json()
    assert d["forecast"]["daily"] == "0.036" and d["forecast"]["daily_exact"] == "1/28" and d["forecast"]["month_total_exact"] == "15/14"
    s = d["scenarios"]["7"]
    assert s["reserve_qty"] == "0.25" and s["reserve_qty_exact"] == "1/4"
    assert s["purchase_qty"] == 0                       # 40 unidades alcanzan para todo el mes: cero calculado


def test_unknown_or_invisible_plans_and_products_are_404(reader_s, seeded, plan_id):
    assert reader_s.http.get(f"{BASE}/plan-inexistente").status_code == 404
    assert code(reader_s.http.get(f"{BASE}/plan-inexistente/results")) == "NO_ENCONTRADO"
    assert reader_s.http.get(f"{BASE}/{plan_id}/results/9999999").status_code == 404
    seeded.plan_runs.insert_one({"plan_id": "plan-staging", "status": "staging", "month": "2026-11"})
    seeded.plan_runs.insert_one({"plan_id": "plan-failed", "status": "failed", "month": "2026-11"})
    seeded.plan_results.insert_one({"plan_id": "plan-staging", "producto_id": "1000001"})
    for pid in ("plan-staging", "plan-failed"):
        assert reader_s.http.get(f"{BASE}/{pid}").status_code == 404
        assert reader_s.http.get(f"{BASE}/{pid}/results").status_code == 404
        assert reader_s.http.get(f"{BASE}/{pid}/results/1000001").status_code == 404
    assert [p["plan_id"] for p in reader_s.http.get(BASE).json()["items"]] == [plan_id]


@pytest.mark.parametrize("path,params", [
    ("/{p}/results", {"q": "{\"$ne\":1}"}), ("/{p}/results", {"q": "$where"}), ("/{p}/results", {"q": "a[0]"}),
    ("/{p}/results", {"q": "x" * 101}), ("/{p}/results", {"$ne": "1"}), ("/{p}/results", {"status": "TODOS"}),
    ("/{p}/results", {"status": "$ne"}), ("/{p}/results", {"sort": "producto_id;drop"}), ("/{p}/results", {"sort": "categoria"}),
    ("/{p}/results", {"sort": "purchase_99"}), ("/{p}/results", {"sort": "$where"}), ("/{p}/results", {"page": "0"}),
    ("/{p}/results", {"page_size": "201"}), ("/{p}/results", {"desconocido": "1"}), ("/{p}/results", {"libre[$gt]": "0"}),
    ("", {"month": "2026-13"}), ("", {"month": "{$ne:1}"}), ("", {"x": "1"}), ("/inputs", {"x": "1"}),
    ("/{p}", {"x": "1"}), ("/{p}/results/1000001", {"x": "1"})])
def test_invalid_or_injected_params_are_422(reader_s, plan_id, path, params):
    r = reader_s.http.get(BASE + path.format(p=plan_id), params=params)
    assert r.status_code == 422 and code(r) == "ENTRADA_INVALIDA", (path, params)


def test_repeated_param_and_bad_ids_are_422(reader_s, plan_id):
    assert reader_s.http.get(f"{BASE}/{plan_id}/results?status=OK&status=OK").status_code == 422
    assert reader_s.http.get(f"{BASE}/a$b").status_code == 422
    assert reader_s.http.get(f"{BASE}/{plan_id}/results/a$b").status_code == 422
    assert reader_s.http.get(f"{BASE}/{plan_id}/results/{'1' * 40}").status_code == 422


def test_reading_and_generating_leave_other_collections_untouched(admin_s, reader_s, seeded, tmp_path):
    before = h.fingerprint(seeded)
    pid = admin_s.post(h.RAW).json()["plan_id"]
    worker(seeded, tmp_path)
    for p in ("", "/inputs", f"/{pid}", f"/{pid}/results", f"/{pid}/results/1000001"):
        assert reader_s.http.get(BASE + p).status_code == 200
    assert h.fingerprint(seeded) == before
    plan_docs = seeded.plan_results.find({"plan_id": pid}).to_list()
    reader_s.http.get(f"{BASE}/{pid}/results", params={"sort": "-forecast"})
    assert plan_docs == seeded.plan_results.find({"plan_id": pid}).to_list()
