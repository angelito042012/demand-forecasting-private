"""Paquete de referencia de RUNTIME para T07 (R14): verificacion sin Git ni repositorio.

El paquete (carpeta privada, montada de solo lectura) contiene los artefactos que el generador necesita, los
documentos aprobados, la configuracion y el CODIGO exacto del commit registrado en el manifiesto T07. Se
construye una vez con Git (scripts/build_runtime_reference.py) y se verifica en runtime sin Git:

  ancla de confianza  config/t08_publish.json -> approved_reference (commit + sha256 normalizados de
                      T07_MANIFIESTO y T07_METRICAS), que viaja VERSIONADA con el codigo de la imagen;
  cadena              T07_MANIFIESTO (hash del paquete == ancla) -> sha256 de artefactos, config_sha256 y
                      codigo_sha256 (se recalcula sobre el contenido del paquete);
  indice              manifest_referencia.json: debe coincidir con el contenido; no autoriza nada por si solo.

Un hash recalculado sobre archivos del paquete NO autoriza una referencia nueva: se compara con los valores
aprobados y versionados. Cualquier alteracion o ausencia produce SourceVerificationError antes de leer datos.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .source import (
    _COMMIT,
    _SHA,
    SourceVerificationError,
    VerifiedSource,
    _check_metrics,
    _norm_sha,
    assemble_source,
    sha256_file,
)

SCHEMA = "df-runtime-reference-1"
INDEX_NAME = "manifest_referencia.json"


def _safe(root: Path, rel: str) -> Path:
    p = (root / rel).resolve()
    if ".." in Path(rel).parts or Path(rel).is_absolute() or not p.is_relative_to(root.resolve()):
        raise SourceVerificationError("ruta fuera del paquete de referencia")
    return p


def required_files(entry: dict, manifest_files: list[str]) -> dict[str, str]:
    """Rutas relativas dentro del paquete -> clase ('artifact' | 'doc' | 'config' | 'code')."""
    req = {f"artifacts/{n}": "artifact" for n in entry["artifacts"]}
    req[f"files/{entry['manifest']}"] = "doc"
    req[f"files/{entry['metrics']}"] = "doc"
    req[f"files/{entry['config']}"] = "config"
    for f in manifest_files:
        req[f"files/{f}"] = "code"
    return req


def _read_json(path: Path, what: str) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SourceVerificationError(f"{what} ilegible en el paquete de referencia") from exc
    if not isinstance(data, dict):
        raise SourceVerificationError(f"{what} con formato inesperado")
    return data


def verify_and_load_runtime(entry: dict, ref_dir: Path) -> VerifiedSource:
    root = Path(ref_dir)
    if not root.is_dir():
        raise SourceVerificationError("el directorio del paquete de referencia no existe")
    root = root.resolve()
    index = _read_json(root / INDEX_NAME, INDEX_NAME)
    if index.get("schema") != SCHEMA:
        raise SourceVerificationError("esquema del indice del paquete de referencia desconocido")
    ref = entry.get("approved_reference") or {}
    if not _COMMIT.match(str(ref.get("commit", ""))):
        raise SourceVerificationError("falta la referencia aprobada (approved_reference.commit) en la configuracion")
    if index.get("approved_commit") != ref["commit"]:
        raise SourceVerificationError("el paquete de referencia declara un commit aprobado distinto al versionado")

    # 1) Anclaje de documentos aprobados: el CONTENIDO del paquete debe igualar el hash versionado.
    docs = {}
    for rel in (entry["manifest"], entry["metrics"]):
        want = ref.get("files", {}).get(rel, "")
        if not _SHA.match(want):
            raise SourceVerificationError(f"referencia aprobada sin hash para {rel}")
        p = _safe(root, f"files/{rel}")
        if not p.is_file():
            raise SourceVerificationError(f"paquete de referencia incompleto: falta {rel}")
        if _norm_sha(p.read_bytes()) != want:
            raise SourceVerificationError(f"{rel} no coincide con la referencia aprobada {ref['commit'][:8]}")
        docs[rel] = want
    manifest = _read_json(_safe(root, f"files/{entry['manifest']}"), "manifiesto T07")
    metrics = _read_json(_safe(root, f"files/{entry['metrics']}"), "metricas T07")
    if manifest.get("agosto_usado") is not False:
        raise SourceVerificationError("el manifiesto no declara agosto_usado=false")
    _check_metrics(metrics)

    # 2) Completitud del paquete antes de leer datos.
    files = list(manifest.get("codigo_archivos") or entry["code_files"])
    req = required_files(entry, files)
    missing = sorted(r for r in req if not _safe(root, r).is_file())
    if missing:
        raise SourceVerificationError(f"paquete de referencia incompleto: faltan {missing[:4]}")
    if index.get("code_commit") != manifest.get("git_commit"):
        raise SourceVerificationError("el commit de codigo del indice no coincide con el manifiesto T07")
    declared = index.get("files", {})
    for rel, kind in req.items():
        if kind in ("doc", "config", "code") and declared.get(rel) != _norm_sha(_safe(root, rel).read_bytes()):
            raise SourceVerificationError(f"{rel} no coincide con el indice del paquete de referencia")

    # 3) Artefactos contra el manifiesto T07 (anclado) y contra el indice.
    artifacts, paths = [], {}
    for name in entry["artifacts"]:
        p = _safe(root, f"artifacts/{name}")
        want = manifest.get("artefactos", {}).get(name, {}).get("sha256", "")
        if not _SHA.match(want):
            raise SourceVerificationError(f"artefacto {name} sin hash en el manifiesto")
        got = sha256_file(p)
        if got != want or declared.get(f"artifacts/{name}") != got:
            raise SourceVerificationError(f"sha256 de {name} no coincide con el manifiesto")
        artifacts.append({"name": name, "sha256": got, "size_bytes": p.stat().st_size})
        paths[name] = p
    metrics_path = _safe(root, f"files/{entry['metrics']}")
    artifacts.append({"name": Path(entry["metrics"]).name, "sha256": sha256_file(metrics_path),
                      "size_bytes": metrics_path.stat().st_size})

    # 4) Codigo: mismo calculo que verify_code, sobre el contenido del paquete (sin Git).
    h = hashlib.sha256()
    for f in files:
        h.update(f.encode() + b"\0" + _safe(root, f"files/{f}").read_bytes().replace(b"\r\n", b"\n") + b"\0")
    if h.hexdigest() != manifest.get("codigo_sha256"):
        raise SourceVerificationError("codigo_sha256 no coincide con el codigo del paquete de referencia")
    code = {"commit": str(manifest.get("git_commit", "")), "codigo_sha256": h.hexdigest(), "files": files}

    # 5) Configuracion T07.
    cfg_raw = _safe(root, f"files/{entry['config']}").read_bytes()
    accepted = {hashlib.sha256(cfg_raw).hexdigest(), hashlib.sha256(cfg_raw.replace(b"\n", b"\r\n")).hexdigest()}
    if manifest.get("config_sha256") not in accepted:
        raise SourceVerificationError("config_sha256 no coincide con la configuracion del paquete de referencia")

    reference = {"commit": ref["commit"], "files": docs}
    return assemble_source(entry, manifest, metrics, cfg_raw, artifacts, paths, reference, code)
