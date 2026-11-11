export type JobType = 'import_excel' | 'generate_run' | 'generate_plan';
export type JobStatus = 'queued' | 'running' | 'completed' | 'failed';

export interface JobError { code: string; message?: string; retryable?: boolean; attempt?: number; at?: string }

export interface JobResult {
  outcome?: 'importado' | 'sin_cambios' | string;
  import_id?: string;
  estado?: string;
  filas_leidas?: number;
  ventas?: number;
  notas_credito?: number;
  rechazadas?: number;
  rechazos_por_motivo?: Record<string, number>;
  insertadas?: number;
  ya_existentes?: number;
  en_conflicto?: number;
  run_id?: string;
  [k: string]: unknown;
}

export interface PublicJob {
  job_id: string;
  type: JobType;
  status: JobStatus;
  stage?: string | null;
  progress?: Record<string, unknown> | null;
  result?: JobResult | null;
  error?: JobError | null;
  created_at?: string;
  updated_at?: string;
  started_at?: string | null;
  finished_at?: string | null;
  attempts?: number;
  max_attempts?: number;
  links?: { import?: string; run?: string } | null;
}
