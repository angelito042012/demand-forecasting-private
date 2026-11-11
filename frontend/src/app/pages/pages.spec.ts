import { Type } from '@angular/core';
import { TestBed, ComponentFixture } from '@angular/core/testing';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting, TestRequest } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { apiInterceptor } from '../core/interceptors';
import { demoInterceptor } from '../core/interceptors';
import { ImportsPage } from './imports.page';
import { RunsPage } from './runs.page';
import { ForecastsPage } from './forecasts.page';
import { RecommendationsPage } from './recommendations.page';
import { SummaryPage } from './summary.page';
import { SystemPage } from './system.page';
import { LoginPage } from './login.page';
import { forecast, page, recoNoSnap, recoOk, runDetail, runSummary } from '../testing/fixtures';

let http: HttpTestingController;

function mount<T>(cmp: Type<T>) {
  TestBed.configureTestingModule({
    imports: [cmp],
    providers: [provideHttpClient(withInterceptors([apiInterceptor, demoInterceptor])), provideHttpClientTesting(), provideRouter([{ path: 'acceso', component: LoginPage }])],
  });
  http = TestBed.inject(HttpTestingController);
  const f = TestBed.createComponent(cmp);
  f.detectChanges();
  return f;
}
const el = (f: ComponentFixture<unknown>) => f.nativeElement as HTMLElement;
const state = (f: ComponentFixture<unknown>) => el(f).querySelector('[data-state]')?.getAttribute('data-state');
const req = (path: string): TestRequest => http.expectOne((r) => r.url === path);
async function flush(r: TestRequest, body: unknown, f: ComponentFixture<unknown>, status = 200) {
  if (status === 200) r.flush(body as object);
  else r.flush(body as object, { status, statusText: 'x' });
  f.detectChanges();
  await f.whenStable();
  f.detectChanges();
}
afterEach(() => http?.verify());

describe('estados cargando / sin datos / error / sesión vencida (Pronósticos como ejemplo)', () => {
  it('cargando, luego sin datos', async () => {
    const f = mount(ForecastsPage);
    http.match((r) => r.url === '/api/v1/runs').forEach((r) => r.flush(page([])));
    expect(state(f)).toBe('loading');
    await flush(req('/api/v1/forecasts'), page([]), f);
    expect(state(f)).toBe('empty');
  });

  it('error 503: mensaje de servicio no disponible, con reintento y SIN datos de relleno', async () => {
    const f = mount(ForecastsPage);
    http.match((r) => r.url === '/api/v1/runs').forEach((r) => r.flush(page([])));
    await flush(req('/api/v1/forecasts'), {}, f, 503);
    expect(state(f)).toBe('error');
    expect(el(f).textContent).toContain('Servicio no disponible');
    expect(el(f).querySelector('table')).toBeNull();
    expect(el(f).textContent).not.toContain('DEMOSTRACIÓN');
    el(f).querySelector('button')!.click();
    await flush(req('/api/v1/forecasts'), page([forecast]), f);
    expect(state(f)).toBe('data');
  });

  it('sesión vencida: mensaje «su sesión venció»', async () => {
    const f = mount(ForecastsPage);
    http.match((r) => r.url === '/api/v1/runs').forEach((r) => r.flush(page([])));
    await flush(req('/api/v1/forecasts'), { error: { code: 'SESION_EXPIRADA', message: 'm' } }, f, 401);
    expect(state(f)).toBe('error');
    expect(el(f).textContent?.toLowerCase()).toContain('sesión venció');
  });
});

describe('Pronósticos', () => {
  it('muestra tres series, banner de corrida con antigüedad y corrida antigua; filtros -> query; paginación', async () => {
    const f = mount(ForecastsPage);
    req('/api/v1/runs').flush(page([runSummary]));
    await flush(req('/api/v1/forecasts'), page([forecast, { ...forecast, entity_id: 'SKU-T2', evaluable: false, observed: null }], { total: 120, has_more: true }), f);
    const t = el(f).textContent!;
    expect(el(f).querySelector('[data-testid="analysis-name"]')?.textContent).toBe('Ejemplo de julio');
    expect(el(f).querySelector('[data-testid="analysis-used"]')?.textContent).toContain('hace 99 días');
    expect(t).toContain('Cantidad estimada');
    expect(t).toContain('modelo experimental que no resultó mejor');
    expect(t).not.toContain('Control (siempre cero)');
    (el(f).querySelector('[data-testid="toggle-details"]') as HTMLButtonElement).click();
    f.detectChanges();
    expect(el(f).textContent).toContain('Control (siempre cero)');
    expect(el(f).querySelector('[data-testid="insufficient"]')).toBeTruthy();
    expect(el(f).querySelectorAll('[data-testid="forecast-table"] tbody tr').length).toBe(2);

    // paginación -> page=2
    (el(f).querySelector('[data-testid="next"]') as HTMLButtonElement).click();
    const r2 = req('/api/v1/forecasts');
    expect(r2.request.params.get('page')).toBe('2');
    await flush(r2, page([forecast], { page: 2, total: 120 }), f);

    // filtros -> query (vuelve a página 1)
    const inputs = el(f).querySelectorAll('form.filters input');
    const sku = Array.from(inputs).find((i) => (i as HTMLInputElement).name === 'sku') as HTMLInputElement;
    sku.value = 'SKU-T1';
    sku.dispatchEvent(new Event('input'));
    f.detectChanges();
    (el(f).querySelector('form.filters') as HTMLFormElement).dispatchEvent(new Event('submit'));
    const r3 = req('/api/v1/forecasts');
    expect(r3.request.params.get('sku')).toBe('SKU-T1');
    expect(r3.request.params.get('page')).toBe('1');
    expect(r3.request.params.get('level')).toBe('sku');
    await flush(r3, page([forecast]), f);
  });
});

describe('Recomendaciones', () => {
  const runs = () => http.match((r) => r.url === '/api/v1/runs').forEach((r) => r.flush(page([runSummary])));
  it('etiqueta de inventario simulado, scenario_id, SKU sin inventario con qué falta (nunca stock cero) y cálculo', async () => {
    const f = mount(RecommendationsPage);
    runs();
    await flush(req('/api/v1/recommendations'), page([recoOk, recoNoSnap]), f);
    const t = el(f).textContent!;
    expect(el(f).querySelector('[data-testid="sim-notice"]')?.textContent).toContain('Inventario simulado con supuestos; no corresponde al inventario real de la empresa');
    expect(el(f).querySelector('[data-testid="scenario-id"]')?.textContent).toBe('T07_L7_S7_promedio_28_2026-07-10');
    const ns = el(f).querySelector('[data-testid="sin-snapshot"]')!;
    expect(ns.textContent).toContain('Sin datos de inventario');
    expect(ns.textContent).toContain('Qué información falta');
    expect(ns.textContent).toContain('SIN_INVENTARIO_SIMULADO_AL_10_07');
    expect(ns.textContent?.toLowerCase()).toContain('no se supone stock cero');
    expect(ns.textContent).not.toMatch(/0/);
    expect(t).toContain('Cantidad sugerida');

    // detalle del SKU con inventario: cálculo paso a paso (completo, plegado) y resumen en tres pasos
    (el(f).querySelector('[data-testid="reco-table"] tbody button') as HTMLButtonElement).click();
    const d = req('/api/v1/recommendations/SKU-T1');
    await flush(d, { ...recoOk, explanation: 'Texto del servidor' }, f);
    expect(el(f).querySelectorAll('[data-testid="simple-steps"] > li').length).toBe(3);
    const steps = Array.from(el(f).querySelectorAll('[data-testid="calc-steps"] li')).map((x) => x.textContent!);
    expect(steps.length).toBe(9);
    expect(steps[0]).toContain('Stock simulado');
    expect(steps[1]).toContain('tránsito');
    expect(steps[4]).toContain('28');
    expect(steps[5]).toContain('7 ×');
    expect(steps[6]).toContain('42');
    expect(steps[7]).toContain('27');
    expect(el(f).querySelector('[data-testid="incoherent"]')).toBeNull();
    expect(el(f).querySelector('[data-testid="reco-dates"]')?.textContent).toContain('10/07/2026');
    expect(el(f).textContent).toContain('Texto del servidor');
  });

  it('detalle sin snapshot: qué falta, sin pedido ni stock 0', async () => {
    const f = mount(RecommendationsPage);
    runs();
    await flush(req('/api/v1/recommendations'), page([recoNoSnap]), f);
    (el(f).querySelector('[data-testid="sin-snapshot"] button') as HTMLButtonElement).click();
    await flush(req('/api/v1/recommendations/SKU-NEW'), recoNoSnap, f);
    expect(el(f).querySelector('[data-testid="calc-steps"]')).toBeNull();
    expect(el(f).querySelector('[data-testid="detail-nosnap"]')?.textContent).toContain('No se supone stock cero');
  });

  it('filtros: categoría, vista y orden se envían al servidor (vista inicial: sugerencias, status=ok y only_orders=true)', async () => {
    const f = mount(RecommendationsPage);
    runs();
    const first = req('/api/v1/recommendations');
    expect(first.request.params.get('status')).toBe('ok');
    expect(first.request.params.get('only_orders')).toBe('true');
    await flush(first, page([recoOk]), f);
    const form = el(f).querySelector('form.filters') as HTMLFormElement;
    const set = (name: string, v: string) => {
      const i = form.querySelector(`[name="${name}"]`) as HTMLInputElement & HTMLSelectElement;
      i.value = v; i.dispatchEvent(new Event(i.tagName === 'SELECT' ? 'change' : 'input'));
    };
    set('cat', 'CAT-T'); set('sort', '-order_qty');
    f.detectChanges();
    form.dispatchEvent(new Event('submit'));
    const r = req('/api/v1/recommendations');
    expect(r.request.params.get('categoria')).toBe('CAT-T');
    expect(r.request.params.get('status')).toBe('ok');
    expect(r.request.params.get('only_orders')).toBe('true');
    expect(r.request.params.get('sort')).toBe('-order_qty');
    await flush(r, page([recoOk]), f);
  });
});

describe('Importaciones', () => {
  it('el lector (sin sesión de administrador) no ve controles de carga ni pide /jobs', async () => {
    const f = mount(ImportsPage);
    await flush(req('/api/v1/imports'), page([]), f);
    expect(state(f)).toBe('empty');
    expect(el(f).querySelector('[data-testid="readonly-note"]')?.textContent).toContain('solo lectura');
    expect(el(f).querySelector('input[type="file"]')).toBeNull();
    expect(Array.from(el(f).querySelectorAll('button')).some((b) => /cargar|subir/i.test(b.textContent!))).toBe(false);
  });
});

describe('Corridas', () => {
  it('tarjeta con nombre, fechas y estado; detalles técnicos plegados con método elegido, RF comparador experimental y control', async () => {
    const f = mount(RunsPage);
    await flush(req('/api/v1/runs'), page([runSummary]), f);
    const card = el(f).querySelector('[data-testid="runs-list"]')!.textContent!;
    expect(card).toContain('Ejemplo de julio');
    expect(card).toContain('En uso por defecto');
    expect(card).toContain('10 de julio de 2026');
    const tech = el(f).querySelector('[data-testid="tech-run-test-1"]') as HTMLDetailsElement;
    expect(tech.open).toBe(false);
    tech.open = true;
    tech.dispatchEvent(new Event('toggle'));
    await flush(req('/api/v1/runs/run-test-1'), runDetail, f);
    const m = el(f).querySelector('[data-testid="method"]')!.textContent!;
    expect(m).toContain('promedio_28');
    expect(m).toContain('comparador experimental');
    expect(m).toContain('no ganó');
    expect(m).toContain('control');
    expect(el(f).querySelector('[data-testid="coverage"]')?.textContent).toContain('SKU sin inventario simulado: 4');
    expect(el(f).querySelector('[data-testid="run-doc"]')).toBeTruthy();
  });
});

describe('Resumen', () => {
  it('muestra notas de crédito aparte, días excluidos y unidades/moneda del contrato', async () => {
    const f = mount(SummaryPage);
    await flush(req('/api/v1/sales/summary'), {
      provenance: 'OBSERVED_EXCEL', unit: 'unidad base', currency: 'PEN', from: '2026-06-01', to: '2026-07-31',
      items: [{ key: '2026-06', lineas_venta: 1, unidades: 2, importe_pen: 3 }],
      notas_credito: { lineas: 4, importe_pen: 5 }, excluded_days: [{ fecha: '2026-06-07', motivo: 'excluido del entrenamiento y métricas; no se informa como venta cero' }],
    }, f);
    expect(el(f).querySelector('[data-testid="credit-notes"]')?.textContent).toContain('4 línea(s)');
    expect(el(f).textContent).toContain('no netas');
    expect(el(f).querySelector('[data-testid="excluded"]')?.textContent).toContain('7 de junio de 2026');
    expect(el(f).querySelector('[data-testid="excluded"]')?.textContent).toContain('no se informa como venta cero');
    expect(el(f).textContent).toContain('OBSERVED_EXCEL');
  });
  it('rango fuera de alcance -> error 422 mostrado, sin tabla', async () => {
    const f = mount(SummaryPage);
    await flush(req('/api/v1/sales/summary'), { error: { code: 'FUERA_DE_RANGO', message: 'La fecha solicitada excede el último día de datos permitido.' } }, f, 422);
    expect(state(f)).toBe('error');
    expect(el(f).textContent).toContain('La fecha solicitada excede');
  });
});

describe('Sistema', () => {
  it('muestra salud del servidor; fallo -> error, no «ok» inventado', async () => {
    const f = mount(SystemPage);
    await flush(req('/api/v1/health'), {}, f, 503);
    expect(state(f)).toBe('error');
    expect(el(f).textContent).not.toContain('operativo');
  });
  it('salud ok', async () => {
    const f = mount(SystemPage);
    await flush(req('/api/v1/health'), { status: 'ok', database: 'ok', version: 'v-test' }, f);
    expect(el(f).querySelector('[data-testid="health"]')?.textContent).toContain('v-test');
  });
});

describe('Acceso', () => {
  it('credenciales incorrectas -> mensaje, contraseña limpiada', async () => {
    const f = mount(LoginPage);
    const c = el(f);
    const set = (n: string, v: string) => { const i = c.querySelector(`[name="${n}"]`) as HTMLInputElement; i.value = v; i.dispatchEvent(new Event('input')); };
    set('username', 'ana'); set('password', 'mala');
    f.detectChanges();
    (c.querySelector('form') as HTMLFormElement).dispatchEvent(new Event('submit'));
    req('/api/v1/auth/login').flush({ error: { code: 'NO_AUTENTICADO', message: 'x' } }, { status: 401, statusText: 'x' });
    f.detectChanges();
    expect(c.querySelector('[data-testid="login-error"]')?.textContent).toContain('incorrectos');
  });
});

describe('sin fallback silencioso ni mocks fuera de ?demo=1', () => {
  it('ninguna pantalla contiene el texto de demostración si la API responde con error', async () => {
    for (const cmp of [ImportsPage, RunsPage, SummaryPage, RecommendationsPage, SystemPage] as Type<unknown>[]) {
      TestBed.resetTestingModule();
      const f = mount(cmp);
      http.match(() => true).forEach((r) => r.flush({}, { status: 503, statusText: 'x' }));
      f.detectChanges();
      expect(el(f).textContent).not.toMatch(/DEMOSTRACIÓN|demo/i);
      expect(el(f).querySelector('[data-state="error"]')).toBeTruthy();
    }
  });
});
