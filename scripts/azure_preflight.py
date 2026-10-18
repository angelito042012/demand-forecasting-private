"""T11B: preflight de Azure de SOLO LECTURA mediante la CLI oficial en contenedor aislado.

No crea, modifica ni registra nada (solo `show`/`list`/GET). La sesion la inicia el propio usuario en su navegador
(`az login --use-device-code`) y vive en un directorio privado (`artifacts/private/t11b/azure_cfg`, fuera de Git). No
imprime ni guarda tokens; el resumen elimina identificadores (suscripcion, tenant, usuario) y deja solo lo necesario.

    python -m scripts.azure_preflight --cfg artifacts/private/t11b/azure_cfg --out artifacts/private/t11b/azure_preflight.json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

IMAGE = "mcr.microsoft.com/azure-cli:latest"
ID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE)
PROVIDERS = ["Microsoft.App", "Microsoft.OperationalInsights", "Microsoft.Storage", "Microsoft.ContainerRegistry",
             "Microsoft.ManagedIdentity", "Microsoft.Authorization", "Microsoft.Insights"]
REGIONS = ["brazilsouth", "eastus", "eastus2", "southcentralus", "westus3"]


def az(cfg: Path, *args: str, timeout: int = 180) -> tuple[int, str, str]:
    cmd = ["docker", "run", "--rm", "-e", "AZURE_CONFIG_DIR=/cfg", "-e", "PYTHONUNBUFFERED=1",
           "-v", f"{cfg.resolve()}:/cfg", IMAGE, "az", *args]
    env = {"MSYS_NO_PATHCONV": "1"}
    import os
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False, env={**os.environ, **env})
    return p.returncode, p.stdout, p.stderr


def jq(cfg: Path, *args: str):
    rc, out, err = az(cfg, *args, "-o", "json")
    if rc != 0:
        return {"error": _clean(err.strip().splitlines()[-1] if err.strip() else f"codigo {rc}")}
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {"error": "salida no JSON"}


def _clean(text: str) -> str:
    return ID_RE.sub("<id>", text)[:300]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cfg", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--login", action="store_true",
                    help="inicia ANTES el login interactivo del usuario (device code en su navegador; sin contrasenas por chat)")
    args = ap.parse_args(argv)
    cfg = args.cfg
    cfg.mkdir(parents=True, exist_ok=True)
    if args.login:
        import os
        cmd = ["docker", "run", "--rm", "-e", "AZURE_CONFIG_DIR=/cfg", "-e", "PYTHONUNBUFFERED=1", "-v", f"{cfg.resolve()}:/cfg",
               IMAGE, "az", "login", "--use-device-code", "--output", "none"]
        if subprocess.run(cmd, check=False, env={**os.environ, "MSYS_NO_PATHCONV": "1"}).returncode != 0:
            print("login no completado")
            return 3
    res: dict = {"solo_lectura": True, "herramienta": IMAGE}
    acc = jq(cfg, "account", "show")
    if "error" in acc:
        res["sesion"] = acc
        args.out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
        print("sin sesion de Azure")
        return 2
    sub = acc["id"]
    res["suscripcion"] = {"estado": acc.get("state"), "nombre_generico": acc.get("name") if "student" in str(acc.get("name", "")).lower()
                          or "estudiante" in str(acc.get("name", "")).lower() else "<oculto>"}
    meta = jq(cfg, "rest", "--method", "get", "--url", f"/subscriptions/{sub}?api-version=2022-12-01")
    pol = (meta or {}).get("subscriptionPolicies", {}) if isinstance(meta, dict) else {}
    res["oferta"] = {"quotaId": pol.get("quotaId"), "spendingLimit": pol.get("spendingLimit"),
                     "locationPlacementId": pol.get("locationPlacementId"), "error": meta.get("error") if isinstance(meta, dict) else None}
    locs = jq(cfg, "account", "list-locations", "--query", "[?metadata.regionType=='Physical'].{n:name,r:metadata.regionCategory}")
    res["regiones_fisicas"] = len(locs) if isinstance(locs, list) else locs
    res["regiones_consultadas"] = {}
    for r in REGIONS:
        res["regiones_consultadas"][r] = bool(isinstance(locs, list) and any(x["n"] == r for x in locs))
    res["proveedores"] = {}
    for p in PROVIDERS:
        d = jq(cfg, "provider", "show", "-n", p, "--query", "{estado:registrationState}")
        res["proveedores"][p] = d.get("estado") if isinstance(d, dict) and "error" not in d else d
    pa = jq(cfg, "rest", "--method", "get", "--url",
            f"/subscriptions/{sub}/providers/Microsoft.Authorization/policyAssignments?api-version=2022-06-01")
    items = pa.get("value", []) if isinstance(pa, dict) else []
    res["politicas"] = {"asignaciones": len(items), "error": pa.get("error") if isinstance(pa, dict) else None,
                        "detalle": [{"nombre": i.get("properties", {}).get("displayName"),
                                     "efecto": (i.get("properties", {}).get("parameters", {}) or {}).get("effect", {}).get("value")}
                                    for i in items[:20]]}
    perm = jq(cfg, "rest", "--method", "get", "--url", f"/subscriptions/{sub}/providers/Microsoft.Authorization/permissions?api-version=2022-04-01")
    acts = []
    for v in (perm.get("value", []) if isinstance(perm, dict) else []):
        acts += v.get("actions", [])
    res["permisos_efectivos_suscripcion"] = {"acciones": sorted(set(acts))[:20], "error": perm.get("error") if isinstance(perm, dict) else None}
    rg = jq(cfg, "group", "list", "--query", "length(@)")
    res["grupos_de_recursos_existentes"] = rg
    roles = jq(cfg, "role", "assignment", "list", "--all", "--query", "[].roleDefinitionName")
    res["roles_propios"] = sorted(set(roles)) if isinstance(roles, list) else roles
    res["cuotas"] = {}
    for r in ("brazilsouth",):
        u = jq(cfg, "rest", "--method", "get", "--url",
               f"/subscriptions/{sub}/providers/Microsoft.App/locations/{r}/usages?api-version=2024-03-01")
        res["cuotas"][r] = ([{"n": x.get("name", {}).get("value"), "u": x.get("currentValue"), "l": x.get("limit")}
                             for x in u.get("value", [])] if isinstance(u, dict) and "error" not in u else u)
    su = jq(cfg, "rest", "--method", "get", "--url",
            f"/subscriptions/{sub}/providers/Microsoft.Storage/locations/brazilsouth/usages?api-version=2023-05-01")
    res["cuotas"]["storage_brazilsouth"] = ([{"n": x.get("name", {}).get("value"), "u": x.get("currentValue"), "l": x.get("limit")}
                                             for x in su.get("value", [])] if isinstance(su, dict) and "error" not in su else su)
    args.out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"ok": True, "secciones": list(res)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
