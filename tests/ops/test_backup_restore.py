"""T11A: copia a la base de publicacion, export y restauracion verificada (MongoDB real, bases df_test_<uuid>, SINTETICO)."""
from __future__ import annotations

import gzip
import json
import os
import uuid
from datetime import datetime

import pytest
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from pipeline.publish import archive as ar
from pipeline.publish import final_package as fp
from pipeline.publish.schema import ensure_schema
from scripts import backup_restore as br
from scripts import build_publication_db as bpd
from tests.publish.test_final_package import make_package

HIST_ACTIVE, HIST_OLD = "hist-20260710-aaaaaaaaaaaa", "hist-20260710-bbbbbbbbbbbb"
GEN_OK, GEN_FAIL = "gen-20260703-cccccccccccc", "gen-20260620-dddddddddddd"
CFG = {"version": "t11a-test", "base_publicacion": "x", "base_origen_solo_lectura": "y",
       "copiar_colecciones": ["sales", "credit_notes", "imports", "import_conflicts", "import_rejects", "month_reservations"],
       "corridas_historicas": [HIST_ACTIVE, HIST_OLD], "puntero_activo": HIST_ACTIVE, "cuota_atlas_free_mb": 512,
       "objetivo_uso_maximo_fraccion": 0.6, "etiqueta": "Inventario simulado con supuestos; no corresponde al inventario real de la empresa"}
T = datetime(2026, 10, 17, 12, 0, 0)


@pytest.fixture
def mongo():
    uri = os.environ.get("MONGODB_URI", "mongodb://127.0.0.1:27017")
    client = MongoClient(uri, serverSelectionTimeoutMS=1500)
    try:
        client.admin.command("ping")
    except PyMongoError:
        client.close()
        pytest.skip("MongoDB no disponible")
    names: list[str] = []

    def new(prefix="df_test_"):
        n = f"{prefix}{uuid.uuid4().hex[:12]}"
        names.append(n)
        return client[n]
    client.new_db = new           # type: ignore[attr-defined]
    try:
        yield client
    finally:
        for n in names:
            client.drop_database(n)
        client.close()


def _fc(rid, level, ent, cat, date, p):
    return {"run_id": rid, "level": level, "entity_id": ent, "sku": ent.split("|")[0] if level == "sku" else None,
            "almacen": "1" if level == "sku" else None, "categoria": cat, "target_date": date, "h": 1,
            "pred": {"promedio_28": p, "rf_categoria_distribuido": p, "cero": 0.0}, "observed": 1, "evaluable": True,
            "provenance": "OBSERVED_EXCEL", "schema_version": 1}


def _run(rid, kind, status, cid=None, n_sku=3, n_rec=2, n_bt=0, cutoff="2026-07-10"):
    r = {"run_id": rid, "status": status, "kind": kind, "run_label": "x", "idempotency_key": f"k-{rid}", "fingerprint": "f",
         "cutoff": cutoff, "origin": cutoff, "target_start": "2026-07-11", "target_end": "2026-07-31", "horizon_days": 21,
         "method": {}, "sources": [], "artifacts": [], "code": {}, "schema_version": 1, "published_at": T,
         "counts": {"forecasts_sku": n_sku, "forecasts_categoria": 1, "recommendations": n_rec, "backtests": n_bt}}
    if cid:
        r["children_ref"] = cid
    return r


def _children(db, cid, n_sku=3, n_rec=2, n_bt=0):
    db.forecasts.insert_many([_fc(cid, "sku", f"91000{i}|1", "CAT A", "2026-07-11", float(i)) for i in range(n_sku)]
                             + [_fc(cid, "categoria", "CAT A", "CAT A", "2026-07-11", 3.0)])
    db.recommendations.insert_many([{"run_id": cid, "sku": f"91000{i}", "almacen": "1", "status": "ok", "categoria": "CAT A"}
                                    for i in range(n_rec)])
    if n_bt:
        db.backtests.insert_one({"backtest_id": f"bt-{cid}", "run_id": cid, "kind": "T07_desarrollo"})


def make_source(db) -> None:
    """Origen sintetico con sesiones, usuarios, trabajos y corridas generadas que NO deben copiarse."""
    db.sales.insert_many([{"linea_id": f"l{i}", "fecha": "2026-03-01", "sku": "9100000", "cantidad_base": i,
                           "doc_hash": "h", "sources": [{"source_sha256": "s"}]} for i in range(25)])
    db.credit_notes.insert_many([{"linea_id": f"c{i}", "fecha": "2026-03-02", "doc_hash": "h", "sources": [{"source_sha256": "s"}]}
                                 for i in range(3)])
    db.imports.insert_one({"import_id": "i1", "sha256": "s", "estado": "completed", "mes": "2026-03", "noop": False})
    db.month_reservations.insert_one({"_id": "2026-03", "state": "completed"})
    db.import_conflicts.insert_one({"conflict_id": "c1"})
    db.import_conflicts.delete_many({})
    db.sessions.insert_one({"token_hash": "SECRETO-SESION", "user": "admin"})
    db.users.insert_one({"username": "admin", "password_hash": "SECRETO-HASH"})
    db.login_attempts.insert_one({"scope_key": "k", "at": T})
    db.jobs.insert_one({"job_id": "j1", "type": "generate"})
    db.scheduler_ticks.insert_one({"tick": 1})
    db.runs.insert_many([_run(HIST_ACTIVE, "historical_development", "completed", n_bt=1),
                         _run(HIST_OLD, "historical_development", "superseded", n_bt=1),
                         _run(GEN_OK, "generated_baseline", "completed", cid=GEN_OK + "~g1"),
                         _run(GEN_FAIL, "generated_baseline", "failed")])
    _children(db, HIST_ACTIVE, n_bt=1)
    _children(db, HIST_OLD, n_bt=1)
    _children(db, GEN_OK + "~g1")
    db.run_pointer.insert_one({"_id": "active", "run_id": GEN_OK, "published_at": T})
    ensure_schema(db)


def _snapshot(db):
    return {n: ar.collection_hash(db[n]) for n in sorted(db.list_collection_names())}


def build(mongo, tmp_path, **kw):
    src = mongo.new_db()
    make_source(src)
    tgt = mongo.new_db()
    man = bpd.build_publication(mongo, CFG, source=src.name, target=tgt.name, out_dir=tmp_path / "t11a", **kw)
    return src, tgt, man


# ------------------------------------------------------------------ base de publicacion
def test_publication_copies_allowed_and_excludes_forbidden(mongo, tmp_path):
    src = mongo.new_db()
    make_source(src)
    before = _snapshot(src)
    tgt = mongo.new_db()
    man = bpd.build_publication(mongo, CFG, source=src.name, target=tgt.name, out_dir=tmp_path / "t11a")
    assert man["ok"], man["problemas"]
    assert _snapshot(src) == before                                    # el origen quedo intacto (solo lectura)
    names = set(tgt.list_collection_names())
    assert not names & {"sessions", "users", "login_attempts", "login_budget", "jobs", "scheduler_ticks"}
    assert {r["run_id"] for r in tgt.runs.find()} == {HIST_ACTIVE, HIST_OLD}
    assert tgt.sales.count_documents({}) == 25 and tgt.credit_notes.count_documents({}) == 3
    assert tgt.runs.find_one({"run_id": HIST_OLD})["status"] == "superseded"
    assert tgt.run_pointer.find_one({"_id": "active"})["run_id"] == HIST_ACTIVE      # no el de las generadas
    assert tgt.forecasts.distinct("run_id") == sorted([HIST_ACTIVE, HIST_OLD])
    for coll in ("sales", "forecasts", "runs"):
        assert ar.collection_hash(tgt[coll])["content_sha256"] == man["colecciones"][coll]["content_sha256"]
    assert {i["name"] for i in tgt.sales.list_indexes()} >= {"uq_linea_id", "ix_fecha_sku", "ix_sku_fecha"}
    assert {i["name"] for i in tgt.forecasts.list_indexes()} >= {"uq_run_level_entity_date"}
    assert ar.check_runs(tgt)["ok"]


def test_publication_archives_omitted_runs_and_manifests_have_no_secrets(mongo, tmp_path):
    src, _tgt, man = build(mongo, tmp_path)
    out = tmp_path / "t11a"
    arch = json.loads((out / "archivo" / "manifiesto_archivo.json").read_text(encoding="utf-8"))
    ids = {c["run_id"] for c in arch["corridas"]}
    assert ids == {GEN_OK, GEN_FAIL}
    ok = next(c for c in arch["corridas"] if c["run_id"] == GEN_OK)
    assert ok["hijos"]["forecasts"]["count"] == 4 and ok["hijos"]["recommendations"]["count"] == 2
    for c in arch["corridas"]:
        for f in c["archivos"]:
            assert ar.sha256_file(out / "archivo" / f["name"]) == f["sha256"]
    with gzip.open(out / "archivo" / f"{GEN_OK}_g1.forecasts.ndjson.gz", "rt", encoding="utf-8") as fh:
        assert sum(1 for _ in fh) == 4
    assert src.runs.count_documents({"run_id": GEN_OK}) == 1              # no se borra del origen
    assert {"sessions", "users", "jobs"} <= set(man["exclusiones"]["colecciones"])
    text = "".join(p.read_text(encoding="utf-8") for p in out.glob("manifiesto_*.json"))
    assert "SECRETO" not in text
    docs = json.loads((out / "manifiesto_publicacion_docs.json").read_text(encoding="utf-8"))
    assert "archivo_privado" not in docs and docs["ok"] is True


def test_publication_without_children_dump_only_hashes(mongo, tmp_path):
    _, _, man = build(mongo, tmp_path, dump_children=False)
    assert man["ok"] and not list((tmp_path / "t11a" / "archivo").glob("*.ndjson.gz"))
    assert all(e["hijos"]["forecasts"]["count"] in (0, 4) for e in man["archivo_privado"]["corridas"])


def test_overwrite_refused_unless_explicit_and_protected_dbs(mongo, tmp_path):
    src, tgt, _ = build(mongo, tmp_path)
    tgt.sales.update_one({}, {"$set": {"marca": "no-borrar"}})
    with pytest.raises(ar.ArchiveError, match="sobrescritura"):
        bpd.build_publication(mongo, CFG, source=src.name, target=tgt.name, out_dir=tmp_path / "o2")
    assert tgt.sales.count_documents({"marca": "no-borrar"}) == 1         # la base existente no se toco
    for name in ("demand_forecasting_v2", "demand_forecasting_dev", "admin"):
        with pytest.raises(ar.ArchiveError, match="protegida"):
            bpd.build_publication(mongo, CFG, source=src.name, target=name, out_dir=tmp_path / "o3", overwrite=True)
    man = bpd.build_publication(mongo, CFG, source=src.name, target=tgt.name, out_dir=tmp_path / "o4", overwrite=True)
    assert man["ok"] and tgt.sales.count_documents({"marca": "no-borrar"}) == 0


def test_source_equal_target_refused(mongo, tmp_path):
    src = mongo.new_db()
    make_source(src)
    with pytest.raises(ar.ArchiveError):
        bpd.build_publication(mongo, CFG, source=src.name, target=src.name, out_dir=tmp_path / "o")


# ------------------------------------------------------------------ export / restauracion
def _export(mongo, tmp_path):
    _src, tgt, _ = build(mongo, tmp_path)
    pkg = make_package(tmp_path / "pkg")
    fp.publish_final(tgt, pkg, seal_doc=None)                             # la base de publicacion tambien lleva la final
    man = ar.export_db(tgt, tmp_path / "bk", artifacts=br.private_artifacts(pkg))
    return tgt, man


def test_export_restore_full_verification(mongo, tmp_path):
    tgt, man = _export(mongo, tmp_path)
    assert not set(man["colecciones"]) & set(ar.SECRET_COLLECTIONS)
    assert {r["run_id"] for r in man["corridas"]} >= {HIST_ACTIVE, HIST_OLD} and len(man["corridas"]) == 3
    assert man["puntero_activo"] == HIST_ACTIVE and man["artefactos_privados"]
    assert all(len(a["sha256"]) == 64 for a in man["artefactos_privados"])
    assert (tmp_path / "bk" / "indices.json").is_file()
    rest = mongo.new_db("df_restore_t11a_")
    rep = ar.restore_db(tmp_path / "bk", rest)
    assert rep["ok"], rep["problemas"]
    assert rep["segundos_restauracion"] >= 0 and rep["medicion"]["data_plus_index_mb"] > 0 and rep["bytes_comprimidos"] > 0
    for n, c in man["colecciones"].items():
        assert rep["colecciones"][n]["ok"] and rep["colecciones"][n]["count"] == c["count"]
        assert ar.collection_hash(tgt[n]) == ar.collection_hash(rest[n])           # identica al origen
        assert ar.index_specs(tgt[n]) == ar.index_specs(rest[n])
    final = rest.runs.find_one({"kind": "final_evaluation"})
    assert final["children_ref"].endswith("~g1") and final["status"] == "completed"
    assert rest.forecasts.count_documents({"run_id": final["children_ref"]}) == final["counts"]["forecasts_sku"] + final["counts"]["forecasts_categoria"]
    assert rest.run_pointer.find_one({"_id": "active"})["run_id"] == HIST_ACTIVE
    assert not set(rest.list_collection_names()) & set(ar.SECRET_COLLECTIONS)


def test_restore_rejects_same_nonempty_and_protected_targets(mongo, tmp_path):
    tgt, _man = _export(mongo, tmp_path)
    with pytest.raises(ar.ArchiveError, match="DIFERENTE"):
        ar.restore_db(tmp_path / "bk", tgt)
    other = mongo.new_db()
    other.sales.insert_one({"x": 1})
    with pytest.raises(ar.ArchiveError, match="no esta vacia"):
        ar.restore_db(tmp_path / "bk", other)
    with pytest.raises(ar.ArchiveError, match="protegida"):
        ar.restore_db(tmp_path / "bk", mongo["demand_forecasting_v2"])


def test_altered_export_file_detected_before_restoring(mongo, tmp_path):
    _, _man = _export(mongo, tmp_path)
    p = tmp_path / "bk" / "sales.ndjson.gz"
    lines = gzip.decompress(p.read_bytes()).decode("utf-8").splitlines()
    lines[3] = lines[3].replace('"cantidad_base": 3', '"cantidad_base": 4444') if '"cantidad_base": 3' in lines[3] else lines[3] + " "
    p.write_bytes(gzip.compress(("\n".join(lines) + "\n").encode("utf-8")))
    assert any("sales" in b for b in ar.verify_export_files(tmp_path / "bk"))
    rest = mongo.new_db("df_restore_t11a_")
    with pytest.raises(ar.ArchiveError, match="alterado"):
        ar.restore_db(tmp_path / "bk", rest)
    assert rest.list_collection_names() == []


def test_altered_document_after_restore_is_detected_by_hash(mongo, tmp_path):
    _, _man = _export(mongo, tmp_path)
    rest = mongo.new_db("df_restore_t11a_")
    assert ar.restore_db(tmp_path / "bk", rest)["ok"]
    rest.sales.update_one({"linea_id": "l3"}, {"$set": {"cantidad_base": 99999}})        # mismo conteo, distinto contenido
    rep = ar.verify_restored(rest, ar.load_manifest(tmp_path / "bk"), tmp_path / "bk")
    assert not rep["ok"] and any("sales" in p and "hash" in p for p in rep["problemas"])


def test_missing_children_and_orphans_detected(mongo, tmp_path):
    _, _man = _export(mongo, tmp_path)
    rest = mongo.new_db("df_restore_t11a_")
    ar.restore_db(tmp_path / "bk", rest)
    one = rest.forecasts.find_one({"run_id": HIST_ACTIVE})
    rest.forecasts.delete_one({"_id": one["_id"]})
    chk = ar.check_runs(rest)
    assert not chk["ok"] and any(HIST_ACTIVE in p and "forecasts_sku" in p or "forecasts_categoria" in p for p in chk["problemas"])
    rest.forecasts.insert_one({**{k: v for k, v in one.items() if k != "_id"}, "run_id": "huerfano~g1"})
    assert any("huerfanos" in p for p in ar.check_runs(rest)["problemas"])


def test_export_refuses_staging_and_nonempty_dir_and_changes(mongo, tmp_path):
    src = mongo.new_db()
    make_source(src)
    src.runs.insert_one(_run("hist-x", "historical_development", "staging"))
    with pytest.raises(ar.ArchiveError, match="staging"):
        ar.export_db(src, tmp_path / "e1")
    src.runs.delete_one({"run_id": "hist-x"})
    (tmp_path / "e2").mkdir()
    (tmp_path / "e2" / "algo").write_text("x", encoding="utf-8")
    with pytest.raises(ar.ArchiveError, match="no esta vacio"):
        ar.export_db(src, tmp_path / "e2")
    man = ar.export_db(src, tmp_path / "e3")
    assert not set(man["colecciones"]) & set(ar.SECRET_COLLECTIONS) and "sessions" in man["excluidas"]
    assert all("SECRETO" not in gzip.decompress(p.read_bytes()).decode("utf-8") for p in (tmp_path / "e3").glob("*.gz"))


def test_cli_export_verify_restore(mongo, tmp_path, monkeypatch, capsys):
    _src, tgt, _ = build(mongo, tmp_path)
    monkeypatch.setattr(br, "get_client", lambda: mongo)
    monkeypatch.setattr(MongoClient, "close", lambda self: None, raising=False)
    assert br.main(["export", "--db", tgt.name, "--out", str(tmp_path / "bk2"), "--artifacts-dir", str(tmp_path / "none")]) == 0
    dst = mongo.new_db("df_restore_t11a_")
    assert br.main(["restore", "--from", str(tmp_path / "bk2"), "--db", dst.name]) == 0
    assert br.main(["verify", "--from", str(tmp_path / "bk2"), "--db", dst.name]) == 0
    out = capsys.readouterr().out
    assert '"ok": true' in out


def test_manifest_timestamp_is_utc_aware(mongo, tmp_path):
    _, man = _export(mongo, tmp_path)
    assert datetime.fromisoformat(man["creado_utc"]).tzinfo is not None
