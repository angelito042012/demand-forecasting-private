"""Read a supplied physical-count form without changing it or historical data."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from collections import Counter
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from pathlib import Path

import openpyxl


def amount(value):
    if value is None or value == "" or isinstance(value, bool):
        raise ValueError("Missing or invalid count")
    try:
        n = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("Non-numeric count") from exc
    if not n.is_finite() or n < 0 or n != n.to_integral_value():
        raise ValueError("Count must be a nonnegative integer in the declared unit")
    return int(n)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(source: Path, package: Path, output: Path, confirmed_no_sales=False, confirmed_warehouse_id=None):
    if output.exists():
        raise FileExistsError("Use a new output directory; never overwrite received evidence")
    digest = sha(source)
    payload = json.loads((package / "workbook_payload.json").read_text(encoding="utf-8"))
    expected = {p["producto_id"]: p for p in payload["products"]}
    wb = openpyxl.load_workbook(source, read_only=True, data_only=False)
    sheet = wb["Conteo_50_productos"]
    metadata = {"count_date": sheet["C3"].value, "count_time": sheet["G3"].value,
                "warehouse_name": sheet["C4"].value, "responsible": sheet["G4"].value,
                "scope": sheet["C5"].value, "movement_statement": sheet["G5"].value}
    if any(v is None or str(v).strip() == "" for v in metadata.values()):
        raise ValueError("Incomplete form metadata")
    d = metadata["count_date"]
    if isinstance(d, datetime):
        d = d.date()
    if not isinstance(d, date):
        raise TypeError("Count date must be an Excel date")
    t = metadata["count_time"]
    if isinstance(t, datetime):
        t = t.time()
    if not isinstance(t, time):
        raise TypeError("Count time must be an Excel time")
    as_of = datetime.combine(d, t).isoformat() + "-05:00"
    records = []
    issues = []
    for row_index, values in enumerate(sheet.iter_rows(min_row=9, values_only=True), start=9):
        values = list(values[:8]) + [None] * max(0, 8 - len(values))
        if all(v is None for v in values):
            continue
        if any(isinstance(v, str) and v.startswith("=") for v in values):
            raise ValueError(f"Formula in received count row {row_index}")
        code, name, unit, meaning, free, reserved, blocked, note = values
        code = str(code).strip()
        if code not in expected:
            raise ValueError(f"Unexpected product at row {row_index}")
        origin = expected[code]
        if name != origin["producto"] or unit != origin["unidad"]:
            raise ValueError(f"Changed product description/unit at row {row_index}")
        if not isinstance(meaning, str) or not meaning.strip():
            raise ValueError(f"Missing physical-unit definition at row {row_index}")
        free, reserved, blocked = amount(free), amount(reserved), amount(blocked)
        records.append({"producto_id": code, "producto": name, "unidad_reporte": unit,
                        "unidad_descripcion_reportada": meaning.strip(), "cantidad_libre_reportada": free,
                        "cantidad_reservada_reportada": reserved, "cantidad_no_vendible_reportada": blocked,
                        "cantidad_fisica_total_reportada": free + reserved + blocked,
                        "fecha_hora_reportada": as_of, "zona_horaria": "America/Lima",
                        "almacen_nombre_reportado": metadata["warehouse_name"],
                        "almacen_id_candidato": origin["almacen"],
                        "almacen_id_confirmado": confirmed_warehouse_id == origin["almacen"],
                        "corte_sin_ventas_confirmado": confirmed_no_sales,
                        "naturaleza": "CONTEO_FISICO_REPORTADO_POR_USUARIO",
                        "verificacion_independiente": False,
                        "estado_uso": "APTO_COMO_SNAPSHOT_FECHADO" if confirmed_no_sales and confirmed_warehouse_id == origin["almacen"] else "PENDIENTE_CONFIRMAR_VENTAS_Y_ALMACEN",
                        "archivo_origen": source.name, "hoja_origen": sheet.title,
                        "fila_origen": row_index, "sha256_origen": digest, "observaciones": note})
    wb.close()
    codes = [r["producto_id"] for r in records]
    if len(codes) != 50 or len(set(codes)) != 50 or set(codes) != set(expected):
        raise ValueError("Count does not cover exactly the 50 selected codes")
    # These are questions about the source semantics, not errors repaired by inference.
    if not confirmed_no_sales:
        issues.append({"code": "VENTAS_DURANTE_CONTEO", "detail": "Only absence of receptions was reported; sales/cutoff consistency not confirmed."})
    if confirmed_warehouse_id != "1":
        issues.append({"code": "MAPEO_ALMACEN", "detail": "Almacen Principal supplied; mapping to original warehouse ID 1 awaits confirmation."})
    issues.extend([
        {"code": "BRECHA_OCTUBRE", "detail": "Sales/purchases end September 30; count is October 18. Missing days are unknown, not zero."},
        {"code": "PEDIDOS_PENDIENTES", "detail": "Count does not report incoming orders; unknown, not zero."},
    ])
    output.mkdir(parents=True)
    backup = output / source.name
    shutil.copy2(source, backup)
    assert sha(backup) == digest == sha(source)
    with (output / "conteo_reportado.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    totals = {k: sum(r[k] for r in records) for k in
              ("cantidad_libre_reportada", "cantidad_reservada_reportada", "cantidad_no_vendible_reportada")}
    result = {"source_sha256": digest, "source_unchanged": True, "metadata": metadata,
              "reported_as_of": as_of, "source_nature": "USER_SUPPLIED_PHYSICAL_COUNT_NOT_INDEPENDENTLY_VERIFIED",
              "rows": 50, "distinct_codes": 50, "complete_group": True, "names_units_match": True,
              "quantities_complete_nonnegative_integers": True, "formulas_in_count": 0,
              "zero_free_products": sum(r["cantidad_libre_reportada"] == 0 for r in records),
              "totals_in_report_units": totals,
              "physical_unit_definitions": dict(Counter(r["unidad_descripcion_reportada"] for r in records)),
              "user_confirmation": {"no_sales_during_count": confirmed_no_sales, "warehouse_id": confirmed_warehouse_id,
                                    "evidence": "Direct user reply in this Codex conversation, 18/10/2026"},
              "pending_questions": issues,
              "snapshot_ready": confirmed_no_sales and confirmed_warehouse_id == "1",
              "current_replenishment_ready": False,
              "historical_stock_reconciled": False, "no_database_models_or_ui_changed": True}
    (output / "review.json").write_text(json.dumps(result, default=str, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "metadata"}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, default=Path("artifacts/private/datos_preparados_v1"))
    parser.add_argument("--source", type=Path)
    parser.add_argument("--output", type=Path, default=Path("artifacts/private/conteo_recibido_20261018_v1"))
    parser.add_argument("--confirmed-no-sales", action="store_true")
    parser.add_argument("--confirmed-warehouse-id")
    args = parser.parse_args()
    main(args.source or args.package / "Solicitud_conteo_50_productos.xlsx", args.package, args.output,
         args.confirmed_no_sales, args.confirmed_warehouse_id)
