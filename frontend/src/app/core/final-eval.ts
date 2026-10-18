// Ayudas de la vista «Evaluación final (T12)». Solo leen el documento publicado (backtest `final_evaluation`);
// no recalculan métricas de modelo. Las únicas cuentas son cocientes de números ya publicados (sesgo/observado,
// variación relativa de dos bloques de simulación cuando la API no trae la diferencia).
import { BacktestDetail, Cohorte, CoverageRow, PredRow, SimBlock, SimDiff, SimScenario } from './models';
import { POLICIES } from './backtest';

export const FINAL_METHOD_INFO: Record<string, { label: string; role: string }> = {
  promedio_28: { label: 'Promedio de 28 días', role: 'método operativo elegido' },
  rf_distribuido: { label: 'RF distribuido', role: 'comparador (sin ganador declarado)' },
  rf_categoria: { label: 'RF por categoría', role: 'comparador (sin ganador declarado)' },
  cero: { label: 'Cero', role: 'control' },
};
const ORDER = ['promedio_28', 'rf_distribuido', 'rf_categoria', 'cero'];
const ord = (m: string) => { const i = ORDER.indexOf(m); return i < 0 ? 99 : i; };

export const FINAL_VISTAS: { id: string; label: string }[] = [
  { id: 'acum10', label: 'Acumulado 10 días (H10)' },
  { id: 'acum14', label: 'Acumulado 14 días (H14)' },
  { id: 'acum21', label: 'Acumulado 21 días (H21)' },
  { id: 'diaria', label: 'Diaria' },
];

/** Filas del bloque único (cualquier fold: la evaluación final solo publica «FINAL»). */
export function finalRows(d: BacktestDetail | null, level: 'sku' | 'categoria', cohorte: string, vista: string): PredRow[] {
  const rows = (d?.predictive?.[level] ?? []).filter((r) => r.cohorte === cohorte && r.vista === vista);
  return [...rows].sort((a, b) => ord(a.metodo) - ord(b.metodo));
}

export interface PrimaryFinding {
  n: number | null;
  wape: { promedio_28: number | null; rf: number | null; cero: number | null };
  mejora: number | null;
  sesgoRelPublicado: number | null;
  /** sesgo acumulado / unidades observadas, calculado con las dos cifras publicadas de cada fila. */
  sesgoObs: { promedio_28: number | null; rf: number | null };
  criterion: string | null;
  note: string | null;
  rfDeclaredWinner: boolean | null;
}

const num = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null);
const ratio = (a: unknown, b: unknown): number | null => (num(a) !== null && num(b) !== null && b !== 0 ? (a as number) / (b as number) : null);

/** Hallazgo primario: WAPE H14, SKU-almacén, cohorte primaria, universo común. Usa `selection.primary`; n sale de la fila publicada. */
export function primaryFinding(d: BacktestDetail | null): PrimaryFinding {
  const rows = finalRows(d, 'sku', 'primaria', 'acum14');
  const by = (m: string) => rows.find((r) => r.metodo === m);
  const p = d?.selection?.primary;
  const prom = by('promedio_28'); const rf = by('rf_distribuido'); const cero = by('cero');
  return {
    n: num(prom?.n) ?? num(rf?.n) ?? num(cero?.n),
    wape: {
      promedio_28: num(p?.WAPE_promedio_28) ?? num(prom?.WAPE),
      rf: num(p?.WAPE_rf_distribuido) ?? num(rf?.WAPE),
      cero: num(p?.WAPE_cero) ?? num(cero?.WAPE),
    },
    mejora: num(p?.mejora_relativa),
    // el publicador guarda el sesgo relativo por método ({promedio_28, rf_distribuido}); se muestra el del comparador RF
    sesgoRelPublicado: num(p?.sesgo_relativo) ?? (p?.sesgo_relativo && typeof p.sesgo_relativo === 'object' ? num((p.sesgo_relativo as Record<string, unknown>)['rf_distribuido']) : null),
    sesgoObs: { promedio_28: ratio(prom?.sesgo_acumulado, prom?.unidades_observadas), rf: ratio(rf?.sesgo_acumulado, rf?.unidades_observadas) },
    criterion: typeof d?.selection?.primary_criterion === 'string' ? d.selection.primary_criterion : null,
    note: typeof d?.selection?.nota === 'string' ? d.selection.nota : typeof d?.selection?.['note'] === 'string' ? (d.selection['note'] as string) : null,
    rfDeclaredWinner: typeof d?.selection?.rf_declared_winner === 'boolean' ? d.selection.rf_declared_winner : null,
  };
}

/** Cobertura del universo común (`coverage.sku|categoria` con fold FINAL) y bloques opcionales de predictivo.json. */
export function finalCoverageRows(d: BacktestDetail | null, level: 'sku' | 'categoria'): CoverageRow[] {
  return (d?.coverage?.[level] ?? d?.predictive?.cobertura?.[level] ?? []).filter((r) => r.metodo === 'universo_comun');
}
export function scalarsOf(o: unknown): [string, string][] {
  if (!o || typeof o !== 'object') return [];
  return Object.entries(o).filter(([, v]) => ['string', 'number', 'boolean'].includes(typeof v)).map(([k, v]) => [k, String(v)]);
}
/** SKU nuevos: bloque `nuevos_sku` en `predictive` o en `coverage` (según lo publique el publicador). */
export function newSkus(d: BacktestDetail | null): Record<string, number> | null {
  const a = d?.predictive?.nuevos_sku ?? (d?.coverage as { nuevos_sku?: Record<string, number> } | undefined)?.nuevos_sku;
  return a && typeof a === 'object' ? a : null;
}
export function universe(d: BacktestDetail | null): Record<string, number> | null {
  const a = d?.predictive?.universo ?? (d?.coverage as { universo?: Record<string, number> } | undefined)?.universo;
  return a && typeof a === 'object' ? a : null;
}

// ---- Simulación ----
export const SCENARIO_ID = (L: number, S: number) => `L${L}_S${S}`;
export const FINAL_BASE = 'promedio_28';

export function scenarioOf(d: BacktestDetail | null, L: number, S: number, policy: string): SimScenario | null {
  return (d?.simulation ?? []).find((x) => x.L === L && x.S === S && x.policy === policy) ?? null;
}
export function blockOf(d: BacktestDetail | null, L: number, S: number, policy: string, cohorte: Cohorte): SimBlock | null {
  const s = scenarioOf(d, L, S, policy);
  return s ? ((s[cohorte] as SimBlock | undefined) ?? null) : null;
}
export function diffOf(d: BacktestDetail | null, L: number, S: number, policy: string, vs: string, cohorte: Cohorte): SimDiff | null {
  return (d?.simulation_differences ?? []).find((x) => x.scenario === SCENARIO_ID(L, S) && x.policy === policy && x.vs === vs && x.cohorte === cohorte) ?? null;
}

export interface ServiceVsInventory {
  L: number; S: number;
  dFill: number | null; dStockRel: number | null; dComprasRel: number | null; dPerdidasRel: number | null;
}

/** RF distribuido frente a promedio_28 en cada escenario (total): servicio frente a stock y compras. Usa la diferencia publicada; si falta, el cociente de los bloques. */
export function serviceVsInventory(d: BacktestDetail | null, Ls: number[], Ss: number[]): ServiceVsInventory[] {
  const out: ServiceVsInventory[] = [];
  const rfId = POLICIES[2].id;
  for (const L of Ls) {
    for (const S of Ss) {
      const pub = diffOf(d, L, S, rfId, FINAL_BASE, 'total')?.metrics;
      const a = blockOf(d, L, S, rfId, 'total'); const b = blockOf(d, L, S, FINAL_BASE, 'total');
      const rel = (k: string) => num(pub?.[k]?.rel) ?? (a && b && num(b[k]) ? ratio((num(a[k]) ?? NaN) - (num(b[k]) ?? NaN), b[k]) : null);
      const dFill = num(pub?.['fill_rate']?.abs) ?? (a && b && num(a['fill_rate']) !== null && num(b['fill_rate']) !== null ? (a['fill_rate'] as number) - (b['fill_rate'] as number) : null);
      out.push({ L, S, dFill, dStockRel: rel('stock_medio_unidades_por_dia'), dComprasRel: rel('compras_desembolsadas_supuesto'), dPerdidasRel: rel('perdidas_unidades') });
    }
  }
  return out;
}
