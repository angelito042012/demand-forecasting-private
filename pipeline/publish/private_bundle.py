"""T11B (R13): bundle privado verificable de los artefactos que Mongo no contiene (paquete T12, referencias T07, anclajes).

* Lista CERRADA en `config/t11b_private_bundle.json`; la entrada opcional `runtime_reference` se incluye solo si existe y
  va en una seccion separada del manifiesto. Nunca se copia nada fuera de la lista (ni .env, secretos, sesiones, .git).
* `export_bundle` copia a `<out>/files/<ruta relativa>` y escribe `bundle_manifest.json` (ruta, bytes, sha256 de bytes y,
  para NPZ, firma logica; version; fecha; exclusiones; `integro`). Un respaldo parcial lleva `integro=false` y falla
  salvo `allow_partial=True`. Se vuelve a hashear el ORIGEN tras copiarlo: si cambio durante el export, se aborta.
* `restore_bundle` restaura en una carpeta NUEVA y VACIA (distinta de originales y bundle), verifica hash de bytes y
  logico y ejecuta una prueba funcional SIN regenerar nada (`FinalRun._load_sealed` real, estado completo, salidas finales,
  sello vs manifiesto, referencias T07 con `_load_forecasts/_load_sim` y anclajes aprobados).
* No usa red ni Git en la restauracion (Git solo es opcional para la comprobacion extra de commits aprobados).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import time
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import numpy as np

BUNDLE_VERSION = "t11b-bundle-1"
MANIFEST_NAME = "bundle_manifest.json"
ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "t11b_private_bundle.json"
_DENY_NAME = re.compile(r"(^\.env)|password|passwd|token|secret|credential|session|cookie|\.pem$|\.key$|\.pfx$", re.IGNORECASE)
_SHA = re.compile(r"^[0-9a-f]{64}$")


class BundleError(RuntimeError):
    """Bundle rechazado: ruta insegura, destino invalido, archivo ausente/alterado o respaldo parcial."""


def load_config(path: Path | None = None) -> dict:
    cfg = json.loads((path or CONFIG_PATH).read_text(encoding="utf-8"))
    if cfg.get("version") != BUNDLE_VERSION:
        raise BundleError("version de configuracion de bundle desconocida")
    for rel in [r for lst in cfg["secciones"].values() for r in lst]:
        safe_rel(rel)
    return cfg


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_rel(rel: str) -> str:
    """Ruta relativa segura: sin absolutas, '..', unidades, barras invertidas, .git ni nombres de secretos."""
    if not isinstance(rel, str) or not rel or rel != rel.strip():
        raise BundleError(f"ruta invalida: {rel!r}")
    if "\\" in rel or rel.startswith("/") or re.match(r"^[A-Za-z]:", rel) or "\x00" in rel:
        raise BundleError(f"ruta no relativa/segura: {rel!r}")
    parts = rel.split("/")
    if any(p in ("", ".", "..") for p in parts):
        raise BundleError(f"path traversal o componente vacio en {rel!r}")
    if ".git" in parts or any(_DENY_NAME.search(p) for p in parts):
        raise BundleError(f"ruta prohibida (git/secreto): {rel!r}")
    return rel


def _is_link(p: Path) -> bool:
    return p.is_symlink() or (hasattr(p, "is_junction") and p.is_junction())


def _no_links(root: Path, p: Path) -> None:
    cur = p
    while True:
        if _is_link(cur):
            raise BundleError(f"enlace simbolico no permitido: {cur}")
        if cur == root or cur.parent == cur:
            return
        cur = cur.parent


def logical_of(path: Path) -> str | None:
    if path.suffix != ".npz":
        return None
    from pipeline.final.core import logical_signature
    with np.load(path, allow_pickle=False) as z:
        return logical_signature({k: z[k] for k in z.files})


def _copy_hash(src: Path, dst: Path) -> tuple[str, int]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    h, n = hashlib.sha256(), 0
    with open(src, "rb") as fi, open(dst, "wb") as fo:
        for chunk in iter(lambda: fi.read(1 << 20), b""):
            h.update(chunk)
            fo.write(chunk)
            n += len(chunk)
    return h.hexdigest(), n


# ------------------------------------------------------------------ lista cerrada
def plan(root: Path, cfg: dict) -> dict:
    """Resuelve la lista cerrada contra `root`: archivos presentes, faltantes obligatorios y seccion opcional."""
    root = Path(root).resolve()
    items, missing = [], []
    for sec, rels in cfg["secciones"].items():
        for rel in rels:
            safe_rel(rel)
            p = root / rel
            _no_links(root, p) if p.exists() or p.is_symlink() else None
            if p.is_file():
                items.append({"ruta": rel, "seccion": sec})
            else:
                missing.append(rel)
    rr_cfg = cfg.get("opcional", {}).get("runtime_reference")
    rr = {"presente": False, "archivos": []}
    if rr_cfg:
        d = root / safe_rel(rr_cfg["directorio"])
        if d.is_dir():
            _no_links(root, d)
            rr["presente"] = True
            for dp, dn, fn in os.walk(d, followlinks=False):
                for name in sorted(dn + fn):
                    if _is_link(Path(dp) / name):
                        raise BundleError(f"enlace simbolico en runtime_reference: {name}")
                for name in sorted(fn):
                    rel = (Path(dp) / name).relative_to(root).as_posix()
                    rr["archivos"].append({"ruta": safe_rel(rel), "seccion": "runtime_reference"})
            rr["archivos"].sort(key=lambda a: a["ruta"])
    return {"items": items, "faltantes": sorted(missing), "runtime_reference": rr}


# ------------------------------------------------------------------ export
def export_bundle(root: Path, out_dir: Path, cfg: dict | None = None, *, allow_partial: bool = False) -> dict:
    cfg = cfg or load_config()
    root, out_dir = Path(root).resolve(), Path(out_dir)
    pl = plan(root, cfg)
    if pl["faltantes"] and not allow_partial:
        raise BundleError("respaldo parcial: faltan " + ", ".join(pl["faltantes"]) + " (use allow_partial para un respaldo NO integro)")
    out_dir.mkdir(parents=True, exist_ok=True)
    if any(out_dir.iterdir()):
        raise BundleError("el directorio del bundle no esta vacio")
    t0 = time.perf_counter()
    entries = []
    for it in pl["items"] + pl["runtime_reference"]["archivos"]:
        src = root / it["ruta"]
        sha, size = _copy_hash(src, out_dir / "files" / it["ruta"])
        if sha256_file(src) != sha or src.stat().st_size != size:
            raise BundleError(f"{it['ruta']}: el origen cambio durante el export")
        e = {"ruta": it["ruta"], "seccion": it["seccion"], "bytes": size, "sha256": sha}
        lg = logical_of(src)
        if lg:
            e["logical_sha256"] = lg
        entries.append(e)
    lima = datetime.now(ZoneInfo("America/Lima"))
    rr = [e for e in entries if e["seccion"] == "runtime_reference"]
    man = {"version": BUNDLE_VERSION, "creado_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
           "creado_lima": lima.isoformat(timespec="seconds"), "integro": not pl["faltantes"], "faltantes": pl["faltantes"],
           "archivos": [e for e in entries if e["seccion"] != "runtime_reference"],
           "runtime_reference": {"presente": pl["runtime_reference"]["presente"], "archivos": rr},
           "exclusiones": list(cfg.get("exclusiones", [])), "config_sha256": hashlib.sha256(
               json.dumps(cfg, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
           "bytes_total": sum(e["bytes"] for e in entries), "n_archivos": len(entries),
           "segundos_export": round(time.perf_counter() - t0, 2)}
    (out_dir / MANIFEST_NAME).write_text(json.dumps(man, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return man


# ------------------------------------------------------------------ verificacion
def load_bundle_manifest(bundle_dir: Path, expected_sha256: str | None = None) -> dict:
    p = Path(bundle_dir) / MANIFEST_NAME
    if not p.is_file():
        raise BundleError("bundle sin bundle_manifest.json")
    if expected_sha256 is not None and sha256_file(p) != expected_sha256:
        raise BundleError("bundle_manifest.json alterado (sha256 distinto del registrado)")
    man = json.loads(p.read_text(encoding="utf-8"))
    if man.get("version") != BUNDLE_VERSION:
        raise BundleError("version de bundle desconocida")
    for e in man.get("archivos", []) + man.get("runtime_reference", {}).get("archivos", []):
        safe_rel(e["ruta"])
        if not _SHA.match(str(e.get("sha256", ""))):
            raise BundleError(f"manifiesto sin sha256 valido para {e.get('ruta')}")
    return man


def _entries(man: dict) -> list[dict]:
    return man["archivos"] + man.get("runtime_reference", {}).get("archivos", [])


def verify_tree(base: Path, man: dict, *, prefix: str = "") -> list[str]:
    """Hash de bytes y logico de cada archivo del manifiesto bajo `base/<prefix><ruta>`; detecta ausentes, alterados,
    enlaces y archivos EXTRA no listados. No lanza: devuelve los problemas."""
    base, bad = Path(base), []
    for e in _entries(man):
        p = base / prefix / e["ruta"]
        if _is_link(p):
            bad.append(f"{e['ruta']}: enlace simbolico")
        elif not p.is_file():
            bad.append(f"{e['ruta']}: ausente")
        elif p.stat().st_size != e["bytes"] or sha256_file(p) != e["sha256"]:
            bad.append(f"{e['ruta']}: hash de bytes distinto del manifiesto")
        elif e.get("logical_sha256") and logical_of(p) != e["logical_sha256"]:
            bad.append(f"{e['ruta']}: firma logica distinta del manifiesto")
    return bad


def verify_bundle(bundle_dir: Path, expected_manifest_sha256: str | None = None) -> dict:
    bundle_dir = Path(bundle_dir)
    man = load_bundle_manifest(bundle_dir, expected_manifest_sha256)
    bad = verify_tree(bundle_dir, man, prefix="files/")
    listed = {e["ruta"] for e in _entries(man)}
    files = bundle_dir / "files"
    if files.is_dir():
        for dp, _dn, fn in os.walk(files):
            for name in fn:
                rel = (Path(dp) / name).relative_to(files).as_posix()
                if rel not in listed:
                    bad.append(f"{rel}: archivo extra no listado en el manifiesto")
    if not man.get("integro", False):
        bad.append("el manifiesto declara integro=false (respaldo parcial): faltan " + ", ".join(man.get("faltantes", [])))
    return {"ok": not bad, "problemas": bad, "manifiesto": man}


# ------------------------------------------------------------------ restauracion
def _check_dest(dest: Path, bundle_dir: Path, root: Path, man: dict) -> Path:
    dest = Path(dest).resolve()
    bundle_dir, root = Path(bundle_dir).resolve(), Path(root).resolve()
    if dest.exists() and (not dest.is_dir() or any(dest.iterdir())):
        raise BundleError("el destino existe y no esta vacio")
    if dest == root or dest.is_relative_to(bundle_dir) or bundle_dir.is_relative_to(dest) or root.is_relative_to(dest):
        raise BundleError("el destino coincide con (o contiene/esta dentro de) el proyecto original o el bundle")
    for e in _entries(man):
        orig = (root / e["ruta"])
        if dest == orig.parent or dest.is_relative_to(orig.parent):
            raise BundleError("el destino esta dentro de un directorio de artefactos originales")
        if orig.resolve().is_relative_to(dest):
            raise BundleError("el destino contiene archivos originales")
    return dest


def restore_bundle(bundle_dir: Path, dest: Path, *, root: Path = ROOT, cfg: dict | None = None,
                   expected_manifest_sha256: str | None = None, functional: bool = True, git_repo: Path | None = None) -> dict:
    """Verifica el bundle, restaura en `dest` (nuevo y vacio), re-verifica bytes/logico y ejecuta la prueba funcional."""
    t0 = time.perf_counter()
    bundle_dir = Path(bundle_dir)
    man = load_bundle_manifest(bundle_dir, expected_manifest_sha256)
    dest = _check_dest(dest, bundle_dir, root, man)
    pre = verify_bundle(bundle_dir, expected_manifest_sha256)
    if not pre["ok"]:
        raise BundleError("bundle no integro, no se restaura: " + "; ".join(pre["problemas"][:5]))
    created = not dest.exists()
    dest.mkdir(parents=True, exist_ok=True)
    try:
        for e in _entries(man):
            sha, size = _copy_hash(bundle_dir / "files" / e["ruta"], _inside(dest, e["ruta"]))
            if sha != e["sha256"] or size != e["bytes"]:
                raise BundleError(f"{e['ruta']}: la copia restaurada no coincide con el manifiesto")
    except BaseException:
        if created:
            shutil.rmtree(dest, ignore_errors=True)
        raise
    bad = verify_tree(dest, man)
    seg_copy = round(time.perf_counter() - t0, 2)
    rep = {"destino": str(dest), "n_archivos": len(_entries(man)), "bytes": man["bytes_total"], "segundos_copia_verificacion": seg_copy,
           "hash_bytes_logico_ok": not bad, "problemas": list(bad), "integro_manifiesto": man["integro"]}
    if functional:
        fc = functional_check(dest, man, cfg or load_config(), git_repo=git_repo)
        rep["funcional"] = fc
        rep["problemas"] += fc["problemas"]
    rep["artefactos_ok"] = not rep["problemas"] and bool(man["integro"])
    rep["segundos_total"] = round(time.perf_counter() - t0, 2)
    return rep


def _inside(base: Path, rel: str) -> Path:
    p = (Path(base) / safe_rel(rel)).resolve()
    if not p.is_relative_to(Path(base).resolve()):
        raise BundleError(f"ruta fuera del destino: {rel}")
    return p


# ------------------------------------------------------------------ prueba funcional (sin regenerar nada)
def _norm_sha(data: bytes) -> str:
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def functional_check(dest: Path, man: dict, cfg: dict, *, git_repo: Path | None = None) -> dict:
    """Lee las salidas restauradas y valida sello, estado y referencias. Solo lectura sobre `dest`."""
    dest = Path(dest)
    probs: list[str] = []
    checks: dict = {}
    fin = dest / cfg["final_dir"]

    def js(rel: str):
        return json.loads((dest / rel).read_text(encoding="utf-8"))

    # 1. paquete final T12
    try:
        from pipeline.final.runner import PHASES, FinalRun
        sealed_man, fixed, init = FinalRun._load_sealed(SimpleNamespace(out=fin))   # funcion real del runner
        checks["load_sealed"] = {"ok": True, "sello_sha256": sealed_man["sello_sha256"],
                                 "predicciones_fijas_claves": len(fixed), "inicializacion_claves": len(init)}
        est = json.loads((fin / "estado.json").read_text(encoding="utf-8"))
        ph = {p: est["fases"].get(p, {}).get("estado") for p in PHASES}
        okst = est.get("completa") is True and all(v == "completa" for v in ph.values())
        checks["estado"] = {"completa": est.get("completa"), "fases": ph, "ok": okst}
        if not okst:
            probs.append("estado.json restaurado: completa!=true o fases incompletas")
        pred = json.loads((fin / "predictivo.json").read_text(encoding="utf-8"))
        sim = json.loads((fin / "simulacion.json").read_text(encoding="utf-8"))
        checks["salidas"] = {"predictivo_claves": sorted(pred)[:8], "simulacion_resultados": len(sim.get("resultados", {})),
                             "ok": bool(pred) and bool(sim.get("resultados"))}
        if not checks["salidas"]["ok"]:
            probs.append("predictivo.json/simulacion.json restaurados vacios")
        if cfg["funcional"].get("t12_sello") and (dest / cfg["funcional"]["t12_sello"]).is_file():
            seal = js(cfg["funcional"]["t12_sello"])
            ok = seal.get("sello_sha256") == sealed_man["sello_sha256"]
            ok = ok and all(seal["archivos"].get(k, {}).get("bytes_sha256") == v["bytes_sha256"]
                            for k, v in sealed_man["archivos"].items())
            checks["sello_vs_manifiesto"] = ok
            if not ok:
                probs.append("T12_SELLO.json no coincide con el manifiesto de preparacion restaurado")
        sel = cfg["funcional"].get("seleccion")
        if sel and (dest / sel["json"]).is_file() and sealed_man.get("seleccion_congelada_sha256"):
            raw = sha256_file(dest / sel["json"])
            checks["seleccion_congelada"] = raw == sealed_man["seleccion_congelada_sha256"] and \
                raw == (dest / sel["sha256"]).read_text(encoding="utf-8").split()[0]
            if not checks["seleccion_congelada"]:
                probs.append("seleccion_congelada.json no coincide con el sello/archivo .sha256")
    except Exception as exc:                # noqa: BLE001 - cualquier fallo es un problema informado
        checks["final_error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
        probs.append(f"paquete final restaurado no valido: {type(exc).__name__}: {str(exc)[:200]}")

    # 2. referencia T07
    t07 = cfg["funcional"].get("t07")
    if t07:
        try:
            from pipeline.publish import source as S
            manifest, metrics = js(t07["manifiesto"]), js(js(t07["publish_config"])["manifests"][t07["entrada"]]["metrics"])
            entry = js(t07["publish_config"])["manifests"][t07["entrada"]]
            if manifest.get("agosto_usado") is not False:
                raise S.SourceVerificationError("T07 no declara agosto_usado=false")
            S._check_metrics(metrics)
            arts = {}
            for name in entry["artifacts"]:
                p = dest / entry["artifacts_dir"] / name
                want = manifest["artefactos"][name]["sha256"]
                arts[name] = (p, sha256_file(p) == want)
                if not arts[name][1]:
                    probs.append(f"T07 {name}: sha256 distinto del manifiesto aprobado")
            ref = entry["approved_reference"]
            refok = {}
            for rel, want in ref["files"].items():
                refok[rel] = _norm_sha((dest / rel).read_bytes()) == want
                if not refok[rel]:
                    probs.append(f"{rel}: contenido normalizado distinto de la referencia aprobada")
            cfg_raw = (dest / t07["config_t07"]).read_bytes()
            cfg_ok = manifest.get("config_sha256") in {hashlib.sha256(cfg_raw).hexdigest(),
                                                      hashlib.sha256(cfg_raw.replace(b"\n", b"\r\n")).hexdigest()}
            if not cfg_ok:
                probs.append("config/t07_config.json restaurado no coincide con config_sha256 del manifiesto T07")
            fc = S._load_forecasts(arts["predicciones_folds.csv.gz"][0], entry, manifest)
            sm = S._load_sim(arts["simulacion_series.npz"][0], entry, manifest)
            checks["t07"] = {"artefactos_sha_ok": all(v[1] for v in arts.values()), "referencia_aprobada_ok": refok,
                             "config_ok": cfg_ok, "filas_fold": len(fc), "skus_simulacion": len(sm["skus"]),
                             "commit_referencia": ref["commit"]}
            if git_repo is not None:
                try:
                    S.verify_reference(entry, dest, Path(git_repo))
                    checks["t07"]["referencia_vs_commit_git"] = True
                except S.SourceVerificationError as exc:
                    checks["t07"]["referencia_vs_commit_git"] = False
                    probs.append(f"referencia vs commit Git: {exc}")
        except Exception as exc:            # noqa: BLE001
            checks["t07_error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
            probs.append(f"referencia T07 restaurada no valida: {type(exc).__name__}: {str(exc)[:200]}")

    # 3. runtime_reference (opcional): hashes del propio manifiesto de referencia, si los declara
    rr = man.get("runtime_reference", {})
    if rr.get("presente"):
        rcfg = cfg["opcional"]["runtime_reference"]
        mrel = f"{rcfg['directorio']}/{rcfg['manifiesto']}"
        info = {"archivos": len(rr["archivos"]), "manifiesto_presente": (dest / mrel).is_file(), "verificados": 0}
        if info["manifiesto_presente"]:
            info["manifiesto_sha256"] = sha256_file(dest / mrel)
            try:
                for rel, sha in _declared_hashes(json.loads((dest / mrel).read_text(encoding="utf-8"))):
                    p = (dest / rcfg["directorio"] / rel)
                    if p.is_file():
                        info["verificados"] += 1
                        if sha256_file(p) != sha:
                            probs.append(f"runtime_reference/{rel}: sha256 distinto del declarado en {rcfg['manifiesto']}")
            except ValueError:
                probs.append("runtime_reference: manifest_referencia.json ilegible")
        else:
            probs.append("runtime_reference presente sin manifest_referencia.json")
        checks["runtime_reference"] = info
    return {"ok": not probs, "problemas": probs, "comprobaciones": checks}


def _declared_hashes(obj) -> list[tuple[str, str]]:
    """Pares (ruta relativa, sha256) declarados en un manifiesto, tolerando {ruta: sha} o {ruta: {sha256|bytes_sha256}}
    bajo las claves archivos/files/artefactos o como lista de {ruta|name|path, sha256}."""
    out = []
    for key in ("archivos", "files", "artefactos"):
        v = obj.get(key) if isinstance(obj, dict) else None
        if isinstance(v, dict):
            for rel, h in v.items():
                sha = h if isinstance(h, str) else (h or {}).get("sha256") or (h or {}).get("bytes_sha256")
                if isinstance(sha, str) and _SHA.match(sha):
                    out.append((rel, sha))
        elif isinstance(v, list):
            for h in v:
                rel = h.get("ruta") or h.get("name") or h.get("path")
                sha = h.get("sha256") or h.get("bytes_sha256")
                if rel and isinstance(sha, str) and _SHA.match(sha):
                    out.append((rel, sha))
    return out
