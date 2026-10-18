"""Fuentes sinteticas para el importador del conteo reportado (T18); no usan datos comerciales."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

GROUP_FIELDS = ["producto_id", "producto", "categoria", "almacen", "unidad", "seleccionado"]
COUNT_FIELDS = [
    "producto_id", "producto", "unidad_reporte", "unidad_descripcion_reportada", "cantidad_libre_reportada",
    "cantidad_reservada_reportada", "cantidad_no_vendible_reportada", "cantidad_fisica_total_reportada",
    "fecha_hora_reportada", "zona_horaria", "almacen_nombre_reportado", "almacen_id_candidato",
    "almacen_id_confirmado", "corte_sin_ventas_confirmado", "naturaleza", "verificacion_independiente",
    "estado_uso", "archivo_origen", "hoja_origen", "fila_origen", "sha256_origen", "observaciones"]
XLSX = "Conteo_sintetico.xlsx"
# codigo, nombre, libre, reservada, no_vendible, total, presentacion
PRODUCTS = [
    ("0010001", "PRODUCTO UNO 100 ML", "5", "0", "0", "5", "Un frasco de 100 ML"),
    ("0010002", "PRODUCTO DOS CJA X 12", "7", "0", "0", "7", "Una caja de 12 unidades"),
    ("2010003", "PRODUCTO TRES PACK", "0", "0", "0", "0", "Un pack amarrado de 2 productos"),
    ("2010004", "PRODUCTO CUATRO", "11", "", "", "", "Un frasco de 1 litro"),
]


def build_source(root: Path, *, excel: bytes = b"excel sintetico v1", edit=None, group_edit=None,
                 review_edit=None, name: str = "src") -> tuple[Path, Path]:
    """Crea carpeta de conteo y catalogo. `edit(rows)` y `group_edit(rows)` modifican las filas antes de escribir."""
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    (d / XLSX).write_bytes(excel)
    sha = hashlib.sha256(excel).hexdigest()
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
            "estado_uso": "APTO_COMO_SNAPSHOT_FECHADO", "archivo_origen": XLSX, "hoja_origen": "Conteo",
            "fila_origen": str(i), "sha256_origen": sha, "observaciones": "-"})
    rows[0]["almacen_id_confirmado"] = "1"
    if edit:
        edit(rows)
    with (d / "conteo_reportado.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COUNT_FIELDS)
        w.writeheader()
        w.writerows(rows)
    review = {"source_sha256": sha, "source_unchanged": True,
              "pending_questions": [{"code": "BRECHA_OCTUBRE", "detail": "Ventas hasta el 30/09; dias faltantes no son cero."},
                                    {"code": "PEDIDOS_PENDIENTES", "detail": "Pedidos por recibir desconocidos."}],
              "user_confirmation": {"warehouse_id": "1", "evidence": "confirmacion sintetica"}}
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
