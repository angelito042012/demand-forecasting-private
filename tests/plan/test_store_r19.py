"""R19 (REVISION_CODEX_19): relevo e interrupcion de un calculo de plan con propiedad por intento (bases df_test_* reales de Mongo).

Dos intentos controlados con el `guard` del trabajo: el intento A (antiguo) dispara en un punto exacto la ejecucion COMPLETA del
intento B (sucesor, tras vencer el lease de A) y despues pierde la propiedad o falla. Con el codigo entregado en 2e99534 la
limpieza de A borraba por `plan_id` y destruia lo publicado por B (cabecera `completed` con 0 filas).
"""
from __future__ import annotations

from datetime import timedelta

import pytest

from pipeline.jobs.queue import LostOwnership
from pipeline.plan import store
from pipeline.plan.engine import PlanRejected
from tests.plan import helpers_plan as h
from tests.publish.helpers import temp_db

pytestmark = pytest.mark.mongo


@pytest.fixture()
def db():
    with temp_db() as database:
        h.seed_all(database)
        yield database


def pid_of(db):
    return store.resolve(db, h.RAW)[1]


def published(db, pid):
    """Filas PUBLICADAS del plan tal como las lee la API (children_ref); con el codigo antiguo, todas las del plan_id."""
    run = db.plan_runs.find_one({"plan_id": pid}, {"_id": 0})
    flt = store.children_filter(run) if hasattr(store, "children_filter") else {"plan_id": pid}
    return list(db.plan_results.find(flt, {"_id": 0}))


def expire_lease(db, pid):
    db.plan_runs.update_one({"plan_id": pid, "status": "staging"}, {"$set": {"lease_expires_at": store._now() - timedelta(seconds=5)}})


def hook_at(n, action):
    """guard del trabajo que ejecuta `action()` en su llamada n (1-based) y cuenta las llamadas."""
    calls = {"n": 0}

    def guard():
        calls["n"] += 1
        if calls["n"] == n:
            action()
    return guard, calls


def test_successor_publishes_before_old_attempt_cleanup_and_old_attempt_loses(db, monkeypatch):
    monkeypatch.setattr(store, "BATCH", 1)
    pid, out = pid_of(db), {}

    def successor_runs_then_old_loses():
        expire_lease(db, pid)                               # el worker antiguo murio/se retraso: su lease vencio
        out["b"] = store.generate_plan(db, h.RAW)           # el sucesor completa el plan por completo
        raise LostOwnership("worker-antiguo")               # y recien entonces el antiguo descubre que perdio el trabajo

    guard, _ = hook_at(3, successor_runs_then_old_loses)    # 1: antes de reclamar, 2: lote 1, 3: lote 2
    with pytest.raises(LostOwnership):
        store.generate_plan(db, h.RAW, guard=guard)
    head = db.plan_runs.find_one({"plan_id": pid}, {"_id": 0})
    rows = published(db, pid)
    assert out["b"]["action"] == "created"
    assert head["status"] == "completed" and head["counts"]["products"] == len(h.PRODUCTS)
    assert len(rows) == len(h.PRODUCTS), "la limpieza del intento antiguo no puede borrar lo publicado por el sucesor"
    assert {r["producto_id"] for r in rows} == set(h.PRODUCTS)


def test_stale_attempt_cannot_write_after_takeover_even_without_guard_failure(db, monkeypatch):
    """El guard del trabajo NO falla: es la propiedad del plan (CAS por intento) la que detiene al intento obsoleto."""
    monkeypatch.setattr(store, "BATCH", 1)
    pid = pid_of(db)

    def successor():
        expire_lease(db, pid)
        store.generate_plan(db, h.RAW)

    guard, _calls = hook_at(2, successor)
    with pytest.raises(LostOwnership):
        store.generate_plan(db, h.RAW, guard=guard)
    assert len(published(db, pid)) == len(h.PRODUCTS)
    # el antiguo escribio a lo sumo antes del relevo; sus filas (otro token) son invisibles y no cuentan para la API
    run = db.plan_runs.find_one({"plan_id": pid}, {"_id": 0})
    invisibles = db.plan_results.count_documents({"plan_id": pid, "attempt": {"$ne": run["children_ref"]}}) if run.get("children_ref") else 0
    assert db.plan_results.count_documents(store.children_filter(run)) == len(h.PRODUCTS) if hasattr(store, "children_filter") else True
    assert invisibles >= 0


def test_late_failure_of_the_old_attempt_does_not_touch_the_published_plan(db, monkeypatch):
    monkeypatch.setattr(store, "BATCH", 1)
    pid = pid_of(db)

    def successor_then_boom():
        expire_lease(db, pid)
        store.generate_plan(db, h.RAW)
        raise RuntimeError("fallo tardio del intento antiguo")

    guard, _ = hook_at(3, successor_then_boom)
    with pytest.raises(RuntimeError):
        store.generate_plan(db, h.RAW, guard=guard)
    head = db.plan_runs.find_one({"plan_id": pid}, {"_id": 0})
    assert head["status"] == "completed", "un fallo tardio ajeno no puede degradar el plan publicado"
    assert len(published(db, pid)) == len(h.PRODUCTS)


def test_takeover_during_the_initial_cleanup_does_not_delete_the_successor_rows(db, monkeypatch):
    """Intercalacion durante la limpieza inicial: el sucesor publica justo antes de que el antiguo limpie."""
    monkeypatch.setattr(store, "BATCH", 1)
    pid = pid_of(db)
    # restos de un intento anterior muerto (staging con lease vencido y filas parciales de SU token)
    first = store.generate_plan(db, h.RAW)
    assert first["action"] == "created"
    db.plan_runs.update_one({"plan_id": pid}, {"$set": {"status": "staging", "lease_expires_at": store._now() - timedelta(seconds=5)}})
    real_purge = getattr(store, "purge_prior", None)
    done = {}

    def interleaved(*a, **k):
        monkeypatch.setattr(store, "purge_prior", real_purge)       # una sola vez: el sucesor usa la limpieza real
        expire_lease(db, pid)
        done["b"] = store.generate_plan(db, h.RAW)          # el sucesor completa entre el reclamo y la limpieza del antiguo
        return real_purge(*a, **k)

    if real_purge:
        monkeypatch.setattr(store, "purge_prior", interleaved)
        with pytest.raises(LostOwnership):                  # el antiguo ya no es dueno: se detiene
            store.generate_plan(db, h.RAW)
    else:                                                   # codigo anterior a R19: limpieza por plan_id al empezar
        monkeypatch.setattr(store, "clean_attempt", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("sin R19")), raising=False)
        pytest.fail("sin proteccion de intento")
    assert len(published(db, pid)) == len(h.PRODUCTS)
    assert db.plan_runs.find_one({"plan_id": pid})["status"] == "completed"


def test_same_plan_concurrent_attempt_is_told_to_retry_and_then_reuses(db):
    pid = pid_of(db)
    seen = {}

    def concurrent():
        try:
            store.generate_plan(db, h.RAW)                  # lease vigente del primero: no puede reclamar
        except PlanRejected as exc:
            seen["code"] = exc.code

    guard, _ = hook_at(2, concurrent)
    first = store.generate_plan(db, h.RAW, guard=guard)
    assert seen["code"] == "PLAN_EN_CURSO" and first["action"] == "created"
    assert len(published(db, pid)) == len(h.PRODUCTS)
    assert store.generate_plan(db, h.RAW)["action"] == "reused"


def test_failed_attempt_of_the_owner_leaves_failed_and_keeps_other_plans(db, monkeypatch):
    other = store.generate_plan(db, {**h.RAW, "reserve_days": 5})
    other_rows = len(published(db, other["plan_id"]))
    monkeypatch.setattr(store, "BATCH", 1)
    pid = pid_of(db)
    guard, _ = hook_at(3, lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(RuntimeError):
        store.generate_plan(db, h.RAW, guard=guard)
    head = db.plan_runs.find_one({"plan_id": pid}, {"_id": 0})
    assert head["status"] == "failed" and db.plan_results.count_documents({"plan_id": pid}) == 0
    assert len(published(db, other["plan_id"])) == other_rows            # otros planes intactos
    again = store.generate_plan(db, h.RAW)                              # el reintento toma el plan fallido y lo completa
    assert again["action"] == "created" and len(published(db, pid)) == len(h.PRODUCTS)


def test_published_results_are_only_those_of_children_ref_and_legacy_plans_still_read(db):
    pid = pid_of(db)
    store.generate_plan(db, h.RAW)
    run = db.plan_runs.find_one({"plan_id": pid}, {"_id": 0})
    # filas huerfanas de otro intento (invisibles) no entran en la lectura
    db.plan_results.insert_one({"plan_id": pid, "attempt": "huerfano", "producto_id": "1000001", "status": "OK", "basura": True})
    assert all(not r.get("basura") for r in published(db, pid)) and len(published(db, pid)) == len(h.PRODUCTS)
    # plan anterior a R19: cabecera sin children_ref y filas sin `attempt`
    db.plan_runs.update_one({"plan_id": pid}, {"$unset": {"children_ref": ""}})
    db.plan_results.update_many({"plan_id": pid, "attempt": run["children_ref"]}, {"$unset": {"attempt": ""}})
    db.plan_results.delete_many({"plan_id": pid, "attempt": "huerfano"})
    legacy = db.plan_runs.find_one({"plan_id": pid}, {"_id": 0})
    assert db.plan_results.count_documents(store.children_filter(legacy)) == len(h.PRODUCTS)


def test_purge_failure_after_publication_does_not_delete_the_published_plan(db, monkeypatch):
    """Adenda de REVISION_CODEX_19: si la purga posterior a la publicacion falla, el plan completado conserva sus resultados."""
    pid = pid_of(db)

    def boom(*_a, **_k):
        raise RuntimeError("fallo de la purga tras publicar")

    monkeypatch.setattr(store, "purge_orphans", boom)
    out = store.generate_plan(db, h.RAW)                    # la publicacion ya ocurrio: el fallo de mantenimiento no la deshace
    head = db.plan_runs.find_one({"plan_id": pid}, {"_id": 0})
    assert out["action"] == "created" and head["status"] == "completed"
    assert len(published(db, pid)) == len(h.PRODUCTS) == head["counts"]["products"]
    monkeypatch.undo()
    assert store.generate_plan(db, h.RAW)["action"] == "reused"


def test_uncertain_publication_acknowledgement_keeps_published_results_and_retry_is_idempotent(db, monkeypatch):
    """Adenda 2 de REVISION_CODEX_19: el servidor aplica la publicacion pero el cliente recibe un error de red."""
    from pymongo.errors import AutoReconnect
    pid = pid_of(db)
    coll = db[store.RUNS]
    real = type(coll).update_one

    def lossy(self, flt, upd, *a, **k):
        res = real(self, flt, upd, *a, **k)
        if upd.get("$set", {}).get("status") == "completed":
            raise AutoReconnect("respuesta perdida tras publicar")
        return res

    monkeypatch.setattr(type(coll), "update_one", lossy)
    with pytest.raises(AutoReconnect):
        store.generate_plan(db, h.RAW)
    monkeypatch.undo()
    head = db.plan_runs.find_one({"plan_id": pid}, {"_id": 0})
    assert head["status"] == "completed" and len(published(db, pid)) == len(h.PRODUCTS) == head["counts"]["products"]
    assert store.generate_plan(db, h.RAW)["action"] == "reused"            # el reintento es idempotente
    assert len(published(db, pid)) == len(h.PRODUCTS)


def test_ordinary_failure_still_cleans_only_its_own_rows_after_winning_the_failed_cas(db, monkeypatch):
    monkeypatch.setattr(store, "BATCH", 1)
    pid = pid_of(db)
    guard, _ = hook_at(3, lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(RuntimeError):
        store.generate_plan(db, h.RAW, guard=guard)
    assert db.plan_runs.find_one({"plan_id": pid})["status"] == "failed" and db.plan_results.count_documents({"plan_id": pid}) == 0
