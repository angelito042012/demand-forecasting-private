"""Regresiones de la revision de Codex 01: R01 (errores de escritura), R02 (identidad de
notas de credito y conflictos) y R03 (conciliacion de archivos solapados)."""
from datetime import datetime

import pytest
from pymongo.errors import BulkWriteError

from pipeline.data import importer
from pipeline.data.importer import (
    ImportWriteError,
    IncompatibleSchemaError,
    _bulk,
    _run_bulk,
    ensure_indexes,
    import_workbook,
)
from pipeline.data.reconcile import reconcile

from .conftest import make_row, write_xlsx

pytestmark = pytest.mark.mongo


def nc(serie, amount, **kw):
    return make_row(ID_PEDIDO=0, TIPO_DOC=7, SERIE_NUMERO=serie, CANTIDAD=-1, CANTIDAD_UM_BASE=-1,
                    TOTAL_LINEA=amount, **kw)


def sale(n, **kw):
    return make_row(ID_PEDIDO=n, SERIE_NUMERO=f"B{n}", ID_ARTICULO=100 + n, **kw)


def folder(xlsx):
    return xlsx("_dir.xlsx", []).parent


def raising(exc):
    def _raise(self, ops, ordered):
        raise exc
    return _raise


class FakeColl:
    """Proxy de coleccion que inyecta el comportamiento de bulk_write indicado."""

    def __init__(self, real, behaviour):
        self.real, self.behaviour, self.calls = real, behaviour, 0

    def bulk_write(self, ops, ordered=False):
        self.calls += 1
        return self.behaviour(self, ops, ordered)

    def __getattr__(self, name):
        return getattr(self.real, name)


def bwe(write_errors=(), wc=(), upserted=0):
    return BulkWriteError({"writeErrors": list(write_errors), "writeConcernErrors": list(wc),
                           "nUpserted": upserted, "nInserted": 0, "nMatched": 0, "nModified": 0,
                           "nRemoved": 0, "upserted": []})


# ------------------------------------------------------------------ R01
def test_r01_validation_error_121_fails_import_and_keeps_good_docs(xlsx, db):
    db.create_collection("sales", validator={"$jsonSchema": {
        "bsonType": "object", "properties": {"sku": {"bsonType": "string", "maxLength": 8}}}})
    rows = [sale(1), sale(2), make_row(ID_PEDIDO=3, SERIE_NUMERO="B3", ID_ARTICULO="X" * 20)]
    p = xlsx("marzo.xlsx", rows)
    with pytest.raises(ImportWriteError, match="121"):
        import_workbook(p, db)
    rec = db.imports.find_one({})
    assert rec["estado"] == "failed" and "121" in rec["error"]
    assert db.sales.count_documents({}) == 2          # lo valido queda; lo invalido no se da por escrito
    assert db.sales.count_documents({"sku": "X" * 20}) == 0
    # corregido el origen del error, la recarga completa sin duplicar
    db.command("collMod", "sales", validator={})
    r = import_workbook(p, db)
    assert r.estado == "completed" and (r.insertadas, r.ya_existentes) == (1, 2)
    assert db.sales.count_documents({}) == 3


def test_r01_write_concern_error_propagates(db):
    ensure_indexes(db)
    wc = [{"code": 64, "errmsg": "waiting for replication timed out"}]
    coll = FakeColl(db.sales, raising(bwe(wc=wc, upserted=1)))
    with pytest.raises(ImportWriteError, match="write concern"):
        _run_bulk(coll, [object()])


def test_r01_mixed_duplicate_and_real_error_is_not_recoverable(db):
    ensure_indexes(db)
    errs = [{"index": 0, "code": 11000, "errmsg": "dup"}, {"index": 1, "code": 121, "errmsg": "doc"}]
    coll = FakeColl(db.sales, raising(bwe(errs)))
    with pytest.raises(ImportWriteError, match="121"):
        _run_bulk(coll, [object(), object()])
    assert coll.calls == 1  # no se reintenta nada si hay un error real


def test_r01_unknown_bulk_error_without_details_propagates(db):
    coll = FakeColl(db.sales, raising(bwe()))
    with pytest.raises(ImportWriteError):
        _run_bulk(coll, [object()])


def test_r01_concurrent_duplicate_is_recovered_and_verified(xlsx, db, monkeypatch):
    ensure_indexes(db)
    captured = {}

    def spy(d, sales, notes, rejects, bs):
        captured["doc"] = sales[0]
        raise RuntimeError("solo capturar el documento")
    monkeypatch.setattr(importer, "_write_batches", spy)
    with pytest.raises(RuntimeError):
        import_workbook(xlsx("marzo.xlsx", [sale(1)]), db)
    monkeypatch.undo()
    doc = captured["doc"]
    raced = {k: v for k, v in doc.items() if k != "sources"}

    def race(self, ops, ordered):
        if self.calls == 1:   # otro proceso inserta el mismo documento justo antes
            self.real.insert_one(dict(raced))
            raise bwe([{"index": 0, "code": 11000, "errmsg": "E11000 dup"}])
        return self.real.bulk_write(ops, ordered=ordered)

    ins, dup = _bulk(FakeColl(db.sales, race), [doc], 100)
    assert (ins, dup) == (0, 1)
    stored = list(db.sales.find({"linea_id": doc["linea_id"]}))
    assert len(stored) == 1 and len(stored[0]["sources"]) == 1  # existe una vez, con procedencia


def test_r01_persistent_duplicate_error_propagates(db):
    ensure_indexes(db)
    coll = FakeColl(db.sales, raising(bwe([{"index": 0, "code": 11000, "errmsg": "dup"}])))
    with pytest.raises(ImportWriteError, match="duplicada persistente"):
        _run_bulk(coll, [object()])


def test_r01_silently_lost_writes_are_detected(db):
    class Fake:
        upserted_count = 1

    coll = FakeColl(db.sales, lambda s, ops, o: Fake())
    with pytest.raises(ImportWriteError, match="persistidos"):
        _bulk(coll, [{"linea_id": "a", "sources": []}], 10)


# ------------------------------------------------------------------ R02
def test_r02_reexported_renamed_reordered_note_not_duplicated_and_sources_kept(xlsx, db):
    a = xlsx("marzo.xlsx", [nc("NC-1", -5.5), nc("NC-2", -3.0), sale(1)])
    import_workbook(a, db)
    b = write_xlsx(folder(xlsx) / "reexport_marzo.xlsx", [sale(1), nc("NC-2", -3), nc("NC-1", -5.50)],
                   title_row=False)
    r = import_workbook(b, db, expected_month="2026-03")
    assert (r.insertadas, r.ya_existentes, r.en_conflicto, r.estado) == (0, 3, 0, "completed")
    assert db.credit_notes.count_documents({}) == 2
    note = next(d for d in db.credit_notes.find() if float(d["importe"].to_decimal()) == -5.5)
    assert {s["source_file"] for s in note["sources"]} == {"marzo.xlsx", "reexport_marzo.xlsx"}


def test_r02_different_note_same_file_name_and_row_is_not_lost(xlsx, db):
    p = xlsx("marzo.xlsx", [nc("NC-1", -5.5)])
    import_workbook(p, db)
    write_xlsx(p, [nc("NC-2", -9.0)])  # el archivo reemplazado conserva nombre y fila
    r = import_workbook(p, db)
    assert r.insertadas == 1 and r.estado == "completed"
    assert sorted(float(d["importe"].to_decimal()) for d in db.credit_notes.find()) == [-9.0, -5.5]


def test_r02_corrected_document_is_a_conflict_not_a_silent_add_or_loss(xlsx, db):
    import_workbook(xlsx("marzo.xlsx", [nc("NC-1", -5.5), sale(1)]), db)
    fixed = write_xlsx(folder(xlsx) / "marzo_corregido.xlsx",
                       [nc("NC-1", -9.0), sale(1, PRECIO=6.0, TOTAL_LINEA=12.0)])
    r = import_workbook(fixed, db, expected_month="2026-03")
    assert r.estado == "completed_with_conflicts" and r.en_conflicto == 2 and r.insertadas == 0
    assert db.credit_notes.count_documents({}) == 1 and db.sales.count_documents({}) == 1
    assert db.credit_notes.find_one()["importe"].to_decimal() == -5.5  # el original no se sobrescribe
    conflicts = list(db.import_conflicts.find({}))
    assert len(conflicts) == 2 and all(c["estado"] == "OPEN" for c in conflicts)
    assert all(c["lineas_existentes"] and c["lineas_nuevas"] for c in conflicts)
    # repetir la carga no multiplica conflictos ni inserta nada
    r2 = import_workbook(fixed, db, expected_month="2026-03")
    assert r2.en_conflicto == 2 and r2.insertadas == 0
    assert db.import_conflicts.count_documents({}) == 2
    assert db.credit_notes.count_documents({}) == 1


def test_r02_identical_legit_note_lines_and_overlap(xlsx, db):
    twice = nc("NC-7", -2.0)
    a = xlsx("marzo.xlsx", [twice, twice])
    r = import_workbook(a, db)
    assert r.insertadas == 2 and db.credit_notes.count_documents({}) == 2
    b = write_xlsx(folder(xlsx) / "marzo_ext.xlsx", [nc("NC-8", -1.0), twice, twice], title_row=False)
    r2 = import_workbook(b, db, expected_month="2026-03")
    assert (r2.insertadas, r2.ya_existentes) == (1, 2) and db.credit_notes.count_documents({}) == 3
    # recarga exacta (mismo sha) es no-op
    assert import_workbook(b, db, expected_month="2026-03").noop


def test_r02_numeric_representation_does_not_change_identity(xlsx, db):
    import_workbook(xlsx("marzo.xlsx", [sale(1, PRECIO=5, TOTAL_LINEA=10, CANTIDAD=2)]), db)
    other = write_xlsx(folder(xlsx) / "m2.xlsx", [sale(1, PRECIO=5.0, TOTAL_LINEA=10.00, CANTIDAD=2.0)],
                       title_row=False)
    r = import_workbook(other, db, expected_month="2026-03")
    assert r.insertadas == 0 and db.sales.count_documents({}) == 1


def test_r02_date_with_other_time_same_day_keeps_identity(xlsx, db):
    import_workbook(xlsx("marzo.xlsx", [sale(1, FECHA=datetime(2026, 3, 2, 0, 0))]), db)
    other = write_xlsx(folder(xlsx) / "m2.xlsx", [sale(1, FECHA=datetime(2026, 3, 2, 13, 30))],
                       title_row=False)
    assert import_workbook(other, db, expected_month="2026-03").insertadas == 0


def test_r02_legacy_schema_database_is_refused_without_changes(xlsx, db):
    db.sales.insert_one({"linea_id": "old", "schema_version": 1})
    with pytest.raises(IncompatibleSchemaError):
        import_workbook(xlsx("marzo.xlsx", [sale(1)]), db)
    assert db.sales.count_documents({}) == 1 and db.imports.count_documents({}) == 0


# ------------------------------------------------------------------ R03
def test_r03_overlapping_files_reconcile_per_import_and_logically(xlsx, db):
    import_workbook(xlsx("marzo.xlsx", [sale(1), nc("NC-1", -5.5)]), db)
    b = write_xlsx(folder(xlsx) / "marzo_b.xlsx", [sale(1), nc("NC-1", -5.5), nc("NC-2", -3.0)],
                   title_row=False)
    import_workbook(b, db, expected_month="2026-03")
    m = reconcile(db)["2026-03"]
    assert len(m["importaciones"]) == 2
    assert sum(i["filas_leidas"] for i in m["importaciones"]) == 5      # entradas repetidas
    assert (m["ventas"], m["notas_credito"]) == (1, 2)                  # entidades unicas
    assert m["cuadra_importaciones"] and m["cuadra_conjunto_logico"]
    assert all(i["cuadra_lectura"] and i["cuadra_escritura"] and i["cuadra_persistencia"]
               for i in m["importaciones"])
    assert "cuadra_filas" not in m and m["cargas_no_completadas"] == []


def test_r03_reconcile_after_failed_load_and_retry(xlsx, db, monkeypatch):
    p = xlsx("marzo.xlsx", [sale(i) for i in range(1, 6)])
    real = importer._bulk

    def flaky(coll, docs, bs):
        real(coll, docs[:2], bs)
        raise RuntimeError("caida")
    monkeypatch.setattr(importer, "_bulk", flaky)
    with pytest.raises(RuntimeError):
        import_workbook(p, db)
    m = reconcile(db)["2026-03"]
    assert m["importaciones"] == [] and m["cargas_no_completadas"][0]["estado"] == "failed"
    assert not m["cuadra_conjunto_logico"]   # la carga fallida no se presenta como conciliada
    monkeypatch.setattr(importer, "_bulk", real)
    import_workbook(p, db)
    m = reconcile(db)["2026-03"]
    assert m["cargas_no_completadas"] == [] and m["cuadra_importaciones"] and m["cuadra_conjunto_logico"]
    assert m["ventas"] == 5


def test_r03_conflicts_are_counted_and_reconcile_stays_consistent(xlsx, db):
    import_workbook(xlsx("marzo.xlsx", [nc("NC-1", -5.5)]), db)
    other = write_xlsx(folder(xlsx) / "c.xlsx", [nc("NC-1", -9.0), nc("NC-3", -1.0)], title_row=False)
    import_workbook(other, db, expected_month="2026-03")
    m = reconcile(db)["2026-03"]
    conf = next(i for i in m["importaciones"] if i["en_conflicto"])
    assert conf["estado"] == "completed_with_conflicts" and conf["lineas_utiles"] == 1
    assert m["notas_credito"] == 2 and m["cuadra_importaciones"] and m["cuadra_conjunto_logico"]
