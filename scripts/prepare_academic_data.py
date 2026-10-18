"""Prepare a provenance-preserving academic dataset; never writes source books/DBs.

Inventory is a retrospective conditional construction, NOT physical stock or an
input to forecasting/backtesting. Existing T12 remains independent.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

import openpyxl

VERSION = "academico_v1"
CUTOFF = date(2026, 7, 31)
START = date(2026, 3, 1)
END = date(2026, 9, 30)
EXCLUDED_FORECAST_DAYS = {date(2026, 4, 3), date(2026, 4, 12), date(2026, 6, 7)}
ZERO = Decimal(0)
TOL = Decimal("0.000001")
FIELDS = ["registro_id", "fecha", "producto_id", "producto", "categoria", "almacen",
          "unidad", "cantidad", "moneda", "importe", "tipo_documento", "documento_id",
          "clasificacion", "grupo_repeticion", "ocurrencia", "incluido_grupo",
          "dia_excluido_pronostico", "archivo", "hoja", "fila", "sha256_origen"]


def number(value):
    if value is None or value == "" or isinstance(value, bool):
        return None
    try:
        n = Decimal(str(value))
        return n if n.is_finite() else None
    except InvalidOperation:
        return None


def text(value):
    if value is None:
        return ""
    if isinstance(value, (int, float, Decimal)):
        n = number(value)
        if n is not None and n == n.to_integral_value():
            return str(int(n))
    return str(value).strip()


def serialize(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, set):
        return sorted(value)
    raise TypeError(type(value).__name__)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=serialize), encoding="utf-8")


def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow({k: serialize(v) if isinstance(v, (date, datetime, Decimal, set)) else v for k, v in r.items() if k in fields})


def currency(value):
    v = text(value).upper()
    if "S/" in v or "SOLES" in v:
        return "PEN"
    if "$" in v and "D" in v:
        return "USD"
    return v


def classify(kind, raw):
    """Processing disposition, never an invented explanation of business meaning."""
    qty, eq, base, amount = (number(raw.get(k)) for k in ("CANTIDAD", "EQUIVALENCIA", "CANTIDAD_UM_BASE", "TOTAL_LINEA"))
    d = raw.get("FECHA")
    if not isinstance(d, (date, datetime)):
        return "CUARENTENA", "FECHA_NO_VALIDA"
    if any(v is None for v in (qty, eq, base, amount)) or eq <= 0:
        return "CUARENTENA", "CANTIDADES_NO_VALIDAS"
    if abs(qty * eq - base) > TOL:
        return "CUARENTENA", "CONVERSION_NO_COINCIDE"
    status = text(raw.get("VEN_ESTADO" if kind == "ventas" else "ESTADO")).upper()
    if status != "ACTIVO" or not text(raw.get("ID_ARTICULO")) or not text(raw.get("ID_ALMACEN")) or not text(raw.get("UM_BASE")):
        return "CUARENTENA", "ESTADO_O_CLAVE_NO_VALIDOS"
    if kind == "ventas" and text(raw.get("TIPO_DOC")) == "7":
        return "CREDITO", "DOCUMENTO_FINANCIERO_SIN_RETORNO_FISICO_INFERIDO"
    if base <= 0:
        return "CUARENTENA", "CANTIDAD_NO_POSITIVA"
    if kind == "compras" and amount < 0:
        return "CUARENTENA", "IMPORTE_NEGATIVO_CON_CANTIDAD_POSITIVA"
    if kind == "ventas" and amount <= 0:
        return "CUARENTENA", "VENTA_SIN_IMPORTE_POSITIVO"
    if kind == "compras" and amount == 0:
        return "COMPRA_SIN_CARGO_REGISTRADO", "CANTIDAD_CONSERVADA_SIN_INFERIR_BONIFICACION"
    return ("VENTA" if kind == "ventas" else "COMPRA"), "CONSERVADO"


def initial_minimum(daily_net):
    cumulative = minimum = ZERO
    for _, net in sorted(daily_net.items()):
        cumulative += net
        minimum = min(minimum, cumulative)
    return -minimum


def choose_group(records, size):
    profiles = defaultdict(lambda: {"sale_months": set(), "purchase_months": set(), "sale_days": set(),
                                    "sale_units": ZERO, "purchase_units": ZERO, "name": "", "category": "", "latest": START})
    for r in records:
        if r["fecha"] > CUTOFF or r["clasificacion"] not in {"VENTA", "COMPRA", "COMPRA_SIN_CARGO_REGISTRADO"}:
            continue
        key = (r["producto_id"], r["almacen"], r["unidad"])
        p = profiles[key]
        if r["clasificacion"] == "VENTA":
            p["sale_months"].add(r["fecha"].month)
            p["sale_days"].add(r["fecha"])
            p["sale_units"] += r["cantidad"]
            if r["fecha"] >= p["latest"]:
                p["name"], p["category"], p["latest"] = r["producto"], r["categoria"], r["fecha"]
        else:
            p["purchase_months"].add(r["fecha"].month)
            p["purchase_units"] += r["cantidad"]
    eligible = [key for key, p in profiles.items() if len(p["sale_months"]) == 5 and len(p["purchase_months"]) >= 2 and key[2] == "UND"]
    ranked = sorted(eligible, key=lambda key: (-len(profiles[key]["sale_days"]), -profiles[key]["sale_units"], key))
    selected = ranked[:size]
    if len(selected) < size:
        raise ValueError(f"Only {len(selected)} eligible; do not silently relax selection")
    ranking = {key: i + 1 for i, key in enumerate(ranked)}
    rows = []
    for key, p in sorted(profiles.items()):
        reasons = []
        if len(p["sale_months"]) != 5:
            reasons.append("SIN_VENTAS_EN_LOS_CINCO_MESES")
        if len(p["purchase_months"]) < 2:
            reasons.append("COMPRAS_EN_MENOS_DE_DOS_MESES")
        if key[2] != "UND":
            reasons.append("UNIDAD_DISTINTA")
        chosen = key in selected
        rows.append({"producto_id": key[0], "producto": p["name"], "categoria": p["category"],
                     "almacen": key[1], "unidad": key[2], "meses_venta": len(p["sale_months"]),
                     "meses_compra": len(p["purchase_months"]), "dias_venta": len(p["sale_days"]),
                     "unidades_vendidas": p["sale_units"], "rango": ranking.get(key), "seleccionado": chosen,
                     "motivo": "SELECCIONADO" if chosen else "|".join(reasons) if reasons else "FUERA_DE_LOS_50_PRIMEROS",
                     "corte_seleccion": CUTOFF})
    return set(selected), rows, len(eligible)


def build_inventory(records, selected, catalog):
    daily = defaultdict(lambda: defaultdict(lambda: {"entradas": ZERO, "salidas": ZERO, "entradas_segundas_copias": ZERO}))
    for r in records:
        key = (r["producto_id"], r["almacen"], r["unidad"])
        if key not in selected:
            continue
        if r["clasificacion"] == "VENTA":
            daily[key][r["fecha"]]["salidas"] += r["cantidad"]
        elif r["clasificacion"] in {"COMPRA", "COMPRA_SIN_CARGO_REGISTRADO"}:
            daily[key][r["fecha"]]["entradas"] += r["cantidad"]
            if r["ocurrencia"] > 1:
                daily[key][r["fecha"]]["entradas_segundas_copias"] += r["cantidad"]
    balances, summary = [], []
    for key in sorted(selected):
        net = {d: v["entradas"] - v["salidas"] for d, v in daily[key].items()}
        alternate = {d: v["entradas"] - v["entradas_segundas_copias"] - v["salidas"] for d, v in daily[key].items()}
        opening = initial_minimum(net)
        alternate_opening = initial_minimum(alternate)
        current = opening
        bought = sold = repeated_units = ZERO
        current_day = START
        while current_day <= END:
            movement = daily[key].get(current_day, {"entradas": ZERO, "salidas": ZERO, "entradas_segundas_copias": ZERO})
            before = current
            current += movement["entradas"] - movement["salidas"]
            bought += movement["entradas"]
            sold += movement["salidas"]
            repeated_units += movement["entradas_segundas_copias"]
            assert current >= 0
            balances.append({"fecha": current_day, "producto_id": key[0], "almacen": key[1], "unidad": key[2],
                             "saldo_inicio_dia": before, "entradas_documentadas": movement["entradas"],
                             "salidas_documentadas": movement["salidas"], "ajustes_incorporados": ZERO,
                             "saldo_fin_dia": current, "origen_saldo": "CALCULADO_BAJO_SUPUESTOS",
                             "conteo_fisico_verificado": False})
            assert before + movement["entradas"] - movement["salidas"] == current
            current_day += timedelta(days=1)
        assert opening + bought - sold == current
        summary.append({"producto_id": key[0], "producto": catalog[key]["producto"], "categoria": catalog[key]["categoria"],
                        "almacen": key[1], "unidad": key[2], "fecha_inicial": START, "saldo_inicial_minimo_calculado": opening,
                        "entradas_documentadas": bought, "salidas_documentadas": sold, "ajustes_incorporados": ZERO,
                        "fecha_final": END, "saldo_final_calculado": current,
                        "unidades_en_segundas_copias": repeated_units,
                        "saldo_inicial_alternativo_sin_segundas_copias": alternate_opening,
                        "saldo_final_alternativo_sin_segundas_copias": alternate_opening + bought - repeated_units - sold,
                        "conteo_fisico": None, "origen_saldo": "CALCULADO_RETROSPECTIVO_NO_USAR_PARA_ENTRENAR"})
    return summary, balances


def main(source, output, group_size=50):
    if output.exists():
        raise FileExistsError(f"Output exists; use a new version directory: {output}")
    files = sorted(source.glob("*.xlsx"))
    if len(files) != 14:
        raise ValueError("Expected exactly 14 source workbooks")
    rows, sources, issues = [], [], []
    first_seen, occurrence = {}, Counter()
    known = {r["file"]: r["sha256"] for r in json.loads((Path(__file__).resolve().parents[1] / "artifacts/private/auditoria_14_excel/audit.json").read_text(encoding="utf-8"))["files"]}
    for path in files:
        digest = sha(path)
        if known.get(path.name) != digest:
            raise ValueError(f"Source changed since audited: {path.name}")
        kind = "compras" if path.stem.startswith("compra") else "ventas"
        book = openpyxl.load_workbook(path, read_only=True, data_only=True)
        if book.sheetnames != ["Hoja1"]:
            raise ValueError("Unexpected sheet layout")
        iterator = book["Hoja1"].iter_rows(min_row=2, values_only=True)
        headers = [text(v) for v in next(iterator)]
        file_counts = Counter()
        original_totals, classified_totals = defaultdict(lambda: ZERO), defaultdict(lambda: ZERO)
        for row_num, raw_values in enumerate(iterator, 3):
            if not any(v is not None for v in raw_values):
                continue
            raw = dict(zip(headers, raw_values))
            status, reason = classify(kind, raw)
            doc_date = raw.get("FECHA")
            d = doc_date.date() if isinstance(doc_date, datetime) else doc_date
            if not START <= d <= END:
                raise ValueError("Date outside declared data window")
            signature = hashlib.sha256(json.dumps(raw_values, ensure_ascii=False, default=serialize).encode()).hexdigest()
            repeat_key = (kind, signature)
            occurrence[repeat_key] += 1
            first_seen.setdefault(repeat_key, (path.name, row_num))
            cur = currency(raw.get("MONEDA"))
            doc_id = hashlib.sha256((kind + "|" + text(raw.get("TIPO_DOC")) + "|" + text(raw.get("SERIE_NUMERO")) + "|" + text(raw.get("ID_PROVEEDOR")) + "|" + text(raw.get("ID_PEDIDO"))).encode()).hexdigest()[:24]
            r = {"registro_id": hashlib.sha256(f"{digest}:Hoja1:{row_num}".encode()).hexdigest()[:24],
                 "fecha": d, "producto_id": text(raw.get("ID_ARTICULO")), "producto": text(raw.get("ARTICULO")),
                 "categoria": text(raw.get("GRUPO")), "almacen": text(raw.get("ID_ALMACEN")),
                 "unidad": text(raw.get("UM_BASE")).upper(), "cantidad": number(raw.get("CANTIDAD_UM_BASE")),
                 "moneda": cur, "importe": number(raw.get("TOTAL_LINEA")), "tipo_documento": text(raw.get("TIPO_DOC")),
                 "documento_id": doc_id, "clasificacion": status, "grupo_repeticion": "", "ocurrencia": occurrence[repeat_key],
                 "incluido_grupo": False, "dia_excluido_pronostico": d in EXCLUDED_FORECAST_DAYS,
                 "archivo": path.name, "hoja": "Hoja1", "fila": row_num, "sha256_origen": digest,
                 "_kind": kind, "_signature": repeat_key, "_reason": reason}
            rows.append(r)
            file_counts[status] += 1
            original_totals[cur] += number(raw.get("TOTAL_LINEA")) or ZERO
            classified_totals[cur] += r["importe"] or ZERO
            if status == "CUARENTENA" or occurrence[repeat_key] > 1:
                issues.append({"registro_id": r["registro_id"], "archivo": path.name, "hoja": "Hoja1", "fila": row_num,
                               "producto_id": r["producto_id"], "cantidad_original": number(raw.get("CANTIDAD")),
                               "equivalencia": number(raw.get("EQUIVALENCIA")), "cantidad_base": r["cantidad"],
                               "importe": r["importe"], "moneda": cur,
                               "motivo": reason if status == "CUARENTENA" else "FILA_IDENTICA_CONSERVADA",
                               "tratamiento": "SEPARADA_DEL_CALCULO" if status == "CUARENTENA" else "CONSERVADA_CON_MARCA",
                               "significado_empresarial_confirmado": False})
        book.close()
        assert original_totals == classified_totals
        assert sha(path) == digest
        sources.append({"archivo": path.name, "tipo": kind, "sha256": digest, "filas": sum(file_counts.values()),
                        "clasificaciones": dict(file_counts), "importes_por_moneda": dict(original_totals)})
        print(json.dumps({"file": path.name, "rows": sum(file_counts.values()), "classes": dict(file_counts)}), flush=True)
    for r in rows:
        if occurrence[r["_signature"]] > 1:
            r["grupo_repeticion"] = r["_signature"][1][:24]
    selected, candidates, eligible = choose_group(rows, group_size)
    for r in rows:
        r["incluido_grupo"] = (r["producto_id"], r["almacen"], r["unidad"]) in selected
    catalog = {(r["producto_id"], r["almacen"], r["unidad"]): r for r in candidates if r["seleccionado"]}
    stock, daily = build_inventory(rows, selected, catalog)
    classes = Counter(r["clasificacion"] for r in rows)
    assert len(rows) == sum(s["filas"] for s in sources) == len({r["registro_id"] for r in rows})
    sales = [r for r in rows if r["clasificacion"] == "VENTA"]
    purchases = [r for r in rows if r["clasificacion"] in {"COMPRA", "COMPRA_SIN_CARGO_REGISTRADO"}]
    credits = [r for r in rows if r["clasificacion"] == "CREDITO"]
    quarantine = [r for r in rows if r["clasificacion"] == "CUARENTENA"]
    assert len(sales) + len(purchases) + len(credits) + len(quarantine) == len(rows)
    chosen_sales = [r for r in sales if r["incluido_grupo"]]
    chosen_purchases = [r for r in purchases if r["incluido_grupo"]]
    chosen_credits = [r for r in credits if r["incluido_grupo"]]
    stock_by_key = {(r["producto_id"], r["almacen"], r["unidad"]): r for r in stock}
    for key in selected:
        assert stock_by_key[key]["salidas_documentadas"] == sum((r["cantidad"] for r in chosen_sales if (r["producto_id"], r["almacen"], r["unidad"]) == key), ZERO)
        assert stock_by_key[key]["entradas_documentadas"] == sum((r["cantidad"] for r in chosen_purchases if (r["producto_id"], r["almacen"], r["unidad"]) == key), ZERO)
    output.mkdir(parents=True)
    original_dir, normalized_dir, group_dir = (output / name for name in ("00_originales", "01_normalizados", "02_grupo"))
    for directory in (original_dir, normalized_dir, group_dir):
        directory.mkdir()
    for path in files:
        shutil.copy2(path, original_dir / path.name)
        assert sha(original_dir / path.name) == known[path.name] == sha(path)
    for name, records in (("ventas", sales), ("compras", purchases), ("creditos", credits), ("cuarentena", quarantine)):
        write_csv(normalized_dir / f"{name}.csv", records, FIELDS)
    write_csv(normalized_dir / "clasificacion_completa.csv", rows, FIELDS)
    write_csv(normalized_dir / "candidatos_grupo.csv", candidates, list(candidates[0]))
    write_csv(normalized_dir / "incidencias.csv", issues, list(issues[0]))
    for name, records in (("ventas", chosen_sales), ("compras", chosen_purchases), ("creditos", chosen_credits)):
        write_csv(group_dir / f"{name}_grupo.csv", records, FIELDS)
    write_csv(group_dir / "productos.csv", list(catalog.values()), list(candidates[0]))
    write_csv(group_dir / "saldos_calculados.csv", stock, list(stock[0]))
    write_csv(group_dir / "balance_diario.csv", daily, list(daily[0]))
    # Explicit planning assumptions only; no operational recommendations are issued.
    parameters = [
        {"parametro": "fecha_entrada_compra", "valor": "FECHA_DOCUMENTO", "unidad": "fecha", "naturaleza": "SUPUESTO", "explicacion": "No hay fecha de recepcion fisica verificada"},
        {"parametro": "ajustes_incorporados", "valor": 0, "unidad": "unidades", "naturaleza": "SUPUESTO", "explicacion": "No afirma que no existieron ajustes"},
        {"parametro": "devoluciones_fisicas_incorporadas", "valor": 0, "unidad": "unidades", "naturaleza": "SUPUESTO", "explicacion": "Una nota de credito no prueba retorno fisico"},
        {"parametro": "plazo_entrega", "valor": 7, "unidad": "dias", "naturaleza": "SUPUESTO_CONFIGURABLE", "explicacion": "Sin fecha de pedido; no medido en facturas"},
        {"parametro": "revision_compras", "valor": 7, "unidad": "dias", "naturaleza": "SUPUESTO_CONFIGURABLE", "explicacion": "Frecuencia para un futuro ejercicio academico"},
        {"parametro": "reserva_cobertura", "valor": 7, "unidad": "dias", "naturaleza": "SUPUESTO_CONFIGURABLE", "explicacion": "Sin validacion de empresa ni optimizacion por resultados"},
        {"parametro": "multiplo_compra", "valor": 1, "unidad": "unidades", "naturaleza": "SUPUESTO_CONFIGURABLE", "explicacion": "El documento no identifica minimo comercial"},
        {"parametro": "pedidos_pendientes", "valor": None, "unidad": "unidades", "naturaleza": "NO_DISPONIBLE", "explicacion": "No confundir ausencia de reporte con cero"},
        {"parametro": "conteo_fisico", "valor": None, "unidad": "unidades", "naturaleza": "NO_DISPONIBLE", "explicacion": "No se ha contado mercaderia de la empresa"},
    ]
    write_csv(group_dir / "parametros.csv", parameters, list(parameters[0]))
    coverage = {"sales_rows": len(chosen_sales), "purchase_rows": len(chosen_purchases), "credit_rows": len(chosen_credits),
                "sale_units": sum((r["cantidad"] for r in chosen_sales), ZERO),
                "all_sale_units": sum((r["cantidad"] for r in sales), ZERO),
                "group_quarantine_rows": sum(r["incluido_grupo"] for r in quarantine),
                "group_repeated_extra_rows": sum(r["ocurrencia"] > 1 for r in chosen_purchases)}
    manifest = {"version": VERSION, "source_dir": str(source), "window_start": START, "window_end": END,
                "selection_cutoff": CUTOFF, "group_size": len(selected), "eligible_products": eligible,
                "selection_rule": "Five sale months Mar-Jul; purchases in >=2 months by Jul31; UND; rank sale days desc, units desc, key asc; top50.",
                "source_rows": len(rows), "class_counts": dict(classes), "coverage": coverage, "sources": sources,
                "inventory_nature": "RETROSPECTIVE_CONDITIONAL_MINIMUM_NOT_OBSERVED",
                "inventory_warning": "Opening stock is computed from March-September future net minima; forbidden for training, historical backtests or proof of real inventory.",
                "duplicate_rule": "KEEP_ALL_WITH_MARKS; alternate balances without second exact copies are sensitivity only",
                "no_database_or_models_changed": True, "source_hashes_verified": True,
                "validation": {"all_rows_classified_once": True, "amounts_reconcile_by_source_currency": True,
                               "daily_balances_conserve": True, "group_sales_and_purchases_reconcile": True,
                               "original_and_backup_hashes_match": True}}
    dump_json(output / "manifest.json", manifest)
    payload = {"manifest": manifest, "sales": chosen_sales, "purchases": chosen_purchases, "credits": chosen_credits,
               "products": sorted(catalog.values(), key=lambda x: x["rango"]), "stock": stock, "daily": daily,
               "parameters": parameters, "issues": issues,
               "source_counts": [{"archivo": s["archivo"], "tipo": s["tipo"], "filas": s["filas"], **s["clasificaciones"]} for s in sources]}
    # Remove internal lookup structures from the builder payload.
    for key in ("sales", "purchases", "credits"):
        payload[key] = [{k: v for k, v in r.items() if not k.startswith("_")} for r in payload[key]]
    dump_json(output / "workbook_payload.json", payload)
    print("RESULT " + json.dumps({"output": str(output), "classes": dict(classes), "eligible": eligible,
                                  "group_size": len(selected), "coverage": coverage,
                                  "daily_rows": len(daily), "validation": manifest["validation"]}, default=serialize), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path(r"C:\Users\rogel\Documents\Datos"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--group-size", type=int, default=50)
    args = parser.parse_args()
    main(args.source, args.output, args.group_size)
