import type { RunHeader, RunQuality } from './run';

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
  WAPE?: number | null;
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

export interface FinalPrimary {
  WAPE_promedio_28?: number | null;
  WAPE_rf_distribuido?: number | null;
  WAPE_cero?: number | null;
  mejora_relativa?: number | null;
  sesgo_relativo?: number | null;
  [k: string]: unknown;
}

export interface BacktestSelection {
  chosen?: string;
  rf_declared_winner?: boolean;
  primary_criterion?: string;
  primary?: FinalPrimary;
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
  kind?: string;
  run_id?: string;
  backtest_id?: string;
  scenario_id?: string;
  provenance?: string;
  disclaimer?: string;
  run?: (RunHeader & RunQuality) | null;
  label?: string;
  folds?: string[] | number;
  predictive?: {
    sku?: PredRow[]; categoria?: PredRow[]; nota?: string;
    nuevos_sku?: Record<string, number>; universo?: Record<string, number>;
    dias_evaluables?: number; dias_no_evaluables?: unknown[]; cobertura?: { sku?: CoverageRow[]; categoria?: CoverageRow[] };
  };
  selection?: BacktestSelection;
  coverage?: { sku?: CoverageRow[]; categoria?: CoverageRow[] };
  simulation?: SimScenario[];
  simulation_differences?: SimDiff[];
  assumptions?: BacktestAssumptions;
  [seccion: string]: unknown;
}
