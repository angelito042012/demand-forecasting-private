"""Motor de simulacion de reposicion determinista y auditable (T07).

ETIQUETA: Inventario simulado con supuestos; no corresponde al inventario real de la empresa.

Orden temporal exacto de cada dia natural d (por SKU, vectorizado):
  1. recepcion: on_hand += pedidos con llegada d
  2. demanda proxy del dia (ventas positivas observadas); NaN = dia sin demanda conocida
     (p. ej. 07/06 enmascarado): no hay evento ni denominador de servicio
  3. atendido = min(on_hand, demanda); faltante perdido = demanda - atendido (sin backorder)
  4. si d es dia de revision (final del dia): pedido q = max(0, objetivo - (on_hand + transito)),
     llegada en d+L (puede caer despues del horizonte: queda en transito final)
  5. holding del dia = costo * tasa_diaria * on_hand (saldo final del dia)
Cantidades enteras (unidades base); empaque y minimo 1. Saldo y posicion nunca negativos.
Los objetivos los calcula el llamador con informacion <= dia de revision; el motor no ve el futuro.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass
class SimResult:
    on_hand: np.ndarray       # (D, n) saldo final de cada dia
    served: np.ndarray        # (D, n)
    lost: np.ndarray          # (D, n)
    received: np.ndarray      # (D, n)
    ordered: np.ndarray       # (D, n) pedidos emitidos ese dia (llegan en d+L)
    pipeline_end: np.ndarray  # (n,) transito final
    stock0: np.ndarray        # (n,)
    holding: np.ndarray       # (n,) costo de mantenimiento supuesto acumulado


def ceil_stable(x: np.ndarray, decimals: int = 9) -> np.ndarray:
    """Techo con redondeo previo a 9 decimales (estabilidad numerica de los objetivos)."""
    return np.ceil(np.round(np.asarray(x, dtype=float), decimals)).astype(np.int64)


def simulate(demand: np.ndarray, review_days: list[int], targets: dict, L: int, stock0: np.ndarray,
             unit_cost: np.ndarray, annual_holding: float = 0.20, days_year: int = 365) -> SimResult:
    """demand: (n, D) con NaN = sin demanda conocida. targets: {indice_dia_revision: (n,) enteros >= 0}."""
    n, D = demand.shape
    known = ~np.isnan(demand)
    dem = np.where(known, demand, 0.0)
    if (dem < 0).any() or not np.array_equal(dem, np.round(dem)):
        raise ValueError("la demanda debe ser entera y no negativa")
    dem = dem.astype(np.int64)
    if (stock0 < 0).any() or (unit_cost < 0).any():
        raise ValueError("stock inicial y costos deben ser no negativos")
    pipe = np.zeros((n, D + L + 1), dtype=np.int64)
    on_hand = stock0.astype(np.int64).copy()
    out = {k: np.zeros((D, n), dtype=np.int64) for k in ("on_hand", "served", "lost", "received", "ordered")}
    holding = np.zeros(n)
    rate = annual_holding / days_year
    reviews = set(review_days)
    for d in range(D):
        arr = pipe[:, d]
        on_hand += arr
        out["received"][d] = arr
        served = np.minimum(on_hand, dem[:, d])
        lost = dem[:, d] - served
        on_hand -= served
        if d in reviews:
            transit = pipe[:, d + 1:].sum(axis=1)
            q = np.maximum(0, targets[d].astype(np.int64) - (on_hand + transit))
            pipe[:, d + L] += q
            out["ordered"][d] = q
        if (on_hand < 0).any():
            raise AssertionError("saldo negativo")
        out["served"][d], out["lost"][d], out["on_hand"][d] = served, lost, on_hand
        holding += unit_cost * rate * on_hand
    return SimResult(on_hand=out["on_hand"], served=out["served"], lost=out["lost"], received=out["received"],
                     ordered=out["ordered"], pipeline_end=pipe[:, D:].sum(axis=1), stock0=stock0.astype(np.int64),
                     holding=holding)


def check_conservation(res: SimResult, demand: np.ndarray) -> dict:
    """Identidades por SKU y de sistema. Lanza AssertionError si alguna falla."""
    known = ~np.isnan(demand)
    dem = np.where(known, demand, 0).astype(np.int64)
    bal = res.stock0 + res.received.sum(0) - res.served.sum(0) - res.on_hand[-1]
    assert (bal == 0).all(), "stock inicial + recibido - atendido != stock final"
    assert (res.served + res.lost == dem.T).all(), "atendido + perdido != demanda proxy"
    assert (res.ordered.sum(0) == res.received.sum(0) + res.pipeline_end).all(), "pedido != recibido + transito final"
    assert (res.on_hand >= 0).all() and (res.pipeline_end >= 0).all()
    assert (res.lost[:, :][~known.T] == 0).all(), "faltante en dia sin demanda conocida"
    return {"saldo_por_sku_ok": True, "demanda_ok": True, "pedidos_ok": True,
            "sistema": int(res.stock0.sum() + res.received.sum() - res.served.sum() - res.on_hand[-1].sum())}


def metrics(res: SimResult, demand: np.ndarray, unit_cost: np.ndarray, mask: np.ndarray | None = None) -> dict:
    """Metricas agregadas sobre los SKU de `mask` (todos por defecto). Compras y costo consumido se
    reportan por separado; no se calcula ahorro ni utilidad."""
    n = demand.shape[0]
    m = np.ones(n, bool) if mask is None else mask
    known = ~np.isnan(demand[m])                       # (n_m, D) dias evaluables por SKU
    eligible = float(np.where(known, demand[m], 0).sum())
    served = float(res.served[:, m].sum())
    lost = float(res.lost[:, m].sum())
    sku_days = int(known.sum())
    stockout_days = int(((res.lost[:, m].T > 0) & known).sum())
    demand_days = int((np.where(known, demand[m], 0) > 0).sum())
    c = unit_cost[m]
    ordered_units = res.ordered[:, m].sum(0)
    return {
        "skus": int(m.sum()), "dias_sku_evaluables": sku_days,
        "demanda_proxy_elegible_unidades": eligible, "atendidas_unidades": served, "perdidas_unidades": lost,
        "fill_rate": served / eligible if eligible > 0 else None,
        "dias_sku_con_faltante": stockout_days,
        "tasa_dias_sku_con_faltante": stockout_days / sku_days if sku_days else None,
        "tasa_faltante_sobre_dias_con_demanda": stockout_days / demand_days if demand_days else None,
        "stock_medio_unidades_por_dia": float(res.on_hand[:, m].sum(1).mean()),
        "stock_inicial_unidades": float(res.stock0[m].sum()), "stock_final_unidades": float(res.on_hand[-1][m].sum()),
        "pedidos_lineas": int((res.ordered[:, m] > 0).sum()), "pedidos_unidades": float(ordered_units.sum()),
        "recibidas_unidades": float(res.received[:, m].sum()), "transito_final_unidades": float(res.pipeline_end[m].sum()),
        "holding_supuesto": float(res.holding[m].sum()),
        "compras_desembolsadas_supuesto": float((ordered_units * c).sum()),
        "costo_consumido_supuesto": float((res.served[:, m].sum(0) * c).sum()),
        "valor_stock_inicial_supuesto": float((res.stock0[m] * c).sum()),
        "valor_stock_final_supuesto": float((res.on_hand[-1][m] * c).sum()),
        "valor_transito_final_supuesto": float((res.pipeline_end[m] * c).sum()),
    }


def value_identity(mt: dict) -> float:
    """compras + stock inicial - costo consumido - stock final - transito final = 0 (en valor, mismos costos)."""
    return (mt["compras_desembolsadas_supuesto"] + mt["valor_stock_inicial_supuesto"] - mt["costo_consumido_supuesto"]
            - mt["valor_stock_final_supuesto"] - mt["valor_transito_final_supuesto"])


def review_indices(n_days: int, every: int = 7, first: int = 0) -> list[int]:
    return list(range(first, n_days, every))


def rel_diff(a: float | None, ref: float | None) -> float | None:
    if a is None or ref is None or ref == 0 or math.isnan(ref):
        return None
    return (a - ref) / ref
