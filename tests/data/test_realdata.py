"""Integracion con los seis Excel reales (solo lectura). Activar con RUN_REALDATA=1."""
import hashlib
import os
from pathlib import Path

import pytest

from pipeline.data.importer import SIX_FILES, import_folder
from pipeline.data.reconcile import compare_with_audit, reconcile

SRC = Path(r"C:\Users\rogel\Documents\Datos")

pytestmark = [
    pytest.mark.mongo,
    pytest.mark.realdata,
    pytest.mark.skipif(not SRC.exists() or os.environ.get("RUN_REALDATA") != "1",
                       reason="requiere C:\\Users\\rogel\\Documents\\Datos y RUN_REALDATA=1"),
]


def _hashes():
    return {n: hashlib.sha256((SRC / f"{n}.xlsx").read_bytes()).hexdigest() for n in SIX_FILES}


def test_real_six_files_load_and_reload(db):
    before = _hashes()
    r1 = import_folder(SRC, db)
    assert [r.estado for r in r1] == ["completed"] * 6
    n_sales, n_notes = db.sales.count_documents({}), db.credit_notes.count_documents({})
    assert n_sales == sum(r.ventas_aceptadas for r in r1)
    assert n_notes == sum(r.notas_credito for r in r1)
    r2 = import_folder(SRC, db)
    assert all(r.insertadas == 0 for r in r2)
    assert db.sales.count_documents({}) == n_sales and db.credit_notes.count_documents({}) == n_notes
    assert db.sales.count_documents({}) == len(db.sales.distinct("linea_id"))
    assert not compare_with_audit(reconcile(db)), compare_with_audit(reconcile(db))
    assert _hashes() == before


EXPECTED_SUMS = {  # importes de ventas / creditos por mes, ya conciliados con los Excel (control de importacion)
    "2026-03": ("426456.21", "-3128.00"), "2026-04": ("429609.99", "-2927.50"),
    "2026-05": ("500621.72", "-2769.38"), "2026-06": ("390855.08", "-9680.60"),
    "2026-07": ("453143.28", "-4548.76"), "2026-08": ("422736.88", "-3799.90"),
}


def test_real_reconciliation_conflicts_and_training_barrier(db):
    from datetime import date

    from pipeline.data.training_access import TrainingCutoffError, load_training_data

    import_folder(SRC, db)
    import_folder(SRC, db)  # recarga
    assert db.import_conflicts.count_documents({}) == 0 and db.import_rejects.count_documents({}) == 0
    result = reconcile(db)
    for month, (sales_sum, credit_sum) in EXPECTED_SUMS.items():
        m = result[month]
        assert m["suma_importe_ventas"] == sales_sum and m["suma_importe_creditos"] == credit_sum
        assert m["cuadra_importaciones"] and m["cuadra_conjunto_logico"] and len(m["importaciones"]) == 1
    data = load_training_data(db, date(2026, 7, 31))
    assert len(data.sales) == 14456 + 13907 + 15380 + 12510 + 15678      # sin agosto
    assert max(r["fecha"] for r in data.sales) <= "2026-07-31"
    assert data.catalog["16140041"] == "MAQUILLAJE PARA ROSTRO"
    assert data.excluded_days == frozenset({date(2026, 4, 3), date(2026, 4, 12), date(2026, 6, 7)})
    with pytest.raises(TrainingCutoffError):
        load_training_data(db, date(2026, 8, 31))
