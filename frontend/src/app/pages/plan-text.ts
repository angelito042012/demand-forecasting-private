// T19: textos de presentación de «Planificar compras». SOLO formato: los valores los entrega la API (cantidades en texto decimal).
import { fmtDec } from '../core/format';
import { PlanScenario, PlanStatus } from '../core/models';
import { monthName } from '../core/ux-text';

export const NOT_COMPUTABLE = 'No se puede calcular';
export const NOT_REPORTED = 'No informado';

export function isDecimalText(v: unknown): v is string {
  return typeof v === 'string' && /^-?\d+(\.\d+)?$/.test(v.trim());
}

/** Cantidad en texto decimal → formato es-PE (hasta 3 decimales). null/ausente ⇒ `fallback` (nunca 0). */
export function qtyText(v: string | number | null | undefined, fallback = NOT_COMPUTABLE): string {
  if (v === null || v === undefined || v === '') return fallback;
  if (typeof v === 'number') return fmtDec(v, 3);
  return isDecimalText(v) ? fmtDec(Number(v), 3) : v;
}

/** Valor de un paso del desglose: números con formato, fracciones («p/q») o textos tal cual. */
export function stepValue(v: string | null | undefined): string {
  return v === null || v === undefined || v === '' ? '' : (isDecimalText(v) ? fmtDec(Number(v), 3) : v);
}

export function isZero(v: string | number | null | undefined): boolean {
  if (typeof v === 'number') return v === 0;
  return isDecimalText(v) && Number(v) === 0;
}

/** Compra propuesta: un 0 calculado se explica; null NUNCA se muestra como 0. */
export function purchaseText(sc: Pick<PlanScenario, 'purchase_qty'>): string | null {
  const v = sc.purchase_qty;
  if (v === null || v === undefined) return null;
  return isZero(v) ? '0 (no hace falta comprar)' : qtyText(v);
}

export function monthWord(month: string | null | undefined): string {
  return month ? (monthName(`${month}-01`) || 'el mes') : 'el mes';
}

/** Estado en palabras sencillas. */
export function statusText(sc: Pick<PlanScenario, 'status' | 'shortage_month'>, month: string | null | undefined): string {
  switch (sc.status as PlanStatus) {
    case 'OK': return `Cubre ${monthWord(month)}`;
    case 'LLEGA_TARDE':
      return sc.shortage_month === null || sc.shortage_month === undefined
        ? 'Llega tarde'
        : `Llega tarde: faltarían ${qtyText(sc.shortage_month)} unidades`;
    case 'NO_LLEGA_A_TIEMPO': return 'No llega a tiempo';
    default: return NOT_COMPUTABLE;
  }
}

export function statusTone(s: PlanStatus | string): 'ok' | 'warn' | 'bad' | '' {
  return s === 'OK' ? 'ok' : s === 'LLEGA_TARDE' ? 'warn' : s === 'NO_LLEGA_A_TIEMPO' ? 'bad' : '';
}

export const STATUS_FILTERS: { value: string; label: string }[] = [
  { value: '', label: 'Todos' },
  { value: 'OK', label: 'Cubre el mes' },
  { value: 'LLEGA_TARDE', label: 'Llega tarde' },
  { value: 'NO_LLEGA_A_TIEMPO', label: 'No llega a tiempo' },
  { value: 'NO_CALCULABLE', label: 'No se puede calcular' },
];

export const NATURE_LABELS: Record<string, string> = { REPORTADA: 'Reportada', ASUMIDA: 'Asumida' };
