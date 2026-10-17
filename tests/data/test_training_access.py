"""Barrera de acceso a entrenamiento por corte temporal (A03 a nivel de datos)."""
from datetime import date, datetime

import pytest

from pipeline.data.calendar import EXCLUDED_DATES
from pipeline.data.importer import import_workbook
from pipeline.data.training_access import (
    TrainingCutoffError,
    load_final_test_sales,
    load_fold,
    load_training_data,
)

from .conftest import make_row, write_xlsx

RM_JUL = ("2026-07",)   # estas bases sinteticas solo traen un mes: se declara explicito
RM_APR = ("2026-04",)

pytestmark = pytest.mark.mongo


def s(n, day, month=7, sku=100, cat="CAT A", qty=2, **kw):
    return make_row(ID_PEDIDO=n, SERIE_NUMERO=f"B{n}", ID_ARTICULO=sku, GRUPO=cat,
                    FECHA=datetime(2026, month, day), CANTIDAD=qty, CANTIDAD_UM_BASE=qty,
                    TOTAL_LINEA=qty * 5.5, **kw)


@pytest.fixture
def loaded(xlsx, db):
    import_workbook(xlsx("julio.xlsx", [s(1, 3), s(2, 10, sku=101), s(3, 20), s(4, 31, cat="CAT B")]), db)
    import_workbook(write_xlsx(xlsx("_d.xlsx", []).parent / "agosto.xlsx",
                               [s(5, 2, 8, cat="CAT C"), s(6, 15, 8, sku=999)]), db)
    return db


def test_august_and_later_cutoffs_are_rejected(loaded):
    for bad in (date(2026, 8, 1), date(2026, 8, 31), date(2026, 9, 30), "2026-08-15"):
        with pytest.raises(TrainingCutoffError):
            load_training_data(loaded, bad, required_months=RM_JUL)


def test_training_data_never_contains_rows_after_cutoff(loaded):
    data = load_training_data(loaded, date(2026, 7, 31), required_months=RM_JUL)
    assert {r["fecha"] for r in data.sales} <= {"2026-07-03", "2026-07-10", "2026-07-20", "2026-07-31"}
    assert all(r["sku"] != "999" for r in data.sales)       # SKU nuevo de agosto no entra
    fold = load_training_data(loaded, date(2026, 7, 10), required_months=RM_JUL)
    assert [r["fecha"] for r in fold.sales] == ["2026-07-03", "2026-07-10"]
    assert fold.cutoff == date(2026, 7, 10) and fold.calendar[-1] == date(2026, 7, 10)


def test_changes_after_cutoff_do_not_change_dataset_catalog_or_fingerprint(loaded):
    cutoff = date(2026, 7, 10)
    before = load_training_data(loaded, cutoff, required_months=RM_JUL)
    # modifica y agrega registros posteriores al corte, incluso agosto y la categoria del mismo SKU
    loaded.sales.update_many({"fecha": {"$gt": "2026-07-10"}}, {"$set": {"categoria_original": "OTRA",
                                                                       "cantidad_base": 999}})
    jul_sha = loaded.imports.find_one({"archivo": "julio.xlsx"})["sha256"]
    loaded.sales.insert_one({"linea_id": "late", "fecha": "2026-07-25", "sku": "100", "cantidad_base": 50,
                             "importe": None, "categoria_original": "ZZZ", "almacen": "1",
                             "sources": [{"source_sha256": jul_sha}]})
    loaded.sales.delete_many({"fecha": "2026-08-15"})
    after = load_training_data(loaded, cutoff, required_months=RM_JUL)
    assert after.sales == before.sales
    assert after.catalog == before.catalog and after.fingerprint == before.fingerprint
    assert after.calendar == before.calendar
    # y un corte posterior si cambia (la prueba no es vacua)
    assert load_training_data(loaded, date(2026, 7, 31), required_months=RM_JUL).fingerprint != after.fingerprint


def test_catalog_uses_only_training_cut(loaded):
    # SKU 100: CAT A (3 y 20 jul), CAT B (31 jul), CAT C (agosto)
    assert load_training_data(loaded, date(2026, 7, 20), required_months=RM_JUL).catalog["100"] == "CAT A"
    assert load_training_data(loaded, date(2026, 7, 31), required_months=RM_JUL).catalog["100"] == "CAT B"
    assert "999" not in load_training_data(loaded, date(2026, 7, 31), required_months=RM_JUL).catalog


def test_excluded_days_masked_without_compressing_calendar(xlsx, db):
    rows = [s(1, 1, 4), s(2, 4, 4), s(3, 13, 4)]
    import_workbook(xlsx("abril.xlsx", rows), db)
    d = load_training_data(db, date(2026, 4, 15), required_months=RM_APR)
    assert d.excluded_days == frozenset({date(2026, 4, 3), date(2026, 4, 12)})
    assert len(d.calendar) == 15                       # dias naturales, sin comprimir
    assert len(d.training_days) == 13
    assert all(r["cantidad_base"] > 0 for r in d.sales)  # ningun cero fabricado


def test_rows_dated_on_excluded_days_are_omitted_from_training(xlsx, db):
    import_workbook(xlsx("abril.xlsx", [s(1, 1, 4), s(2, 3, 4)]), db)
    d = load_training_data(db, date(2026, 4, 15), required_months=RM_APR)
    assert [r["fecha"] for r in d.sales] == ["2026-04-01"] and d.omitted_excluded_rows == 1
    assert db.sales.count_documents({}) == 2           # la fila sigue en la base, solo se enmascara
    assert date(2026, 4, 3) in EXCLUDED_DATES


def test_fold_validation_window_limits_and_metric_mask(xlsx, db):
    import_workbook(xlsx("abril.xlsx", [s(1, 1, 4), s(2, 5, 4), s(3, 20, 4)]), db)
    fold = load_fold(db, date(2026, 4, 2), date(2026, 4, 15), required_months=RM_APR)
    assert [r["fecha"] for r in fold.validation_sales] == ["2026-04-05"]
    assert date(2026, 4, 12) in fold.validation_excluded_days
    assert date(2026, 4, 12) not in fold.metric_days and len(fold.validation_calendar) == 13
    assert all(r["fecha"] <= "2026-04-02" for r in fold.train.sales)
    with pytest.raises(TrainingCutoffError):
        load_fold(db, date(2026, 4, 2), date(2026, 8, 5), required_months=RM_APR)      # validacion no puede tocar agosto
    with pytest.raises(TrainingCutoffError):
        load_fold(db, date(2026, 4, 2), date(2026, 4, 2), required_months=RM_APR)      # ventana vacia/invertida


def test_final_test_requires_explicit_confirmation(loaded):
    for flag in (False, None, 1, "yes"):
        with pytest.raises(TrainingCutoffError):
            load_final_test_sales(loaded, frozen_selection_confirmed=flag, required_months=RM_JUL)
    aug = load_final_test_sales(loaded, frozen_selection_confirmed=True, required_months=RM_JUL)
    assert [r["fecha"] for r in aug] == ["2026-08-02", "2026-08-15"]
