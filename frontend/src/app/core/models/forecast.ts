import type { Page } from './common';
import type { RunHeader, RunQuality } from './run';

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
  pred: { promedio_28: number; rf_categoria_distribuido: number | null; cero: number };
  observed: number | null;
  evaluable: boolean | null;
  provenance: 'OBSERVED_EXCEL';
  run_kind?: string;
}

export interface ForecastPage extends Page<ForecastItem> {
  run?: (RunHeader & RunQuality) | null;
  warnings?: string[];
}
