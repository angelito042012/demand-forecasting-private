"""T11B: registra UNICAMENTE el proveedor Microsoft.App (autorizado por el usuario) y reconsulta la cuota de Container Apps.

No crea recursos ni grupos, no registra otros proveedores, no asigna permisos ni cambia la oferta. La sesion la inicia el
usuario en su navegador (device code) en un directorio privado; al terminar se hace `az logout` y se borra la cache.

    python -m scripts.azure_register_app --cfg artifacts/private/t11b/azure_cfg2 --out artifacts/private/t11b/azure_microsoft_app.json
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from scripts.azure_preflight import IMAGE, _clean, az, jq

PROVIDER = "Microsoft.App"
ALLOWED = ["brazilsouth", "canadacentral", "northcentralus", "westus", "westus2"]


def _docker(cfg: Path, *args: str) -> int:
    cmd = ["docker", "run", "--rm", "-e", "AZURE_CONFIG_DIR=/cfg", "-e", "PYTHONUNBUFFERED=1", "-v", f"{cfg.resolve()}:/cfg",
           IMAGE, "az", *args]
    return subprocess.run(cmd, check=False, env={**os.environ, "MSYS_NO_PATHCONV": "1"}).returncode


def _quota(cfg: Path, sub: str, region: str):
    u = jq(cfg, "rest", "--method", "get", "--url",
           f"/subscriptions/{sub}/providers/{PROVIDER}/locations/{region}/usages?api-version=2024-03-01")
    if not isinstance(u, dict) or "error" in u:
        return u
    return [{"n": x.get("name", {}).get("value"), "u": x.get("currentValue"), "l": x.get("limit")} for x in u.get("value", [])]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cfg", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--skip-login", action="store_true", help="reutiliza la sesion ya iniciada por el usuario en --cfg")
    args = ap.parse_args(argv)
    cfg = args.cfg
    cfg.mkdir(parents=True, exist_ok=True)
    res: dict = {"alcance": f"solo registro de {PROVIDER}; sin recursos, grupos, permisos ni cambio de oferta"}
    try:
        if not args.skip_login and _docker(cfg, "login", "--use-device-code", "--output", "none") != 0:
            res["login"] = "no completado"
            return 3
        acc = jq(cfg, "account", "show")
        if "error" in acc:
            res["login"] = acc
            return 2
        sub = acc["id"]
        res["antes"] = jq(cfg, "provider", "show", "-n", PROVIDER, "--query", "{estado:registrationState}")
        res["antes_cuota_brazilsouth"] = _quota(cfg, sub, "brazilsouth")
        if (res["antes"] or {}).get("estado") == "Registered":
            res["registro"] = {"omitido": "ya estaba registrado"}
        else:
            rc, _, err = az(cfg, "provider", "register", "-n", PROVIDER)
            res["registro"] = {"codigo": rc, "error": _clean(err.strip().splitlines()[-1]) if rc != 0 and err.strip() else None}
        estado = None
        for _ in range(40):
            d = jq(cfg, "provider", "show", "-n", PROVIDER, "--query", "{estado:registrationState}")
            estado = d.get("estado") if isinstance(d, dict) else None
            if estado == "Registered":
                break
            time.sleep(15)
        res["despues"] = {"estado": estado}
        res["cuotas"] = {"brazilsouth": _quota(cfg, sub, "brazilsouth")}
        def _managed(q):
            return next((x for x in q if x["n"] == "ManagedEnvironmentCount"), None) if isinstance(q, list) else None
        mb = _managed(res["cuotas"]["brazilsouth"])
        if not mb or not mb["l"]:
            for r in ALLOWED:
                if r != "brazilsouth":
                    res["cuotas"][r] = _quota(cfg, sub, r)
        res["managed_environment_count"] = {r: _managed(q) for r, q in res["cuotas"].items()}
        return 0
    finally:
        _docker(cfg, "logout")
        shutil.rmtree(cfg, ignore_errors=True)
        res["sesion_cerrada_y_cache_borrada"] = not cfg.exists()
        args.out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
