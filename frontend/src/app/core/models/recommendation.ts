import type { Page } from './common';
import type { RunHeader, RunQuality } from './run';

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
  sum_28?: string | number | null;
  days_28?: number | null;
  mean_28_exact?: string | null;
  transit_breakdown?: { ordered_until_snapshot?: number; received_until_snapshot?: number } | null;
  run?: (RunHeader & RunQuality) | null;
}

export interface RecoPage extends Page<Recommendation> {
  provenance?: string;
  disclaimer?: string;
  nota?: string;
  run?: (RunHeader & RunQuality) | null;
  unavailable_reason?: string;
  see_run?: string | null;
}
