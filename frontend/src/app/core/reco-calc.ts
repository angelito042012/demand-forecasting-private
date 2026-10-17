import { Recommendation } from './models';
import { fmtDate, fmtDec, fmtInt, fmtPen } from './format';

export interface CalcStep { n: number; label: string; text: string; value: number; unit: string }
export interface CalcResult {
  steps: CalcStep[];
  check: { target: boolean; position: boolean; order: boolean };
  /** 'exact': presentación derivada de sum_28/days_28 (enteros); 'published': valores publicados (corridas antiguas). */
  mode: 'exact' | 'published';
}

function gcd(a: number, b: number): number { return b === 0 ? Math.abs(a) : gcd(b, a % b); }

/** Fracción reducida «3/7» (o «2» si el denominador es 1) a partir de enteros. */
export function fraction(sum: number, days: number): string {
  if (sum === 0) return '0';
  const g = gcd(sum, days);
  const n = sum / g, d = days / g;
  return d === 1 ? String(n) : `${n}/${d}`;
}

/**
 * Pasos del cálculo según T08 §5. La presentación nunca alimenta el resultado:
 * - con `sum_28` y `days_28` enteros, pronóstico, seguridad y objetivo se derivan en aritmética entera exacta
 *   (objetivo = techo((H + S) × suma / días), sin épsilon ni cifras truncadas);
 * - sin ellos (corrida antigua) se muestran los valores publicados y `check` los contrasta con la regla.
 * Devuelve null si no hay inventario simulado (sin_snapshot): nunca se supone stock cero.
 */
export function calcSteps(r: Recommendation): CalcResult | null {
  if (r.status !== 'ok') return null;
  const nums = [r.on_hand, r.in_transit, r.position, r.forecast_14d, r.safety, r.target, r.order_qty, r.mean_28];
  if (nums.some((n) => n === null || n === undefined)) return null;
  const u = 'unidad base';
  const H = r.horizon_days, S = r.safety_days;
  const exact = Number.isInteger(r.sum_28) && Number.isInteger(r.days_28) && (r.days_28 as number) > 0;

  let forecast = r.forecast_14d!, safety = r.safety!, target = r.target!, mean = r.mean_28!;
  let meanText: string;
  if (exact) {
    const sum = r.sum_28 as number, days = r.days_28 as number;
    mean = sum / days;
    forecast = (H * sum) / days;
    safety = (S * sum) / days;
    target = Math.floor(((H + S) * sum + days - 1) / days); // techo en aritmética entera
    const frac = r.mean_28_exact || fraction(sum, days);
    meanText = `${fmtInt(sum)} unidades en ${days} días útiles = ${frac} por día`;
  } else {
    meanText = `${fmtDec(r.mean_28)} unidades por día (promedio de 28 días)`;
  }
  const order = Math.max(0, target - r.position!);

  const b = r.transit_breakdown;
  const transit = b && Number.isFinite(Number(b.ordered_until_snapshot)) && Number.isFinite(Number(b.received_until_snapshot))
    ? ` (${fmtInt(b.ordered_until_snapshot)} pedidas − ${fmtInt(b.received_until_snapshot)} recibidas)` : '';
  const raw: [string, string, number][] = [
    [`Stock simulado al cierre del ${fmtDate(r.snapshot_date)}`, `${fmtInt(r.on_hand)} unidades`, r.on_hand!],
    ['En tránsito (pedidos emitidos menos recibidos a esa fecha)', `${fmtInt(r.in_transit)} unidades${transit}`, r.in_transit!],
    ['Posición de inventario (stock + tránsito)', `${fmtInt(r.on_hand)} + ${fmtInt(r.in_transit)} = ${fmtInt(r.position)} unidades`, r.position!],
    ['Demanda media diaria', meanText, mean],
    [`Pronóstico de ${H} días (${fmtDate(r.forecast_from)} a ${fmtDate(r.forecast_to)}, ${r.model})`, `${H} × ${fmtDec(mean)} = ${fmtDec(forecast)} unidades`, forecast],
    [`Stock de seguridad (${S} días de demanda media)`, `${S} × ${fmtDec(mean)} = ${fmtDec(safety)} unidades`, safety],
    ['Objetivo (pronóstico + seguridad, redondeado hacia arriba)', `redondeo hacia arriba de (${fmtDec(forecast)} + ${fmtDec(safety)}) = ${fmtInt(target)} unidades`, target],
    ['Pedido sugerido', `máx(0, ${fmtInt(target)} − ${fmtInt(r.position)}) = ${fmtInt(order)} unidades`, order],
  ];
  if (r.unit_cost_assumed !== null && r.unit_cost_assumed !== undefined) {
    const value = r.order_value_assumed ?? r.order_qty! * r.unit_cost_assumed;
    raw.push([
      'Valor supuesto del pedido',
      `${fmtInt(r.order_qty)} × ${fmtPen(r.unit_cost_assumed)} = ${fmtPen(value)} (costo unitario supuesto: 65 % de la mediana de precio base hasta el 31/05)`,
      value,
    ]);
  }
  const steps: CalcStep[] = raw.map(([label, text, value], i) => ({ n: i + 1, label, text, value, unit: u }));

  const check = {
    position: r.on_hand! + r.in_transit! === r.position!,
    target: exact ? target === r.target! : Math.ceil(Math.round((r.forecast_14d! + r.safety!) * 1e9) / 1e9) === r.target!,
    order: Math.max(0, r.target! - r.position!) === r.order_qty!,
  };
  return { steps, check, mode: exact ? 'exact' : 'published' };
}
