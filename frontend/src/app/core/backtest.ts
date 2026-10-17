import { BacktestDetail, CoverageRow, Cohorte, PredRow, SimBlock, SimDiff, SimScenario } from './models';

/** Orden y rótulos de las tres políticas de reposición comparadas (T07). */
export const POLICIES: { id: string; label: string; role: string }[] = [
  { id: 'referencia_fija', label: 'Referencia fija (0531)', role: 'referencia' },
  { id: 'promedio_28', label: 'Promedio de 28 días', role: 'elegida' },
  { id: 'rf_categoria_distribuido', label: 'RF por categoría distribuido', role: 'comparador experimental (no ganó)' },
];
export const BASE_POLICY = 'promedio_28';

export const METHOD_INFO: Record<string, { label: string; role: string }> = {
  promedio_28: { label: 'Promedio de 28 días', role: 'elegido' },
  rf_distribuido: { label: 'RF distribuido', role: 'comparador experimental (no ganó)' },
  rf_categoria: { label: 'RF por categoría', role: 'comparador experimental (no ganó)' },
  referencia_fija_0531: { label: 'Referencia fija (0531)', role: 'referencia' },
  cero: { label: 'Cero', role: 'control' },
};
export const METHOD_ORDER = ['promedio_28', 'rf_distribuido', 'rf_categoria', 'referencia_fija_0531', 'cero'];

export const COHORTES: { id: Cohorte; label: string }[] = [
  { id: 'total', label: 'Total (todos los SKU)' },
  { id: 'primaria', label: 'Cohorte primaria' },
  { id: 'historia_corta', label: 'Historia corta' },
];
export const PRED_COHORTES = COHORTES.filter((c) => c.id !== 'total');
export const VISTAS: { id: string; label: string }[] = [
  { id: 'acum10', label: 'Acumulado 10 días' },
  { id: 'acum14', label: 'Acumulado 14 días' },
  { id: 'acum21', label: 'Acumulado 21 días' },
  { id: 'diaria', label: 'Diaria' },
];
export const AGREGADO = 'AGREGADO';

/** Rótulos de las métricas de simulación (todas se conservan en el detalle plegado). */
export const SIM_LABELS: Record<string, string> = {
  skus: 'SKU simulados',
  dias_sku_evaluables: 'Días-SKU evaluables',
  demanda_proxy_elegible_unidades: 'Demanda proxy elegible (unidades)',
  atendidas_unidades: 'Unidades atendidas',
  perdidas_unidades: 'Unidades perdidas (faltantes)',
  fill_rate: 'Servicio (fill rate)',
  dias_sku_con_faltante: 'Días-SKU con faltante',
  tasa_dias_sku_con_faltante: 'Tasa de días-SKU con faltante',
  tasa_faltante_sobre_dias_con_demanda: 'Faltante sobre días con demanda',
  stock_medio_unidades_por_dia: 'Stock medio (unidades/día)',
  stock_inicial_unidades: 'Stock inicial (unidades)',
  stock_final_unidades: 'Stock final (unidades)',
  pedidos_lineas: 'Líneas de pedido',
  pedidos_unidades: 'Unidades pedidas',
  recibidas_unidades: 'Unidades recibidas',
  transito_final_unidades: 'Tránsito final (unidades)',
  holding_supuesto: 'Costo de mantener stock (PEN, supuesto)',
  compras_desembolsadas_supuesto: 'Compras desembolsadas (PEN, supuesto)',
  costo_consumido_supuesto: 'Costo consumido (PEN, supuesto)',
  valor_stock_inicial_supuesto: 'Valor del stock inicial (PEN, supuesto)',
  valor_stock_final_supuesto: 'Valor del stock final (PEN, supuesto)',
  valor_transito_final_supuesto: 'Valor del tránsito final (PEN, supuesto)',
};
export type MetricKind = 'int' | 'pen' | 'pct';
const KIND: Record<string, MetricKind> = {
  fill_rate: 'pct', tasa_dias_sku_con_faltante: 'pct', tasa_faltante_sobre_dias_con_demanda: 'pct',
  holding_supuesto: 'pen', compras_desembolsadas_supuesto: 'pen', costo_consumido_supuesto: 'pen',
  valor_stock_inicial_supuesto: 'pen', valor_stock_final_supuesto: 'pen', valor_transito_final_supuesto: 'pen',
};
export const kindOf = (k: string): MetricKind => KIND[k] ?? 'int';

export function scenarioKey(L: number, S: number): string { return `L${L}_S${S}`; }

export interface SimRow {
  policy: string;
  scenario: SimScenario | null;
  block: SimBlock | null;
  /** Diferencias frente a promedio_28 en la misma cohorte (null para la propia base o si falta). */
  diff: SimDiff | null;
}

/** Las tres políticas del escenario (L, S) y cohorte elegidos, con sus diferencias frente a promedio_28. */
export function simRows(d: BacktestDetail | null, L: number, S: number, cohorte: Cohorte): SimRow[] {
  const sims = d?.simulation ?? [];
  const diffs = d?.simulation_differences ?? [];
  return POLICIES.map((p) => {
    const scenario = sims.find((x) => x.L === L && x.S === S && x.policy === p.id) ?? null;
    const diff = p.id === BASE_POLICY ? null
      : diffs.find((x) => x.scenario === scenarioKey(L, S) && x.policy === p.id && x.vs === BASE_POLICY && x.cohorte === cohorte) ?? null;
    return { policy: p.id, scenario, block: scenario ? (scenario[cohorte] as SimBlock) ?? null : null, diff };
  });
}

const order = (m: string) => { const i = METHOD_ORDER.indexOf(m); return i < 0 ? 99 : i; };

/** Filas predictivas del nivel/cohorte/vista/fold elegidos, en el orden fijo de métodos. */
export function predRows(d: BacktestDetail | null, level: 'sku' | 'categoria', cohorte: string, vista: string, fold: string): PredRow[] {
  const rows = (d?.predictive?.[level] ?? []).filter((r) => r.cohorte === cohorte && r.vista === vista && r.fold === fold);
  return [...rows].sort((a, b) => order(a.metodo) - order(b.metodo));
}

export function foldsOf(d: BacktestDetail | null): string[] {
  const set = new Set<string>();
  for (const r of [...(d?.predictive?.sku ?? []), ...(d?.predictive?.categoria ?? [])]) if (r.fold !== AGREGADO) set.add(r.fold);
  return [AGREGADO, ...[...set].sort()];
}

export interface CoverageInfo { conPrediccion: number; universo: number }

/** Cobertura de un método: entidades con predicción sobre el universo común (suma de los folds elegidos). */
export function coverageOf(d: BacktestDetail | null, level: 'sku' | 'categoria', cohorte: string, fold: string, metodo: string): CoverageInfo | null {
  const rows: CoverageRow[] = (d?.coverage?.[level] ?? []).filter((r) => r.cohorte === cohorte && (fold === AGREGADO || r.fold === fold));
  const universe = rows.filter((r) => r.metodo === 'universo_comun');
  if (!universe.length) return null;
  const total = universe.reduce((a, r) => a + (r.entidades ?? 0), 0);
  const own = rows.filter((r) => r.metodo === metodo && r.entidades_con_prediccion !== undefined);
  const con = own.length ? own.reduce((a, r) => a + (r.entidades_con_prediccion ?? 0), 0) : universe.reduce((a, r) => a + (r.comunes ?? 0), 0);
  return { conPrediccion: con, universo: total };
}
