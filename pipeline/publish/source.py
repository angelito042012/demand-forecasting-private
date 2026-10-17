"""Lectura y VERIFICACION de artefactos T07 antes de publicar (T08 §4 paso 1).

No reentrena, no carga modelos joblib, no lee agosto ni reference_v1. Verifica sha256 de
los artefactos contra el manifiesto, su estructura, y el codigo contra el commit
registrado en el manifiesto (git show, CRLF->LF); NO exige que el arbol actual coincida.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PUBLISHER_VERSION = "t08r-1"   # t08r-1: senales exactas (R05), anclaje de referencia y reemplazo de corridas
CSV_COLUMNS = ["fold", "entidad", "cohorte", "fecha", "h", "evaluable", "real", "pred_promedio_28",
               "pred_referencia_fija_0531", "pred_rf_distribuido"]
NPZ_ROLES = ("on_hand", "ordered", "received")
LAST_ALLOWED = "2026-07-31"
_SHA = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_SKU = re.compile(r"^[A-Za-z0-9._-]{1,32}$")


class SourceVerificationError(Exception):
    """Artefacto ausente, alterado o con estructura incoherente: no se publica."""


@dataclass
class VerifiedSource:
    entry: dict
    manifest: dict
    metrics: dict
    config_t07: dict
    forecasts: pd.DataFrame            # solo fold G4
    sim: dict                          # skus, costo, on_hand, ordered_cum, received_cum (arrays)
    artifacts: list = field(default_factory=list)   # {name, sha256, size_bytes}
    code: dict = field(default_factory=dict)
    source_fingerprint: str = ""
    paths: dict = field(default_factory=dict)       # nombre de artefacto -> ruta verificada (solo uso interno)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_publish_config(path: Path | None = None) -> dict:
    return json.loads((path or PROJECT_ROOT / "config" / "t08_publish.json").read_text(encoding="utf-8"))


def resolve_entry(name: str, cfg: dict) -> dict:
    manifests = cfg.get("manifests", {})
    if name not in manifests:
        raise SourceVerificationError(f"manifiesto '{name}' fuera de la lista cerrada")
    return manifests[name]


def _inside(root: Path, rel: str) -> Path:
    p = (root / rel).resolve()
    if not p.is_relative_to(root.resolve()):
        raise SourceVerificationError("ruta fuera del proyecto")
    return p


def _git_show(repo: Path, commit: str, rel: str) -> bytes:
    if not _COMMIT.match(commit) or rel.startswith("-") or ".." in Path(rel).parts:
        raise SourceVerificationError("commit o ruta de codigo invalidos")
    try:
        out = subprocess.run(["git", "-C", str(repo), "show", f"{commit}:{rel}"],
                             capture_output=True, timeout=30, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        raise SourceVerificationError("git no disponible para verificar el codigo") from exc
    if out.returncode != 0:
        raise SourceVerificationError(f"no se pudo leer {rel} en el commit registrado")
    return out.stdout


def verify_code(manifest: dict, files: list[str], repo: Path) -> dict:
    commit = str(manifest.get("git_commit", ""))
    h = hashlib.sha256()
    for f in files:
        h.update(f.encode() + b"\0" + _git_show(repo, commit, f).replace(b"\r\n", b"\n") + b"\0")
    if h.hexdigest() != manifest.get("codigo_sha256"):
        raise SourceVerificationError("codigo_sha256 no coincide con el commit registrado")
    return {"commit": commit, "codigo_sha256": h.hexdigest(), "files": list(files)}


def _norm_sha(data: bytes) -> str:
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def verify_reference(entry: dict, root: Path, repo: Path) -> dict:
    """Ancla el manifiesto y las metricas a la referencia versionada aprobada (commit + contenido normalizado).
    Un hash recalculado sobre el archivo actual NO verifica nada: se compara con el blob del commit aprobado
    y con el valor fijado en la configuracion de publicacion."""
    ref = entry.get("approved_reference")
    if not ref or not _COMMIT.match(str(ref.get("commit", ""))):
        raise SourceVerificationError("falta la referencia aprobada (approved_reference.commit) en la configuracion")
    out = {}
    for rel in (entry["manifest"], entry["metrics"]):
        want_cfg = ref.get("files", {}).get(rel, "")
        if not _SHA.match(want_cfg):
            raise SourceVerificationError(f"referencia aprobada sin hash para {rel}")
        at_commit = _norm_sha(_git_show(repo, ref["commit"], rel))
        current = _norm_sha(_inside(root, rel).read_bytes())
        if not (at_commit == want_cfg == current):
            raise SourceVerificationError(f"{rel} no coincide con la referencia aprobada {ref['commit'][:8]}")
        out[rel] = current
    return {"commit": ref["commit"], "files": out}


def verify_training_match(src: VerifiedSource, training_fingerprint: str, sources: list) -> None:
    """Antes de combinar catalogo/senales con G4: fingerprint y fuentes deben ser los del manifiesto aceptado.
    Falla ANTES de escribir si cambiaron las fuentes o el catalogo."""
    fold = src.manifest["folds_predictivos"][src.entry["fold"]]
    if training_fingerprint != fold["fingerprint"]:
        raise SourceVerificationError("el fingerprint de entrenamiento actual no coincide con el del fold aceptado")
    key = lambda s: (s["mes"], s["archivo"], s["sha256"])
    if sorted(map(key, sources)) != sorted(map(key, fold["fuentes"])):
        raise SourceVerificationError("las fuentes aprobadas actuales no coinciden con las del manifiesto aceptado")


def verify_config(manifest: dict, entry: dict, repo: Path) -> bytes:
    raw = _git_show(repo, str(manifest.get("git_commit", "")), entry["config"])
    accepted = {hashlib.sha256(raw).hexdigest(), hashlib.sha256(raw.replace(b"\n", b"\r\n")).hexdigest()}
    if manifest.get("config_sha256") not in accepted:
        raise SourceVerificationError("config_sha256 no coincide con el commit registrado")
    return raw


def _load_forecasts(path: Path, entry: dict, manifest: dict) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"entidad": str, "fold": str, "cohorte": str, "fecha": str})
    if list(df.columns) != CSV_COLUMNS:
        raise SourceVerificationError("columnas de predicciones_folds inesperadas")
    if df["fecha"].max() > LAST_ALLOWED:
        raise SourceVerificationError("el CSV contiene fechas posteriores a 2026-07-31")
    g = df[df["fold"] == entry["fold"]].copy()
    fold = manifest["folds_predictivos"][entry["fold"]]
    if fold["corte"] != entry["cutoff"]:
        raise SourceVerificationError("corte del fold distinto al configurado")
    n_ent = g["entidad"].nunique()
    if n_ent != fold["skus_conocidos"] or len(g) != 21 * n_ent:
        raise SourceVerificationError("conteo de entidades/filas del fold incoherente con el manifiesto")
    if g.duplicated(["entidad", "fecha"]).any():
        raise SourceVerificationError("filas duplicadas (entidad, fecha)")
    if g["fecha"].min() != entry["target_start"] or g["fecha"].max() != entry["target_end"]:
        raise SourceVerificationError("rango de fechas objetivo incoherente")
    cut = date.fromisoformat(entry["cutoff"])
    hh = pd.to_datetime(g["fecha"]).dt.date.map(lambda d: (d - cut).days).to_numpy()
    if not np.array_equal(hh, g["h"].to_numpy()) or g["h"].min() != 1 or g["h"].max() != 21:
        raise SourceVerificationError("h incoherente con fecha-corte")
    if not g["entidad"].map(lambda e: e.count("|") == 1 and bool(_SKU.match(e.split("|")[0]))).all():
        raise SourceVerificationError("entidad con formato inesperado")
    if not set(g["cohorte"]) <= {"primaria", "historia_corta"}:
        raise SourceVerificationError("cohorte desconocida")
    preds = g[["pred_promedio_28", "pred_rf_distribuido"]].to_numpy(float)
    if not np.isfinite(preds).all() or (preds < 0).any() or (g["real"] < 0).any():
        raise SourceVerificationError("predicciones o reales no finitos/negativos")
    if g.groupby("entidad")["pred_promedio_28"].nunique().max() != 1:
        raise SourceVerificationError("pred_promedio_28 no es constante por SKU")
    g["evaluable"] = g["evaluable"].astype(bool)
    return g.sort_values(["entidad", "fecha"]).reset_index(drop=True)


def _load_sim(path: Path, entry: dict, manifest: dict, origin: date | None = None) -> dict:
    """Instantanea de la trayectoria simulada al cierre de `origin` (por defecto el corte del fold: indice
    natural = origen - sim_start). Un origen distinto se admite solo dentro de los dias del escenario."""
    key = entry["scenario_key"]
    days_total = int(manifest["simulacion"]["dias"])
    if origin is None:
        idx = int(entry["snapshot_index"])
        origin = date.fromisoformat(entry["cutoff"])
    else:
        idx = (origin - date.fromisoformat(entry["sim_start"])).days
        if not 0 <= idx < days_total:
            raise SourceVerificationError("origen fuera de la ventana de la simulacion")
    if (origin - date.fromisoformat(entry["sim_start"])).days != idx:
        raise SourceVerificationError("indice de snapshot incoherente con las fechas")
    with np.load(path, allow_pickle=False) as z:
        need = ["skus", "costo", "demanda"] + [f"{key}__{r}" for r in NPZ_ROLES]
        missing = [k for k in need if k not in z.files]
        if missing:
            raise SourceVerificationError(f"faltan claves en el NPZ: {missing}")
        skus, costo = z["skus"].astype(str), z["costo"].astype(float)
        n = manifest["simulacion"]["universo_skus"]
        days = manifest["simulacion"]["dias"]
        if skus.shape != (n,) or costo.shape != (n,) or z["demanda"].shape != (n, days):
            raise SourceVerificationError("dimensiones del NPZ incoherentes con el manifiesto")
        if len(set(skus.tolist())) != n or not np.isfinite(costo).all() or (costo <= 0).any():
            raise SourceVerificationError("skus duplicados o costos invalidos")
        arrs = {}
        for r in NPZ_ROLES:
            a = z[f"{key}__{r}"]
            if a.shape != (days, n) or a.dtype.kind not in "iu" or (a < 0).any():
                raise SourceVerificationError(f"serie {r} invalida")
            arrs[r] = a
        upto = idx + 1
        ordered_cum = arrs["ordered"][:upto].sum(axis=0).astype(np.int64)
        received_cum = arrs["received"][:upto].sum(axis=0).astype(np.int64)
        if (ordered_cum < received_cum).any():
            raise SourceVerificationError("recepciones acumuladas exceden pedidos acumulados")
        return {"skus": skus, "costo": costo, "on_hand": arrs["on_hand"][idx].astype(np.int64),
                "ordered_cum": ordered_cum, "received_cum": received_cum}


def _check_metrics(metrics: dict) -> None:
    for k in ("predictivo", "simulacion", "diferencias"):
        if k not in metrics:
            raise SourceVerificationError(f"T07_METRICAS sin seccion {k}")
    expected = {f"L{L}_S{S}|{p}" for L in (3, 7, 14) for S in (0, 7, 14)
                for p in ("referencia_fija", "promedio_28", "rf_categoria_distribuido")}
    if set(metrics["simulacion"]) != expected:
        raise SourceVerificationError("simulacion: no son las 27 combinaciones esperadas")
    if not {"sku", "categoria", "seleccion", "cobertura"} <= set(metrics["predictivo"]):
        raise SourceVerificationError("predictivo incompleto")


def verify_and_load(entry: dict, root: Path | None = None, *, code_repo: Path | None = None) -> VerifiedSource:
    root = (root or PROJECT_ROOT).resolve()
    repo = code_repo or PROJECT_ROOT
    try:
        manifest = json.loads(_inside(root, entry["manifest"]).read_text(encoding="utf-8"))
        metrics = json.loads(_inside(root, entry["metrics"]).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SourceVerificationError("manifiesto o metricas ilegibles") from exc
    if manifest.get("agosto_usado") is not False:
        raise SourceVerificationError("el manifiesto no declara agosto_usado=false")
    _check_metrics(metrics)
    artifacts, paths = [], {}
    for name in entry["artifacts"]:
        p = _inside(root, f"{entry['artifacts_dir']}/{name}")
        want = manifest.get("artefactos", {}).get(name, {}).get("sha256", "")
        if not _SHA.match(want) or not p.is_file():
            raise SourceVerificationError(f"artefacto {name} ausente o sin hash en el manifiesto")
        got = sha256_file(p)
        if got != want:
            raise SourceVerificationError(f"sha256 de {name} no coincide con el manifiesto")
        artifacts.append({"name": name, "sha256": got, "size_bytes": p.stat().st_size})
        paths[name] = p
    reference = verify_reference(entry, root, repo)
    metrics_path = _inside(root, entry["metrics"])
    artifacts.append({"name": Path(entry["metrics"]).name, "sha256": sha256_file(metrics_path),
                      "size_bytes": metrics_path.stat().st_size})
    files = manifest.get("codigo_archivos") or entry["code_files"]
    code = verify_code(manifest, files, repo)
    cfg_raw = verify_config(manifest, entry, repo)
    cfg_t07 = json.loads(cfg_raw.decode("utf-8"))
    forecasts = _load_forecasts(paths["predicciones_folds.csv.gz"], entry, manifest)
    sim = _load_sim(paths["simulacion_series.npz"], entry, manifest)
    if not set(sim["skus"].tolist()) <= set(forecasts["entidad"].str.split("|").str[0]):
        raise SourceVerificationError("SKU del NPZ ausentes en el fold publicado")
    fp = hashlib.sha256(json.dumps({
        "v": PUBLISHER_VERSION, "arts": artifacts, "cfg": manifest["config_sha256"],
        "code": code["codigo_sha256"], "commit": code["commit"], "scenario": entry["scenario_id"],
        "fold": entry["fold"], "cutoff": entry["cutoff"], "ref": reference}, sort_keys=True).encode()).hexdigest()
    return VerifiedSource(entry, manifest, metrics, cfg_t07, forecasts, sim, artifacts, code, fp, paths=paths)


def load_snapshot(src: VerifiedSource, origin: date) -> dict:
    """Snapshot de la simulacion T07 al cierre de `origin` (indice = origen - 2026-06-01), con las mismas
    comprobaciones que la corrida historica (checksum ya verificado en `verify_and_load`, universo, dimensiones,
    transito = pedidos - recepciones acumulados hasta ese dia). Devuelve ademas el indice natural."""
    path = src.paths.get("simulacion_series.npz")
    if path is None:
        raise SourceVerificationError("artefacto de simulacion no verificado")
    if origin == date.fromisoformat(src.entry["cutoff"]):
        sim = src.sim
    else:
        sim = _load_sim(path, src.entry, src.manifest, origin)
    if len(sim["skus"]) != int(src.manifest["simulacion"]["universo_skus"]):
        raise SourceVerificationError("universo de la simulacion incoherente con el manifiesto")
    return {**sim, "index": (origin - date.fromisoformat(src.entry["sim_start"])).days}
