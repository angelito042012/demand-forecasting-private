"""R18 (REVISION_CODEX_18): el CSV derivado debe corresponder al Excel revisado ANTES de importar.

Fuentes sinteticas con un libro .xlsx REAL; el CSV se altera sin tocar el Excel (o al reves) manteniendo coherentes aritmetica,
SHA del Excel y review.json. Sin base de datos: `prepare()` valida antes de cualquier escritura.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from pipeline.inventory import reported_count as rc
from pipeline.publish.source import PROJECT_ROOT
from tests.inventory.conftest import COUNT_FIELDS, SHEET, XLSX, build_source

REAL_DIR = PROJECT_ROOT / "artifacts/private/conteo_recibido_20261018_v2"
REAL_GROUP = PROJECT_ROOT / "artifacts/private/datos_preparados_v1/02_grupo/productos.csv"


def _set(rows, idx, **kw):
    rows[idx].update(kw)


def _all(**kw):
    return lambda rows: [r.update(kw) for r in rows]


def _mismatch(tmp_path, **kw):
    d, g = build_source(tmp_path, **kw)
    with pytest.raises(rc.ImportRejected) as e:
        rc.prepare(d, g)
    assert e.value.code == "DERIVADO_NO_COINCIDE", e.value
    assert str(tmp_path) not in str(e.value)
    return e.value


def test_legitimate_derivative_is_accepted_and_idempotent(tmp_path):
    d, g = build_source(tmp_path)
    a, b = rc.prepare(d, g), rc.prepare(d, g)
    assert a.header["snapshot_id"] == b.header["snapshot_id"] and a.header["source"] == b.header["source"]
    assert a.header["source"]["verified_against_excel"] is True and a.header["source"]["excel_rows_verified"] == 4
    assert [i["libre"] for i in a.items] == [5, 7, 0, 11] and a.items[3]["reservada"] is None   # vacio sigue siendo null


def test_coherent_but_different_quantity_and_total_is_rejected(tmp_path):
    """Caso de la revision: +1 en disponible y total; aritmetica, SHA del Excel y review.json siguen coherentes."""
    _mismatch(tmp_path, edit=lambda rows: _set(rows, 0, cantidad_libre_reportada="6", cantidad_fisica_total_reportada="6"))


def test_uniform_date_different_from_document_is_rejected(tmp_path):
    _mismatch(tmp_path, edit=_all(fecha_hora_reportada="2026-10-19T17:00:00-05:00"))
    _mismatch(tmp_path / "h", edit=_all(fecha_hora_reportada="2026-10-18T18:00:00-05:00"))


def test_changed_presentation_is_rejected(tmp_path):
    _mismatch(tmp_path, edit=lambda rows: _set(rows, 1, unidad_descripcion_reportada="Un frasco de 12 ML"))


def test_changed_name_unit_code_and_observations_are_rejected(tmp_path):
    def other_name(rows):
        rows[0]["producto"] = "OTRO NOMBRE"
    def group_name(grows):
        grows[0]["producto"] = "OTRO NOMBRE"
    # el catalogo coincide con el CSV alterado, pero el Excel no
    _mismatch(tmp_path, edit=other_name, group_edit=group_name)
    _mismatch(tmp_path / "o", edit=lambda rows: _set(rows, 2, observaciones="se ajusto"))
    # codigos intercambiados entre dos filas (conjunto exacto, pero cada fila apunta a otra celda)
    def swap(rows):
        a, b = rows[0]["fila_origen"], rows[1]["fila_origen"]
        rows[0]["fila_origen"], rows[1]["fila_origen"] = b, a
    _mismatch(tmp_path / "s", edit=swap)


def test_blank_versus_zero_is_not_interchangeable(tmp_path):
    # Excel: reservada vacia (producto 4) -> el CSV no puede declarar 0; y un 0 del Excel no puede quedar vacio.
    _mismatch(tmp_path, edit=lambda rows: _set(rows, 3, cantidad_reservada_reportada="0", cantidad_no_vendible_reportada="0",
                                                cantidad_fisica_total_reportada="11"))
    _mismatch(tmp_path / "b", edit=lambda rows: _set(rows, 0, cantidad_reservada_reportada="", cantidad_fisica_total_reportada=""))


def test_total_must_derive_from_document_cells(tmp_path):
    # total informado aunque el documento deje reservada/no vendible vacias: dato que el documento no informa
    _mismatch(tmp_path, edit=lambda rows: _set(rows, 3, cantidad_fisica_total_reportada="11"))


def test_changed_warehouse_name_is_rejected(tmp_path):
    _mismatch(tmp_path, edit=_all(almacen_nombre_reportado="Otro Almacen"))


def test_extra_or_missing_document_rows_are_rejected(tmp_path):
    def extra_row(ws):
        for c, v in enumerate(["9999999", "PRODUCTO EXTRA", "UND", "Un frasco", 3, 0, 0, "-"], start=1):
            ws.cell(row=13, column=c, value=v)
    _mismatch(tmp_path, excel_edit=extra_row)
    _mismatch(tmp_path / "f", edit=lambda rows: _set(rows, 3, fila_origen="40"))


def test_review_metadata_must_match_the_document(tmp_path):
    _mismatch(tmp_path, review_edit=lambda r: r["metadata"].update(responsible="Otra Persona"))
    _mismatch(tmp_path / "f", review_edit=lambda r: r["metadata"].update(count_date="2026-10-19 00:00:00"))
    _mismatch(tmp_path / "x", review_edit=lambda r: r.pop("metadata"))


def test_human_confirmations_are_checked_separately(tmp_path):
    d, g = build_source(tmp_path, review_edit=lambda r: r["user_confirmation"].update(no_sales_during_count=False))
    with pytest.raises(rc.ImportRejected) as e:
        rc.prepare(d, g)
    assert e.value.code == "CORTE_NO_CONFIRMADO"


def test_excel_changed_but_derivative_not_rederived_is_rejected(tmp_path):
    """El Excel cambia (y los SHA declarados se recalculan) pero el CSV conserva los valores antiguos."""
    _mismatch(tmp_path, excel_edit=lambda ws: ws.cell(row=9, column=5, value=9))


def test_formula_or_text_in_quantity_cell_is_rejected(tmp_path):
    _mismatch(tmp_path, excel_edit=lambda ws: ws.cell(row=9, column=5, value="=2+3"))
    _mismatch(tmp_path / "t", excel_edit=lambda ws: ws.cell(row=9, column=5, value="5"))


def test_legitimate_modified_source_needs_its_own_version(tmp_path):
    """Una fuente modificada legitimamente (Excel y CSV coherentes) se acepta como OTRA fuente (otro SHA => otro snapshot)."""
    d1, g1 = build_source(tmp_path / "a")
    d2, g2 = build_source(tmp_path / "b", excel_edit=lambda ws: ws.cell(row=9, column=5, value=9),
                          edit=lambda rows: _set(rows, 0, cantidad_libre_reportada="9", cantidad_fisica_total_reportada="9"))
    a, b = rc.prepare(d1, g1), rc.prepare(d2, g2)
    assert a.header["snapshot_id"] != b.header["snapshot_id"] and b.items[0]["libre"] == 9


def test_unreadable_workbook_with_matching_hashes_is_rejected(tmp_path):
    d, g = build_source(tmp_path)
    (d / XLSX).write_bytes(b"no es un libro xlsx")
    sha = hashlib.sha256(b"no es un libro xlsx").hexdigest()
    rows = list(csv.DictReader((d / "conteo_reportado.csv").open(encoding="utf-8-sig", newline="")))
    for r in rows:
        r["sha256_origen"] = sha
    with (d / "conteo_reportado.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COUNT_FIELDS)
        w.writeheader()
        w.writerows(rows)
    rev = json.loads((d / "review.json").read_text(encoding="utf-8"))
    rev["source_sha256"] = sha
    (d / "review.json").write_text(json.dumps(rev), encoding="utf-8")
    with pytest.raises(rc.ImportRejected) as e:
        rc.prepare(d, g)
    assert e.value.code == "FUENTE_ALTERADA"


def test_wrong_sheet_name_is_rejected(tmp_path):
    _mismatch(tmp_path, edit=_all(hoja_origen="Otra_hoja"))
    assert SHEET == "Conteo"


@pytest.mark.skipif(not (REAL_DIR / "conteo_reportado.csv").is_file() or not REAL_GROUP.is_file(), reason="conteo real no disponible")
def test_real_package_verified_against_excel_and_tampered_copy_rejected(tmp_path):
    ok = rc.prepare(REAL_DIR, REAL_GROUP)
    assert ok.header["source"]["verified_against_excel"] is True and ok.header["source"]["excel_rows_verified"] == 50
    assert ok.header["counts"] == {"items": 50, "with_stock": 48, "no_stock": 2}
    # copia manipulada: +1 en disponible y total de la primera fila con existencia; Excel, SHA y review.json intactos
    copy = tmp_path / "real"
    copy.mkdir()
    for n in ("Solicitud_conteo_50_productos.xlsx", "review.json"):
        (copy / n).write_bytes((REAL_DIR / n).read_bytes())
    rows = list(csv.DictReader((REAL_DIR / "conteo_reportado.csv").open(encoding="utf-8-sig", newline="")))
    tgt = next(r for r in rows if int(r["cantidad_libre_reportada"]) > 0)
    tgt["cantidad_libre_reportada"] = str(int(tgt["cantidad_libre_reportada"]) + 1)
    tgt["cantidad_fisica_total_reportada"] = str(int(tgt["cantidad_fisica_total_reportada"]) + 1)
    with (copy / "conteo_reportado.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    with pytest.raises(rc.ImportRejected) as e:
        rc.prepare(copy, REAL_GROUP)
    assert e.value.code == "DERIVADO_NO_COINCIDE"
    # y la fecha uniforme al 19/10
    for r in rows:
        r["fecha_hora_reportada"] = "2026-10-19T17:00:00-05:00"
    tgt["cantidad_libre_reportada"] = str(int(tgt["cantidad_libre_reportada"]) - 1)
    tgt["cantidad_fisica_total_reportada"] = str(int(tgt["cantidad_fisica_total_reportada"]) - 1)
    with (copy / "conteo_reportado.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    with pytest.raises(rc.ImportRejected) as e2:
        rc.prepare(copy, REAL_GROUP)
    assert e2.value.code == "DERIVADO_NO_COINCIDE"
    assert Path(REAL_DIR / "Solicitud_conteo_50_productos.xlsx").is_file()   # la fuente original no se toco
