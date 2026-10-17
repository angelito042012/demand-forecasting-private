import { Pipe, PipeTransform } from '@angular/core';

/**
 * Formato de números para pantalla (es-PE). Solo presentación: los cálculos usan siempre el valor exacto.
 * - unidades de stock/pedido: enteros
 * - medias y pronósticos: hasta 3 decimales
 * - PEN: 2 decimales
 * - porcentajes: 1 decimal
 */
const LOCALE = 'es-PE';
export const DASH = '—';

const cache = new Map<string, Intl.NumberFormat>();
function nf(min: number, max: number, signed: boolean): Intl.NumberFormat {
  const key = `${min}|${max}|${signed}`;
  let f = cache.get(key);
  if (!f) {
    f = new Intl.NumberFormat(LOCALE, {
      minimumFractionDigits: min, maximumFractionDigits: max, ...(signed ? { signDisplay: 'exceptZero' as const } : {}),
    });
    cache.set(key, f);
  }
  return f;
}

export function isNum(v: unknown): v is number {
  return typeof v === 'number' && Number.isFinite(v);
}

function fmt(v: unknown, min: number, max: number, signed: boolean): string {
  if (!isNum(v)) return DASH;
  const rounded = Number(v.toFixed(max));
  // evita «-0», «-0.00» y «+0»: un valor que redondea a cero se muestra sin signo
  const x = rounded === 0 ? 0 : v;
  return nf(min, max, signed).format(x);
}

/** Unidades de stock, tránsito, pedido: enteros. */
export function fmtInt(v: unknown, signed = false): string { return fmt(v, 0, 0, signed); }
/** Medias y pronósticos: hasta 3 decimales, sin ceros sobrantes. */
export function fmtDec(v: unknown, maxDecimals = 3, signed = false): string { return fmt(v, 0, maxDecimals, signed); }
/** Importes: 2 decimales y moneda. */
export function fmtPen(v: unknown, signed = false): string {
  const s = fmt(v, 2, 2, signed);
  return s === DASH ? s : `${s} PEN`;
}
/** Fracción (0,1 = 10 %) a porcentaje con 1 decimal. */
export function fmtPct(v: unknown, signed = false): string {
  if (!isNum(v)) return DASH;
  const s = fmt(v * 100, 1, 1, signed);
  return `${s} %`;
}
/** Diferencia de una fracción en puntos porcentuales (ej. servicio -0.0399 = -4.0 pp). */
export function fmtPp(v: unknown): string {
  if (!isNum(v)) return DASH;
  return `${fmt(v * 100, 1, 1, true)} pp`;
}

export type FmtKind = 'int' | 'dec' | 'pen' | 'pct' | 'pp';

@Pipe({ name: 'fmt' })
export class FmtPipe implements PipeTransform {
  transform(v: unknown, kind: FmtKind = 'int', signed = false): string {
    switch (kind) {
      case 'int': return fmtInt(v, signed);
      case 'dec': return fmtDec(v, 3, signed);
      case 'pen': return fmtPen(v, signed);
      case 'pct': return fmtPct(v, signed);
      case 'pp': return fmtPp(v);
    }
  }
}

/** Fecha AAAA-MM-DD a DD/MM/AAAA para texto en español. */
export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return DASH;
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  return m ? `${m[3]}/${m[2]}/${m[1]}` : iso;
}
