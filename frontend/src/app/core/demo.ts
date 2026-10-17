import { Injectable, isDevMode } from '@angular/core';
import { HttpErrorResponse, HttpInterceptorFn, HttpResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { Observable, delay, of, throwError } from 'rxjs';

/**
 * Modo demostración: SOLO con bandera explícita `?demo=1` y SOLO en compilación de desarrollo.
 * Nunca se activa por un fallo de la API ni de forma silenciosa.
 */
@Injectable({ providedIn: 'root' })
export class DemoMode {
  readonly enabled: boolean =
    isDevMode() && typeof location !== 'undefined' && new URLSearchParams(location.search).get('demo') === '1';
}

const DEMO_LABEL = 'DEMOSTRACIÓN – datos ficticios, no son resultados reales';

function fixture(url: string): unknown | undefined {
  const path = url.replace(/^\/api\/v1/, '').split('?')[0];
  if (path === '/auth/me') {
    return { username: 'demo', role: 'lector', csrf_token: 'demo', expires_at: '2099-01-01T00:00:00Z', idle_expires_at: '2099-01-01T00:00:00Z' };
  }
  if (path === '/health') return { status: 'ok', database: 'ok', version: 'demo' };
  if (path === '/runs') {
    return {
      items: [{ run_id: 'demo-run', run_label: DEMO_LABEL, cutoff: '1970-01-01', generated_at: '1970-01-01T00:00:00Z', published_at: '1970-01-01T00:00:00Z', age_days_at_view: 0, is_active: true }],
      page: 1, page_size: 50, total: 1, has_more: false,
    };
  }
  if (path === '/imports') return { items: [], page: 1, page_size: 50, total: 0, has_more: false };
  return undefined;
}

/** Interceptor de demostración: responde con fixtures solo si DemoMode.enabled; si no, no hace nada. */
export const demoInterceptor: HttpInterceptorFn = (req, next): Observable<any> => {
  if (!inject(DemoMode).enabled || !req.url.startsWith('/api/')) return next(req);
  if (req.method === 'POST' && req.url.endsWith('/auth/logout')) return of(new HttpResponse({ status: 204 }));
  const body = fixture(req.url);
  if (body === undefined) {
    return throwError(
      () => new HttpErrorResponse({ status: 404, url: req.url, error: { error: { code: 'NO_ENCONTRADO', message: 'Esta pantalla no tiene datos en el modo demostración.' } } }),
    );
  }
  return of(new HttpResponse({ status: 200, body })).pipe(delay(150));
};
