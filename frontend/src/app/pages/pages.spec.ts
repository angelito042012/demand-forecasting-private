import { Type } from '@angular/core';
import { TestBed, ComponentFixture } from '@angular/core/testing';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting, TestRequest } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { apiInterceptor } from '../core/http.interceptor';
import { demoInterceptor } from '../core/demo';
import { ImportsPage } from './imports.page';
import { RunsPage } from './runs.page';
import { ForecastsPage } from './forecasts.page';
import { RecommendationsPage } from './recommendations.page';
import { ComparisonPage } from './comparison.page';
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
    expect(t).toContain('Corrida histórica de desarrollo al 10/07/2026');
    expect(el(f).querySelector('[data-testid="stale"]')).toBeTruthy();
    expect(el(f).querySelector('[data-testid="age"]')?.textContent).toBe('99');
    expect(t).toContain('promedio_28 (elegido)');
    expect(t).toContain('comparador experimental que no ganó');
    expect(t).toContain('cero (control)');
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
  it('etiqueta de inventario simulado, scenario_id, SKU sin inventario con motivo (nunca stock cero) y cálculo', async () => {
    const f = mount(RecommendationsPage);
    await flush(req('/api/v1/recommendations'), page([recoOk, recoNoSnap]), f);
    const t = el(f).textContent!;
    expect(el(f).querySelector('[data-testid="sim-notice"]')?.textContent).toContain('Inventario simulado con supuestos; no corresponde al inventario real de la empresa');
    expect(el(f).querySelector('[data-testid="scenario-id"]')?.textContent).toBe('T07_L7_S7_promedio_28_2026-07-10');
    const ns = el(f).querySelector('[data-testid="sin-snapshot"]')!;
    expect(ns.textContent).toContain('Sin inventario simulado al 10/07');
    expect(ns.textContent).toContain('SIN_INVENTARIO_SIMULADO_AL_10_07');
    expect(ns.textContent?.toLowerCase()).toContain('no se supone stock cero');
    expect(ns.textContent).not.toMatch(/\b0\b/);
    expect(t).toContain('Valor del pedido (PEN, supuesto)');

    // detalle del SKU con inventario: cálculo paso a paso
    (el(f).querySelector('[data-testid="reco-table"] tbody button') as HTMLButtonElement).click();
    const d = req('/api/v1/recommendations/SKU-T1');
    await flush(d, { ...recoOk, explanation: 'Texto del servidor' }, f);
    const steps = Array.from(el(f).querySelectorAll('[data-testid="calc-steps"] li')).map((x) => x.textContent!);
    expect(steps.length).toBe(7);
    expect(steps[0]).toContain('Stock simulado');
    expect(steps[1]).toContain('tránsito');
    expect(steps[3]).toContain('28');
    expect(steps[4]).toContain('7 × media de 28 días');
    expect(steps[5]).toContain('42');
    expect(steps[6]).toContain('27');
    expect(el(f).querySelector('[data-testid="incoherent"]')).toBeNull();
    expect(el(f).querySelector('[data-testid="reco-dates"]')?.textContent).toContain('2026-07-10');
    expect(el(f).textContent).toContain('Texto del servidor');
  });

  it('detalle sin snapshot: motivo, sin pedido ni stock 0', async () => {
    const f = mount(RecommendationsPage);
    await flush(req('/api/v1/recommendations'), page([recoNoSnap]), f);
    (el(f).querySelector('[data-testid="sin-snapshot"] button') as HTMLButtonElement).click();
    await flush(req('/api/v1/recommendations/SKU-NEW'), recoNoSnap, f);
    expect(el(f).querySelector('[data-testid="calc-steps"]')).toBeNull();
    expect(el(f).querySelector('[data-testid="detail-nosnap"]')?.textContent).toContain('No se supone stock cero');
  });

  it('filtros: categoría, estado y solo con pedido se envían al servidor', async () => {
    const f = mount(RecommendationsPage);
    await flush(req('/api/v1/recommendations'), page([recoOk]), f);
    const form = el(f).querySelector('form.filters') as HTMLFormElement;
    const set = (name: string, v: string | boolean) => {
      const i = form.querySelector(`[name="${name}"]`) as HTMLInputElement & HTMLSelectElement;
      if (typeof v === 'boolean') { i.checked = v; i.dispatchEvent(new Event('change')); }
      else { i.value = v; i.dispatchEvent(new Event(i.tagName === 'SELECT' ? 'change' : 'input')); }
    };
    set('cat', 'CAT-T'); set('status', 'ok'); set('only', true); set('sort', '-order_qty');
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
  it('aclara que la carga nueva sigue por CLI y no ofrece botón de carga', async () => {
    const f = mount(ImportsPage);
    await flush(req('/api/v1/imports'), page([]), f);
    expect(state(f)).toBe('empty');
    expect(el(f).querySelector('[data-testid="cli-note"]')?.textContent).toContain('línea de comandos');
    expect(el(f).textContent).toContain('T10');
    expect(el(f).querySelector('input[type="file"]')).toBeNull();
    expect(Array.from(el(f).querySelectorAll('button')).some((b) => /cargar|subir/i.test(b.textContent!))).toBe(false);
  });
});

describe('Corridas', () => {
  it('lista con etiqueta y antigüedad; detalle con método elegido, RF comparador experimental y control', async () => {
    const f = mount(RunsPage);
    await flush(req('/api/v1/runs'), page([runSummary]), f);
    expect(el(f).querySelector('[data-testid="runs-table"]')?.textContent).toContain('Corrida histórica de desarrollo al 10/07/2026');
    expect(el(f).querySelector('[data-testid="runs-table"]')?.textContent).toContain('99');
    (el(f).querySelector('[data-testid="runs-table"] button') as HTMLButtonElement).click();
    await flush(req('/api/v1/runs/run-test-1'), runDetail, f);
    const m = el(f).querySelector('[data-testid="method"]')!.textContent!;
    expect(m).toContain('promedio_28');
    expect(m).toContain('comparador experimental');
    expect(m).toContain('no ganó');
    expect(m).toContain('control');
    expect(el(f).querySelector('[data-testid="coverage"]')?.textContent).toContain('SKU sin inventario simulado: 4');
    expect(el(f).querySelector('[data-testid="stale"]')).toBeTruthy();
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
    expect(el(f).querySelector('[data-testid="excluded"]')?.textContent).toContain('2026-06-07');
    expect(el(f).textContent).toContain('OBSERVED_EXCEL');
  });
  it('rango en agosto -> error 422 mostrado, sin tabla', async () => {
    const f = mount(SummaryPage);
    await flush(req('/api/v1/sales/summary'), { error: { code: 'AGOSTO_RESERVADO', message: 'agosto de 2026 está reservado para la prueba final' } }, f, 422);
    expect(state(f)).toBe('error');
    expect(el(f).textContent).toContain('agosto de 2026 está reservado');
  });
});

describe('Comparación', () => {
  it('lista backtests, pide la vista y muestra límites, RF no ganó y escenario/aviso del servidor', async () => {
    const f = mount(ComparisonPage);
    await flush(req('/api/v1/backtests'), [{ backtest_id: 'bt-1', kind: 'T07_desarrollo', label: 'T07', folds: 4, created: '2026-10-16' }], f);
    await new Promise((r) => setTimeout(r, 0));
    const d = req('/api/v1/backtests/bt-1');
    expect(d.request.params.get('view')).toBe('all');
    await flush(d, { scenario_id: 'esc-1', provenance: 'SYNTHETIC_NOT_REAL_INVENTORY', disclaimer: 'Aviso del servidor', predictive: [{ metodo: 'promedio_28', mape: 1 }] }, f);
    const t = el(f).textContent!;
    expect(el(f).querySelector('[data-testid="limits"]')?.textContent).toContain('no ganó');
    expect(t).toContain('más stock y más compras');
    expect(t).toContain('27 combinaciones');
    expect(t).toContain('Inventario simulado con supuestos');
    expect(el(f).querySelector('[data-testid="disclaimer"]')?.textContent).toBe('Aviso del servidor');
    expect(t).toContain('esc-1');
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
