"""Existencia reconstruida (T20 §2): verificacion aritmetica, identidad con el conteo base, idempotencia y versionado. Datos sinteticos."""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path

import pytest

from pipeline.inventory import reconstructed as rc
from pipeline.inventory.reconstructed import ImportRejected, prepare, run

BASE_CSV_SHA = "b" * 64
REPORT_SHA = "a" * 64
# producto, conteo, ent_cierre, sal_cierre, ent_ult, sal_ult, stock_sistema
SPEC = [("1001", 10, 5, 3, 6, 4, 12), ("1002", 4, 0, 2, 0, 3, 1), ("1003", 0, 2, 0, 2, 1, 0)]


def _row(pid, c, ec, sc, eu, su, sis):
    ult = c + eu - su
    d = sis - ult
    return {"producto_id": pid, "producto": f"PRODUCTO {pid}", "unidad_reporte": "UND", "unidad_descripcion": "un frasco",
            "conteo_libre": c, "entradas_hasta_cierre": ec, "salidas_hasta_cierre": sc, "existencia_cierre_20_10": c + ec - sc,
            "entradas_hasta_ultimo_mov": eu, "salidas_hasta_ultimo_mov": su, "existencia_ultimo_mov": ult,
            "stock_sistema_ultimo_mov": sis, "reservado_sistema": 1, "diferencia": d, "estado": "COINCIDE" if d == 0 else "DISCREPANTE"}


def build(root: Path, *, rows=None, manifest_edit=None, name="pkg", csv_edit_after_manifest=None) -> Path:
    pkg = root / name
    pkg.mkdir(parents=True, exist_ok=True)
    rows = rows if rows is not None else [_row(*s) for s in SPEC]
    with (pkg / "existencias.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rc.COLUMNS)
        w.writeheader()
        w.writerows(rows)
    disc = sum(1 for r in rows if r["diferencia"] != 0)
    man = {"kind": "EXISTENCIA_RECONSTRUIDA", "warehouse": {"id": "1", "name": "Almacen Principal"},
           "as_of_local": "2026-10-20T23:59:59-05:00",
           "base_count": {"as_of_local": "2026-10-18T17:00:00-05:00", "csv_sha256": BASE_CSV_SHA},
           "movements": {"from_local": "2026-10-18T17:00:00-05:00", "closing_local": "2026-10-20T23:59:59-05:00",
                         "last_movement_local": "2026-10-21T16:26:38-05:00"},
           "rule": "conteo + entradas - salidas", "csv_sha256": hashlib.sha256((pkg / "existencias.csv").read_bytes()).hexdigest(),
           "sql_report_sha256": REPORT_SHA, "generated_at": "2026-10-21T20:00:00", "products": len(rows), "discrepancies": disc}
    if manifest_edit:
        manifest_edit(man)
    (pkg / "manifest.json").write_text(json.dumps(man), encoding="utf-8")
    if csv_edit_after_manifest:
        csv_edit_after_manifest(pkg / "existencias.csv")
    return pkg


def seed_base(db, *, csv_sha=BASE_CSV_SHA, libres=None, extra=None, drop=None, status="current"):
    sid = "invrep-20261018T1700-a1-test"
    libres = libres or {}
    db[rc.BASE_SNAP_COLL].insert_one({"snapshot_id": sid, "version": 1, "status": status, "as_of_local": rc.BASE_AS_OF_LOCAL,
                                      "as_of_utc": datetime(2026, 10, 18, 22), "warehouse": {"id": "1"},
                                      "source": {"csv_sha256": csv_sha, "sha256": "d" * 64}})
    items = [{"snapshot_id": sid, "producto_id": s[0], "categoria": f"CAT{s[0][-1]}", "libre": libres.get(s[0], s[1])} for s in SPEC
             if s[0] != drop]
    if extra:
        items.append({"snapshot_id": sid, "producto_id": extra, "categoria": "X", "libre": 1})
    db[rc.BASE_ITEM_COLL].insert_many(items)


@pytest.fixture()
def db():
    from tests.publish.helpers import temp_db
    with temp_db() as d:
        yield d


def reject(pkg, code, db=None, **kw):
    with pytest.raises(ImportRejected) as e:
        prepare(pkg, db, **kw)
    assert e.value.code == code
    return e.value


# ------------------------------------------------------------------ sin Mongo: aritmetica y manifiesto
def test_prepare_ok_builds_header_and_items(tmp_path):
    p = prepare(build(tmp_path))
    h = p.header
    assert h["snapshot_id"].startswith("invrec-20261020-") and len(h["snapshot_id"]) == len("invrec-20261020-") + 12
    assert h["kind"] == "EXISTENCIA_RECONSTRUIDA" and h["counts"] == {"products": 3, "discrepancies": 1}
    assert h["as_of_local"] == "2026-10-20T23:59:59-05:00" and h["as_of_utc"] == datetime(2026, 10, 21, 4, 59, 59)
    assert h["source"]["csv_sha256"] == p.csv_sha256 and h["base_count"]["csv_sha256"] == BASE_CSV_SHA
    it = {i["producto_id"]: i for i in p.items}
    assert it["1001"]["libre"] == 12 and it["1001"]["base_count"] == 10 and it["1001"]["reconstructed_at_last_movement"] == 12
    assert it["1001"]["discrepancy"] is None
    assert it["1002"]["libre"] == 2 and it["1002"]["movements"] == {"entradas_cierre": 0, "salidas_cierre": 2, "entradas_ultimo_mov": 0, "salidas_ultimo_mov": 3}
    assert it["1003"]["system_stock_at_last_movement"] == 0 and it["1003"]["system_reserved"] == 1


def test_discrepancy_values_follow_the_system_stock(tmp_path):
    p = prepare(build(tmp_path))
    d = {i["producto_id"]: i["discrepancy"] for i in p.items}
    # 1001: 10+6-4=12 vs 12 => coincide; 1002: 4-3=1 vs 1 => coincide; 1003: 0+2-1=1 vs 0 => -1
    assert d["1001"] is None and d["1002"] is None
    assert d["1003"] == {"difference": -1, "compared_at_local": "2026-10-21T16:26:38-05:00"}


def test_counts_in_header_match_discrepancies(tmp_path):
    rows = [_row("1001", 10, 5, 3, 6, 4, 11), _row("1002", 4, 0, 2, 0, 3, 1)]
    p = prepare(build(tmp_path, rows=rows))
    assert p.header["counts"]["discrepancies"] == 1 and p.items[0]["discrepancy"]["difference"] == -1


def test_rejects_altered_csv_sha(tmp_path):
    pkg = build(tmp_path, csv_edit_after_manifest=lambda p: p.write_text(p.read_text(encoding="utf-8").replace("PRODUCTO 1001", "OTRO"), encoding="utf-8"))
    reject(pkg, "FUENTE_ALTERADA")


def test_rejects_wrong_manifest_csv_sha(tmp_path):
    reject(build(tmp_path, manifest_edit=lambda m: m.update(csv_sha256="0" * 64)), "FUENTE_ALTERADA")


def test_rejects_sql_report_sha_mismatch(tmp_path):
    rep = tmp_path / "informe.json"
    rep.write_text("{}", encoding="utf-8")
    reject(build(tmp_path), "FUENTE_ALTERADA", sql_report=rep)
    good = build(tmp_path, name="ok", manifest_edit=lambda m: m.update(sql_report_sha256=hashlib.sha256(rep.read_bytes()).hexdigest()))
    prepare(good, None, rep)


def test_rejects_negative_stock(tmp_path):
    rows = [_row("1001", 3, 0, 5, 0, 5, 0)]            # 3 - 5 = -2 (aritmetica coherente, existencia negativa)
    reject(build(tmp_path, rows=rows), "CANTIDAD_NEGATIVA")


def test_rejects_broken_closing_arithmetic(tmp_path):
    rows = [_row(*s) for s in SPEC]
    rows[0]["existencia_cierre_20_10"] += 1
    reject(build(tmp_path, rows=rows), "ARITMETICA_INVALIDA")


def test_rejects_broken_last_movement_arithmetic(tmp_path):
    rows = [_row(*s) for s in SPEC]
    rows[1]["existencia_ultimo_mov"] += 1
    reject(build(tmp_path, rows=rows), "ARITMETICA_INVALIDA")


def test_rejects_wrong_difference_and_state(tmp_path):
    rows = [_row(*s) for s in SPEC]
    rows[2]["diferencia"] = 5
    reject(build(tmp_path, rows=rows), "ARITMETICA_INVALIDA")
    rows = [_row(*s) for s in SPEC]
    rows[2]["estado"] = "COINCIDE"
    reject(build(tmp_path, rows=rows, name="b"), "ARITMETICA_INVALIDA")


def test_rejects_duplicated_product_and_bad_columns(tmp_path):
    reject(build(tmp_path, rows=[_row(*SPEC[0]), _row(*SPEC[0])]), "CODIGO_REPETIDO")
    pkg = build(tmp_path, name="c")
    text = (pkg / "existencias.csv").read_text(encoding="utf-8").replace("estado", "estadoX", 1)
    (pkg / "existencias.csv").write_text(text, encoding="utf-8")
    m = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))
    m["csv_sha256"] = hashlib.sha256((pkg / "existencias.csv").read_bytes()).hexdigest()
    (pkg / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
    reject(pkg, "CSV_ESTRUCTURA_INVALIDA")


@pytest.mark.parametrize("edit,code", [
    (lambda m: m.update(kind="OTRO"), "MANIFIESTO_INVALIDO"),
    (lambda m: m["warehouse"].update(id="2"), "ALMACEN_NO_CONFIRMADO"),
    (lambda m: m.update(as_of_local="2026-10-20T23:59:59+00:00"), "FECHA_ZONA_INVALIDA"),
    (lambda m: m.update(as_of_local="2026-10-19T23:59:59-05:00"), "FECHA_ZONA_INVALIDA"),
    (lambda m: m["movements"].update(last_movement_local="2026-10-20T10:00:00-05:00"), "FECHA_ZONA_INVALIDA"),
    (lambda m: m.update(sql_report_sha256="x"), "MANIFIESTO_INVALIDO"),
    (lambda m: m.update(discrepancies=0), "MANIFIESTO_INVALIDO"),
])
def test_rejects_bad_manifest(tmp_path, edit, code):
    reject(build(tmp_path, manifest_edit=edit), code)


# ------------------------------------------------------------------ con Mongo: conteo base, idempotencia, versiones
@pytest.mark.mongo
def test_verifies_against_base_snapshot(tmp_path, db):
    seed_base(db)
    p = prepare(build(tmp_path), db)
    assert p.header["base_count"]["snapshot_id"] == "invrep-20261018T1700-a1-test" and p.header["source"]["verified_against_base_count"]
    assert {i["producto_id"]: i["categoria"] for i in p.items}["1002"] == "CAT2"


@pytest.mark.mongo
def test_rejects_product_outside_base(tmp_path, db):
    seed_base(db, drop="1003")
    reject(build(tmp_path), "CODIGOS_SOBRANTES", db)


@pytest.mark.mongo
def test_rejects_missing_product_of_base(tmp_path, db):
    seed_base(db, extra="9999")
    reject(build(tmp_path), "CODIGOS_FALTANTES", db)


@pytest.mark.mongo
def test_rejects_different_count_quantity(tmp_path, db):
    seed_base(db, libres={"1001": 11})
    reject(build(tmp_path), "CONTEO_BASE_DISTINTO", db)


@pytest.mark.mongo
def test_rejects_different_base_sha(tmp_path, db):
    seed_base(db, csv_sha="e" * 64)
    reject(build(tmp_path), "CONTEO_BASE_DISTINTO", db)


@pytest.mark.mongo
def test_create_idempotent_new_version_and_supersede(tmp_path, db):
    seed_base(db)
    other = {n: db[n].count_documents({}) for n in (rc.BASE_SNAP_COLL, rc.BASE_ITEM_COLL)}
    pkg1 = build(tmp_path, name="p1")
    dry = run(pkg1, db, dry_run=True)
    assert dry["action"] == "would_created" and rc.SNAP_COLL not in db.list_collection_names()
    r1 = run(pkg1, db)
    assert r1["action"] == "created" and r1["version"] == 1 and r1["items"] == 3 and r1["discrepancias"] == 1
    assert run(pkg1, db)["action"] == "unchanged"
    assert db[rc.ITEM_COLL].count_documents({}) == 3 and db[rc.SNAP_COLL].count_documents({}) == 1
    head = db[rc.SNAP_COLL].find_one({})
    assert head["status"] == "current" and head["supersedes"] is None and head["kind"] == "EXISTENCIA_RECONSTRUIDA"
    # contenido distinto (otro ultimo movimiento) => nueva version; la anterior queda superseded y legible
    pkg2 = build(tmp_path, name="p2", manifest_edit=lambda m: m["movements"].update(last_movement_local="2026-10-21T18:00:00-05:00"))
    r2 = run(pkg2, db)
    assert r2["action"] == "new_version" and r2["version"] == 2
    old = db[rc.SNAP_COLL].find_one({"snapshot_id": r1["snapshot_id"]})
    new = db[rc.SNAP_COLL].find_one({"snapshot_id": r2["snapshot_id"]})
    assert old["status"] == "superseded" and new["status"] == "current" and new["supersedes"] == r1["snapshot_id"]
    assert db[rc.ITEM_COLL].count_documents({"snapshot_id": r1["snapshot_id"]}) == 3
    with pytest.raises(ImportRejected) as e:
        run(pkg1, db)
    assert e.value.code == "VERSION_SUSTITUIDA"
    assert {n: db[n].count_documents({}) for n in (rc.BASE_SNAP_COLL, rc.BASE_ITEM_COLL)} == other


@pytest.mark.mongo
def test_rejected_import_writes_nothing(tmp_path, db):
    seed_base(db, libres={"1001": 99})
    with pytest.raises(ImportRejected):
        run(build(tmp_path), db)
    assert rc.SNAP_COLL not in db.list_collection_names() and rc.ITEM_COLL not in db.list_collection_names()


def test_cli_rejects_protected_db(tmp_path, capsys):
    assert rc.main(["--package", str(tmp_path), "--db", "demand_forecasting_dev"]) == 1
    assert rc.main(["--package", str(tmp_path), "--db", "no valido!"]) == 2
