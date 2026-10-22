"""Dataset v2 (T20 §1): 14 libros + octubre verificado contra SQL + parcial del 21/10 aparte. Sinteticos; la prueba con datos reales
solo corre con RUN_REALDATA=1 y en --dry-run (no escribe)."""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path

import pytest

from pipeline.plan import dataset as ds
from pipeline.plan import dataset_v2 as v2
from pipeline.plan.dataset import COLLECTIONS, HEADER_COLL, ImportRejected
from pipeline.plan.dataset_v2 import PARTIAL_COLL, prepare, run
from pipeline.plan.normalize import sha256_file
from tests.plan.conftest import audit_of, line, write_book

pytestmark = pytest.mark.mongo
ROOT = Path(__file__).resolve().parents[2]


def october_rows():
    rows = []
    for d, p in ((1, "1001"), (2, "1002"), (10, "1001"), (19, "1003"), (20, "1001")):
        rows.append(line("ventas", 10, d, p, serie=f"B001-O{d}{p}"))
    rows.append(line("ventas", 10, 12, "1001", -1, -10, tipo="7", serie="NC01-O"))
    return rows


PARTIAL_ROWS = [
    ["2026-10-21", "10:16:33", "03", "B001-00681900", "00001001", "001", "UND", "1.0000", "1.0000", "53.0000"],
    ["2026-10-21", "10:17:45", "03", "B001-00681901", "00001002", "001", "UND", "2.0000", "1.0000", "37.4000"],
    ["2026-10-21", "16:26:38", "03", "B001-00681902", "00001001", "001", "UND", "1.0000", "1.0000", "20.0000"],
]


def make_inputs(pkg: Path, *, rows=None, partial=None, report_edit=None, name="oct"):
    d = pkg.parent / name
    d.mkdir(exist_ok=True)
    book = d / "octubre.xlsx"
    write_book(book, "ventas", rows if rows is not None else october_rows())
    n = len(rows if rows is not None else october_rows())
    rep = {"ultimo_dia_completo": "2026-10-20", "libros": {"octubre.xlsx": sha256_file(book)},
           "ventas_excel_vs_sql": {"octubre.xlsx": {"lineas_excel": n, "lineas_sql": n, "solo_excel": 0, "solo_sql": 0,
                                                    "documentos_excel": n - 1, "ultimo_dia": "2026-10-20", "coincide": True}},
           "datos_preparados": {"parcial_21_lineas": len(partial if partial is not None else PARTIAL_ROWS),
                                "parcial_21_ultima_hora_documento": "16:26:38"}}
    if report_edit:
        report_edit(rep)
    rpath = d / "informe.json"
    rpath.write_text(json.dumps(rep), encoding="utf-8")
    cpath = d / "parcial.csv"
    with cpath.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(v2.PARTIAL_COLS)
        w.writerows(partial if partial is not None else PARTIAL_ROWS)
    return book, rpath, cpath


@pytest.fixture()
def inputs(pkg):
    return make_inputs(pkg)


def go(pkg, inputs):
    book, rep, part = inputs
    return prepare(pkg, book, rep, part, audit_of(pkg))


def reject(pkg, inputs, code):
    with pytest.raises(ImportRejected) as e:
        go(pkg, inputs)
    assert e.value.code == code
    return e.value


# ------------------------------------------------------------------ preparacion
def test_prepare_seals_v2(pkg, inputs):
    p = go(pkg, inputs)
    v1 = ds.prepare(pkg, audit_of(pkg))
    h = p.header
    assert h["dataset_id"].startswith("plds-") and h["dataset_id"] != v1.header["dataset_id"]
    assert h["base_dataset_id"] == v1.header["dataset_id"]
    assert h["window_end"] == h["sales_cutoff"] == "2026-10-20" and len(h["sources"]) == 15
    assert h["sources"][-1]["archivo"] == "octubre.xlsx" and h["source_rows"] == v1.header["source_rows"] + 6
    assert h["october_verification"] == {"sql_report_sha256": sha256_file(inputs[1]), "lines": 6, "documents": 5, "sql_match": True}
    assert h["partial"] == {"date": "2026-10-21", "lines": 3, "last_document_time": "16:26:38", "collection": "plan_sales_partial",
                            "sha256": h["partial"]["sha256"], "used_for_forecast": False}
    assert len(h["partial"]["sha256"]) == 64
    sales = p.docs["plan_sales"]
    assert len(sales) == len(v1.docs["plan_sales"]) + 5 and max(d["fecha"] for d in sales) == "2026-10-20"
    assert len(p.docs["plan_credits"]) == len(v1.docs["plan_credits"]) + 1
    assert len({d["registro_id"] for c in COLLECTIONS.values() for d in p.docs[c]}) == h["source_rows"]


def test_partial_only_in_separate_collection_with_original_codes(pkg, inputs):
    p = go(pkg, inputs)
    assert set(p.docs) == set(COLLECTIONS.values()) and set(p.extra) == {PARTIAL_COLL}
    assert all(d["fecha"] <= "2026-10-20" for c in p.docs.values() for d in c)
    part = p.extra[PARTIAL_COLL]
    assert [d["producto_id"] for d in part] == ["1001", "1002", "1001"] and {d["almacen"] for d in part} == {"1"}
    assert part[0] == {"linea": 1, "fecha": "2026-10-21", "hora_documento": "10:16:33", "tipo_documento": "03",
                       "documento": "B001-00681900", "producto_id": "1001", "almacen": "1", "unidad": "UND",
                       "cantidad": "1", "total": "53"}


def test_id_depends_on_book_and_partial(pkg, inputs):
    a = go(pkg, inputs).header["dataset_id"]
    assert go(pkg, inputs).header["dataset_id"] == a                              # determinista
    other = make_inputs(pkg, partial=PARTIAL_ROWS[:2], name="oct2", report_edit=lambda r: r["datos_preparados"].update(
        parcial_21_ultima_hora_documento="10:17:45"))
    assert go(pkg, other).header["dataset_id"] != a
    rows = october_rows()
    rows[0] = line("ventas", 10, 1, "1001", 3, 30, serie="B001-O1x")
    assert go(pkg, make_inputs(pkg, rows=rows, name="oct3")).header["dataset_id"] != a


# ------------------------------------------------------------------ rechazos
def test_rejects_book_sha_not_in_report(pkg, inputs):
    rep = inputs[1]
    r = json.loads(rep.read_text(encoding="utf-8"))
    r["libros"]["octubre.xlsx"] = "0" * 64
    rep.write_text(json.dumps(r), encoding="utf-8")
    reject(pkg, inputs, "FUENTE_ALTERADA")


def test_rejects_modified_book_after_report(pkg, inputs):
    book = inputs[0]
    write_book(book, "ventas", october_rows() + [line("ventas", 10, 5, "1002", serie="B001-extra")])
    reject(pkg, inputs, "FUENTE_ALTERADA")


@pytest.mark.parametrize("edit", [
    lambda r: r["ventas_excel_vs_sql"]["octubre.xlsx"].update(coincide=False),
    lambda r: r["ventas_excel_vs_sql"]["octubre.xlsx"].update(lineas_excel=7),
    lambda r: r["ventas_excel_vs_sql"]["octubre.xlsx"].update(lineas_sql=7),
    lambda r: r["ventas_excel_vs_sql"]["octubre.xlsx"].update(solo_sql=1),
    lambda r: r["ventas_excel_vs_sql"]["octubre.xlsx"].update(ultimo_dia="2026-10-19"),
    lambda r: r["ventas_excel_vs_sql"].pop("octubre.xlsx"),
])
def test_rejects_sql_mismatch(pkg, edit):
    reject(pkg, make_inputs(pkg, report_edit=edit), "SQL_NO_COINCIDE")


def test_rejects_october_sale_after_cutoff(pkg):
    rows = october_rows() + [line("ventas", 10, 21, "1001", serie="B001-late")]
    with pytest.raises(ImportRejected) as e:
        go(pkg, make_inputs(pkg, rows=rows))
    assert e.value.code == "DERIVADO_NO_COINCIDE"                    # fuera de la ventana declarada


@pytest.mark.parametrize("partial,code", [
    ([["2026-10-20", *PARTIAL_ROWS[0][1:]]], "PARCIAL_INVALIDO"),
    ([[*PARTIAL_ROWS[0][:1], "25:61:00", *PARTIAL_ROWS[0][2:]]], "PARCIAL_INVALIDO"),
    ([[*PARTIAL_ROWS[0][:7], "abc", *PARTIAL_ROWS[0][8:]]], "PARCIAL_INVALIDO"),
    ([[*PARTIAL_ROWS[0][:4], "X1", *PARTIAL_ROWS[0][5:]]], "PARCIAL_INVALIDO"),
])
def test_rejects_bad_partial(pkg, partial, code):
    reject(pkg, make_inputs(pkg, partial=partial, report_edit=lambda r: r["datos_preparados"].update(
        parcial_21_lineas=1, parcial_21_ultima_hora_documento="10:16:33")), code)


def test_rejects_partial_not_matching_report(pkg):
    reject(pkg, make_inputs(pkg, report_edit=lambda r: r["datos_preparados"].update(parcial_21_lineas=99)), "PARCIAL_INVALIDO")


def test_rejects_partial_wrong_columns(pkg, inputs):
    inputs[2].write_text("a,b\n1,2\n", encoding="utf-8")
    reject(pkg, inputs, "CSV_ESTRUCTURA_INVALIDA")


def test_v1_rules_still_apply(pkg, inputs):
    p = pkg / "01_normalizados" / "ventas.csv"
    p.write_text(p.read_text(encoding="utf-8-sig").replace("PRODUCTO UNO", "PRODUCTO UNO!", 1), encoding="utf-8-sig")
    reject(pkg, inputs, "DERIVADO_NO_COINCIDE")


# ------------------------------------------------------------------ importacion
def test_dry_run_writes_nothing(db, pkg, inputs):
    book, rep, part = inputs
    r = run(pkg, book, rep, part, db, audit_of(pkg), dry_run=True)
    assert r["action"] == "would_created" and r["collections"][PARTIAL_COLL] == 3
    assert not set(db.list_collection_names()) & {*COLLECTIONS.values(), HEADER_COLL, PARTIAL_COLL}


def test_create_idempotent_and_partial_isolated(db, pkg, inputs):
    book, rep, part = inputs
    r1 = run(pkg, book, rep, part, db, audit_of(pkg))
    assert r1["action"] == "created" and r1["version"] == 1 and r1["sales_cutoff"] == "2026-10-20"
    did = r1["dataset_id"]
    counts = {c: db[c].count_documents({"dataset_id": did}) for c in (*COLLECTIONS.values(), PARTIAL_COLL)}
    assert counts[PARTIAL_COLL] == 3 and counts["plan_sales"] == r1["collections"]["plan_sales"]
    r2 = run(pkg, book, rep, part, db, audit_of(pkg))
    assert r2["action"] == "unchanged" and r2["dataset_id"] == did
    assert {c: db[c].count_documents({}) for c in counts} == counts
    # el parcial nunca aparece en plan_sales ni hay ventas posteriores al corte
    assert db.plan_sales.count_documents({"dataset_id": did, "fecha": {"$gt": "2026-10-20"}}) == 0
    head = db[HEADER_COLL].find_one({"dataset_id": did})
    assert head["status"] == "current" and head["partial"]["used_for_forecast"] is False and head["partial"]["lines"] == 3
    assert db[PARTIAL_COLL].find_one({"dataset_id": did, "linea": 1})["producto_id"] == "1001"


def test_v1_superseded_and_readable_then_new_v2_version(db, pkg, inputs):
    book, rep, part = inputs
    v1 = ds.run(pkg, db, audit_of(pkg))
    assert v1["action"] == "created"
    r2 = run(pkg, book, rep, part, db, audit_of(pkg))
    assert r2["action"] == "new_version" and r2["version"] == 2
    old = db[HEADER_COLL].find_one({"dataset_id": v1["dataset_id"]})
    new = db[HEADER_COLL].find_one({"dataset_id": r2["dataset_id"]})
    assert old["status"] == "superseded" and new["status"] == "current" and new["supersedes"] == v1["dataset_id"]
    assert new["base_dataset_id"] == v1["dataset_id"]
    assert db.plan_sales.count_documents({"dataset_id": v1["dataset_id"]}) == v1["collections"]["plan_sales"]   # v1 sigue legible
    assert db.plan_sales.count_documents({"dataset_id": r2["dataset_id"]}) == v1["collections"]["plan_sales"] + 5
    assert db[PARTIAL_COLL].count_documents({"dataset_id": v1["dataset_id"]}) == 0
    # un parcial nuevo (otro contenido) => v3, v2 superseded; v1 no se reimporta
    other = make_inputs(pkg, partial=PARTIAL_ROWS[:2], name="oct2", report_edit=lambda r: r["datos_preparados"].update(
        parcial_21_ultima_hora_documento="10:17:45"))
    r3 = run(pkg, other[0], other[1], other[2], db, audit_of(pkg))
    assert r3["action"] == "new_version" and r3["version"] == 3
    assert db[HEADER_COLL].find_one({"dataset_id": r2["dataset_id"]})["status"] == "superseded"
    assert db[PARTIAL_COLL].count_documents({"dataset_id": r2["dataset_id"]}) == 3
    with pytest.raises(ImportRejected) as e:
        run(pkg, book, rep, part, db, audit_of(pkg))
    assert e.value.code == "VERSION_SUSTITUIDA"
    with pytest.raises(ImportRejected) as e:
        ds.run(pkg, db, audit_of(pkg))
    assert e.value.code == "VERSION_SUSTITUIDA"


def test_rejection_writes_nothing(db, pkg, inputs):
    book, rep, part = inputs
    r = json.loads(rep.read_text(encoding="utf-8"))
    r["ventas_excel_vs_sql"]["octubre.xlsx"]["coincide"] = False
    rep.write_text(json.dumps(r), encoding="utf-8")
    with pytest.raises(ImportRejected):
        run(pkg, book, rep, part, db, audit_of(pkg))
    assert not set(db.list_collection_names()) & {*COLLECTIONS.values(), HEADER_COLL, PARTIAL_COLL}


def test_protected_db_and_cli(pkg, inputs, capsys):
    book, rep, part = inputs
    base = ["--package", str(pkg), "--october", str(book), "--sql-report", str(rep), "--partial-csv", str(part)]
    assert v2.main([*base, "--db", "demand_forecasting_dev"]) == 1
    assert v2.main([*base, "--db", "mal nombre"]) == 2
    assert v2.main([*base, "--db", "df_test_cli", "--audit", str(pkg / "no_existe.json")]) == 1


# ------------------------------------------------------------------ datos reales (opcional; solo --dry-run)
REAL = {"pkg": ROOT / "artifacts/private/datos_preparados_v1", "october": Path("C:/Users/rogel/Documents/Datos/octubre.xlsx"),
        "report": ROOT / "artifacts/private/sql21_prep/informe.json",
        "partial": ROOT / "artifacts/private/sql21_prep/ventas_20261021_parcial_sql.csv"}


@pytest.mark.skipif(os.environ.get("RUN_REALDATA") != "1" or not all(p.exists() for p in REAL.values()),
                    reason="RUN_REALDATA=1 y datos reales privados requeridos")
def test_real_data_dry_run(db):
    r = run(REAL["pkg"], REAL["october"], REAL["report"], REAL["partial"], db, ds.default_audit(REAL["pkg"]), dry_run=True)
    assert r["action"] == "would_created" and r["sales_cutoff"] == "2026-10-20"
    assert r["collections"][PARTIAL_COLL] == 318
    assert not set(db.list_collection_names()) & {*COLLECTIONS.values(), HEADER_COLL, PARTIAL_COLL}
    h = prepare(REAL["pkg"], REAL["october"], REAL["report"], REAL["partial"], ds.default_audit(REAL["pkg"])).header
    assert len(h["sources"]) == 15 and h["october_verification"]["lines"] == 9853 and h["october_verification"]["documents"] == 5609
    assert h["partial"]["last_document_time"] == "16:26:38" and h["partial"]["used_for_forecast"] is False
