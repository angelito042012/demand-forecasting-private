"""T11A: empaquetado en contenedores. Parte estatica siempre; el smoke del stack (RUN_CONTAINER_SMOKE=1) usa
Docker local, una base temporal propia del Mongo del compose (volumen nombrado, se elimina al final), secretos
aleatorios generados en el momento y datos sinteticos. No toca demand_forecasting_v2/_dev ni la red externa."""
from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import subprocess
import time
import uuid
from datetime import datetime
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "artifacts" / "private" / "t11a" / "contenedores"
DOCKER = shutil.which("docker")
PORT = int(os.environ.get("DF_PROXY_PORT", "18443"))
BASE = f"https://localhost:{PORT}"
ORIGIN = BASE
DUMMY_ENV = {k: "x" * 40 for k in ("MONGODB_URI", "MONGODB_DATABASE", "AUTH_SECRET", "MONGO_ROOT_USER",
                                   "MONGO_ROOT_PASSWORD", "MONGO_APP_USER", "MONGO_APP_PASSWORD")}


# ---------------------------------------------------------------- estatica (sin daemon)

def test_dockerfile_usuario_no_root_healthcheck_sin_env():
    text = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert re.search(r"^USER app$", text, re.MULTILINE) and "useradd --system --uid 10001" in text
    assert "HEALTHCHECK" in text and "/api/v1/health" in text
    assert "npm ci" in text and "ng build --configuration production" in text
    assert "python:3.12-slim" in text and "requirements.lock.txt" in text
    assert not re.search(r"^(COPY|ADD)\s.*\.env", text, re.MULTILINE) and "COPY . " not in text
    assert "ENTRYPOINT" in text and 'CMD ["api"]' in text


def test_dockerignore_excluye_datos_y_secretos():
    ignore = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    assert "**" in ignore                                       # lista blanca: todo excluido salvo lo listado
    allowed = [line[1:] for line in ignore if line.startswith("!")]
    for forbidden in ("data", "artifacts", ".git", ".venv", "node_modules", "docs", "tests"):
        assert not any(a.split("/")[0] == forbidden for a in allowed), forbidden
    assert "**/.env" in ignore


def test_compose_texto_sin_secretos():
    text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    for forbidden in ("mongodb://", "password: ", ".env"):
        assert forbidden not in text
    for line in text.splitlines():
        if re.search(r"(PASSWORD|SECRET|MONGODB_URI)\s*:", line):
            assert "${" in line, line                       # solo referencias a variables, nunca valores
    assert not (ROOT / ".env.production").exists()


@pytest.mark.skipif(DOCKER is None, reason="docker no esta en PATH")
def test_compose_config_valida_con_variables_ficticias():
    env = {**os.environ, **DUMMY_ENV, "MONGODB_URI": "mongodb://u:p@mongo:27017/x"}
    r = subprocess.run([DOCKER, "compose", "config", "--quiet"], cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    assert r.returncode == 0, r.stderr[-500:]
    r = subprocess.run([DOCKER, "compose", "config", "--quiet"], cwd=ROOT, env={k: v for k, v in os.environ.items()
                       if k not in DUMMY_ENV}, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    assert r.returncode != 0 and "required variable" in r.stderr    # sin secretos no arranca
    r = subprocess.run([DOCKER, "compose", "config", "--format", "json"], cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    cfg = json.loads(r.stdout)["services"]
    assert not cfg["mongo"].get("ports") and not cfg["worker"].get("ports") and not cfg["api"].get("ports")
    assert all(p["host_ip"] == "127.0.0.1" for p in cfg["proxy"]["ports"])
    assert json.loads(r.stdout)["networks"]["data"]["internal"] is True
    assert cfg["api"]["environment"]["TRUSTED_PROXIES"] == "172.31.250.2/32"
    assert cfg["worker"]["environment"]["DF_UPLOADS_DIR"] == cfg["api"]["environment"]["DF_UPLOADS_DIR"]
    assert "scheduler" not in cfg                               # perfil opt-in: no se levanta por defecto


# ---------------------------------------------------------------- smoke del stack (opt-in)

smoke = pytest.mark.skipif(os.environ.get("RUN_CONTAINER_SMOKE") != "1" or DOCKER is None,
                           reason="smoke de contenedores: RUN_CONTAINER_SMOKE=1 y Docker disponible")


class Stack:
    def __init__(self):
        suffix = uuid.uuid4().hex[:8]
        self.project = f"df-t11a-{suffix}"
        self.db = f"df_test_t11a_{suffix}"
        app_pw = secrets.token_urlsafe(24)
        self.admin_pw = secrets.token_urlsafe(18)
        self.reader_pw = secrets.token_urlsafe(18)
        self.env = {**os.environ, "DF_PROXY_PORT": str(PORT), "ALLOWED_ORIGINS": ORIGIN,
                    "MONGODB_DATABASE": self.db, "MONGO_ROOT_USER": "root_" + suffix,
                    "MONGO_ROOT_PASSWORD": secrets.token_urlsafe(24), "MONGO_APP_USER": "dfapp",
                    "MONGO_APP_PASSWORD": app_pw, "AUTH_SECRET": secrets.token_urlsafe(48),
                    "MONGODB_URI": f"mongodb://dfapp:{app_pw}@mongo:27017/{self.db}?authSource={self.db}"}
        self.secrets = [self.env[k] for k in ("MONGO_ROOT_PASSWORD", "MONGO_APP_PASSWORD", "AUTH_SECRET")] + [
            self.admin_pw, self.reader_pw]
        self.transcript: list[dict] = []

    def compose(self, *args, check=True, extra_env=None, input=None, timeout=900):
        env = {**self.env, **(extra_env or {})}
        r = subprocess.run([DOCKER, "compose", "-p", self.project, *args], cwd=ROOT, env=env, capture_output=True, encoding="utf-8", errors="replace",
                           text=True, timeout=timeout, input=input, check=False)
        if check and r.returncode != 0:
            raise AssertionError(f"compose {args[0]} fallo: {self.scrub(r.stderr)[-800:]}")
        return r

    def scrub(self, text: str) -> str:
        for s in self.secrets:
            text = text.replace(s, "***")
        return text

    def record(self, name: str, ok: bool, detail: str = ""):
        self.transcript.append({"check": name, "ok": bool(ok), "detail": self.scrub(str(detail))[:300]})
        assert ok, f"{name}: {detail}"

    def wait_health(self, seconds=120):
        end = time.time() + seconds
        while time.time() < end:
            try:
                r = httpx.get(BASE + "/api/v1/health", verify=False, timeout=3)
                if r.status_code == 200 and r.json().get("database") == "ok":
                    return r.json()
            except httpx.HTTPError:
                pass
            time.sleep(2)
        raise AssertionError("el stack no quedo sano a tiempo")

    def create_user(self, name, role, password):
        r = subprocess.run([DOCKER, "compose", "-p", self.project, "exec", "-T", "-e", "DF_NEW_PASSWORD", "api", "df-entrypoint",
                            "cli", "create-user", "--username", name, "--role", role], cwd=ROOT,
                           env={**self.env, "DF_NEW_PASSWORD": password}, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
        assert r.returncode == 0, self.scrub(r.stdout + r.stderr)[-300:]
        assert password not in r.stdout + r.stderr


def login(client, user, password, **headers):
    return client.post("/api/v1/auth/login", json={"username": user, "password": password},
                       headers={"Origin": ORIGIN, **headers})


def make_xlsx() -> bytes:
    from tests.backend.test_t10_api import make_xlsx as build
    return build()


@smoke
def test_smoke_stack_local():
    stack = Stack()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    started = datetime.now().astimezone().isoformat(timespec="seconds")
    try:
        stack.compose("up", "-d", "--build")
        health = stack.wait_health()
        stack.record("health via proxy TLS", health["status"] == "ok" and health["environment"] == "production", health)
        stack.create_user("admin1", "admin", stack.admin_pw)
        stack.create_user("lector1", "lector", stack.reader_pw)
        stack.record("usuarios por CLI sin imprimir contrasena", True)

        with httpx.Client(base_url=BASE, verify=False, timeout=20) as c:
            r = c.get("/api/v1/health")
            for h in ("x-content-type-options", "x-frame-options", "content-security-policy", "strict-transport-security"):
                stack.record(f"cabecera {h}", h in r.headers)
            for route in ("/", "/corridas", "/pronosticos", "/recomendaciones"):
                r = c.get(route)
                stack.record(f"ruta Angular recargable {route}", r.status_code == 200 and "<app-root" in r.text, r.status_code)
            r = c.get("/api/v1/ruta-desconocida")
            stack.record("/api desconocida -> JSON 404", r.status_code == 404 and r.json()["error"]["code"] == "NO_ENCONTRADO"
                         and "<app-root" not in r.text, r.text[:100])
            r = login(c, "admin1", stack.admin_pw)
            cookie = r.headers.get("set-cookie", "").lower()
            stack.record("login admin", r.status_code == 200, r.status_code)
            stack.record("cookie Secure+HttpOnly+SameSite=Strict",
                         "secure" in cookie and "httponly" in cookie and "samesite=strict" in cookie, cookie[:20])
            csrf = r.json()["csrf_token"]
            stack.record("mutacion sin CSRF rechazada", c.post("/api/v1/imports", files={"file": ("a.xlsx", b"x")},
                         headers={"Origin": ORIGIN}).status_code == 403)

            data = make_xlsx()
            r = c.post("/api/v1/imports", files={"file": ("sintetico_junio.xlsx", data, "application/octet-stream")},
                       headers={"Origin": ORIGIN, "X-CSRF-Token": csrf})
            stack.record("subida aceptada y encolada", r.status_code in (200, 201, 202), f"{r.status_code} {r.text[:120]}")
            job_id = r.json().get("job", {}).get("id") or r.json().get("job_id") or r.json().get("id")
            stack.record("respuesta con id de trabajo", bool(job_id), list(r.json())[:6])
            status = ""
            for _ in range(60):
                status = c.get(f"/api/v1/jobs/{job_id}").json().get("status", "")
                if status not in ("queued", "running"):
                    break
                time.sleep(2)
            stack.record("worker proceso el trabajo (estado terminal)", status in ("completed",), status)

        # X-Forwarded-For variable no evita el limite (usuario distinto del admin ya autenticado)
        with httpx.Client(base_url=BASE, verify=False, timeout=20) as c2:
            codes = [login(c2, "lector1", "incorrecta-xxx-" + str(i), **{"X-Forwarded-For": f"198.51.100.{20 + i}"}).status_code
                     for i in range(8)]
            stack.record("XFF variable no evita el limite de login", codes[:5] == [401] * 5 and set(codes[5:]) == {429}, codes)

        # reinicio/reemplazo de contenedores conserva subidas y trabajos
        listing_before = stack.compose("exec", "-T", "worker", "ls", "/data/uploads").stdout.split()
        stack.record("la subida esta en el volumen compartido", len(listing_before) == 1 and listing_before[0].endswith(".xlsx"), listing_before)
        stack.compose("up", "-d", "--force-recreate", "--no-deps", "api", "worker")
        stack.wait_health()
        listing_after = stack.compose("exec", "-T", "worker", "ls", "/data/uploads").stdout.split()
        stack.record("reemplazo api/worker conserva subidas", listing_after == listing_before, listing_after)
        with httpx.Client(base_url=BASE, verify=False, timeout=20) as c3:
            login(c3, "admin1", stack.admin_pw)
            jobs = c3.get("/api/v1/jobs").json()
            total = jobs.get("total", len(jobs.get("items", [])))
            stack.record("trabajos persisten tras reemplazo", total >= 1, total)
        stack.compose("down")                                    # sin -v: conserva volumenes
        stack.compose("up", "-d")
        stack.wait_health()
        listing_down = stack.compose("exec", "-T", "worker", "ls", "/data/uploads").stdout.split()
        stack.record("down/up sin -v conserva subidas", listing_down == listing_before, listing_down)

        # exposicion y endurecimiento
        ids = stack.compose("ps", "-q").stdout.split()
        published = {}
        for cid in ids:
            info = json.loads(subprocess.run([DOCKER, "inspect", cid], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False).stdout)[0]
            published[info["Config"]["Labels"]["com.docker.compose.service"]] = {
                k: v for k, v in (info["NetworkSettings"]["Ports"] or {}).items() if v}
        stack.record("solo el proxy publica puertos (127.0.0.1)",
                     all(not v for k, v in published.items() if k != "proxy")
                     and all(b["HostIp"] == "127.0.0.1" for v in published["proxy"].values() for b in v), published)
        uid = stack.compose("exec", "-T", "api", "id", "-u").stdout.strip()
        stack.record("proceso no root", uid == "10001", uid)
        w = stack.compose("exec", "-T", "api", "sh", "-c", "touch /app/x 2>&1; echo rc=$?", check=False)
        stack.record("sistema de archivos de solo lectura", "rc=0" not in w.stdout, w.stdout.strip())
        egress = stack.compose("exec", "-T", "worker", "python", "-c",
                               "import socket;socket.create_connection(('1.1.1.1',443),timeout=4)", check=False)
        stack.record("red interna del worker sin salida a Internet", egress.returncode != 0)
        env_dump = stack.compose("exec", "-T", "api", "sh", "-c", "ls -a /app | grep -c '^.env' || true").stdout.strip()
        stack.record("la imagen no contiene .env", env_dump == "0", env_dump)
        health_status = subprocess.run([DOCKER, "inspect", "--format", "{{.State.Health.Status}}", ids[0]],
                                       capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
        api_id = stack.compose("ps", "-q", "api").stdout.strip()
        hs = subprocess.run([DOCKER, "inspect", "--format", "{{.State.Health.Status}}", api_id], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False).stdout.strip()
        stack.record("HEALTHCHECK del contenedor api", hs in ("healthy", "starting"), (hs, health_status.returncode))

        logs = stack.compose("logs", "--no-color", "--tail", "400", check=False).stdout
        leaked = [s for s in stack.secrets if s in logs]
        stack.record("los logs no contienen secretos", not leaked)
        (EVIDENCE / "smoke_logs.txt").write_text(stack.scrub(logs), encoding="utf-8")
    finally:
        stack.compose("down", "-v", check=False)
        result = {"started": started, "finished": datetime.now().astimezone().isoformat(timespec="seconds"),
                  "project": stack.project, "database": stack.db, "checks": stack.transcript,
                  "passed": sum(c["ok"] for c in stack.transcript), "total": len(stack.transcript),
                  "note": "secretos aleatorios generados en la ejecucion; datos sinteticos; volumenes eliminados al final"}
        (EVIDENCE / "smoke_resultado.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
