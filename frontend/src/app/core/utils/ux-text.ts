/**
 * UX01: textos y nombres comprensibles. SOLO presentación: nunca altera valores, fechas ni resultados.
 * Los nombres de análisis se derivan de los datos que publica la API (tipo, fecha de corte, fechas objetivo); nada está escrito
 * para tres registros concretos. Los identificadores técnicos (run_id, tipo interno) se muestran solo en «Detalles técnicos».
 */
import { fmtDate } from './format';
import { isFinal, isGenerated } from '../run-choice';
import type { JobStatus, RunSummary } from '../models';

const MONTHS = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];

/** «2026-07-10» → «julio»; '' si la fecha no es válida. */
export function monthName(iso: string | null | undefined): string {
  const m = /^(\d{4})-(\d{2})-/.exec(iso ?? '');
  return m ? (MONTHS[Number(m[2]) - 1] ?? '') : '';
}

/** «2026-07-10» → «10 de julio de 2026» (fechas en español para texto corrido). */
export function longDate(iso: string | null | undefined): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso ?? '');
  return m ? `${Number(m[3])} de ${MONTHS[Number(m[2]) - 1]} de ${m[1]}` : '—';
}

type RunLike = Pick<RunSummary, 'kind' | 'cutoff' | 'run_label' | 'target_start' | 'target_end' | 'origin' | 'is_active' | 'status' | 'validation_status'>;

/** Nombre corto y comprensible del análisis, derivado de sus datos. */
export function analysisName(r: RunLike | null | undefined): string {
  if (!r) return 'Análisis';
  if (isFinal(r.kind)) { const mes = monthName(r.target_start); return mes ? `Evaluación de ${mes}` : 'Evaluación de resultados'; }
  if (isGenerated(r.kind)) return `Análisis creado con ventas hasta el ${fmtDate(r.origin ?? r.cutoff)}`;
  const mes = monthName(r.origin ?? r.cutoff);
  return mes ? `Ejemplo de ${mes}` : (r.run_label || 'Ejemplo histórico');
}

/** Frase de una línea sobre qué permite hacer el análisis. */
export function analysisPurpose(r: Pick<RunSummary, 'kind'> | null | undefined): string {
  if (!r) return '';
  if (isFinal(r.kind)) return 'Permite comparar estimaciones con ventas registradas; no genera pedidos.';
  if (isGenerated(r.kind)) return 'Estimaciones creadas desde la aplicación con el promedio de una ventana de 28 días de calendario; no incluyen una evaluación contra ventas registradas, por diseño.';
  return 'Ejemplo con datos históricos: compara estimaciones con ventas ya registradas y permite explorar una reposición simulada.';
}

/** Tipo de análisis en palabras sencillas (el tipo interno queda en los detalles técnicos). */
export function kindWords(kind: string | null | undefined): string {
  if (isFinal(kind)) return 'Evaluación';
  if (isGenerated(kind)) return 'Creado en la aplicación';
  return 'Ejemplo histórico';
}

export function isReplaced(r: Pick<RunSummary, 'status' | 'validation_status'> | null | undefined): boolean {
  if (!r) return false;
  return r.status === 'superseded' || (r.validation_status !== undefined && r.validation_status !== null && r.validation_status !== 'valid');
}

/** «En uso por defecto» (puntero original, sin modificarlo) frente a «Seleccionado para consultar» (solo la interfaz). */
export function runStatusChip(r: Pick<RunSummary, 'is_active' | 'status' | 'validation_status'>, selected: boolean): { text: string; tone: 'ok' | 'info' | 'bad' | '' } {
  if (isReplaced(r)) return { text: 'Versión reemplazada', tone: 'bad' };
  if (r.is_active) return { text: 'En uso por defecto', tone: 'ok' };
  return selected ? { text: 'Seleccionado para consultar', tone: 'info' } : { text: 'Disponible', tone: '' };
}

/** Período estimado en una frase; vacío si la API no lo publica. */
export function periodText(r: Pick<RunSummary, 'target_start' | 'target_end'>): string {
  return r.target_start && r.target_end ? `del ${fmtDate(r.target_start)} al ${fmtDate(r.target_end)}` : '';
}

/** Días transcurridos en palabras sencillas (el dato lo entrega el servidor). */
export function ageWords(days: number | null | undefined): string {
  if (days === null || days === undefined) return '';
  return days === 0 ? 'hoy' : days === 1 ? 'hace 1 día' : `hace ${days} días`;
}

/** Categoría legible: «HIGIENE CAPILAR» → «Higiene capilar». No inventa nombres de producto. */
export function categoryLabel(c: string | null | undefined): string {
  if (!c) return 'Sin categoría';
  const t = c.trim().toLowerCase();
  return t.charAt(0).toUpperCase() + t.slice(1);
}

/** Producto sin descripción autorizada: «Producto 1010004 · Higiene capilar». */
export function productLabel(code: string | null | undefined, categoria?: string | null): string {
  const base = `Producto ${code ?? '—'}`;
  return categoria ? `${base} · ${categoryLabel(categoria)}` : base;
}

/** Estado de un trabajo en palabras sencillas. */
export function jobStatusWords(s: JobStatus | string | undefined): string {
  switch (s) {
    case 'queued': return 'Esperando turno';
    case 'running': return 'En curso';
    case 'completed': return 'Terminado';
    case 'failed': return 'No se pudo completar';
    default: return String(s ?? '');
  }
}

/** Glosario (Ayuda): término de la interfaz → explicación y término técnico original. */
export const GLOSSARY: { term: string; meaning: string; technical: string }[] = [
  { term: 'Análisis', meaning: 'Un conjunto de resultados que puedes consultar: el ejemplo histórico, los que se crean en la aplicación y la evaluación de agosto.', technical: 'corrida (run_id)' },
  { term: 'Ventas utilizadas hasta', meaning: 'Última fecha de ventas registradas que usó el cálculo. Nada posterior a esa fecha influyó en las estimaciones.', technical: 'corte / origen' },
  { term: 'Período estimado', meaning: 'Fechas para las que se estimaron ventas; «día de la previsión» indica cuántos días después de la fecha de corte cae cada estimación.', technical: 'horizonte / h' },
  { term: 'Código del producto', meaning: 'Identificador del producto en las ventas. La aplicación no muestra nombres comerciales porque los archivos no los traen autorizados.', technical: 'SKU' },
  { term: 'Por recibir (simulado)', meaning: 'Unidades que, en el escenario simulado, ya fueron pedidas y todavía no llegan.', technical: 'tránsito / in_transit' },
  { term: 'Promedio de los últimos 28 días', meaning: 'Método elegido: estima las ventas diarias con el promedio de una ventana de 28 días de calendario: cuentan los días válidos, incluidos los de venta cero, y no cuentan los días excluidos. No supone que todo producto tenga 28 días de historia.', technical: 'promedio_28' },
  { term: 'Modelo experimental', meaning: 'Un segundo método (bosque aleatorio) que se compara con el promedio. No resultó mejor y no se usa para decidir.', technical: 'RF distribuido / Random Forest' },
  { term: 'Comparación con ventas registradas', meaning: 'Qué tanto se parecieron las estimaciones a las ventas que sí ocurrieron en un período ya conocido.', technical: 'backtest' },
  { term: 'Tipo de historial', meaning: 'Productos con historia suficiente («primaria») o con historia corta; se evalúan por separado.', technical: 'cohorte' },
  { term: 'Error absoluto (WAPE)', meaning: 'Suma de los errores dividida entre las unidades vendidas. 0,78 equivale a un error acumulado del 78 % del volumen vendido; no significa 78 % de acierto.', technical: 'WAPE' },
  { term: 'Ejemplo de julio / Evaluación de agosto', meaning: 'El ejemplo usa ventas hasta julio para explorar estimaciones y reposición simulada. La evaluación compara estimaciones fijadas a fines de julio con las ventas reales de agosto.', technical: 'T07 / T12' },
  { term: 'En uso por defecto', meaning: 'Análisis que la aplicación abre cuando no eliges otro. Elegir otro para consultar no cambia cuál está en uso por defecto.', technical: 'corrida activa (puntero)' },
  { term: 'Inventario simulado', meaning: 'Existencias inventadas con supuestos para poder ilustrar el cálculo. No corresponden al inventario real de la empresa.', technical: 'SYNTHETIC_NOT_REAL_INVENTORY' },
  { term: 'Inventario informado', meaning: 'Existencias que la empresa declaró en un conteo con fecha y hora. No se verificó de forma independiente y no es inventario simulado.', technical: 'CONTEO_FISICO_REPORTADO_POR_USUARIO' },
  { term: 'Disponible', meaning: 'Unidades libres para vender que la empresa informó, en la presentación indicada (p. ej. caja de 12); no se multiplicó.', technical: 'libre' },
  { term: 'Plan de compra', meaning: 'Unidades que habría que pedir por producto para cubrir un mes, bajo supuestos visibles. No es un pedido ejecutado ni una mejora comprobada.', technical: 'plan_id / escenario' },
  { term: 'Compra propuesta', meaning: 'Una sola orden por producto, hecha en la fecha de decisión y redondeada al final. Si no se puede calcular, se dice así; nunca se muestra como cero.', technical: 'purchase_qty' },
  { term: 'Faltante', meaning: 'Ventas que no se podrían atender porque no habría existencias. No se recuperan después.', technical: 'shortage' },
  { term: 'Reserva', meaning: 'Días de ventas previstas que se quieren dejar al terminar el mes. Es un supuesto, no una garantía de atención.', technical: 'reserve_days' },
  { term: 'Plazo de entrega', meaning: 'Días naturales entre la decisión de compra y la llegada del pedido. Es un supuesto que se puede cambiar.', technical: 'lead_days' },
  { term: 'No informado', meaning: 'La empresa no declaró ese dato. No equivale a cero.', technical: 'null' },
];
