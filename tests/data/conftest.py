"""Fixtures: Excel sinteticos pequenos (openpyxl) y base MongoDB aislada."""
import os
import uuid
from datetime import datetime

import openpyxl
import pytest
from pymongo import MongoClient
from pymongo.errors import PyMongoError

HEADERS = ["ID_PEDIDO", "TIPO_DOC", "SERIE_NUMERO", "FECHA", "ID_CLIENTE", "CLIENTE", "TIPOPAGO",
           "ID_TIENDA", "TIENDA", "MONEDA", "VENDEDOR", "ID_ARTICULO", "ARTICULO", "ID_ALMACEN",
           "CANTIDAD", "PRECIO", "DSCTO", "TOTAL_LINEA", "ID_UM", "EQUIVALENCIA", "UM_BASE",
           "CANTIDAD_UM_BASE", "GRUPO", "SUBGRUPO", "MARCA", "VEN_ESTADO", "RUC_Proveedor",
           "Proveedor", "DEPARTAMENTO", "PROVINCIA", "DISTRITO"]


def make_row(**kw):
    """Fila sintetica valida; kw sobreescribe columnas."""
    base = {"ID_PEDIDO": 1, "TIPO_DOC": 3, "SERIE_NUMERO": "B001-1", "FECHA": datetime(2026, 3, 2),
            "ID_CLIENTE": "X", "CLIENTE": "SINTETICO", "TIPOPAGO": "EFECTIVO", "ID_TIENDA": 1,
            "TIENDA": "T", "MONEDA": "SOLES (S/)", "VENDEDOR": "V", "ID_ARTICULO": 100,
            "ARTICULO": "A", "ID_ALMACEN": 1, "CANTIDAD": 2, "PRECIO": 5.5, "DSCTO": 0,
            "TOTAL_LINEA": 11.0, "ID_UM": "UND", "EQUIVALENCIA": 1, "UM_BASE": "UND",
            "CANTIDAD_UM_BASE": 2, "GRUPO": " CAT A ", "SUBGRUPO": "S", "MARCA": "M",
            "VEN_ESTADO": "ACTIVO"}
    base.update(kw)
    return [base.get(h) for h in HEADERS]


def write_xlsx(path, rows, title_row=True):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Hoja1"
    if title_row:
        ws.append(["Reporte sintetico"])
    ws.append(HEADERS)
    for r in rows:
        ws.append(r)
    wb.save(path)
    return path


@pytest.fixture
def xlsx(tmp_path):
    def _make(name, rows):
        return write_xlsx(tmp_path / name, rows)
    return _make


@pytest.fixture
def db():
    uri = os.environ.get("MONGODB_URI", "mongodb://127.0.0.1:27017")
    client = MongoClient(uri, serverSelectionTimeoutMS=1500)
    try:
        client.admin.command("ping")
    except PyMongoError:
        client.close()
        pytest.skip("MongoDB no disponible")
    name = f"df_test_{uuid.uuid4().hex[:12]}"
    yield client[name]
    client.drop_database(name)
    client.close()
