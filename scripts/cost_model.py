"""T11B: modelo de costo REPRODUCIBLE del despliegue propuesto (Azure Container Apps Consumption, Brazil South, USD).

    python -m scripts.cost_model [--prices artifacts/private/t11b/azure_prices.json] [--days 6] [--out artifacts/private/t11b/costo.json]

Las tarifas salen de `scripts/azure_prices.py` (Azure Retail Prices API publica; precios de lista). Los grants gratuitos de
Container Apps Consumption son POR SUSCRIPCION y por mes (180 000 vCPU-s, 360 000 GiB-s, 2 M peticiones): se restan UNA
sola vez del total de la suscripcion, no por aplicacion. Un worker que sondea la cola NO se presume ocioso: se calcula con
una fraccion activa `f` explicita (idle exige CPU < 0,01 vCPU y red < 1000 B/s; si no, se factura como activo).

El resultado es una ESTIMACION con rango, no una cotizacion: ver el plan para los conceptos no determinables.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CPU, MEM = 0.5, 1.0                      # vCPU y GiB por contenedor (medido: pico worker ~406 MiB)
GRANT_CPU_S, GRANT_MEM_S = 180_000, 360_000
DAY_S = 86_400


def tariffs(prices: Path) -> dict:
    d = json.loads(prices.read_text(encoding="utf-8"))
    t: dict = {"consultado_utc": d["consultado_utc"]}
    for m in d["items"]["Azure Container Apps"]["medidores"]:
        if m["meterName"] == "Standard vCPU Active Usage":
            t["vcpu_activa_s"] = m["retailPrice"]
        elif m["meterName"] == "Standard vCPU Idle Usage":
            t["vcpu_idle_s"] = m["retailPrice"]
        elif m["meterName"] == "Standard Memory Active Usage":
            t["mem_activa_gibs"] = m["retailPrice"]
        elif m["meterName"] == "Standard Memory Idle Usage":
            t["mem_idle_gibs"] = m["retailPrice"]
        elif m["meterName"] == "Standard Requests":
            t["req_millon"] = m["retailPrice"]
    for m in d["items"]["Container Registry"]["medidores"]:
        if m["meterName"] == "Basic Registry Unit":
            t["acr_basic_dia"] = m["retailPrice"]
    for m in d["items"]["Storage"]["medidores"]:
        if m["productName"] == "Files" and m["meterName"] == "LRS Data Stored" and m["skuName"] == "Standard LRS":
            t["files_gb_mes"] = m["retailPrice"]
    for m in d["items"]["Log Analytics"]["medidores"]:
        if m["meterName"] == "Analytics Logs Data Ingestion" and m["retailPrice"] > 0:
            t["logs_gb_sobre_5"] = m["retailPrice"]
    return t


def container_seconds(days: float, *, active_fraction: float) -> dict:
    """vCPU-s y GiB-s (activos e ociosos) de UN contenedor 0,5 vCPU / 1 GiB encendido todo el periodo."""
    total = days * DAY_S
    act = total * active_fraction
    idle = total - act
    return {"vcpu_act": CPU * act, "vcpu_idle": CPU * idle, "mem_act": MEM * act, "mem_idle": MEM * idle}


def job_seconds(days: float, *, every_min: int, run_s: int) -> dict:
    runs = days * 24 * 60 / every_min
    act = runs * run_s
    return {"vcpu_act": CPU * act, "vcpu_idle": 0.0, "mem_act": MEM * act, "mem_idle": 0.0}


def cost(parts: list[dict], t: dict, grants: str) -> float:
    """grants: 'ninguno' (sin descuento), 'favorable' (los grants restan a lo activo), 'conservador' (restan a lo ocioso)."""
    s = {k: sum(p[k] for p in parts) for k in ("vcpu_act", "vcpu_idle", "mem_act", "mem_idle")}
    cpu_total, mem_total = s["vcpu_act"] + s["vcpu_idle"], s["mem_act"] + s["mem_idle"]
    g_cpu, g_mem = (0, 0) if grants == "ninguno" else (min(GRANT_CPU_S, cpu_total), min(GRANT_MEM_S, mem_total))
    if grants == "favorable":
        a_cpu = min(g_cpu, s["vcpu_act"])
        a_mem = min(g_mem, s["mem_act"])
        return ((s["vcpu_act"] - a_cpu) * t["vcpu_activa_s"] + (s["vcpu_idle"] - (g_cpu - a_cpu)) * t["vcpu_idle_s"]
                + (s["mem_act"] - a_mem) * t["mem_activa_gibs"] + (s["mem_idle"] - (g_mem - a_mem)) * t["mem_idle_gibs"])
    i_cpu = min(g_cpu, s["vcpu_idle"])
    i_mem = min(g_mem, s["mem_idle"])
    return ((s["vcpu_act"] - (g_cpu - i_cpu)) * t["vcpu_activa_s"] + (s["vcpu_idle"] - i_cpu) * t["vcpu_idle_s"]
            + (s["mem_act"] - (g_mem - i_mem)) * t["mem_activa_gibs"] + (s["mem_idle"] - i_mem) * t["mem_idle_gibs"])


def fixed(days: float, t: dict, *, files_gb: float = 0.5, logs_gb: float = 1.0) -> dict:
    """Costos no ligados al computo. Registro Basic + Files + logs (los primeros 5 GB/mes de ingestion sin cargo)."""
    return {"acr": t["acr_basic_dia"] * days, "files": t["files_gb_mes"] * files_gb * days / 30.0,
            "logs": max(0.0, logs_gb * days / 30.0 - 5.0) * t["logs_gb_sobre_5"], "atlas": 0.0}


SCENARIOS = {
    "A_api_min1+worker_continuo": lambda d, f_api, f_w: [container_seconds(d, active_fraction=f_api),
                                                         container_seconds(d, active_fraction=f_w)],
    "B_api_min1+job_5min_30s": lambda d, f_api, f_w: [container_seconds(d, active_fraction=f_api),
                                                      job_seconds(d, every_min=5, run_s=30)],
    "C_api_min0+job_5min_30s": lambda d, f_api, f_w: [container_seconds(d, active_fraction=1.0)
                                                      if False else {k: v * 2 / 24 for k, v in container_seconds(d, active_fraction=1.0).items()},
                                                      job_seconds(d, every_min=5, run_s=30)],
}


def run(prices: Path, days_event: float) -> dict:
    t = tariffs(prices)
    out: dict = {"tarifas": t, "supuestos": {"contenedor": f"{CPU} vCPU / {MEM} GiB", "grants": "por suscripcion y mes, una sola vez",
                                             "api_fraccion_activa": [0.05, 1.0], "worker_fraccion_activa": [0.0, 0.25, 1.0],
                                             "files_gb": 0.5, "logs_gb_por_30d": 1.0, "egreso": "dentro de los primeros 100 GB/mes gratis",
                                             "grants_nota": "los grants se restan una vez del total; 'favorable' los aplica a lo activo, 'conservador' a lo ocioso"},
                 "escenarios": {}}
    for name, fn in SCENARIOS.items():
        out["escenarios"][name] = {}
        for label, days in (("hasta_23_10", days_event), ("mes_30d", 30.0)):
            rows = []
            for f_api in (0.05, 1.0):
                for f_w in ((0.0, 0.25, 1.0) if name.startswith("A") else (0.0,)):
                    parts = fn(days, f_api, f_w)
                    fx = fixed(days, t)
                    row = {"f_api": f_api, "f_worker": f_w if name.startswith("A") else None, "dias": days}
                    for g in ("ninguno", "favorable", "conservador"):
                        row[f"computo_{g}"] = round(cost(parts, t, g), 2)
                    row["fijo"] = {k: round(v, 2) for k, v in fx.items()}
                    row["total_min"] = round(row["computo_favorable"] + sum(fx.values()), 2)
                    row["total_max"] = round(row["computo_ninguno"] + sum(fx.values()), 2)
                    rows.append(row)
            out["escenarios"][name][label] = rows
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prices", type=Path, default=Path("artifacts/private/t11b/azure_prices.json"))
    ap.add_argument("--days", type=float, default=6.0, help="dias hasta el 23/10 desde el aprovisionamiento")
    ap.add_argument("--out", type=Path, default=Path("artifacts/private/t11b/costo.json"))
    args = ap.parse_args(argv)
    res = run(args.prices, args.days)
    args.out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    for name, per in res["escenarios"].items():
        for label, rows in per.items():
            lo = min(r["total_min"] for r in rows)
            hi = max(r["total_max"] for r in rows)
            print(f"{name:32s} {label:12s} US$ {lo:6.2f} – {hi:6.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
