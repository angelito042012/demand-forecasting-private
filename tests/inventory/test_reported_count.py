"""Importador del conteo reportado (T18 §2-§3) sobre bases temporales; fuentes reales con skip y sinteticas."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

import pytest

from pipeline.inventory import reported_count as rc
from pipeline.publish.source import PROJECT_ROOT
from tests.inventory.conftest import XLSX, build_source
from tests.publish.helpers import temp_db

pytestmark = pytest.mark.mongo

REAL_DIR = PROJECT_ROOT / "artifacts/private/conteo_recibido_20261018_v2"
REAL_GROUP = PROJECT_ROOT / "artifacts/private/datos_preparados_v1/02_grupo/productos.csv"
needs_real = pytest.mark.skipif(not (REAL_DIR / "conteo_reportado.csv").is_file() or not REAL_GROUP.is_file(),
                                reason="conteo real no disponible")


def _set(rows, idx, **kw):
    rows[idx].update(kw)


def _reject(tmp_path, code, **kw):
    d, g = build_source(tmp_path, **kw)
    with pytest.raises(rc.ImportRejected) as e:
        rc.prepare(d, g)
    assert e.value.code == code
    assert str(d) not in str(e.value) and str(tmp_path) not in str(e.value)
    return e.value


def _counts(db):
    return {c: db[c].count_documents({}) for c in (rc.SNAP_COLL, rc.ITEM_COLL)}


@needs_real
def test_real_count_imports_50_with_48_in_stock():
    with temp_db() as db:
        res = rc.run(REAL_DIR, REAL_GROUP, db)
        assert res["action"] == "created" and res["version"] == 1
        assert (res["items"], res["con_existencia"], res["sin_existencia"]) == (50, 48, 2)
        assert res["snapshot_id"] == "invrep-20261018T1700-a1-608d15a74a58"
        s = db[rc.SNAP_COLL].find_one({})
        assert s["status"] == "current" and s["as_of_utc"] == datetime(2026, 10, 18, 22, 0)
        assert s["as_of_local"] == "2026-10-18T17:00:00-05:00" and s["warehouse"] == {"id": "1", "name": "Almacen Principal"}
        assert s["independent_verification"] is False and s["context"] == {"sales_history_end": "2026-09-30"}
        items = list(db[rc.ITEM_COLL].find({}))
        assert len(items) == 50 and all(i["reservada"] == 0 and i["no_vendible"] == 0 for i in items)
        assert sum(1 for i in items if i["libre"] == 0) == 2 and sum(i["libre"] for i in items) == 12391
        by = {i["producto_id"]: i for i in items}
        assert by["6020011"]["libre"] == 106 and "12" in by["6020011"]["unidad_descripcion"]   # caja de 12, sin multiplicar
        assert all(isinstance(k, str) for k in by) and all(i["categoria"] for i in items)
        assert db[rc.SNAP_COLL].find_one({}, {"source": 1})["source"]["sha256"].startswith("608d15a74a58")
        # repeticion: sin escrituras ni duplicados
        before = _counts(db)
        again = rc.run(REAL_DIR, REAL_GROUP, db)
        assert again["action"] == "unchanged" and again["snapshot_id"] == res["snapshot_id"]
        assert _counts(db) == before == {rc.SNAP_COLL: 1, rc.ITEM_COLL: 50}


def test_synthetic_import_idempotent_and_values(tmp_path):
    d, g = build_source(tmp_path)
    with temp_db() as db:
        res = rc.run(d, g, db)
        assert res == {"action": "created", "snapshot_id": res["snapshot_id"], "version": 1, "items": 4,
                       "con_existencia": 3, "sin_existencia": 1}
        it = {i["producto_id"]: i for i in db[rc.ITEM_COLL].find({})}
        assert set(it) == {"0010001", "0010002", "2010003", "2010004"}      # ceros a la izquierda conservados
        assert it["2010003"]["libre"] == 0 and it["2010003"]["reservada"] == 0       # cero declarado
        assert it["2010004"]["reservada"] is None and it["2010004"]["no_vendible"] is None   # vacio != 0
        assert it["2010004"]["fisica_total"] is None
        assert it["0010002"]["libre"] == 7 and it["0010002"]["unidad_descripcion"] == "Una caja de 12 unidades"
        assert it["2010003"]["libre"] * 2 == 0 and it["0010001"]["libre"] == 5     # nada multiplicado
        before = _counts(db)
        assert rc.run(d, g, db)["action"] == "unchanged"
        assert _counts(db) == before
        assert rc.run(d, g, db, dry_run=True)["action"] == "unchanged"
        names = {i["name"] for i in db[rc.SNAP_COLL].list_indexes()} | {i["name"] for i in db[rc.ITEM_COLL].list_indexes()}
        assert {"snapshot_id_unique", "wh_asof_version_unique", "snapshot_product_unique"} <= names


def test_dry_run_writes_nothing(tmp_path):
    d, g = build_source(tmp_path)
    with temp_db() as db:
        assert rc.run(d, g, db, dry_run=True)["action"] == "would_created"
        assert db.list_collection_names() == []


def test_new_version_supersedes_and_keeps_previous(tmp_path):
    d1, g1 = build_source(tmp_path, name="a")
    d2, g2 = build_source(tmp_path, name="b", excel_edit=lambda ws: ws.cell(row=9, column=5, value=9),
                          edit=lambda rows: _set(rows, 0, cantidad_libre_reportada="9", cantidad_fisica_total_reportada="9"))
    with temp_db() as db:
        r1 = rc.run(d1, g1, db)
        r2 = rc.run(d2, g2, db)
        assert r2["action"] == "new_version" and r2["version"] == 2 and r2["snapshot_id"] != r1["snapshot_id"]
        st = {s["snapshot_id"]: s for s in db[rc.SNAP_COLL].find({})}
        assert st[r1["snapshot_id"]]["status"] == "superseded" and st[r2["snapshot_id"]]["status"] == "current"
        assert st[r2["snapshot_id"]]["supersedes"] == r1["snapshot_id"]
        assert db[rc.ITEM_COLL].count_documents({"snapshot_id": r1["snapshot_id"]}) == 4
        assert db[rc.ITEM_COLL].find_one({"snapshot_id": r1["snapshot_id"], "producto_id": "0010001"})["libre"] == 5
        assert db[rc.ITEM_COLL].find_one({"snapshot_id": r2["snapshot_id"], "producto_id": "0010001"})["libre"] == 9
        # reimportar la version sustituida no la revive ni duplica
        with pytest.raises(rc.ImportRejected) as e:
            rc.run(d1, g1, db)
        assert e.value.code == "VERSION_SUSTITUIDA"
        assert _counts(db) == {rc.SNAP_COLL: 2, rc.ITEM_COLL: 8}


def test_interrupted_staging_is_cleaned_by_own_id(tmp_path):
    d, g = build_source(tmp_path)
    prep = rc.prepare(d, g)
    sid = prep.header["snapshot_id"]
    with temp_db() as db:
        # restos de un intento interrumpido: cabecera en staging y solo 2 filas; mas un ajeno que no se toca
        db[rc.SNAP_COLL].insert_one({**prep.header, "version": 1, "status": "staging", "supersedes": None,
                                     "imported_at": datetime(2026, 10, 18)})
        db[rc.ITEM_COLL].insert_many([{"snapshot_id": sid, **i} for i in prep.items[:2]])
        db[rc.ITEM_COLL].insert_one({"snapshot_id": "invrep-otro", "producto_id": "X", "libre": 1})
        res = rc.run(d, g, db)
        assert res["action"] == "created" and res["version"] == 1
        assert db[rc.ITEM_COLL].count_documents({"snapshot_id": sid}) == 4
        assert db[rc.ITEM_COLL].count_documents({"snapshot_id": "invrep-otro"}) == 1
        assert db[rc.SNAP_COLL].count_documents({"snapshot_id": sid, "status": "current"}) == 1


def test_failed_write_leaves_no_staging(tmp_path, monkeypatch):
    d, g = build_source(tmp_path)
    with temp_db() as db:
        orig = type(db[rc.ITEM_COLL]).insert_many

        def boom(self, *a, **k):
            raise RuntimeError("corte simulado")
        monkeypatch.setattr(type(db[rc.ITEM_COLL]), "insert_many", boom)
        with pytest.raises(RuntimeError):
            rc.run(d, g, db)
        monkeypatch.setattr(type(db[rc.ITEM_COLL]), "insert_many", orig)
        assert _counts(db) == {rc.SNAP_COLL: 0, rc.ITEM_COLL: 0}
        assert rc.run(d, g, db)["action"] == "created"


def test_time_zone_lima_to_utc(tmp_path):
    d, g = build_source(tmp_path)
    prep = rc.prepare(d, g)
    assert prep.header["as_of_utc"] == datetime(2026, 10, 18, 22, 0)
    assert prep.header["as_of_local"] == "2026-10-18T17:00:00-05:00"
    assert prep.header["snapshot_id"].startswith("invrep-20261018T1700-a1-")


def test_rejects_missing_repeated_and_extra_codes(tmp_path):
    _reject(tmp_path / "a", "CODIGOS_FALTANTES", edit=lambda rows: rows.pop())
    _reject(tmp_path / "b", "CODIGO_REPETIDO", edit=lambda rows: _set(rows, 3, producto_id="0010001"))
    _reject(tmp_path / "c", "CODIGOS_SOBRANTES", group_edit=lambda g: g.pop())
    _reject(tmp_path / "d", "CODIGO_INVALIDO", edit=lambda rows: _set(rows, 0, producto_id="10001.0"))
    _reject(tmp_path / "e", "NOMBRE_NO_COINCIDE", edit=lambda rows: _set(rows, 0, producto="OTRO"))
    _reject(tmp_path / "f", "UNIDAD_NO_COINCIDE", edit=lambda rows: _set(rows, 0, unidad_reporte="CJA"))
    _reject(tmp_path / "g", "PRESENTACION_FALTANTE", edit=lambda rows: _set(rows, 0, unidad_descripcion_reportada=" "))


@pytest.mark.parametrize("bad", ["", "-1", "2.5", "abc", "1e3", "5,0"])
def test_rejects_invalid_free_quantity(tmp_path, bad):
    _reject(tmp_path, "CANTIDAD_INVALIDA", edit=lambda rows: _set(rows, 0, cantidad_libre_reportada=bad))


@pytest.mark.parametrize("field", ["cantidad_reservada_reportada", "cantidad_no_vendible_reportada"])
@pytest.mark.parametrize("bad", ["-1", "0.5", "x"])
def test_rejects_invalid_reserved_or_unsellable(tmp_path, field, bad):
    _reject(tmp_path, "CANTIDAD_INVALIDA", edit=lambda rows: _set(rows, 0, **{field: bad}))


def test_rejects_inconsistent_total(tmp_path):
    _reject(tmp_path, "TOTAL_INCONSISTENTE", edit=lambda rows: _set(rows, 0, cantidad_fisica_total_reportada="6"))


def test_rejects_altered_excel_or_hashes(tmp_path):
    d, g = build_source(tmp_path)
    (d / XLSX).write_bytes((d / XLSX).read_bytes() + b"alterado")
    with pytest.raises(rc.ImportRejected) as e:
        rc.prepare(d, g)
    assert e.value.code == "FUENTE_ALTERADA"
    _reject(tmp_path / "r", "FUENTE_ALTERADA", review_edit=lambda r: r.update(source_sha256="0" * 64))
    _reject(tmp_path / "s", "FUENTE_ALTERADA", edit=lambda rows: _set(rows, 2, sha256_origen=hashlib.sha256(b"z").hexdigest()))
    _reject(tmp_path / "t", "FUENTE_ALTERADA", review_edit=lambda r: r.update(source_unchanged=False))


def test_rejects_other_time_zone_or_offset(tmp_path):
    def all_rows(**kw):
        return lambda rows: [r.update(kw) for r in rows]
    _reject(tmp_path / "a", "FECHA_ZONA_INVALIDA", edit=all_rows(zona_horaria="UTC"))
    _reject(tmp_path / "b", "FECHA_ZONA_INVALIDA", edit=all_rows(fecha_hora_reportada="2026-10-18T17:00:00+00:00"))
    _reject(tmp_path / "c", "FECHA_ZONA_INVALIDA", edit=all_rows(fecha_hora_reportada="2026-10-18T17:00:00"))
    _reject(tmp_path / "d", "FECHA_ZONA_INVALIDA", edit=lambda rows: _set(rows, 1, fecha_hora_reportada="2026-10-18T18:00:00-05:00"))


def test_rejects_unconfirmed_warehouse_and_state(tmp_path):
    _reject(tmp_path / "a", "ALMACEN_NO_CONFIRMADO", edit=lambda rows: _set(rows, 0, almacen_id_confirmado="2"))
    _reject(tmp_path / "b", "ALMACEN_NO_CONFIRMADO", edit=lambda rows: _set(rows, 0, almacen_id_confirmado=""))
    _reject(tmp_path / "b2", "ALMACEN_NO_CONFIRMADO", edit=lambda rows: _set(rows, 0, almacen_id_candidato="2"))
    _reject(tmp_path / "b3", "ALMACEN_NO_CONFIRMADO", edit=lambda rows: _set(rows, 0, almacen_id_confirmado="False"))
    _reject(tmp_path / "c", "CORTE_NO_CONFIRMADO", edit=lambda rows: _set(rows, 1, corte_sin_ventas_confirmado="False"))
    _reject(tmp_path / "d", "ESTADO_NO_APTO", edit=lambda rows: _set(rows, 1, estado_uso="BORRADOR"))
    _reject(tmp_path / "e", "NATURALEZA_INVALIDA", edit=lambda rows: _set(rows, 1, naturaleza="SIMULADO"))
    _reject(tmp_path / "f", "VERIFICACION_INVALIDA", edit=lambda rows: _set(rows, 1, verificacion_independiente="True"))


def test_missing_files_rejected(tmp_path):
    d, g = build_source(tmp_path)
    (d / "review.json").unlink()
    with pytest.raises(rc.ImportRejected) as e:
        rc.prepare(d, g)
    assert e.value.code == "ARCHIVO_FALTANTE"


@pytest.mark.parametrize("name", ["demand_forecasting_dev", "demand_forecasting_v2", "demand_forecasting_pub"])
def test_protected_databases_refused(tmp_path, name):
    from pymongo import MongoClient
    d, g = build_source(tmp_path)
    client = MongoClient("mongodb://127.0.0.1:1", serverSelectionTimeoutMS=100)   # nunca se usa: se rechaza antes
    with pytest.raises(rc.ImportRejected) as e:
        rc.run(d, g, client[name])
    assert e.value.code == "BASE_PROTEGIDA"
    assert rc.main(["--count-dir", str(d), "--group", str(g), "--db", name]) == 1
    assert rc.main(["--count-dir", str(d), "--group", str(g), "--db", "bad name!"]) == 2
    client.close()


def test_isolation_from_existing_collections(tmp_path):
    d, g = build_source(tmp_path)
    with temp_db() as db:
        for c in ("recommendations", "inventory_snapshot", "runs"):
            db[c].insert_many([{"run_id": "r1", "n": n, "value": n * 3} for n in range(5)])

        def digest():
            out = {}
            for c in ("recommendations", "inventory_snapshot", "runs"):
                docs = sorted(json.dumps(x, default=str, sort_keys=True) for x in db[c].find({}))
                out[c] = (len(docs), hashlib.sha256("|".join(docs).encode()).hexdigest())
            return out
        before = digest()
        rc.run(d, g, db)
        rc.run(d, g, db)
        d2, g2 = build_source(tmp_path, name="v2", salt="otro")
        rc.run(d2, g2, db)
        assert digest() == before
        assert sorted(db.list_collection_names()) == sorted(
            ["recommendations", "inventory_snapshot", "runs", rc.SNAP_COLL, rc.ITEM_COLL])


def test_cli_prints_json_without_secrets(tmp_path, capsys, monkeypatch):
    d, g = build_source(tmp_path)
    with temp_db() as db:
        monkeypatch.setenv("MONGODB_URI", "mongodb://127.0.0.1:27017")
        assert rc.main(["--count-dir", str(d), "--group", str(g), "--db", db.name]) == 0
        out = json.loads(capsys.readouterr().out)
        assert out["action"] == "created" and out["items"] == 4 and "mongodb" not in json.dumps(out)
        assert rc.main(["--count-dir", str(d), "--group", str(g), "--db", db.name]) == 0
        assert json.loads(capsys.readouterr().out)["action"] == "unchanged"
        (d / XLSX).write_bytes(b"x")
        assert rc.main(["--count-dir", str(d), "--group", str(g), "--db", db.name]) == 1
        err = capsys.readouterr().err
        assert "FUENTE_ALTERADA" in err and str(Path(d)) not in err
