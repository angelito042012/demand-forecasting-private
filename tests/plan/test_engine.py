"""Motor puro del plan T19: ejemplos calculados a mano (contrato §4), conservacion, minimalidad y validaciones."""
from __future__ import annotations

from datetime import date, timedelta
from fractions import Fraction as F

import pytest

from pipeline.plan import engine as e

COUNT = date(2026, 10, 18)
CUT = date(2026, 9, 30)
MS, ME = date(2026, 11, 1), date(2026, 11, 30)
M2 = F(2)


def scen(libre, lead, *, m=M2, decision=COUNT, reserve=7, minimo=1, mult=1, pending=None, month=(MS, ME)):
    return e.calc_scenario(m=m, libre=libre, count_date=COUNT, decision_date=decision, lead=lead, reserve_days=reserve,
                           min_order=minimo, order_multiple=mult, month_start=month[0], month_end=month[1],
                           pending={d: F(q) for d, q in (pending or {}).items()})


def d(day, month=10):
    return date(2026, month, day)


# ------------------------------------------------------------------ prevision
def test_forecast_exact_mean_and_window():
    by_day = {date(2026, 9, 3) + timedelta(days=k): F(2) for k in range(28)}
    fc = e.forecast_promedio_28(by_day, CUT)
    assert (fc.window_start, fc.window_end, fc.sum_28, fc.days_valid, fc.m) == (date(2026, 9, 3), CUT, 56, 28, 2)
    assert fc.masked_days == ()
    frac = e.forecast_promedio_28({date(2026, 9, 30): F(1)}, CUT)
    assert frac.m == F(1, 28)                       # sin redondeo diario
    assert e.exact(frac.m * 30) == "15/14" and e.dec(frac.m * 30) == "1.071"


def test_forecast_ignores_days_outside_the_window_and_after_cutoff():
    base = {date(2026, 9, 3) + timedelta(days=k): F(2) for k in range(28)}
    noisy = {**base, date(2026, 9, 2): F(999), date(2026, 10, 5): F(5000), date(2026, 8, 1): F(7)}
    assert e.forecast_promedio_28(noisy, CUT) == e.forecast_promedio_28(base, CUT)


@pytest.mark.parametrize("cutoff,masked,valid", [
    (date(2026, 6, 20), (date(2026, 6, 7),), 27),
    (date(2026, 4, 14), (date(2026, 4, 3), date(2026, 4, 12)), 26),
    (date(2026, 9, 30), (), 28)])
def test_masked_days_leave_the_window_numerator_and_denominator(cutoff, masked, valid):
    ws = cutoff - timedelta(days=27)
    by_day = {ws + timedelta(days=k): F(2) for k in range(28)}
    for md in masked:
        by_day[md] = F(100)                          # lo vendido en un dia enmascarado no cuenta
    fc = e.forecast_promedio_28(by_day, cutoff)
    assert fc.masked_days == masked and fc.days_valid == valid
    assert fc.sum_28 == 2 * valid and fc.m == 2


def test_zero_with_complete_coverage_is_zero_and_explained_not_october_zero():
    res = _product(libre=30, by_day={}, history_rows=3)
    fc = res["forecast"]
    assert fc["daily"] == "0" and fc["month_total"] == "0" and fc["zero_reason"] == "SIN_VENTAS_EN_VENTANA"
    assert "octubre" in fc["note"]
    sc = res["scenarios"]["7"]
    assert sc["status"] == "OK" and sc["purchase_qty"] == 0 and sc["end_stock"] == "30"
    assert sc["served_month"] == "0" and sc["shortage_month"] == "0"       # demanda 0, no "octubre vendido 0"


def _product(*, libre, by_day, unit="UND", window_units=frozenset({"UND"}), history_units=frozenset({"UND"}),
             history_rows=1, params=None, pending=None):
    p = params or e.validate_params(
        {"month": "2026-11", "decision_date": "2026-10-18", "lead_days": [7, 14], "reserve_days": 7, "min_order": 1,
         "order_multiple": 1, "pending_orders": []}, count_date=COUNT, sales_cutoff=CUT, group_ids=["1"])
    return e.compute_product(params=p, count_date=COUNT, sales_cutoff=CUT, libre=libre, unidad_reporte=unit,
                             by_day=by_day, window_units=window_units, history_units=history_units,
                             history_rows=history_rows, pending=pending)


# ------------------------------------------------------------------ ejemplos del contrato §4 (m = 2, reserva 14)
def test_ex1_enough_stock_zero_is_calculated_and_explained():
    c = scen(500, 7)
    assert c["arrival_date"] == d(25) and c["consumed_before_arrival"] == 12 and c["shortage_before_arrival"] == 0
    assert c["stock_at_arrival"] == 488 and c["qty"] == 0 and c["status"] == "OK"
    assert c["final_need"] == 2 * 37 + 14 - 488 == -400
    s = e.serialize_scenario(c)
    assert s["purchase_qty"] == 0 and s["breakdown"]["binding"] == "none"
    assert [st["key"] for st in s["explanation"]][-1] == "purchase_qty" and s["explanation"][-1]["value"] == "0"


def test_ex2_stock_40_lead7_bridge_month_reserve():
    c = scen(40, 7)
    assert c["stock_at_arrival"] == 28
    assert (c["bridge_days"], c["month_days_after_arrival"]) == (7, 30)
    s = e.serialize_scenario(c)
    b = s["breakdown"]
    assert (b["bridge_demand"], b["month_demand"], b["reserve"], b["total_need"]) == ("14", "60", "14", "88")
    assert c["qty"] == 60 and s["purchase_qty"] == 60 and s["status"] == "OK"
    assert s["stock_month_start"] == "74"            # 28 + 60 de la orden - 14 de puente
    # el desglose reproduce la cantidad: necesidad - S - recepciones posteriores = 60
    assert F(b["total_need"]) - F(b["stock_at_arrival"]) - F(b["pending_after_arrival"]) == 60


def test_ex2_stock_40_lead14_same_quantity_not_forced_to_differ():
    c = scen(40, 14)
    assert c["arrival_date"] == date(2026, 11, 1) and c["consumed_before_arrival"] == 26
    assert c["stock_at_arrival"] == 14 and c["bridge_days"] == 0 and c["qty"] == 60
    assert scen(40, 7)["qty"] == c["qty"]
    assert e.serialize_scenario(c)["stock_month_start"] == "74"     # 14 + 60 al inicio del 01/11


def test_ex3_stock_10_lost_sales_are_not_inherited():
    c14, c7 = scen(10, 14), scen(10, 7)
    assert c14["consumed_before_arrival"] == 10 and c14["shortage_before_arrival"] == 16
    assert c14["stock_at_arrival"] == 0 and c14["qty"] == 74            # 60 + 14 - 0; no se suman las perdidas
    assert c7["consumed_before_arrival"] == 10 and c7["shortage_before_arrival"] == 2
    assert c7["stock_at_arrival"] == 0 and c7["qty"] == 88              # 74 + 14
    assert c14["qty"] < c7["qty"] and c14["shortage_before_arrival"] > c7["shortage_before_arrival"]
    assert c14["shortage_before_month"] == 16 and c14["shortage_month"] == 0 and c14["status"] == "OK"


def test_ex4_late_arrival_inside_the_month():
    ok = scen(40, 14, decision=d(25))
    assert ok["arrival_date"] == date(2026, 11, 8) and ok["stock_at_arrival"] == 0 and ok["shortage_before_arrival"] == 0
    assert ok["bridge_days"] == 0 and ok["month_days_after_arrival"] == 23 and ok["qty"] == 60 and ok["status"] == "OK"
    late = scen(20, 14, decision=d(25))
    assert late["shortage_before_arrival"] == 20                       # 29/10 a 07/11: 10 dias x 2
    assert late["shortage_before_month"] == 6 and late["shortage_month"] == 14      # 29-31/10 = 6; 1-7/11 = 14
    assert late["stock_at_arrival"] == 0 and late["qty"] == 60 and late["status"] == "LLEGA_TARDE"
    assert late["demand_before_arrival_in_month"] == 14
    assert late["served_month"] == 2 * 23


def test_ex5_pending_with_date_later_receipt_does_not_cover_earlier_shortage():
    c = scen(40, 7, pending={date(2026, 11, 5): 30})
    assert c["stock_at_arrival"] == 28 and c["final_need"] == 30 and c["prefix_need"] < 30
    assert c["qty"] == 30 and c["binding"] == "final"
    rows = {r.day: r for r in c["rows"]}
    assert rows[date(2026, 11, 5)].recepciones == 30 and rows[date(2026, 11, 4)].recepciones == 0
    assert all(r.faltante == 0 for r in c["rows"] if r.day >= d(25))
    # con pedido pendiente de 30 el 20/10 (antes de A) entra en S, no se vuelve a restar
    early = scen(40, 7, pending={d(20): 30})
    assert early["stock_at_arrival"] == 28 + 30 and early["pending_after_arrival"] == 0
    assert early["qty"] == 88 - 58 == 30
    # pedido el mismo dia A: forma parte de S (se aplica una sola vez)
    same = scen(40, 7, pending={d(25): 30})
    assert same["stock_at_arrival"] == 58 and same["qty"] == 30


def test_late_pending_makes_the_prefix_the_binding_constraint():
    # 100 unidades llegan el 29/11, pero al 28/11 el consumo acumulado desde A es 70 > S=28 => Q >= 42
    c = scen(40, 7, pending={date(2026, 11, 29): 100})
    assert c["final_need"] == 74 + 14 - 28 - 100 == -40
    assert (c["prefix_need"], c["binding"], c["binding_date"]) == (42, "prefix", date(2026, 11, 28))
    assert c["qty"] == 42
    # Q-1 deja un faltante el 28/11
    low = e.run_days(F(28), d(25), ME, M2, {d(25): 41, date(2026, 11, 29): 100})
    assert any(r.faltante > 0 for r in low)
    ok = e.run_days(F(28), d(25), ME, M2, {d(25): 42, date(2026, 11, 29): 100})
    assert all(r.faltante == 0 for r in ok) and ok[-1].fin >= 14
    assert e.serialize_scenario(c)["explanation"][-3]["key"] == "prefix_need"


def test_ex6_does_not_arrive_in_time_with_required_decision_date():
    c = scen(40, 14, decision=date(2026, 11, 25))
    assert c["arrival_date"] == date(2026, 12, 9) and c["status"] == "NO_LLEGA_A_TIEMPO" and c["qty"] is None
    assert c["required_arrival_date"] == d(18)                          # 01/11 - 14 dias
    s = e.serialize_scenario(c)
    assert s["purchase_qty"] is None and s["required_arrival_date"] == "2026-10-18"
    assert s["explanation"][-1]["key"] == "required_date"
    assert all(r.day <= ME for r in c["rows"])                          # no se proyecta una orden de diciembre
    assert c["shortage_month"] > 0 and c["end_stock"] == 0


def test_ex6_order_multiple_12_rounds_only_at_the_end():
    c = scen(47, 7, mult=12)                                            # S = 35 => 88 - 35 = 53
    assert c["stock_at_arrival"] == 35 and c["qty_unrounded"] == 53 and c["qty"] == 60
    assert scen(47, 7, mult=1)["qty"] == 53
    assert scen(47, 7, minimo=50, mult=12)["qty"] == 60
    assert scen(47, 7, minimo=70, mult=12)["qty"] == 72
    assert scen(47, 7, minimo=100)["qty"] == 100
    assert scen(500, 7, minimo=100)["qty"] == 0                          # el minimo no fuerza una compra innecesaria


def test_ex6_not_calculable_is_not_zero():
    for libre, unit, reason in ((None, "UND", "SIN_CONTEO"), (5, "CAJA", "UNIDAD_INCOMPATIBLE")):
        r = _product(libre=libre, unit=unit, by_day={date(2026, 9, 30): F(1)})
        assert r["status"] == "NO_CALCULABLE" and r["reason"] == reason
        assert all(s["status"] == "NO_CALCULABLE" and s["purchase_qty"] is None and s["series"] == []
                   for s in r["scenarios"].values())
    assert _product(libre=5, by_day={}, history_rows=0)["reason"] == "SIN_SENAL"
    assert _product(libre=5, by_day={}, history_units=frozenset({"CAJA"}))["reason"] == "UNIDAD_INCOMPATIBLE"
    assert _product(libre=5, by_day={}, window_units=frozenset({"UND", "PAQ"}))["reason"] == "UNIDAD_INCOMPATIBLE"


# ------------------------------------------------------------------ invariantes (bateria)
def _battery():
    ms = [F(2), F(17, 28), F(0), F(5, 3), F(1, 28)]
    cases = []
    for m in ms:
        for libre in (0, 1, 10, 40, 333, 500):
            for lead in (1, 7, 14, 30):
                for decision in (COUNT, d(25), date(2026, 11, 10), date(2026, 11, 28)):
                    for reserve, mult, minimo in ((7, 1, 1), (0, 1, 1), (30, 12, 50), (3, 5, 1)):
                        for pend in (None, {date(2026, 11, 5): 30}, {d(20): 7, date(2026, 11, 29): 100}):
                            cases.append((m, libre, lead, decision, reserve, mult, minimo, pend))
    return cases


def test_balance_conservation_all_series():
    n = 0
    for m, libre, lead, decision, reserve, mult, minimo, pend in _battery():
        c = scen(libre, lead, m=m, decision=decision, reserve=reserve, mult=mult, minimo=minimo, pending=pend)
        prev = F(libre)
        assert c["rows"][0].day == d(19) and c["rows"][-1].day == ME
        for r in c["rows"]:
            assert r.inicio == prev                                        # inicio_t = fin_{t-1}
            assert r.inicio + r.recepciones - r.atendida == r.fin          # conservacion de unidades
            assert r.disponible == r.inicio + r.recepciones
            assert r.atendida + r.faltante == r.demanda == m
            assert r.fin >= 0 and r.atendida <= r.disponible and r.faltante >= 0
            assert (r.faltante == 0) or (r.fin == 0)                       # solo hay faltante si el stock se agoto
            prev = r.fin
        total_rec = sum(r.recepciones for r in c["rows"])
        assert libre + total_rec - sum(r.atendida for r in c["rows"]) == c["rows"][-1].fin
        s = e.serialize_scenario(c)
        assert [F(x["fin"]) for x in s["series"]] == [r.fin for r in c["rows"]]
        n += 1
    assert n > 1500


def test_quantity_satisfies_prefixes_and_reserve_and_is_minimal():
    checked = 0
    for m, libre, lead, decision, reserve, mult, minimo, pend in _battery():
        c = scen(libre, lead, m=m, decision=decision, reserve=reserve, mult=mult, minimo=minimo, pending=pend)
        if c["status"] == "NO_LLEGA_A_TIEMPO":
            assert c["qty"] is None
            continue
        A, q = c["arrival_date"], c["qty"]
        pending = {k: F(v) for k, v in (pend or {}).items()}
        R = reserve * m

        def violates(qty, A=A, c=c, pending=pending, R=R, m=m):
            rec = dict(pending)
            rec[A] = rec.get(A, F(0)) + qty
            pre = e.run_days(F(c["libre"]), d(19), A - timedelta(days=1), m, pending)
            start = pre[-1].fin if pre else F(c["libre"])
            post = e.run_days(start, A, ME, m, rec)
            return any(r.faltante > 0 for r in post) or post[-1].fin < R

        assert not violates(q), (m, libre, lead, decision, reserve, pend)      # cumple cada prefijo y la reserva
        assert q % mult == 0 and (q == 0 or q >= minimo)
        if q > 0:
            lower = q - mult
            # el menor multiplo anterior (o cualquier cantidad menor que cumpla el minimo) incumple prefijos o reserva
            if lower >= minimo:          # un candidato menor permitido por minimo y multiplo
                assert violates(lower), (m, libre, lead, decision, reserve, mult, minimo, pend, q)
            if mult == 1 and minimo == 1:
                assert violates(q - 1)
        checked += 1
    assert checked > 1000


def test_decision_date_later_than_count_projects_from_the_count():
    c = scen(40, 7, decision=d(25))
    assert c["arrival_date"] == date(2026, 11, 1) and c["rows"][0].day == d(19)
    assert c["consumed_before_arrival"] == 26 and c["stock_at_arrival"] == 14 and c["qty"] == 60


def test_events_are_ordered_and_receipts_precede_demand():
    s = e.serialize_scenario(scen(40, 7, pending={date(2026, 11, 5): 30, d(25): 3}))
    types = [(ev["date"], ev["type"]) for ev in s["events"]]
    assert types == sorted(types, key=lambda t: (t[0], ["CONTEO", "DECISION_ORDEN", "RECEPCION_PENDIENTE",
                                                       "LLEGADA_ORDEN", "PRIMER_DIA_CON_FALTANTE"].index(t[1])))
    assert s["event_order"] == "recepciones(t) -> demanda(t)"
    assert types[0] == ("2026-10-18", "CONTEO")


# ------------------------------------------------------------------ formato y validaciones
def test_exact_and_decimal_formats():
    assert e.exact(F(4, 2)) == "2" and e.exact(F(-1, 3)) == "-1/3" and e.dec(F(1, 3)) == "0.333"
    assert e.dec(F(2, 3)) == "0.667" and e.dec(F(5)) == "5" and e.dec(F(-1, 3)) == "-0.333" and e.dec(F(1, 2000)) == "0.001"
    assert e.dec(F(1, 4000)) == "0" and e.dec(F(1005, 1000)) == "1.005" and e.dec(F(-1, 5000)) == "0"


RAW = {"month": "2026-11", "decision_date": "2026-10-18", "lead_days": [7, 14], "reserve_days": 7, "min_order": 1,
       "order_multiple": 1, "pending_orders": []}


def vp(**kw):
    raw = {**RAW, **kw}
    return e.validate_params(raw, count_date=COUNT, sales_cutoff=CUT, group_ids=["1", "2"])


def test_valid_params_normalised_and_ordered():
    p = vp(lead_days=[14, 7], pending_orders=[{"producto_id": "2", "units": 5, "arrival_date": "2026-11-03", "nature": "REPORTADA"},
                                              {"producto_id": "1", "units": 3, "arrival_date": "2026-10-19", "nature": "ASUMIDA"}])
    assert p.lead_days == (7, 14) and [o.producto_id for o in p.pending] == ["1", "2"]
    assert p.pending_by_product()["1"] == {date(2026, 10, 19): 3}
    assert vp(month="2026-12", decision_date="2026-12-31").month == "2026-12"


@pytest.mark.parametrize("kw,code", [
    ({"month": "2026-13"}, "MES_INVALIDO"), ({"month": "noviembre"}, "MES_INVALIDO"), ({"month": 11}, "MES_INVALIDO"),
    ({"month": "2026-10"}, "MES_NO_POSTERIOR_AL_CONTEO"), ({"month": "2027-01"}, "HORIZONTE_EXCEDIDO"),
    ({"month": "2027-02"}, "HORIZONTE_EXCEDIDO"),
    ({"decision_date": "2026-10-17"}, "DECISION_ANTERIOR_AL_CONTEO"), ({"decision_date": "2026-12-01"}, "DECISION_FUERA_DE_RANGO"),
    ({"decision_date": "18/10/2026"}, "FECHA_INVALIDA"), ({"decision_date": None}, "FECHA_INVALIDA"),
    ({"decision_date": "2026-02-30"}, "FECHA_INVALIDA"),
    ({"lead_days": []}, "PLAZOS_INVALIDOS"), ({"lead_days": [0]}, "PLAZOS_INVALIDOS"), ({"lead_days": [61]}, "PLAZOS_INVALIDOS"),
    ({"lead_days": [1, 2, 3, 4, 5]}, "PLAZOS_INVALIDOS"), ({"lead_days": [7, 7]}, "PLAZOS_INVALIDOS"),
    ({"lead_days": [7.5]}, "PLAZOS_INVALIDOS"), ({"lead_days": [True]}, "PLAZOS_INVALIDOS"), ({"lead_days": "7"}, "PLAZOS_INVALIDOS"),
    ({"reserve_days": 31}, "RESERVA_INVALIDA"), ({"reserve_days": -1}, "RESERVA_INVALIDA"), ({"reserve_days": 1.5}, "RESERVA_INVALIDA"),
    ({"min_order": 0}, "MINIMO_INVALIDO"), ({"min_order": "1"}, "MINIMO_INVALIDO"),
    ({"order_multiple": 0}, "MULTIPLO_INVALIDO"), ({"order_multiple": 2.5}, "MULTIPLO_INVALIDO"),
    ({"pending_orders": [{"producto_id": "1", "units": 5, "arrival_date": None, "nature": "ASUMIDA"}]}, "PENDIENTE_SIN_FECHA"),
    ({"pending_orders": [{"producto_id": "1", "units": 5, "nature": "ASUMIDA"}]}, "PENDIENTE_SIN_FECHA"),
    ({"pending_orders": [{"producto_id": "1", "units": 5, "arrival_date": "2026-10-18", "nature": "ASUMIDA"}]}, "PENDIENTE_INVALIDO"),
    ({"pending_orders": [{"producto_id": "1", "units": 5, "arrival_date": "2026-12-01", "nature": "ASUMIDA"}]}, "PENDIENTE_INVALIDO"),
    ({"pending_orders": [{"producto_id": "99", "units": 5, "arrival_date": "2026-11-03", "nature": "ASUMIDA"}]}, "PENDIENTE_INVALIDO"),
    ({"pending_orders": [{"producto_id": "1", "units": 0, "arrival_date": "2026-11-03", "nature": "ASUMIDA"}]}, "PENDIENTE_INVALIDO"),
    ({"pending_orders": [{"producto_id": "1", "units": 2.5, "arrival_date": "2026-11-03", "nature": "ASUMIDA"}]}, "PENDIENTE_INVALIDO"),
    ({"pending_orders": [{"producto_id": "1", "units": 5, "arrival_date": "2026-11-03", "nature": "CIERTA"}]}, "PENDIENTE_INVALIDO"),
    ({"pending_orders": [{"producto_id": "1", "units": 5, "arrival_date": "2026-11-03", "nature": "ASUMIDA", "x": 1}]}, "PENDIENTE_INVALIDO"),
])
def test_validation_codes(kw, code):
    with pytest.raises(e.PlanRejected) as ex:
        vp(**kw)
    assert ex.value.code == code


def test_extra_parameter_rejected_and_horizon_boundary():
    with pytest.raises(e.PlanRejected) as ex:
        e.validate_params({**RAW, "extra": 1}, count_date=COUNT, sales_cutoff=CUT, group_ids=["1"])
    assert ex.value.code == "ENTRADA_INVALIDA"
    assert e.allowed_months(COUNT, CUT) == ["2026-11", "2026-12"]            # enero termina el 31/01 > 28/01/2027
    assert CUT + timedelta(days=120) == date(2027, 1, 28)


def test_plan_id_depends_on_every_input():
    base = vp()
    ident = e.identity(base, dataset_id="ds", sales_cutoff="2026-09-30", snapshot_id="s", snapshot_sha256="a",
                       snapshot_csv_sha256="b")
    pid = e.plan_id_for(base, ident)
    assert pid == e.plan_id_for(base, dict(ident)) and pid.startswith("plan-2026-11-d20261018-") and len(pid) == 35
    assert e.plan_id_for(vp(lead_days=[14, 7]), e.identity(vp(lead_days=[14, 7]), dataset_id="ds", sales_cutoff="2026-09-30",
                                                           snapshot_id="s", snapshot_sha256="a", snapshot_csv_sha256="b")) == pid
    variants = [{"dataset_id": "ds2"}, {"sales_cutoff": "2026-10-31"}, {"snapshot_id": "s2"}, {"snapshot_sha256": "x"},
                {"snapshot_csv_sha256": "y"}]
    seen = {pid}
    for v in variants:
        kw = {"dataset_id": "ds", "sales_cutoff": "2026-09-30", "snapshot_id": "s", "snapshot_sha256": "a", "snapshot_csv_sha256": "b"}
        kw.update(v)
        seen.add(e.plan_id_for(base, e.identity(base, **kw)))
    for p in (vp(reserve_days=8), vp(min_order=2), vp(order_multiple=2), vp(lead_days=[7]), vp(decision_date="2026-10-19"),
              vp(month="2026-12", decision_date="2026-10-18"),
              vp(pending_orders=[{"producto_id": "1", "units": 5, "arrival_date": "2026-11-03", "nature": "ASUMIDA"}]),
              vp(pending_orders=[{"producto_id": "1", "units": 5, "arrival_date": "2026-11-03", "nature": "REPORTADA"}])):
        seen.add(e.plan_id_for(p, e.identity(p, dataset_id="ds", sales_cutoff="2026-09-30", snapshot_id="s",
                                             snapshot_sha256="a", snapshot_csv_sha256="b")))
    assert len(seen) == 1 + len(variants) + 8
