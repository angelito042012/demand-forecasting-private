// R21: Inicio, Ventas previstas y Compra recomendada muestran el MISMO plan vigente (plan_id, corte, ventas previstas y compra).
// Los cuerpos reproducen la FORMA de la API (docs/T20_CONTRATO_ACTUALIZACION_V2.md §3); las cifras son fixtures, no resultados reales.
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting, TestRequest } from '@angular/common/http/testing';
import { Router, provideRouter } from '@angular/router';
import { apiInterceptor } from '../core/http.interceptor';
import { AuthService } from '../core/auth.service';
import { CurrentPlanStore } from '../core/current-plan.store';
import { App } from '../app';
import { HomePage } from './home.page';
import { PlanForecastsPage } from './plan-forecasts.page';
import { PlanPage } from './plan.page';
import { StockPage } from './stock.page';
import { page, session } from '../testing/fixtures';

const API = '/api/v1';
const V2 = 'plan-2026-11-d20261021-bbbbbbbbbbbb';
const V1 = 'plan-2026-11-d20261018-aaaaaaaaaaaa';
const CLOSING = '2026-10-20T23:59:59-05:00';
const BASE = '2026-10-18T17:00:00-05:00';
const LAST = '2026-10-21T16:26:38-05:00';
const WH = { id: '1', name: 'Almacén Principal' };
let http: HttpTestingController;

const ref = (id: string, version: number) => ({
  plan_id: id, month: '2026-11', decision_date: '2026-10-21', lead_days: [7, 14], status: 'completed', created_at: '2026-10-21T18:30:00-05:00',
  dataset_id: 'plds-x', snapshot_id: 'invrec-20261020-abc', counts: { products: 2 }, version,
});
const header = (id: string, version: number) => ({
  ...ref(id, version),
  dates: { sales_cutoff: '2026-10-20', count_date: '2026-10-20', count_as_of_local: CLOSING, decision_date: '2026-10-21', month_start: '2026-11-01', month_end: '2026-11-30' },
  params: { month: '2026-11', decision_date: '2026-10-21', lead_days: [7, 14], reserve_days: 7, min_order: 1, order_multiple: 1, pending_orders: [] },
  dataset: { dataset_id: 'plds-x', sales_cutoff: '2026-10-20' },
  snapshot: { snapshot_id: 'invrec-20261020-abc', as_of_local: CLOSING, warehouse: WH, kind: 'RECONSTRUIDO', base_count_as_of_local: BASE, last_movement_local: LAST, discrepancy_products: [] },
  confirmations: [], assumptions: [], warnings: [], provenance: {},
});
const inputs = () => ({
  dataset: { dataset_id: 'plds-x', sales_cutoff: '2026-10-20' }, snapshot: { snapshot_id: 'invrec-20261020-abc', as_of_local: CLOSING, warehouse: WH, kind: 'RECONSTRUIDO' },
  defaults: { month: '2026-11', decision_date: '2026-10-21', lead_days: [7, 14], reserve_days: 7, min_order: 1, order_multiple: 1, pending_orders: [] },
  limits: { decision_min: '2026-10-21', decision_max: '2026-11-30', months: ['2026-11'], lead_min: 1, lead_max: 60, max_leads: 4, horizon_days: 120 },
});
const sc = (buy: number, arrival: string) => ({
  lead_days: 7, arrival_date: arrival, status: 'OK', reason: null, purchase_qty: buy, stock_month_start: '14', shortage_before_month: '0', shortage_month: '0', served_month: '60',
});
const item = (code: string, total: string, daily: string, buy7: number, buy14: number) => ({
  producto_id: code, producto: 'PRODUCTO ' + code, categoria: 'X', unidad_descripcion: 'Un frasco', status: 'OK',
  forecast: { daily, daily_exact: daily, month_total: total, month_days: 30, window_start: '2026-09-23', window_end: '2026-10-20', sum_28: '56', days_valid: 28 },
  count_stock: { libre: 40, as_of_local: CLOSING }, stock_provenance: { kind: 'RECONSTRUIDO', base_count: 38, movements_net_to_closing: 2, discrepancy: null },
  scenarios: { '7': sc(buy7, '2026-10-28'), '14': sc(buy14, '2026-11-04') },
});
const ITEMS = [item('1000001', '60', '2', 60, 70), item('1000002', '45', '1.5', 50, 0), item('1000003', '30', '1', 25, 25)];
const results = (id: string, items = ITEMS) => ({
  plan: ref(id, 2), items, page: 1, page_size: 50, total: items.length, has_more: false,
  status_counts: { all: items.length, OK: items.length, LLEGA_TARDE: 0, NO_LLEGA_A_TIEMPO: 0, NO_CALCULABLE: 0 },
});

async function settle(f: ComponentFixture<unknown>) { f.detectChanges(); await f.whenStable(); f.detectChanges(); }
async function ok(f: ComponentFixture<unknown>, r: TestRequest, b: unknown) { r.flush(b as object); await settle(f); }
const at = (path: string) => http.expectOne((r) => r.url === `${API}${path}`);
const q = (el: HTMLElement, id: string) => el.querySelector(`[data-testid="${id}"]`) as HTMLElement | null;
const txt = (el: HTMLElement, id: string) => (q(el, id)?.textContent ?? '').replace(/\s+/g, ' ').trim();
const cell = (el: HTMLElement, sku: string, col: string) => (el.querySelector(`tr[data-sku="${sku}"] [data-col="${col}"]`)?.textContent ?? '').replace(/\s+/g, ' ').trim();
/** Responde las peticiones históricas de Inicio (análisis y cifra de reposición) sin interesar su contenido. */
function answerHistorical() {
  http.match((r) => r.url === `${API}/runs`).forEach((r) => r.flush(page([])));
  http.match((r) => r.url === `${API}/recommendations`).forEach((r) => r.flush({ items: [], total: 0, page: 1, page_size: 1, has_more: false }));
}
afterEach(() => http?.verify());

function setup(url = '/inicio') {
  TestBed.configureTestingModule({
    imports: [HomePage, PlanForecastsPage, PlanPage, StockPage],
    providers: [provideHttpClient(withInterceptors([apiInterceptor])), provideHttpClientTesting(), provideRouter([{ path: '**', children: [] }])],
  });
  TestBed.inject(AuthService).session.set(session);
  http = TestBed.inject(HttpTestingController);
  return TestBed.inject(Router).navigateByUrl(url);
}

/** Resuelve el plan vigente tal como lo hace el servicio compartido: inputs → plans → plan. */
async function resolveCurrent(f: ComponentFixture<unknown>, list = [V2, V1]) {
  await ok(f, at('/plans/inputs'), inputs());
  const pr = at('/plans');
  expect(pr.request.params.get('month')).toBe('2026-11');
  await ok(f, pr, { items: list.map((id, i) => ref(id, list.length - i)) });
  await ok(f, at(`/plans/${list[0]}`), header(list[0], list.length));
}

describe('R21 · mismo plan vigente en Inicio, Ventas previstas y Compra recomendada', () => {
  it('Inicio → Ventas previstas → Compra recomendada: mismo plan_id, mismo corte, mismas cantidades', async () => {
    await setup();
    // ---- Inicio
    const home = TestBed.createComponent(HomePage);
    home.detectChanges();
    await resolveCurrent(home);
    answerHistorical();
    const hr = at(`/plans/${V2}/results`);
    expect(hr.request.params.get('page_size')).toBe('50');
    await ok(home, hr, results(V2));
    const h = home.nativeElement as HTMLElement;
    expect(txt(h, 'page-title')).toBe('Ventas previstas y compra recomendada para noviembre');
    expect(txt(h, 'hp-version')).toContain('Versión 2');
    expect(txt(h, 'hp-version')).toContain('decisión de compra el 21/10/2026');
    expect(txt(h, 'hp-cutoff')).toContain('20 de octubre de 2026');
    expect(txt(h, 'hp-stock')).toContain('reconstruida al cierre del 20/10/2026');
    expect(txt(h, 'hp-counts')).toContain('3 de 3 con plazo de 7 días');
    expect(txt(h, 'hp-counts')).toContain('2 de 3 con plazo de 14 días');
    expect(h.textContent).not.toMatch(/datos del ejemplo/);
    const homePlanId = TestBed.inject(CurrentPlanStore).plan()!.ref.plan_id;
    home.destroy();

    // ---- Ventas previstas (reutiliza el plan ya resuelto: no vuelve a pedir inputs, plans ni cabecera)
    const fc = TestBed.createComponent(PlanForecastsPage);
    fc.detectChanges();
    http.expectNone((r) => r.url === `${API}/plans/inputs` || r.url === `${API}/plans` || r.url === `${API}/plans/${V2}`);
    await ok(fc, at(`/plans/${V2}/results`), results(V2));
    const f = fc.nativeElement as HTMLElement;
    expect(txt(f, 'page-title')).toBe('Ventas previstas');
    expect(txt(f, 'fc-version')).toContain('Versión 2');
    expect(txt(f, 'fc-sales')).toContain('20 de octubre de 2026');
    expect(txt(f, 'fc-stock')).toContain('20/10/2026');
    expect(txt(f, 'fc-provenance')).toMatch(/Dato real[\s\S]*Proyección/);
    expect(f.querySelectorAll('[data-testid="fc-table"] tbody tr').length).toBe(3);
    expect(cell(f, '1000001', 'forecast')).toBe('60');
    expect(cell(f, '1000002', 'forecast')).toBe('45');
    expect(cell(f, '1000002', 'daily')).toBe('1.5');
    expect(cell(f, '1000002', 'window')).toContain('23/09/2026 al 20/10/2026');
    expect(cell(f, '1000002', 'stock')).toBe('40');
    const link = f.querySelector('tr[data-sku="1000002"] [data-testid="fc-to-plan"]') as HTMLAnchorElement;
    expect(link.textContent).toContain('Ver compra recomendada');
    expect(link.getAttribute('href')).toContain('/planificar');
    expect(link.getAttribute('href')).toContain('q=1000002');
    expect(TestBed.inject(CurrentPlanStore).plan()!.ref.plan_id).toBe(homePlanId);
    const fcForecast = ['1000001', '1000002', '1000003'].map((c) => cell(f, c, 'forecast'));
    fc.destroy();

    // ---- Compra recomendada (por defecto elige el primero de GET /plans: el mismo)
    const pp = TestBed.createComponent(PlanPage);
    pp.detectChanges();
    await ok(pp, at('/plans/inputs'), inputs());
    await ok(pp, at('/plans'), { items: [ref(V2, 2), ref(V1, 1)] });
    await ok(pp, at(`/plans/${V2}`), header(V2, 2));
    await ok(pp, at(`/plans/${V2}/results`), results(V2));
    const p = pp.nativeElement as HTMLElement;
    expect((pp.componentInstance as PlanPage).planId()).toBe(homePlanId);
    expect(txt(p, 'src-sales')).toContain('20 de octubre de 2026');
    expect(q(p, 'plan-not-current')).toBeNull();
    expect(['1000001', '1000002', '1000003'].map((c) => cell(p, c, 'forecast'))).toEqual(fcForecast);
    expect(cell(p, '1000001', 'buy-7')).toContain('60');
    expect(cell(p, '1000001', 'buy-14')).toContain('70');
    expect(cell(p, '1000002', 'buy-7')).toContain('50');
    expect(cell(p, '1000002', 'buy-14')).toContain('0 (no hace falta comprar)');
  });

  it('si el usuario elige otra versión en Compra recomendada, se rotula y el vigente sigue siendo el primero', async () => {
    await setup();
    const pp = TestBed.createComponent(PlanPage);
    pp.detectChanges();
    await ok(pp, at('/plans/inputs'), inputs());
    await ok(pp, at('/plans'), { items: [ref(V2, 2), ref(V1, 1)] });
    await ok(pp, at(`/plans/${V2}`), header(V2, 2));
    await ok(pp, at(`/plans/${V2}/results`), results(V2));
    const p = pp.nativeElement as HTMLElement;
    const sel = q(p, 'plan-version') as HTMLSelectElement;
    sel.value = V1; sel.dispatchEvent(new Event('change')); await settle(pp);
    await ok(pp, at(`/plans/${V1}`), header(V1, 1));
    await ok(pp, at(`/plans/${V1}/results`), results(V1));
    expect(txt(p, 'plan-not-current')).toContain('no es la vigente');
    expect(txt(p, 'plan-not-current')).toContain('Inicio');
  });

  it('Ventas previstas sin plan: estado vacío en palabras sencillas', async () => {
    await setup('/pronosticos');
    const fc = TestBed.createComponent(PlanForecastsPage);
    fc.detectChanges();
    await ok(fc, at('/plans/inputs'), inputs());
    await ok(fc, at('/plans'), { items: [], unavailable_reason: 'SIN_PLAN' });
    expect(fc.nativeElement.textContent).toContain('Todavía no se generó un plan de compra');
    expect(q(fc.nativeElement, 'fc-table')).toBeNull();
  });

  it('Ventas previstas con error del servidor: aviso y «Reintentar» (una petición)', async () => {
    await setup('/pronosticos');
    const fc = TestBed.createComponent(PlanForecastsPage);
    fc.detectChanges();
    at('/plans/inputs').flush({ error: { code: 'X', message: 'x' } }, { status: 503, statusText: 'x' });
    await settle(fc);
    const el = fc.nativeElement as HTMLElement;
    expect(el.querySelector('[data-state="error"]')).toBeTruthy();
    expect(q(el, 'fc-table')).toBeNull();
    (el.querySelector('[data-state="error"] button') as HTMLButtonElement).click();
    await resolveCurrent(fc);
    await ok(fc, at(`/plans/${V2}/results`), results(V2));
    expect(el.querySelectorAll('[data-testid="fc-table"] tbody tr').length).toBe(3);
  });

  it('Ventas previstas: error en los resultados y búsqueda por producto (q) con orden', async () => {
    await setup('/pronosticos');
    const fc = TestBed.createComponent(PlanForecastsPage);
    fc.detectChanges();
    await resolveCurrent(fc);
    at(`/plans/${V2}/results`).flush({ error: { code: 'PROHIBIDO', message: 'x' } }, { status: 403, statusText: 'x' });
    await settle(fc);
    expect(q(fc.nativeElement, 'fc-forbidden')).toBeTruthy();
  });

  it('Ventas previstas: la búsqueda pide q y sort al servidor', async () => {
    await setup('/pronosticos');
    const fc = TestBed.createComponent(PlanForecastsPage);
    fc.detectChanges();
    await resolveCurrent(fc);
    await ok(fc, at(`/plans/${V2}/results`), results(V2));
    const el = fc.nativeElement as HTMLElement;
    const input = q(el, 'fc-q') as HTMLInputElement;
    input.value = '1000002'; input.dispatchEvent(new Event('input')); await settle(fc);
    (q(el, 'fc-search') as HTMLButtonElement).click(); await settle(fc);
    const r = at(`/plans/${V2}/results`);
    expect(r.request.params.get('q')).toBe('1000002');
    expect(r.request.params.get('page')).toBe('1');
    await ok(fc, r, results(V2, [ITEMS[1]]));
    expect(el.querySelectorAll('[data-testid="fc-table"] tbody tr').length).toBe(1);
  });

  it('Inicio sin plan: estado vacío; las vistas históricas siguen en su sección académica', async () => {
    await setup();
    const home = TestBed.createComponent(HomePage);
    home.detectChanges();
    await ok(home, at('/plans/inputs'), {});
    answerHistorical();
    await settle(home);
    const el = home.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Todavía no se generó un plan de compra');
    expect(q(el, 'hp-cutoff')).toBeNull();
    expect(q(el, 'home-academic')).toBeTruthy();
    expect(q(el, 'home-academic')!.textContent).toContain('inventario simulado');
  });
});

describe('R21 · franja de contexto y rutas', () => {
  it('Inicio y Ventas previstas no dicen «Ejemplo con datos históricos»; la ruta académica sí', async () => {
    TestBed.configureTestingModule({
      imports: [App],
      providers: [provideHttpClient(withInterceptors([apiInterceptor])), provideHttpClientTesting(),
        provideRouter([{ path: 'inicio', children: [] }, { path: 'pronosticos', children: [] }, { path: 'evaluacion/ventas-previstas', children: [] }, { path: 'recomendaciones', children: [] }])],
    });
    http = TestBed.inject(HttpTestingController);
    TestBed.inject(AuthService).session.set(session);
    const f = TestBed.createComponent(App);
    const router = TestBed.inject(Router);
    const el = f.nativeElement as HTMLElement;
    const strip = async (url: string) => { await router.navigateByUrl(url); await settle(f); return txt(el, 'context-strip'); };
    for (const u of ['/inicio', '/pronosticos']) {
      const t = await strip(u);
      expect(t, u).toContain('Plan de noviembre vigente');
      expect(t, u).not.toContain('Ejemplo con datos históricos');
    }
    expect(await strip('/evaluacion/ventas-previstas')).toContain('Ejemplo con datos históricos de 2026');
    expect(await strip('/recomendaciones')).toContain('Inventario simulado con supuestos; no corresponde al inventario real de la empresa');
  });
});
