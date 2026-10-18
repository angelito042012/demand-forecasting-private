"""Rutas de lectura T08 §3 sobre una base temporal con la corrida REAL publicada."""
from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal

import pytest
from bson.decimal128 import Decimal128
from fastapi.testclient import TestClient

from backend.app.auth.deps import CurrentUser, require_user
from backend.app.data import common
from backend.app.db import get_db
from backend.app.errors import ApiError
from backend.app.main import create_app
from pipeline.publish.publisher import publish
from tests.publish.helpers import (
    make_catalog,
    make_signals,
    needs_artifacts,
    real_source,
    temp_db,
)

pytestmark = [pytest.mark.mongo, pytest.mark.realdata, needs_artifacts]

SHA_A, SHA_B, SHA_AUG = "a" * 64, "b" * 64, "c" * 64
IMPORT_A, IMPORT_AUG = "1" * 32, "2" * 32


def _seed_observed(db):
    def imp(iid, sha, mes, archivo, **kw):
        base = {"import_id": iid, "archivo": archivo, "sha256": sha, "mes": mes, "estado": "completed",
                "noop": False, "dry_run": False, "filas_leidas": 10, "ventas_aceptadas": 6,
                "notas_credito": 1, "rechazadas": 3, "insertadas": 10, "ya_existentes": 0, "en_conflicto": 0,
                "rechazos_por_motivo": {"FECHA_INVALIDA": 2, "CANTIDAD_INVALIDA": 1}, "error": None,
                "iniciado_utc": datetime(2026, 10, 17, 12, 0, 0), "finalizado_utc": datetime(2026, 10, 17, 12, 1, 0)}
        db.imports.insert_one({**base, **kw})

    imp(IMPORT_A, SHA_A, "2026-06", "C:\\Users\\privado\\junio.xlsx")
    imp("3" * 32, SHA_A, "2026-06", "junio.xlsx", noop=True)
    imp(IMPORT_AUG, SHA_AUG, "2026-08", "agosto.xlsx")

    def sale(fecha, cant, imp_, cat, sha, sku="1"):
        return {"linea_id": f"{fecha}{cant}{sha[:2]}{sku}{cat}", "fecha": fecha, "sku": sku, "cantidad_base": cant,
                "importe": Decimal128(Decimal(imp_)), "categoria_original": cat,
                "sources": [{"source_sha256": sha, "source_file": "x", "source_row": 1}]}

    db.sales.insert_many([
        sale("2026-06-01", 2, "10.50", "CAT A", SHA_A), sale("2026-06-02", 3, "4.25", "CAT A", SHA_A),
        sale("2026-06-02", 1, "5.00", "CAT B", SHA_A, sku="2"),
        sale("2026-06-07", 9, "99.00", "CAT A", SHA_A),             # dia enmascarado: no se suma
        sale("2026-06-03", 7, "70.00", "CAT A", SHA_B),             # fuente no aprobada: no se suma
        sale("2026-08-01", 5, "50.00", "CAT A", SHA_AUG),           # agosto: jamas
    ])
    db.credit_notes.insert_one({**sale("2026-06-02", -1, "-5.00", "CAT A", SHA_A)})


@pytest.fixture(scope="module")
def env():
    src = real_source()
    cat, fp = make_catalog(src)
    with temp_db() as db:
        res = publish(db, src, cat, fp, make_signals(src))
        _seed_observed(db)
        app = create_app()
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_user] = lambda: CurrentUser("lector1", "lector", "x")
        yield TestClient(app, raise_server_exceptions=False), db, res, app


def _get(env, url):
    return env[0].get("/api/v1" + url)


def test_runs_list_and_detail(env):
    r = _get(env, "/runs").json()
    assert r["total"] == 1 and r["page"] == 1 and r["has_more"] is False
    it = r["items"][0]
    assert it["run_label"] == "Corrida histórica de desarrollo al 10/07/2026" and it["is_active"] is True
    assert it["cutoff"] == "2026-07-10" and it["age_days_at_view"] >= 0
    assert it["generated_at"].endswith("Z") and it["published_at"].endswith("Z")
    d = _get(env, f"/runs/{it['run_id']}").json()
    assert d["method"]["chosen"] == "promedio_28" and d["coverage"]["skus_sin_snapshot"] == 300
    assert d["code"]["commit"] and all(set(a) == {"name", "sha256", "size_bytes"} for a in d["artifacts"])
    text = json.dumps(d)
    assert "C:\\" not in text and "artifacts/private" not in text and "idempotency" not in text
    assert _get(env, "/runs/no-existe").status_code == 404
    assert _get(env, "/runs?status=staging").status_code == 422


def test_incomplete_runs_are_ignored_by_readers(env):
    _, db, res, _ = env
    for rid, st in (("run-staging", "staging"), ("run-failed", "failed")):
        db.runs.insert_one({"run_id": rid, "status": st, "kind": "historical_development", "cutoff": "2026-07-10",
                            "idempotency_key": rid, "published_at": datetime(2030, 1, 1)})
        db.forecasts.insert_one({"run_id": rid, "level": "sku", "entity_id": "9|1", "sku": "9", "categoria": "X",
                                 "target_date": "2026-07-11", "pred": {"promedio_28": 1, "rf_categoria_distribuido": 1,
                                                                       "cero": 0}})
        db.backtests.insert_one({"backtest_id": f"bt-{rid}", "run_id": rid, "kind": "T07_desarrollo"})
    try:
        assert [i["run_id"] for i in _get(env, "/runs").json()["items"]] == [res.run_id]
        assert _get(env, "/runs/run-staging").status_code == 404
        assert _get(env, "/forecasts?run_id=run-failed").status_code == 404
        assert _get(env, "/recommendations?run_id=run-staging").status_code == 404
        assert _get(env, "/backtests/bt-run-failed").status_code == 404
        assert [b["run_id"] for b in _get(env, "/backtests").json()["items"]] == [res.run_id]
        assert _get(env, "/forecasts?page_size=1").json()["run"]["run_id"] == res.run_id
        # puntero roto hacia una corrida incompleta: se usa la ultima completa
        db.run_pointer.update_one({"_id": "active"}, {"$set": {"run_id": "run-failed"}})
        assert _get(env, "/forecasts?page_size=1").json()["run"]["run_id"] == res.run_id
    finally:
        db.run_pointer.update_one({"_id": "active"}, {"$set": {"run_id": res.run_id}})
        db.runs.delete_many({"run_id": {"$in": ["run-staging", "run-failed"]}})
        db.forecasts.delete_many({"run_id": {"$in": ["run-staging", "run-failed"]}})
        db.backtests.delete_many({"run_id": {"$in": ["run-staging", "run-failed"]}})


def test_forecasts_pagination_filters_and_sort(env):
    r = _get(env, "/forecasts?page_size=50&page=2").json()
    assert r["total"] == 76587 and len(r["items"]) == 50 and r["page"] == 2 and r["has_more"] is True
    assert r["unit"] == "unidad base" and r["run"]["run_label"].startswith("Corrida histórica")
    it = r["items"][0]
    assert set(it["pred"]) == {"promedio_28", "rf_categoria_distribuido", "cero"}
    assert it["chosen_method"] == "promedio_28" and it["provenance"] == "OBSERVED_EXCEL" and "_id" not in it
    s = _get(env, "/forecasts?sku=1010004").json()
    assert s["total"] == 21 and {i["sku"] for i in s["items"]} == {"1010004"}
    assert [i["target_date"] for i in s["items"]] == sorted(i["target_date"] for i in s["items"])
    c = _get(env, "/forecasts?level=categoria&categoria=CAT3&from=2026-07-11&to=2026-07-13").json()
    assert c["total"] == 3 and all(i["level"] == "categoria" for i in c["items"])
    d = _get(env, "/forecasts?sort=-pred_chosen&page_size=5").json()["items"]
    assert [i["pred"]["promedio_28"] for i in d] == sorted((i["pred"]["promedio_28"] for i in d), reverse=True)
    assert _get(env, "/forecasts?cohorte=historia_corta&page_size=1").json()["total"] == 8337


@pytest.mark.parametrize("qs", [
    "sort=pred.cero", "sort=$natural", "page=0", "page_size=201", "page_size=0", "level=otro", "cohorte=x",
    "from=2026-13-01", "unknown=1", "sku=a b", "page=1&page=2", "from=2026-07-31&to=2026-01-01",
    "from=2025-01-01&to=2026-07-31",
])
def test_forecasts_invalid_params_422(env, qs):
    r = _get(env, "/forecasts?" + qs)
    assert r.status_code == 422 and r.json()["error"]["code"] == "ENTRADA_INVALIDA"


@pytest.mark.parametrize("qs", ["from=2026-08-01", "to=2026-08-15", "from=2026-07-01&to=2026-09-01"])
def test_august_is_rejected(env, qs):
    for route in ("/forecasts?", "/sales/summary?"):
        r = _get(env, route + qs)
        assert r.status_code == 422 and r.json()["error"]["code"] == "AGOSTO_RESERVADO"


@pytest.mark.parametrize("qs", [
    "sku[$ne]=x", "sku=%7B%22%24gt%22%3A%22%22%7D", "sku=$ne", "categoria=%24ne", "categoria=%7B%22%24gt%22%3A1%7D",
    "run_id=%7B%22%24ne%22%3Anull%7D", "run_id[$ne]=x", "$where=1", "sort[$gt]=1",
])
def test_injection_has_no_effect(env, qs):
    for route in ("/forecasts?", "/recommendations?", "/backtests?"):
        r = _get(env, route + qs)
        assert r.status_code == 422, (route, qs, r.text[:120])
    assert _get(env, "/forecasts?sku=1010004").json()["total"] == 21        # la base no se alteró


def test_recommendations_list_detail_and_filters(env):
    r = _get(env, "/recommendations?page_size=10&sort=-order_qty").json()
    assert r["total"] == 3647 and r["provenance"] == "SYNTHETIC_NOT_REAL_INVENTORY"
    assert r["disclaimer"].startswith("Inventario simulado con supuestos")
    q = [i["order_qty"] for i in r["items"]]
    assert q == sorted(q, reverse=True) and q[0] > 0
    ok_orders = _get(env, "/recommendations?only_orders=true&status=ok").json()
    assert ok_orders["total"] == 582 and all(i["order_qty"] > 0 for i in ok_orders["items"])
    ss = _get(env, "/recommendations?status=sin_snapshot&page_size=1").json()
    assert ss["total"] == 300 and ss["items"][0]["order_qty"] is None
    one = _get(env, "/recommendations/1010004").json()
    assert one["status"] == "ok" and one["almacen"] == "1" and "Pedido sugerido" in one["explanation"]
    assert one["currency"] == "PEN" and one["unit"] == "unidad base" and one["run"]["is_active"] is True
    nos = _get(env, "/recommendations?status=sin_snapshot&page_size=1").json()["items"][0]["sku"]
    d = _get(env, f"/recommendations/{nos}").json()
    assert d["status"] == "sin_snapshot" and d["on_hand"] is None and "no se supone stock cero" in d["reason"]
    assert _get(env, "/recommendations/999999999").status_code == 404
    assert _get(env, "/recommendations/1010004?almacen=9").status_code == 404
    assert _get(env, "/recommendations/1010004?almacen=%24ne").status_code == 422
    assert _get(env, "/recommendations?sort=-sku").status_code == 422
    assert _get(env, "/recommendations?status=otro").status_code == 422


def test_recommendations_no_orders_view(env):
    """UX01: vista «sin necesidad de reponer» filtrada en el servidor (SKU con inventario simulado y pedido 0)."""
    ok = _get(env, "/recommendations?status=ok&page_size=1").json()["total"]
    con = _get(env, "/recommendations?only_orders=true&status=ok&page_size=1").json()["total"]
    sin = _get(env, "/recommendations?no_orders=true&page_size=50").json()
    assert sin["total"] == ok - con and sin["total"] > 0
    assert all(i["status"] == "ok" and i["order_qty"] == 0 for i in sin["items"])  # ni pedidos positivos ni sin snapshot (null)
    assert sin["provenance"] == "SYNTHETIC_NOT_REAL_INVENTORY" and sin["disclaimer"].startswith("Inventario simulado con supuestos")
    assert _get(env, "/recommendations?no_orders=true&only_orders=true").status_code == 422
    assert _get(env, "/recommendations?no_orders=true&status=sin_snapshot").json()["total"] == 0  # sin snapshot nunca es «sin necesidad»


def test_backtests_views(env):
    lst = _get(env, "/backtests").json()
    assert lst["total"] == 1
    bid = lst["items"][0]["backtest_id"]
    assert set(lst["items"][0]) >= {"backtest_id", "kind", "label", "folds", "created"}
    a = _get(env, f"/backtests/{bid}").json()
    assert a["provenance"] == "SYNTHETIC_NOT_REAL_INVENTORY" and a["scenario_id"] and a["disclaimer"]
    assert len(a["simulation"]) == 27 and a["selection"]["cumple_regla"] is False and "predictive" in a
    assert a["assumptions"]["factor_costo_sobre_mediana_precio"] == 0.65
    p = _get(env, f"/backtests/{bid}?view=predictive").json()
    assert "predictive" in p and "simulation" not in p
    s = _get(env, f"/backtests/{bid}?view=simulation").json()
    assert "simulation" in s and "predictive" not in s and s["disclaimer"]
    assert _get(env, f"/backtests/{bid}?view=otro").status_code == 422
    assert _get(env, "/backtests/no-existe").status_code == 404


def test_imports_list_and_detail_hide_internals(env):
    r = _get(env, "/imports").json()
    assert r["total"] == 2                                   # sin la repeticion no-op
    by_mes = {i["mes"]: i for i in r["items"]}
    assert by_mes["2026-06"]["archivo"] == "junio.xlsx"       # nombre base, sin ruta local
    assert by_mes["2026-06"]["ventas_aceptadas"] == 6 and by_mes["2026-06"]["reservado_prueba_final"] is False
    assert by_mes["2026-08"]["ventas_aceptadas"] is None and by_mes["2026-08"]["reservado_prueba_final"] is True
    assert _get(env, "/imports?mes=2026-06").json()["total"] == 1
    assert _get(env, "/imports?mes=2026-13").status_code == 422
    d = _get(env, f"/imports/{IMPORT_A}").json()
    assert d["rechazos_por_motivo"] == {"FECHA_INVALIDA": 2, "CANTIDAD_INVALIDA": 1}
    assert d["sha256_abreviado"] == "a" * 12 and d["conflictos_abiertos"] == 0
    assert {"codigo": "RECHAZO_FECHA_INVALIDA", "n": 2} in d["incidencias"]
    assert "sha256" not in d and "C:\\" not in json.dumps(d)
    assert _get(env, f"/imports/{IMPORT_AUG}").json()["rechazos_por_motivo"] == {}
    assert _get(env, "/imports/" + "9" * 32).status_code == 404
    assert _get(env, "/imports/%24ne").status_code == 422


def test_sales_summary_approved_sources_and_excluded_days(env):
    r = _get(env, "/sales/summary?from=2026-06-01&to=2026-07-31&group_by=day").json()
    assert r["provenance"] == "OBSERVED_EXCEL" and r["unit"] == "unidad base" and r["currency"] == "PEN"
    got = {i["key"]: i for i in r["items"]}
    assert set(got) == {"2026-06-01", "2026-06-02"}            # sin 07/06 (mascara), sin fuente no aprobada, sin agosto
    assert got["2026-06-02"] == {"key": "2026-06-02", "lineas_venta": 2, "unidades": 4.0, "importe_pen": 9.25}
    assert [e["fecha"] for e in r["excluded_days"]] == ["2026-06-07"]
    assert r["notas_credito"]["lineas"] == 1 and r["notas_credito"]["importe_pen"] == -5.0
    m = _get(env, "/sales/summary?group_by=month").json()
    assert [i["key"] for i in m["items"]] == ["2026-06"] and m["items"][0]["unidades"] == 6.0
    c = _get(env, "/sales/summary?group_by=category&categoria=CAT%20A").json()
    assert [i["key"] for i in c["items"]] == ["CAT A"]
    assert _get(env, "/sales/summary?group_by=x").status_code == 422
    assert _get(env, "/sales/summary?categoria=%24ne").status_code == 422


def test_all_data_routes_require_user_and_forward_auth_errors(env):
    _, _, _, app = env
    paths = {"/api/v1/imports", "/api/v1/imports/{import_id}", "/api/v1/sales/summary", "/api/v1/runs",
             "/api/v1/runs/{run_id}", "/api/v1/forecasts", "/api/v1/recommendations",
             "/api/v1/recommendations/{sku}", "/api/v1/backtests", "/api/v1/backtests/{backtest_id}"}

    def calls(dep):
        yield dep.call
        for sub in dep.dependencies:
            yield from calls(sub)

    found = set()
    for inc in app.routes:
        router = getattr(inc, "original_router", None)
        for route in (router.routes if router else []):
            full = "/api/v1" + route.path
            if full in paths:
                assert require_user in set(calls(route.dependant)), full
                found.add(full)
    assert found == paths

    def deny():
        raise ApiError(401, "NO_AUTENTICADO", "No autenticado.")

    app.dependency_overrides[require_user] = deny
    try:
        client = TestClient(app, raise_server_exceptions=False)
        for p in ("/runs", "/forecasts", "/recommendations", "/backtests", "/imports", "/sales/summary"):
            assert client.get("/api/v1" + p).status_code == 401
    finally:
        app.dependency_overrides[require_user] = lambda: CurrentUser("lector1", "lector", "x")


def test_age_days_uses_lima_today(env, monkeypatch):
    monkeypatch.setattr(common, "today_lima", lambda: datetime(2026, 10, 17).date())
    assert _get(env, "/runs").json()["items"][0]["age_days_at_view"] == 99
