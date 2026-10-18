"""R14: paquete de referencia de runtime verificable SIN Git. Usa los artefactos T07 reales (solo lectura) y Git
local unicamente para CONSTRUIR el paquete en una carpeta temporal; la verificacion corre con PATH sin git."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from pipeline.generate import baseline
from pipeline.generate.config import GenerationError
from pipeline.publish.runtime_reference import INDEX_NAME, verify_and_load_runtime
from pipeline.publish.source import (
    RUNTIME_REFERENCE_ENV,
    SourceVerificationError,
    _norm_sha,
    verify_and_load,
)
from scripts.build_runtime_reference import build_package
from tests.publish.helpers import ARTIFACTS_OK, ENTRY, PROJECT_ROOT, real_source

pytestmark = pytest.mark.skipif(not ARTIFACTS_OK, reason="artefactos T07 reales no disponibles")


@pytest.fixture(scope="module")
def good_pkg(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("rr") / "pkg"
    build_package(out)
    return out


@pytest.fixture
def pkg(good_pkg, tmp_path) -> Path:
    dest = tmp_path / "pkg"
    shutil.copytree(good_pkg, dest)
    return dest


@pytest.fixture
def no_git(monkeypatch):
    monkeypatch.setenv("PATH", "")                       # sin git alcanzable
    assert shutil.which("git") is None


def _reindex(pkg: Path, rel: str) -> None:
    """Actualiza el indice con el contenido alterado: la cadena aprobada (manifiesto/hashes) debe detectarlo igual."""
    idx = json.loads((pkg / INDEX_NAME).read_text(encoding="utf-8"))
    idx["files"][rel] = _norm_sha((pkg / rel).read_bytes())
    (pkg / INDEX_NAME).write_text(json.dumps(idx), encoding="utf-8")


@pytest.fixture
def dev():
    return real_source()                                 # verificado con Git antes de ocultarlo


def test_paquete_correcto_verifica_sin_git_y_coincide_con_desarrollo(dev, good_pkg, no_git):
    src = verify_and_load_runtime(ENTRY, good_pkg)
    assert src.forecasts.equals(dev.forecasts)
    assert src.code == dev.code and src.manifest == dev.manifest
    assert {a["name"]: a["sha256"] for a in src.artifacts if a["name"] != "T07_METRICAS.json"} == \
           {a["name"]: a["sha256"] for a in dev.artifacts if a["name"] != "T07_METRICAS.json"}
    assert (src.sim["on_hand"] == dev.sim["on_hand"]).all()


def test_variable_de_entorno_usa_paquete_y_no_git(good_pkg, no_git, monkeypatch):
    monkeypatch.setenv(RUNTIME_REFERENCE_ENV, str(good_pkg))
    assert verify_and_load(ENTRY).entry["fold"] == "G4"
    monkeypatch.delenv(RUNTIME_REFERENCE_ENV)
    with pytest.raises(SourceVerificationError, match="git no disponible"):   # el camino de desarrollo exige Git
        verify_and_load(ENTRY)


def test_paquete_se_construye_sin_incluir_git_ni_secretos(good_pkg):
    names = [p.relative_to(good_pkg).as_posix() for p in good_pkg.rglob("*") if p.is_file()]
    assert not any(".git" in n.split("/") or n.endswith((".env", ".joblib")) for n in names)
    assert "manifest_referencia.json" in names and "artifacts/simulacion_series.npz" in names


@pytest.mark.parametrize("rel, match", [
    ("files/docs/T07_MANIFIESTO.json", "referencia aprobada"),
    ("files/docs/T07_METRICAS.json", "referencia aprobada"),
])
def test_manifiesto_o_metricas_alterados_aunque_el_indice_se_actualice(pkg, rel, match):
    p = pkg / rel
    p.write_bytes(p.read_bytes().replace(b"{", b"{ ", 1))
    _reindex(pkg, rel)
    with pytest.raises(SourceVerificationError, match=match):
        verify_and_load_runtime(ENTRY, pkg)


def test_config_alterada(pkg):
    rel = "files/config/t07_config.json"
    p = pkg / rel
    p.write_bytes(p.read_bytes() + b"\n ")
    _reindex(pkg, rel)
    with pytest.raises(SourceVerificationError, match="config_sha256"):
        verify_and_load_runtime(ENTRY, pkg)


def test_codigo_alterado(pkg):
    rel = "files/pipeline/forecast/baselines.py"
    p = pkg / rel
    p.write_bytes(p.read_bytes() + b"\n# alterado\n")
    _reindex(pkg, rel)
    with pytest.raises(SourceVerificationError, match="codigo_sha256"):
        verify_and_load_runtime(ENTRY, pkg)


def test_codigo_alterado_sin_actualizar_indice(pkg):
    p = pkg / "files/pipeline/sim/engine.py"
    p.write_bytes(p.read_bytes() + b"x")
    with pytest.raises(SourceVerificationError, match="indice"):
        verify_and_load_runtime(ENTRY, pkg)


@pytest.mark.parametrize("name", ["simulacion_series.npz", "predicciones_folds.csv.gz"])
def test_artefacto_alterado(pkg, name):
    p = pkg / "artifacts" / name
    data = bytearray(p.read_bytes())
    data[len(data) // 2] ^= 0xFF
    p.write_bytes(bytes(data))
    with pytest.raises(SourceVerificationError, match=f"sha256 de {name}"):
        verify_and_load_runtime(ENTRY, pkg)


@pytest.mark.parametrize("rel", ["artifacts/simulacion_series.npz", "artifacts/predicciones_folds.csv.gz",
                                 "files/pipeline/sim/engine.py", "files/config/t07_config.json",
                                 "files/docs/T07_METRICAS.json", "files/docs/T07_MANIFIESTO.json"])
def test_paquete_incompleto(pkg, rel):
    (pkg / rel).unlink()
    with pytest.raises(SourceVerificationError, match="incompleto"):
        verify_and_load_runtime(ENTRY, pkg)


def test_indice_ausente_o_commit_distinto_o_directorio_inexistente(pkg, tmp_path):
    with pytest.raises(SourceVerificationError, match="no existe"):
        verify_and_load_runtime(ENTRY, tmp_path / "nada")
    idx = json.loads((pkg / INDEX_NAME).read_text(encoding="utf-8"))
    idx["approved_commit"] = "0" * 40
    (pkg / INDEX_NAME).write_text(json.dumps(idx), encoding="utf-8")
    with pytest.raises(SourceVerificationError, match="commit aprobado distinto"):
        verify_and_load_runtime(ENTRY, pkg)
    (pkg / INDEX_NAME).unlink()
    with pytest.raises(SourceVerificationError, match="ilegible"):
        verify_and_load_runtime(ENTRY, pkg)


def test_ancla_versionada_distinta_rechaza_un_paquete_valido(good_pkg):
    """No se autoriza recalculando el hash del archivo del paquete: manda el ancla versionada."""
    entry = json.loads(json.dumps(ENTRY))
    entry["approved_reference"]["files"]["docs/T07_METRICAS.json"] = "0" * 64
    with pytest.raises(SourceVerificationError, match="referencia aprobada"):
        verify_and_load_runtime(entry, good_pkg)


# --- comportamiento del generador -----------------------------------------------------------------

def test_sin_variable_y_sin_git_la_referencia_es_opcional_con_motivo(no_git, monkeypatch):
    monkeypatch.delenv(RUNTIME_REFERENCE_ENV, raising=False)
    src, why = baseline._load_reference()
    assert src is None and "artefactos T07 no verificados" in why


def test_variable_definida_con_paquete_valido_carga(good_pkg, no_git, monkeypatch):
    monkeypatch.setenv(RUNTIME_REFERENCE_ENV, str(good_pkg))
    src, why = baseline._load_reference()
    assert src is not None and why == ""


def test_variable_definida_con_paquete_alterado_falla_claro_y_no_degrada(pkg, no_git, monkeypatch):
    p = pkg / "artifacts" / "simulacion_series.npz"
    p.write_bytes(p.read_bytes() + b"")
    monkeypatch.setenv(RUNTIME_REFERENCE_ENV, str(pkg))
    with pytest.raises(GenerationError) as exc:
        baseline._load_reference()
    assert exc.value.code == "REFERENCIA_INVALIDA" and "sha256 de simulacion_series.npz" in exc.value.message


def test_el_almacen_privado_no_se_sirve_por_web():
    text = (PROJECT_ROOT / "backend/app/hardening.py").read_text(encoding="utf-8")
    main = (PROJECT_ROOT / "backend/app/main.py").read_text(encoding="utf-8")
    assert "StaticFiles" not in text + main and ".mount(" not in main
    assert "runtime_reference" not in text + main and "artifacts" not in text
