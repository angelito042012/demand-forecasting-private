import type { JobStatus } from './job';

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

export interface ImportAccepted {
  job_id: string;
  status: JobStatus;
  upload?: { sha256_short?: string; size_bytes?: number; month?: string; label?: string };
  reused?: boolean;
}
