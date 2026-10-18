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

// ---- UX01R: vista inicial comprensible (solo presentación; ninguna cifra se calcula aquí) ----

/** Umbral de lectura (presentación): desde este error absoluto se añade «Es un error alto por …». No es un criterio de calidad del modelo. */
export const HIGH_ERROR = 0.5;

/** Ventana del promedio de 28 días: calendario, días válidos con ceros incluidos, días excluidos fuera. No afirma 28 días de historia. */
export const WINDOW_NOTE = 'El promedio de 28 días se calcula sobre una ventana de 28 días de calendario antes de la fecha de corte: se usan los días válidos, incluidos los de venta cero; los días excluidos no cuentan. No toda serie tiene 28 días de historia.';

/** Aviso de un análisis generado que no se evalúa contra ventas registradas, por diseño (no afirma que no existan ventas posteriores). */
export const GENERATED_NO_EVAL = 'Este análisis se creó en la aplicación y no incluye una evaluación contra ventas registradas, por diseño. Para ver una comparación con ventas registradas abre el ejemplo de julio o la evaluación de agosto.';

/** Suma días a una fecha AAAA-MM-DD (UTC). */
export function addDays(iso: string, n: number): string {
  const [y, m, d] = iso.split('-').map(Number);
  return new Date(Date.UTC(y, m - 1, d + n)).toISOString().slice(0, 10);
}

const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
const parts = (iso: string) => { const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso); return m ? { y: +m[1], mo: +m[2], d: m[3] } : null; };

/** «01 al 14 de agosto» (mismo mes) o «30 de julio al 14 de agosto»; null si falta una fecha. */
export function rangeEs(a: string | null | undefined, b: string | null | undefined): string | null {
  const pa = a ? parts(a) : null; const pb = b ? parts(b) : null;
  if (!pa || !pb) return null;
  return pa.mo === pb.mo && pa.y === pb.y ? `${pa.d} al ${pb.d} de ${MESES[pb.mo - 1]}` : `${pa.d} de ${MESES[pa.mo - 1]} al ${pb.d} de ${MESES[pb.mo - 1]}`;
}

/** «acumulando 14 días» / «día por día» a partir de la vista publicada (acumNN | diaria). */
export function horizonPhrase(vista: string): string {
  const m = /^acum(\d+)$/.exec(vista);
  return m ? `acumulando ${m[1]} días` : vista === 'diaria' ? 'día por día' : vista;
}
export function horizonShort(vista: string): string {
  const m = /^acum(\d+)$/.exec(vista);
  return m ? `acumulado de ${m[1]} días` : vista === 'diaria' ? 'día por día' : vista;
}
/** Quién se evalúa, en palabras sencillas, según el nivel y el tipo de historial. */
export function whoPhrase(level: 'sku' | 'categoria', cohorte: string): string {
  const c = cohorte === 'primaria' ? 'con historia suficiente' : cohorte === 'historia_corta' ? 'con historia corta' : '';
  if (level === 'categoria') return c ? `las categorías de productos ${c}` : 'las categorías';
  return c ? `los productos ${c}` : 'todos los productos';
}

/** «productos con historia suficiente · acumulado de 14 días · 1.000 productos». */
export function simpleScope(level: 'sku' | 'categoria', cohorte: string, vista: string, n: string): string {
  const who = whoPhrase(level, cohorte).replace(/^los /, '').replace(/^las /, '');
  return `${who} · ${horizonShort(vista)} · ${n} ${level === 'sku' ? 'productos' : 'categorías'}`;
}

/** Resultado principal en una frase: error absoluto como porcentaje del volumen vendido, nunca como acierto. */
export function mainExplanation(wape: number | null | undefined, level: 'sku' | 'categoria', cohorte: string, vista: string): string {
  if (!isNum(wape)) return 'El error absoluto no es evaluable en este alcance (no hay ventas observadas para calcularlo); no se reemplaza por cero.';
  const x = fmtPct(wape);
  const unit = level === 'sku' ? 'producto' : 'categoría';
  return `Para ${whoPhrase(level, cohorte)}, ${horizonPhrase(vista)}, el error absoluto del promedio de 28 días equivale a cerca del ${x} del volumen vendido; no significa ${x} de acierto.${wape >= HIGH_ERROR ? ` Es un error alto por ${unit}.` : ''}`;
}

/** Etiquetas distintas: la métrica de N días (primeros N del bloque) y el bloque de prueba disponible. Fechas derivadas de las publicadas. */
export function metricPeriods(vista: string, start: string | null | undefined, end: string | null | undefined): { metric: string; block: string } {
  const m = /^acum(\d+)$/.exec(vista);
  const n = m ? +m[1] : null;
  const blockRange = rangeEs(start, end);
  const block = `Bloque de prueba disponible${blockRange ? ` del ${blockRange}` : ': fechas no publicadas'}`;
  if (n === null) return { metric: 'Métrica diaria: cada día del bloque', block };
  const mEnd = start ? addDays(start, n - 1) : null;
  const within = !!end && !!mEnd && mEnd <= end;
  const r = within ? rangeEs(start, mEnd) : null;
  const metric = r ? `Métrica del ${r}` : `Métrica de los primeros ${n} días del bloque${start && parts(start) ? ` (desde el ${parts(start)!.d} de ${MESES[parts(start)!.mo - 1]})` : ''}`;
  return { metric, block };
}
