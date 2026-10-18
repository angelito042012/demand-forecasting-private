"""T11B (R14): comprobaciones estaticas del montaje de solo lectura del paquete de referencia y de los limites de
recursos. La generacion real en el stack se ejecuto una vez con scripts privados (evidencia en
artifacts/private/t11b/generacion/, ver docs/T11B_GENERACION_CONTENEDOR.md); aqui no se levanta Docker."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOCKER = shutil.which("docker")
DUMMY = {k: "x" * 40 for k in ("MONGODB_URI", "MONGODB_DATABASE", "AUTH_SECRET", "MONGO_ROOT_USER",
                               "MONGO_ROOT_PASSWORD", "MONGO_APP_USER", "MONGO_APP_PASSWORD")}


def test_imagen_sin_referencia_ni_git_ni_artefactos():
    ignore = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    allowed = [line[1:] for line in ignore if line.startswith("!")]
    assert "**" in ignore and not any(a.split("/")[0] in ("artifacts", "data", ".git") for a in allowed)
    docker = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "runtime_reference" not in docker and "apt-get" not in docker and "git " not in docker.lower().replace("github", "")
    assert "DF_RUNTIME_REFERENCE_DIR" not in docker            # la ruta la define el despliegue, no la imagen


@pytest.mark.skipif(DOCKER is None, reason="docker no esta en PATH")
def test_compose_monta_referencia_solo_lectura_y_limites_equivalentes_a_bicep():
    r = subprocess.run([DOCKER, "compose", "config", "--format", "json"], cwd=ROOT, env={**os.environ, **DUMMY},
                       capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    assert r.returncode == 0, r.stderr[-400:]
    svc = json.loads(r.stdout)["services"]
    mounts = [v for v in svc["worker"]["volumes"] if v["target"] == "/reference"]
    assert len(mounts) == 1 and mounts[0]["read_only"] is True and mounts[0]["type"] == "bind"
    assert svc["worker"]["environment"]["DF_RUNTIME_REFERENCE_DIR"] == "/reference"
    assert not any(v["target"] == "/reference" for v in svc["api"]["volumes"])     # la API solo encola
    for name in ("api", "worker"):
        lim = svc[name]["deploy"]["resources"]["limits"]
        assert float(lim["cpus"]) == 0.5 and int(lim["memory"]) == 1024 ** 3, lim
        assert svc[name]["read_only"] is True and svc[name]["cap_drop"] == ["ALL"]


def test_bicep_declara_los_mismos_limites():
    text = (ROOT / "infra" / "main.bicep").read_text(encoding="utf-8")
    assert text.count("resources: { cpu: json('0.5'), memory: '1Gi' }") >= 2
