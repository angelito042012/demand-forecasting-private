"""T04: reglas de series diarias (sin Mongo; TrainingData construido a mano)."""
from datetime import date, timedelta

from bson.decimal128 import Decimal128

from pipeline.data import daily_series as ds
from pipeline.data.training_access import TrainingData


def _data(rows, first=date(2026, 4, 1), last=date(2026, 4, 14), skip_cover=()):
    cal = tuple(first + timedelta(days=i) for i in range((last - first).days + 1))
    mask0 = {date(2026, 4, 3), date(2026, 4, 12)}   # SKU de relleno 'Z': todo dia no enmascarado tiene filas
    rows = list(rows) + [(d.isoformat(), "Z", 1, "CAT Z") for d in cal if d not in mask0 and d.isoformat() not in skip_cover]
    sales = tuple({"linea_id": f"l{i}", "fecha": f, "sku": sku, "cantidad_base": q, "importe": Decimal128(str(q * 5)),
                   "categoria_original": cat, "almacen": "1", "unidad_base": "UND"}
                  for i, (f, sku, q, cat) in enumerate(rows))
    mask = frozenset({date(2026, 4, 3), date(2026, 4, 12)})
    return TrainingData(cutoff=last, sales=sales, calendar=cal, excluded_days=mask,
                        catalog={"A": "CAT X", "B": "CAT Y"}, fingerprint="f")


ROWS = [("2026-04-01", "A", 2, "CAT X"), ("2026-04-01", "A", 1, "CAT X"), ("2026-04-06", "A", 4, "CAT X"),
        ("2026-04-08", "B", 1, "CAT Y")]


def test_series_start_at_first_observation_without_known_zeros_before():
    p = ds.pair_daily(_data(ROWS))
    b = p[p.sku == "B"]
    assert b.fecha.iloc[0] == "2026-04-08" and b.dias_desde_primera_obs.iloc[0] == 0
    assert len(b) == 7 and len(p[p.sku == "A"]) == 14            # B: 8..14; A: 1..14 (calendario natural)


def test_zero_after_first_observation_is_observed_zero_and_mask_is_not_zero():
    p = ds.pair_daily(_data(ROWS))
    a = p[p.sku == "A"].set_index("fecha")
    assert a.loc["2026-04-01", "cantidad_base"] == 3 and a.loc["2026-04-01", "n_lineas"] == 2
    assert a.loc["2026-04-02", "estado"] == ds.CERO and a.loc["2026-04-02", "cantidad_base"] == 0
    for d in ("2026-04-03", "2026-04-12"):
        assert a.loc[d, "estado"] == ds.MASCARA and a.loc[d].isna()["cantidad_base"]
    assert a.index.is_monotonic_increasing and len(a) == 14      # calendario sin comprimir


def test_category_series_and_importe_in_exact_cents():
    p = ds.pair_daily(_data(ROWS))
    assert p[(p.sku == "A") & (p.fecha == "2026-04-01")].importe_centimos.iloc[0] == 1500
    c = ds.category_daily(p)
    y = c[c.categoria_corte == "CAT Y"]
    assert y.fecha.iloc[0] == "2026-04-08" and set(c.estado) == {ds.VENTA, ds.CERO, ds.MASCARA}
    x = c[c.categoria_corte == "CAT X"].set_index("fecha")
    assert x.loc["2026-04-06", "cantidad_base_suma_heterogenea"] == 4 and x.loc["2026-04-12", "estado"] == ds.MASCARA


def test_intermittency_ignores_masked_days_and_flags_single_sale():
    i = ds.intermittency(ds.pair_daily(_data(ROWS))).set_index("sku")
    assert i.loc["A", "dias"] == 12 and i.loc["A", "dias_con_venta"] == 2      # 14 dias - 2 enmascarados
    assert i.loc["B", "clase_sbc"] == "UNA_SOLA_VENTA" and i.loc["B", "dias"] == 6


def test_serialization_is_deterministic():
    p = ds.pair_daily(_data(ROWS))
    assert ds.to_csv_gz_bytes(p) == ds.to_csv_gz_bytes(p.copy())
    assert ds.content_sha256(p) == ds.content_sha256(ds.pair_daily(_data(ROWS)))


def test_day_without_any_rows_is_not_turned_into_zero():
    rows = [r for r in ROWS if r[0] != "2026-04-06"] + [("2026-04-07", "A", 1, "CAT X")]
    p = ds.pair_daily(_data(rows, skip_cover=("2026-04-06",)))
    a = p[p.sku == "A"].set_index("fecha")
    assert a.loc["2026-04-06", "estado"] == ds.SIN_COBERTURA and a.loc["2026-04-06"].isna()["cantidad_base"]
    assert a.loc["2026-04-02", "estado"] == ds.VENTA or a.loc["2026-04-02", "estado"] == ds.CERO
    assert ds.intermittency(p).set_index("sku").loc["A", "dias"] == 11
