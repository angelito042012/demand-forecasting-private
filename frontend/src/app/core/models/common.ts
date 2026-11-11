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

export type ErrorCode =
  | 'NO_AUTENTICADO' | 'SESION_EXPIRADA' | 'PROHIBIDO' | 'NO_ENCONTRADO' | 'ENTRADA_INVALIDA'
  | 'DEMASIADOS_INTENTOS' | 'CSRF_INVALIDO' | 'ORIGEN_NO_PERMITIDO' | 'FUERA_DE_RANGO'
  | 'SERVICIO_NO_DISPONIBLE' | 'RED' | 'DESCONOCIDO' | 'CORTE_FUERA_DE_RANGO';

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
