"""Construye el paquete de referencia de RUNTIME de T07 (R14). Usa Git local SOLO durante la construccion.

    python -m scripts.build_runtime_reference [--out artifacts/private/runtime_reference] [--force]

Contenido (todo privado, fuera de Git y de la imagen; se monta de solo lectura en API y worker):
  artifacts/predicciones_folds.csv.gz, artifacts/simulacion_series.npz   (verificados contra T07_MANIFIESTO)
  files/docs/T07_MANIFIESTO.json, files/docs/T07_METRICAS.json           (blobs del commit aprobado)
  files/config/t07_config.json y files/<codigo T07>                      (blobs del commit del manifiesto)
  manifest_referencia.json                                               (indice: commits y sha256 normalizados)

El paquete no se autoriza por el hash del archivo actual: los blobs deben coincidir con los hashes aprobados
versionados en config/t08_publish.json y con codigo_sha256/config_sha256 del manifiesto. Sin Git en runtime.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

from pipeline.publish.runtime_reference import INDEX_NAME, SCHEMA, required_files
from pipeline.publish.source import (
    PROJECT_ROOT,
    SourceVerificationError,
    _git_show,
    _norm_sha,
    load_publish_config,
    resolve_entry,
    sha256_file,
    verify_code,
    verify_config,
    verify_reference,
)


def build_package(out: Path, *, root: Path | None = None, repo: Path | None = None, name: str = "t07",
                  force: bool = False) -> dict:
    root, repo = (root or PROJECT_ROOT), (repo or PROJECT_ROOT)
    entry = resolve_entry(name, load_publish_config(root / "config" / "t08_publish.json"))
    out = Path(out)
    if out.exists() and any(out.iterdir()):
        if not force:
            raise SourceVerificationError("el destino no esta vacio (use --force para reconstruir)")
        shutil.rmtree(out)
    manifest = json.loads((root / entry["manifest"]).read_text(encoding="utf-8"))
    ref = verify_reference(entry, root, repo)                    # actual == commit aprobado == hash versionado
    files = list(manifest.get("codigo_archivos") or entry["code_files"])
    verify_code(manifest, files, repo)                           # el codigo del commit del manifiesto es el registrado
    cfg_raw = verify_config(manifest, entry, repo)
    index_files: dict[str, str] = {}
    out.mkdir(parents=True, exist_ok=True)
    try:
        for rel in (entry["manifest"], entry["metrics"]):
            data = _git_show(repo, ref["commit"], rel)
            _put(out, f"files/{rel}", data, index_files)
        _put(out, f"files/{entry['config']}", cfg_raw, index_files)
        for f in files:
            _put(out, f"files/{f}", _git_show(repo, manifest["git_commit"], f), index_files)
        arts = {}
        for nm in entry["artifacts"]:
            src = root / entry["artifacts_dir"] / nm
            want = manifest["artefactos"][nm]["sha256"]
            if sha256_file(src) != want:
                raise SourceVerificationError(f"sha256 de {nm} no coincide con el manifiesto")
            dest = out / "artifacts" / nm
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)
            arts[f"artifacts/{nm}"] = want
        index_files.update(arts)
        assert set(index_files) == set(required_files(entry, files))
        index = {"schema": SCHEMA, "construido": datetime.now().astimezone().isoformat(timespec="seconds"),
                 "manifiesto": name, "approved_commit": ref["commit"], "code_commit": manifest["git_commit"],
                 "codigo_sha256": manifest["codigo_sha256"], "config_sha256": manifest["config_sha256"],
                 "files": dict(sorted(index_files.items())),
                 "nota": "Paquete privado de referencia T07. Solo lectura. No contiene .git, secretos ni ventas."}
        (out / INDEX_NAME).write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")
    except Exception:
        shutil.rmtree(out, ignore_errors=True)
        raise
    return index


def _put(out: Path, rel: str, data: bytes, index_files: dict) -> None:
    dest = out / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)                                       # bytes exactos del blob (sin conversion)
    index_files[rel] = _norm_sha(data)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Paquete de referencia de runtime T07")
    ap.add_argument("--out", type=Path, default=PROJECT_ROOT / "artifacts" / "private" / "runtime_reference")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)
    try:
        index = build_package(args.out, force=args.force)
    except SourceVerificationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"paquete listo: {args.out} ({len(index['files'])} archivos; commit aprobado {index['approved_commit'][:8]}, "
          f"codigo {index['code_commit'][:8]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
