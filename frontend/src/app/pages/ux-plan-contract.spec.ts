// R20: contrato REAL de la API de planes (backend/app/data/plan.py + pipeline/plan/store.py::_header/_product_doc + engine.py).
// Los cuerpos reproducen la forma del servidor: `params`, `dates`, `dataset` en la cabecera; `series` por escenario; `forecast: null`.
// Las cifras son de FORMA (fixtures), no resultados reales.
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting, TestRequest } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { apiInterceptor } from '../core/interceptors';
import { AuthService } from '../core/services/auth.service';
import { PlanPage } from './plan.page';

const API = '/api/v1';
const ID_A = 'plan-2026-11-d20261018-aaaaaaaaaaaa';   // corte 31/08, parámetros no predeterminados, un pedido por recibir
const ID_B = 'plan-2026-11-d20261018-bbbbbbbbbbbb';   // corte 31/07, parámetros predeterminados, sin pedidos
let http: HttpTestingController;

const SNAP = { snapshot_id: 'invrep-1', as_of_local: '2026-10-18T17:00:00-05:00', warehouse: { id: '1', name: 'Almacén Principal' } };
const inputs = () => ({
  label: 'x', dataset: { dataset_id: 'plds-new', sales_cutoff: '2026-09-30', source_rows: 10, classes: {}, imported_at: '2026-10-18T12:00:00Z' },
  snapshot: { ...SNAP, products: 3 },
  defaults: { month: '2026-11', decision_date: '2026-10-18', lead_days: [7, 14], reserve_days: 7, min_order: 1, order_multiple: 1, pending_orders: [] },
  limits: { decision_min: '2026-10-18', decision_max: '2026-11-30', months: ['2026-11', '2026-12'], lead_min: 1, lead_max: 60, max_leads: 4, horizon_days: 120 },
  assumptions: [{ code: 'PEDIDOS_PENDIENTES', nature: 'SUPUESTO', text: 'En este escenario no llegan otros pedidos (0 asumido; no es un dato informado por la empresa).' }],
});
const summary = (id: string, over: object = {}) => ({
  plan_id: id, month: '2026-11', decision_date: '2026-10-18', lead_days: [7, 14], status: 'completed', created_at: '2026-10-18T18:30:00-05:00',
  dataset_id: 'plds-x', snapshot_id: 'invrep-1', counts: { products: 3 }, version: 1, label: 'x', ...over,
});
const PENDING = [{ producto_id: '1000001', units: 30, arrival_date: '2026-11-05', nature: 'ASUMIDA' }];
const header = (id: string, cutoff: string, o: { reserve?: number; min?: number; mult?: number; pending?: object[] } = {}) => ({
  ...summary(id),
  dates: { sales_cutoff: cutoff, count_date: '2026-10-18', count_as_of_local: SNAP.as_of_local, decision_date: '2026-10-18', month_start: '2026-11-01', month_end: '2026-11-30', window_start: '2026-07-04' },
  distances: { cutoff_to_count: 48, cutoff_to_month_start: 62, cutoff_to_month_end: 91, count_to_decision: 0, horizon_limit_days: 120 },
  params: { month: '2026-11', decision_date: '2026-10-18', lead_days: [7, 14], reserve_days: o.reserve ?? 7, min_order: o.min ?? 1, order_multiple: o.mult ?? 1, pending_orders: o.pending ?? [] },
  dataset: { dataset_id: 'plds-x', sales_cutoff: cutoff, source_rows: 10, classes: {}, imported_at: '2026-10-18T12:00:00Z' },
  snapshot: { ...SNAP, version: 1, sha256_short: 'abc', csv_sha256_short: 'def' },
  method: 'promedio_28', engine_version: '1', contract_version: '1',
  assumptions: [{ code: 'PEDIDOS_PENDIENTES', nature: (o.pending ?? []).length ? 'DECLARADO' : 'SUPUESTO', text: 'x' }],
  warnings: ['Planificación con información desactualizada.', 'Plan de compra bajo supuestos; no es un pedido ejecutado ni una mejora comprobada.'],
  provenance: { sales: 'VENTAS_REALES_HASTA_' + cutoff }, completed_at: '2026-10-18T23:30:00Z',
});
const fc = (total = '60') => ({
  daily: '2', daily_exact: '2', month_total: total, month_days: 30, window_start: '2026-07-04', window_end: '2026-07-31', sum_28: '56', days_valid: 28, zero_reason: null,
});
const scen = (over: object = {}) => ({
  lead_days: 7, decision_date: '2026-10-18', arrival_date: '2026-10-25', status: 'OK', reason: null, purchase_qty: 60, required_arrival_date: '2026-10-25',
  stock_at_arrival: '28', stock_month_start: '14', shortage_before_month: '0', shortage_month: '0', served_month: '60', ...over,
});
const noLleg = () => scen({ status: 'NO_LLEGA_A_TIEMPO', purchase_qty: null, arrival_date: '2026-11-02', required_arrival_date: '2026-10-18', stock_at_arrival: null,
  stock_month_start: null, shortage_before_month: null, shortage_month: null, served_month: null });
const listItem = (code: string, over: object = {}) => ({
  producto_id: code, producto: 'PRODUCTO ' + code, categoria: 'X', unidad_descripcion: 'Un frasco', unidad_reporte: 'UND', status: 'OK', reason: null,
  forecast: fc(), count_stock: { libre: 40, as_of_local: SNAP.as_of_local }, scenarios: { '7': scen(), '14': scen({ arrival_date: '2026-11-01' }) }, ...over,
});
const nullItem = (code: string) => listItem(code, {
  status: 'NO_CALCULABLE', reason: 'UNIDAD_INCOMPATIBLE', forecast: null, count_stock: { libre: null, as_of_local: SNAP.as_of_local },
  scenarios: {
    '7': scen({ status: 'NO_CALCULABLE', reason: 'UNIDAD_INCOMPATIBLE', purchase_qty: null, required_arrival_date: null, stock_at_arrival: null, stock_month_start: null, shortage_before_month: null, shortage_month: null, served_month: null }),
    '14': scen({ status: 'NO_CALCULABLE', reason: 'UNIDAD_INCOMPATIBLE', purchase_qty: null, required_arrival_date: null, stock_at_arrival: null, stock_month_start: null, shortage_before_month: null, shortage_month: null, served_month: null }),
  },
});
const results = (id: string, items: object[]) => ({
  plan: summary(id), items, page: 1, page_size: 50, total: items.length, has_more: false,
  status_counts: { all: items.length, OK: items.length, LLEGA_TARDE: 0, NO_LLEGA_A_TIEMPO: 0, NO_CALCULABLE: 0 },
});
const ROW = { fecha: '2026-10-19', inicio: '40', recepciones: '0', disponible: '40', demanda: '2', atendida: '2', faltante: '0', fin: '38' };
const STEPS = [{ key: 'stock_conteo', label: 'Stock del conteo', text: 'existencias', value: '40', exact: '40' }, { key: 'compra', label: 'Compra redondeada', text: null, value: '60', exact: '60' }];
const detail = (id: string, code: string, over: object = {}) => ({
  ...listItem(code), plan_id: id, label: 'x', pending_orders: [], statuses: ['OK', 'OK'],
  scenarios: {
    '7': { ...scen(), explanation: STEPS, breakdown: {}, events: [], series: [ROW, { ...ROW, fecha: '2026-10-20', inicio: '38', disponible: '38', fin: '36' }] },
    '14': { ...scen({ arrival_date: '2026-11-01' }), explanation: STEPS, breakdown: {}, events: [], series: [ROW] },
  }, ...over,
});

async function settle(f: ComponentFixture<unknown>) { f.detectChanges(); await f.whenStable(); f.detectChanges(); }
async function ok(f: ComponentFixture<unknown>, r: TestRequest, b: unknown) { r.flush(b as object); await settle(f); }
const at = (path: string) => http.expectOne((r) => r.url === `${API}${path}`);
const q = (el: HTMLElement, id: string) => el.querySelector(`[data-testid="${id}"]`) as HTMLElement | null;
const txt = (el: HTMLElement, id: string) => (q(el, id)?.textContent ?? '').replace(/\s+/g, ' ').trim();
const cell = (el: HTMLElement, sku: string, col: string) => (el.querySelector(`tr[data-sku="${sku}"] [data-col="${col}"]`)?.textContent ?? '').replace(/\s+/g, ' ').trim();

/** Monta la página con los planes dados; responde cabecera y resultados SOLO del primero. */
async function open(plans: { id: string; hdr: object; items: object[] }[]) {
  TestBed.configureTestingModule({
    imports: [PlanPage],
    providers: [provideHttpClient(withInterceptors([apiInterceptor])), provideHttpClientTesting(), provideRouter([{ path: '**', children: [] }])],
  });
  TestBed.inject(AuthService).session.set({ username: 'u', role: 'lector', csrf_token: 'c', expires_at: '2026-10-18T23:00:00Z' });
  http = TestBed.inject(HttpTestingController);
  const f = TestBed.createComponent(PlanPage);
  f.detectChanges();
  const el = f.nativeElement as HTMLElement;
  await ok(f, at('/plans/inputs'), inputs());
  await ok(f, at('/plans'), { items: plans.map((p) => summary(p.id)), total: plans.length, page: 1, page_size: 50, has_more: false });
  await ok(f, at(`/plans/${plans[0].id}`), plans[0].hdr);
  await ok(f, at(`/plans/${plans[0].id}/results`), results(plans[0].id, plans[0].items));
  return { f, el };
}
async function openProduct(f: ComponentFixture<unknown>, el: HTMLElement, id: string, code: string, body: unknown) {
  (el.querySelector(`tr[data-sku="${code}"] [data-testid="plan-understand"]`) as HTMLElement).click();
  await settle(f);
  await ok(f, at(`/plans/${id}/results/${code}`), body);
}
async function pickVersion(f: ComponentFixture<unknown>, el: HTMLElement, id: string) {
  const s = q(el, 'plan-version') as HTMLSelectElement;
  s.value = id; s.dispatchEvent(new Event('change')); await settle(f);
}
afterEach(() => http?.verify());

const planA = () => ({ id: ID_A, hdr: header(ID_A, '2026-08-31', { reserve: 9, min: 3, mult: 2, pending: PENDING }), items: [listItem('1000001'), nullItem('1000002')] });
const planB = () => ({ id: ID_B, hdr: header(ID_B, '2026-07-31'), items: [listItem('2000001')] });

describe('Planificar compras · contrato real (R20)', () => {
  it('1. reserva, mínimo y múltiplo salen de params del plan, distintos de los valores por defecto', async () => {
    const { el } = await open([planA()]);
    const t = txt(el, 'src-params');
    expect(t).toContain('reserva 9 días');
    expect(t).toContain('compra mínima 3');
    expect(t).toContain('múltiplo 2');
    expect(t).toContain('7 y 14 días');
    expect(txt(el, 'head-decision')).toBe('18/10/2026');   // la decisión se muestra una sola vez, en el resumen
  });

  it('2. el corte es el del PLAN seleccionado (31/08), no el del dataset más nuevo (30/09)', async () => {
    const { f, el } = await open([planA()]);
    expect(f.componentInstance instanceof PlanPage).toBe(true);
    expect(txt(el, 'src-sales')).toContain('31 de agosto de 2026');
    expect(txt(el, 'plan-cutoff')).toContain('31 de agosto de 2026');
    expect(el.textContent).not.toContain('30 de septiembre');
    expect((f.componentInstance as PlanPage).cutoff()).toBe('2026-08-31');
  });

  it('3. «Ver el día a día» lee scenarios[lead].series, con la columna Disponible', async () => {
    const { f, el } = await open([planA()]);
    await openProduct(f, el, ID_A, '1000001', detail(ID_A, '1000001'));
    const d7 = q(el, 'ex-daily-7')!;
    expect(d7.querySelectorAll('tbody tr').length).toBe(2);
    expect(d7.textContent).not.toContain('no entregó la serie');
    expect(Array.from(d7.querySelectorAll('thead th')).map((h) => h.textContent)).toContain('Disponible');
    expect(q(el, 'ex-daily-14')!.querySelectorAll('tbody tr').length).toBe(1);
  });

  it('3b. sin serie (producto no calculable) se informa que no hay serie, sin error', async () => {
    const { f, el } = await open([planA()]);
    const d = detail(ID_A, '1000001');
    d.scenarios['7'].series = [];
    await openProduct(f, el, ID_A, '1000001', d);
    expect(q(el, 'ex-daily-7')!.textContent).toContain('no entregó la serie diaria');
  });

  it('4. con un pedido declarado el aviso lo dice, lo lista con su naturaleza y NO afirma «no llegan otros pedidos» a secas', async () => {
    const { el } = await open([planA()]);
    expect(txt(el, 'src-orders')).not.toContain('En este escenario no llegan otros pedidos');
    expect(txt(el, 'src-orders')).toContain('Se considera 1 pedido por recibir declarado');
    expect(txt(el, 'src-orders')).toContain('no llegan otros adicionales (supuesto)');
    const list = txt(el, 'src-pending');
    expect(list).toContain('1000001');
    expect(list).toContain('30 unidades');
    expect(list).toContain('05/11/2026');
    expect(list).toContain('Asumido');
    expect(list).not.toContain('Reportado');
  });

  it('4b. un plan sin pedidos dice que no llegan otros (supuesto) y no muestra lista', async () => {
    const { el } = await open([planB()]);
    expect(txt(el, 'src-orders')).toContain('En este escenario no llegan otros pedidos (supuesto)');
    expect(q(el, 'src-pending')).toBeNull();
  });

  it('5. forecast null: «No se puede calcular» en tabla y en «Entender la compra», nunca 0', async () => {
    const { f, el } = await open([planA()]);
    expect(cell(el, '1000002', 'forecast')).toBe('No se puede calcular');
    expect(cell(el, '1000002', 'count')).toBe('No informado');
    expect(cell(el, '1000002', 'buy-7')).toBe('No se puede calcular');
    await openProduct(f, el, ID_A, '1000002', detail(ID_A, '1000002', {
      forecast: null, status: 'NO_CALCULABLE', count_stock: { libre: null, as_of_local: null },
      scenarios: { '7': { ...nullItem('x').scenarios['7'], explanation: [{ key: 'no_calculable', label: 'No calculable', text: 'Unidad incompatible', value: null }], series: [] },
                   '14': { ...nullItem('x').scenarios['14'], explanation: [], series: [] } },
    }));
    const p = txt(el, 'plan-explain');
    expect(txt(el, 'ex-forecast')).toContain('Ventas previstas del mes, sin limitar por stock: No se puede calcular');
    expect(p).not.toMatch(/stock: 0\b/);
    expect(txt(q(el, 'ex-lead-7')!, 'ex-served')).toContain('Ventas previstas sin limitar por stock: No se puede calcular');
    expect(txt(q(el, 'ex-lead-7')!, 'ex-buy')).toBe('Compra recomendada: No se puede calcular');
  });

  it('6. NO_LLEGA_A_TIEMPO muestra la fecha de decisión que entrega el servidor', async () => {
    const { f, el } = await open([planA()]);
    const d = detail(ID_A, '1000001');
    d.scenarios['14'] = { ...noLleg(), explanation: [], breakdown: null, events: [], series: [] } as never;
    await openProduct(f, el, ID_A, '1000001', d);
    expect(txt(q(el, 'ex-lead-14')!, 'ex-decide')).toBe('Para que llegue el primer día del mes habría que decidir la compra el 18 de octubre de 2026.');
    expect(q(q(el, 'ex-lead-7')!, 'ex-decide')).toBeNull();
    expect(txt(q(el, 'ex-lead-14')!, 'ex-buy')).toBe('Compra recomendada: No se puede calcular');
  });

  it('7. dos planes con cortes distintos: al cambiar de versión nada del plan anterior sobrevive', async () => {
    const { f, el } = await open([planA(), planB()]);
    await openProduct(f, el, ID_A, '1000001', detail(ID_A, '1000001'));
    expect(q(el, 'plan-explain')).toBeTruthy();
    expect(txt(el, 'src-sales')).toContain('31 de agosto de 2026');
    expect(q(el, 'src-pending')).toBeTruthy();

    await pickVersion(f, el, ID_B);
    // mientras llegan las respuestas del plan nuevo: no queda nada del anterior
    expect(q(el, 'plan-explain')).toBeNull();
    expect(q(el, 'src-pending')).toBeNull();
    expect(el.textContent).not.toContain('31 de agosto');
    expect(el.textContent).not.toContain('1000001');
    await ok(f, at(`/plans/${ID_B}`), planB().hdr);
    await ok(f, at(`/plans/${ID_B}/results`), results(ID_B, planB().items));

    expect(txt(el, 'src-sales')).toContain('31 de julio de 2026');
    expect(txt(el, 'src-sales')).not.toContain('agosto');
    expect(txt(el, 'src-params')).toContain('reserva 7 días');
    expect(txt(el, 'src-params')).toContain('compra mínima 1');
    expect(q(el, 'src-pending')).toBeNull();
    expect(txt(el, 'plan-cutoff')).toContain('31 de julio de 2026');
    expect(txt(el, 'src-orders')).toContain('En este escenario no llegan otros pedidos (supuesto)');
    expect(el.querySelector('tr[data-sku="1000001"]')).toBeNull();
    expect(el.querySelector('tr[data-sku="2000001"]')).toBeTruthy();
    expect(q(el, 'plan-explain')).toBeNull();
  });

  it('7b. si falla la cabecera del plan nuevo no se muestran el corte ni los parámetros del anterior', async () => {
    const { f, el } = await open([planA(), planB()]);
    await pickVersion(f, el, ID_B);
    at(`/plans/${ID_B}`).flush({ error: { code: 'X', message: 'x' } }, { status: 500, statusText: 'x' });
    await settle(f);
    at(`/plans/${ID_B}/results`).flush({ error: { code: 'X', message: 'x' } }, { status: 500, statusText: 'x' });
    await settle(f);
    expect(el.textContent).not.toContain('31 de agosto');
    expect(el.textContent).not.toContain('reserva 9 días');
    expect(el.textContent).not.toContain('30 de septiembre');   // tampoco el corte del dataset más nuevo
    expect(q(el, 'src-pending')).toBeNull();
  });

  it('7c. al cambiar de mes se limpia la selección y el plan anterior', async () => {
    const { f, el } = await open([planA()]);
    await openProduct(f, el, ID_A, '1000001', detail(ID_A, '1000001'));
    const m = q(el, 'plan-month') as HTMLSelectElement;
    m.value = '2026-12'; m.dispatchEvent(new Event('change')); await settle(f);
    expect(q(el, 'plan-explain')).toBeNull();
    expect(el.querySelector('tr[data-sku="1000001"]')).toBeNull();
    expect(q(el, 'src-pending')).toBeNull();
    const pr = at('/plans');
    expect(pr.request.params.get('month')).toBe('2026-12');
    await ok(f, pr, { items: [], total: 0, page: 1, page_size: 50, has_more: false, unavailable_reason: 'SIN_PLAN' });
    expect(el.textContent).toContain('Todavía no se generó un plan para este mes');
    expect(txt(el, 'plan-cutoff')).toContain('30 de septiembre de 2026');   // sin plan elegido: el de las entradas
    expect(txt(el, 'plan-cutoff')).toContain('En este escenario no llegan otros pedidos (supuesto)');
  });
});
