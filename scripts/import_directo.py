"""Importación directa de ventas (enero-septiembre) a Atlas, sin cola de jobs.

Uso:
  python scripts/import_directo.py

Conecta a Atlas, limpia jobs fallidos y month_locks, e importa
los 9 archivos Excel desde fuentes_originales/.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from pymongo import MongoClient
from pipeline.data.importer import import_workbook

ATLAS_URI = os.environ["MONGODB_URI"]
DB_NAME = os.environ.get("MONGODB_DATABASE", "demand_forecasting_pub")
FUENTES = Path(r"D:\PROYECTOS2\Entrega_equipo_20261023\fuentes_originales")

FILES = [
    ("enero.xlsx",     "2026-01"),
    ("febrero.xlsx",   "2026-02"),
    ("marzo.xlsx",     "2026-03"),
    ("abril.xlsx",     "2026-04"),
    ("mayo.xlsx",      "2026-05"),
    ("junio.xlsx",     "2026-06"),
    ("julio.xlsx",     "2026-07"),
    ("agosto.xlsx",    "2026-08"),
    ("setiembre.xlsx", "2026-09"),
]


def main():
    client = MongoClient(ATLAS_URI)
    db = client[DB_NAME]

    # Importar cada mes
    for filename, month in FILES:
        path = FUENTES / filename
        if not path.is_file():
            print(f"  SKIP {filename} — archivo no encontrado")
            continue
        print(f"  Importando {filename} ({month})...", end=" ", flush=True)
        try:
            rep = import_workbook(path, db, expected_month=month)
            print(f"OK — {rep.ventas_aceptadas} ventas, {rep.notas_credito} NC, "
                  f"{rep.rechazadas} rechazadas, estado={rep.estado}")
        except Exception as exc:
            print(f"ERROR — {exc}")

    # 3. Resumen
    total_sales = db.sales.count_documents({})
    total_imports = db.imports.count_documents({"estado": "completed"})
    print(f"\nTotal: {total_sales} ventas en BD, {total_imports} importaciones completadas")
    client.close()


if __name__ == "__main__":
    main()
