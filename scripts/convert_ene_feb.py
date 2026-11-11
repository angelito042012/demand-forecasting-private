"""Convierte los Excel de enero y febrero (formato 'Ventas detalladas') al formato
estándar del importador (31 columnas, encabezados en fila 2).

Uso:
  python scripts/convert_ene_feb.py <entrada.xlsx> <salida.xlsx>
"""
from __future__ import annotations
import sys
from pathlib import Path
from openpyxl import Workbook, load_workbook

STANDARD_HEADERS = [
    "ID_PEDIDO", "TIPO_DOC", "SERIE_NUMERO", "FECHA", "ID_CLIENTE", "CLIENTE",
    "TIPOPAGO", "ID_TIENDA", "TIENDA", "MONEDA", "VENDEDOR", "ID_ARTICULO",
    "ARTICULO", "ID_ALMACEN", "CANTIDAD", "PRECIO", "DSCTO", "TOTAL_LINEA",
    "ID_UM", "EQUIVALENCIA", "UM_BASE", "CANTIDAD_UM_BASE", "GRUPO", "SUBGRUPO",
    "MARCA", "VEN_ESTADO", "RUC_Proveedor", "Proveedor", "DEPARTAMENTO",
    "PROVINCIA", "DISTRITO",
]

SRC_HEADER_MAP = {
    "Fecha": "FECHA",
    "Tipo documento": "TIPO_DOC",
    "Serie y número": "SERIE_NUMERO",
    "Código artículo": "ID_ARTICULO",
    "Artículo": "ARTICULO",
    "Cantidad": "CANTIDAD",
    "Unidad": "ID_UM",
    "Precio": "PRECIO",
    "Descuento línea": "DSCTO",
    "Total línea": "TOTAL_LINEA",
}

DEFAULTS = {
    "ID_PEDIDO": 0,
    "ID_CLIENTE": "C000000000",
    "CLIENTE": "CLIENTES VARIOS",
    "TIPOPAGO": "EFECTIVO",
    "ID_TIENDA": 1,
    "TIENDA": "COSMETICA",
    "MONEDA": "SOLES (S/)",
    "VENDEDOR": None,
    "ID_ALMACEN": 1,
    "EQUIVALENCIA": 1,
    "UM_BASE": "UND",
    "CANTIDAD_UM_BASE": None,  # se copia de CANTIDAD
    "GRUPO": "SIN GRUPO",
    "SUBGRUPO": None,
    "MARCA": None,
    "VEN_ESTADO": "ACTIVO",
    "RUC_Proveedor": None,
    "Proveedor": None,
    "DEPARTAMENTO": None,
    "PROVINCIA": None,
    "DISTRITO": None,
}


def find_header_row(ws):
    for i, row in enumerate(ws.iter_rows(max_row=15, values_only=True), 1):
        vals = [str(v).strip() if v else "" for v in row]
        if "Fecha" in vals and "Código artículo" in vals:
            return i, vals
    return None, None


def convert(src_path: str, dst_path: str):
    wb_src = load_workbook(src_path, read_only=True, data_only=True)
    ws_src = wb_src.active

    hdr_row, src_headers = find_header_row(ws_src)
    if hdr_row is None:
        print(f"ERROR: No se encontraron encabezados en {src_path}", file=sys.stderr)
        sys.exit(2)

    col_map = {}
    for idx, h in enumerate(src_headers):
        std = SRC_HEADER_MAP.get(h)
        if std:
            col_map[std] = idx

    wb_dst = Workbook()
    ws_dst = wb_dst.active
    ws_dst.title = "Hoja1"

    ws_dst.append([None] * len(STANDARD_HEADERS))  # fila 1 vacía
    ws_dst.append(STANDARD_HEADERS)  # fila 2: encabezados

    pedido_counter = 0
    written = 0
    for row in ws_src.iter_rows(min_row=hdr_row + 1, values_only=True):
        fecha = row[col_map["FECHA"]] if "FECHA" in col_map else None
        if fecha is None:
            continue

        pedido_counter += 1
        out = []
        for h in STANDARD_HEADERS:
            if h in col_map:
                out.append(row[col_map[h]])
            elif h == "ID_PEDIDO":
                out.append(pedido_counter)
            elif h == "CANTIDAD_UM_BASE":
                out.append(row[col_map["CANTIDAD"]] if "CANTIDAD" in col_map else None)
            else:
                out.append(DEFAULTS.get(h))
        out[STANDARD_HEADERS.index("TIPO_DOC")] = _normalize_tipo_doc(
            out[STANDARD_HEADERS.index("TIPO_DOC")])
        ws_dst.append(out)
        written += 1

    wb_src.close()
    wb_dst.save(dst_path)
    wb_dst.close()
    print(f"Convertido: {written} filas -> {dst_path}")


def _normalize_tipo_doc(val):
    if val is None:
        return 3
    s = str(val).strip()
    if s in ("03", "3"):
        return 3
    if s in ("07", "7"):
        return 7
    try:
        return int(s)
    except ValueError:
        return 3


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Uso: python {sys.argv[0]} <entrada.xlsx> <salida.xlsx>")
        sys.exit(1)
    convert(sys.argv[1], sys.argv[2])
