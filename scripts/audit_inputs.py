"""Read-only structural audit; never exports customer or employee records."""
import argparse
import calendar
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

import openpyxl


def audit(folder):
    results = []
    months = {"marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8}
    for name, month in months.items():
        path = folder / f"{name}.xlsx"
        book = openpyxl.load_workbook(path, read_only=True, data_only=True)
        for sheet in book:
            rows = sheet.iter_rows(values_only=True)
            headers = None
            for header_row, row in enumerate(rows, 1):
                if "ID_PEDIDO" in row and "FECHA" in row:
                    headers = [str(v).strip() if v is not None else "" for v in row]
                    break
            if headers is None:
                raise ValueError(f"Missing headers: {path.name}/{sheet.title}")
            counts, statuses, doc_types = Counter(), Counter(), Counter()
            dates, skus, categories, stores, seen = [], set(), set(), set(), set()
            positive_total = 0.0
            for row in rows:
                if not any(v is not None for v in row):
                    continue
                counts["nonempty"] += 1
                record = dict(zip(headers, row))
                date = record.get("FECHA")
                if isinstance(date, datetime):
                    dates.append(date)
                    if (date.year, date.month) != (2026, month):
                        counts["outside_expected_month"] += 1
                else:
                    counts["invalid_date"] += 1
                amount = record.get("TOTAL_LINEA", record.get("VEN_TOTAL"))
                if isinstance(amount, (int, float)):
                    counts["positive" if amount > 0 else "negative" if amount < 0 else "zero"] += 1
                else:
                    counts["invalid_amount"] += 1
                if record.get("ID_PEDIDO") in (None, 0):
                    counts["missing_or_zero_order"] += 1
                for field in ("ID_ARTICULO", "CANTIDAD", "GRUPO", "ID_ALMACEN", "CANTIDAD_UM_BASE", "EQUIVALENCIA"):
                    if record.get(field) is None or record.get(field) == "":
                        counts[f"missing_{field}"] += 1
                quantity = record.get("CANTIDAD")
                if isinstance(quantity, (int, float)) and quantity <= 0:
                    counts["nonpositive_quantity"] += 1
                if record.get("ID_PEDIDO") not in (None, 0) and record.get("ID_ARTICULO") is not None and record.get("GRUPO") and isinstance(amount, (int, float)) and amount > 0:
                    counts["positive_identified_lines"] += 1
                    positive_total += amount
                    skus.add(str(record["ID_ARTICULO"]))
                    categories.add(str(record["GRUPO"]).strip())
                if record.get("ID_TIENDA") is not None:
                    stores.add(str(record["ID_TIENDA"]))
                statuses[str(record.get("VEN_ESTADO"))] += 1
                doc_types[str(record.get("TIPO_DOC"))] += 1
                signature = tuple(row)
                if signature in seen:
                    counts["exact_repeated_rows"] += 1
                seen.add(signature)
            days = {d.day for d in dates if d.year == 2026 and d.month == month}
            results.append({
                "file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "sheet": sheet.title, "rows": sheet.max_row, "header_row": header_row,
                "columns": headers, "counts": dict(counts),
                "first": min(dates).isoformat() if dates else None,
                "last": max(dates).isoformat() if dates else None,
                "days": len(days), "missing_calendar_days": sorted(set(range(1, calendar.monthrange(2026, month)[1] + 1)) - days),
                "skus": len(skus), "categories": len(categories), "store_ids": sorted(stores),
                "positive_line_total": round(positive_total, 2),
                "statuses": dict(statuses), "document_types": dict(doc_types),
            })
        book.close()
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    data = audit(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    for item in data:
        print(json.dumps({k: v for k, v in item.items() if k not in ("columns", "sha256")}, ensure_ascii=False))
