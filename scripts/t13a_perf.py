"""T13A/R15: ensayo de rendimiento de lecturas paginadas (1 y 5 sesiones) contra una instancia ya levantada.

    python -m scripts.t13a_perf --base https://localhost:8443 --creds <json privado> --run-id hist-... --container df-demo-api-1 \
        --out artifacts/private/t13b/perf.json --samples artifacts/private/t13b/perf_muestras.json --insecure-local

`--creds` es un JSON privado {"usuarios": [{"username":..., "password":...}, ...]} (>= 1; cada sesion hace su propio login, sin
evadir el limite de intentos). Solo GET. Por consulta y nivel: calentamiento explicito (5 solicitudes descartadas) y 20 medidas por
sesion, sesiones concurrentes (hilos) en bucle cerrado.

Percentil = nearest-rank: valor de rango ceil(q*n) en la muestra ordenada (n=20 -> p95 es la 19.a; n=100 -> la 95.a).
Una tanda INCOMPLETA (menos muestras de las esperadas, excepciones, estados distintos de 200, cero muestras) se informa como
`completa: false` y el programa termina con codigo 1: nunca produce un informe aprobado. TLS se verifica por defecto;
`--insecure-local` (certificado autofirmado de ensayo local) es la unica forma de omitirlo. Las muestras crudas se guardan en
`--samples` (privado) para recalcular. No imprime ni guarda contraseñas ni cookies.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import platform
import statistics
import subprocess
import threading
import time
from pathlib import Path

import httpx

N_MEDIDAS, N_CALENTAMIENTO = 20, 5
UMBRAL_LENTO_MS = 2000.0


def percentile(vals: list[float], q: float) -> float | None:
    """Nearest-rank: s[ceil(q*n) - 1] sobre la muestra ordenada; None si no hay muestras."""
    if not vals:
        return None
    s = sorted(vals)
    return s[max(1, math.ceil(q * len(s))) - 1]


def summarize(latencies: list[list[float]], errors: list[list[str]], expected_per_session: int, sizes: list[int] | None = None) -> dict:
    """Resumen de una tanda. `latencies[k]` son las medidas OK de la sesion k; `errors[k]`, los fallos (excepcion / estado)."""
    n_sess = len(latencies)
    per_session = [len(x) for x in latencies]
    allv = [v for lat in latencies for v in lat]
    n_err = sum(len(e) for e in errors)
    completa = n_sess > 0 and all(c == expected_per_session for c in per_session) and n_err == 0
    p50, p95 = (statistics.median(allv) if allv else None), percentile(allv, 0.95)
    return {"sesiones": n_sess, "esperadas": n_sess * expected_per_session, "medidas_ok": len(allv), "por_sesion": per_session,
            "errores": n_err, "detalle_errores": sorted({e for es in errors for e in es})[:10], "completa": completa,
            "p50_ms": round(p50, 1) if p50 is not None else None, "p95_ms": round(p95, 1) if p95 is not None else None,
            "percentil": "nearest-rank", "max_ms": round(max(allv), 1) if allv else None,
            "solicitudes_sobre_2s": sum(1 for v in allv if v > UMBRAL_LENTO_MS),
            "bytes_resp_medio": int(statistics.mean(sizes)) if sizes else None}


def run_level(sessions: list, urlf, *, n_medidas: int = N_MEDIDAS, n_calentamiento: int = N_CALENTAMIENTO):
    """Ejecuta una tanda con `len(sessions)` hilos. Devuelve (resumen, muestras). Cada excepcion/estado!=200 se contabiliza."""
    n = len(sessions)
    lat: list[list[float]] = [[] for _ in range(n)]
    err: list[list[str]] = [[] for _ in range(n)]
    sizes: list[int] = []
    for k, c in enumerate(sessions):  # calentamiento explicito, descartado; un fallo aqui tambien cuenta
        for i in range(n_calentamiento):
            try:
                r = c.get(urlf(100 + i))
                if r.status_code != 200:
                    err[k].append(f"calentamiento estado {r.status_code}")
            except Exception as e:  # noqa: BLE001 - se contabiliza, no se oculta
                err[k].append(f"calentamiento {type(e).__name__}")
    gate = threading.Barrier(n) if n else None

    def work(k: int) -> None:
        try:
            gate.wait(timeout=30)
        except threading.BrokenBarrierError:
            err[k].append("BarreraRota")
            return
        for i in range(n_medidas):
            t = time.perf_counter()
            try:
                r = sessions[k].get(urlf(i))
            except Exception as e:  # noqa: BLE001
                err[k].append(type(e).__name__)
                continue
            ms = (time.perf_counter() - t) * 1000
            if r.status_code != 200:
                err[k].append(f"estado {r.status_code}")
                continue
            lat[k].append(ms)
            if k == 0:
                sizes.append(len(r.content))

    threads = [threading.Thread(target=work, args=(k,)) for k in range(n)]
    t0 = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    res = summarize(lat, err, n_medidas, sizes)
    res["duracion_s"] = round(time.perf_counter() - t0, 2)
    return res, {"latencias_ms": [[round(v, 2) for v in x] for x in lat], "errores": err}


def login(base: str, u: dict, *, verify: bool, timeout: float = 30) -> httpx.Client:
    c = httpx.Client(base_url=base, verify=verify, timeout=timeout, headers={"Origin": base})
    try:
        r = c.post("/api/v1/auth/login", json={"username": u["username"], "password": u["password"]})
        if r.status_code != 200:
            raise RuntimeError(f"login {r.status_code}")
    except BaseException:
        c.close()
        raise
    return c


def queries(run: str, sku: str) -> dict:
    return {
        "forecasts_sku": lambda i: f"/api/v1/forecasts?run_id={run}&level=sku&page={1 + i % 20}&page_size=50",
        "recommendations_pedidos": lambda i: f"/api/v1/recommendations?run_id={run}&only_orders=true&page={1 + i % 10}&page_size=50",
        "recommendation_detalle": lambda i: f"/api/v1/recommendations/{sku}?run_id={run}",
    }


def cgroup(container: str, f: str) -> str:
    return subprocess.run(["docker", "exec", container, "cat", f"/sys/fs/cgroup/{f}"], check=False, capture_output=True, text=True).stdout.strip()


def wait_health(base: str, *, verify: bool, timeout_s: float) -> float | None:
    """Segundos hasta que /health responde 200, o None si se agota `timeout_s` (timeout TOTAL de arranque)."""
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < timeout_s:
        try:
            if httpx.get(base + "/api/v1/health", verify=verify, timeout=3).status_code == 200:
                return round(time.perf_counter() - t0, 2)
        except httpx.HTTPError:
            pass
        time.sleep(0.25)
    return None


def first_sku(c: httpx.Client, run: str) -> str:
    r = c.get(f"/api/v1/recommendations?run_id={run}&only_orders=true&page_size=1")
    r.raise_for_status()
    return r.json()["items"][0]["sku"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--creds", type=Path, required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--container", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--samples", type=Path, required=True, help="muestras crudas (privado)")
    ap.add_argument("--skip-cold", action="store_true")
    ap.add_argument("--cold-timeout", type=float, default=120.0, help="timeout total del arranque en frio (s)")
    ap.add_argument("--insecure-local", action="store_true", help="NO verificar TLS: solo certificado autofirmado de ensayo local")
    a = ap.parse_args(argv)
    verify = not a.insecure_local
    users = json.loads(a.creds.read_text(encoding="utf-8"))["usuarios"]
    res: dict = {"metodo": f"{N_CALENTAMIENTO} calentamiento + {N_MEDIDAS} medidas por sesion y consulta; hilos concurrentes; GET; percentil nearest-rank",
                 "tls_verificado": verify, "hardware": {"so": platform.platform(), "cpu_logicas_host": os.cpu_count()}}
    raw: dict = {}
    res["hardware"]["docker_ncpu_memtotal_bytes"] = subprocess.run(["docker", "info", "--format", "{{.NCPU}} {{.MemTotal}}"], check=False,
                                                                  capture_output=True, text=True).stdout.split()
    res["contenedor"] = subprocess.run(["docker", "inspect", a.container, "--format", "{{.HostConfig.NanoCpus}} {{.HostConfig.Memory}}"],
                                       check=False, capture_output=True, text=True).stdout.strip()
    completa = True
    if not a.skip_cold:  # arranque en frio: reinicio de la API y primera solicitud de cada consulta
        subprocess.run(["docker", "restart", a.container], check=False, capture_output=True)
        t_ready = wait_health(a.base, verify=verify, timeout_s=a.cold_timeout)
        res["arranque_en_frio"] = {"health_listo_s": t_ready, "timeout_s": a.cold_timeout}
        if t_ready is None:
            completa = False
        else:
            c = login(a.base, users[0], verify=verify)
            try:
                sku = first_sku(c, a.run_id)
                first = {}
                for name, f in queries(a.run_id, sku).items():
                    t = time.perf_counter()
                    r = c.get(f(0))
                    first[name] = {"ms": round((time.perf_counter() - t) * 1000, 1), "status": r.status_code}
                    completa = completa and r.status_code == 200
                res["arranque_en_frio"]["primera_solicitud_por_consulta"] = first
            finally:
                c.close()
    res["niveles"] = {}
    sku = None
    c = None
    try:
        c = login(a.base, users[0], verify=verify)
        sku = first_sku(c, a.run_id)
    except Exception as e:  # noqa: BLE001
        res["error_preparacion"] = f"{type(e).__name__}: {e}"
        completa = False
    finally:
        if c is not None:
            c.close()
    if sku:
        res["sku_detalle"] = sku
        for name, f in queries(a.run_id, sku).items():
            res["niveles"][name] = {}
            raw[name] = {}
            for n in (1, 5):
                sessions: list[httpx.Client] = []
                try:
                    for i in range(n):
                        sessions.append(login(a.base, users[i % len(users)], verify=verify))
                    out, muestras = run_level(sessions, f)
                except Exception as e:  # noqa: BLE001
                    out, muestras = {"sesiones": n, "completa": False, "errores": 1, "detalle_errores": [f"{type(e).__name__}: {e}"[:120]]}, {}
                finally:
                    for s in sessions:
                        try:
                            s.post("/api/v1/auth/logout")
                        except httpx.HTTPError:
                            pass
                        s.close()
                res["niveles"][name][str(n)] = out
                raw[name][str(n)] = muestras
                completa = completa and bool(out.get("completa"))
    res["memoria_pico_api_mib"] = round(int(cgroup(a.container, "memory.peak") or 0) / 1048576, 1)
    res["cgroup_cpu_stat"] = cgroup(a.container, "cpu.stat").replace("\n", "; ")
    res["completa"] = completa
    a.out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    a.samples.write_text(json.dumps(raw), encoding="utf-8")
    for n, per in res["niveles"].items():
        for k, v in per.items():
            print(f"{n:26s} sesiones={k} completa={v.get('completa')} p50={v.get('p50_ms')} p95={v.get('p95_ms')} max={v.get('max_ms')} "
                  f"err={v.get('errores')}")
    print("COMPLETA" if completa else "INCOMPLETA: no usar como evidencia aprobada")
    return 0 if completa else 1


if __name__ == "__main__":
    raise SystemExit(main())
