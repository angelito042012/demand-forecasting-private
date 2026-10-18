"""R16: demostracion LOCAL sobre una copia restaurada, con una sola base comun para API, worker y creacion de usuarios.

    python -m scripts.demo_local up [--build]        # crea/levanta el stack df-demo (solo 127.0.0.1) y restaura la copia si hace falta
    python -m scripts.demo_local status [--writers]  # contenedores, MISMA base en api/worker/usuarios, corridas visibles, escritores
    python -m scripts.demo_local create-user --username U --role admin|lector            # contrasena por consola (getpass) o:
    python -m scripts.demo_local create-user --username U --role lector --generate       # la genera y la guarda en un archivo privado
    python -m scripts.demo_local stop                # detiene (conserva volumenes y base); `up` la reanuda
    python -m scripts.demo_local down                # elimina contenedores y redes, CONSERVA los volumenes (la base restaurada)

Todos los procesos reciben la misma MONGODB_URI/MONGODB_DATABASE desde el estado privado (`artifacts/private/t13b/demo_state.json`,
fuera de Git); la comprobacion `status` compara un hash del nombre de base visto por cada contenedor, sin imprimir URI ni claves.
Solo toca el proyecto compose `df-demo`: no detiene Mongo de desarrollo ni otras aplicaciones, no usa `down -v`.
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import secrets
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRIV = ROOT / "artifacts" / "private" / "t13b"
STATE = PRIV / "demo_state.json"
CREDS = PRIV / "demo_credenciales.txt"
BACKUP = ROOT / "artifacts" / "private" / "t11a" / "backup"
IMAGE = "df-app:t11a-local"
PROJECT = "df-demo"
PORT = 8443

CHECK = r"""
import hashlib, json, os
from pymongo import MongoClient
db = MongoClient(os.environ["MONGODB_URI"], serverSelectionTimeoutMS=4000)[os.environ["MONGODB_DATABASE"]]
runs = [{"run_id": r["run_id"], "kind": r.get("kind"), "status": r.get("status")} for r in db.runs.find({}, {"run_id": 1, "kind": 1, "status": 1})]
ptr = db.run_pointer.find_one({}) or {}
jobs = {s: db.jobs.count_documents({"status": s}) for s in ("queued", "running")}
print(json.dumps({"db_hash": hashlib.sha256(os.environ["MONGODB_DATABASE"].encode()).hexdigest()[:12], "db": os.environ["MONGODB_DATABASE"],
                  "runs": sorted(runs, key=lambda r: r["run_id"]), "puntero": ptr.get("run_id"), "jobs": jobs,
                  "usuarios": db.users.count_documents({}), "staging": db.runs.count_documents({"status": "staging"})}))
"""


def state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    PRIV.mkdir(parents=True, exist_ok=True)
    st = {"project": PROJECT, "db": "df_demo_" + time.strftime("%Y%m%d%H%M%S"), "root_user": "root_demo", "root_pw": secrets.token_urlsafe(24),
          "app_user": "dfapp", "app_pw": secrets.token_urlsafe(24), "auth": secrets.token_urlsafe(48), "port": PORT, "restored": False}
    save(st)
    return st


def save(st: dict) -> None:
    STATE.write_text(json.dumps(st), encoding="utf-8")


def env(st: dict) -> dict:
    uri = f"mongodb://{st['app_user']}:{st['app_pw']}@mongo:27017/{st['db']}?authSource={st['db']}"
    return {**os.environ, "DF_PROXY_PORT": str(st["port"]), "ALLOWED_ORIGINS": f"https://localhost:{st['port']}", "MONGODB_DATABASE": st["db"],
            "MONGO_ROOT_USER": st["root_user"], "MONGO_ROOT_PASSWORD": st["root_pw"], "MONGO_APP_USER": st["app_user"],
            "MONGO_APP_PASSWORD": st["app_pw"], "AUTH_SECRET": st["auth"], "MONGODB_URI": uri}


def dc(st: dict, *a: str, extra: dict | None = None, inp: str | None = None):
    return subprocess.run(["docker", "compose", "-p", st["project"], *a], cwd=ROOT, env={**env(st), **(extra or {})}, check=False,
                          capture_output=True, text=True, encoding="utf-8", errors="replace", input=inp)


def mask(text: str, st: dict) -> str:
    for k in ("app_pw", "root_pw", "auth"):
        text = text.replace(st[k], "***")
    return text


def port_free(port: int) -> bool:
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def cmd_up(a) -> int:
    st = state()
    running = dc(st, "ps", "-q").stdout.split()
    if not running and not port_free(st["port"]):
        print(f"El puerto {st['port']} de 127.0.0.1 ya esta ocupado por otro programa; no se toca.")
        return 2
    if a.build:
        r = dc(st, "build", "api")
        if r.returncode:
            print(mask(r.stderr[-600:], st))
            return 1
    r = dc(st, "up", "-d", "--no-build", "mongo")
    if r.returncode:
        print(mask(r.stderr[-600:], st))
        return 1
    for _ in range(40):
        h = subprocess.run(["docker", "ps", "--filter", f"name={st['project']}-mongo", "--format", "{{.Status}}"], check=False,
                           capture_output=True, text=True).stdout
        if "(healthy)" in h:
            break
        time.sleep(3)
    if not st.get("restored"):
        if not (BACKUP / "manifiesto.json").exists():
            print("Falta el respaldo verificado (artifacts/private/t11a/backup).")
            return 1
        e = env(st)
        r = subprocess.run(["docker", "run", "--rm", "--network", f"{st['project']}_data", "-v", f"{ROOT}/scripts:/app/scripts:ro", "-v", f"{BACKUP}:/backup:ro",
                            "-e", "MONGODB_URI", "-e", "MONGODB_DATABASE", "--entrypoint", "python", IMAGE, "-m", "scripts.backup_restore", "restore",
                            "--from", "/backup", "--db", st["db"]], env={**os.environ, "MONGODB_URI": e["MONGODB_URI"], "MONGODB_DATABASE": st["db"]},
                           check=False, capture_output=True, text=True)
        out = json.loads(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 and r.stdout.strip() else {}
        if not out.get("ok"):
            print("Restauracion no verificada:", mask(r.stdout[-300:] + r.stderr[-300:], st))
            return 1
        st["restored"] = True
        save(st)
        print(f"Copia restaurada: puntero {out.get('puntero')}, {out.get('data_plus_index_mb')} MB, sin problemas.")
    r = dc(st, "up", "-d", "--no-build", "api", "worker", "proxy")
    if r.returncode:
        print(mask(r.stderr[-600:], st))
        return 1
    print(f"Demostracion en https://localhost:{st['port']} (solo 127.0.0.1; certificado autofirmado: el navegador avisara). Base: {st['db']}")
    return 0


def _check(st: dict, service: str) -> dict:
    r = dc(st, "exec", "-T", service, "python", "-c", CHECK)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return {"error": mask((r.stderr or r.stdout)[-200:], st)}


def cmd_status(a) -> int:
    st = state()
    ps = dc(st, "ps", "--format", "{{.Service}}={{.State}}({{.Health}})").stdout.split()
    print("contenedores:", " ".join(ps) or "ninguno")
    out = {s: _check(st, s) for s in ("api", "worker")}
    if any("error" in v for v in out.values()):
        print("No se pudo consultar la base:", {k: v.get("error") for k, v in out.items()})
        return 1
    hashes = {s: v["db_hash"] for s, v in out.items()}
    expected = hashlib.sha256(st["db"].encode()).hexdigest()[:12]
    same = len(set(hashes.values())) == 1 and expected in hashes.values()
    print(f"misma base en api y worker y en el estado de la demo: {same} (base {out['api']['db']}, hash {expected})")
    v = out["api"]
    for r in v["runs"]:
        print(f"  corrida {r['run_id']} tipo={r['kind']} estado={r['status']}")
    print(f"puntero activo: {v['puntero']} | usuarios: {v['usuarios']} | jobs: {v['jobs']} | corridas en staging: {v['staging']}")
    if a.writers:
        busy = v["jobs"]["queued"] + v["jobs"]["running"] + v["staging"]
        print("ESCRITORES ACTIVOS: " + ("SI, no hacer mantenimiento/exportacion" if busy else "ninguno visible (jobs y staging en 0)"))
    return 0 if same else 1


def cmd_create_user(a) -> int:
    st = state()
    if a.generate:
        pw = secrets.token_urlsafe(14)
        gen = True
    else:
        pw = getpass.getpass("Contrasena (no se muestra): ")
        if pw != getpass.getpass("Repita la contrasena: "):
            print("No coinciden.")
            return 2
        gen = False
    r = dc(st, "exec", "-T", "-e", "DF_NEW_PASSWORD", "api", "df-entrypoint", "cli", "create-user", "--username", a.username, "--role", a.role,
           extra={"DF_NEW_PASSWORD": pw})
    print(mask((r.stdout + r.stderr).replace(pw, "***")[-300:], st).strip())
    if r.returncode == 0 and gen:
        PRIV.mkdir(parents=True, exist_ok=True)
        with CREDS.open("a", encoding="utf-8") as f:
            f.write(f"{a.username} ({a.role}): {pw}\n")
        print(f"Usuario creado. La contrasena generada se guardo en {CREDS} (privado, fuera de Git); no se muestra aqui.")
    return r.returncode


def cmd_stop(a) -> int:
    st = state()
    r = dc(st, "stop")
    print("detenido (volumenes y base conservados)" if r.returncode == 0 else mask(r.stderr[-300:], st))
    return r.returncode


def cmd_down(a) -> int:
    st = state()
    r = dc(st, "down")
    print("contenedores y redes eliminados; volumenes (base restaurada) conservados" if r.returncode == 0 else mask(r.stderr[-300:], st))
    return r.returncode


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="scripts.demo_local")
    sub = ap.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("up")
    u.add_argument("--build", action="store_true")
    s = sub.add_parser("status")
    s.add_argument("--writers", action="store_true")
    c = sub.add_parser("create-user")
    c.add_argument("--username", required=True)
    c.add_argument("--role", required=True, choices=["admin", "lector"])
    c.add_argument("--generate", action="store_true")
    sub.add_parser("stop")
    sub.add_parser("down")
    a = ap.parse_args(argv)
    return {"up": cmd_up, "status": cmd_status, "create-user": cmd_create_user, "stop": cmd_stop, "down": cmd_down}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
