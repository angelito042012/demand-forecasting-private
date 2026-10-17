"""T07: motor de simulacion con casos manuales pequenos."""
import numpy as np
import pytest

from pipeline.sim import engine as eng

NAN = np.nan


def run(demand, reviews, targets, L, stock0, cost=None):
    d = np.array([demand], dtype=float)
    c = np.array([1.0 if cost is None else cost])
    res = eng.simulate(d, reviews, {k: np.array([v]) for k, v in targets.items()}, L, np.array([stock0]), c)
    return d, c, res


def test_order_arrives_exactly_after_lead_time_and_nothing_before():
    d, _, res = run([0] * 10, [0], {0: 5}, 3, 0)
    assert res.ordered[0, 0] == 5 and res.received[:, 0].tolist() == [0, 0, 0, 5, 0, 0, 0, 0, 0, 0]
    assert res.on_hand[:, 0].tolist() == [0, 0, 0, 5, 5, 5, 5, 5, 5, 5]
    eng.check_conservation(res, d)


def test_weekly_review_and_in_transit_prevents_duplicate_order():
    # L=14: la orden del dia 0 sigue en transito en la revision del dia 7; el objetivo ya esta cubierto
    d, _, res = run([0] * 22, [0, 7, 14, 21], {0: 5, 7: 5, 14: 5, 21: 5}, 14, 0)
    assert res.ordered[:, 0].tolist() == [5] + [0] * 21
    assert res.received[14, 0] == 5 and res.pipeline_end[0] == 0
    eng.check_conservation(res, d)


def test_stockout_is_lost_not_backordered_and_position_never_negative():
    d, _, res = run([5, 0, 0, 4], [], {}, 7, 2)
    assert res.served[:, 0].tolist() == [2, 0, 0, 0] and res.lost[:, 0].tolist() == [3, 0, 0, 4]
    assert (res.on_hand >= 0).all() and res.on_hand[-1, 0] == 0
    eng.check_conservation(res, d)


def test_review_after_sales_uses_posterior_stock_and_rounds_up():
    # dia 0: stock 10, demanda 4 -> 6; objetivo 9 -> pedido 3 (llega dia 2)
    _d, _, res = run([4, 0, 0], [0], {0: 9}, 2, 10)
    assert res.ordered[0, 0] == 3 and res.on_hand[:, 0].tolist() == [6, 6, 9]
    assert eng.ceil_stable(np.array([2.0000000001, 2.000000002, 0.0, -0.3])).tolist() == [2, 3, 0, 0]


def test_unknown_demand_day_has_no_event_and_no_denominator():
    d, c, res = run([3, NAN, 2], [], {}, 1, 10)
    assert res.served[:, 0].tolist() == [3, 0, 2] and res.lost.sum() == 0
    m = eng.metrics(res, d, c)
    assert m["dias_sku_evaluables"] == 2 and m["demanda_proxy_elegible_unidades"] == 5 and m["fill_rate"] == 1.0
    assert m["tasa_dias_sku_con_faltante"] == 0.0
    eng.check_conservation(res, d)


def test_terminal_stock_pipeline_costs_and_value_identity():
    # stock0=2, L=3, revisiones en los dias 0 y 3 de un horizonte de 5 dias, costo 2
    # d0: vende 1 (queda 1), pide 6-(1+0)=5 -> llega d3; d1: queda 0; d2: faltante 1;
    # d3: recibe 5, vende 1 (queda 4), pide 6-(4+0)=2 -> llega d6 (transito final); d4: queda 3
    d, c, res = run([1, 1, 1, 1, 1], [0, 3], {0: 6, 3: 6}, 3, 2, cost=2.0)
    eng.check_conservation(res, d)
    m = eng.metrics(res, d, c)
    assert res.ordered[:, 0].tolist() == [5, 0, 0, 2, 0] and res.on_hand[:, 0].tolist() == [1, 0, 0, 4, 3]
    assert m["transito_final_unidades"] == 2 and m["recibidas_unidades"] == 5 and m["perdidas_unidades"] == 1
    assert m["compras_desembolsadas_supuesto"] == 7 * 2.0 and m["costo_consumido_supuesto"] == 4 * 2.0
    assert m["valor_stock_final_supuesto"] == 3 * 2.0 and m["valor_transito_final_supuesto"] == 2 * 2.0
    assert abs(eng.value_identity(m)) < 1e-12
    assert m["holding_supuesto"] == pytest.approx(2.0 * (0.20 / 365) * (1 + 0 + 0 + 4 + 3))
    assert m["fill_rate"] == pytest.approx(4 / 5) and m["dias_sku_con_faltante"] == 1


def test_zero_denominators_are_not_evaluable_and_rel_diff_guards():
    d, c, res = run([0, 0, 0], [], {}, 1, 3)
    m = eng.metrics(res, d, c)
    assert m["fill_rate"] is None and m["demanda_proxy_elegible_unidades"] == 0
    assert eng.rel_diff(1.0, 0.0) is None and eng.rel_diff(None, 1.0) is None and eng.rel_diff(3.0, 2.0) == 0.5


def test_non_integer_or_negative_demand_rejected():
    with pytest.raises(ValueError):
        eng.simulate(np.array([[1.5]]), [], {}, 1, np.array([1]), np.array([1.0]))
    with pytest.raises(ValueError):
        eng.simulate(np.array([[-1.0]]), [], {}, 1, np.array([1]), np.array([1.0]))


def test_identical_inputs_give_identical_results_and_policies_share_initial_state():
    dem = np.array([[2, 0, 5, 1, 0, 3, 2, 2, 0, 1]], dtype=float)
    a = eng.simulate(dem, [0, 7], {0: np.array([6]), 7: np.array([6])}, 3, np.array([4]), np.array([1.0]))
    b = eng.simulate(dem, [0, 7], {0: np.array([6]), 7: np.array([6])}, 3, np.array([4]), np.array([1.0]))
    assert np.array_equal(a.on_hand, b.on_hand) and np.array_equal(a.ordered, b.ordered)
    other = eng.simulate(dem, [0, 7], {0: np.array([9]), 7: np.array([9])}, 3, np.array([4]), np.array([1.0]))
    assert a.stock0[0] == other.stock0[0] == 4
