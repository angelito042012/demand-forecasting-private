"""T10R R09: una sola fuente aprobada por mes aunque dos importadores corran a la vez; propiedad y recuperacion.

Bases temporales df_test_<uuid> y libros sinteticos; no se toca demand_forecasting_v2 ni los originales."""
from __future__ import annotations

import threading
from datetime import UTC, date, datetime, timedelta

import pytest
from pymongo.errors import ConnectionFailure

from pipeline.data import importer, month_lock
from pipeline.data.sources import approved_sources, evaluate_sources
from pipeline.jobs import handlers
from pipeline.jobs.keys import import_key
from tests.jobs.jobs_support import enqueue_import, month_rows, run_job, store_upload
from tests.publish.helpers import temp_db

pytestmark = pytest.mark.mongo


@pytest.fixture
def env(tmp_path):
    uploads = tmp_path / "uploads"
    with temp_db() as db:
        yield db, uploads, tmp_path


def rows_by_source(db, sha):
    return db.sales.count_documents({"sources.source_sha256": sha}) + \
        db.credit_notes.count_documents({"sources.source_sha256": sha})


def two_sources_march(uploads, tmp):
    a = store_upload(uploads, tmp, month_rows(3, n_sales=10, n_credit=0, bad_currency=0, seed=1), "a.xlsx")
    b = store_upload(uploads, tmp, month_rows(3, n_sales=10, n_credit=0, bad_currency=0, seed=2), "b.xlsx")
    assert a[0] != b[0]
    return a, b


def test_two_different_sources_for_the_same_month_synchronized_after_the_check_yield_one_winner(env, monkeypatch):
    db, uploads, tmp = env
    (sha_a, size_a), (sha_b, size_b) = two_sources_march(uploads, tmp)
    enqueue_import(db, sha_a, size_a, "2026-03")
    enqueue_import(db, sha_b, size_b, "2026-03")
    gate = threading.Barrier(2, timeout=60)
    real = handlers.approved_sources

    def synced(database):                                 # ambos pasan el chequeo ANTES de que alguno reserve/escriba
        out = real(database)
        gate.wait()
        return out
    monkeypatch.setattr(handlers, "approved_sources", synced)
    done, errs = [], []

    def go(name):
        try:
            done.append(run_job(db, uploads, worker=name))
        except Exception as exc:  # noqa: BLE001
            errs.append(exc)

    ts = [threading.Thread(target=go, args=(f"w{i}",)) for i in range(2)]
    [t.start() for t in ts]
    [t.join(180) for t in ts]
    assert not errs and len(done) == 2
    ok = [j for j in done if j["status"] == "completed"]
    lost = [j for j in done if j["status"] == "failed"]
    assert len(ok) == 1 and len(lost) == 1
    assert lost[0]["error"]["code"] == "MES_CON_FUENTE_APROBADA" and lost[0]["error"]["retryable"] is False
    assert "docs/REMEDIACION_FUENTES.md" in lost[0]["error"]["message"]
    winner = ok[0]["input"]["upload_sha256"]
    loser = lost[0]["input"]["upload_sha256"]
    assert set(approved_sources(db)) == {winner}
    assert rows_by_source(db, loser) == 0 and rows_by_source(db, winner) == 10 and db.sales.count_documents({}) == 10
    assert db.imports.count_documents({"sha256": loser}) == 0                        # el perdedor ni siquiera abre importacion
    assert evaluate_sources(db, date(2026, 3, 31), required_months=("2026-03",)).ok
    assert db.month_reservations.find_one({"_id": "2026-03"})["state"] == "approved"


def test_same_source_retry_is_idempotent_and_a_known_source_is_a_noop(env):
    db, uploads, tmp = env
    (sha_a, size_a), _ = two_sources_march(uploads, tmp)
    enqueue_import(db, sha_a, size_a, "2026-03")
    first = run_job(db, uploads)
    assert first["status"] == "completed" and first["result"]["outcome"] == "importado"
    before = (db.sales.count_documents({}), db.imports.count_documents({}))
    enqueue_import(db, sha_a, size_a, "2026-03", key=import_key(sha_a) + ":otra")
    again = run_job(db, uploads)
    assert again["status"] == "completed" and again["result"]["outcome"] == "sin_cambios"
    assert (db.sales.count_documents({}), db.imports.count_documents({})) == before
    assert db.month_reservations.count_documents({}) == 1


def test_restart_midway_keeps_the_month_reserved_as_partial_and_blocks_another_source(env, monkeypatch):
    db, uploads, tmp = env
    (sha_a, size_a), (sha_b, size_b) = two_sources_march(uploads, tmp)
    enqueue_import(db, sha_a, size_a, "2026-03")
    original = importer._write_batches

    def partial(database, sales, notes, rejects, batch_size):
        importer._bulk(database.sales, sales[:4], batch_size)            # escritura parcial y caida
        raise ConnectionFailure("simulado")
    monkeypatch.setattr(importer, "_write_batches", partial)
    first = run_job(db, uploads)
    assert first["status"] == "queued" and first["error"]["retryable"] is True
    assert db.month_reservations.find_one({"_id": "2026-03"})["state"] == "partial"
    assert 0 < db.sales.count_documents({}) < 10 and sha_a not in approved_sources(db)
    # otra fuente durante la recuperacion: rechazada, sin una sola fila, el mes NO se libera como si estuviera vacio
    db.jobs.update_one({"input.upload_sha256": sha_a}, {"$set": {"available_at": datetime.now(UTC) + timedelta(hours=1)}})
    enqueue_import(db, sha_b, size_b, "2026-03")
    monkeypatch.setattr(importer, "_write_batches", original)
    b = run_job(db, uploads, worker="w-b")
    assert b["input"]["upload_sha256"] == sha_b and b["status"] == "failed"
    assert b["error"]["code"] == "MES_CON_FUENTE_APROBADA" and "parcial" in b["error"]["message"]
    assert rows_by_source(db, sha_b) == 0 and db.imports.count_documents({"sha256": sha_b}) == 0
    assert db.month_reservations.find_one({"_id": "2026-03"})["state"] == "partial"
    # la misma fuente reintenta y completa sin duplicar; el mes queda aprobado para A
    db.jobs.update_one({"input.upload_sha256": sha_a}, {"$set": {"available_at": datetime.now(UTC)}})
    a = run_job(db, uploads, worker="w-a")
    assert a["status"] == "completed" and a["result"]["outcome"] == "importado" and a["result"]["ya_existentes"] > 0
    assert db.sales.count_documents({}) == 10 and set(approved_sources(db)) == {sha_a}
    assert db.month_reservations.find_one({"_id": "2026-03"})["state"] == "approved"


def test_other_source_is_rejected_while_the_month_is_partial_and_same_source_resumes(env):
    db, uploads, tmp = env
    (sha_a, size_a), (sha_b, size_b) = two_sources_march(uploads, tmp)
    resv = month_lock.reserve(db, "2026-03", sha_a)               # A empezo, escribio algo y murio
    month_lock.finish(db, resv, "partial")
    enqueue_import(db, sha_b, size_b, "2026-03")
    b = run_job(db, uploads, worker="w-b")
    assert b["status"] == "failed" and b["error"]["code"] == "MES_CON_FUENTE_APROBADA"
    assert "parcial" in b["error"]["message"] and rows_by_source(db, sha_b) == 0 and db.imports.count_documents({}) == 0
    enqueue_import(db, sha_a, size_a, "2026-03")                  # la misma fuente retoma
    a = run_job(db, uploads, worker="w-a")
    assert a["status"] == "completed" and a["result"]["outcome"] == "importado"
    assert db.month_reservations.find_one({"_id": "2026-03"})["state"] == "approved"
    assert db.month_reservations.find_one({"_id": "2026-03"})["generation"] == 2


def test_failure_before_any_write_releases_the_month_for_another_source(env, monkeypatch):
    db, uploads, tmp = env
    (sha_a, size_a), (sha_b, size_b) = two_sources_march(uploads, tmp)
    enqueue_import(db, sha_a, size_a, "2026-03")
    monkeypatch.setattr(importer, "check_schema",
                        lambda d: (_ for _ in ()).throw(importer.IncompatibleSchemaError("simulado")))
    failed = run_job(db, uploads)
    assert failed["status"] == "failed" and failed["error"]["code"] == "ESQUEMA_INCOMPATIBLE"
    assert db.month_reservations.count_documents({}) == 0         # sin escrituras: el mes sigue vacio y libre
    monkeypatch.undo()
    enqueue_import(db, sha_b, size_b, "2026-03")
    assert run_job(db, uploads)["status"] == "completed"


def test_late_return_of_a_replaced_owner_cannot_write_or_finalize(env):
    db, uploads, tmp = env
    (sha_a, size_a), _ = two_sources_march(uploads, tmp)
    path = uploads / f"{sha_a}.xlsx"
    old = month_lock.reserve(db, "2026-03", sha_a)
    db.month_reservations.update_one({"_id": "2026-03"}, {"$set": {"lease_expires_at": datetime.now(UTC) - timedelta(seconds=9)}})
    new = month_lock.reserve(db, "2026-03", sha_a)               # el reemplazo (misma fuente) asume
    assert new.generation == 2
    with pytest.raises(month_lock.LostReservation):
        importer.import_workbook(path, db, expected_month="2026-03", fence=month_lock.Fence(db, old))
    assert db.sales.count_documents({}) == 0 and sha_a not in approved_sources(db)
    failed = db.imports.find_one({"sha256": sha_a})
    assert failed["estado"] == "failed" and "LostReservation" in failed["error"]
    # el nuevo dueno si completa
    rep = importer.import_workbook(path, db, expected_month="2026-03", fence=month_lock.Fence(db, new))
    assert rep.estado == "completed" and db.sales.count_documents({}) == 10
    month_lock.finish(db, new, "approved")
    with pytest.raises(month_lock.LostReservation):
        month_lock.finish(db, old, "approved")                    # el obsoleto tampoco puede cerrar la reserva


def test_owner_replaced_in_the_middle_of_the_import_stops_after_the_current_batch(env):
    db, uploads, tmp = env
    (sha_a, size_a), _ = two_sources_march(uploads, tmp)
    path = uploads / f"{sha_a}.xlsx"
    old = month_lock.reserve(db, "2026-03", sha_a)
    hits = {"n": 0}
    real_bulk = importer._run_bulk

    def takeover_after_first_batch(coll, ops):
        res = real_bulk(coll, ops)
        hits["n"] += 1
        if hits["n"] == 1:                                         # tras el primer lote otro intento asume el mes
            db.month_reservations.update_one({"_id": "2026-03"},
                                             {"$set": {"lease_expires_at": datetime.now(UTC) - timedelta(seconds=9)}})
            hits["new"] = month_lock.reserve(db, "2026-03", sha_a)
        return res
    importer._run_bulk, saved = takeover_after_first_batch, importer._run_bulk
    try:
        with pytest.raises(month_lock.LostReservation):
            importer.import_workbook(path, db, expected_month="2026-03", batch_size=3,
                                     fence=month_lock.Fence(db, old))
    finally:
        importer._run_bulk = saved
    n_after_loss = db.sales.count_documents({})
    assert 0 < n_after_loss <= 3 + 3                               # a lo sumo el lote en curso; nada despues
    assert sha_a not in approved_sources(db)
    rep = importer.import_workbook(path, db, expected_month="2026-03", fence=month_lock.Fence(db, hits["new"]))
    assert rep.estado == "completed" and db.sales.count_documents({}) == 10 and len(db.sales.distinct("linea_id")) == 10


def test_reserve_does_not_displace_a_same_source_owner_that_renewed_between_read_and_cas(env):
    db, uploads, tmp = env
    (sha_a, _), _ = two_sources_march(uploads, tmp)
    owner = month_lock.reserve(db, "2026-03", sha_a)
    db.month_reservations.update_one({"_id": "2026-03"}, {"$set": {"lease_expires_at": datetime.now(UTC) - timedelta(seconds=9)}})
    with pytest.raises(month_lock.ImportInProgress):
        month_lock.reserve(db, "2026-03", sha_a, after_read=lambda: month_lock.renew(db, owner))
    assert db.month_reservations.find_one({"_id": "2026-03"})["generation"] == 1
    month_lock.renew(db, owner)                                    # el dueno original sigue vigente


def test_two_concurrent_reservations_of_different_sources_have_one_winner(env):
    db, uploads, tmp = env
    (sha_a, _), (sha_b, _) = two_sources_march(uploads, tmp)
    gate, out = threading.Barrier(2, timeout=30), []

    def go(sha):
        gate.wait()
        try:
            out.append(("ok", month_lock.reserve(db, "2026-03", sha).sha256))
        except month_lock.MonthReserved:
            out.append(("reserved", sha))
    ts = [threading.Thread(target=go, args=(s,)) for s in (sha_a, sha_b)]
    [t.start() for t in ts]
    [t.join(30) for t in ts]
    assert sorted(o[0] for o in out) == ["ok", "reserved"]
    assert db.month_reservations.count_documents({}) == 1


def test_different_months_are_independent(env):
    db, uploads, tmp = env
    s3 = store_upload(uploads, tmp, month_rows(3, bad_currency=0), "m3.xlsx")
    s4 = store_upload(uploads, tmp, month_rows(4, bad_currency=0), "m4.xlsx")
    enqueue_import(db, s3[0], s3[1], "2026-03")
    enqueue_import(db, s4[0], s4[1], "2026-04")
    assert run_job(db, uploads)["status"] == "completed" and run_job(db, uploads)["status"] == "completed"
    assert set(approved_sources(db)) == {s3[0], s4[0]}
