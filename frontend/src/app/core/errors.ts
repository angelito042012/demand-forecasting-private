import { HttpErrorResponse } from '@angular/common/http';
import { AppError, ErrorCode } from './models';

const KNOWN: ErrorCode[] = [
  'NO_AUTENTICADO', 'SESION_EXPIRADA', 'PROHIBIDO', 'NO_ENCONTRADO', 'ENTRADA_INVALIDA',
  'DEMASIADOS_INTENTOS', 'CSRF_INVALIDO', 'ORIGEN_NO_PERMITIDO', 'AGOSTO_RESERVADO', 'SERVICIO_NO_DISPONIBLE',
];

export const UNAVAILABLE_MSG = 'Servicio no disponible, reintente en unos minutos.';

/** Convierte una respuesta HTTP fallida en un error de aplicación con mensaje en español. */
export function toAppError(e: HttpErrorResponse): AppError {
  const body = (e.error ?? {}) as { error?: { code?: string; message?: string; details?: unknown[] } };
  const raw = body.error;
  const code = raw?.code as ErrorCode | undefined;
  const retry = Number(e.headers?.get?.('Retry-After'));
  const retryAfter = Number.isFinite(retry) && retry > 0 ? retry : undefined;

  if (e.status === 0 || e.status === 502 || e.status === 503 || e.status === 504 || (e.status >= 500 && !raw?.code) || code === 'SERVICIO_NO_DISPONIBLE') {
    // 5xx sin cuerpo de error de la API (p. ej. el proxy no alcanza al servidor) = servicio no disponible
    return { status: e.status, code: e.status === 0 ? 'RED' : 'SERVICIO_NO_DISPONIBLE', message: UNAVAILABLE_MSG };
  }
  if (code === 'SESION_EXPIRADA') return { status: e.status, code, message: 'Su sesión venció. Ingrese de nuevo.' };
  if (e.status === 401) return { status: 401, code: 'NO_AUTENTICADO', message: raw?.message || 'Debe ingresar para continuar.' };
  if (e.status === 403) {
    return { status: 403, code: code ?? 'PROHIBIDO', message: 'No tiene permiso para esta acción.' };
  }
  if (e.status === 429) {
    const espera = retryAfter ? ` Espere ${retryAfter} s antes de reintentar.` : ' Espere unos minutos antes de reintentar.';
    return { status: 429, code: 'DEMASIADOS_INTENTOS', message: 'Demasiados intentos.' + espera, retryAfter };
  }
  if (e.status === 422) {
    return {
      status: 422, code: code ?? 'ENTRADA_INVALIDA',
      message: raw?.message || 'Los datos o filtros enviados no son válidos.', details: raw?.details,
    };
  }
  if (e.status === 404) return { status: 404, code: 'NO_ENCONTRADO', message: raw?.message || 'No se encontró el recurso.' };
  return {
    status: e.status,
    code: code && KNOWN.includes(code) ? code : 'DESCONOCIDO',
    message: raw?.message || 'Ocurrió un error inesperado.',
  };
}
