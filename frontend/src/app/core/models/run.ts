export interface RunHeader {
  run_id: string;
  run_label: string;
  cutoff: string;
  generated_at: string;
  published_at: string;
  age_days_at_view: number;
  is_active: boolean;
  kind?: string;
  target_start?: string | null;
  target_end?: string | null;
  evaluation_period?: Record<string, unknown> | null;
  warnings?: string[];
}

export interface FinalPackage {
  seal_sha256?: string | null;
  seal_short?: string | null;
  frozen_selection_sha256?: string | null;
  phases?: Record<string, string | { estado?: string; [k: string]: unknown }>;
  corrections?: (string | Record<string, unknown>)[];
  audit_ok?: boolean | null;
}

export interface QualityIssue {
  superseded_by?: string;
  reason?: string;
  message?: string;
  code?: string;
  [k: string]: unknown;
}

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
  final_package?: FinalPackage | null;
}

export interface RunDetail extends RunHeader, RunQuality {
  kind?: string;
  origin?: string;
  target_start?: string;
  target_end?: string;
  horizon_days?: number;
  provenance?: string;
  disclaimer?: string;
  fingerprint_short?: string;
  method: { chosen: string; comparator: string; control: string; note?: string; rf_declared_winner?: boolean; category_baseline?: string };
  final_package?: FinalPackage | null;
  config?: Record<string, unknown>;
  sources?: unknown;
  artifacts?: { name: string; sha256: string; size?: number; size_bytes?: number }[];
  code?: { commit: string };
  counts?: Record<string, number>;
  coverage?: { skus_pronosticados?: number; skus_con_recomendacion?: number; skus_sin_snapshot?: number; categorias?: number; skus_categoria_desconocida?: number; [k: string]: unknown };
  evaluation_period?: { start?: string; end?: string } | Record<string, unknown>;
  provenance_notes?: string[] | string;
}

export interface RunAccepted { job_id: string; status: import('./job').JobStatus; origin: string; horizon_days: number; method: string }

export interface RunOptions {
  origin_min: string;
  origin_max: string;
  origin_default: string;
  horizon_max: number;
  methods: string[];
  development_policy?: boolean;
}
