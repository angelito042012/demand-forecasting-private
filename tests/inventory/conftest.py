"""Fuentes sinteticas para el importador del conteo reportado (T18); no usan datos comerciales.

R18: el Excel sintetico es un libro .xlsx REAL (openpyxl) con la misma disposicion que la plantilla recibida, y el CSV derivado se
genera desde ese libro, de modo que las pruebas pueden comprobar (y romper) la correspondencia derivado <-> documento.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
from pathlib import Path

from openpyxl import Workbook

GROUP_FIELDS = ["producto_id", "producto", "categoria", "almacen", "unidad", "seleccionado"]
COUNT_FIELDS = [
    "producto_id", "producto", "unidad_reporte", "unidad_descripcion_reportada", "cantidad_libre_reportada",
    "cantidad_reservada_reportada", "cantidad_no_vendible_reportada", "cantidad_fisica_total_reportada",
    "fecha_hora_reportada", "zona_horaria", "almacen_nombre_reportado", "almacen_id_candidato",
    "almacen_id_confirmado", "corte_sin_ventas_confirmado", "naturaleza", "verificacion_independiente",
    "estado_uso", "archivo_origen", "hoja_origen", "fila_origen", "sha256_origen", "observaciones"]
XLSX = "Conteo_sintetico.xlsx"
SHEET = "Conteo"
HEADERS = ["Código original", "Producto / presentación del reporte", "Unidad en reporte", "¿Qué representa 1 UND?",
           "Aptas y libres para vender", "Reservadas (aptas)", "Dañadas / vencidas / no vendibles", "Observaciones"]
# codigo, nombre, libre, reservada, no_vendible, total, presentacion
PRODUCTS = [
    ("0010001", "PRODUCTO UNO 100 ML", "5", "0", "0", "5", "Un frasco de 100 ML"),
    ("0010002", "PRODUCTO DOS CJA X 12", "7", "0", "0", "7", "Una caja de 12 unidades"),
    ("2010003", "PRODUCTO TRES PACK", "0", "0", "0", "0", "Un pack amarrado de 2 productos"),
    ("2010004", "PRODUCTO CUATRO", "11", "", "", "", "Un frasco de 1 litro"),
]
META = {"warehouse_name": "Almacen Principal", "responsible": "Responsable Sintetico",
        "scope": "Alcance sintetico", "movement_statement": "No hubo recepciones durante el conteo",
        "count_date": "2026-10-18 00:00:00", "count_time": "17:00:00"}


def _num(v: str):
    return None if v == "" else int(v)


def write_workbook(path: Path, *, salt: str = "", excel_edit=None) -> None:
    """Libro con la disposicion de la plantilla recibida: metadatos en C3/G3/C4/G4/C5/G5, encabezado en la fila 8, datos desde la 9."""
    wb = Workbook()
    ws = wb.active
    ws.title = SHEET
    ws["A1"] = "CONTEO DE EXISTENCIAS | PRODUCTOS SINTETICOS"
    ws["A3"], ws["C3"], ws["E3"], ws["G3"] = "Fecha del conteo", dt.datetime(2026, 10, 18), "Hora de corte", dt.time(17, 0)
    ws["A4"], ws["C4"], ws["E4"], ws["G4"] = "Tienda / almacén contado", META["warehouse_name"], "Responsable", META["responsible"]
    ws["A5"], ws["C5"], ws["E5"], ws["G5"] = "Alcance", META["scope"], "Situación de movimientos", META["movement_statement"]
    for c, h in enumerate(HEADERS, start=1):
        ws.cell(row=8, column=c, value=h)
    for i, (cod, nom, libre, res, nov, _tot, desc) in enumerate(PRODUCTS, start=9):
        for c, v in enumerate([cod, nom, "UND", desc, _num(libre), _num(res), _num(nov), "-"], start=1):
            ws.cell(row=i, column=c, value=v)
    other = wb.create_sheet("Como_completar")
    other["A1"] = "Instrucciones" + (f" {salt}" if salt else "")      # `salt` cambia los bytes del libro sin tocar el conteo
    if excel_edit:
        excel_edit(ws)
    wb.save(path)


def build_source(root: Path, *, salt: str = "", excel_edit=None, edit=None, group_edit=None, review_edit=None,
                 name: str = "src") -> tuple[Path, Path]:
    """Crea carpeta de conteo y catalogo. El CSV se deriva de PRODUCTS (como el derivado legitimo del Excel);
    `edit(rows)` lo altera DESPUES (derivado distinto del documento), `excel_edit(ws)` altera el libro ANTES de calcular su SHA."""
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    write_workbook(d / XLSX, salt=salt, excel_edit=excel_edit)
    sha = hashlib.sha256((d / XLSX).read_bytes()).hexdigest()
    rows = []
    for i, (cod, nom, libre, res, nov, tot, desc) in enumerate(PRODUCTS, start=9):
        rows.append({
            "producto_id": cod, "producto": nom, "unidad_reporte": "UND", "unidad_descripcion_reportada": desc,
            "cantidad_libre_reportada": libre, "cantidad_reservada_reportada": res,
            "cantidad_no_vendible_reportada": nov, "cantidad_fisica_total_reportada": tot,
            "fecha_hora_reportada": "2026-10-18T17:00:00-05:00", "zona_horaria": "America/Lima",
            "almacen_nombre_reportado": "Almacen Principal", "almacen_id_candidato": "1",
            "almacen_id_confirmado": "True", "corte_sin_ventas_confirmado": "True",
            "naturaleza": "CONTEO_FISICO_REPORTADO_POR_USUARIO", "verificacion_independiente": "False",
            "estado_uso": "APTO_COMO_SNAPSHOT_FECHADO", "archivo_origen": XLSX, "hoja_origen": SHEET,
            "fila_origen": str(i), "sha256_origen": sha, "observaciones": "-"})
    rows[0]["almacen_id_confirmado"] = "1"
    if edit:
        edit(rows)
    with (d / "conteo_reportado.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COUNT_FIELDS)
        w.writeheader()
        w.writerows(rows)
    review = {"source_sha256": sha, "source_unchanged": True, "metadata": dict(META),
              "pending_questions": [{"code": "BRECHA_OCTUBRE", "detail": "Ventas hasta el 30/09; dias faltantes no son cero."},
                                    {"code": "PEDIDOS_PENDIENTES", "detail": "Pedidos por recibir desconocidos."}],
              "user_confirmation": {"warehouse_id": "1", "no_sales_during_count": True, "evidence": "confirmacion sintetica"}}
    if review_edit:
        review_edit(review)
    (d / "review.json").write_text(json.dumps(review), encoding="utf-8")
    grows = [{"producto_id": c, "producto": n, "categoria": f"CAT{c[-1]}", "almacen": "1", "unidad": "UND",
              "seleccionado": "True"} for c, n, *_ in PRODUCTS]
    if group_edit:
        group_edit(grows)
    g = root / f"{name}_productos.csv"
    with g.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=GROUP_FIELDS)
        w.writeheader()
        w.writerows(grows)
    return d, g
