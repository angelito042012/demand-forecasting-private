"""R04: solo fuentes completas/aprobadas llegan a entrenamiento y catalogo."""
from datetime import date, datetime

import pytest

import pipeline.data.importer as imp
from pipeline.data.catalog import build_category_catalog
from pipeline.data.importer import import_workbook
from pipeline.data.reconcile import reconcile
from pipeline.data.sources import SourceApprovalError, approved_filter, evaluate_sources
from pipeline.data.training_access import load_fold, load_training_data

from .conftest import make_row

pytestmark = pytest.mark.mongo
RM = ("2026-07",)   # estas bases sinteticas solo traen un mes: se declara explicito


def s(n, day, month=7, sku=100, cat="CAT A", qty=2, **kw):
    return make_row(ID_PEDIDO=n, SERIE_NUMERO=f"B{n}", ID_ARTICULO=sku, GRUPO=cat,
                    FECHA=datetime(2026, month, day), CANTIDAD=qty, CANTIDAD_UM_BASE=qty,
                    TOTAL_LINEA=qty * 5.5, **kw)


def _fail_after_first(monkeypatch):
    """Simula un error tras insertar la primera venta (carga parcial). Devuelve la funcion real."""
    real = imp._write_batches

    def partial(db, sales, notes, rejects, batch_size):
        real(db, sales[:1], [], [], batch_size)
        raise RuntimeError("fallo simulado tras escritura parcial")
    monkeypatch.setattr(imp, "_write_batches", partial)
    return real


def test_partial_failed_load_is_blocked_not_trained(xlsx, db, monkeypatch):
    _fail_after_first(monkeypatch)
    with pytest.raises(RuntimeError):
        import_workbook(xlsx("julio.xlsx", [s(1, 3), s(2, 4)]), db)
    assert db.sales.count_documents({}) == 1 and db.imports.find_one()["estado"] == "failed"
    with pytest.raises(SourceApprovalError) as exc:
        load_training_data(db, date(2026, 7, 31), required_months=RM)
    codes = {i["codigo"] for i in exc.value.issues}
    assert {"MES_SIN_FUENTE_APROBADA", "CARGA_NO_COMPLETADA", "LINEAS_SIN_FUENTE_APROBADA"} <= codes


def test_complete_retry_unblocks_and_rows_are_used_once(xlsx, db, monkeypatch):
    path = xlsx("julio.xlsx", [s(1, 3), s(2, 4)])
    real = _fail_after_first(monkeypatch)
    with pytest.raises(RuntimeError):
        import_workbook(path, db)
    monkeypatch.setattr(imp, "_write_batches", real)
    rep = import_workbook(path, db)
    assert rep.estado == "completed" and rep.ya_existentes == 1 and rep.insertadas == 1
    data = load_training_data(db, date(2026, 7, 31), required_months=RM)
    assert [r["fecha"] for r in data.sales] == ["2026-07-03", "2026-07-04"]
    assert len({r["linea_id"] for r in data.sales}) == len(data.sales) == 2
    assert data.sources.ok and len(data.sources.manifest) == 1


def test_open_conflict_blocks_only_when_relevant_to_the_cutoff(xlsx, db):
    import_workbook(xlsx("julio.xlsx", [s(1, 3)]), db)
    jul = db.imports.find_one({"archivo": "julio.xlsx"})["sha256"]
    db.import_conflicts.insert_one({"conflict_id": "c1", "coleccion": "sales", "estado": "OPEN",
                                    "source_sha256": "otra", "lineas_nuevas": [{"fecha": "2026-07-03"}]})
    with pytest.raises(SourceApprovalError) as exc:
        load_training_data(db, date(2026, 7, 31), required_months=RM)
    assert "CONFLICTO_ABIERTO" in {i["codigo"] for i in exc.value.issues}
    db.import_conflicts.update_one({"conflict_id": "c1"}, {"$set": {"lineas_nuevas": [{"fecha": "2026-07-20"}]}})
    assert load_training_data(db, date(2026, 7, 10), required_months=RM).sales   # posterior al corte
    # un conflicto abierto de la propia fuente la desaprueba
    db.import_conflicts.update_one({"conflict_id": "c1"}, {"$set": {"source_sha256": jul}})
    with pytest.raises(SourceApprovalError):
        load_training_data(db, date(2026, 7, 10), required_months=RM)


def test_load_with_conflicts_is_not_approved(xlsx, db):
    import_workbook(xlsx("julio.xlsx", [s(1, 3)]), db)
    r = import_workbook(xlsx("julio_b.xlsx", [s(1, 3), s(1, 5, sku=101)]), db, expected_month="2026-07")
    assert r.estado == "completed_with_conflicts"
    with pytest.raises(SourceApprovalError) as exc:
        load_training_data(db, date(2026, 7, 31), required_months=RM)
    assert {"CARGA_NO_COMPLETADA", "CONFLICTO_ABIERTO"} <= {i["codigo"] for i in exc.value.issues}


def test_rows_with_invalid_or_missing_provenance_are_rejected(xlsx, db):
    import_workbook(xlsx("julio.xlsx", [s(1, 3)]), db)
    base = {"fecha": "2026-07-05", "sku": "9", "cantidad_base": 1, "importe": None,
            "categoria_original": "X", "almacen": "1"}
    db.sales.insert_one({**base, "linea_id": "ghost1", "sources": [{"source_sha256": "desconocida"}]})
    db.sales.insert_one({**base, "linea_id": "ghost2"})
    rep = evaluate_sources(db, date(2026, 7, 31), required_months=RM)
    issue = next(i for i in rep.issues if i["codigo"] == "LINEAS_SIN_FUENTE_APROBADA")
    assert issue["n"] == 2
    with pytest.raises(SourceApprovalError):
        load_training_data(db, date(2026, 7, 31), required_months=RM)


def test_catalog_obeys_same_source_selection(xlsx, db):
    import_workbook(xlsx("julio.xlsx", [s(1, 3, cat="CAT A")]), db)
    db.sales.insert_one({"linea_id": "g", "fecha": "2026-07-20", "sku": "100", "cantidad_base": 1,
                         "importe": None, "categoria_original": "FANTASMA", "almacen": "1", "sources": []})
    rep = evaluate_sources(db, date(2026, 7, 31), required_months=RM)
    assert build_category_catalog(db, "2026-07-31")["100"] == "FANTASMA"          # sin filtro
    assert build_category_catalog(db, "2026-07-31", source_filter=approved_filter(rep))["100"] == "CAT A"


def test_required_months_missing_are_reported_by_default_march_to_cutoff(xlsx, db):
    import_workbook(xlsx("julio.xlsx", [s(1, 3)]), db)
    with pytest.raises(SourceApprovalError) as exc:
        load_training_data(db, date(2026, 7, 31))     # por defecto exige 2026-03..2026-07
    missing = [i["mes"] for i in exc.value.issues if i["codigo"] == "MES_SIN_FUENTE_APROBADA"]
    assert missing == ["2026-03", "2026-04", "2026-05", "2026-06"]


def test_empty_database_is_never_approved(db):
    with pytest.raises(SourceApprovalError):
        load_training_data(db, date(2026, 7, 31), required_months=RM)
    with pytest.raises(SourceApprovalError):
        load_training_data(db, date(2026, 7, 31), required_months=())
    assert reconcile(db) == {}


def test_reconcile_not_approved_without_import_records(xlsx, db):
    import_workbook(xlsx("julio.xlsx", [s(1, 3)]), db)
    db.imports.delete_many({})                            # ventas sin importaciones registradas
    assert reconcile(db)["2026-07"]["cuadra_importaciones"] is False


def test_failed_post_cutoff_load_does_not_change_approved_dataset(xlsx, db, monkeypatch):
    import_workbook(xlsx("julio.xlsx", [s(1, 3), s(2, 20)]), db)
    before = load_training_data(db, date(2026, 7, 10), required_months=RM)
    _fail_after_first(monkeypatch)
    with pytest.raises(RuntimeError):
        import_workbook(xlsx("agosto.xlsx", [s(7, 2, 8), s(8, 3, 8)]), db)   # carga fallida de agosto
    after = load_training_data(db, date(2026, 7, 10), required_months=RM)
    assert after.sales == before.sales and after.fingerprint == before.fingerprint
    f = load_fold(db, date(2026, 7, 10), date(2026, 7, 25), required_months=RM)
    assert [r["fecha"] for r in f.validation_sales] == ["2026-07-20"]


def test_august_never_in_training_even_with_approved_source(xlsx, db):
    import_workbook(xlsx("julio.xlsx", [s(1, 3)]), db)
    import_workbook(xlsx("agosto.xlsx", [s(2, 2, 8)]), db)
    data = load_training_data(db, date(2026, 7, 31), required_months=RM)
    assert all(r["fecha"] <= "2026-07-31" for r in data.sales)
    assert data.sources.manifest[-1]["mes"] == "2026-07"
