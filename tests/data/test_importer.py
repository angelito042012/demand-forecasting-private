import dataclasses
import json
from datetime import date, datetime

import pytest

from pipeline.data import importer
from pipeline.data.calendar import (
    EXCLUDED_DATES,
    FINAL_TEST_START,
    exclusion_mask,
    is_excluded,
    is_final_test,
    month_days,
)
from pipeline.data.catalog import UNKNOWN_CATEGORY, build_category_catalog, lookup
from pipeline.data.importer import (
    ImportInvariantError,
    ImportReport,
    classify_row,
    import_workbook,
)
from pipeline.data.reconcile import reconcile

from .conftest import make_row, write_xlsx

pytestmark = pytest.mark.mongo


def good_rows():
    return [
        make_row(ID_PEDIDO=1, SERIE_NUMERO="B1", ID_ARTICULO=100),
        make_row(ID_PEDIDO=2, SERIE_NUMERO="B2", ID_ARTICULO=101, FECHA=datetime(2026, 3, 3)),
        make_row(ID_PEDIDO=0, TIPO_DOC=7, SERIE_NUMERO="NC1", CANTIDAD=-1, CANTIDAD_UM_BASE=-1,
                 TOTAL_LINEA=-5.5),
    ]


def test_A01_import_and_reload_no_duplicates(xlsx, db):
    p = xlsx("marzo.xlsx", good_rows())
    r1 = import_workbook(p, db)
    assert (r1.filas_leidas, r1.ventas_aceptadas, r1.notas_credito, r1.rechazadas) == (3, 2, 1, 0)
    assert (r1.insertadas, r1.ya_existentes, r1.estado) == (3, 0, "completed")
    r2 = import_workbook(p, db)
    assert r2.noop and r2.insertadas == 0 and r2.ya_existentes == 3
    assert db.sales.count_documents({}) == 2 and db.credit_notes.count_documents({}) == 1
    assert db.imports.count_documents({}) == 2
    json.dumps(r1.to_dict())  # serializable
    s = db.sales.find_one({"sku": "100"})
    assert s["categoria_original"] == "CAT A" and s["fecha"] == "2026-03-02"
    assert s["provenance"] == "OBSERVED_EXCEL" and s["source_row"] == 3
    assert s["importe"].to_decimal() == 11
    assert "SERIE_NUMERO" not in s and "cliente" not in s


def test_reload_with_different_sha_same_content_not_duplicated(xlsx, db):
    import_workbook(xlsx("marzo.xlsx", good_rows()), db)
    # contenido logico igual, archivo distinto (otro sha): ventas no se duplican
    p2 = write_xlsx(xlsx("x.xlsx", []).parent / "marzo_b.xlsx", good_rows()[:2], title_row=False)
    r = import_workbook(p2, db, expected_month="2026-03")
    assert r.insertadas == 0 and r.ya_existentes == 2
    assert db.sales.count_documents({}) == 2


def test_A02_invalid_date_summary_and_credit_note(xlsx, db):
    rows = good_rows() + [
        make_row(FECHA="no-fecha"),
        make_row(FECHA=None, ID_ARTICULO=None, CANTIDAD=None, TOTAL_LINEA="TOTAL"),  # fila resumen
        make_row(FECHA=datetime(2026, 4, 1)),
        make_row(ID_ARTICULO=None),
        make_row(ID_ALMACEN=None),
        make_row(CANTIDAD=None),
        make_row(TOTAL_LINEA="abc"),
        make_row(CANTIDAD=0, CANTIDAD_UM_BASE=0),
        make_row(TOTAL_LINEA=-3.0),  # negativo que no es tipo 7
        make_row(MONEDA="USD"),
        make_row(VEN_ESTADO="ANULADO"),
        make_row(EQUIVALENCIA=0),
        make_row(EQUIVALENCIA=12, CANTIDAD_UM_BASE=2),
        make_row(TIPO_DOC=7, TOTAL_LINEA=5.0),
    ]
    p = xlsx("marzo.xlsx", rows)
    r = import_workbook(p, db)
    assert r.filas_leidas == 3 + 14
    assert r.rechazadas == 14 and r.ventas_aceptadas == 2 and r.notas_credito == 1
    assert r.rechazos_por_motivo == {
        "FECHA_INVALIDA": 2, "FECHA_FUERA_DE_MES": 1, "SKU_FALTANTE": 1, "ALMACEN_FALTANTE": 1,
        "CANTIDAD_FALTANTE": 1, "IMPORTE_NO_NUMERICO": 1, "CANTIDAD_NO_POSITIVA_EN_VENTA": 1,
        "IMPORTE_NEGATIVO_NO_TIPO7": 1, "MONEDA_NO_PEN": 1, "ESTADO_NO_ACTIVO": 1,
        "EQUIVALENCIA_INVALIDA": 1, "EQUIVALENCIA_INCONSISTENTE": 1,
        "TIPO7_IMPORTE_NO_NEGATIVO": 1}
    assert db.import_rejects.count_documents({}) == 14
    rej = db.import_rejects.find_one({"motivo": "FECHA_FUERA_DE_MES"})
    assert rej["source_row"] and rej["valores"]["fecha_raw"].startswith("2026-04-01")
    # el reingreso no duplica rechazos
    import_workbook(p, db)
    assert db.import_rejects.count_documents({}) == 14
    # la nota de credito no esta en sales y no hay vinculo a ventas
    assert db.sales.count_documents({"tipo_doc": 7}) == 0
    nc = db.credit_notes.find_one({})
    assert nc["importe"].to_decimal() < 0 and "venta_id" not in nc


def test_identical_legit_lines_not_merged_and_overlap(xlsx, db):
    dup = make_row(ID_PEDIDO=9, SERIE_NUMERO="B9")
    a = xlsx("marzo.xlsx", [dup, dup, dup, make_row(ID_PEDIDO=10, SERIE_NUMERO="B10")])
    r = import_workbook(a, db)
    assert r.ventas_aceptadas == 4 and r.insertadas == 4
    assert db.sales.count_documents({}) == 4
    # archivo solapado: las mismas 3 lineas identicas mas una nueva, en otro orden
    b = write_xlsx(a.parent / "marzo_ext.xlsx",
                   [make_row(ID_PEDIDO=11, SERIE_NUMERO="B11"), dup, dup, dup], title_row=False)
    r2 = import_workbook(b, db, expected_month="2026-03")
    assert r2.insertadas == 1 and r2.ya_existentes == 3
    assert db.sales.count_documents({}) == 5


def test_failure_midway_then_resume(xlsx, db, monkeypatch):
    rows = [make_row(ID_PEDIDO=i, SERIE_NUMERO=f"B{i}", ID_ARTICULO=100 + i) for i in range(1, 8)]
    p = xlsx("marzo.xlsx", rows)
    real = importer._bulk
    calls = {"n": 0}

    def flaky(coll, docs, batch_size):
        calls["n"] += 1
        real(coll, docs[:3], batch_size)  # escritura parcial y luego caida
        raise RuntimeError("caida simulada")

    monkeypatch.setattr(importer, "_bulk", flaky)
    with pytest.raises(RuntimeError):
        import_workbook(p, db)
    failed = db.imports.find_one({})
    assert failed["estado"] == "failed" and "caida" in failed["error"]
    assert db.sales.count_documents({}) == 3
    monkeypatch.setattr(importer, "_bulk", real)
    r = import_workbook(p, db)
    assert r.estado == "completed" and not r.noop
    assert r.insertadas == 4 and r.ya_existentes == 3
    assert db.sales.count_documents({}) == 7
    assert sorted(d["estado"] for d in db.imports.find({})) == ["completed", "failed"]


def test_count_invariant_enforced():
    rep = ImportReport("i", "f", "s", "2026-03", filas_leidas=5, ventas_aceptadas=2,
                       notas_credito=1, rechazadas=1)
    with pytest.raises(ImportInvariantError):
        rep.check_invariant()
    assert dataclasses.is_dataclass(rep)


def test_invariant_failure_marks_failed(xlsx, db, monkeypatch):
    p = xlsx("marzo.xlsx", good_rows())
    monkeypatch.setattr(ImportReport, "check_invariant",
                        lambda self: (_ for _ in ()).throw(ImportInvariantError("x")))
    with pytest.raises(ImportInvariantError):
        import_workbook(p, db)
    assert db.imports.find_one({})["estado"] == "failed"
    assert db.sales.count_documents({}) == 0


def test_equivalence_inconsistent_unit_and_case(xlsx, db):
    rows = [make_row(ID_PEDIDO=1, ID_UM="CJA", EQUIVALENCIA=12, CANTIDAD=2, CANTIDAD_UM_BASE=24,
                     UM_BASE="und", SERIE_NUMERO="E1"),
            make_row(ID_PEDIDO=2, EQUIVALENCIA=12, CANTIDAD=2, CANTIDAD_UM_BASE=2, SERIE_NUMERO="E2")]
    r = import_workbook(xlsx("marzo.xlsx", rows), db)
    assert r.ventas_aceptadas == 1 and r.rechazos_por_motivo == {"EQUIVALENCIA_INCONSISTENTE": 1}
    s = db.sales.find_one({})
    assert s["cantidad_base"] == 24 and s["unidad_original"] == "CJA"
    assert s["um_base_original"] == "und" and s["unidad_base"] == "UND"


def test_classify_row_pure():
    kind, f = classify_row(dict(zip(__import__("tests.data.conftest", fromlist=["HEADERS"]).HEADERS,
                                    make_row())), (2026, 3))
    assert kind == "sale" and f["sku"] == "100"


def test_dry_run_writes_nothing(xlsx, db):
    r = importer.import_workbook(xlsx("marzo.xlsx", good_rows()), db, dry_run=True)
    assert r.ventas_aceptadas == 2 and r.insertadas == 0
    assert db.sales.count_documents({}) == 0 and db.imports.count_documents({}) == 0


def test_catalog_by_cutoff(xlsx, db):
    jul = [make_row(ID_PEDIDO=1, SERIE_NUMERO="J1", ID_ARTICULO=16140041, FECHA=datetime(2026, 7, 10),
                    GRUPO="MAQUILLAJE PARA ROSTRO")]
    ago = [make_row(ID_PEDIDO=2, SERIE_NUMERO="A1", ID_ARTICULO=16140041, FECHA=datetime(2026, 8, 5),
                    GRUPO="MAQUILLAJE PARA OJOS"),
           make_row(ID_PEDIDO=3, SERIE_NUMERO="A2", ID_ARTICULO=16140041, FECHA=datetime(2026, 8, 6),
                    GRUPO="MAQUILLAJE PARA OJOS"),
           make_row(ID_PEDIDO=4, SERIE_NUMERO="A3", ID_ARTICULO=555, FECHA=datetime(2026, 8, 6))]
    import_workbook(xlsx("julio.xlsx", jul), db)
    import_workbook(xlsx("agosto.xlsx", ago), db)
    cat = build_category_catalog(db, date(2026, 7, 31))
    assert cat["16140041"] == "MAQUILLAJE PARA ROSTRO"
    assert lookup(cat, "555") == UNKNOWN_CATEGORY
    assert build_category_catalog(db, "2026-08-31")["16140041"] == "MAQUILLAJE PARA OJOS"
    # categoria_original conserva el valor por transaccion
    assert db.sales.count_documents({"sku": "16140041", "categoria_original": "MAQUILLAJE PARA OJOS"}) == 2


def test_catalog_tiebreak_frequency_then_alpha(xlsx, db):
    d = datetime(2026, 3, 5)
    rows = [make_row(ID_PEDIDO=1, SERIE_NUMERO="1", FECHA=d, GRUPO="B"),
            make_row(ID_PEDIDO=2, SERIE_NUMERO="2", FECHA=d, GRUPO="B"),
            make_row(ID_PEDIDO=3, SERIE_NUMERO="3", FECHA=d, GRUPO="A"),
            make_row(ID_PEDIDO=4, SERIE_NUMERO="4", ID_ARTICULO=200, FECHA=d, GRUPO="Z"),
            make_row(ID_PEDIDO=5, SERIE_NUMERO="5", ID_ARTICULO=200, FECHA=d, GRUPO="M")]
    import_workbook(xlsx("marzo.xlsx", rows), db)
    cat = build_category_catalog(db, "2026-03-31")
    assert cat["100"] == "B" and cat["200"] == "M"


def test_excluded_days_mask_without_zeros_or_deletion(xlsx, db):
    assert EXCLUDED_DATES == {date(2026, 4, 3), date(2026, 4, 12), date(2026, 6, 7)}
    assert is_excluded(date(2026, 4, 3)) and is_excluded("2026-06-07") and not is_excluded(date(2026, 4, 4))
    assert is_final_test(date(2026, 8, 15)) and FINAL_TEST_START == date(2026, 8, 1)
    days = month_days(2026, 4)
    assert len(days) == 30 and sum(exclusion_mask(days)) == 2  # calendario no comprimido
    # una venta en dia excluido NO se elimina; el dia sin registros no genera filas
    rows = [make_row(ID_PEDIDO=1, SERIE_NUMERO="1", FECHA=datetime(2026, 4, 3)),
            make_row(ID_PEDIDO=2, SERIE_NUMERO="2", FECHA=datetime(2026, 4, 4)),
            make_row(ID_PEDIDO=3, SERIE_NUMERO="3", FECHA=datetime(2026, 4, 12))]
    import_workbook(xlsx("abril.xlsx", rows), db)
    assert db.sales.count_documents({}) == 3
    rec = reconcile(db)["2026-04"]
    assert rec["dias_con_registros"] == 3 and len(rec["dias_sin_registros"]) == 27
    assert rec["dias_sin_registros_excluidos"] == []  # con registros: se mantienen
    assert db.sales.count_documents({"cantidad_base": 0}) == 0


def test_reconcile_month(xlsx, db):
    rows = good_rows() + [make_row(FECHA="x")]
    import_workbook(xlsx("marzo.xlsx", rows), db)
    m = reconcile(db)["2026-03"]
    imp = m["importaciones"][0]
    assert (imp["filas_leidas"], m["ventas"], m["notas_credito"], imp["rechazos"]) == (4, 2, 1, 1)
    assert m["cuadra_importaciones"] and m["cuadra_conjunto_logico"] and m["sku_con_ventas"] == 2 and m["dias_con_registros"] == 2
    assert m["suma_importe_ventas"] == "22.00"
    assert m["suma_importe_creditos"] == "-5.50" and m["saldo_neto"] == "16.50"
    assert "2026-03-01" in m["dias_sin_registros"]


def test_excluded_dates_listed_when_missing(xlsx, db):
    rows = [make_row(FECHA=datetime(2026, 4, 1))]
    import_workbook(xlsx("abril.xlsx", rows), db)
    m = reconcile(db)["2026-04"]
    assert m["dias_sin_registros_excluidos"] == ["2026-04-03", "2026-04-12"]
