"""T12: verificacion de la congelacion y carga del motor de simulacion EXACTO del commit experimental.

* `verify_freeze` comprueba (sha256 normalizados CRLF->LF) el JSON congelado contra su `.sha256`, el documento contra su
  referencia previa (9596d26), la config T07 y los 14 archivos del modulo experimental contra el commit y los hashes
  registrados en la congelacion. Los archivos vivos que coinciden se usan tal cual; los que difieren se informan.
* El motor de simulacion vivo recibio endurecimiento posterior (d59703b: validacion de entradas y un balance diario
  adicional; mismas ecuaciones). Para los calculos experimentales congelados se usa la copia byte a byte (hash
  `09cddb7d...`) del commit e5466413 en `pipeline/final/frozen_code/engine_e5466413.py`.
* `importer.py` (vivo) difiere del congelado por la reserva de mes/valla de escritura de T10R: solo se usa para
  ingestion y `get_client`/`sha256_file`; T12 no importa ni escribe.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FROZEN_JSON = ROOT / "config" / "seleccion_congelada.json"
FROZEN_JSON_SHA = ROOT / "config" / "seleccion_congelada.sha256"
FROZEN_DOC = ROOT / "docs" / "SELECCION_CONGELADA.md"
T07_CONFIG = ROOT / "config" / "t07_config.json"
DOC_REFERENCE_COMMIT = "9596d26"
FROZEN_ENGINE_COPY = ROOT / "pipeline" / "final" / "frozen_code" / "engine_e5466413.py"
FROZEN_ENGINE_LIVE_PATH = "pipeline/sim/engine.py"


class FreezeError(RuntimeError):
    """La congelacion fue alterada o el codigo congelado no coincide: la evaluacion final no puede continuar."""


def norm_sha256(data: bytes) -> str:
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def file_sha256(path: Path) -> str:
    return norm_sha256(Path(path).read_bytes())


def git_blob(commit: str, path: str) -> bytes:
    out = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=ROOT, capture_output=True, check=False)
    if out.returncode != 0:
        raise FreezeError(f"no se pudo recuperar {path}@{commit}")
    return out.stdout


def load_frozen_config() -> dict:
    return json.loads(FROZEN_JSON.read_text(encoding="utf-8"))


def verify_freeze(*, root: Path = ROOT) -> dict:
    """Devuelve un informe con todas las verificaciones; lanza FreezeError si algo congelado no coincide."""
    report: dict = {"ok": False, "comprobaciones": {}}
    cfg = load_frozen_config()
    # 1. JSON congelado contra su .sha256 registrado
    want = FROZEN_JSON_SHA.read_text(encoding="utf-8").split()[0].lower()
    got = file_sha256(FROZEN_JSON)
    report["comprobaciones"]["json_congelado"] = {"esperado": want, "actual": got, "ok": want == got}
    # 2. documento contra su referencia previa a T10/T12
    ref = norm_sha256(git_blob(DOC_REFERENCE_COMMIT, "docs/SELECCION_CONGELADA.md"))
    doc = file_sha256(FROZEN_DOC)
    report["comprobaciones"]["documento_congelado"] = {"esperado": ref, "actual": doc, "referencia": DOC_REFERENCE_COMMIT,
                                                        "ok": ref == doc}
    # 3. config T07
    t07_want = cfg["comparador_experimental"]["config_t07_sha256"]
    t07_got = file_sha256(T07_CONFIG)
    report["comprobaciones"]["config_t07"] = {"esperado": t07_want, "actual": t07_got, "ok": t07_want == t07_got}
    # 4. 14 archivos del modulo experimental: contra el commit (git) y contra el estado vivo
    mod = cfg["comparador_experimental"]["modulo_experimental"]
    files = {}
    for rel, want_sha in mod["archivos_sha256"].items():
        in_git = norm_sha256(git_blob(mod["commit"], rel))
        live_path = root / rel
        live = file_sha256(live_path) if live_path.is_file() else None
        files[rel] = {"esperado": want_sha, "commit_ok": in_git == want_sha, "vivo_igual": live == want_sha,
                      "vivo": live}
    report["comprobaciones"]["archivos_experimentales"] = files
    # 5. copia aislada del motor
    eng = file_sha256(FROZEN_ENGINE_COPY)
    eng_want = mod["archivos_sha256"][FROZEN_ENGINE_LIVE_PATH]
    report["comprobaciones"]["motor_congelado_copia"] = {"esperado": eng_want, "actual": eng, "ok": eng == eng_want}
    bad = [k for k, v in report["comprobaciones"].items() if isinstance(v, dict) and "ok" in v and not v["ok"]]
    bad += [f"commit:{rel}" for rel, v in files.items() if not v["commit_ok"]]
    # el codigo vivo que se importa en el calculo (todos salvo importer y engine, reemplazados/no usados) debe coincidir
    used_live = [r for r in files if r not in ("pipeline/data/importer.py", FROZEN_ENGINE_LIVE_PATH, "scripts/run_t07.py")]
    bad += [f"vivo:{r}" for r in used_live if not files[r]["vivo_igual"]]
    report["no_coinciden_vivo_y_motivo"] = {
        r: ("endurecimiento T10R: reserva de mes/valla; no se usa en el calculo" if r == "pipeline/data/importer.py"
            else "endurecimiento d59703b (validacion de entradas); se usa la copia congelada" if r == FROZEN_ENGINE_LIVE_PATH
            else "script T07 no se ejecuta en T12") for r in files if not files[r]["vivo_igual"]}
    report["errores"] = bad
    report["ok"] = not bad
    if bad:
        raise FreezeError("congelacion alterada o codigo distinto del congelado: " + ", ".join(bad))
    return report


def load_frozen_engine():
    """Importa el motor de simulacion congelado (copia exacta) como modulo aislado."""
    if file_sha256(FROZEN_ENGINE_COPY) != load_frozen_config()["comparador_experimental"]["modulo_experimental"][
            "archivos_sha256"][FROZEN_ENGINE_LIVE_PATH]:
        raise FreezeError("la copia del motor congelado no coincide con el hash registrado")
    spec = importlib.util.spec_from_file_location("engine_e5466413", FROZEN_ENGINE_COPY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
