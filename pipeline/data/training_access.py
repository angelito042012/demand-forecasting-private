"""Barrera unica de acceso a datos de entrenamiento por corte temporal.

Todo codigo de features/modelos debe leer ventas SOLO a traves de estas
funciones; nunca consultar `sales` directamente. Garantias:
  - el corte debe ser <= LAST_TRAIN_DATE (2026-07-31): agosto y posteriores no
    son accesibles desde la ruta de entrenamiento ni de validacion de folds;
  - solo fecha <= corte del fold; el catalogo de categorias se construye con el
    mismo corte; las notas de credito no forman parte del objetivo;
  - los dias de EXCLUDED_DATES se omiten del entrenamiento y de las metricas
    mediante mascara, sin comprimir el calendario ni crear ventas cero;
  - R04: solo se leen lineas con alguna fuente APROBADA (carga completa, sin
    conflictos abiertos; ver sources.py). Cargas fallidas/parciales, fuentes no
    reconocidas, conflictos abiertos relevantes o meses requeridos sin fuente
    detienen la construccion con SourceApprovalError; nada entra en silencio.
    El catalogo usa la misma seleccion de fuentes que las ventas;
  - `fingerprint` resume el contenido de entrenamiento: cambiar registros
    posteriores al corte no lo altera (probado en tests/data/test_training_access.py).
Agosto solo se obtiene con load_final_test_sales(..., frozen_selection_confirmed=True),
una ruta de evaluacion explicita para cuando la seleccion este congelada.
Una consulta directa a MongoDB puede saltarse esta barrera: es una convencion
de ingenieria verificada con pruebas y revision, no un control de seguridad.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, timedelta

from .calendar import (
    EXCLUDED_DATES,
    FINAL_TEST_END,
    FINAL_TEST_START,
    LAST_TRAIN_DATE,
    to_date,
)
from .catalog import build_category_catalog
from .sources import SourceReport, approved_filter, require_approved_sources

_FIELDS = {"_id": 0, "linea_id": 1, "fecha": 1, "sku": 1, "cantidad_base": 1, "importe": 1,
           "categoria_original": 1, "almacen": 1, "unidad_base": 1}


class TrainingCutoffError(ValueError):
    """Corte o ventana que tocaria datos reservados (agosto) o posteriores al fold."""


@dataclass(frozen=True)
class TrainingData:
    cutoff: date
    sales: tuple          # dicts ordenados por (fecha, linea_id); solo ventas observadas
    calendar: tuple       # todos los dias naturales [primer_dia, corte]
    excluded_days: frozenset  # dias del calendario enmascarados (no implica cierre)
    catalog: dict         # sku -> categoria conocida al corte
    fingerprint: str
    omitted_excluded_rows: int = 0
    sources: SourceReport | None = None  # manifiesto de fuentes aprobadas usado

    @property
    def training_days(self) -> tuple:
        """Dias naturales usables como objetivo supervisado (calendario sin comprimir)."""
        return tuple(d for d in self.calendar if d not in self.excluded_days)


@dataclass(frozen=True)
class FoldData:
    train: TrainingData
    validation_sales: tuple
    validation_calendar: tuple
    validation_excluded_days: frozenset

    @property
    def metric_days(self) -> tuple:
        return tuple(d for d in self.validation_calendar if d not in self.validation_excluded_days)


def _check_cutoff(value) -> date:
    cutoff = to_date(value)
    if cutoff > LAST_TRAIN_DATE or cutoff >= FINAL_TEST_START:
        raise TrainingCutoffError(
            f"corte {cutoff} posterior a {LAST_TRAIN_DATE}: agosto 2026 esta reservado como test final")
    return cutoff


def _days(first: date, last: date) -> tuple:
    return tuple(first + timedelta(days=i) for i in range((last - first).days + 1))


def _fetch(db, first: date | None, last: date, report: SourceReport) -> list:
    query: dict = {"fecha": {"$lte": last.isoformat()}, **approved_filter(report)}
    if first is not None:
        query["fecha"]["$gte"] = first.isoformat()
    rows = list(db.sales.find(query, _FIELDS))
    rows.sort(key=lambda r: (r["fecha"], r["linea_id"]))
    return rows


def _fingerprint(rows, cutoff: date, catalog: dict, report: SourceReport) -> str:
    """Firma de contenido y decisiones: filas (fecha, sku, cantidad, importe, categoria,
    almacen), catalogo al corte, mascara de exclusion, corte y manifiesto de fuentes."""
    h = hashlib.sha256()
    h.update(f"v2|cutoff={cutoff}|mask={sorted(d.isoformat() for d in EXCLUDED_DATES)}\n".encode())
    for m in report.manifest:
        h.update(f"src|{m['mes']}|{m['archivo']}|{m['sha256']}\n".encode())
    for sku in sorted(catalog):
        h.update(f"cat|{sku}|{catalog[sku]}\n".encode())
    for r in rows:
        h.update(f"{r['linea_id']}|{r['fecha']}|{r['sku']}|{r['cantidad_base']}|{r['importe']}|"
                 f"{r.get('categoria_original', '')}|{r.get('almacen', '')}\n".encode())
    return h.hexdigest()


def load_training_data(db, cutoff, *, start=None, required_months=None) -> TrainingData:
    """Ventas de entrenamiento con fecha <= corte (corte <= 2026-07-31), solo de fuentes
    aprobadas. `required_months` (por defecto 2026-03..mes del corte) debe tener fuente aprobada."""
    last = _check_cutoff(cutoff)
    first = to_date(start) if start is not None else None
    report = require_approved_sources(db, last, required_months=required_months)
    rows = _fetch(db, first, last, report)
    if any(r["fecha"] > last.isoformat() for r in rows):  # defensa en profundidad
        raise TrainingCutoffError("la consulta devolvio fechas posteriores al corte")
    kept = [r for r in rows if to_date(r["fecha"]) not in EXCLUDED_DATES]
    cal_first = first or (to_date(kept[0]["fecha"]) if kept else last)
    calendar = _days(cal_first, last) if cal_first <= last else ()
    catalog = build_category_catalog(db, last, source_filter=approved_filter(report))
    return TrainingData(
        cutoff=last, sales=tuple(kept), calendar=calendar,
        excluded_days=frozenset(d for d in calendar if d in EXCLUDED_DATES),
        catalog=catalog, fingerprint=_fingerprint(kept, last, catalog, report),
        omitted_excluded_rows=len(rows) - len(kept), sources=report)


def load_fold(db, train_cutoff, validation_end, *, start=None, required_months=None) -> FoldData:
    """Fold temporal: entrenamiento <= corte; validacion en (corte, validation_end].
    validation_end tambien debe ser <= 2026-07-31 (agosto no se usa para elegir)."""
    train = load_training_data(db, train_cutoff, start=start, required_months=required_months)
    end = _check_cutoff(validation_end)
    if end <= train.cutoff:
        raise TrainingCutoffError("validation_end debe ser posterior al corte de entrenamiento")
    report = require_approved_sources(db, end, required_months=required_months)
    first = train.cutoff + timedelta(days=1)
    rows = [r for r in _fetch(db, first, end, report) if to_date(r["fecha"]) not in EXCLUDED_DATES]
    calendar = _days(first, end)
    return FoldData(train=train, validation_sales=tuple(rows), validation_calendar=calendar,
                    validation_excluded_days=frozenset(d for d in calendar if d in EXCLUDED_DATES))


def load_final_test_sales(db, *, frozen_selection_confirmed: bool, required_months=None) -> tuple:
    """Ruta explicita de evaluacion final (agosto). Solo con la seleccion congelada."""
    if frozen_selection_confirmed is not True:
        raise TrainingCutoffError("agosto es test final: requiere frozen_selection_confirmed=True")
    report = require_approved_sources(db, FINAL_TEST_END, required_months=required_months)
    rows = _fetch(db, FINAL_TEST_START, FINAL_TEST_END, report)
    return tuple(r for r in rows if to_date(r["fecha"]) not in EXCLUDED_DATES)
