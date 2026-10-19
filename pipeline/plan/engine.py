"""T19 — Motor PURO del plan de compra de un mes (contrato docs/T19_CONTRATO_PLANIFICACION.md §2-§4).

Sin Mongo, sin reloj, sin red: solo `fractions.Fraction` (aritmetica exacta; nada se redondea por dia, solo la compra
final). Recibe ventas por dia ya cargadas, el stock del conteo y los parametros; devuelve diccionarios JSON-ables con
cantidades como texto exacto (`"p"` o `"p/q"`).

Convencion del dia `t`: (1) recepciones del dia (pedidos pendientes y, si t = A, la orden nueva) al INICIO del dia;
(2) despues la demanda `m`. `inicio` = stock al cierre del dia anterior; `disponible` = inicio + recepciones;
atendida = min(disponible, m); faltante = m - atendida (venta no atendida: NO se arrastra); fin = disponible - atendida.
"""
from __future__ import annotations

import calendar
import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from fractions import Fraction
from typing import NamedTuple

ENGINE_VERSION = "plan-engine-1.0.0"
CONTRACT_VERSION = "T19-1"
METHOD = "promedio_28"
WINDOW_DAYS = 28
HORIZON_DAYS = 120
MASK_DAYS = frozenset({date(2026, 4, 3), date(2026, 4, 12), date(2026, 6, 7)})
LEAD_MIN, LEAD_MAX, MAX_LEADS = 1, 60, 4
RESERVE_MAX = 30
MAX_PENDING = 500
MAX_UNITS = 10_000_000
MAX_MULTIPLE = 1_000_000
NATURES = ("REPORTADA", "ASUMIDA")
STATUSES = ("OK", "LLEGA_TARDE", "NO_LLEGA_A_TIEMPO", "NO_CALCULABLE")
_WORST = {"OK": 0, "LLEGA_TARDE": 1, "NO_LLEGA_A_TIEMPO": 2, "NO_CALCULABLE": 3}
REASON_TEXT = {
    "SIN_CONTEO": "El producto no tiene cantidad libre en el conteo; sin conteo no se calcula (no es cero).",
    "UNIDAD_INCOMPATIBLE": "La unidad de las ventas o del conteo no es UND; no se infieren equivalencias.",
    "SIN_SENAL": "El producto no tiene ventas registradas en la fuente; sin señal no se calcula (no es cero).",
}
_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_CODE_RE = re.compile(r"^[A-Za-z0-9._-]{1,32}$")


class PlanRejected(Exception):
    """Entrada o fuente no valida; `code` estable, sin rutas ni secretos."""

    def __init__(self, code: str, message: str, field: str | None = None):
        super().__init__(f"[{code}] {message}")
        self.code, self.message, self.field = code, message, field


# ------------------------------------------------------------------ formato
def exact(x: Fraction) -> str:
    x = Fraction(x)
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"


def dec(x: Fraction, places: int = 3) -> str:
    """Texto decimal con hasta `places` decimales (redondeo mitad-hacia-afuera; sin ceros finales). Solo presentacion."""
    x = Fraction(x)
    scale = 10 ** places
    q, r = divmod(abs(x.numerator) * scale, x.denominator)
    if 2 * r >= x.denominator:
        q += 1
    ip, fp = divmod(q, scale)
    out = f"{'-' if x < 0 and q else ''}{ip}"
    return out + ("." + f"{fp:0{places}d}".rstrip("0") if fp else "")


def parse_exact(text: str) -> Fraction:
    return Fraction(text)


def _ceil(x: Fraction) -> int:
    return -((-x.numerator) // x.denominator)


def _dmy(d: date) -> str:
    return f"{d.day:02d}/{d.month:02d}/{d.year}"


def month_bounds(month: str) -> tuple[date, date]:
    if not isinstance(month, str) or not _MONTH_RE.match(month):
        raise PlanRejected("MES_INVALIDO", "El mes debe tener el formato AAAA-MM.", "month")
    y, m = int(month[:4]), int(month[5:])
    return date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1])


def _days(a: date, b: date) -> int:
    """Dias naturales de a a b, ambos incluidos (0 si b < a)."""
    return max(0, (b - a).days + 1)


def allowed_months(count_date: date, sales_cutoff: date) -> list[str]:
    """Meses que empiezan despues del conteo y terminan <= corte + 120 dias (horizonte acotado)."""
    out, y, m = [], count_date.year, count_date.month
    limit = sales_cutoff + timedelta(days=HORIZON_DAYS)
    for _ in range(14):
        m += 1
        if m == 13:
            y, m = y + 1, 1
        s, e = month_bounds(f"{y:04d}-{m:02d}")
        if s > count_date and e <= limit:
            out.append(f"{y:04d}-{m:02d}")
    return out


# ------------------------------------------------------------------ parametros
@dataclass(frozen=True)
class PendingOrder:
    producto_id: str
    units: int
    arrival_date: date
    nature: str


@dataclass(frozen=True)
class PlanParams:
    month: str
    decision_date: date
    lead_days: tuple[int, ...]
    reserve_days: int
    min_order: int
    order_multiple: int
    pending: tuple[PendingOrder, ...] = ()

    def to_dict(self) -> dict:
        return {"month": self.month, "decision_date": self.decision_date.isoformat(), "lead_days": list(self.lead_days),
                "reserve_days": self.reserve_days, "min_order": self.min_order, "order_multiple": self.order_multiple,
                "pending_orders": [{"producto_id": p.producto_id, "units": p.units,
                                    "arrival_date": p.arrival_date.isoformat(), "nature": p.nature}
                                   for p in self.pending]}

    def pending_by_product(self) -> dict[str, dict[date, Fraction]]:
        out: dict[str, dict[date, Fraction]] = {}
        for p in self.pending:
            d = out.setdefault(p.producto_id, {})
            d[p.arrival_date] = d.get(p.arrival_date, Fraction(0)) + p.units
        return out


def _int(v, field: str, code: str, lo: int, hi: int, what: str) -> int:
    if isinstance(v, bool) or not isinstance(v, int):
        raise PlanRejected(code, f"{what} debe ser un número entero.", field)
    if not lo <= v <= hi:
        raise PlanRejected(code, f"{what} debe estar entre {lo} y {hi}.", field)
    return v


def _date(v, field: str, code: str = "FECHA_INVALIDA") -> date:
    if not isinstance(v, str) or len(v) != 10:
        raise PlanRejected(code, "La fecha debe tener el formato AAAA-MM-DD.", field)
    try:
        return date.fromisoformat(v)
    except ValueError:
        raise PlanRejected(code, "La fecha no es válida.", field) from None


def validate_params(raw: Mapping, *, count_date: date, sales_cutoff: date, group_ids) -> PlanParams:
    """Validacion del servidor (contrato §2, §3, §6). Lanza PlanRejected con codigos estables."""
    if not isinstance(raw, Mapping):
        raise PlanRejected("ENTRADA_INVALIDA", "Los parámetros deben ser un objeto.")
    extra = set(raw) - {"month", "decision_date", "lead_days", "reserve_days", "min_order", "order_multiple",
                        "pending_orders"}
    if extra:
        raise PlanRejected("ENTRADA_INVALIDA", "Parámetros no permitidos.", min(extra)[:40])
    start, end = month_bounds(raw.get("month"))
    if start <= count_date:
        raise PlanRejected("MES_NO_POSTERIOR_AL_CONTEO", "El mes objetivo debe empezar después de la fecha del conteo.",
                           "month")
    if end > sales_cutoff + timedelta(days=HORIZON_DAYS):
        raise PlanRejected("HORIZONTE_EXCEDIDO", "El mes termina más de 120 días después de la última venta conocida.",
                           "month")
    decision = _date(raw.get("decision_date"), "decision_date")
    if decision < count_date:
        raise PlanRejected("DECISION_ANTERIOR_AL_CONTEO",
                           "La fecha de decisión no puede ser anterior al conteo (sería información futura).",
                           "decision_date")
    if decision > end:
        raise PlanRejected("DECISION_FUERA_DE_RANGO", "La fecha de decisión debe ser anterior al fin del mes objetivo.",
                           "decision_date")
    leads = raw.get("lead_days")
    if not isinstance(leads, (list, tuple)) or not 1 <= len(leads) <= MAX_LEADS:
        raise PlanRejected("PLAZOS_INVALIDOS", f"Indique de 1 a {MAX_LEADS} plazos de entrega.", "lead_days")
    lead_vals = [_int(x, "lead_days", "PLAZOS_INVALIDOS", LEAD_MIN, LEAD_MAX, "Cada plazo") for x in leads]
    if len(set(lead_vals)) != len(lead_vals):
        raise PlanRejected("PLAZOS_INVALIDOS", "Los plazos no deben repetirse.", "lead_days")
    reserve = _int(raw.get("reserve_days"), "reserve_days", "RESERVA_INVALIDA", 0, RESERVE_MAX, "La reserva")
    min_order = _int(raw.get("min_order"), "min_order", "MINIMO_INVALIDO", 1, MAX_UNITS, "El mínimo de compra")
    multiple = _int(raw.get("order_multiple"), "order_multiple", "MULTIPLO_INVALIDO", 1, MAX_MULTIPLE,
                    "El múltiplo de compra")
    pend_raw = raw.get("pending_orders", [])
    if not isinstance(pend_raw, (list, tuple)) or len(pend_raw) > MAX_PENDING:
        raise PlanRejected("PENDIENTE_INVALIDO", f"Se admiten hasta {MAX_PENDING} pedidos por recibir.", "pending_orders")
    groups, pend = set(group_ids), []
    for i, p in enumerate(pend_raw):
        f = f"pending_orders[{i}]"
        if not isinstance(p, Mapping) or set(p) - {"producto_id", "units", "arrival_date", "nature"}:
            raise PlanRejected("PENDIENTE_INVALIDO", "Pedido por recibir con campos no permitidos.", f)
        if p.get("arrival_date") in (None, ""):
            raise PlanRejected("PENDIENTE_SIN_FECHA", "Una cantidad por recibir exige su fecha de llegada.", f)
        pid = p.get("producto_id")
        if not isinstance(pid, str) or not _CODE_RE.match(pid) or pid not in groups:
            raise PlanRejected("PENDIENTE_INVALIDO", "El producto del pedido por recibir no pertenece al grupo.", f)
        units = _int(p.get("units"), f, "PENDIENTE_INVALIDO", 1, MAX_UNITS, "Las unidades del pedido por recibir")
        arrival = _date(p.get("arrival_date"), f, "PENDIENTE_INVALIDO")
        if arrival <= count_date or arrival > end:
            raise PlanRejected("PENDIENTE_INVALIDO",
                               "La llegada del pedido por recibir debe ser posterior al conteo y no pasar del fin del mes.", f)
        nature = p.get("nature")
        if nature not in NATURES:
            raise PlanRejected("PENDIENTE_INVALIDO", "La naturaleza debe ser REPORTADA o ASUMIDA.", f)
        pend.append(PendingOrder(pid, units, arrival, nature))
    pend.sort(key=lambda o: (o.producto_id, o.arrival_date, o.units, o.nature))
    return PlanParams(raw["month"], decision, tuple(sorted(lead_vals)), reserve, min_order, multiple, tuple(pend))


def identity(params: PlanParams, *, dataset_id: str, sales_cutoff: str, snapshot_id: str, snapshot_sha256: str,
             snapshot_csv_sha256: str) -> dict:
    """TODAS las entradas que determinan el resultado (contrato §5)."""
    return {"dataset_id": dataset_id, "sales_cutoff": sales_cutoff, "snapshot_id": snapshot_id,
            "snapshot_sha256": snapshot_sha256, "snapshot_csv_sha256": snapshot_csv_sha256, "params": params.to_dict(),
            "method": METHOD, "engine_version": ENGINE_VERSION, "contract_version": CONTRACT_VERSION}


def plan_id_for(params: PlanParams, ident: dict) -> str:
    blob = json.dumps(ident, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return f"plan-{params.month}-d{params.decision_date:%Y%m%d}-{hashlib.sha256(blob.encode()).hexdigest()[:12]}"


# ------------------------------------------------------------------ prevision
@dataclass(frozen=True)
class Forecast:
    window_start: date
    window_end: date
    sum_28: Fraction
    days_valid: int
    masked_days: tuple[date, ...]
    m: Fraction


def forecast_promedio_28(by_day: Mapping[date, Fraction], cutoff: date) -> Forecast:
    """m = sum_28 / days_valid; ventana [corte-27, corte]; los dias enmascarados no suman ni cuentan en days_valid.
    Solo lee dias dentro de la ventana: lo posterior al corte o anterior a la ventana no puede alterar `m`."""
    ws = cutoff - timedelta(days=WINDOW_DAYS - 1)
    masked = tuple(sorted(d for d in MASK_DAYS if ws <= d <= cutoff))
    total = Fraction(0)
    for d, q in by_day.items():
        if ws <= d <= cutoff and d not in MASK_DAYS:
            total += Fraction(q)
    valid = WINDOW_DAYS - len(masked)
    return Forecast(ws, cutoff, total, valid, masked, total / valid)


# ------------------------------------------------------------------ balance diario
class Row(NamedTuple):
    day: date
    inicio: Fraction
    recepciones: Fraction
    disponible: Fraction
    demanda: Fraction
    atendida: Fraction
    faltante: Fraction
    fin: Fraction


def run_days(start_stock: Fraction, first: date, last: date, m: Fraction, receipts: Mapping[date, Fraction]) -> list[Row]:
    """Balance diario exacto de `first` a `last`: recepciones -> demanda; el faltante no se arrastra."""
    rows, fin, d = [], Fraction(start_stock), first
    while d <= last:
        rec = Fraction(receipts.get(d, 0))
        disp = fin + rec
        att = min(disp, m)
        rows.append(Row(d, fin, rec, disp, m, att, m - att, disp - att))
        fin, d = disp - att, d + timedelta(days=1)
    return rows


def _sum(rows, attr: str, pred=lambda r: True) -> Fraction:
    return sum((getattr(r, attr) for r in rows if pred(r)), Fraction(0))


def calc_scenario(*, m: Fraction, libre: int, count_date: date, decision_date: date, lead: int, reserve_days: int,
                  min_order: int, order_multiple: int, month_start: date, month_end: date,
                  pending: Mapping[date, Fraction] | None = None) -> dict:
    """Escenario de un plazo (contrato §4). Devuelve Fractions y filas; `serialize_scenario` lo convierte a JSON."""
    pending = {d: Fraction(q) for d, q in (pending or {}).items()}
    A = decision_date + timedelta(days=lead)
    day0, E, R = count_date + timedelta(days=1), month_end, reserve_days * m
    out: dict = {"lead_days": lead, "decision_date": decision_date, "arrival_date": A, "m": m, "libre": libre,
                 "reserve_days": reserve_days, "reserve_qty": R, "count_date": count_date, "month_start": month_start,
                 "month_end": month_end, "min_order": min_order, "order_multiple": order_multiple,
                 "pending": pending, "required_arrival_date": None, "stock_at_arrival": None, "qty": None,
                 "qty_unrounded": None, "binding": None, "binding_date": None, "prefix_need": None, "final_need": None,
                 "bridge_days": 0, "month_days_after_arrival": 0}
    if A > E:
        rows = run_days(Fraction(libre), day0, E, m, pending)
        out.update(status="NO_LLEGA_A_TIEMPO", rows=rows,
                   required_arrival_date=month_start - timedelta(days=lead))
    else:
        pre = run_days(Fraction(libre), day0, A - timedelta(days=1), m, pending)
        fin_pre = pre[-1].fin if pre else Fraction(libre)
        S = fin_pre + pending.get(A, Fraction(0))
        n_days = _days(A, E)
        after = {d: q for d, q in pending.items() if A < d <= E}
        rec_total = sum(after.values(), Fraction(0))
        best, best_day, cum_rec, t, i = None, None, Fraction(0), A, 0
        while t <= E:
            i += 1
            cum_rec += after.get(t, Fraction(0))
            term = m * i - S - cum_rec
            if best is None or term > best:
                best, best_day = term, t
            t += timedelta(days=1)
        final_need = m * n_days + R - S - rec_total
        q_min = max(best, final_need, Fraction(0))
        if q_min <= 0:
            qty, binding = 0, "none"
        else:
            binding = "final" if final_need >= best else "prefix"
            qty = _ceil(q_min / order_multiple) * order_multiple
            if qty < min_order:
                qty = _ceil(Fraction(min_order, order_multiple)) * order_multiple
        receipts = dict(pending)
        receipts[A] = receipts.get(A, Fraction(0)) + qty
        rows = pre + run_days(fin_pre, A, E, m, receipts)
        post = [r for r in rows if r.day >= A]
        if any(r.faltante != 0 for r in post) or rows[-1].fin < R:
            raise RuntimeError("INVARIANTE_COMPRA: la cantidad no cubre el periodo")      # no debe ocurrir
        bridge_end = min(E, month_start - timedelta(days=1))
        out.update(status="OK", rows=rows, stock_at_arrival=S, qty=qty, qty_unrounded=q_min, binding=binding,
                   binding_date=best_day if binding == "prefix" else None, prefix_need=best, final_need=final_need,
                   bridge_days=_days(A, bridge_end), month_days_after_arrival=_days(max(A, month_start), E),
                   pending_after_arrival=rec_total)
    rows = out["rows"]
    row_ms = next(r for r in rows if r.day == month_start)
    in_month = lambda r: r.day >= month_start
    before = lambda r: r.day < month_start
    pre_arr = lambda r: r.day < A
    out.update(
        stock_month_start=row_ms.disponible,
        shortage_before_month=_sum(rows, "faltante", before), shortage_month=_sum(rows, "faltante", in_month),
        served_month=_sum(rows, "atendida", in_month),
        demand_before_arrival_in_month=m * _days(month_start, min(A - timedelta(days=1), E)),
        end_stock=rows[-1].fin, consumed_before_arrival=_sum(rows, "atendida", pre_arr),
        shortage_before_arrival=_sum(rows, "faltante", pre_arr))
    if out["status"] == "OK" and out["shortage_month"] > 0:
        out["status"] = "LLEGA_TARDE"
    return out


def _step(key: str, label: str, text: str, value: Fraction | int | None) -> dict:
    v = None if value is None else Fraction(value)
    return {"key": key, "label": label, "text": text, "value": None if v is None else dec(v),
            "exact": None if v is None else exact(v)}


def _explain(c: dict) -> tuple[dict, list[dict]]:
    """Desglose de «Entender la compra» y pasos que reproducen la cantidad."""
    m, A, E = c["m"], c["arrival_date"], c["month_end"]
    ms, cd = c["month_start"], c["count_date"]
    pre_rows = [r for r in c["rows"] if r.day < A]
    rec_to_A = sum((q for d, q in c["pending"].items() if d <= A), Fraction(0))
    r_days = c["reserve_days"]
    if c["status"] == "NO_LLEGA_A_TIEMPO":
        steps = [
            _step("stock_count", "Stock del conteo", f"Stock libre reportado el {_dmy(cd)}.", c["libre"]),
            _step("arrival", "Llegada de la orden", f"Con decisión el {_dmy(c['decision_date'])} y {c['lead_days']} días, "
                  f"llegaría el {_dmy(A)}, después del {_dmy(E)}: no sirve para este mes.", None),
            _step("required_date", "Fecha requerida", f"Para llegar el {_dmy(ms)} habría que decidir el "
                  f"{_dmy(c['required_arrival_date'])}.", None)]
        return ({"stock_count": exact(Fraction(c["libre"])), "arrival_date": A.isoformat(),
                 "required_arrival_date": c["required_arrival_date"].isoformat(), "purchase_qty": None}, steps)
    N = _days(A, E)
    bridge, month_dem = m * c["bridge_days"], m * c["month_days_after_arrival"]
    reserve = c["reserve_qty"]
    need = bridge + month_dem + reserve
    S, pend_after = c["stock_at_arrival"], c["pending_after_arrival"]
    bd = {"stock_count": exact(Fraction(c["libre"])), "consumed_before_arrival": exact(c["consumed_before_arrival"]),
          "shortage_before_arrival": exact(c["shortage_before_arrival"]), "other_receipts_until_arrival": exact(rec_to_A),
          "stock_at_arrival": exact(S), "bridge_days": c["bridge_days"], "bridge_demand": exact(bridge),
          "month_days_after_arrival": c["month_days_after_arrival"], "month_demand": exact(month_dem),
          "reserve_days": r_days, "reserve": exact(reserve), "total_need": exact(need),
          "pending_after_arrival": exact(pend_after), "final_need": exact(c["final_need"]),
          "prefix_need": exact(c["prefix_need"]), "binding": c["binding"],
          "binding_date": c["binding_date"].isoformat() if c["binding_date"] else None,
          "qty_unrounded": exact(c["qty_unrounded"]), "min_order": c["min_order"],
          "order_multiple": c["order_multiple"], "purchase_qty": c["qty"]}
    first_pre = cd + timedelta(days=1)
    steps = [
        _step("stock_count", "Stock del conteo", f"Stock libre reportado el {_dmy(cd)} a las 17:00.", c["libre"]),
        _step("consumed_before_arrival", "Ventas atendidas antes de llegar",
              f"Del {_dmy(first_pre)} al {_dmy(A - timedelta(days=1))} se atiende la demanda prevista mientras haya stock."
              if pre_rows else "La orden llega el primer día simulado: no hay consumo previo.", c["consumed_before_arrival"]),
        _step("shortage_before_arrival", "Ventas no atendidas antes de llegar",
              "Venta perdida antes de la llegada; no se repone ni se arrastra como pedido atrasado.",
              c["shortage_before_arrival"]),
        _step("other_receipts_until_arrival", "Otras recepciones hasta el día de llegada",
              "Pedidos por recibir con fecha hasta el día de llegada (ya incluidos en el stock siguiente).", rec_to_A),
        _step("stock_at_arrival", "Stock al inicio del día de llegada (S)",
              f"Stock del {_dmy(A)} tras las otras recepciones del día y antes de la orden nueva.", S),
        _step("bridge_demand", "Demanda del puente anterior al mes",
              f"{c['bridge_days']} día(s) desde la llegada ({_dmy(A)}) hasta el fin del mes anterior.", bridge),
        _step("month_demand", "Demanda del mes",
              f"{c['month_days_after_arrival']} día(s) del mes desde {_dmy(max(A, ms))} hasta {_dmy(E)}.", month_dem),
        _step("reserve", "Reserva al cierre", f"{r_days} día(s) de ventas previstas (supuesto, no garantía de servicio).",
              reserve),
        _step("total_need", "Necesidad total", f"Demanda de {N} día(s) desde la llegada hasta {_dmy(E)} más la reserva.", need),
        _step("less_stock", "Menos el stock S", "Se descuenta lo que ya hay al llegar la orden.", -S),
        _step("less_pending", "Menos recepciones posteriores", "Pedidos por recibir con fecha después de la llegada.",
              -pend_after),
        _step("final_need", "Cantidad necesaria sin redondear", "Necesidad total menos S menos recepciones posteriores.",
              c["final_need"])]
    if c["binding"] == "prefix":
        steps.append(_step("prefix_need", "Exigencia por día (prefijo)",
                           f"Para no tener faltante hasta el {_dmy(c['binding_date'])} se necesita más que al cierre del mes.",
                           c["prefix_need"]))
    steps.append(_step("qty_unrounded", "Cantidad mínima exigida", "El mayor entre lo necesario al cierre, lo exigido "
                       "por cada día y cero.", c["qty_unrounded"]))
    steps.append(_step("purchase_qty", "Compra propuesta",
                       f"Menor entero que cumple múltiplo de {c['order_multiple']} y mínimo de {c['min_order']}.", c["qty"]))
    return bd, steps


def _events(c: dict) -> list[dict]:
    ev = [(c["count_date"], 0, "CONTEO", Fraction(c["libre"]), "Stock libre reportado (17:00)")]
    for d, q in sorted(c["pending"].items()):
        ev.append((d, 2, "RECEPCION_PENDIENTE", q, "Pedido por recibir (recepción al inicio del día)"))
    if c["qty"] is not None:
        ev.append((c["decision_date"], 1, "DECISION_ORDEN", Fraction(c["qty"]), "Orden única propuesta"))
        ev.append((c["arrival_date"], 3, "LLEGADA_ORDEN", Fraction(c["qty"]), "Recepción de la orden (inicio del día)"))
    first = next((r for r in c["rows"] if r.faltante > 0), None)
    if first:
        ev.append((first.day, 4, "PRIMER_DIA_CON_FALTANTE", first.faltante, "Primer día con venta no atendida"))
    ev.sort(key=lambda e: (e[0], e[1]))
    return [{"date": d.isoformat(), "type": t, "units": exact(u), "note": n} for d, _r, t, u, n in ev]


def serialize_scenario(c: dict) -> dict:
    bd, steps = _explain(c)
    ex = exact
    return {
        "lead_days": c["lead_days"], "decision_date": c["decision_date"].isoformat(),
        "arrival_date": c["arrival_date"].isoformat(), "status": c["status"], "reason": None,
        "purchase_qty": c["qty"],
        "required_arrival_date": c["required_arrival_date"].isoformat() if c["required_arrival_date"] else None,
        "stock_at_arrival": None if c["stock_at_arrival"] is None else ex(c["stock_at_arrival"]),
        "stock_month_start": ex(c["stock_month_start"]), "shortage_before_month": ex(c["shortage_before_month"]),
        "shortage_month": ex(c["shortage_month"]), "served_month": ex(c["served_month"]),
        "demand_before_arrival_in_month": ex(c["demand_before_arrival_in_month"]), "end_stock": ex(c["end_stock"]),
        "consumed_before_arrival": ex(c["consumed_before_arrival"]),
        "shortage_before_arrival": ex(c["shortage_before_arrival"]), "reserve_qty": ex(c["reserve_qty"]),
        "qty_unrounded": None if c["qty_unrounded"] is None else ex(c["qty_unrounded"]),
        "breakdown": bd, "explanation": steps, "events": _events(c),
        "event_order": "recepciones(t) -> demanda(t)",
        "series": [{"fecha": r.day.isoformat(), "inicio": ex(r.inicio), "recepciones": ex(r.recepciones),
                    "disponible": ex(r.disponible), "demanda": ex(r.demanda), "atendida": ex(r.atendida),
                    "faltante": ex(r.faltante), "fin": ex(r.fin)} for r in c["rows"]]}


def _not_calculable(reason: str, lead: int, decision: date) -> dict:
    return {"lead_days": lead, "decision_date": decision.isoformat(),
            "arrival_date": (decision + timedelta(days=lead)).isoformat(), "status": "NO_CALCULABLE", "reason": reason,
            "reason_text": REASON_TEXT[reason], "purchase_qty": None, "required_arrival_date": None,
            "stock_at_arrival": None, "stock_month_start": None, "shortage_before_month": None, "shortage_month": None,
            "served_month": None, "demand_before_arrival_in_month": None, "end_stock": None,
            "consumed_before_arrival": None, "shortage_before_arrival": None, "reserve_qty": None,
            "qty_unrounded": None, "breakdown": None, "explanation": [
                {"key": "no_calculable", "label": "No calculable", "text": REASON_TEXT[reason], "value": None,
                 "exact": None}], "events": [], "event_order": "recepciones(t) -> demanda(t)", "series": []}


def worst_status(statuses) -> str:
    return max(statuses, key=lambda s: _WORST[s])


def compute_product(*, params: PlanParams, count_date: date, sales_cutoff: date, libre: int | None,
                    unidad_reporte: str | None, by_day: Mapping[date, Fraction], window_units: frozenset,
                    history_units: frozenset, history_rows: int, pending: Mapping[date, Fraction] | None) -> dict:
    """Resultado de un producto: `forecast`, `scenarios` por plazo, `status` (el peor), `statuses`, `reason`.
    NO_CALCULABLE (nunca 0) si falta conteo, la unidad no es UND o no hay señal de ventas."""
    month_start, month_end = month_bounds(params.month)
    reason = None
    if (history_units and "UND" not in history_units) or (window_units - {"UND"}):
        reason = "UNIDAD_INCOMPATIBLE"
    elif history_rows <= 0:
        reason = "SIN_SENAL"
    elif libre is None:
        reason = "SIN_CONTEO"
    elif unidad_reporte != "UND":
        reason = "UNIDAD_INCOMPATIBLE"
    month_days = _days(month_start, month_end)
    forecast, fc = None, None
    if reason not in ("UNIDAD_INCOMPATIBLE", "SIN_SENAL"):
        fc = forecast_promedio_28(by_day, sales_cutoff)
        forecast = {
            "daily": dec(fc.m), "daily_exact": exact(fc.m), "month_total": dec(fc.m * month_days),
            "month_total_exact": exact(fc.m * month_days), "month_days": month_days,
            "window_start": fc.window_start.isoformat(), "window_end": fc.window_end.isoformat(),
            "sum_28": exact(fc.sum_28), "days_valid": fc.days_valid,
            "masked_days": [d.isoformat() for d in fc.masked_days],
            "zero_reason": ("SIN_VENTAS_EN_VENTANA" if fc.sum_28 == 0 else None),
            "note": ("Cobertura completa de la ventana sin ventas del producto: previsión 0 explicada; "
                     "el octubre desconocido no se rellena con ceros." if fc.sum_28 == 0 else None)}
    scenarios = {}
    for lead in params.lead_days:
        if reason is not None:
            scenarios[str(lead)] = _not_calculable(reason, lead, params.decision_date)
        else:
            calc = calc_scenario(m=fc.m, libre=libre, count_date=count_date, decision_date=params.decision_date,
                                 lead=lead, reserve_days=params.reserve_days, min_order=params.min_order,
                                 order_multiple=params.order_multiple, month_start=month_start, month_end=month_end,
                                 pending=pending)
            scenarios[str(lead)] = serialize_scenario(calc)
    statuses = [s["status"] for s in scenarios.values()]
    return {"forecast": forecast, "scenarios": scenarios, "status": worst_status(statuses),
            "statuses": sorted(set(statuses), key=lambda s: _WORST[s]), "reason": reason}
