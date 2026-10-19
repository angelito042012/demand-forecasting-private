"""Dataset de planificacion (T19 §1/§5): verificacion contra libros, sellado, importacion idempotente y particiones."""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import date
from decimal import Decimal

import pytest
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

from pipeline.plan import dataset as ds
from pipeline.plan.dataset import (
    COLLECTIONS,
    HEADER_COLL,
    ImportRejected,
    prepare,
    run,
    write_dataset,
)
from tests.plan.conftest import (
    GROUP_SIZE,
    audit_of,
    build_package,
    default_books,
    edit_csv,
    edit_manifest,
    line,
    total_qty,
)

pytestmark = pytest.mark.mongo
ALL = list(COLLECTIONS.values())


def reject(pkg, code=None, audit=True):
    with pytest.raises(ImportRejected) as e:
        prepare(pkg, audit_of(pkg) if audit else None)
    if code:
        assert e.value.code == code
    return e.value


def nothing_written(db):
    assert not (set(db.list_collection_names()) & {*ALL, HEADER_COLL})


# ---------------------------------------------------------------- aceptacion e idempotencia
def test_prepare_accepts_and_seals(pkg):
    p = prepare(pkg, audit_of(pkg))
    h = p.header
    assert h["dataset_id"].startswith("plds-") and len(h["dataset_id"]) == 17
    assert h["audit_checked"] is True and h["schema_version"] == 1
    assert h["counts"]["VENTA"] and h["counts"]["CREDITO"] == 7 and h["counts"]["CUARENTENA"] == 2
    assert h["source_rows"] == sum(h["counts"].values()) == sum(len(v) for v in p.docs.values())
    assert h["sales_cutoff"] == "2026-09-30" and h["window_start"] == "2026-03-01"
    assert len(h["sources"]) == 14 and set(h["partitions"]) == {"sales", "purchases", "credits", "quarantine"}
    assert all(len(v["sha256"]) == 64 for v in h["partitions"].values())
    assert h["group"]["size"] == GROUP_SIZE


def test_without_audit_declares_it(pkg):
    audit_of(pkg).unlink()
    assert prepare(pkg, audit_of(pkg)).header["audit_checked"] is False


def test_same_content_same_id_regardless_of_location(pkg, tmp_path):
    other = tmp_path / "otra"
    shutil.copytree(pkg.parent, other)
    assert prepare(pkg, audit_of(pkg)).header["dataset_id"] == prepare(other / "pkg", audit_of(other / "pkg")).header["dataset_id"]


def test_import_and_idempotent(pkg, db):
    r1 = run(pkg, db, audit_of(pkg))
    assert r1["action"] == "created" and r1["version"] == 1 and r1["sales_cutoff"] == "2026-09-30"
    heads = list(db[HEADER_COLL].find({}, {"_id": 0}))
    assert len(heads) == 1 and heads[0]["status"] == "current" and heads[0]["supersedes"] is None
    before = {c: sorted(d["registro_id"] for d in db[c].find({}, {"registro_id": 1})) for c in ALL}
    snap = {c: list(db[c].find({}, {"_id": 0}).sort("registro_id", 1)) for c in [*ALL, HEADER_COLL]}
    r2 = run(pkg, db, audit_of(pkg))
    assert r2["action"] == "unchanged" and r2["dataset_id"] == r1["dataset_id"]
    assert {c: sorted(d["registro_id"] for d in db[c].find({}, {"registro_id": 1})) for c in ALL} == before
    assert {c: list(db[c].find({}, {"_id": 0}).sort("registro_id", 1)) for c in [*ALL, HEADER_COLL]} == snap
    assert sum(len(v) for v in before.values()) == r1["source_rows"]


def test_dry_run_writes_nothing(pkg, db):
    assert run(pkg, db, audit_of(pkg), dry_run=True)["action"] == "would_created"
    nothing_written(db)


def test_document_schema_types_and_indexes(pkg, db):
    run(pkg, db, audit_of(pkg))
    did = db[HEADER_COLL].find_one({})["dataset_id"]
    keys = {"dataset_id", "registro_id", "fecha", "producto_id", "producto", "categoria", "almacen", "unidad", "cantidad",
            "moneda", "importe", "tipo_documento", "documento_id", "clase", "grupo_repeticion", "ocurrencia",
            "dia_excluido_pronostico", "archivo", "hoja", "fila", "sha256_origen"}
    for c in ALL:
        for d in db[c].find({"dataset_id": did}, {"_id": 0}):
            assert set(d) == keys
            assert isinstance(d["fecha"], str) and date.fromisoformat(d["fecha"])
            assert isinstance(d["producto_id"], str) and isinstance(d["almacen"], str)
            assert d["cantidad"] is None or isinstance(d["cantidad"], str)
            assert d["importe"] is None or isinstance(d["importe"], str)
            assert isinstance(d["ocurrencia"], int) and isinstance(d["fila"], int) and isinstance(d["dia_excluido_pronostico"], bool)
        info = db[c].index_information()
        assert any(v["key"] == [("dataset_id", 1), ("registro_id", 1)] and v.get("unique") for v in info.values())
        assert any(v["key"] == [("dataset_id", 1), ("producto_id", 1), ("fecha", 1)] for v in info.values())
        first = db[c].find_one({}, {"_id": 0})
        with pytest.raises(DuplicateKeyError):
            db[c].insert_one(dict(first))


# ---------------------------------------------------------------- particiones y semantica
def test_partitions_exhaustive_and_disjoint(pkg, db):
    run(pkg, db, audit_of(pkg))
    h = db[HEADER_COLL].find_one({})
    ids = [d["registro_id"] for c in ALL for d in db[c].find({}, {"registro_id": 1})]
    assert len(ids) == len(set(ids)) == h["source_rows"]
    assert {d["clase"] for d in db.plan_sales.find()} == {"VENTA"}
    assert {d["clase"] for d in db.plan_purchases.find()} == {"COMPRA", "COMPRA_SIN_CARGO_REGISTRADO"}
    assert {d["clase"] for d in db.plan_credits.find()} == {"CREDITO"}
    assert {d["clase"] for d in db.plan_quarantine.find()} == {"CUARENTENA"}
    for k, part in h["partitions"].items():
        assert db[part["collection"]].count_documents({}) == part["count"], k


def test_credits_never_become_entries_or_sales(pkg, db):
    run(pkg, db, audit_of(pkg))
    credits = list(db.plan_credits.find())
    assert len(credits) == 7 and all(d["tipo_documento"] == "7" and Decimal(d["cantidad"]) < 0 for d in credits)
    assert not db.plan_sales.count_documents({"tipo_documento": "7"})
    assert not db.plan_purchases.count_documents({"tipo_documento": "7"})
    assert all(Decimal(d["cantidad"]) > 0 for d in db.plan_purchases.find())     # ninguna entrada negativa
    assert all(Decimal(d["cantidad"]) > 0 for d in db.plan_sales.find())


def test_missing_data_is_not_zero_sales(pkg, db):
    run(pkg, db, audit_of(pkg))
    q = list(db.plan_quarantine.find())
    assert len(q) == 2 and any(d["cantidad"] is None for d in q)
    assert not db.plan_sales.count_documents({"cantidad": None})
    assert not db.plan_sales.count_documents({"$or": [{"cantidad": "0"}, {"cantidad": ""}]})
    sales_total = total_qty(db.plan_sales.find())
    expected = Decimal(0)
    for rows in default_books().values():
        for r in rows:
            if r["TIPO_DOC"] == "7" or r.get("VEN_ESTADO", "ACTIVO") != "ACTIVO" or r["CANTIDAD"] is None or "VEN_ESTADO" not in r:
                continue
            expected += Decimal(str(r["CANTIDAD"]))
    assert sales_total == expected                                              # incluye 0.5 exacto, sin redondeo
    assert db.plan_sales.count_documents({"cantidad": "0.5"}) == 1


def test_currencies_separate_no_invented_prices(pkg, db):
    run(pkg, db, audit_of(pkg))
    h = db[HEADER_COLL].find_one({})
    assert h["partitions"]["purchases"]["importes_por_moneda"]["USD"] == "50"
    assert set(h["partitions"]["sales"]["importes_por_moneda"]) == {"PEN"}
    assert db.plan_purchases.count_documents({"moneda": "USD"}) == 1
    free = list(db.plan_purchases.find({"clase": "COMPRA_SIN_CARGO_REGISTRADO"}))
    assert len(free) == 7 and all(d["importe"] == "0" and d["moneda"] == "PEN" for d in free)    # sin precio inventado
    assert h["currencies"] == ["PEN", "USD"]


def test_repeated_copies_marked_not_deleted(pkg, db):
    run(pkg, db, audit_of(pkg))
    copies = list(db.plan_purchases.find({"grupo_repeticion": {"$ne": ""}}))
    assert len(copies) == 2 and {d["ocurrencia"] for d in copies} == {1, 2}
    assert len({d["grupo_repeticion"] for d in copies}) == 1
    h = db[HEADER_COLL].find_one({})
    assert h["repeated_extra_rows"] == h["repeated_extra_rows_marked"] == 1
    assert db.plan_purchases.count_documents({"producto_id": "1003", "importe": "40"}) == 2


def test_masked_day_flag_and_cutoff(pkg, db):
    run(pkg, db, audit_of(pkg))
    flagged = {d["fecha"] for d in db.plan_sales.find({"dia_excluido_pronostico": True})}
    assert flagged == {"2026-04-03"}
    assert db[HEADER_COLL].find_one({})["sales_cutoff"] == max(d["fecha"] for d in db.plan_sales.find())


def test_traceability_fields(pkg, db):
    run(pkg, db, audit_of(pkg))
    h = db[HEADER_COLL].find_one({})
    shas = {s["archivo"]: s["sha256"] for s in h["sources"]}
    for c in ALL:
        for d in db[c].find():
            assert d["hoja"] == "Hoja1" and d["fila"] >= 3 and shas[d["archivo"]] == d["sha256_origen"]


# ---------------------------------------------------------------- rechazos antes de escribir
def _coherent_qty_total(rows):
    r = next(x for x in rows if x["producto_id"] == "1001")
    r["cantidad"] = str(Decimal(r["cantidad"]) * 5)
    r["importe"] = str(Decimal(r["importe"]) * 5)


def _set(field, value, pred=lambda r: True):
    def fn(rows):
        next(r for r in rows if pred(r))[field] = value
    return fn


def _drop_first(rows):
    return rows[1:]


def _extra_row(rows):
    new = dict(rows[0])
    new["registro_id"] = "f" * 24
    return [*rows, new]


def _dup_row(rows):
    return [*rows, dict(rows[0])]


TAMPER = [
    ("qty_total_coherentes", "ventas.csv", _coherent_qty_total),
    ("fecha", "ventas.csv", _set("fecha", "2026-09-29")),
    ("codigo", "ventas.csv", _set("producto_id", "1002")),
    ("clase_dentro_del_archivo", "compras.csv", _set("clasificacion", "COMPRA", lambda r: r["clasificacion"] != "COMPRA")),
    ("clase_venta_a_credito", "ventas.csv", _set("clasificacion", "CREDITO")),
    ("moneda", "compras.csv", _set("moneda", "PEN", lambda r: r["moneda"] == "USD")),
    ("importe_cero_a_precio", "compras.csv", _set("importe", "9.99", lambda r: r["importe"] == "0")),
    ("fila", "ventas.csv", _set("fila", "999")),
    ("ocurrencia", "compras.csv", _set("ocurrencia", "1", lambda r: r["ocurrencia"] == "2")),
    ("grupo_repeticion", "compras.csv", _set("grupo_repeticion", "", lambda r: r["grupo_repeticion"] != "")),
    ("sha256_origen", "ventas.csv", _set("sha256_origen", "0" * 64)),
    ("archivo", "ventas.csv", _set("archivo", "abril.xlsx", lambda r: r["archivo"] != "abril.xlsx")),
    ("documento_id", "ventas.csv", _set("documento_id", "0" * 24)),
    ("incluido_grupo", "ventas.csv", _set("incluido_grupo", "True", lambda r: r["incluido_grupo"] == "False")),
    ("dia_excluido", "ventas.csv", _set("dia_excluido_pronostico", "True", lambda r: r["dia_excluido_pronostico"] == "False")),
    ("nombre", "ventas.csv", _set("producto", "OTRO")),
    ("categoria", "ventas.csv", _set("categoria", "OTRA")),
    ("registro_faltante", "ventas.csv", _drop_first),
    ("registro_sobrante", "ventas.csv", _extra_row),
    ("registro_duplicado", "ventas.csv", _dup_row),
    ("cuarentena_faltante", "cuarentena.csv", lambda rows: rows[1:]),
    ("cantidad_faltante_a_cero", "cuarentena.csv", _set("cantidad", "0", lambda r: r["cantidad"] == "")),
]


@pytest.mark.parametrize(("name", "csv_name", "fn"), TAMPER, ids=[t[0] for t in TAMPER])
def test_tampered_derivative_rejected_without_writing(pkg, db, name, csv_name, fn):
    edit_csv(pkg, csv_name, fn)
    exc = reject(pkg)
    assert exc.code == "DERIVADO_NO_COINCIDE"
    with pytest.raises(ImportRejected):
        run(pkg, db, audit_of(pkg))
    nothing_written(db)


def test_row_moved_to_another_partition_rejected(pkg):
    moved = {}
    edit_csv(pkg, "ventas.csv", lambda rows: moved.setdefault("r", rows[0]) and rows[1:])
    edit_csv(pkg, "creditos.csv", lambda rows: [*rows, moved["r"]])
    assert reject(pkg).code == "DERIVADO_NO_COINCIDE"


def test_columns_changed_rejected(pkg):
    path = pkg / "01_normalizados" / "ventas.csv"
    text = path.read_text(encoding="utf-8-sig").replace("registro_id", "registro", 1)
    path.write_text(text, encoding="utf-8-sig")
    assert reject(pkg).code == "CSV_ESTRUCTURA_INVALIDA"


def test_productos_csv_changed_rejected(pkg):
    path = pkg / "02_grupo" / "productos.csv"
    path.write_text(path.read_text(encoding="utf-8-sig").replace("1002", "1003"), encoding="utf-8-sig")
    assert reject(pkg).code == "DERIVADO_NO_COINCIDE"


@pytest.mark.parametrize("edit", [
    lambda m: m["class_counts"].update(VENTA=m["class_counts"]["VENTA"] + 1),
    lambda m: m.update(source_rows=m["source_rows"] + 1),
    lambda m: m["sources"][0].update(filas=m["sources"][0]["filas"] + 1),
    lambda m: m["sources"][0]["importes_por_moneda"].update(PEN="1.00"),
    lambda m: m["sources"][0]["clasificaciones"].update(VENTA=99),
    lambda m: m.update(eligible_products=99),
    lambda m: m.update(group_size=3),
], ids=["class_counts", "source_rows", "filas", "importes", "clasificaciones", "elegibles", "group_size"])
def test_manifest_tampered_rejected(pkg, edit):
    edit_manifest(pkg, edit)
    assert reject(pkg).code == "DERIVADO_NO_COINCIDE"


def test_manifest_book_hash_altered_rejected(pkg):
    edit_manifest(pkg, lambda m: m["sources"][3].update(sha256="0" * 64))
    assert reject(pkg).code == "FUENTE_ALTERADA"


def test_book_bytes_altered_rejected(pkg):
    with (pkg / "00_originales" / "marzo.xlsx").open("ab") as f:
        f.write(b"x")
    assert reject(pkg).code == "FUENTE_ALTERADA"


def test_audit_hash_mismatch_rejected(pkg):
    a = audit_of(pkg)
    data = json.loads(a.read_text())
    data["files"][0]["sha256"] = "1" * 64
    a.write_text(json.dumps(data))
    assert reject(pkg).code == "FUENTE_ALTERADA"


def test_audit_missing_book_rejected(pkg):
    a = audit_of(pkg)
    data = json.loads(a.read_text())
    data["files"].pop()
    a.write_text(json.dumps(data))
    assert reject(pkg).code == "FUENTE_ALTERADA"


def test_unreadable_book_even_with_consistent_hashes(pkg):
    bad = pkg / "00_originales" / "mayo.xlsx"
    bad.write_bytes(b"no es un xlsx")
    digest = hashlib.sha256(bad.read_bytes()).hexdigest()
    edit_manifest(pkg, lambda m: next(s for s in m["sources"] if s["archivo"] == "mayo.xlsx").update(sha256=digest))
    assert reject(pkg, audit=False).code == "FUENTE_ALTERADA"


def test_book_changed_with_consistent_hashes_but_stale_csv(pkg):
    """Cambio coherente de libro + manifiesto + audit: el CSV derivado ya no corresponde."""
    books = default_books()
    books["mayo"][0]["CANTIDAD"] = 3
    books["mayo"][0]["CANTIDAD_UM_BASE"] = 3
    books["mayo"][0]["TOTAL_LINEA"] = 30
    other = build_package(pkg.parent.parent / "otra", books)
    shutil.copy2(other / "00_originales" / "mayo.xlsx", pkg / "00_originales" / "mayo.xlsx")
    new = hashlib.sha256((pkg / "00_originales" / "mayo.xlsx").read_bytes()).hexdigest()
    edit_manifest(pkg, lambda m: next(s for s in m["sources"] if s["archivo"] == "mayo.xlsx").update(sha256=new))
    a = audit_of(pkg)
    data = json.loads(a.read_text())
    next(f for f in data["files"] if f["file"] == "mayo.xlsx")["sha256"] = new
    a.write_text(json.dumps(data))
    assert reject(pkg).code == "DERIVADO_NO_COINCIDE"


def test_extra_or_missing_book_rejected(pkg):
    shutil.copy2(pkg / "00_originales" / "marzo.xlsx", pkg / "00_originales" / "extra.xlsx")
    assert reject(pkg).code == "FUENTE_ALTERADA"
    (pkg / "00_originales" / "extra.xlsx").unlink()
    (pkg / "00_originales" / "marzo.xlsx").unlink()
    assert reject(pkg).code == "FUENTE_ALTERADA"


def test_date_outside_window_rejected(tmp_path):
    books = default_books()
    books["setiembre"].append(line("ventas", 9, 30, "1001"))
    books["setiembre"][-1]["FECHA"] = books["setiembre"][-1]["FECHA"].replace(month=10, day=2)
    with pytest.raises(Exception) as e:                    # el propio generador (normalize) ya rechaza la fecha
        build_package(tmp_path / "x", books)
    assert "FECHA_FUERA_DE_VENTANA" in str(e.value)


def test_manifest_missing_rejected(pkg):
    (pkg / "manifest.json").unlink()
    assert reject(pkg).code == "ARCHIVO_FALTANTE"


# ---------------------------------------------------------------- versionado, aislamiento, robustez
def test_new_content_new_version_old_superseded_kept(pkg, db, tmp_path):
    r1 = run(pkg, db, audit_of(pkg))
    old_counts = {c: db[c].count_documents({"dataset_id": r1["dataset_id"]}) for c in ALL}
    books = default_books()
    books["setiembre"].append(line("ventas", 9, 29, "1002", 7, 70, serie="B001-new"))
    new_pkg = build_package(tmp_path / "v2", books)
    r2 = run(new_pkg, db, audit_of(new_pkg))
    assert r2["action"] == "new_version" and r2["version"] == 2 and r2["dataset_id"] != r1["dataset_id"]
    heads = {h["dataset_id"]: h for h in db[HEADER_COLL].find()}
    assert heads[r1["dataset_id"]]["status"] == "superseded" and heads[r2["dataset_id"]]["status"] == "current"
    assert heads[r2["dataset_id"]]["supersedes"] == r1["dataset_id"]
    assert {c: db[c].count_documents({"dataset_id": r1["dataset_id"]}) for c in ALL} == old_counts      # conservada
    assert db.plan_sales.count_documents({"dataset_id": r2["dataset_id"]}) == old_counts["plan_sales"] + 1
    assert run(new_pkg, db, audit_of(new_pkg))["action"] == "unchanged"
    with pytest.raises(ImportRejected) as e:                                                              # no vuelve atras
        run(pkg, db, audit_of(pkg))
    assert e.value.code == "VERSION_SUSTITUIDA"


def test_isolation_other_collections_untouched(pkg, db):
    others = {"runs": [{"run_id": "r1", "x": 1}], "recommendations": [{"sku": "9", "q": 3}],
              "inventory_reported_snapshots": [{"snapshot_id": "s"}], "sales_daily": [{"fecha": "2026-01-01", "v": 5}]}
    for name, docs in others.items():
        db[name].insert_many([dict(d) for d in docs])

    def fp():
        return {n: hashlib.sha256(json.dumps(list(db[n].find({}, {"_id": 0}).sort("_id", 1)), sort_keys=True, default=str).encode()).hexdigest()
                for n in others}
    before = fp()
    run(pkg, db, audit_of(pkg))
    assert fp() == before
    assert set(db.list_collection_names()) - set(others) == {*ALL, HEADER_COLL}


def test_protected_db_refused(pkg):
    client = MongoClient("mongodb://127.0.0.1:27017", serverSelectionTimeoutMS=500)
    try:
        for name in ("demand_forecasting_dev", "demand_forecasting_v2", "demand_forecasting_pub"):
            with pytest.raises(ImportRejected) as e:
                run(pkg, client[name], audit_of(pkg))
            assert e.value.code == "BASE_PROTEGIDA"
            with pytest.raises(ImportRejected):
                write_dataset(client[name], prepare(pkg, audit_of(pkg)))
        assert ds.main(["--package", str(pkg), "--db", "demand_forecasting_pub"]) == 1
    finally:
        client.close()


def test_interrupted_staging_cleaned_by_own_id_only(pkg, db):
    prep = prepare(pkg, audit_of(pkg))
    did = prep.header["dataset_id"]
    ds.ensure_indexes(db)
    db[HEADER_COLL].insert_one({"dataset_id": did, "status": "staging", "version": 1})
    stale = {"dataset_id": did, **prep.docs["plan_sales"][0]}
    db.plan_sales.insert_one(stale)
    other = {"dataset_id": "plds-otro", **prep.docs["plan_sales"][0]}                      # intento ajeno: no se toca
    db.plan_sales.insert_one(other)
    db[HEADER_COLL].insert_one({"dataset_id": "plds-otro", "status": "staging", "version": 0})
    r = write_dataset(db, prep)
    assert r["action"] in ("created", "new_version")
    assert db.plan_sales.count_documents({"dataset_id": did}) == len(prep.docs["plan_sales"])
    assert db.plan_sales.count_documents({"dataset_id": "plds-otro"}) == 1
    assert db[HEADER_COLL].find_one({"dataset_id": "plds-otro"})["status"] == "staging"
    assert db[HEADER_COLL].find_one({"dataset_id": did})["status"] == "current"


def test_failed_write_cleans_staging_and_keeps_previous(pkg, db, tmp_path):
    r1 = run(pkg, db, audit_of(pkg))
    books = default_books()
    books["setiembre"].append(line("ventas", 9, 29, "1002", 7, 70, serie="B001-new"))
    new_pkg = build_package(tmp_path / "v2", books)
    prep = prepare(new_pkg, audit_of(new_pkg))
    prep.docs["plan_credits"].append(dict(prep.docs["plan_credits"][0]))              # fallo inyectado: registro_id duplicado
    with pytest.raises(Exception):  # noqa: B017 - BulkWriteError
        write_dataset(db, prep)
    new_id = prep.header["dataset_id"]
    assert not any(db[c].count_documents({"dataset_id": new_id}) for c in ALL)
    assert db[HEADER_COLL].count_documents({"dataset_id": new_id}) == 0
    cur = list(db[HEADER_COLL].find({"status": "current"}))
    assert [c["dataset_id"] for c in cur] == [r1["dataset_id"]]
    assert db.plan_sales.count_documents({"dataset_id": r1["dataset_id"]}) == r1["collections"]["plan_sales"]


def test_cli_prints_json_without_private_paths(pkg, db, capsys):
    code = ds.main(["--package", str(pkg), "--db", db.name, "--audit", str(audit_of(pkg))])
    out = capsys.readouterr().out
    assert code == 0
    data = json.loads(out)
    assert data["action"] == "created" and data["sales_cutoff"] == "2026-09-30" and data["dataset_id"].startswith("plds-")
    assert str(pkg) not in out and "mongodb" not in out.lower()
    assert ds.main(["--package", str(pkg), "--db", db.name, "--audit", str(audit_of(pkg))]) == 0
    assert json.loads(capsys.readouterr().out)["action"] == "unchanged"


def test_cli_rejects_tampered_without_traceback(pkg, db, capsys):
    edit_csv(pkg, "ventas.csv", _coherent_qty_total)
    assert ds.main(["--package", str(pkg), "--db", db.name]) == 1
    cap = capsys.readouterr()
    assert "DERIVADO_NO_COINCIDE" in cap.err and cap.out == ""
    nothing_written(db)
