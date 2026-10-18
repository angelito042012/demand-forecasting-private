"""T13A: ensayo de rendimiento LOCAL de lecturas paginadas (1 y 5 sesiones) contra una instancia ya levantada.

    python -m scripts.t13a_perf --base https://localhost:18445 --creds artifacts/private/t13a/perf_creds.json \
        --run-id hist-20260710-4ea348836e35 --container df-t13a-api-1 --out artifacts/private/t13a/perf.json

`--creds` es un JSON privado {"usuarios": [{"username":..., "password":...}, ...]} (>= 1; cada sesion hace su propio login, sin
evadir el limite de intentos). Solo lecturas GET. Mide por consulta: calentamiento explicito (5 solicitudes, descartadas),
20 solicitudes medidas por sesion con paginas distintas, sesiones concurrentes (hilos) y cada una en bucle cerrado. p50/p95
sobre todas las muestras (con 20 muestras el p95 es la 19.a ordenada: indicativo, no estadistico). El arranque en frio se mide
aparte reiniciando el contenedor de la API. No imprime ni guarda contraseñas ni cookies.
"""
from __future__ import annotations

import argparse
import json
import platform
import statistics
import subprocess
import threading
import time
from pathlib import Path

import httpx

N_MEDIDAS, N_CALENTAMIENTO = 20, 5


def pct(vals: list[float], q: float) -> float:
    s = sorted(vals)
    return s[min(len(s) - 1, max(0, round(q * len(s) + 0.5) - 1))]


def login(base: str, u: dict) -> httpx.Client:
    c = httpx.Client(base_url=base, verify=False, timeout=30, headers={"Origin": base})
    r = c.post("/api/v1/auth/login", json={"username": u["username"], "password": u["password"]})
    if r.status_code != 200:
        raise SystemExit(f"login {r.status_code}")
    return c


def queries(run: str, sku: str) -> dict[str, callable]:
    return {
        "forecasts_sku_p50": lambda i: f"/api/v1/forecasts?run_id={run}&level=sku&page={1 + i % 20}&page_size=50",
        "recommendations_pedidos_p50": lambda i: f"/api/v1/recommendations?run_id={run}&only_orders=true&page={1 + i % 10}&page_size=50",
        "recommendation_detalle": lambda i: f"/api/v1/recommendations/{sku}?run_id={run}",
    }


def cgroup(container: str, f: str) -> str:
    return subprocess.run(["docker", "exec", container, "cat", f"/sys/fs/cgroup/{f}"], check=False, capture_output=True, text=True).stdout.strip()


def run_level(base, users, name, urlf, n_sess) -> dict:
    sessions = [login(base, users[i % len(users)]) for i in range(n_sess)]
    for c in sessions:  # calentamiento explicito, descartado
        for i in range(N_CALENTAMIENTO):
            c.get(urlf(100 + i))
    lat: list[list[float]] = [[] for _ in sessions]
    err = [0] * n_sess
    sizes: list[int] = []
    gate = threading.Barrier(n_sess)

    def work(k):
        gate.wait()
        for i in range(N_MEDIDAS):
            t = time.perf_counter()
            r = sessions[k].get(urlf(i))
            lat[k].append((time.perf_counter() - t) * 1000)
            if r.status_code != 200:
                err[k] += 1
            elif k == 0:
                sizes.append(len(r.content))

    t0 = time.perf_counter()
    th = [threading.Thread(target=work, args=(k,)) for k in range(n_sess)]
    [t.start() for t in th]
    [t.join() for t in th]
    dur = time.perf_counter() - t0
    allv = [v for l in lat for v in l]
    for c in sessions:
        c.post("/api/v1/auth/logout")
        c.close()
    return {"sesiones": n_sess, "solicitudes": len(allv), "errores": sum(err), "p50_ms": round(statistics.median(allv), 1),
            "p95_ms": round(pct(allv, 0.95), 1), "max_ms": round(max(allv), 1), "bytes_resp_medio": int(statistics.mean(sizes)) if sizes else None,
            "duracion_s": round(dur, 2)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--creds", type=Path, required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--container", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--skip-cold", action="store_true")
    a = ap.parse_args(argv)
    users = json.loads(a.creds.read_text(encoding="utf-8"))["usuarios"]
    res: dict = {"metodo": f"{N_CALENTAMIENTO} calentamiento + {N_MEDIDAS} medidas por sesion y consulta; hilos concurrentes; GET; via proxy TLS local",
                 "hardware": {"so": platform.platform(), "cpu_logicas_host": __import__("os").cpu_count()}}
    info = subprocess.run(["docker", "info", "--format", "{{.NCPU}} {{.MemTotal}}"], check=False, capture_output=True, text=True).stdout.split()
    res["hardware"]["docker_ncpu_memtotal_bytes"] = info
    res["contenedor"] = subprocess.run(["docker", "inspect", a.container, "--format", "{{.HostConfig.NanoCpus}} {{.HostConfig.Memory}}"],
                                       check=False, capture_output=True, text=True).stdout.strip()
    if not a.skip_cold:  # arranque en frio: reinicio de la API y primera solicitud de cada consulta
        t0 = time.perf_counter()
        subprocess.run(["docker", "restart", a.container], check=False, capture_output=True)
        while True:
            try:
                if httpx.get(a.base + "/api/v1/health", verify=False, timeout=3).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.25)
        res["arranque_en_frio"] = {"health_listo_s": round(time.perf_counter() - t0, 2)}
        c = login(a.base, users[0])
        sku = c.get(f"/api/v1/recommendations?run_id={a.run_id}&only_orders=true&page_size=1").json()["items"][0]["sku"]
        first = {}
        for name, f in queries(a.run_id, sku).items():
            t = time.perf_counter()
            r = c.get(f(0))
            first[name] = {"ms": round((time.perf_counter() - t) * 1000, 1), "status": r.status_code}
        res["arranque_en_frio"]["primera_solicitud_por_consulta"] = first
        c.close()
    c = login(a.base, users[0])
    sku = c.get(f"/api/v1/recommendations?run_id={a.run_id}&only_orders=true&page_size=1").json()["items"][0]["sku"]
    c.close()
    res["sku_detalle"] = sku
    res["niveles"] = {}
    for name, f in queries(a.run_id, sku).items():
        res["niveles"][name] = {str(n): run_level(a.base, users, name, f, n) for n in (1, 5)}
    res["memoria_pico_api_mib"] = round(int(cgroup(a.container, "memory.peak") or 0) / 1048576, 1)
    res["cgroup_cpu_stat"] = cgroup(a.container, "cpu.stat").replace("\n", "; ")
    a.out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    for n, per in res["niveles"].items():
        for k, v in per.items():
            print(f"{n:30s} sesiones={k} p50={v['p50_ms']} p95={v['p95_ms']} err={v['errores']}")
    print("pico memoria API MiB", res["memoria_pico_api_mib"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
