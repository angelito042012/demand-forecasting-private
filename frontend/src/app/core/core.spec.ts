import { TestBed } from '@angular/core/testing';
import { Component } from '@angular/core';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Router, provideRouter } from '@angular/router';
import { ApiService } from './api.service';
import { AuthService } from './auth.service';
import { authGuard } from './auth.guard';
import { apiInterceptor } from './http.interceptor';
import { demoInterceptor } from './demo';
import { AppError } from './models';
import { calcSteps } from './reco-calc';
import { isStaleAge } from './age';
import { recoNoSnap, recoOk, session } from '../testing/fixtures';

@Component({ template: '' })
class Dummy {}

let ctl: HttpTestingController | null = null;

function setup() {
  TestBed.configureTestingModule({
    providers: [
      provideHttpClient(withInterceptors([apiInterceptor, demoInterceptor])),
      provideHttpClientTesting(),
      provideRouter([
        { path: 'acceso', component: Dummy },
        { path: 'privada', component: Dummy, canActivate: [authGuard] },
      ]),
    ],
  });
  ctl = TestBed.inject(HttpTestingController);
  return { http: ctl, auth: TestBed.inject(AuthService), api: TestBed.inject(ApiService), router: TestBed.inject(Router) };
}

const err = (e: unknown) => e as AppError;

afterEach(() => { ctl?.verify(); ctl = null; });

describe('autenticación', () => {
  it('login correcto: guarda sesión en memoria, csrf en memoria y nada en storage', () => {
    const { http, auth } = setup();
    auth.login('ana', 'clave-larga-123').subscribe();
    const r = http.expectOne('/api/v1/auth/login');
    expect(r.request.method).toBe('POST');
    expect(r.request.withCredentials).toBe(true);
    expect(r.request.headers.has('X-CSRF-Token')).toBe(false);
    expect(r.request.body).toEqual({ username: 'ana', password: 'clave-larga-123' });
    r.flush(session);
    expect(auth.session()?.username).toBe('ana');
    expect(auth.csrfToken).toBe('csrf-123');
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
  });

  it('login incorrecto: error 401 sin sesión', () => {
    const { http, auth } = setup();
    let e: AppError | undefined;
    auth.login('ana', 'mala').subscribe({ error: (x) => (e = x) });
    http.expectOne('/api/v1/auth/login').flush({ error: { code: 'NO_AUTENTICADO', message: 'Credenciales incorrectas' } }, { status: 401, statusText: 'x' });
    expect(e?.status).toBe(401);
    expect(auth.session()).toBeNull();
  });

  it('login con 429 muestra espera y Retry-After', () => {
    const { http, auth } = setup();
    let e: AppError | undefined;
    auth.login('ana', 'x').subscribe({ error: (x) => (e = x) });
    http.expectOne('/api/v1/auth/login').flush({ error: { code: 'DEMASIADOS_INTENTOS', message: 'm' } }, { status: 429, statusText: 'x', headers: { 'Retry-After': '120' } });
    expect(e?.code).toBe('DEMASIADOS_INTENTOS');
    expect(e?.retryAfter).toBe(120);
    expect(e?.message).toContain('120');
  });

  it('logout (mutación) envía X-CSRF-Token y withCredentials', () => {
    const { http, auth } = setup();
    auth.session.set(session);
    auth.logout().subscribe();
    const r = http.expectOne('/api/v1/auth/logout');
    expect(r.request.method).toBe('POST');
    expect(r.request.headers.get('X-CSRF-Token')).toBe('csrf-123');
    expect(r.request.withCredentials).toBe(true);
    expect(r.request.body).toEqual({});
    expect(r.request.detectContentTypeHeader()).toBe('application/json');
    r.flush(null, { status: 204, statusText: 'No Content' });
    expect(auth.session()).toBeNull();
  });

  it('las lecturas (GET) no llevan X-CSRF-Token pero sí credenciales', () => {
    const { http, auth, api } = setup();
    auth.session.set(session);
    api.health().subscribe();
    const r = http.expectOne('/api/v1/health');
    expect(r.request.headers.has('X-CSRF-Token')).toBe(false);
    expect(r.request.withCredentials).toBe(true);
    r.flush({ status: 'ok', database: 'ok', version: 't' });
  });
});

describe('guard de rutas', () => {
  it('con sesión válida (GET /auth/me 200) permite entrar', async () => {
    const { http, router } = setup();
    const nav = router.navigateByUrl('/privada');
    await new Promise((r) => setTimeout(r, 0));
    http.expectOne('/api/v1/auth/me').flush(session);
    expect(await nav).toBe(true);
    expect(router.url).toBe('/privada');
  });

  it('sin sesión (401) redirige a /acceso', async () => {
    const { http, router, auth } = setup();
    const nav = router.navigateByUrl('/privada');
    await new Promise((r) => setTimeout(r, 0));
    http.expectOne('/api/v1/auth/me').flush({ error: { code: 'NO_AUTENTICADO', message: 'm' } }, { status: 401, statusText: 'x' });
    await nav;
    expect(router.url).toBe('/acceso');
    expect(auth.session()).toBeNull();
  });

  it('401 SESION_EXPIRADA en datos: limpia sesión, avisa «su sesión venció» y va a /acceso', async () => {
    const { http, router, auth, api } = setup();
    auth.session.set(session);
    let e: AppError | undefined;
    api.runs(1, 50).subscribe({ error: (x) => (e = x) });
    http.expectOne((r) => r.url === '/api/v1/runs').flush({ error: { code: 'SESION_EXPIRADA', message: 'm' } }, { status: 401, statusText: 'x' });
    await new Promise((r) => setTimeout(r, 0));
    expect(err(e).code).toBe('SESION_EXPIRADA');
    expect(auth.session()).toBeNull();
    expect(auth.notice()).toContain('sesión venció');
    expect(router.url).toBe('/acceso');
  });

  it('503 al verificar sesión: redirige a acceso con aviso de servicio no disponible', async () => {
    const { http, router, auth } = setup();
    const nav = router.navigateByUrl('/privada');
    await new Promise((r) => setTimeout(r, 0));
    http.expectOne('/api/v1/auth/me').flush({}, { status: 503, statusText: 'x' });
    await nav;
    expect(router.url).toBe('/acceso');
    expect(auth.notice()).toContain('Servicio no disponible');
  });
});

describe('mapeo de errores', () => {
  const cases: [number, object | string, string][] = [
    [403, { error: { code: 'PROHIBIDO', message: 'x' } }, 'PROHIBIDO'],
    [422, { error: { code: 'AGOSTO_RESERVADO', message: 'agosto de 2026 está reservado para la prueba final' } }, 'AGOSTO_RESERVADO'],
    [503, { error: { code: 'SERVICIO_NO_DISPONIBLE', message: 'interno' } }, 'SERVICIO_NO_DISPONIBLE'],
    [404, { error: { code: 'NO_ENCONTRADO', message: 'no' } }, 'NO_ENCONTRADO'],
    [500, 'proxy sin cuerpo JSON', 'SERVICIO_NO_DISPONIBLE'],
    [500, { error: { code: 'ERROR_INTERNO', message: 'Error interno.' } }, 'DESCONOCIDO'],
  ];
  it.each(cases)('status %i -> %s', (status, body, code) => {
    const { http, api } = setup();
    let e: AppError | undefined;
    api.health().subscribe({ error: (x) => (e = x) });
    http.expectOne('/api/v1/health').flush(body, { status, statusText: 'x' });
    expect(e?.code).toBe(code);
    if (status === 503 || typeof body === 'string') expect(e?.message).toContain('Servicio no disponible');
    if (status === 403) expect(e?.message).toContain('permiso');
  });

  it('error de red (status 0) -> RED con mensaje de servicio no disponible', () => {
    const { http, api } = setup();
    let e: AppError | undefined;
    api.health().subscribe({ error: (x) => (e = x) });
    http.expectOne('/api/v1/health').error(new ProgressEvent('error'));
    expect(e?.code).toBe('RED');
    expect(e?.message).toContain('Servicio no disponible');
  });
});

describe('parámetros de consulta', () => {
  it('pronósticos: solo envía filtros con valor, con nombres del contrato', () => {
    const { http, api } = setup();
    api.forecasts({ level: 'categoria', categoria: 'CAT-T', cohorte: 'C1', from: '2026-07-11', to: '2026-07-20', page: 2, page_size: 25, sort: '-target_date' }).subscribe();
    const r = http.expectOne((x) => x.url === '/api/v1/forecasts');
    const p = r.request.params;
    expect(p.get('level')).toBe('categoria');
    expect(p.get('categoria')).toBe('CAT-T');
    expect(p.get('cohorte')).toBe('C1');
    expect(p.get('from')).toBe('2026-07-11');
    expect(p.get('to')).toBe('2026-07-20');
    expect(p.get('page')).toBe('2');
    expect(p.get('page_size')).toBe('25');
    expect(p.get('sort')).toBe('-target_date');
    expect(p.has('sku')).toBe(false);
    r.flush({ items: [], page: 2, page_size: 25, total: 0, has_more: false });
  });

  it('recomendaciones: only_orders solo si está activo; el SKU del detalle se codifica', () => {
    const { http, api } = setup();
    api.recommendations({ only_orders: true, status: 'ok', page: 1, page_size: 50, sort: '-order_qty' }).subscribe();
    const r = http.expectOne((x) => x.url === '/api/v1/recommendations');
    expect(r.request.params.get('only_orders')).toBe('true');
    expect(r.request.params.get('status')).toBe('ok');
    r.flush({ items: [], page: 1, page_size: 50, total: 0, has_more: false });
    api.recommendations({ only_orders: false, page: 1, page_size: 50 }).subscribe();
    const r2 = http.expectOne((x) => x.url === '/api/v1/recommendations');
    expect(r2.request.params.has('only_orders')).toBe(false);
    r2.flush({ items: [], page: 1, page_size: 50, total: 0, has_more: false });
    api.recommendation('A/B C', 'run-1').subscribe();
    const r3 = http.expectOne((x) => x.url === '/api/v1/recommendations/A%2FB%20C');
    expect(r3.request.params.get('almacen')).toBe('1');
    r3.flush(recoOk);
  });

  it('resumen de ventas usa group_by y categoría', () => {
    const { http, api } = setup();
    api.salesSummary('2026-06-01', '2026-07-31', 'category', 'CAT-T').subscribe();
    const r = http.expectOne((x) => x.url === '/api/v1/sales/summary');
    expect(r.request.params.get('group_by')).toBe('category');
    expect(r.request.params.get('from')).toBe('2026-06-01');
    r.flush({});
  });
});

describe('cálculo de recomendación (fixture del contrato)', () => {
  it('muestra pasos coherentes: posición, objetivo y pedido', () => {
    const c = calcSteps(recoOk)!;
    expect(c.steps.map((s) => s.value)).toEqual([10, 5, 15, 28, 14, 42, 27]);
    expect(c.check).toEqual({ position: true, target: true, order: true });
  });
  it('detecta valores publicados incoherentes', () => {
    expect(calcSteps({ ...recoOk, order_qty: 99 })!.check.order).toBe(false);
  });
  it('sin_snapshot no genera cálculo ni stock cero', () => {
    expect(calcSteps(recoNoSnap)).toBeNull();
  });
});

describe('antigüedad', () => {
  it('marca corrida antigua según age_days_at_view', () => {
    expect(isStaleAge(99)).toBe(true);
    expect(isStaleAge(3)).toBe(false);
    expect(isStaleAge(null)).toBe(true);
  });
});
