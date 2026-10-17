"""Compara la base v1 con la v2 (solo lectura) y verifica la recarga idempotente de v2.

Uso: python -m scripts.compare_v1_v2 [--reload SRC] [--out ruta.json]
Compara por mes y coleccion: conteos, suma de importes (Decimal) y el multiconjunto de
lineas normalizadas (documento, pedido, fecha, sku, almacen, cantidades, precio, importe,
tipo_doc, categoria_original) sin usar linea_id, cuya clave cambio entre esquemas.
Con --reload recarga los seis Excel sobre v2 y exige cero inserciones/conflictos/rechazos.
No modifica v1 ni los Excel.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path

from pipeline.data.importer import _canon, get_client, import_folder


def _norm(d: dict) -> str:
    imp = d["importe"].to_decimal() if d.get("importe") is not None else None
    pre = d.get("precio_unitario_original")
    pre = pre.to_decimal() if pre is not None else None
    parts = [d["doc_hash"], str(d.get("pedido_id")), d["fecha"], d["sku"], d["almacen"],
             _canon(d["cantidad_original"]), _canon(d["cantidad_base"]),
             "" if pre is None else _canon(pre), "" if imp is None else _canon(imp),
             str(d["tipo_doc"]), d.get("categoria_original", "")]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def summarize(db) -> dict:
    out: dict = {}
    for coll in ("sales", "credit_notes"):
        by_month: dict = {}
        for d in db[coll].find({}, {"_id": 0}):
            m = by_month.setdefault(d["mes"], {"n": 0, "suma": Decimal(0), "lineas": Counter()})
            m["n"] += 1
            m["suma"] += d["importe"].to_decimal()
            m["lineas"][_norm(d)] += 1
        out[coll] = by_month
    return out


def compare(db1, db2) -> dict:
    a, b = summarize(db1), summarize(db2)
    report: dict = {"colecciones": {}, "coincide": True}
    for coll in a:
        rows = {}
        for mes in sorted(set(a[coll]) | set(b[coll])):
            x, y = a[coll].get(mes), b[coll].get(mes)
            xs, ys = (x or {}), (y or {})
            same = bool(x and y) and x["n"] == y["n"] and x["suma"] == y["suma"] and x["lineas"] == y["lineas"]
            rows[mes] = {"v1_n": xs.get("n", 0), "v2_n": ys.get("n", 0),
                         "v1_suma": f"{xs.get('suma', Decimal(0)):.2f}",
                         "v2_suma": f"{ys.get('suma', Decimal(0)):.2f}",
                         "lineas_normalizadas_iguales": same,
                         "solo_v1": sum((xs.get("lineas", Counter()) - ys.get("lineas", Counter())).values()),
                         "solo_v2": sum((ys.get("lineas", Counter()) - xs.get("lineas", Counter())).values())}
            report["coincide"] &= same
        report["colecciones"][coll] = rows
    for db, k in ((db1, "v1"), (db2, "v2")):
        report[f"{k}_duplicados_linea_id"] = {c: db[c].count_documents({}) - len(db[c].distinct("linea_id"))
                                              for c in ("sales", "credit_notes")}
    report["v2_conflictos"] = db2.import_conflicts.count_documents({})
    report["v2_rechazos"] = db2.import_rejects.count_documents({})
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--v1", default="demand_forecasting_dev")
    ap.add_argument("--v2", default="demand_forecasting_v2")
    ap.add_argument("--reload", type=Path, help="carpeta con los seis Excel para repetir la carga en v2")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)
    client = get_client()
    db1, db2 = client[args.v1], client[args.v2]
    result: dict = {}
    if args.reload:
        before = (db2.sales.count_documents({}), db2.credit_notes.count_documents({}))
        reps = import_folder(args.reload, db2)
        result["recarga_v2"] = {"conteos_antes": before,
                                "conteos_despues": (db2.sales.count_documents({}),
                                                    db2.credit_notes.count_documents({})),
                                "importaciones": [{"archivo": r.archivo, "noop": r.noop, "estado": r.estado,
                                                   "insertadas": r.insertadas, "en_conflicto": r.en_conflicto}
                                                  for r in reps]}
        result["recarga_ok"] = (before == result["recarga_v2"]["conteos_despues"]
                                and all(r.insertadas == 0 and r.en_conflicto == 0 for r in reps))
    result["comparacion"] = compare(db1, db2)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    print(text)
    return 0 if result["comparacion"]["coincide"] and result.get("recarga_ok", True) else 1


if __name__ == "__main__":
    sys.exit(main())
