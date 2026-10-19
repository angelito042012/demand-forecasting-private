"""Paquete REAL datos_preparados_v1 (14 libros, 106 525 registros). Lento (~30 s de verificacion). Activar con RUN_REALDATA=1."""
from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

import pytest

from pipeline.plan.dataset import COLLECTIONS, HEADER_COLL, ImportRejected, prepare, run
from tests.plan.conftest import edit_csv

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "artifacts" / "private" / "datos_preparados_v1"
AUDIT = ROOT / "artifacts" / "private" / "auditoria_14_excel" / "audit.json"

pytestmark = [
    pytest.mark.mongo, pytest.mark.realdata,
    pytest.mark.skipif(not (PKG / "manifest.json").is_file() or os.environ.get("RUN_REALDATA") != "1",
                       reason="requiere el paquete real y RUN_REALDATA=1"),
]


@pytest.fixture(scope="module")
def real():
    t0 = time.perf_counter()
    prep = prepare(PKG, AUDIT if AUDIT.is_file() else None)
    prep.header["_seconds"] = round(time.perf_counter() - t0, 1)
    return prep


def test_real_package_verifies_exactly(real):
    h = real.header
    print(f"verificacion real: {h['_seconds']} s")
    assert h["source_rows"] == 106525
    assert h["counts"] == {"VENTA": 101080, "COMPRA": 3555, "COMPRA_SIN_CARGO_REGISTRADO": 1224, "CREDITO": 664, "CUARENTENA": 2}
    assert {k: len(v) for k, v in real.docs.items()} == {"plan_sales": 101080, "plan_purchases": 4779, "plan_credits": 664, "plan_quarantine": 2}
    assert h["sales_cutoff"] == "2026-09-30" and h["window_start"] == "2026-03-01"
    assert h["repeated_extra_rows_marked"] == 6
    assert len(h["sources"]) == 14 and h["group"]["size"] == 50 and h["currencies"]


def test_real_import_into_temp_db(real):
    from tests.publish.helpers import temp_db
    with temp_db() as db:
        r = run(PKG, db, AUDIT if AUDIT.is_file() else None)
        assert r["action"] == "created" and r["sales_cutoff"] == "2026-09-30"
        assert {c: db[c].count_documents({}) for c in COLLECTIONS.values()} == {
            "plan_sales": 101080, "plan_purchases": 4779, "plan_credits": 664, "plan_quarantine": 2}
        h = db[HEADER_COLL].find_one({})
        assert h["status"] == "current" and h["dataset_id"] == real.header["dataset_id"] and h["source_rows"] == 106525
        assert db.plan_purchases.count_documents({"clase": "COMPRA_SIN_CARGO_REGISTRADO"}) == 1224
        assert db.plan_purchases.count_documents({"ocurrencia": {"$gt": 1}}) == h["repeated_extra_rows_marked"]
        assert run(PKG, db, AUDIT if AUDIT.is_file() else None)["action"] == "unchanged"


def test_real_coherent_manipulation_rejected(tmp_path):
    copy = tmp_path / "pkg"
    (copy / "00_originales").parent.mkdir(parents=True)
    shutil.copytree(PKG / "00_originales", copy / "00_originales")
    shutil.copytree(PKG / "01_normalizados", copy / "01_normalizados")
    shutil.copytree(PKG / "02_grupo", copy / "02_grupo")
    shutil.copy2(PKG / "manifest.json", copy / "manifest.json")

    def tamper(rows):
        r = next(x for x in rows if x["producto_id"] == rows[100]["producto_id"])
        r["cantidad"] = str(int(float(r["cantidad"])) * 10 + 10)
        r["importe"] = str(round(float(r["importe"]) * 10, 2) + 10)

    edit_csv(copy, "ventas.csv", tamper)
    with pytest.raises(ImportRejected) as e:
        prepare(copy, AUDIT if AUDIT.is_file() else None)
    assert e.value.code == "DERIVADO_NO_COINCIDE"
