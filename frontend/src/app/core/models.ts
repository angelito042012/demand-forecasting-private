// Tipos alineados con docs/CONTRATOS.md (API propuesta). Provisionales hasta que exista la API real.
export type Provenance = 'DEMO_MOCK' | 'SYNTHETIC_NOT_REAL_INVENTORY' | 'REAL';

export interface ImportRecord {
  id: string;
  filename: string;
  status: 'accepted' | 'rejected' | 'processing';
  rows_total: number;
  rows_accepted: number;
  rows_rejected: number;
  errors: string[];
}
export interface RunRecord {
  run_id: string;
  status: 'completed' | 'running' | 'failed';
  cutoff: string;
  completed_at: string | null;
}
export interface ForecastRow {
  run_id: string;
  entity: string;
  target_date: string;
  quantity: number;
  model: string;
}
export interface RecommendationRow {
  sku: string;
  stock: number;
  in_transit: number;
  horizon_days: number;
  order_qty: number;
  reason: string;
  provenance: Provenance;
  scenario_id: string;
}
export interface HealthInfo {
  status: 'ok' | 'degraded';
  api_version: string;
}

export type LoadState<T> =
  | { kind: 'loading' }
  | { kind: 'error'; message: string }
  | { kind: 'empty' }
  | { kind: 'data'; data: T; provenance: Provenance };
