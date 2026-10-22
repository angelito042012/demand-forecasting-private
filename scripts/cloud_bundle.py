# ruff: noqa: ISC004
"""T20: paquete de datos MINIMO para la nube, con copia verificable y restauracion probada (sin tocar Azure/Atlas).

    python -m scripts.cloud_bundle export --env ens19 --out artifacts/private/cloud_bundle_20261021
    python -m scripts.cloud_bundle verify --env ens19 --out artifacts/private/cloud_bundle_20261021

* export: `mongodump` (dentro del contenedor mongo del entorno) de SOLO lo necesario para operar la aplicacion; excluye
  usuarios, sesiones, intentos de acceso, trabajos, colecciones sin uso y el parcial del 21/10; de `plan_sales` solo las
  lineas del dataset vigente. Escribe archivos .gz y un manifiesto con conteos, huella de contenido por coleccion (bson
  ordenado por _id) y sha256 de cada archivo. No imprime la URI ni credenciales.
* verify: restaura el paquete en una base TEMPORAL del mismo servidor (nunca sobre la original), compara conteos y huellas
  contra el manifiesto y elimina la base temporal. Es la prueba de recuperacion que debe preceder a cualquier borrado.
Los datos no incluyen clientes, usuarios ni proveedores (ver docs/T20_PLAN_NUBE.md §3).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

EXCLUDE = ["users", "sessions", "login_attempts", "login_budget", "jobs", "scheduler_ticks", "import_conflicts", "import_rejects",
           "plan_sales", "plan_sales_partial"]
HASH_PY = r'''
import os, sys, json, hashlib
from pymongo import MongoClient
from bson import encode
db = MongoClient(os.environ["URI"])[sys.argv[1]]
out = {}
for n in sorted(db.list_collection_names()):
    h, c = hashlib.sha256(), 0
    for d in db[n].find({}).sort("_id", 1):
        h.update(encode(d)); c += 1
    out[n] = {"n": c, "sha256": h.hexdigest()}
print(json.dumps(out))
'''


def sh(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, **kw, check=False)


def api_env(project: str, name: str) -> str:
    r = sh(["docker", "exec", f"{project}-api-1", "printenv", name], text=True)
    if r.returncode:
        raise SystemExit(f"No se pudo leer {name} del contenedor api.")
    return r.stdout.strip()


def digest_collections(project: str, db_name: str, uri: str) -> dict:
    r = sh(["docker", "exec", "-e", f"URI={uri}", f"{project}-api-1", "python", "-c", HASH_PY, db_name], text=True)
    if r.returncode:
        raise SystemExit("No se pudo calcular la huella: " + r.stderr[-200:])
    return json.loads(r.stdout)


def sha_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def dump(project: str, uri: str, db_name: str, out: Path, name: str, extra: list[str]) -> Path:
    tmp = f"/tmp/{name}.gz"
    r = sh(["docker", "exec", f"{project}-mongo-1", "mongodump", f"--uri={uri}", f"--db={db_name}", f"--archive={tmp}", "--gzip", "--quiet", *extra],
           text=True)
    if r.returncode:
        raise SystemExit(f"mongodump fallo ({name}): " + (r.stderr or "")[-300:].replace(uri, "<uri>"))
    dst = out / f"{name}.gz"
    c = sh(["docker", "cp", f"{project}-mongo-1:{tmp}", str(dst)])
    sh(["docker", "exec", f"{project}-mongo-1", "rm", "-f", tmp])
    if c.returncode:
        raise SystemExit("docker cp fallo")
    return dst


def export(a) -> int:
    project = f"df-{a.env}"
    uri, db_name = api_env(project, "MONGODB_URI"), api_env(project, "MONGODB_DATABASE")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    heads = json.loads(sh(["docker", "exec", "-e", f"URI={uri}", f"{project}-api-1", "python", "-c",
                           "import os,sys,json\nfrom pymongo import MongoClient\n"
                           f"db=MongoClient(os.environ['URI'])['{db_name}']\n"
                           "h=db.plan_datasets.find_one({'status':'current'},{'_id':0,'dataset_id':1,'version':1,'sales_cutoff':1})\n"
                           "print(json.dumps(h))"], text=True).stdout)
    files = {}
    files["general"] = dump(project, uri, db_name, out, "general", [f"--excludeCollection={c}" for c in EXCLUDE])
    q = json.dumps({"dataset_id": heads["dataset_id"]})
    files["plan_sales"] = dump(project, uri, db_name, out, "plan_sales_vigente", ["--collection=plan_sales", f"--query={q}"])
    # huellas del ORIGEN para el subconjunto exportado (plan_sales filtrado se calcula aparte)
    digests = digest_collections(project, db_name, uri)
    ps = json.loads(sh(["docker", "exec", "-e", f"URI={uri}", f"{project}-api-1", "python", "-c",
                        "import os,json,hashlib\nfrom pymongo import MongoClient\nfrom bson import encode\n"
                        f"c=MongoClient(os.environ['URI'])['{db_name}'].plan_sales\n"
                        f"h=hashlib.sha256();n=0\nfor d in c.find({{'dataset_id':'{heads['dataset_id']}'}}).sort('_id',1):\n h.update(encode(d));n+=1\n"
                        "print(json.dumps({'n':n,'sha256':h.hexdigest()}))"], text=True).stdout)
    expected = {k: v for k, v in digests.items() if k not in EXCLUDE}
    expected["plan_sales"] = ps
    sizes = {k: p.stat().st_size for k, p in files.items()}
    manifest = {"generado": datetime.now().isoformat(timespec="seconds"), "entorno": a.env, "dataset_vigente": heads,
                "excluidas": EXCLUDE, "colecciones": expected, "archivos": {p.name: {"sha256": sha_file(p), "bytes": p.stat().st_size} for p in files.values()},
                "nota": "Sin usuarios, sesiones, trabajos ni credenciales; sin clientes ni proveedores; el parcial del 21/10 queda fuera."}
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"colecciones": {k: v["n"] for k, v in expected.items()}, "bytes_gz": sizes}, ensure_ascii=False))
    return 0


def verify(a) -> int:
    project = f"df-{a.env}"
    uri, db_name = api_env(project, "MONGODB_URI"), api_env(project, "MONGODB_DATABASE")
    out = Path(a.out)
    m = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    for fname, meta in m["archivos"].items():
        if sha_file(out / fname) != meta["sha256"]:
            print(f"ARCHIVO ALTERADO: {fname}")
            return 1
    pref = "vfy" + datetime.now().strftime("%H%M%S") + "_"      # el usuario de la app solo escribe en SU base: coleccion con prefijo
    ok = True
    try:
        for fname in m["archivos"]:
            sh(["docker", "cp", str(out / fname), f"{project}-mongo-1:/tmp/{fname}"])
            r = sh(["docker", "exec", f"{project}-mongo-1", "mongorestore", f"--uri={uri}", f"--archive=/tmp/{fname}", "--gzip", "--quiet",
                    f"--nsFrom={db_name}.$col$", f"--nsTo={db_name}.{pref}$col$"], text=True)
            sh(["docker", "exec", f"{project}-mongo-1", "rm", "-f", f"/tmp/{fname}"])
            if r.returncode:
                print("mongorestore fallo:", (r.stderr or "")[-300:].replace(uri, "<uri>"))
                return 1
        got = {k[len(pref):]: v for k, v in digest_collections(project, db_name, uri).items() if k.startswith(pref)}
        for name, exp in m["colecciones"].items():
            same = got.get(name) == exp
            ok &= same
            if not same:
                print("DIFERENCIA", name, exp["n"], (got.get(name) or {}).get("n"))
        extra = set(got) - set(m["colecciones"])
        if extra:
            print("colecciones inesperadas:", sorted(extra))
            ok = False
    finally:
        sh(["docker", "exec", "-e", f"URI={uri}", f"{project}-api-1", "python", "-c",
            "import os; from pymongo import MongoClient; "
            f"db = MongoClient(os.environ['URI'])['{db_name}']; "
            f"[db.drop_collection(n) for n in db.list_collection_names() if n.startswith('{pref}')]"])
    print("RESTAURACION VERIFICADA" if ok else "RESTAURACION CON DIFERENCIAS", json.dumps({k: v["n"] for k, v in m["colecciones"].items()}))
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["export", "verify"])
    ap.add_argument("--env", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    return export(a) if a.cmd == "export" else verify(a)


if __name__ == "__main__":
    sys.exit(main())
