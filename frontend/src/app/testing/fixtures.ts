// Fixtures SOLO para pruebas: respetan la forma del contrato T08; los valores son de prueba, no resultados reales.
import { ForecastItem, Page, Recommendation, RunDetail, RunSummary, Session } from '../core/models';

export const session: Session = { username: 'ana', role: 'lector', csrf_token: 'csrf-123', expires_at: '2026-10-17T20:00:00Z', idle_expires_at: '2026-10-17T13:00:00Z' };

export function page<T>(items: T[], extra: Partial<Page<T>> = {}): Page<T> {
  return { items, page: 1, page_size: 50, total: items.length, has_more: false, ...extra };
}

export const runSummary: RunSummary = {
  run_id: 'run-test-1', run_label: 'Corrida histórica de desarrollo al 10/07/2026', cutoff: '2026-07-10',
  generated_at: '2026-10-16T10:00:00Z', published_at: '2026-10-17T10:00:00Z', age_days_at_view: 99, is_active: true,
};

export const runDetail: RunDetail = {
  ...runSummary,
  method: { chosen: 'promedio_28', comparator: 'rf_categoria_distribuido', control: 'cero', note: 'nota de prueba' },
  coverage: { skus_pronosticados: 10, skus_con_recomendacion: 6, skus_sin_snapshot: 4, categorias: 2 },
};

export const forecast: ForecastItem = {
  run_id: 'run-test-1', level: 'sku', entity_id: 'SKU-T1', sku: 'SKU-T1', almacen: '1', categoria: 'CAT-T', cohorte: 'C1',
  target_date: '2026-07-11', h: 1, chosen_method: 'promedio_28',
  pred: { promedio_28: 2, rf_categoria_distribuido: 3, cero: 0 }, observed: 1, evaluable: true, provenance: 'OBSERVED_EXCEL',
};

export const recoOk: Recommendation = {
  run_id: 'run-test-1', scenario_id: 'T07_L7_S7_promedio_28_2026-07-10', provenance: 'SYNTHETIC_NOT_REAL_INVENTORY',
  snapshot_date: '2026-07-10', sku: 'SKU-T1', almacen: '1', categoria: 'CAT-T', status: 'ok', reason: null,
  on_hand: 10, in_transit: 5, position: 15, mean_28: 2, forecast_14d: 28, safety: 14, target: 42, order_qty: 27,
  horizon_days: 14, lead_time_days: 7, review_days: 7, safety_days: 7, unit_cost_assumed: 3.5, order_value_assumed: 94.5,
  currency: 'PEN', unit: 'unidad base', origin: '2026-07-10', forecast_from: '2026-07-11', forecast_to: '2026-07-24', model: 'promedio_28',
};

export const recoNoSnap: Recommendation = {
  ...recoOk, sku: 'SKU-NEW', status: 'sin_snapshot',
  reason: 'SIN_INVENTARIO_SIMULADO_AL_10_07: producto conocido despues del 31/05; no se supone stock cero',
  on_hand: null, in_transit: null, position: null, mean_28: null, forecast_14d: null, safety: null, target: null,
  order_qty: null, unit_cost_assumed: null, order_value_assumed: null,
};
