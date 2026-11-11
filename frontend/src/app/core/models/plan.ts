import type { JobStatus } from './job';
import type { PlanConfirmation, PlanSnapshotKind } from './stock';

export type PlanStatus = 'OK' | 'LLEGA_TARDE' | 'NO_LLEGA_A_TIEMPO' | 'NO_CALCULABLE';
export type PlanNature = 'REPORTADA' | 'ASUMIDA';
export interface PlanPendingOrder { producto_id: string; units: number; arrival_date: string; nature: PlanNature }
export interface PlanAssumption { code?: string; text: string; nature?: string }

export interface PlanInputs {
  dataset: { dataset_id: string; sales_cutoff: string; source_rows?: number; classes?: Record<string, number>; imported_at?: string } | null;
  snapshot: { snapshot_id: string; as_of_local: string; warehouse?: { id: string; name: string } | string; products?: number; kind?: PlanSnapshotKind } | null;
  defaults?: {
    month: string; decision_date: string; lead_days: number[]; reserve_days: number; min_order: number; order_multiple: number;
    pending_orders: PlanPendingOrder[];
  };
  limits?: {
    decision_min: string; decision_max: string; months: string[]; lead_min: number; lead_max: number; max_leads: number; horizon_days: number;
  };
  assumptions?: PlanAssumption[];
  unavailable_reason?: string | null;
}

export interface PlanRef {
  plan_id: string; month: string; decision_date: string; lead_days: number[]; status: string; created_at?: string;
  version?: number | null; dataset_id?: string; snapshot_id?: string; counts?: Record<string, unknown> | null;
}

export interface PlanList { items?: PlanRef[]; unavailable_reason?: string | null }

export interface PlanParams {
  month: string; decision_date: string; lead_days: number[]; reserve_days: number; min_order: number; order_multiple: number;
  pending_orders: PlanPendingOrder[];
}

export interface PlanDates {
  sales_cutoff: string; count_date?: string; count_as_of_local?: string; decision_date?: string;
  month_start?: string; month_end?: string; window_start?: string;
}

export interface PlanSnapshotHeader {
  snapshot_id?: string; as_of_local?: string; warehouse?: { id: string; name: string } | string;
  kind?: PlanSnapshotKind;
  base_count_as_of_local?: string; last_movement_local?: string; discrepancy_products?: string[];
}

export interface PlanHeader extends PlanRef {
  dates?: PlanDates;
  distances?: { cutoff_to_count?: number; cutoff_to_month_start?: number; cutoff_to_month_end?: number; count_to_decision?: number; horizon_limit_days?: number };
  params?: PlanParams;
  dataset?: { dataset_id: string; sales_cutoff: string; source_rows?: number; classes?: Record<string, number>; imported_at?: string };
  snapshot?: PlanSnapshotHeader | null;
  confirmations?: PlanConfirmation[];
  assumptions?: PlanAssumption[];
  warnings?: string[];
  provenance?: Record<string, string>;
  method?: string; engine_version?: string;
}

export interface StockDiscrepancyPlan { difference: number | string; system_stock?: number | string; reconstructed?: number | string; compared_at_local?: string }

export interface StockProvenance {
  kind?: PlanSnapshotKind | string;
  base_count?: number | string | null;
  movements_net_to_closing?: number | string | null;
  discrepancy: StockDiscrepancyPlan | null;
}

export interface PlanScenario {
  arrival_date: string | null;
  stock_at_arrival?: string | null;
  purchase_qty: number | null;
  stock_month_start: string | null;
  shortage_before_month: string | null;
  shortage_month: string | null;
  served_month: string | null;
  demand_before_arrival_in_month?: string | null;
  end_stock?: string | null;
  status: PlanStatus;
  reason?: string | null;
  required_arrival_date?: string | null;
}

export interface PlanForecast {
  daily: string | null; daily_exact?: string | null; month_total: string | null; month_days?: number;
  window_start?: string; window_end?: string; sum_28?: string; days_valid?: number;
}

export interface PlanResultItem {
  producto_id: string; producto: string; categoria?: string; unidad_descripcion?: string | null;
  status?: PlanStatus; reason?: string | null;
  forecast: PlanForecast | null;
  count_stock: { libre: number | null; as_of_local?: string | null };
  stock_provenance?: StockProvenance | null;
  scenarios: Record<string, PlanScenario>;
}

export interface PlanResultsPage {
  items: PlanResultItem[]; page: number; page_size: number; total: number; has_more: boolean;
  status_counts?: Partial<Record<PlanStatus | 'all', number>>;
  unavailable_reason?: string | null;
}

export interface PlanStep { label: string; text?: string; value?: string | null }
export interface PlanDailyRow { fecha: string; inicio: string; recepciones: string; disponible?: string; demanda: string; atendida: string; faltante: string; fin: string }

export interface PlanScenarioDetail extends PlanScenario {
  explanation?: PlanStep[];
  breakdown?: Record<string, string | null> | null;
  series?: PlanDailyRow[];
}

export interface PlanResultDetail extends Omit<PlanResultItem, 'scenarios'> {
  scenarios: Record<string, PlanScenarioDetail>;
  pending_orders?: { arrival_date: string; units: number }[];
}

export interface PlanCreateBody {
  month: string; decision_date: string; lead_days: number[]; reserve_days: number; min_order: number; order_multiple: number;
  pending_orders: PlanPendingOrder[];
}

export interface PlanAccepted { plan_id: string; job_id: string; status: JobStatus; reused: boolean }

export interface PlanCompareSide {
  forecast_daily: string | null; month_total: string | null; libre: number | string | null;
  purchase: Record<string, number | string | null>; status?: string | null;
}

export interface PlanCompareItem {
  producto_id: string; producto: string;
  a: PlanCompareSide | null; b: PlanCompareSide | null;
  delta?: { daily?: string | null; month_total?: string | null; purchase?: Record<string, number | string | null> } | null;
}

export interface PlanCompareResponse {
  base?: Partial<PlanRef> & { snapshot?: PlanSnapshotHeader | null };
  other?: Partial<PlanRef> & { snapshot?: PlanSnapshotHeader | null };
  summary?: Record<string, unknown> | null;
  note?: string | null;
  items: PlanCompareItem[];
}
