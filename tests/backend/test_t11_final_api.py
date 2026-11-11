"""T11A: corrida final_evaluation en la API de lectura (docs/T11_CONTRATO.md §1-§3). Base temporal df_test_<uuid>
con datos SINTETICOS de prueba; solo lectura, sin ejecutar modelos."""
from __future__ import annotations

import json
from datetime import date

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.config import get_settings
from backend.app.data import common
from backend.app.db import get_db
from backend.app.errors import install_error_handlers
from backend.app.routers import auth, backtests, forecasts, recommendations, runs
from tests.backend import final_fixture as fx
from tests.backend import test_auth_common as ac
from tests.backend.test_auth_common import login

pytestmark = pytest.mark.mongo

db, settings, users = ac.db, ac.settings, ac.users


@pytest.fixture
def ids(db):
    return fx.seed(db)


@pytest.fixture
def app(db, settings, users, ids):
    application = FastAPI()
    install_error_handlers(application)
    for module in (auth, runs, forecasts, backtests, recommendations):
        application.include_router(module.router, prefix="/api/v1")
    application.dependency_overrides[get_db] = lambda: db
    application.dependency_overrides[get_settings] = lambda: settings
    return application


def _session(app, user):
    c = TestClient(app, base_url="http://testserver")
    assert login(c, user).status_code == 200
    return c


@pytest.fixture
def reader(app):
    c = _session(app, "luis")
    yield c
    c.close()


@pytest.fixture
def admin(app):
    c = _session(app, "ana")
    yield c
    c.close()


@pytest.fixture
def anon(app):
    with TestClient(app, base_url="http://testserver") as c:
        yield c


def get(c, url):
    return c.get("/api/v1" + url)


def code(r):
    return r.json()["error"]["code"]


# ---------------------------------------------------------------- corridas y tipos
def test_runs_list_exposes_three_kinds_and_pointer_stays_historical(reader, ids):
    r = get(reader, "/runs").json()
    kinds = {i["run_id"]: i["kind"] for i in r["items"]}
    assert kinds == {fx.HIST_ID: "historical_development", fx.GEN_ID: "generated_baseline",
                     fx.FINAL_ID: "final_evaluation"}
    active = [i["run_id"] for i in r["items"] if i["is_active"]]
    assert active == [fx.HIST_ID]            # la final no activa el puntero
    only_hist = next(i for i in r["items"] if i["run_id"] == fx.HIST_ID)
    assert only_hist["warnings"] == [] and only_hist["final_package"] is None


def test_final_run_detail_summary_and_warnings(reader):
    d = get(reader, f"/runs/{fx.FINAL_ID}").json()
    assert d["kind"] == "final_evaluation" and d["is_active"] is False
    assert d["evaluation_period"] == {"start": "2026-08-01", "end": "2026-08-21", "single_block": True}
    fp = d["final_package"]
    assert fp["seal_short"] == fx.SEAL[:12] and fp["audit_ok"] is True
    assert list(fp["phases"]) == fx.PHASES and fp["corrections"][0]["code"] == "R11"
    text = " ".join(d["warnings"])
    assert "WAPE no es exactitud" in text and "78 %" in text
    assert "Categoría = suma de unidades base heterogéneas" in text
    assert "Un solo bloque de 21 días; sin inferencia de ganador" in text
    assert "no pronostica octubre" in text
    assert d["method"]["rf_declared_winner"] is False
    dump = json.dumps(d)
    assert "idempotency" not in dump and "secreta" not in dump and "C:\\" not in dump


def test_non_final_runs_have_no_final_package(reader):
    for rid in (fx.HIST_ID, fx.GEN_ID):
        d = get(reader, f"/runs/{rid}").json()
        assert d["final_package"] is None and d["warnings"] == []


# ---------------------------------------------------------------- fechas
def test_historical_dates_within_allowed_range(reader):
    assert get(reader, "/forecasts?run_id=" + fx.HIST_ID + "&to=2026-10-21").status_code == 200
    r = get(reader, "/forecasts?run_id=" + fx.HIST_ID + "&to=2026-10-22")
    assert r.status_code == 422 and code(r) == "FUERA_DE_RANGO"
    r = get(reader, "/forecasts?from=2026-10-22")
    assert r.status_code == 422 and code(r) == "FUERA_DE_RANGO"
    r = get(reader, "/forecasts?run_id=" + fx.GEN_ID + "&to=2026-10-22")
    assert r.status_code == 422 and code(r) == "FUERA_DE_RANGO"
    assert get(reader, "/forecasts?run_id=" + fx.HIST_ID + "&to=2026-07-31").status_code == 200


def test_unknown_run_with_out_of_range_date_keeps_general_barrier(reader):
    r = get(reader, "/forecasts?run_id=no-existe&to=2026-10-22")
    assert r.status_code == 422 and code(r) == "FUERA_DE_RANGO"
    assert get(reader, "/forecasts?run_id=no-existe").status_code == 404


def test_final_run_accepts_up_to_aug_21_only(reader):
    base = f"/forecasts?run_id={fx.FINAL_ID}&level=sku&page_size=200"
    r = get(reader, base + "&from=2026-08-01&to=2026-08-21")
    assert r.status_code == 200 and r.json()["total"] == 42            # 2 SKU x 21 dias
    assert get(reader, base + "&to=2026-08-22").status_code == 422
    assert code(get(reader, base + "&to=2026-08-22")) == "ENTRADA_INVALIDA"
    assert get(reader, base + "&from=2026-08-30").status_code == 422
    assert code(get(reader, base + "&from=2026-08-10&to=2026-08-01")) == "ENTRADA_INVALIDA"
    assert get(reader, base + "&from=2026-08-22&to=2026-08-22").status_code == 422


def test_final_forecasts_content_cohorts_unevaluable_and_relabel(reader):
    r = get(reader, f"/forecasts?run_id={fx.FINAL_ID}&level=sku&page_size=200").json()
    assert {i["run_id"] for i in r["items"]} == {fx.FINAL_ID}          # relabel del id de intento
    assert r["run"]["kind"] == "final_evaluation" and "warnings" in r and r["unit"] == "unidad base"
    assert {i["cohorte"] for i in r["items"]} == {"primaria", "historia_corta"}
    assert all(i["run_kind"] == "final_evaluation" for i in r["items"])
    assert all("2026-08-01" <= i["target_date"] <= "2026-08-21" for i in r["items"])
    non = [i for i in r["items"] if i["evaluable"] is False]
    assert len(non) == 1 and non[0]["target_date"] == "2026-08-15" and non[0]["observed"] is None
    cat = get(reader, f"/forecasts?run_id={fx.FINAL_ID}&level=categoria&cohorte=primaria").json()
    assert cat["total"] == 21
    hc = get(reader, f"/forecasts?run_id={fx.FINAL_ID}&cohorte=historia_corta&page_size=5").json()
    assert hc["total"] == 21 and len(hc["items"]) == 5 and hc["has_more"] is True


def test_pagination_and_sort_unchanged(reader):
    p1 = get(reader, f"/forecasts?run_id={fx.FINAL_ID}&page=1&page_size=10&sort=-target_date").json()
    p2 = get(reader, f"/forecasts?run_id={fx.FINAL_ID}&page=2&page_size=10&sort=-target_date").json()
    assert p1["items"][0]["target_date"] == "2026-08-21"
    assert p1["page"] == 1 and p2["page"] == 2 and p1["total"] == 42
    ids1 = {(i["entity_id"], i["target_date"]) for i in p1["items"]}
    assert not ids1 & {(i["entity_id"], i["target_date"]) for i in p2["items"]}
    assert get(reader, "/forecasts?sort=bogus").status_code == 422
    assert get(reader, "/forecasts?page_size=500").status_code == 422
    assert get(reader, "/forecasts?foo=1").status_code == 422
    hist = get(reader, "/forecasts").json()                            # sin run_id -> la activa (historica)
    assert hist["run"]["run_id"] == fx.HIST_ID and hist["total"] == 21


def test_generated_run_untouched(reader):
    r = get(reader, f"/forecasts?run_id={fx.GEN_ID}").json()
    assert r["total"] == 3 and r["items"][0]["observed"] is None and r["items"][0]["run_id"] == fx.GEN_ID
    assert "warnings" not in r


# ---------------------------------------------------------------- recomendaciones
def test_final_recommendations_unavailable_with_reason(reader):
    r = get(reader, f"/recommendations?run_id={fx.FINAL_ID}")
    assert r.status_code == 200
    b = r.json()
    assert b["items"] == [] and b["total"] == 0
    assert b["unavailable_reason"] == "RECOMENDACION_NO_VALIDADA_PARA_ESTE_ORIGEN"
    assert b["see_run"] == fx.HIST_ID and b["run"]["kind"] == "final_evaluation"
    assert "99" not in json.dumps(b["items"])
    assert get(reader, f"/recommendations/9?run_id={fx.FINAL_ID}").status_code == 404


def test_other_runs_recommendations_unchanged(reader):
    h = get(reader, f"/recommendations?run_id={fx.HIST_ID}").json()
    assert h["total"] == 1 and "unavailable_reason" not in h
    g = get(reader, f"/recommendations?run_id={fx.GEN_ID}").json()
    assert g["total"] == 1 and g["items"][0]["run_id"] == fx.GEN_ID


# ---------------------------------------------------------------- backtests
def test_final_backtest_structure_and_views(reader):
    bid = f"bt-{fx.FINAL_ID}"
    d = get(reader, f"/backtests/{bid}").json()
    assert d["backtest_id"] == bid and d["run_id"] == fx.FINAL_ID and d["kind"] == "final_evaluation"
    for key in ("predictive", "selection", "coverage", "simulation", "simulation_differences", "assumptions"):
        assert key in d
    assert d["selection"]["rf_declared_winner"] is False and d["provenance"] == "SYNTHETIC_NOT_REAL_INVENTORY"
    assert "no corresponde al inventario real" in d["disclaimer"]
    p = get(reader, f"/backtests/{bid}?view=predictive").json()
    assert "predictive" in p and "simulation" not in p
    s = get(reader, f"/backtests/{bid}?view=simulation").json()
    assert "simulation" in s and "predictive" not in s and "assumptions" in s
    assert get(reader, f"/backtests/{bid}?view=otra").status_code == 422
    assert get(reader, "/backtests/bt-no-existe").status_code == 404
    lst = get(reader, f"/backtests?run_id={fx.FINAL_ID}").json()
    assert lst["total"] == 1 and lst["items"][0]["backtest_id"] == bid
    allbt = get(reader, "/backtests").json()
    assert {i["kind"] for i in allbt["items"]} == {"T07_desarrollo", "final_evaluation"}
    assert get(reader, f"/backtests/bt-{fx.HIST_ID}").json()["kind"] == "T07_desarrollo"


# ---------------------------------------------------------------- roles
def test_roles_reader_and_admin_read_anonymous_denied(reader, admin, anon):
    for c in (reader, admin):
        assert get(c, f"/runs/{fx.FINAL_ID}").status_code == 200
        assert get(c, f"/forecasts?run_id={fx.FINAL_ID}").status_code == 200
        assert get(c, f"/recommendations?run_id={fx.FINAL_ID}").status_code == 200
        assert get(c, f"/backtests/bt-{fx.FINAL_ID}").status_code == 200
    for url in (f"/runs/{fx.FINAL_ID}", f"/forecasts?run_id={fx.FINAL_ID}",
                f"/recommendations?run_id={fx.FINAL_ID}", f"/backtests/bt-{fx.FINAL_ID}"):
        assert get(anon, url).status_code == 401


def test_general_barrier_constants_unchanged():
    assert common.LAST_ALLOWED_DATE.isoformat() == "2026-10-21"
    with pytest.raises(Exception) as e:
        common.check_dates(None, date(2026, 10, 22))
    assert getattr(e.value, "code", "") == "FUERA_DE_RANGO"
