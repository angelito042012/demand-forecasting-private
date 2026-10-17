// Tipos según docs/T08_CONTRATO.md (API v1). Solo lo que el contrato define.
export type Role = 'admin' | 'lector';

export interface Session {
  username: string;
  role: Role;
  csrf_token: string;
  expires_at: string;
  idle_expires_at?: string;
}

export interface Page<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  has_more: boolean;
}

export interface Health {
  status: 'ok' | 'degraded';
  database: 'ok' | 'unavailable';
  version: string;
}

export interface RunHeader {
  run_id: string;
  run_label: string;
  cutoff: string;
  generated_at: string;
  published_at: string;
  age_days_at_view: number;
  is_active: boolean;
}

export interface RunSummary extends RunHeader {
  status?: string;
  kind?: string;
}

export interface RunDetail extends RunHeader {
  status?: string;
  method: { chosen: string; comparator: string; control: string; note?: string };
  config?: Record<string, unknown>;
  sources?: unknown;
  artifacts?: { name: string; sha256: string; size: number }[];
  code?: { commit: string };
  counts?: Record<string, number>;
  coverage?: { skus_pronosticados: number; skus_con_recomendacion: number; skus_sin_snapshot: number; categorias: number };
  evaluation_period?: { start?: string; end?: string } | Record<string, unknown>;
  provenance_notes?: string[] | string;
}

export interface ImportItem {
  import_id: string;
  archivo: string;
  mes: string;
  estado: string;
  filas_leidas: number;
  ventas_aceptadas: number;
  notas_credito: number;
  rechazadas: number;
  insertadas: number;
  ya_existentes: number;
  en_conflicto: number;
  iniciado_utc: string;
  finalizado_utc: string | null;
}
export interface ImportDetail extends ImportItem {
  rechazos_por_motivo?: Record<string, number>;
  conflictos_abiertos?: number;
  sha256?: string;
  incidencias?: Record<string, number> | { codigo: string; conteo: number }[];
}

export type GroupBy = 'day' | 'month' | 'category';
export interface SalesSummary {
  provenance: 'OBSERVED_EXCEL';
  unit: string;
  currency: string;
  from: string;
  to: string;
  items: { key: string; lineas_venta: number; unidades: number; importe_pen: number }[];
  notas_credito: { lineas: number; importe_pen: number };
  excluded_days: { fecha: string; motivo: string }[];
}

export interface ForecastItem {
  run_id: string;
  level: 'sku' | 'categoria';
  entity_id: string;
  sku: string | null;
  almacen: string | null;
  categoria: string | null;
  cohorte: string | null;
  target_date: string;
  h: number;
  chosen_method: string;
  pred: { promedio_28: number; rf_categoria_distribuido: number; cero: number };
  observed: number | null;
  evaluable: boolean;
  provenance: 'OBSERVED_EXCEL';
}

export interface Recommendation {
  run_id: string;
  scenario_id: string;
  provenance: 'SYNTHETIC_NOT_REAL_INVENTORY';
  snapshot_date: string;
  sku: string;
  almacen: string;
  categoria: string | null;
  status: 'ok' | 'sin_snapshot';
  reason: string | null;
  on_hand: number | null;
  in_transit: number | null;
  position: number | null;
  mean_28: number | null;
  forecast_14d: number | null;
  safety: number | null;
  target: number | null;
  order_qty: number | null;
  horizon_days: number;
  lead_time_days: number;
  review_days: number;
  safety_days: number;
  unit_cost_assumed: number | null;
  order_value_assumed?: number | null;
  currency: string;
  unit: string;
  origin: string;
  forecast_from: string;
  forecast_to: string;
  model: string;
  explanation_steps?: string[];
  explanation?: string | string[];
}

export interface BacktestItem {
  backtest_id: string;
  kind: string;
  label: string;
  folds: number | string[];
  created: string;
}
export type BacktestView = 'predictive' | 'simulation' | 'all';
/** El contrato no fija el esquema interno de métricas: se muestra tal cual lo publica el servidor. */
export interface BacktestDetail {
  backtest_id?: string;
  scenario_id?: string;
  provenance?: string;
  disclaimer?: string;
  [seccion: string]: unknown;
}

export type ErrorCode =
  | 'NO_AUTENTICADO' | 'SESION_EXPIRADA' | 'PROHIBIDO' | 'NO_ENCONTRADO' | 'ENTRADA_INVALIDA'
  | 'DEMASIADOS_INTENTOS' | 'CSRF_INVALIDO' | 'ORIGEN_NO_PERMITIDO' | 'AGOSTO_RESERVADO'
  | 'SERVICIO_NO_DISPONIBLE' | 'RED' | 'DESCONOCIDO';

export interface AppError {
  status: number;
  code: ErrorCode;
  message: string;
  retryAfter?: number;
  details?: unknown[];
}

export type LoadState<T> =
  | { kind: 'loading' }
  | { kind: 'error'; error: AppError }
  | { kind: 'empty' }
  | { kind: 'data'; data: T };

export const SIM_NOTICE = 'Inventario simulado con supuestos; no corresponde al inventario real de la empresa';
export const RUN_LABEL = 'Corrida histórica de desarrollo al 10/07/2026';
