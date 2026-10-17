"""T10 §6: stop-local solo detiene un PID cuando hora de inicio y ejecutable coinciden con el registro."""
from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="scripts PowerShell de Windows")


def _spawn():
    return subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])


def _start_time_utc(pid: int) -> str:
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          f"(Get-Process -Id {pid}).StartTime.ToUniversalTime().ToString('o')"],
                         capture_output=True, text=True, check=True).stdout.strip()
    return out


def _stop(registry: Path) -> str:
    r = subprocess.run(["powershell", "-NoProfile", "-File", str(ROOT / "scripts" / "stop-local.ps1"),
                        "-RegistryPath", str(registry)], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return r.stdout


def _alive(p: subprocess.Popen) -> bool:
    return p.poll() is None


def test_matching_process_is_stopped_and_reused_pid_is_not(tmp_path):
    good, reused = _spawn(), _spawn()
    try:
        time.sleep(1)
        reg = tmp_path / "procesos.json"
        reg.write_text(json.dumps({"procesos": [
            {"name": "ok", "pid": good.pid, "start": _start_time_utc(good.pid), "exe": sys.executable},
            # PID "reutilizado": hora de inicio distinta (proceso de una sesion antigua)
            {"name": "reusado", "pid": reused.pid, "start": datetime(2020, 1, 1, tzinfo=UTC).isoformat(),
             "exe": sys.executable}]}), encoding="utf-8")
        out = _stop(reg)
        time.sleep(1)
        assert not _alive(good) and "ok: detenido" in out
        assert _alive(reused) and "NO se detiene" in out         # no se mata un PID ajeno
        assert not reg.exists()
    finally:
        for p in (good, reused):
            if _alive(p):
                p.kill()


def test_different_executable_is_not_stopped(tmp_path):
    p = _spawn()
    try:
        time.sleep(1)
        reg = tmp_path / "procesos.json"
        reg.write_text(json.dumps({"procesos": [{"name": "otro", "pid": p.pid, "start": _start_time_utc(p.pid),
                                                 "exe": "C:\\Windows\\System32\\notepad.exe"}]}), encoding="utf-8")
        assert "NO se detiene" in _stop(reg)
        assert _alive(p)
    finally:
        p.kill()


def test_missing_registry_is_a_noop(tmp_path):
    assert "No hay procesos registrados" in _stop(tmp_path / "no-existe.json")
