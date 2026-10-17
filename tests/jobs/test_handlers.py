"""T10 §4: handlers import_excel y generate_run ejecutados por el worker, en bases temporales df_test_<uuid>."""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from pymongo.errors import ConnectionFailure

from pipeline.data import importer
from pipeline.data.sources import approved_sources, evaluate_sources
from pipeline.jobs import queue
from pipeline.jobs.handlers import JobFailure, classify, safe_message
from pipeline.jobs.keys import import_key
from tests.data.conftest import make_row, write_xlsx
from tests.generate.helpers import build_months, patch_reference
from tests.jobs.jobs_support import (
    enqueue_generate,
    enqueue_import,
    month_rows,
    put_bytes,
    run_job,
    store_upload,
)
from tests.publish.helpers import temp_db

pytestmark = pytest.mark.mongo


@pytest.fixture
def env(tmp_path):
    uploads = tmp_path / "uploads"
    with temp_db() as db:
        yield db, uploads, tmp_path


def snapshot(db) -> dict:
    return {"sales": db.sales.count_documents({}), "credit": db.credit_notes.count_documents({}),
            "imports": db.imports.count_documents({}), "rejects": db.import_rejects.count_documents({}),
            "conflicts": db.import_conflicts.count_documents({}),
            "ids": sorted(d["linea_id"] for d in db.sales.find({}, {"linea_id": 1}))}


# ------------------------------------------------------------------ import_excel
def test_import_valid_workbook_separates_sales_and_credit_notes_and_reports_real_counts(env):
    db, uploads, tmp = env
    sha, size = store_upload(uploads, tmp, month_rows(3))
    job = enqueue_import(db, sha, size, "2026-03")
    done = run_job(db, uploads)
    assert done["job_id"] == job["job_id"] and done["status"] == "completed" and done["attempts"] == 1
    r = done["result"]
    assert r["outcome"] == "importado" and r["estado"] == "completed" and r["mes"] == "2026-03"
    assert (r["filas_leidas"], r["ventas"], r["notas_credito"], r["rechazadas"]) == (13, 10, 2, 1)
    assert r["rechazos_por_motivo"] == {"MONEDA_NO_PEN": 1}
    assert (r["insertadas"], r["ya_existentes"], r["en_conflicto"]) == (12, 0, 0)
    assert db.sales.count_documents({}) == 10 and db.credit_notes.count_documents({}) == 2
    assert db.sales.count_documents({"tipo_doc": 7}) == 0              # notas de credito separadas de la venta bruta
    assert done["progress"]["filas_leidas"] == 13                       # conteos reales, no porcentajes inventados
    assert sha in approved_sources(db) and evaluate_sources(db, date(2026, 3, 31), required_months=("2026-03",)).ok
    assert done["error"] is None and "owner" in done and str(tmp) not in str(queue.public_job(done))


def test_duplicate_import_is_sin_cambios_and_touches_nothing(env):
    db, uploads, tmp = env
    sha, size = store_upload(uploads, tmp, month_rows(3))
    enqueue_import(db, sha, size, "2026-03")
    first = run_job(db, uploads)
    before = snapshot(db)
    enqueue_import(db, sha, size, "2026-03", key="import:reenvio-manual")        # otra clave: reenvio del mismo archivo
    second = run_job(db, uploads)
    assert second["status"] == "completed" and second["result"]["outcome"] == "sin_cambios"
    assert second["result"]["import_id"] == first["result"]["import_id"]
    assert (second["result"]["ventas"], second["result"]["notas_credito"]) == (10, 2)
    assert second["result"]["insertadas"] == 0
    assert snapshot(db) == before                                         # ni siquiera un registro de no-op en imports


def test_conflicting_file_for_month_with_approved_source_is_rejected_without_touching_anything(env):
    db, uploads, tmp = env
    sha_a, size_a = store_upload(uploads, tmp, month_rows(5, seed=1))
    enqueue_import(db, sha_a, size_a, "2026-05")
    assert run_job(db, uploads)["status"] == "completed"
    before = snapshot(db)
    sha_b, size_b = store_upload(uploads, tmp, month_rows(5, n_sales=12, seed=2), "otro.xlsx")
    assert sha_b != sha_a
    enqueue_import(db, sha_b, size_b, "2026-05")
    done = run_job(db, uploads)
    assert done["status"] == "failed" and done["attempts"] == 1            # permanente: sin reintentos
    err = done["error"]
    assert err["code"] == "MES_CON_FUENTE_APROBADA" and err["retryable"] is False
    assert "REMEDIACION_FUENTES.md" in err["message"] and len(err["message"]) <= 300
    assert snapshot(db) == before
    assert sha_b not in approved_sources(db) and db.imports.count_documents({"sha256": sha_b}) == 0
    assert (uploads / f"{sha_b}.xlsx").is_file()                           # el archivo queda en cuarentena
    assert queue.public_job(done)["error"]["code"] == "MES_CON_FUENTE_APROBADA"


def test_august_or_out_of_scope_dates_are_rejected_before_any_write(env):
    db, uploads, tmp = env
    rows = month_rows(3, n_sales=250, n_credit=0, bad_currency=0)
    rows.append(make_row(ID_PEDIDO=99999, SERIE_NUMERO="B-AGO", FECHA=datetime(2026, 8, 3)))   # tras las 200 primeras
    sha, size = store_upload(uploads, tmp, rows)
    enqueue_import(db, sha, size, "2026-03")
    done = run_job(db, uploads)
    assert done["status"] == "failed" and done["error"]["code"] == "FECHAS_FUERA_DE_ALCANCE"
    assert done["error"]["retryable"] is False and "2026-08-03" in done["error"]["message"]
    assert (db.sales.count_documents({}), db.credit_notes.count_documents({}), db.imports.count_documents({}),
            db.import_rejects.count_documents({})) == (0, 0, 0, 0)
    # archivo entero de agosto, y archivo con otro mes que el declarado
    aug, size2 = store_upload(uploads, tmp, [make_row(ID_PEDIDO=5, SERIE_NUMERO="A1", FECHA=datetime(2026, 8, 2))], "a.xlsx")
    enqueue_import(db, aug, size2, "2026-07")
    assert run_job(db, uploads)["error"]["code"] == "FECHAS_FUERA_DE_ALCANCE"
    other, size3 = store_upload(uploads, tmp, month_rows(4), "b.xlsx")
    enqueue_import(db, other, size3, "2026-03")
    assert run_job(db, uploads)["error"]["code"] == "MES_NO_COINCIDE"
    assert db.sales.count_documents({}) == 0 and db.imports.count_documents({}) == 0


def test_corrupt_truncated_tampered_and_misplaced_files_fail_permanently(env):
    db, uploads, tmp = env
    good = Path(write_xlsx(tmp / "ok.xlsx", month_rows(3))).read_bytes()
    cases = {
        "truncado": put_bytes(uploads, good[: len(good) // 2]),
        "no_zip": put_bytes(uploads, b"esto no es un libro de excel" * 20),
    }
    codes = {}
    for name, (sha, size) in cases.items():
        enqueue_import(db, sha, size, "2026-03")
        done = run_job(db, uploads)
        codes[name] = (done["status"], done["error"]["code"], done["error"]["retryable"], done["attempts"])
    assert codes == {"truncado": ("failed", "ARCHIVO_INVALIDO", False, 1), "no_zip": ("failed", "ARCHIVO_INVALIDO", False, 1)}
    # contenido alterado despues de la subida: el nombre ya no corresponde al sha256
    sha, size = put_bytes(uploads, good)
    (uploads / f"{sha}.xlsx").write_bytes(good + b"alterado")
    enqueue_import(db, sha, size, "2026-03")
    assert run_job(db, uploads)["error"]["code"] == "ARCHIVO_ALTERADO"
    # rutas fuera del directorio privado, nombre distinto del sha, archivo inexistente
    for bad in ("../fuera.xlsx", "..\\fuera.xlsx", "sub/" + sha + ".xlsx", "otro.xlsx", f"{'0' * 64}.xlsx"):
        enqueue_import(db, sha, size, "2026-03", key=f"import:{bad}", upload_path=bad)
        done = run_job(db, uploads)
        assert done["status"] == "failed" and done["error"]["code"] == "ARCHIVO_NO_DISPONIBLE", bad
    assert db.sales.count_documents({}) == 0 and db.imports.count_documents({}) == 0


def test_transient_failure_retries_without_duplicating_and_then_completes(env, monkeypatch):
    db, uploads, tmp = env
    sha, size = store_upload(uploads, tmp, month_rows(6, n_sales=14))
    enqueue_import(db, sha, size, "2026-06")
    original = importer._write_batches

    def flaky(database, sales, notes, rejects, batch_size):
        importer._bulk(database.sales, sales[:5], batch_size)               # escritura parcial y caida de la base
        raise ConnectionFailure("simulado")

    monkeypatch.setattr(importer, "_write_batches", flaky)
    first = run_job(db, uploads)
    assert first["status"] == "queued" and first["error"]["retryable"] is True
    assert first["error"]["code"] == "BASE_DE_DATOS_NO_DISPONIBLE" and first["attempts"] == 1
    assert 0 < db.sales.count_documents({}) < 14
    assert sha not in approved_sources(db)                                    # la carga parcial NO esta aprobada
    monkeypatch.setattr(importer, "_write_batches", original)
    second = run_job(db, uploads)
    assert second["status"] == "completed" and second["attempts"] == 2 and second["result"]["outcome"] == "importado"
    assert db.sales.count_documents({}) == 14 and len(db.sales.distinct("linea_id")) == 14
    assert (second["result"]["insertadas"], second["result"]["ya_existentes"]) == (11, 5)   # 5 ya estaban: sin duplicar
    assert sha in approved_sources(db) and evaluate_sources(db, date(2026, 6, 30), required_months=("2026-06",)).ok
    assert db.imports.count_documents({"sha256": sha, "estado": "failed"}) == 1       # la traza del fallo se conserva


def test_classification_distinguishes_transient_from_permanent_and_sanitizes_messages():
    assert classify(ConnectionFailure("down"))[2] is True
    assert classify(JobFailure("DATOS", "x"))[2] is False
    assert classify(importer.ImportWriteError("error de escritura"))[2] is False
    code, msg, retry = classify(RuntimeError("fallo en C:\\Users\\rogel\\private\\a.xlsx mongodb://u:clave@h/db"))
    assert code == "ERROR_INTERNO" and retry is False and "rogel" not in msg and "clave" not in msg
    cleaned = safe_message("no se lee C:\\Users\\rogel\\x.xlsx y /home/u/datos/a.xlsx; vence 31/07/2026 mongodb://u:p@h")
    assert "rogel" not in cleaned and "/home/u" not in cleaned and "u:p@h" not in cleaned and "31/07/2026" in cleaned


# ------------------------------------------------------------------ generate_run
def test_generate_run_job_publishes_once_and_a_second_request_is_sin_cambios(env, monkeypatch):
    db, uploads, tmp = env
    patch_reference(monkeypatch)
    build_months(db, tmp)
    first_job = enqueue_generate(db, date(2026, 6, 20))
    done = run_job(db, uploads)
    assert done["status"] == "completed" and done["result"]["outcome"] == "generada"
    run_id = done["result"]["run_id"]
    assert run_id.startswith("gen-20260620-") and done["result"]["comparator_available"] is False
    assert done["stage"] == "completado" and done["progress"]["forecasts_sku"] == done["result"]["counts"]["forecasts_sku"]
    assert db.runs.count_documents({"status": "completed"}) == 1
    again = enqueue_generate(db, date(2026, 6, 20), header="reintento-admin")      # clave distinta: mismo calculo
    assert again["job_id"] != first_job["job_id"]
    second = run_job(db, uploads)
    assert second["result"]["outcome"] == "sin_cambios" and second["result"]["run_id"] == run_id
    assert db.runs.count_documents({}) == 1


def test_generate_run_with_out_of_policy_or_unapproved_input_fails_permanently(env):
    db, uploads, _tmp = env
    queue.ensure_indexes(db)
    t0 = datetime.now(UTC) - timedelta(minutes=5)          # created_at distintos: el orden de reclamo es determinista
    for i, (key, inp) in enumerate([
            ("g-ago", {"origin": "2026-08-01", "horizon_days": 21, "method": "promedio_28"}),
            ("g-sin", {"origin": "2026-06-20", "horizon_days": 21, "method": "promedio_28"}),
            ("g-mal", {"origin": "no-fecha"})]):
        queue.enqueue(db, "generate_run", inp, key, "admin", now=t0 + timedelta(seconds=i))
    codes = [run_job(db, uploads)["error"] for _ in range(3)]
    assert [(e["code"], e["retryable"]) for e in codes] == [("CORTE_FUERA_DE_RANGO", False),
                                                             ("FUENTES_NO_APROBADAS", False),
                                                             ("ENTRADA_INVALIDA", False)]
    assert db.runs.count_documents({}) == 0 and import_key("a") == "import:a"
