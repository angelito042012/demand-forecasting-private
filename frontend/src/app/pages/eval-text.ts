// UX01: textos de lectura de la evaluación. SOLO presentación: cada cifra sale de los números que publica la API
// (o del cociente de dos cifras publicadas, como ya hace core/final-eval.ts); nunca se sustituye por una métrica más favorable.
import { SimBlock } from '../core/models';
import { fmtPct, fmtPp, isNum } from '../core/format';

export const NOT_EVALUABLE = 'no evaluable';

/** Error absoluto como porcentaje del volumen observado; indefinido (null/undefined) = «no evaluable», nunca 0. */
export function errorText(wape: number | null | undefined): string {
  return isNum(wape) ? fmtPct(wape) : NOT_EVALUABLE;
}

/** sesgo acumulado / unidades observadas (cociente de dos cifras publicadas); null si no se puede calcular. */
export function biasRatio(sesgo: unknown, observadas: unknown): number | null {
  return isNum(sesgo) && isNum(observadas) && observadas !== 0 ? sesgo / observadas : null;
}
export function biasText(sesgo: unknown, observadas: unknown): string {
  const r = biasRatio(sesgo, observadas);
  return r === null ? NOT_EVALUABLE : fmtPct(r, true);
}

/** Lectura en lenguaje llano del error absoluto acumulado (WAPE). */
export function readingSentence(wape: number | null | undefined): string {
  if (!isNum(wape)) return 'El error absoluto acumulado no es evaluable en este alcance (no hay ventas observadas para calcularlo); no se reemplaza por cero.';
  const x = fmtPct(wape);
  return `El error absoluto acumulado equivale aproximadamente al ${x} del volumen observado. No significa un ${x} de acierto.`;
}

/** Compara dos errores sin convertirlo en una insignia: dice quién tuvo menor error y por cuántos puntos porcentuales. */
export function compareSentence(base: number | null | undefined, exp: number | null | undefined): string {
  if (!isNum(base) || !isNum(exp)) return 'No se puede comparar el error de los dos métodos porque al menos uno no es evaluable.';
  const d = exp - base;
  if (Math.abs(d) < 0.0005) return 'El modelo experimental y el promedio de 28 días tuvieron prácticamente el mismo error.';
  return `El modelo experimental tuvo un error ${d > 0 ? 'mayor' : 'menor'} que el promedio de 28 días (${fmtPp(d)}).`;
}

function relWord(rel: unknown): string {
  if (!isNum(rel)) return 'sin dato comparable';
  if (Math.abs(rel) < 0.0005) return 'igual';
  return `${fmtPct(Math.abs(rel))} ${rel > 0 ? 'mayor' : 'menor'}`;
}

type DiffMetrics = Record<string, { abs: number | null; rel: number | null }> | null | undefined;

/**
 * Conclusión corta de la reposición simulada: modelo experimental frente al promedio de 28 días en el escenario elegido.
 * Servicio, stock y compras se leen juntos; el servicio mayor no se presenta como mejora si trae más stock o compras.
 */
export function simConclusion(base: SimBlock | null, exp: SimBlock | null, diff: DiffMetrics): string[] {
  if (!base || !exp) return [];
  const fb = base['fill_rate']; const fe = exp['fill_rate'];
  const dFill = diff?.['fill_rate']?.abs ?? (isNum(fb) && isNum(fe) ? fe - fb : null);
  const stockRel = diff?.['stock_medio_unidades_por_dia']?.rel;
  const comprasRel = diff?.['compras_desembolsadas_supuesto']?.rel;
  const lines: string[] = [];
  lines.push(`Servicio simulado (unidades atendidas sobre la demanda): ${fmtPct(fb)} con el promedio de 28 días y ${fmtPct(fe)} con el modelo experimental${isNum(dFill) ? ` (${fmtPp(dFill)})` : ''}.`);
  lines.push(`En el mismo escenario, el stock medio del modelo experimental fue ${relWord(stockRel)} y las compras desembolsadas (supuestas), ${relWord(comprasRel)}, frente al promedio de 28 días.`);
  const more = (isNum(stockRel) && stockRel > 0) || (isNum(comprasRel) && comprasRel > 0);
  lines.push(isNum(dFill) && dFill > 0 && more
    ? 'Más servicio vino acompañado de más stock o más compras: no se presenta como una mejora neta ni como ahorro.'
    : 'Más servicio puede ir con más stock y más compras: léelos siempre juntos.');
  lines.push('Es una simulación con inventario, costos y plazos supuestos; no se atribuye un impacto real.');
  return lines;
}
