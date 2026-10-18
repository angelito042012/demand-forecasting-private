// Fixtures SOLO para pruebas (T11A): respetan la FORMA del contrato de la corrida final (docs/T11_CONTRATO.md §2) pero
// sus números son inventados (no son resultados de T12). Ninguna pantalla los usa fuera de las pruebas.
import { BacktestDetail, BacktestItem, ForecastPage, ForecastItem, Page, PredRow, RecoPage, RunSummary, SimBlock, SimDiff, SimScenario } from '../core/models';
import { FINAL_WARNINGS } from '../core/models';

export const FINAL_ID = 'final-20260731-0123456789ab';
export const HIST_ID = 'hist-test-active';
export const SEAL = 'd587255d87fb2d99e449a098e4c1fa6e1c1c6d5838180b7aa8fe098e9a2ce663';
export const PHASES = ['verificacion', 'preparacion', 'lectura_agosto', 'evaluacion_predictiva', 'simulacion', 'auditoria', 'reporte'];

const hdr = { generated_at: '2026-10-17T12:00:00Z', published_at: '2026-10-17T12:08:00Z', age_days_at_view: 78 };

export const histRun: RunSummary = {
  run_id: HIST_ID, run_label: 'Corrida histórica de desarrollo al 10/07/2026', cutoff: '2026-07-10', ...hdr, is_active: true,
  kind: 'historical_development', warnings: [], final_package: null,
};
export const genRun: RunSummary = {
  run_id: 'gen-test-1', run_label: 'Corrida de desarrollo generada por la aplicación con origen 10/06/2026', cutoff: '2026-06-10', ...hdr,
  is_active: false, kind: 'generated_baseline', warnings: [], final_package: null,
};
export const finalRun: RunSummary = {
  run_id: FINAL_ID, run_label: 'Evaluación final de agosto (origen 31/07/2026, bloque 01–21/08/2026)', cutoff: '2026-07-31', ...hdr,
  is_active: false, kind: 'final_evaluation', origin: '2026-07-31', target_start: '2026-08-01', target_end: '2026-08-21', horizon_days: 21,
  evaluation_period: { start: '2026-08-01', end: '2026-08-21', single_block: true },
  warnings: [...FINAL_WARNINGS],
  method: { chosen: 'promedio_28', comparator: 'rf_categoria_distribuido', control: 'cero', rf_declared_winner: false },
  coverage: { dias_evaluables: 21, nota: 'un solo bloque' },
  final_package: {
    seal_sha256: SEAL, seal_short: SEAL.slice(0, 12), frozen_selection_sha256: '8'.repeat(64),
    phases: Object.fromEntries(PHASES.map((p) => [p, 'completa'])),
    corrections: [{ code: 'R11', label: 'reconciliación técnica posterior' }], audit_ok: true,
  },
};

// ---- Backtest final ----
const methodsSku = ['cero', 'promedio_28', 'rf_distribuido'];
const methodsCat = ['cero', 'promedio_28', 'rf_categoria'];
const VISTAS = ['acum10', 'acum14', 'acum21', 'diaria'];
const WAPE: Record<string, number> = { cero: 1, promedio_28: 0.5, rf_distribuido: 0.6, rf_categoria: 0.6 };

function row(coh: string, metodo: string, vista: string, n: number, obs: number): PredRow {
  if (obs === 0) return { fold: 'FINAL', cohorte: coh, metodo, vista, n, unidades_observadas: 0, unidades_predichas: 3, MAE: 3, RMSE: 3, WAPE: null, sesgo_acumulado: 3, prop_subpronostico: 0, prop_sobrepronostico: 1, prop_exacto: 0, MAPE: null, MAPE_cobertura_reales_positivos: 0, MAPE_ceros_excluidos: 1, R2: null, R2_nota: 'indefinido' };
  return { fold: 'FINAL', cohorte: coh, metodo, vista, n, unidades_observadas: obs, unidades_predichas: obs * (metodo === 'cero' ? 0 : 1.1), MAE: 2, RMSE: 4, WAPE: WAPE[metodo] + (vista === 'diaria' ? 1 : 0), sesgo_acumulado: metodo === 'cero' ? -obs : obs * 0.1, prop_subpronostico: 0.3, prop_sobrepronostico: 0.4, prop_exacto: 0.3, MAPE: 0.9, MAPE_cobertura_reales_positivos: 0.4, MAPE_ceros_excluidos: 10, R2: metodo === 'cero' ? -0.1 : 0.3, R2_nota: null };
}
const skuRows = (): PredRow[] => ['primaria', 'historia_corta'].flatMap((c) => methodsSku.flatMap((m) => VISTAS.map((v) => row(c, m, v, c === 'primaria' ? 1000 : 100, c === 'primaria' ? 5000 : 400))));
const catRows = (): PredRow[] => ['primaria', 'historia_corta'].flatMap((c) => methodsCat.flatMap((m) => VISTAS.map((v) => row(c, m, v, c === 'primaria' ? 36 : 1, c === 'primaria' ? 9000 : 0))));

const block = (fill: number, lost: number, stock: number, buys: number): SimBlock => ({
  skus: 3758, demanda_proxy_elegible_unidades: 20000, atendidas_unidades: 20000 - lost, perdidas_unidades: lost, fill_rate: fill,
  stock_medio_unidades_por_dia: stock, stock_final_unidades: stock + 100, compras_desembolsadas_supuesto: buys, valor_stock_final_supuesto: 1000 + stock,
});
const POLICY_IDS = ['referencia_fija', 'promedio_28', 'rf_categoria_distribuido'];
const LS = [3, 7, 14]; const SS = [0, 7, 14];

function sims(): SimScenario[] {
  const out: SimScenario[] = [];
  for (const L of LS) for (const S of SS) POLICY_IDS.forEach((p, i) => {
    const b = block(0.6 + 0.01 * i + 0.001 * L, 8000 - 100 * i - L, 10000 + 500 * i + 10 * S, 200000 + 10000 * i + 100 * L);
    out.push({ scenario_id: `T12_L${L}_S${S}`, L, S, R: 7, policy: p, total: b, primaria: { ...b, skus: 3401 }, historia_corta: { ...b, skus: 357 } });
  });
  return out;
}
function diffs(): SimDiff[] {
  const m = (a: number, r: number) => ({ abs: a, rel: r });
  const metrics = (k: number) => ({ fill_rate: m(0.01 * k, 0.02 * k), perdidas_unidades: m(-50 * k, -0.01 * k), stock_medio_unidades_por_dia: m(100 * k, 0.03 * k), compras_desembolsadas_supuesto: m(5000 * k, 0.05 * k), valor_stock_final_supuesto: m(300 * k, 0.04 * k) });
  const out: SimDiff[] = [];
  for (const L of LS) for (const S of SS) {
    const pairs: [string, string][] = [['referencia_fija', 'promedio_28'], ['promedio_28', 'referencia_fija'], ['rf_categoria_distribuido', 'referencia_fija'], ['rf_categoria_distribuido', 'promedio_28']];
    for (const coh of ['total', 'primaria', 'historia_corta']) pairs.forEach(([policy, vs], i) => out.push({ scenario: `L${L}_S${S}`, policy, vs, cohorte: coh, metrics: metrics(i + 1) }));
  }
  return out;
}

export const finalBacktest: BacktestDetail = {
  backtest_id: `bt-${FINAL_ID}`, kind: 'final_evaluation', label: 'Evaluación final T12 (fixture)', folds: ['FINAL'], created: '2026-10-17T12:09:00Z',
  run_id: FINAL_ID, scenario_id: 'T12_fixture_2026-08', provenance: 'SYNTHETIC_NOT_REAL_INVENTORY',
  disclaimer: 'Inventario simulado con supuestos; no corresponde al inventario real de la empresa',
  run: { ...finalRun } as BacktestDetail['run'], view: 'all',
  predictive: {
    sku: skuRows(), categoria: catRows(),
    nuevos_sku: { skus_nuevos_con_venta_en_bloque: 7, unidades_nuevos_evaluables: 21 },
    universo: { sku_conocidos: 1100, primaria: 1000, categorias: 37 },
  } as BacktestDetail['predictive'],
  selection: {
    chosen: 'promedio_28', rf_declared_winner: false, primary_criterion: 'WAPE H14 SKU-almacén, primaria, universo común',
    primary: { WAPE_promedio_28: 0.5, WAPE_rf_distribuido: 0.6, WAPE_cero: 1, mejora_relativa: -0.2, sesgo_relativo: 0.04 },
    nota: 'no aplicable: un solo bloque',
  },
  coverage: {
    sku: [
      { fold: 'FINAL', cohorte: 'primaria', metodo: 'universo_comun', entidades: 1000, comunes: 1000, dias_evaluables_21: 21 },
      { fold: 'FINAL', cohorte: 'historia_corta', metodo: 'universo_comun', entidades: 100, comunes: 100, dias_evaluables_21: 21 },
    ],
    categoria: [{ fold: 'FINAL', cohorte: 'primaria', metodo: 'universo_comun', entidades: 36, comunes: 36, dias_evaluables_21: 21 }],
  },
  simulation: sims(), simulation_differences: diffs(),
  assumptions: { L: LS, S: SS, R: 7, escenario_principal: { L: 7, S: 7 }, limites: ['un solo bloque de 21 días'], demanda: 'proxy: venta observada' },
};

export const finalBacktestList: Page<BacktestItem> = {
  items: [{ backtest_id: finalBacktest.backtest_id!, kind: 'final_evaluation', label: finalBacktest.label!, folds: ['FINAL'], created: '2026-10-17T12:09:00Z', run_id: FINAL_ID }],
  page: 1, page_size: 50, total: 1, has_more: false,
};

// ---- Pronósticos ----
function fitem(over: Partial<ForecastItem>): ForecastItem {
  return { run_id: FINAL_ID, level: 'sku', entity_id: '1|1', sku: '1', almacen: '1', categoria: 'CAT A', cohorte: 'primaria', target_date: '2026-08-01', h: 1, chosen_method: 'promedio_28',
    pred: { promedio_28: 1, rf_categoria_distribuido: 1.5, cero: 0 }, observed: 2, evaluable: true, provenance: 'OBSERVED_EXCEL', run_kind: 'final_evaluation', ...over };
}
export const finalForecasts = (): ForecastPage => ({
  items: [fitem({}), fitem({ entity_id: '2|1', sku: '2', cohorte: 'historia_corta', target_date: '2026-08-15', observed: null, evaluable: false }), fitem({ entity_id: '3|1', sku: '3', target_date: '2026-08-21', observed: 0 })],
  page: 1, page_size: 50, total: 3, has_more: false, warnings: [...FINAL_WARNINGS],
});

export const finalRecoPage = (see: string | null = HIST_ID): RecoPage => ({
  items: [], page: 1, page_size: 50, total: 0, has_more: false, unavailable_reason: 'RECOMENDACION_NO_VALIDADA_PARA_ESTE_ORIGEN', see_run: see,
  run: { ...finalRun } as RecoPage['run'], provenance: 'SYNTHETIC_NOT_REAL_INVENTORY',
});
