"""T11B: tarifas minoristas de Azure para el plan (API publica, sin autenticacion, solo lectura).

    python -m scripts.azure_prices --region brazilsouth --out artifacts/private/t11b/azure_prices.json

Guarda los medidores relevantes con su `effectiveStartDate` y la URL de consulta para que la tabla del plan sea
reproducible. Los precios son de lista (retail); los de la cuenta Azure for Students deben contrastarse en la calculadora.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

API = "https://prices.azure.com/api/retail/prices"
SERVICES = ["Azure Container Apps", "Container Registry", "Storage", "Log Analytics", "Azure Monitor", "Bandwidth", "Key Vault"]


def _get(url: str) -> dict:
    """GET con reintentos y espera ante 429 (la API publica limita la tasa)."""
    for attempt in range(8):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as exc:
            if exc.code != 429:
                raise
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("429 persistente")


def fetch(flt: str, limit: int = 600) -> list[dict]:
    url = API + "?" + urllib.parse.urlencode({"$filter": flt, "currencyCode": "USD"})
    out: list[dict] = []
    while url and len(out) < limit:
        data = _get(url)
        out += data.get("Items", [])
        url = data.get("NextPageLink")
        time.sleep(2)
    return out


def slim(i: dict) -> dict:
    return {k: i.get(k) for k in ("serviceName", "productName", "skuName", "meterName", "armRegionName", "unitOfMeasure",
                                  "retailPrice", "tierMinimumUnits", "type", "effectiveStartDate")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default="brazilsouth")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    res: dict = {"consultado_utc": datetime.now(UTC).isoformat(timespec="seconds"), "api": API, "region": args.region, "items": {}}
    for svc in SERVICES:
        flt = f"serviceName eq '{svc}' and armRegionName eq '{args.region}'"
        try:
            items = fetch(flt)
        except Exception as exc:  # noqa: BLE001
            res["items"][svc] = {"error": f"{type(exc).__name__}: {exc}"[:200], "filtro": flt}
            continue
        res["items"][svc] = {"filtro": flt, "n": len(items), "medidores": [slim(i) for i in items]}
    # medidores globales (sin region) de Container Apps y red
    for svc in ("Azure Container Apps", "Bandwidth"):
        try:
            glob = fetch(f"serviceName eq '{svc}' and armRegionName eq 'Global'", 200)
            res["items"][svc + " (Global)"] = {"n": len(glob), "medidores": [slim(i) for i in glob]}
        except Exception as exc:  # noqa: BLE001
            res["items"][svc + " (Global)"] = {"error": str(exc)[:200]}
    args.out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: (v.get("n") if isinstance(v, dict) else None) for k, v in res["items"].items()}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
