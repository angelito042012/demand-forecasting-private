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

/** Motivo de sustitución de una corrida (la API lo publica cuando una corrección de precisión la reemplaza). */
export interface QualityIssue {
  superseded_by?: string;
  reason?: string;
  message?: string;
  code?: string;
  [k: string]: unknown;
}

/** Estado de calidad de una corrida; se repite en `run` de recomendaciones y backtests. */
export interface RunQuality {
  status?: string;
  validation_status?: string;
  quality_issue?: QualityIssue | null;
}

export interface RunSummary extends RunHeader, RunQuality {
  kind?: string;
  origin?: string;
  target_start?: string;
  target_end?: string;
  horizon_days?: number;
  provenance?: string;
  disclaimer?: string;
  method?: RunDetail['method'];
  counts?: Record<string, number>;
  coverage?: RunDetail['coverage'];
  evaluation_period?: RunDetail['evaluation_period'];
}

export interface RunDetail extends RunHeader, RunQuality {
  kind?: string;
  provenance?: string;
  disclaimer?: string;
  fingerprint_short?: string;
  method: { chosen: string; comparator: string; control: string; note?: string };
  config?: Record<string, unknown>;
  sources?: unknown;
  artifacts?: { name: string; sha256: string; size?: number; size_bytes?: number }[];
  code?: { commit: string };
  counts?: Record<string, number>;
  coverage?: { skus_pronosticados: number; skus_con_recomendacion: number; skus_sin_snapshot: number; categorias: number; skus_categoria_desconocida?: number };
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
  disclaimer?: string;
  explanation_steps?: string[];
  explanation?: string | string[];
  /** Señales exactas (corridas corregidas): suma de unidades y días útiles de la ventana, y la media como fracción. */
  sum_28?: string | number | null;   // la API lo publica como texto exacto
  days_28?: number | null;
  mean_28_exact?: string | null;
  transit_breakdown?: { ordered_until_snapshot?: number; received_until_snapshot?: number } | null;
  run?: (RunHeader & RunQuality) | null;
}

/** Página de recomendaciones: el servidor añade la corrida a la que pertenecen. */
export interface RecoPage extends Page<Recommendation> {
  provenance?: string;
  disclaimer?: string;
  nota?: string;
  run?: (RunHeader & RunQuality) | null;
}

export interface BacktestItem {
  backtest_id: string;
  kind: string;
  label: string;
  folds: number | string[];
  created: string;
  run_id?: string;
  scenario_id?: string;
  provenance?: string;
  disclaimer?: string;
  run?: (RunHeader & RunQuality) | null;
}
export type BacktestView = 'predictive' | 'simulation' | 'all';

export type Cohorte = 'total' | 'primaria' | 'historia_corta';
export type Vista = 'acum10' | 'acum14' | 'acum21' | 'diaria';

/** Fila predictiva publicada (backtest T07). Las filas sin datos evaluables solo traen n = 0. */
export interface PredRow {
  fold: string;
  cohorte: string;
  metodo: string;
  vista: string;
  n: number;
  unidades_observadas?: number;
  unidades_predichas?: number;
  MAE?: number;
  RMSE?: number;
  WAPE?: number;
  sesgo_acumulado?: number;
  prop_subpronostico?: number;
  prop_sobrepronostico?: number;
  prop_exacto?: number;
  MAPE?: number | null;
  MAPE_cobertura_reales_positivos?: number | null;
  MAPE_ceros_excluidos?: number | null;
  R2?: number | null;
  R2_nota?: string | null;
}

export interface CoverageRow {
  fold: string;
  cohorte: string;
  metodo: string;
  entidades?: number;
  entidades_con_prediccion?: number;
  comunes?: number;
  dias_evaluables_21?: number;
}

export type SimBlock = Record<string, number | null>;
export interface SimScenario {
  scenario_id: string;
  L: number;
  S: number;
  R: number;
  policy: string;
  total: SimBlock;
  primaria: SimBlock;
  historia_corta: SimBlock;
  [k: string]: unknown;
}
export interface SimDiff {
  scenario: string;
  policy: string;
  vs: string;
  cohorte: string;
  metrics: Record<string, { abs: number | null; rel: number | null }>;
}

export interface BacktestAssumptions {
  L?: number[];
  S?: number[];
  R?: number;
  escenario_principal?: { L: number; S: number };
  limites?: string[];
  demanda?: string;
  [k: string]: unknown;
}

export interface BacktestSelection {
  vista?: string;
  mejora_relativa?: number;
  cumple_regla?: boolean;
  nota?: string;
  metodo_elegido?: string;
  comparador?: string;
  control?: string;
  [k: string]: unknown;
}

export interface BacktestDetail {
  run_id?: string;
  backtest_id?: string;
  scenario_id?: string;
  provenance?: string;
  disclaimer?: string;
  run?: (RunHeader & RunQuality) | null;
  label?: string;
  folds?: string[] | number;
  predictive?: { sku?: PredRow[]; categoria?: PredRow[]; nota?: string };
  selection?: BacktestSelection;
  coverage?: { sku?: CoverageRow[]; categoria?: CoverageRow[] };
  simulation?: SimScenario[];
  simulation_differences?: SimDiff[];
  assumptions?: BacktestAssumptions;
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
