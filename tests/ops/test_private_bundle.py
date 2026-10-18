"""T11B (R13): bundle privado, export/restauracion integral y consistencia fuerte (SINTETICO, Mongo real en df_test_*)."""
from __future__ import annotations

import json
import os
import shutil
import uuid
from pathlib import Path

import pytest
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from pipeline.publish import archive as ar
from pipeline.publish import private_bundle as pb
from scripts import backup_restore as br
from tests.ops.test_backup_restore import make_source
from tests.publish.test_final_package import make_package


@pytest.fixture
def mongo():
    client = MongoClient(os.environ.get("MONGODB_URI", "mongodb://127.0.0.1:27017"), serverSelectionTimeoutMS=1500)
    try:
        client.admin.command("ping")
    except PyMongoError:
        client.close()
        pytest.skip("MongoDB no disponible")
    names: list[str] = []

    def new(prefix="df_test_"):
        names.append(f"{prefix}{uuid.uuid4().hex[:12]}")
        return client[names[-1]]
    client.new_db = new           # type: ignore[attr-defined]
    try:
        yield client
    finally:
        for n in names:
            client.drop_database(n)
        client.close()


FINAL = "artifacts/private/final"
RR = "artifacts/private/runtime_reference"
SECCIONES = {
    "t12_final": [f"{FINAL}/preparacion/manifiesto_preparacion.json", f"{FINAL}/preparacion/predicciones_fijas.npz",
                  f"{FINAL}/preparacion/inicializacion_sim.npz", f"{FINAL}/preparacion/rf_categoria_T12.joblib",
                  f"{FINAL}/reales_bloque.npz", f"{FINAL}/ventas_agosto_min.csv.gz", f"{FINAL}/predictivo.json",
                  f"{FINAL}/simulacion.json", f"{FINAL}/simulacion_series.npz", f"{FINAL}/auditoria.json",
                  f"{FINAL}/estado.json", f"{FINAL}/verificacion.json"],
    "anclajes_versionados": ["docs/T12_SELLO.json", "config/algo.json"],
}


def make_cfg() -> dict:
    return {"version": pb.BUNDLE_VERSION, "final_dir": FINAL, "secciones": json.loads(json.dumps(SECCIONES)),
            "opcional": {"runtime_reference": {"directorio": RR, "manifiesto": "manifest_referencia.json"}},
            "funcional": {"t12_sello": "docs/T12_SELLO.json"}, "exclusiones": ["secretos", ".git"]}


def make_root(tmp: Path, *, runtime_reference: bool = False) -> Path:
    root = tmp / "proyecto"
    make_package(root / FINAL)
    prep = json.loads((root / FINAL / "preparacion" / "manifiesto_preparacion.json").read_text(encoding="utf-8"))
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "config").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "T12_SELLO.json").write_text(json.dumps({"sello_sha256": prep["sello_sha256"], "archivos": prep["archivos"]}),
                                                  encoding="utf-8")
    (root / "config" / "algo.json").write_text("{}", encoding="utf-8")
    if runtime_reference:
        d = root / RR
        d.mkdir(parents=True)
        (d / "datos.bin").write_bytes(b"referencia-sintetica")
        import hashlib
        (d / "manifest_referencia.json").write_text(json.dumps(
            {"archivos": {"datos.bin": hashlib.sha256(b"referencia-sintetica").hexdigest()}}), encoding="utf-8")
    return root


def export(tmp, *, runtime_reference=False, **kw):
    root = make_root(tmp, runtime_reference=runtime_reference)
    cfg = make_cfg()
    man = pb.export_bundle(root, tmp / "bundle", cfg, **kw)
    return root, cfg, man


# ------------------------------------------------------------------ export y restauracion correctos
def test_export_restore_ok_with_optional_runtime_reference(tmp_path):
    root, cfg, man = export(tmp_path, runtime_reference=True)
    assert man["integro"] is True and man["faltantes"] == []
    assert man["runtime_reference"]["presente"] and [e["ruta"] for e in man["runtime_reference"]["archivos"]] == [
        f"{RR}/datos.bin", f"{RR}/manifest_referencia.json"]
    npz = [e for e in man["archivos"] if e["ruta"].endswith(".npz")]
    assert npz and all("logical_sha256" in e for e in npz)
    assert not any(".env" in e["ruta"] or ".git" in e["ruta"] for e in man["archivos"])
    assert pb.verify_bundle(tmp_path / "bundle")["ok"]
    rep = pb.restore_bundle(tmp_path / "bundle", tmp_path / "rest", root=root, cfg=cfg)
    assert rep["artefactos_ok"] is True, rep["problemas"]
    fc = rep["funcional"]["comprobaciones"]
    assert fc["load_sealed"]["ok"] and fc["estado"]["ok"] and fc["sello_vs_manifiesto"] is True
    assert fc["runtime_reference"]["verificados"] == 1
    for e in man["archivos"]:                     # bytes identicos a los originales
        assert (tmp_path / "rest" / e["ruta"]).read_bytes() == (root / e["ruta"]).read_bytes()


def test_without_optional_runtime_reference_is_still_integral(tmp_path):
    _root, _cfg, man = export(tmp_path)
    assert man["integro"] is True and man["runtime_reference"] == {"presente": False, "archivos": []}


# ------------------------------------------------------------------ respaldo parcial
def test_partial_backup_not_announced_as_integral(tmp_path):
    root = make_root(tmp_path)
    (root / FINAL / "auditoria.json").unlink()
    cfg = make_cfg()
    with pytest.raises(pb.BundleError, match="parcial"):
        pb.export_bundle(root, tmp_path / "b1", cfg)
    man = pb.export_bundle(root, tmp_path / "b2", cfg, allow_partial=True)
    assert man["integro"] is False and man["faltantes"] == [f"{FINAL}/auditoria.json"]
    assert not pb.verify_bundle(tmp_path / "b2")["ok"]
    with pytest.raises(pb.BundleError, match="no integro"):
        pb.restore_bundle(tmp_path / "b2", tmp_path / "rest", root=root, cfg=cfg)
    assert not (tmp_path / "rest").exists()


# ------------------------------------------------------------------ ausente / alterado
def test_missing_altered_and_extra_files_in_bundle(tmp_path):
    root, cfg, _ = export(tmp_path)
    b = tmp_path / "bundle" / "files" / FINAL
    (b / "predictivo.json").write_text("{}", encoding="utf-8")
    bad = pb.verify_bundle(tmp_path / "bundle")["problemas"]
    assert any("predictivo.json" in p and "hash de bytes" in p for p in bad)
    (b / "simulacion.json").unlink()
    (b / "extra.txt").write_text("x", encoding="utf-8")
    bad = pb.verify_bundle(tmp_path / "bundle")["problemas"]
    assert any("simulacion.json: ausente" in p for p in bad) and any("extra.txt" in p for p in bad)
    with pytest.raises(pb.BundleError, match="no integro"):
        pb.restore_bundle(tmp_path / "bundle", tmp_path / "rest", root=root, cfg=cfg)
    assert not (tmp_path / "rest").exists()


def test_npz_same_bytes_different_logic_and_manifest_tamper_detected(tmp_path):
    root, cfg, _ = export(tmp_path)
    p = tmp_path / "bundle" / "files" / FINAL / "reales_bloque.npz"
    import numpy as np
    np.savez(p, x=np.arange(3))
    assert any("reales_bloque.npz" in x for x in pb.verify_bundle(tmp_path / "bundle")["problemas"])
    # alterar tambien el manifiesto para que coincida: solo lo detecta el sha256 externo registrado
    mp = tmp_path / "bundle" / pb.MANIFEST_NAME
    good = pb.sha256_file(mp)
    man = json.loads(mp.read_text(encoding="utf-8"))
    mp.write_text(json.dumps(man, indent=2), encoding="utf-8")
    with pytest.raises(pb.BundleError, match="alterado"):
        pb.restore_bundle(tmp_path / "bundle", tmp_path / "rest", root=root, cfg=cfg, expected_manifest_sha256=good)


def test_restored_copy_altered_after_restore_is_detected(tmp_path):
    root, cfg, man = export(tmp_path)
    rep = pb.restore_bundle(tmp_path / "bundle", tmp_path / "rest", root=root, cfg=cfg)
    assert rep["artefactos_ok"]
    (tmp_path / "rest" / FINAL / "predictivo.json").write_text("{}", encoding="utf-8")
    assert pb.verify_tree(tmp_path / "rest", man)


# ------------------------------------------------------------------ rutas inseguras
@pytest.mark.parametrize("rel", ["../x.json", "a/../../x", "/abs/x", "C:/x/y", "a\\b", "a//b", ".git/config", "a/.env",
                                 "a/.env.local", "a/session_token.json", "a/clave.pem", "", "a/./b"])
def test_unsafe_relative_paths_rejected(rel):
    with pytest.raises(pb.BundleError):
        pb.safe_rel(rel)


def test_safe_paths_accepted():
    assert pb.safe_rel("artifacts/private/final/estado.json") == "artifacts/private/final/estado.json"


def test_config_and_manifest_with_path_traversal_rejected(tmp_path):
    cfg = make_cfg()
    cfg["secciones"]["t12_final"].append("../fuera.json")
    p = tmp_path / "c.json"
    p.write_text(json.dumps(cfg), encoding="utf-8")
    with pytest.raises(pb.BundleError):
        pb.load_config(p)
    root, cfg, _ = export(tmp_path)
    mp = tmp_path / "bundle" / pb.MANIFEST_NAME
    man = json.loads(mp.read_text(encoding="utf-8"))
    man["archivos"][0]["ruta"] = "../../escape.txt"
    mp.write_text(json.dumps(man), encoding="utf-8")
    with pytest.raises(pb.BundleError, match="traversal"):
        pb.restore_bundle(tmp_path / "bundle", tmp_path / "rest", root=root, cfg=cfg)
    assert not (tmp_path / "escape.txt").exists() and not (tmp_path / "rest").exists()


def test_symlink_and_secret_files_never_included(tmp_path):
    root = make_root(tmp_path, runtime_reference=True)
    cfg = make_cfg()
    (root / RR / ".env").write_text("SECRETO=1", encoding="utf-8")
    with pytest.raises(pb.BundleError, match="prohibida"):
        pb.export_bundle(root, tmp_path / "b1", cfg)
    (root / RR / ".env").unlink()
    link = root / RR / "enlace"
    try:
        os.symlink(root / FINAL / "estado.json", link)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks no disponibles")
    with pytest.raises(pb.BundleError, match="enlace"):
        pb.export_bundle(root, tmp_path / "b2", cfg)


# ------------------------------------------------------------------ destino
def test_destination_rejections(tmp_path):
    root, cfg, _ = export(tmp_path)
    b = tmp_path / "bundle"
    nonempty = tmp_path / "ne"
    nonempty.mkdir()
    (nonempty / "a").write_text("x", encoding="utf-8")
    for dest, msg in [(nonempty, "no esta vacio"), (root, "no esta vacio"), (root / FINAL, "no esta vacio"),
                      (root / FINAL / "nuevo", "originales"), (root / "docs" / "nuevo", "originales"),
                      (b / "restaurado", "bundle"), (tmp_path, "contiene|no esta vacio")]:
        with pytest.raises(pb.BundleError, match=msg):
            pb.restore_bundle(b, dest, root=root, cfg=cfg)
    assert not (root / FINAL / "nuevo").exists() and not (b / "restaurado").exists()
    # originales intactos tras los rechazos
    assert (root / FINAL / "estado.json").is_file()
    empty = tmp_path / "vacio"
    empty.mkdir()
    assert pb.restore_bundle(b, empty, root=root, cfg=cfg)["artefactos_ok"]


# ------------------------------------------------------------------ prueba funcional
def test_functional_check_fails_when_state_incomplete_or_seal_mismatch(tmp_path):
    root = make_root(tmp_path)
    est = json.loads((root / FINAL / "estado.json").read_text(encoding="utf-8"))
    est["completa"] = False
    (root / FINAL / "estado.json").write_text(json.dumps(est), encoding="utf-8")
    cfg = make_cfg()
    pb.export_bundle(root, tmp_path / "b", cfg)         # hashes correctos, contenido funcionalmente invalido
    rep = pb.restore_bundle(tmp_path / "b", tmp_path / "r", root=root, cfg=cfg)
    assert rep["hash_bytes_logico_ok"] and rep["artefactos_ok"] is False
    assert any("estado.json" in p for p in rep["problemas"])
    root2 = make_root(tmp_path / "otro")
    (root2 / "docs" / "T12_SELLO.json").write_text(json.dumps({"sello_sha256": "0" * 64, "archivos": {}}), encoding="utf-8")
    pb.export_bundle(root2, tmp_path / "b2", cfg)
    rep2 = pb.restore_bundle(tmp_path / "b2", tmp_path / "r2", root=root2, cfg=cfg)
    assert rep2["artefactos_ok"] is False and any("T12_SELLO" in p for p in rep2["problemas"])


def test_functional_check_detects_tampered_sealed_manifest(tmp_path):
    root = make_root(tmp_path)
    cfg = make_cfg()
    mp = root / FINAL / "preparacion" / "manifiesto_preparacion.json"
    man = json.loads(mp.read_text(encoding="utf-8"))
    man["origen"] = "2026-08-15"                         # contenido distinto, sello sin recalcular
    mp.write_text(json.dumps(man), encoding="utf-8")
    pb.export_bundle(root, tmp_path / "b", cfg)
    rep = pb.restore_bundle(tmp_path / "b", tmp_path / "r", root=root, cfg=cfg)
    assert rep["artefactos_ok"] is False and any("sello" in p.lower() for p in rep["problemas"])


# ------------------------------------------------------------------ mantenimiento y consistencia fuerte (Mongo real)
def _db(mongo):
    db = mongo.new_db()
    make_source(db)
    return db


def test_maintenance_requires_confirmation_and_no_writers(mongo):
    db = _db(mongo)
    with pytest.raises(ar.ArchiveError, match="mantenimiento"):
        ar.check_maintenance(db, confirmed=False)
    assert ar.check_maintenance(db, confirmed=True)["jobs_running"] == 0
    db.jobs.insert_one({"job_id": "j2", "status": "running"})
    with pytest.raises(ar.ArchiveError, match="job"):
        ar.check_maintenance(db, confirmed=True)
    db.jobs.delete_one({"job_id": "j2"})
    db.scheduler_ticks.insert_one({"tick": 2, "status": "procesando"})
    with pytest.raises(ar.ArchiveError, match="tick"):
        ar.check_maintenance(db, confirmed=True)
    db.scheduler_ticks.delete_one({"tick": 2})
    db.runs.insert_one({"run_id": "stg", "status": "staging"})
    with pytest.raises(ar.ArchiveError, match="staging"):
        ar.check_maintenance(db, confirmed=True)


def _mutate_same_count(db):
    db.sales.update_one({"linea_id": "l3"}, {"$set": {"cantidad_base": 999}})


def test_same_count_mutation_during_export_detected_by_content_hash(mongo, tmp_path, monkeypatch):
    db = _db(mongo)
    real = ar._dump_collection
    state = {"done": False}

    def dump_then_mutate(coll, path):
        out = real(coll, path)
        if coll.name == "sales" and not state["done"]:
            state["done"] = True
            _mutate_same_count(coll.database)          # mismo conteo, distinto contenido, tras leer la coleccion
        return out
    monkeypatch.setattr(ar, "_dump_collection", dump_then_mutate)
    # el control debil (solo conteos) NO lo detecta
    ar.export_db(db, tmp_path / "debil")
    state["done"] = False
    db.sales.update_one({"linea_id": "l3"}, {"$set": {"cantidad_base": 3}})
    with pytest.raises(ar.ArchiveError, match="mismo conteo"):
        ar.export_db(db, tmp_path / "fuerte", strict_content=True)


def test_same_count_mutation_between_fingerprint_and_dump_detected(mongo, tmp_path, monkeypatch):
    db = _db(mongo)
    real = ar.collection_hash
    calls = {"n": 0}

    def hash_then_mutate(coll, flt=None):
        out = real(coll, flt)
        if coll.name == "sales" and calls["n"] == 0:
            calls["n"] += 1
            _mutate_same_count(coll.database)           # tras la huella previa, antes del volcado
        return out
    monkeypatch.setattr(ar, "collection_hash", hash_then_mutate)
    with pytest.raises(ar.ArchiveError, match="mismo conteo"):
        ar.export_db(db, tmp_path / "e", strict_content=True)


# ------------------------------------------------------------------ export-all / restore-all
def _export_all(mongo, tmp_path, root, cfg, **kw):
    db = _db(mongo)
    rec = br.export_all(mongo, db.name, tmp_path / "resp", root=root, cfg=cfg, maintenance_confirmed=True, **kw)
    return rec


def test_export_all_requires_maintenance_and_refuses_partial(mongo, tmp_path):
    root = make_root(tmp_path)
    cfg = make_cfg()
    db = _db(mongo)
    with pytest.raises(ar.ArchiveError, match="mantenimiento"):
        br.export_all(mongo, db.name, tmp_path / "r1", root=root, cfg=cfg)
    assert not (tmp_path / "r1").exists()
    (root / FINAL / "verificacion.json").unlink()
    with pytest.raises(pb.BundleError, match="parcial"):
        br.export_all(mongo, db.name, tmp_path / "r2", root=root, cfg=cfg, maintenance_confirmed=True)
    assert not (tmp_path / "r2").exists()
    rec = br.export_all(mongo, db.name, tmp_path / "r3", root=root, cfg=cfg, maintenance_confirmed=True, allow_partial=True)
    assert rec["bundle_integro"] is False and rec["bundle_faltantes"]
    res = br.restore_all(mongo, tmp_path / "r3", mongo.new_db("df_restore_t11b_").name, tmp_path / "dest", root=root, cfg=cfg)
    assert res["mongo_ok"] is True, (res["errores"], res.get("mongo"))
    assert res["artefactos_ok"] is False and res["recuperacion_integral_ok"] is False


def test_export_all_failure_leaves_no_partial_output(mongo, tmp_path, monkeypatch):
    root = make_root(tmp_path)
    cfg = make_cfg()
    db = _db(mongo)
    real = ar._dump_collection

    def mutate(coll, path):
        out = real(coll, path)
        if coll.name == "sales":
            _mutate_same_count(coll.database)
        return out
    monkeypatch.setattr(ar, "_dump_collection", mutate)
    with pytest.raises(ar.ArchiveError, match="mismo conteo"):
        br.export_all(mongo, db.name, tmp_path / "resp", root=root, cfg=cfg, maintenance_confirmed=True)
    assert not (tmp_path / "resp").exists()


def test_integral_recovery_reports_mongo_and_artifacts_separately(mongo, tmp_path):
    root = make_root(tmp_path, runtime_reference=True)
    cfg = make_cfg()
    rec = _export_all(mongo, tmp_path, root, cfg)
    assert rec["bundle_integro"] and rec["ventana_mantenimiento"]["confirmada"] and "fuerte" in rec["consistencia_mongo"]
    names = {p.name for p in (tmp_path / "resp" / "mongo").glob("*.ndjson.gz")}
    assert "sessions.ndjson.gz" not in names and "users.ndjson.gz" not in names
    res = br.restore_all(mongo, tmp_path / "resp", mongo.new_db("df_restore_t11b_").name, tmp_path / "dest", root=root, cfg=cfg)
    assert res["mongo_ok"] and res["artefactos_ok"] and res["recuperacion_integral_ok"], res
    assert res["bundle"]["hash_bytes_logico_ok"] and res["funcional"]["ok"]
    # artefacto alterado en el respaldo: mongo_ok sigue true, la recuperacion integral NO
    victim = tmp_path / "resp" / "bundle" / "files" / FINAL / "predictivo.json"
    victim.write_text("{}", encoding="utf-8")
    res2 = br.restore_all(mongo, tmp_path / "resp", mongo.new_db("df_restore_t11b_").name, tmp_path / "dest2", root=root, cfg=cfg)
    assert res2["mongo_ok"] is True and res2["artefactos_ok"] is False and res2["recuperacion_integral_ok"] is False
    assert not (tmp_path / "dest2").exists()
    shutil.rmtree(tmp_path / "dest", ignore_errors=True)


def test_cli_export_all_and_restore_all(mongo, tmp_path, monkeypatch, capsys):
    root = make_root(tmp_path)
    cfg = make_cfg()
    db = _db(mongo)
    monkeypatch.setattr(br, "get_client", lambda: mongo)
    monkeypatch.setattr(br, "ROOT", root)
    monkeypatch.setattr(pb, "load_config", lambda path=None: cfg)
    monkeypatch.setattr(br.pb, "load_config", lambda path=None: cfg)
    import pymongo
    monkeypatch.setattr(pymongo.MongoClient, "close", lambda self: None, raising=False)
    orig_export_all, orig_restore_all = br.export_all, br.restore_all
    monkeypatch.setattr(br, "export_all", lambda c, d, o, **kw: orig_export_all(c, d, o, root=root, cfg=cfg, **kw))
    monkeypatch.setattr(br, "restore_all", lambda c, s, d, t, **kw: orig_restore_all(c, s, d, t, root=root, cfg=cfg, **kw))
    assert br.main(["export-all", "--db", db.name, "--out", str(tmp_path / "x1")]) == 1      # sin --maintenance-confirmed
    assert br.main(["export-all", "--db", db.name, "--out", str(tmp_path / "x2"), "--maintenance-confirmed"]) == 0
    dst = mongo.new_db("df_restore_t11b_")
    assert br.main(["restore-all", "--from", str(tmp_path / "x2"), "--db", dst.name, "--dest", str(tmp_path / "d"),
                    "--report", str(tmp_path / "rep.json")]) == 0
    assert '"recuperacion_integral_ok": true' in capsys.readouterr().out
    assert json.loads(Path(tmp_path / "rep.json").read_text(encoding="utf-8"))["mongo_ok"] is True


def test_link_detection_logic_with_simulated_link(tmp_path, monkeypatch):
    """En Windows sin privilegios no se pueden crear symlinks: se simula la deteccion sobre un archivo de la lista."""
    root = make_root(tmp_path)
    cfg = make_cfg()
    target = (root / FINAL / "estado.json").resolve()
    monkeypatch.setattr(pb, "_is_link", lambda p: Path(p).resolve() == target)
    with pytest.raises(pb.BundleError, match="enlace"):
        pb.export_bundle(root, tmp_path / "b", cfg)
