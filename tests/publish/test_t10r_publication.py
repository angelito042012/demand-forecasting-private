"""T10R R07/R08: limpieza y toma de control NO pueden pisar a un propietario que renueva/promueve.

Cada prueba intercala la accion del otro actor justo DESPUES de la lectura y ANTES del CAS/borrado (el envoltorio
`Interleaved` ejecuta un callback una vez, al volver el primer `runs.find_one` que cumple el filtro). Funciona
igual contra el codigo anterior, de modo que estas regresiones fallan antes de la correccion."""
from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta

import pytest

from pipeline.publish import protocol
from pipeline.publish.protocol import (
    LostOwnership,
    PublishInProgressError,
    claim_run,
    complete_run,
    guard,
    insert_children,
    purge_orphans,
)
from pipeline.publish.schema import ensure_schema

from .helpers import temp_db
from .test_protocol_concurrency import prepared, run_doc

pytestmark = pytest.mark.mongo
CHILDREN = ("forecasts", "recommendations", "backtests")


class _Coll:
    def __init__(self, coll, after):
        self._c, self._after = coll, after

    def find_one(self, *a, **k):
        r = self._c.find_one(*a, **k)
        self._after(a, r)
        return r

    def __getattr__(self, name):
        return getattr(self._c, name)


class Interleaved:
    """Base envuelta: tras la primera lectura `runs.find_one` que cumpla `when`, ejecuta `action` (una sola vez)."""

    def __init__(self, db, when, action):
        self._db, self._when, self._action, self._done = db, when, action, False
        self.runs = _Coll(db.runs, self._after)

    def _after(self, args, result):
        if not self._done and result is not None and self._when(args, result):
            self._done = True
            self._action()

    def __getattr__(self, name):
        return getattr(self._db, name)

    def __getitem__(self, name):
        return self.runs if name == "runs" else self._db[name]


def staged(db, n=10, run_id="gen-test", key="k1", stale=True):
    """Intento 1 con hijos ya escritos y (si stale) lease vencido. Devuelve el Attempt."""
    ensure_schema(db)
    t0 = datetime.now(UTC) - timedelta(seconds=500)
    _, att = claim_run(db, run_doc(run_id, key), now=t0, lease_seconds=60)
    data = prepared(n)
    protocol.stamp(att, data)
    insert_children(db, att, data, lambda: guard(db, att, now=t0, lease_seconds=60))
    if stale:
        db.runs.update_one({"run_id": run_id}, {"$set": {"lease_expires_at": t0 + timedelta(seconds=60)}})
    return att


def count(db, cid):
    return {c: db[c].count_documents({"run_id": cid}) for c in CHILDREN}


def by_run(args, base):
    return args and args[0].get("run_id") == base


def test_r07_renewal_between_read_and_cleanup_keeps_all_children():
    with temp_db() as db:
        att = staged(db)
        before = count(db, att.children_id)
        proxy = Interleaved(db, lambda a, r: by_run(a, "gen-test"), lambda: guard(db, att))   # el dueno renueva
        purge_orphans(proxy)
        assert count(db, att.children_id) == before and all(before.values())
        assert db.runs.find_one({"run_id": "gen-test"})["status"] == "staging"
        complete_run(db, att, {})                                   # y aun puede promover
        assert db.runs.find_one({"run_id": "gen-test"})["children_ref"] == att.children_id


def test_r07_promotion_and_activation_between_read_and_cleanup_keep_visible_run_intact():
    with temp_db() as db:
        att = staged(db)
        before = count(db, att.children_id)

        def promote():
            guard(db, att)
            t = complete_run(db, att, {})
            assert protocol.activate_monotonic(db, "gen-test", t)

        purge_orphans(Interleaved(db, lambda a, r: by_run(a, "gen-test"), promote))
        run = db.runs.find_one({"run_id": "gen-test"})
        assert run["status"] == "completed" and run["children_ref"] == att.children_id
        assert count(db, att.children_id) == before and all(before.values())
        assert db.run_pointer.find_one({"_id": "active"})["run_id"] == "gen-test"


def test_r07_cleanup_reserves_first_then_old_owner_cannot_renew_complete_write_or_activate():
    with temp_db() as db:
        att = staged(db)
        removed = purge_orphans(db)
        assert sum(removed.get(c, 0) for c in CHILDREN) > 0 and not any(count(db, att.children_id).values())
        run = db.runs.find_one({"run_id": "gen-test"})
        assert run["status"] == "failed" and run["owner"] is None and run["error"]["code"] == "INTENTO_ABANDONADO"
        with pytest.raises(LostOwnership):
            guard(db, att)
        with pytest.raises(LostOwnership):
            complete_run(db, att, {})
        data = prepared(3)
        protocol.stamp(att, data)
        with pytest.raises(LostOwnership):
            insert_children(db, att, data, lambda: guard(db, att))
        assert not any(count(db, att.children_id).values())
        with pytest.raises(protocol.PublishValidationError):
            protocol.activate_monotonic(db, "gen-test", datetime.now(UTC))
        assert db.run_pointer.find_one({"_id": "active"}) is None


def test_r07_two_cleaners_one_reserves_the_other_is_a_noop_and_repetition_is_idempotent():
    with temp_db() as db:
        att = staged(db)
        gate = threading.Barrier(2, timeout=30)

        def wait_both():
            gate.wait()

        results, errors = [], []

        def cleaner():
            try:
                results.append(purge_orphans(Interleaved(db, lambda a, r: by_run(a, "gen-test"), wait_both)))
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        ts = [threading.Thread(target=cleaner) for _ in range(2)]
        [t.start() for t in ts]
        [t.join(60) for t in ts]
        assert not errors and len(results) == 2
        assert not any(count(db, att.children_id).values())
        assert db.runs.find_one({"run_id": "gen-test"})["status"] == "failed"
        assert purge_orphans(db) == {}                              # repeticion: nada que hacer, sin error
        assert db.runs.count_documents({"run_id": "gen-test"}) == 1


def test_r07_returning_old_attempt_cannot_touch_the_new_generation():
    with temp_db() as db:
        old = staged(db)
        purge_orphans(db)
        _, new = claim_run(db, run_doc("gen-test", "k1"))
        assert new.generation == 2
        data = prepared(5)
        protocol.stamp(new, data)
        insert_children(db, new, data, lambda: guard(db, new))
        complete_run(db, new, {})
        with pytest.raises(LostOwnership):
            guard(db, old)
        protocol.delete_own_children(db, old)                       # solo su propio espacio (vacio)
        purge_orphans(db)
        assert count(db, new.children_id) == {"forecasts": 5, "recommendations": 5, "backtests": 1}


def test_r07_partial_cleanup_failure_is_resumed_by_the_next_pass():
    with temp_db() as db:
        att = staged(db)

        class Boom(Exception):
            pass

        real = db["recommendations"].delete_many
        calls = {"n": 0}

        class FlakyColl(_Coll):
            def delete_many(self, *a, **k):
                calls["n"] += 1
                if calls["n"] == 1:
                    raise Boom()
                return real(*a, **k)

        class Flaky(Interleaved):
            def __getitem__(self, name):
                return FlakyColl(self._db[name], lambda *_: None) if name == "recommendations" else super().__getitem__(name)

        with pytest.raises(Boom):
            purge_orphans(Flaky(db, lambda a, r: False, lambda: None))
        assert db.runs.find_one({"run_id": "gen-test"})["status"] == "failed"      # ya reservada: no puede revivir
        with pytest.raises(LostOwnership):
            guard(db, att)
        purge_orphans(db)
        assert not any(count(db, att.children_id).values())


def test_r07_completed_superseded_and_historic_children_are_never_cleaned():
    with temp_db() as db:
        att = staged(db, run_id="gen-ok", key="k-ok", stale=False)
        complete_run(db, att, {})
        att2 = staged(db, run_id="gen-old", key="k-old", stale=False)
        complete_run(db, att2, {})
        db.runs.update_one({"run_id": "gen-old"}, {"$set": {"status": "superseded"}})
        db.runs.insert_one({"run_id": "hist-x", "status": "completed", "idempotency_key": "kh", "children_ref": None})
        db.forecasts.insert_one({"run_id": "hist-x", "level": "sku", "entity_id": "h|1", "h": 1, "target_date": "d"})
        snapshot = {a: count(db, a) for a in (att.children_id, att2.children_id, "hist-x")}
        assert purge_orphans(db) == {}
        assert {a: count(db, a) for a in snapshot} == snapshot


def test_r07_staging_run_without_children_and_expired_lease_is_marked_abandoned_but_kept():
    with temp_db() as db:
        ensure_schema(db)
        t0 = datetime.now(UTC) - timedelta(seconds=500)
        claim_run(db, run_doc("gen-empty", "ke"), now=t0, lease_seconds=60)
        purge_orphans(db)
        doc = db.runs.find_one({"run_id": "gen-empty"})
        assert doc is not None and doc["status"] == "failed" and doc["error"]["code"] == "INTENTO_ABANDONADO"
        _, again = claim_run(db, run_doc("gen-empty", "ke"))         # se puede reintentar (ruta de recuperacion)
        assert again.generation == 2


# ------------------------------------------------------------------------------------------------ R08
def test_r08_takeover_does_not_displace_an_owner_that_renewed_between_read_and_cas():
    with temp_db() as db:
        att = staged(db)
        proxy = Interleaved(db, lambda a, r: "idempotency_key" in (a[0] if a else {}), lambda: guard(db, att))
        with pytest.raises(PublishInProgressError):
            claim_run(proxy, run_doc("gen-test", "k1"))
        run = db.runs.find_one({"run_id": "gen-test"})
        assert run["generation"] == 1 and run["owner"] == att.owner and run["status"] == "staging"
        complete_run(db, att, {})                                   # el dueno original sigue pudiendo promover


def test_r08_takeover_proceeds_when_the_lease_really_expired():
    with temp_db() as db:
        staged(db)
        status, new = claim_run(db, run_doc("gen-test", "k1"))
        assert status == "claimed" and new.generation == 2


def test_r08_takeover_of_a_run_with_no_lease_still_works_and_two_contenders_yield_one_winner():
    with temp_db() as db:
        staged(db)
        gate = threading.Barrier(2, timeout=30)
        out = []

        def contender():
            try:
                px = Interleaved(db, lambda a, r: "idempotency_key" in (a[0] if a else {}), lambda: gate.wait())
                out.append(claim_run(px, run_doc("gen-test", "k1"))[0])
            except PublishInProgressError:
                out.append("busy")

        ts = [threading.Thread(target=contender) for _ in range(2)]
        [t.start() for t in ts]
        [t.join(60) for t in ts]
        assert sorted(out) == ["busy", "claimed"]
        assert db.runs.find_one({"run_id": "gen-test"})["generation"] == 2
