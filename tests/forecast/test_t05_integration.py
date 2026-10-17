"""T05: folds sin fuga, cohortes, ceros de elegibles, mascara y reproducibilidad (Mongo, datos sinteticos)."""
from datetime import datetime

import numpy as np
import pytest

from pipeline.data.importer import import_workbook
from pipeline.forecast.baselines import METHODS
from pipeline.forecast.t05 import run_all, run_fold
from tests.data.conftest import make_row

pytestmark = pytest.mark.mongo
RM = ("2026-04",)
MASKED = (3, 12)


def line(n, day, sku, qty, cat="CAT A"):
    return make_row(ID_PEDIDO=n, SERIE_NUMERO=f"B{n}", ID_ARTICULO=sku, GRUPO=cat, FECHA=datetime(2026, 4, day),
                    CANTIDAD=qty, CANTIDAD_UM_BASE=qty, TOTAL_LINEA=qty * 5.5)


def rows(extra=()):
    out, n = [], 0
    for d in range(1, 31):
        if d in MASKED:
            continue
        n += 1
        out.append(line(n, d, 100, 2))                      # vende todos los dias
        if d % 2 == 0:
            n += 1
            out.append(line(n, d, 101, 1, "CAT B"))         # un dia si y otro no
    n += 1
    out.append(line(n, 22, 102, 5, "CAT C"))                # SKU nuevo durante la validacion
    return out + list(extra)


CFG = {"inicio_entrenamiento": "2026-04-01", "horizonte_dias": 7, "ventana_promedio_dias": 28, "r2_minimo_n": 30,
       "cohorte_primaria": {"historia_minima_dias": 9, "observaciones_utilizables_minimas_en_28": 7},
       "referencia_t06": {"candidatos": ["ultimo_dia", "naive_semanal", "promedio_28"],
                          "desempate_orden": ["promedio_28", "ultimo_dia", "naive_semanal"], "umbral_empate_relativo": 0.01},
       "folds": [{"id": "A", "corte": "2026-04-20", "validacion": ["2026-04-21", "2026-04-27"]},
                 {"id": "B", "corte": "2026-04-09", "validacion": ["2026-04-10", "2026-04-16"]}]}


@pytest.fixture
def loaded(xlsx, db):
    import_workbook(xlsx("abril.xlsx", rows()), db)
    return db


def _preds(res, fold):
    p = res["predicciones"]
    return p[p["fold"] == fold].sort_values(["nivel", "entidad", "fecha"]).reset_index(drop=True)


def test_primary_cohort_includes_zero_rows_of_eligible_products(loaded):
    res = run_all(loaded, CFG, required_months=RM)
    p = _preds(res, "A")
    sku101 = p[(p.nivel == "sku") & (p.entidad == "101|1") & (p.cohorte == "primaria")]
    assert len(sku101) == 7 and (sku101["real"] == 0).sum() == 4 and sku101["evaluable"].all()   # 22,24,26: no; incluye ceros
    assert sorted(p[p.nivel == "sku"].entidad.unique()) == ["100|1", "101|1"]                  # 102 es nuevo: sin prediccion
    nuevos = res["folds"]["A"]["niveles"]["sku"]["nuevos_en_validacion"]
    assert nuevos["entidades"] == 1 and nuevos["unidades_evaluables"] == 5
    cat = res["folds"]["A"]["niveles"]["categoria"]["nuevos_en_validacion"]
    assert cat["categorias"] == ["DESCONOCIDA"] and cat["unidades_evaluables"] == 5            # SKU nuevo => categoria desconocida
    assert "CAT C" not in set(p[p.nivel == "categoria"].entidad)


def test_masked_validation_day_is_not_evaluable_but_calendar_keeps_seven_dates(loaded):
    res = run_all(loaded, CFG, required_months=RM)
    f = res["folds"]["B"]
    assert len(f["dias_validacion"]) == 7 and f["dias_evaluables"] == 6 and f["dias_no_evaluables"] == ["2026-04-12"]
    p = _preds(res, "B")
    d = p[(p.nivel == "sku") & (p.fecha == "2026-04-12")]
    assert len(d) > 0 and not d.evaluable.any()
    m = next(r for r in res["metricas"] if r["fold"] == "B" and r["nivel"] == "sku" and r["cohorte"] == "primaria"
         and r["universo"] == "comun" and r["vista"] == "diaria" and r["metodo"] == "cero")
    assert m["n"] == 1 * 6          # solo el SKU 100 es elegible en B (101 tiene 8 dias de historia)


def test_training_inputs_come_from_cutoff_not_future(loaded):
    before = run_fold(loaded, CFG["folds"][1], CFG, required_months=RM)
    # cambiar ventas posteriores al corte (y la categoria de un SKU) no altera catalogo ni pronosticos emitidos
    loaded.sales.update_many({"fecha": {"$gt": "2026-04-09"}}, {"$set": {"cantidad_base": 50, "categoria_original": "ZZ"}})
    after = run_fold(loaded, CFG["folds"][1], CFG, required_months=RM)
    cols = [f"pred_{m}" for m in METHODS]
    b, a = pd_frame(before), pd_frame(after)
    for c in cols + ["historia_dias", "antiguedad_ultimo_dia", "naive_fallback"]:
        assert np.array_equal(b[c].to_numpy(float), a[c].to_numpy(float), equal_nan=True), c
    assert before["fingerprint"] == after["fingerprint"]


def pd_frame(fold_result):
    import pandas as pd

    from pipeline.forecast.t05 import PRED_COLUMNS
    return pd.DataFrame(fold_result["predicciones"], columns=PRED_COLUMNS).sort_values(["nivel", "entidad", "fecha"])


def test_fallback_counted_when_weekly_source_day_is_masked(loaded):
    res = run_all(loaded, CFG, required_months=RM)
    p = _preds(res, "B")                       # origen 04-09: t+h-7 cae en 04-03..04-09 => 04-03 (h=1) enmascarado
    sku100 = p[(p.nivel == "sku") & (p.entidad == "100|1")]
    assert sku100["naive_fallback"].sum() == 1
    cov = next(c for c in res["cobertura"] if c["fold"] == "B" and c["nivel"] == "sku" and c["cohorte"] == "primaria")
    assert cov["naive_fallback_filas"] >= 1


def test_repeated_evaluation_is_identical(loaded):
    r1, r2 = run_all(loaded, CFG, required_months=RM), run_all(loaded, CFG, required_months=RM)
    assert r1["predicciones"].equals(r2["predicciones"]) and r1["metricas"] == r2["metricas"]
    assert r1["referencia_t06"]["seleccion"] in CFG["referencia_t06"]["candidatos"]


def test_august_is_never_requested(loaded, monkeypatch):
    import pipeline.data.training_access as ta
    monkeypatch.setattr(ta, "load_final_test_sales", lambda *a, **k: (_ for _ in ()).throw(AssertionError("agosto")))
    run_all(loaded, CFG, required_months=RM)
