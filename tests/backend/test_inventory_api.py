"""GET /inventory/reported* (T18 §4) sobre una base temporal con el conteo importado."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from backend.app.auth.deps import CurrentUser, require_user
from backend.app.db import get_db
from backend.app.main import create_app
from pipeline.inventory import reported_count as rc
from pipeline.publish.source import PROJECT_ROOT
from tests.inventory.conftest import build_source
from tests.publish.helpers import temp_db

pytestmark = pytest.mark.mongo

REAL_DIR = PROJECT_ROOT / "artifacts/private/conteo_recibido_20261018_v2"
REAL_GROUP = PROJECT_ROOT / "artifacts/private/datos_preparados_v1/02_grupo/productos.csv"
URL = "/api/v1/inventory/reported"
SNAP_KEYS = {"snapshot_id", "version", "status", "as_of_local", "as_of_utc", "timezone", "warehouse", "nature",
             "independent_verification", "source", "counts", "declared_unknowns", "context", "confirmations",
             "imported_at"}
ITEM_KEYS = {"producto_id", "producto", "categoria", "unidad_reporte", "unidad_descripcion", "libre", "reservada",
             "no_vendible", "fisica_total"}


@pytest.fixture()
def env(tmp_path):
    d, g = build_source(tmp_path)
    with temp_db() as db:
        res = rc.run(d, g, db)
        app = create_app()
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_user] = lambda: CurrentUser("lector1", "lector", "x")
        yield TestClient(app, raise_server_exceptions=False), db, res, app, (tmp_path, d, g)


def test_reader_and_admin_get_exact_schema(env):
    c, res, app = env[0], env[2], env[3]
    for user in (CurrentUser("lector1", "lector", "x"), CurrentUser("admin1", "admin", "x")):
        app.dependency_overrides[require_user] = lambda u=user: u
        r = c.get(URL)
        assert r.status_code == 200
        b = r.json()
        assert set(b) == {"snapshot", "items", "page", "page_size", "total", "has_more", "view_counts",
                          "provenance", "disclaimer"}
        assert set(b["snapshot"]) == SNAP_KEYS and all(set(i) == ITEM_KEYS for i in b["items"])
        s = b["snapshot"]
        assert s["snapshot_id"] == res["snapshot_id"] and s["status"] == "current" and s["version"] == 1
        assert s["as_of_utc"] == "2026-10-18T22:00:00Z" and s["as_of_local"] == "2026-10-18T17:00:00-05:00"
        assert s["timezone"] == "America/Lima" and s["independent_verification"] is False
        assert s["source"] == {"file": "Conteo_sintetico.xlsx", "sha256_short": s["source"]["sha256_short"]}
        assert len(s["source"]["sha256_short"]) == 12 and s["counts"] == {"items": 4, "with_stock": 3, "no_stock": 1}
        assert {u["code"] for u in s["declared_unknowns"]} == {"BRECHA_OCTUBRE", "PEDIDOS_PENDIENTES"}
        assert s["context"] == {"sales_history_end": "2026-09-30"}
        assert b["provenance"] == "INVENTARIO_INFORMADO_POR_LA_EMPRESA" and "no es inventario simulado" in b["disclaimer"]
        assert b["total"] == 4 and b["view_counts"] == {"all": 4, "with_stock": 3, "no_stock": 1}
        assert "sha256\"" not in json.dumps(b) and "csv_sha256" not in json.dumps(b)
        assert "\"_id\"" not in json.dumps(b)


def test_zero_visible_null_not_zero_and_no_multiplication(env):
    c = env[0]
    items = {i["producto_id"]: i for i in c.get(URL).json()["items"]}
    assert list(items) == ["0010001", "0010002", "2010003", "2010004"]     # texto con ceros, orden por codigo
    assert items["2010003"]["libre"] == 0 and items["2010003"]["reservada"] == 0
    assert items["2010004"]["reservada"] is None and items["2010004"]["no_vendible"] is None
    assert items["2010004"]["fisica_total"] is None
    assert items["0010002"]["libre"] == 7 and items["0010002"]["unidad_descripcion"] == "Una caja de 12 unidades"


def test_views_search_sort_and_server_counts(env):
    c = env[0]
    w = c.get(URL, params={"view": "with_stock", "page_size": 2}).json()
    assert w["total"] == 3 and len(w["items"]) == 2 and w["has_more"] is True
    assert w["view_counts"] == {"all": 4, "with_stock": 3, "no_stock": 1}      # del servidor, no de la pagina
    assert [i["producto_id"] for i in c.get(URL, params={"view": "with_stock", "page_size": 2, "page": 2}).json()["items"]] \
        == ["2010004"]
    n = c.get(URL, params={"view": "no_stock"}).json()
    assert [i["producto_id"] for i in n["items"]] == ["2010003"] and n["total"] == 1
    assert [i["producto_id"] for i in c.get(URL, params={"sort": "-libre"}).json()["items"]] \
        == ["2010004", "0010002", "0010001", "2010003"]
    assert next(i["producto_id"] for i in c.get(URL, params={"sort": "libre"}).json()["items"]) == "2010003"
    assert next(i["producto_id"] for i in c.get(URL, params={"sort": "-producto_id"}).json()["items"]) == "2010004"
    assert next(i["producto"] for i in c.get(URL, params={"sort": "-producto"}).json()["items"]) == "PRODUCTO UNO 100 ML"
    q = c.get(URL, params={"q": "00100"}).json()
    assert [i["producto_id"] for i in q["items"]] == ["0010001", "0010002"]
    assert q["view_counts"] == {"all": 2, "with_stock": 2, "no_stock": 0}
    assert [i["producto_id"] for i in c.get(URL, params={"q": "tres"}).json()["items"]] == ["2010003"]
    assert c.get(URL, params={"q": "a.*"}).json()["total"] == 0               # texto literal, no regex
    assert c.get(URL, params={"q": "ZZZ"}).json()["items"] == []


def test_no_snapshot_returns_200_with_reason(env):
    c, db = env[0], env[1]
    db[rc.SNAP_COLL].delete_many({})
    b = c.get(URL).json()
    assert c.get(URL).status_code == 200
    assert b["snapshot"] is None and b["items"] == [] and b["total"] == 0
    assert b["unavailable_reason"] == "SIN_INVENTARIO_INFORMADO" and b["provenance"] == "INVENTARIO_INFORMADO_POR_LA_EMPRESA"
    assert c.get(URL + "/snapshots").json()["items"] == []


def test_snapshot_id_lookup_and_404(env):
    c, db, res = env[0], env[1], env[2]
    assert c.get(URL, params={"snapshot_id": res["snapshot_id"]}).status_code == 200
    r = c.get(URL, params={"snapshot_id": "invrep-inexistente"})
    assert r.status_code == 404 and r.json()["error"]["code"] == "NO_ENCONTRADO"
    # un staging nunca es visible
    db[rc.SNAP_COLL].update_one({"snapshot_id": res["snapshot_id"]}, {"$set": {"status": "staging"}})
    assert c.get(URL, params={"snapshot_id": res["snapshot_id"]}).status_code == 404
    assert c.get(URL).json()["snapshot"] is None
    db[rc.SNAP_COLL].update_one({"snapshot_id": res["snapshot_id"]}, {"$set": {"status": "current"}})


def test_versions_listed_and_latest_current_default(env):
    c, db, res, tmp_path = env[0], env[1], env[2], env[4][0]
    d2, g2 = build_source(tmp_path, name="v2", excel_edit=lambda ws: ws.cell(row=9, column=5, value=9),
                          edit=lambda rows: rows[0].update(cantidad_libre_reportada="9", cantidad_fisica_total_reportada="9"))
    r2 = rc.run(d2, g2, db)
    lst = c.get(URL + "/snapshots").json()
    assert [(s["version"], s["status"]) for s in lst["items"]] == [(2, "current"), (1, "superseded")]
    assert set(lst["items"][0]) == {"snapshot_id", "version", "status", "as_of_local", "warehouse", "source", "imported_at"}
    top = c.get(URL).json()
    assert top["snapshot"]["snapshot_id"] == r2["snapshot_id"]
    assert next(i for i in top["items"] if i["producto_id"] == "0010001")["libre"] == 9
    old = c.get(URL, params={"snapshot_id": res["snapshot_id"]}).json()
    assert old["snapshot"]["status"] == "superseded"
    assert next(i for i in old["items"] if i["producto_id"] == "0010001")["libre"] == 5


def test_requires_session(env):
    c, app = env[0], env[3]
    app.dependency_overrides.pop(require_user)
    assert c.get(URL).status_code == 401
    assert c.get(URL + "/snapshots").status_code == 401


@pytest.mark.parametrize("params", [
    {"q": "{\"$ne\":1}"}, {"q": "$where"}, {"q": "a[0]"}, {"q": "x" * 101}, {"$ne": "1"}, {"snapshot_id": "{$gt:1}"},
    {"snapshot_id": "a$b"}, {"view": "todos"}, {"view": "$ne"}, {"sort": "producto_id;drop"}, {"sort": "categoria"},
    {"page": "0"}, {"page_size": "201"}, {"page": "x"}, {"desconocido": "1"}, {"libre[$gt]": "0"}])
def test_invalid_or_injected_params_are_422(env, params):
    r = env[0].get(URL, params=params)
    assert r.status_code == 422, params
    assert r.json()["error"]["code"] == "ENTRADA_INVALIDA"


def test_repeated_param_and_snapshots_strict(env):
    c = env[0]
    assert c.get(URL + "?view=all&view=no_stock").status_code == 422
    assert c.get(URL + "/snapshots?q=x").status_code == 422
    assert c.get(URL + "/snapshots?$ne=1").status_code == 422


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
@pytest.mark.parametrize("path", [URL, URL + "/snapshots"])
def test_no_write_routes(env, method, path):
    r = getattr(env[0], method)(path)
    assert r.status_code in (404, 405)


def test_reading_does_not_modify_collections(env):
    c, db = env[0], env[1]
    before = {n: db[n].count_documents({}) for n in db.list_collection_names()}
    docs = list(db[rc.SNAP_COLL].find({}))
    for p in ({}, {"view": "no_stock"}, {"q": "uno"}, {"sort": "-libre"}):
        c.get(URL, params=p)
    c.get(URL + "/snapshots")
    assert before == {n: db[n].count_documents({}) for n in db.list_collection_names()}
    assert docs == list(db[rc.SNAP_COLL].find({}))


@pytest.mark.skipif(not (REAL_DIR / "conteo_reportado.csv").is_file() or not REAL_GROUP.is_file(),
                    reason="conteo real no disponible")
def test_real_count_through_api():
    with temp_db() as db:
        rc.run(REAL_DIR, REAL_GROUP, db)
        app = create_app()
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_user] = lambda: CurrentUser("lector1", "lector", "x")
        c = TestClient(app, raise_server_exceptions=False)
        b = c.get(URL, params={"page_size": 200}).json()
        assert b["total"] == 50 and b["view_counts"] == {"all": 50, "with_stock": 48, "no_stock": 2}
        assert len(b["items"]) == 50 and b["snapshot"]["source"]["sha256_short"] == "608d15a74a58"
        assert sum(1 for i in b["items"] if i["libre"] == 0) == 2
        assert all(i["reservada"] == 0 and i["no_vendible"] == 0 for i in b["items"])
        by = {i["producto_id"]: i for i in b["items"]}
        assert by["6020011"]["libre"] == 106 and "12" in by["6020011"]["unidad_descripcion"]
        assert c.get(URL, params={"page_size": 20, "view": "with_stock"}).json()["has_more"] is True
