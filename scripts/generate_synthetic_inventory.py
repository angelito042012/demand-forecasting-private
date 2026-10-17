"""Generate a labeled inventory scenario, never empirical inventory evidence."""
import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import median

import openpyxl

LABEL = "SYNTHETIC_NOT_REAL_INVENTORY"
START = date(2026, 8, 1)
END = date(2026, 8, 31)


def write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def generate(source, destination):
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("Output directory is not empty; choose a new scenario directory.")
    prices, categories = defaultdict(list), defaultdict(list)
    july = Counter()
    demand = defaultdict(Counter)
    inputs = []
    for month in ("marzo", "abril", "mayo", "junio", "julio", "agosto"):
        path = source / (month + ".xlsx")
        inputs.append({"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        book = openpyxl.load_workbook(path, read_only=True, data_only=True)
        rows = book.active.iter_rows(values_only=True)
        next(rows)
        headers = next(rows)
        for row in rows:
            record = dict(zip(headers, row))
            timestamp = record.get("FECHA")
            if not isinstance(timestamp, datetime):
                continue
            day = timestamp.date()
            qty = record.get("CANTIDAD_UM_BASE")
            amount = record.get("TOTAL_LINEA")
            if record.get("TIPO_DOC") == 7 or not isinstance(qty, (int, float)) or qty <= 0 or not isinstance(amount, (int, float)) or amount <= 0:
                continue
            sku = str(record["ID_ARTICULO"])
            if day < START:
                equivalence = record["EQUIVALENCIA"]
                price = record["PRECIO"]
                if equivalence <= 0 or price <= 0:
                    raise ValueError("Invalid unit price or equivalence")
                prices[sku].append(price / equivalence)
                categories[sku].append((day, str(record["GRUPO"]).strip()))
                if date(2026, 7, 4) <= day <= date(2026, 7, 31):
                    july[sku] += qty
            elif START <= day <= END:
                demand[day][sku] += qty
        book.close()
    parameters = []
    stocks, initial, targets = {}, {}, {}
    for sku in sorted(prices):
        history = categories[sku]
        latest_date = max(day for day, _ in history)
        candidates = {category for day, category in history if day == latest_date}
        frequencies = Counter(category for _, category in history)
        category = sorted(candidates, key=lambda c: (-frequencies[c], c))[0]
        average = july[sku] / 28
        stocks[sku] = initial[sku] = math.ceil(average * 14)
        targets[sku] = math.ceil(average * 21)
        parameters.append(dict(sku=sku, category_at_cutoff=category, provenance=LABEL,
            cutoff="2026-07-31", reference_daily_units=average,
            assumed_unit_cost=round(median(prices[sku]) * 0.65, 4),
            lead_time_days=7, review_days=7, safety_days=7,
            order_multiple=1, minimum_order=1, annual_holding_rate=0.20,
            initial_stock=initial[sku], initial_in_transit=0, reference_target=targets[sku]))
    arrivals = defaultdict(Counter)
    transit = Counter()
    movements, orders, daily = [], [], []
    received, issued = Counter(), Counter()
    skipped_units = 0
    unknown_skus = set()
    for offset in range(31):
        day = START + timedelta(days=offset)
        for sku, qty in sorted(arrivals[day].items()):
            stocks[sku] += qty
            transit[sku] -= qty
            received[sku] += qty
            movements.append(dict(date=day.isoformat(), sku=sku, type="simulated_receipt", quantity=qty, provenance=LABEL))
        for sku, qty in sorted(demand[day].items()):
            if sku not in stocks:
                unknown_skus.add(sku)
                skipped_units += qty
                continue
            served = min(stocks[sku], qty)
            stocks[sku] -= served
            issued[sku] += served
            if served:
                movements.append(dict(date=day.isoformat(), sku=sku, type="simulated_issue", quantity=-served, provenance=LABEL))
            daily.append(dict(date=day.isoformat(), sku=sku, observed_sales_proxy_units=qty,
                simulated_served_units=served, simulated_unserved_units=qty-served,
                provenance=LABEL))
        if offset % 7 == 0:
            for sku in sorted(stocks):
                qty = max(0, math.ceil(targets[sku] - stocks[sku] - transit[sku]))
                if qty:
                    due = day + timedelta(days=7)
                    arrivals[due][sku] += qty
                    transit[sku] += qty
                    orders.append(dict(order_date=day.isoformat(), arrival_date=due.isoformat(), sku=sku, quantity=qty, provenance=LABEL))
        for sku in stocks:
            assert stocks[sku] >= -1e-8
            assert abs(initial[sku] + received[sku] - issued[sku] - stocks[sku]) < 1e-6
            assert transit[sku] >= 0
    destination.mkdir(parents=True, exist_ok=True)
    write_csv(destination / "parameters_and_initial_stock.csv", parameters, list(parameters[0]))
    write_csv(destination / "movements_reference.csv", movements, ["date", "sku", "type", "quantity", "provenance"])
    write_csv(destination / "orders_reference.csv", orders, ["order_date", "arrival_date", "sku", "quantity", "provenance"])
    write_csv(destination / "daily_reference.csv", daily, ["date", "sku", "observed_sales_proxy_units", "simulated_served_units", "simulated_unserved_units", "provenance"])
    final = [dict(sku=sku, final_stock=stocks[sku], pending_units=transit[sku], provenance=LABEL) for sku in sorted(stocks)]
    write_csv(destination / "final_stock_reference.csv", final, ["sku", "final_stock", "pending_units", "provenance"])
    manifest = dict(provenance=LABEL, scenario="reference_v1", calibration_end="2026-07-31",
        evaluation_period=[START.isoformat(), END.isoformat()], inputs=inputs,
        eligible_skus=len(parameters), august_new_skus_excluded=len(unknown_skus),
        august_units_excluded=skipped_units, simulated_movements=len(movements),
        simulated_orders=len(orders), balance_checks="passed_every_day_every_sku",
        warning="Sales are a demand proxy. This is not actual inventory, actual procurement, or actual policy. No empirical improvement established.")
    (destination / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (destination / "README.md").write_text("# Inventario simulado\n\nDatos sintéticos con supuestos; no corresponden al inventario real de la empresa. Ventas de agosto usadas como proxy de demanda, parámetros calculados solo con marzo-julio. No usar para entrenar pronósticos ni para afirmar mejoras empíricas. Consultar docs/DECISIONES_DATOS.md en la raíz del proyecto.\n", encoding="utf-8")
    return {k: v for k, v in manifest.items() if k != "inputs"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(json.dumps(generate(args.source, args.destination), ensure_ascii=False))
