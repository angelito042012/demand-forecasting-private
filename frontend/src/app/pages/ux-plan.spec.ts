// T19: «Planificar compras». Fixtures de FORMA con el esquema de docs/T19_CONTRATO_PLANIFICACION.md §6 y los ejemplos calculados a mano
// del §4 (m = 2, conteo 40). No son resultados reales ni se prueban contra el backend.
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting, TestRequest } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { apiInterceptor } from '../core/interceptors';
import { AuthService } from '../core/services/auth.service';
import { Role } from '../core/models';
import { routes } from '../app.routes';
import { PlanPage } from './plan.page';

const API = '/api/v1';
const PLAN_ID = 'plan-2026-11-d20261018-0123456789ab';
let http: HttpTestingController;

const inputsBody = (over: object = {}) => ({
  dataset: { dataset_id: 'plds-aaaaaaaaaaaa', sales_cutoff: '2026-09-30', source_rows: 106525, imported_at: '2026-10-18T12:00:00Z' },
  snapshot: { snapshot_id: 'invrep-20261018T1700-a1-608d15a74a58', as_of_local: '2026-10-18T17:00:00-05:00', warehouse: { id: '1', name: 'Almacén Principal' }, products: 50 },
  defaults: { month: '2026-11', decision_date: '2026-10-18', lead_days: [7, 14], reserve_days: 7, min_order: 1, order_multiple: 1, pending_orders: [] },
  limits: { decision_min: '2026-10-18', decision_max: '2026-11-30', months: ['2026-11', '2026-12'], lead_min: 1, lead_max: 60, max_leads: 4, horizon_days: 120 },
  assumptions: [{ text: 'No llegan otros pedidos', nature: 'ASUMIDA' }], ...over,
});
const planRef = (id = PLAN_ID, over: object = {}) => ({ plan_id: id, month: '2026-11', decision_date: '2026-10-18', lead_days: [7, 14], status: 'completed', created_at: '2026-10-18T18:30:00-05:00', ...over });
const header = () => ({
  ...planRef(), version: 1, counts: { products: 50 }, dataset_id: 'plds-aaaaaaaaaaaa', snapshot_id: 'invrep-20261018T1700-a1-608d15a74a58',
  dataset: { dataset_id: 'plds-aaaaaaaaaaaa', sales_cutoff: '2026-09-30', source_rows: 106525 },
  dates: { sales_cutoff: '2026-09-30', count_date: '2026-10-18', count_as_of_local: '2026-10-18T17:00:00-05:00', decision_date: '2026-10-18', month_start: '2026-11-01', month_end: '2026-11-30', window_start: '2026-09-03' },
  snapshot: { snapshot_id: 'invrep-20261018T1700-a1-608d15a74a58', as_of_local: '2026-10-18T17:00:00-05:00', warehouse: { id: '1', name: 'Almacén Principal' } },
  params: { month: '2026-11', decision_date: '2026-10-18', lead_days: [7, 14], reserve_days: 7, min_order: 1, order_multiple: 1, pending_orders: [] },
  distances: { cutoff_to_count: 18, cutoff_to_month_start: 32, cutoff_to_month_end: 61, count_to_decision: 0, horizon_limit_days: 120 },
  assumptions: [{ code: 'PEDIDOS_PENDIENTES', text: 'En este escenario no llegan otros pedidos (0 asumido).', nature: 'SUPUESTO' }], warnings: [],
});
const sc = (over: object = {}) => ({
  arrival_date: '2026-10-25', stock_at_arrival: '28', purchase_qty: 60, stock_month_start: '14', shortage_before_month: '0', shortage_month: '0',
  served_month: '60', status: 'OK', ...over,
});
function item(i: number, over: object = {}) {
  return {
    producto_id: String(3230000 + i).padStart(9, '0'), producto: `PRODUCTO DE PRUEBA ${i + 1}`, categoria: 'X', unidad_descripcion: i === 1 ? 'Caja de 12' : 'Un frasco de 250 ML',
    forecast: { daily: '2', daily_exact: '2', month_total: i === 7 ? '0' : '60', month_days: 30, sum_28: '56', days_valid: 28 },
    count_stock: { libre: 40, as_of_local: '2026-10-18T17:00:00-05:00' },
    scenarios: { '7': sc(), '14': sc({ arrival_date: '2026-11-01', stock_at_arrival: '14' }) },
    ...over,
  };
}
function items() {
  return Array.from({ length: 50 }, (_, i) => {
    if (i === 0) return item(i, { scenarios: { '7': sc({ purchase_qty: 0 }), '14': sc({ purchase_qty: 0, arrival_date: '2026-11-01' }) } });
    if (i === 1) return item(i, { scenarios: { '7': sc({ purchase_qty: 74 }), '14': sc({ arrival_date: null, purchase_qty: null, stock_at_arrival: null, stock_month_start: null, shortage_before_month: null, shortage_month: null, served_month: null, status: 'NO_LLEGA_A_TIEMPO' }) } });
    if (i === 2) return item(i, { scenarios: { '7': sc(), '14': sc({ arrival_date: '2026-11-08', purchase_qty: 60, status: 'LLEGA_TARDE', shortage_month: '14', stock_month_start: '0' }) } });
    if (i === 3) return item(i, { forecast: null, count_stock: { libre: null, as_of_local: null }, scenarios: { '7': sc({ arrival_date: null, purchase_qty: null, stock_at_arrival: null, stock_month_start: null, shortage_before_month: null, shortage_month: null, served_month: null, status: 'NO_CALCULABLE' }), '14': sc({ arrival_date: null, purchase_qty: null, stock_at_arrival: null, stock_month_start: null, shortage_before_month: null, shortage_month: null, served_month: null, status: 'NO_CALCULABLE' }) } });
    return item(i);
  });
}
const resultsBody = (over: object = {}) => ({ items: items(), page: 1, page_size: 50, total: 50, has_more: false, status_counts: { OK: 47, LLEGA_TARDE: 1, NO_LLEGA_A_TIEMPO: 1, NO_CALCULABLE: 1 }, ...over });
const steps7 = [
  { label: 'Stock del conteo', text: 'existencias informadas el 18/10/2026 17:00', value: '40' },
  { label: 'Consumo antes de que llegue el pedido', text: '19/10 a 24/10: 6 días × 2 por día', value: '12' },
  { label: 'Stock al llegar el pedido', text: '25/10', value: '28' },
  { label: 'Ventas previstas hasta fin de octubre', text: 'demanda puente', value: '14' },
  { label: 'Ventas previstas de noviembre', value: '60' },
  { label: 'Reserva al cierre', text: '7 días × 2', value: '14' },
  { label: 'Necesidad total', text: '14 + 60 + 14', value: '88' },
  { label: 'Menos el stock al llegar y las recepciones', value: '28' },
  { label: 'Cantidad sin redondear', value: '60' },
  { label: 'Compra redondeada', value: '60' },
];
const steps14 = [
  { label: 'Stock del conteo', value: '40' }, { label: 'Stock al llegar el pedido', text: '01/11', value: '14' },
  { label: 'Cantidad sin redondear', value: '60' }, { label: 'Compra redondeada', value: '60' },
];
const daily = (n: number) => Array.from({ length: n }, (_, i) => ({ fecha: `2026-10-${String(19 + i).padStart(2, '0')}`, inicio: '40', recepciones: '0', disponible: '40', demanda: '2', atendida: '2', faltante: '0', fin: '38' }));
const detailBody = () => ({
  ...item(4),
  scenarios: {
    '7': { ...sc({ served_month: '60' }), explanation: steps7, series: daily(3) },
    '14': { ...sc({ arrival_date: '2026-11-01', stock_at_arrival: '14', served_month: '60' }), explanation: steps14, series: daily(2) },
  },
});

async function settle(f: ComponentFixture<unknown>) { f.detectChanges(); await f.whenStable(); f.detectChanges(); }
async function ok(f: ComponentFixture<unknown>, r: TestRequest, b: unknown) { r.flush(b as object); await settle(f); }
async function fail(f: ComponentFixture<unknown>, r: TestRequest, status: number, body: object = {}) { r.flush(body, { status, statusText: 'x' }); await settle(f); }
const q = (el: HTMLElement, id: string) => el.querySelector(`[data-testid="${id}"]`) as HTMLElement | null;
const txt = (el: HTMLElement, id: string) => (q(el, id)?.textContent ?? '').replace(/\s+/g, ' ').trim();
const cell = (el: HTMLElement, sku: string, col: string) => (el.querySelector(`tr[data-sku="${sku}"] [data-col="${col}"]`)?.textContent ?? '').replace(/\s+/g, ' ').trim();
const at = (path: string) => http.expectOne((r) => r.url === `${API}${path}`);
async function typeIn(f: ComponentFixture<unknown>, el: HTMLElement, id: string, value: string, ev = 'input') {
  const i = q(el, id) as HTMLInputElement | HTMLSelectElement;
  i.value = value; i.dispatchEvent(new Event(ev)); await settle(f);
}
async function click(f: ComponentFixture<unknown>, el: HTMLElement, id: string) { (q(el, id) as HTMLElement).click(); await settle(f); }

/** Monta la página y responde a la cadena inputs → plans → (plan, results). */
async function open(role: Role = 'lector', o: { inputs?: object; plans?: unknown; skip?: 'plans' | 'plan' } = {}) {
  TestBed.configureTestingModule({
    imports: [PlanPage],
    providers: [provideHttpClient(withInterceptors([apiInterceptor])), provideHttpClientTesting(), provideRouter([{ path: '**', children: [] }])],
  });
  TestBed.inject(AuthService).session.set({ username: 'u', role, csrf_token: 'csrf-' + role, expires_at: '2026-10-18T23:00:00Z' });
  http = TestBed.inject(HttpTestingController);
  const f = TestBed.createComponent(PlanPage);
  f.detectChanges();
  const el = f.nativeElement as HTMLElement;
  await ok(f, at('/plans/inputs'), inputsBody(o.inputs));
  const pr = at('/plans');
  if (o.skip === 'plans') return { f, el, pr };
  await ok(f, pr, o.plans ?? [planRef()]);
  if (o.skip === 'plan') return { f, el, pr };
  await ok(f, at(`/plans/${PLAN_ID}`), header());
  const rr = at(`/plans/${PLAN_ID}/results`);
  await ok(f, rr, resultsBody());
  return { f, el, pr, rr };
}
afterEach(() => http?.verify());

describe('Planificar compras: lectura', () => {
  it('muestra el encabezado, la franja de supuestos y 50 productos con ceros; sin total general ni «simulado»', async () => {
    const { el, pr, rr } = await open();
    expect(pr.request.params.get('month')).toBe('2026-11');
    expect(rr!.request.params.get('page_size')).toBe('50');
    expect(el.querySelectorAll('h1').length).toBe(1);
    expect(txt(el, 'page-title')).toBe('Compra recomendada');
    expect(txt(el, 'plan-band')).toContain('Plan de compra bajo supuestos');
    expect(el.querySelectorAll('[data-testid="plan-table"] tbody tr').length).toBe(50);
    expect(cell(el, '003230000', 'code')).toBe('003230000');      // código como texto con ceros
    expect(cell(el, '003230001', 'unit')).toContain('Caja de 12');
    expect(cell(el, '003230007', 'forecast')).toBe('0');            // cero previsto conservado
    expect(txt(el, 'plan-legend')).toContain('sin limitar por stock');
    expect(el.textContent).not.toMatch(/simulad/i);
    expect(el.textContent).not.toMatch(/Total general:|Total:|PEN|S\//);
    expect(txt(el, 'plan-units-note')).toContain('no se suman entre productos');
    expect(el.querySelector('.table-wrap table')).toBeTruthy();
    expect(el.querySelectorAll('.btn:not(.secondary)').length).toBe(1);   // lector: solo «Buscar»
    expect(el.querySelector('app-plan-form')).toBeNull();
  });

  it('el aviso de corte y la procedencia salen de la API (30/09, conteo con fecha, hora y almacén, distancias)', async () => {
    const { el } = await open();
    expect(txt(el, 'plan-cutoff')).toContain('30 de septiembre de 2026');
    expect(txt(el, 'plan-cutoff')).toContain('desconocido, no es cero');
    expect(txt(el, 'src-orders')).toContain('En este escenario no llegan otros pedidos (supuesto)');
    expect(txt(el, 'src-sales')).toContain('30 de septiembre de 2026');
    expect(txt(el, 'src-count')).toContain('18/10/2026 a las 17:00');
    expect(txt(el, 'src-count')).toContain('Almacén Principal (almacén 1)');
    expect(txt(el, 'src-count')).not.toMatch(/simulad/i);
    expect(txt(el, 'src-projection')).toContain('no son ventas observadas');
    expect(txt(el, 'src-params')).toContain('7 y 14 días');
    expect(txt(el, 'src-params')).toContain('reserva 7 días');
    expect(txt(el, 'src-distance')).toContain('18 días');
    expect(txt(el, 'src-distance')).toContain('32 días');
    expect(txt(el, 'src-distance')).toContain('61 días');
  });

  it('estados en palabras sencillas: un 0 calculado se explica y null nunca se muestra como 0', async () => {
    const { el } = await open();
    expect(cell(el, '003230000', 'buy-7')).toContain('0 (no hace falta comprar)');
    expect(cell(el, '003230000', 'buy-7')).toContain('Cubre noviembre');
    expect(cell(el, '003230001', 'buy-7')).toContain('74');
    const nl = cell(el, '003230001', 'buy-14');
    expect(nl).toBe('No llega a tiempo');
    expect(nl).not.toMatch(/\b0\b/);
    expect(cell(el, '003230001', 'arrival-14')).toBe('No llega en el mes');
    expect(cell(el, '003230001', 'start-14')).toBe('No se puede calcular');
    expect(cell(el, '003230001', 'short-14')).toBe('No se puede calcular');
    expect(cell(el, '003230002', 'buy-14')).toContain('Llega tarde: faltarían 14 unidades');
    expect(cell(el, '003230003', 'buy-7')).toBe('No se puede calcular');
    expect(cell(el, '003230003', 'count')).toBe('No informado');
    expect(cell(el, '003230003', 'forecast')).toBe('No se puede calcular');   // forecast null del servidor: nunca 0
    expect(cell(el, '003230004', 'buy-7')).toContain('60');
    expect(cell(el, '003230004', 'arrival-7')).toContain('25/10/2026');
    expect(cell(el, '003230004', 'start-14')).toBe('14');
  });

  it('los filtros y la paginación se piden al servidor (q, status, sort, page) y la tabla no se filtra en el navegador', async () => {
    const { f, el } = await open();
    await typeIn(f, el, 'plan-q', ' 003230004 ');
    await click(f, el, 'plan-search');
    let r = at(`/plans/${PLAN_ID}/results`);
    expect(r.request.params.get('q')).toBe('003230004');
    expect(r.request.params.get('page')).toBe('1');
    await ok(f, r, resultsBody({ items: [item(4)], total: 1 }));
    expect(el.querySelectorAll('[data-testid="plan-table"] tbody tr').length).toBe(1);

    await typeIn(f, el, 'plan-status', 'LLEGA_TARDE', 'change');
    r = at(`/plans/${PLAN_ID}/results`);
    expect(r.request.params.get('status')).toBe('LLEGA_TARDE');
    expect(r.request.params.get('q')).toBe('003230004');
    await ok(f, r, resultsBody({ items: [], total: 0 }));
    expect(q(el, 'plan-no-match')).toBeTruthy();

    await typeIn(f, el, 'plan-sort', '-forecast', 'change');
    r = at(`/plans/${PLAN_ID}/results`);
    expect(r.request.params.get('sort')).toBe('-forecast');
    await ok(f, r, resultsBody({ items: items().slice(0, 25), page: 1, page_size: 25, total: 60, has_more: true }));
    await click(f, el, 'next');
    r = at(`/plans/${PLAN_ID}/results`);
    expect(r.request.params.get('page')).toBe('2');
    await ok(f, r, resultsBody({ items: items().slice(0, 25), page: 2, page_size: 25, total: 60, has_more: false }));
  });

  it('«Entender la compra» reproduce la cantidad (ejemplo 2 del contrato) y compara los dos plazos', async () => {
    const { f, el } = await open();
    expect(q(el, 'plan-explain')).toBeNull();
    const row = el.querySelector('tr[data-sku="003230004"]')!;
    (row.querySelector('[data-testid="plan-understand"]') as HTMLElement).click();
    await settle(f);
    const d = at(`/plans/${PLAN_ID}/results/003230004`);
    await ok(f, d, detailBody());
    const panel = q(el, 'plan-explain')!;
    expect(panel.querySelector('h2')!.textContent).toBe('Entender la compra');
    expect(txt(panel, 'ex-forecast')).toContain('sin limitar por stock');
    expect(txt(panel, 'ex-forecast')).toContain('56 unidades vendidas en 28 días válidos');
    const s7 = Array.from(q(panel, 'ex-steps-7')!.querySelectorAll('li')).map((li) => (li.textContent ?? '').replace(/\s+/g, ' ').trim());
    const values = s7.map((t) => /= (\S+)$/.exec(t)?.[1]);
    expect(values).toEqual(['40', '12', '28', '14', '60', '14', '88', '28', '60', '60']);
    // 40 - 12 = 28 ; 14 + 60 + 14 = 88 ; 88 - 28 = 60 (los pasos entregados por la API cuadran con la compra)
    expect(Number(values[0]) - Number(values[1])).toBe(Number(values[2]));
    expect(Number(values[3]) + Number(values[4]) + Number(values[5])).toBe(Number(values[6]));
    expect(Number(values[6]) - Number(values[7])).toBe(Number(values[8]));
    expect(txt(q(panel, 'ex-lead-7')!, 'ex-buy')).toBe('Compra recomendada: 60');
    expect(txt(q(panel, 'ex-lead-14')!, 'ex-buy')).toBe('Compra recomendada: 60');
    expect(q(panel, 'ex-lead-14')!.textContent).toContain('Llega el 1 de noviembre de 2026');
    expect(txt(q(panel, 'ex-lead-7')!, 'ex-served')).toContain('Ventas que podrían atenderse en este escenario: 60');
    expect(txt(q(panel, 'ex-lead-7')!, 'ex-served')).toContain('Ventas previstas sin limitar por stock: 60');
    const det = q(panel, 'ex-daily-7') as HTMLDetailsElement;
    expect(det.open).toBe(false);
    expect(det.querySelectorAll('tbody tr').length).toBe(3);
    expect(det.querySelector('table caption')).toBeTruthy();
    expect(det.querySelector('th[scope="row"]')!.textContent).toBe('19/10/2026');
    expect(det.textContent).toContain('Disponible');
  });

  it('un plan con varias versiones ofrece una lista corta y cambia de plan', async () => {
    const other = 'plan-2026-11-d20261018-ffffffffffff';
    const { f, el } = await open('lector', { plans: [planRef(), planRef(other, { created_at: '2026-10-17T10:00:00-05:00' })] });
    const sel = q(el, 'plan-version') as HTMLSelectElement;
    expect(sel.options.length).toBe(2);
    await typeIn(f, el, 'plan-version', other, 'change');
    await ok(f, at(`/plans/${other}`), header());
    await ok(f, at(`/plans/${other}/results`), resultsBody());
    expect(el.querySelectorAll('[data-testid="plan-table"] tbody tr').length).toBe(50);
  });

  it('sin plan para el mes: mensaje claro y el lector no ve el formulario', async () => {
    const { el } = await open('lector', { plans: { items: [], unavailable_reason: 'SIN_PLAN' }, skip: 'plan' });
    expect(el.textContent).toContain('Todavía no se generó un plan para este mes');
    expect(el.querySelector('app-plan-form')).toBeNull();
    expect(q(el, 'plan-generate')).toBeNull();
    expect(el.querySelector('[data-state="empty"]')).toBeTruthy();
  });

  it('error al cargar: «Reintentar» hace una sola petición', async () => {
    const { f, el } = await open('lector', { skip: 'plans' }).then(async (x) => { await fail(x.f, x.pr, 500); return x; });
    expect(el.querySelector('[data-state="error"]')).toBeTruthy();
    expect(el.textContent).toContain('Servicio no disponible');
    const btn = Array.from(el.querySelectorAll('[data-state="error"] button')).find((b) => b.textContent === 'Reintentar') as HTMLElement;
    btn.click();
    await settle(f);
    const retry = at('/plans');
    await ok(f, retry, [planRef()]);
    await ok(f, at(`/plans/${PLAN_ID}`), header());
    await ok(f, at(`/plans/${PLAN_ID}/results`), resultsBody());
    expect(el.querySelectorAll('[data-testid="plan-table"] tbody tr').length).toBe(50);
  });

  it('403: mensaje de permiso sin datos', async () => {
    TestBed.configureTestingModule({
      imports: [PlanPage],
      providers: [provideHttpClient(withInterceptors([apiInterceptor])), provideHttpClientTesting(), provideRouter([{ path: '**', children: [] }])],
    });
    http = TestBed.inject(HttpTestingController);
    const f = TestBed.createComponent(PlanPage);
    f.detectChanges();
    await fail(f, at('/plans/inputs'), 403, { error: { code: 'PROHIBIDO', message: 'x' } });
    const el = f.nativeElement as HTMLElement;
    expect(txt(el, 'plan-forbidden')).toContain('No tienes permiso');
    expect(el.querySelector('table')).toBeNull();
  });

  it('la ruta existe, es perezosa y se llama «Compra recomendada»', () => {
    const r = routes.find((x) => x.canActivate)!.children!.find((x) => x.path === 'planificar')!;
    expect(r.title).toBe('Compra recomendada');
    expect(typeof r.loadComponent).toBe('function');
  });
});

describe('Planificar compras: administrador', () => {
  it('ve el formulario con el supuesto visible y un único botón principal', async () => {
    const { el } = await open('admin');
    expect(q(el, 'plan-form')).toBeTruthy();
    expect(txt(el, 'pf-assumption')).toContain('No llegan otros pedidos (supuesto)');
    expect(el.querySelectorAll('.btn:not(.secondary)').length).toBe(1);
    expect(txt(el, 'plan-generate')).toBe('Generar plan');
    expect(el.querySelectorAll('h1').length).toBe(1);
    expect((q(el, 'pf-leads') as HTMLInputElement).value).toBe('7, 14');
    expect((q(el, 'pf-month') as HTMLSelectElement).options.length).toBe(2);
  });

  it('no agrega un pedido sin fecha de llegada; con fecha lo agrega y lo muestra', async () => {
    const { f, el } = await open('admin');
    await typeIn(f, el, 'po-code', '003230004');
    await typeIn(f, el, 'po-units', '30');
    await click(f, el, 'po-add');
    expect(txt(el, 'po-error')).toContain('sin fecha no se admite');
    expect(el.querySelectorAll('[data-testid="pf-order"]').length).toBe(0);
    await typeIn(f, el, 'po-arrival', '2026-10-18');
    await click(f, el, 'po-add');
    expect(txt(el, 'po-error')).toContain('posterior a la fecha del conteo');
    await typeIn(f, el, 'po-arrival', '2026-11-05');
    await click(f, el, 'po-add');
    expect(q(el, 'po-error')).toBeNull();
    expect(txt(el, 'pf-order')).toContain('003230004');
    expect(txt(el, 'pf-order')).toContain('30 unidades');
    expect(txt(el, 'pf-order')).toContain('05/11/2026');
    expect(txt(el, 'pf-order')).toContain('Reportada');
    expect(txt(el, 'pf-assumption')).toContain('Se consideran los pedidos declarados abajo; no llegan otros adicionales (supuesto)');
  });

  it('valida antes de enviar (plazos fuera de rango) y bloquea el botón', async () => {
    const { f, el } = await open('admin');
    await typeIn(f, el, 'pf-leads', '7, 90');
    expect((q(el, 'plan-generate') as HTMLButtonElement).disabled).toBe(true);
    expect(txt(el, 'pf-errors')).toContain('entre 1 y 60');
    await typeIn(f, el, 'pf-leads', '7, 14');
    expect((q(el, 'plan-generate') as HTMLButtonElement).disabled).toBe(false);
  });

  it('Generar plan envía el cuerpo exacto, sigue el trabajo y al terminar recarga el plan', async () => {
    const { f, el } = await open('admin');
    await typeIn(f, el, 'po-code', '003230004');
    await typeIn(f, el, 'po-units', '30');
    await typeIn(f, el, 'po-arrival', '2026-11-05');
    await typeIn(f, el, 'po-nature', 'ASUMIDA', 'change');
    await click(f, el, 'po-add');
    await click(f, el, 'plan-generate');
    const post = http.expectOne((r) => r.method === 'POST' && r.url === `${API}/plans`);
    expect(post.request.body).toEqual({
      month: '2026-11', decision_date: '2026-10-18', lead_days: [7, 14], reserve_days: 7, min_order: 1, order_multiple: 1,
      pending_orders: [{ producto_id: '003230004', units: 30, arrival_date: '2026-11-05', nature: 'ASUMIDA' }],
    });
    expect(post.request.headers.get('X-CSRF-Token')).toBe('csrf-admin');
    const newId = 'plan-2026-11-d20261018-aaaaaaaaaaaa';
    await ok(f, post, { plan_id: newId, job_id: 'job-1', status: 'queued', reused: false });
    const job = at('/jobs/job-1');
    await ok(f, job, { job_id: 'job-1', type: 'generate_plan', status: 'running', stage: 'running' });
    expect(txt(el, 'plan-job-status')).toBe('En curso');
    // el sondeo sigue cada 2 s: se fuerza con el temporizador real acortado
    await new Promise((r) => setTimeout(r, 2100));
    const job2 = at('/jobs/job-1');
    await ok(f, job2, { job_id: 'job-1', type: 'generate_plan', status: 'completed', result: { plan_id: newId } });
    expect(txt(el, 'plan-job-status')).toBe('Terminado');
    const pr = at('/plans');
    await ok(f, pr, [planRef(newId), planRef()]);
    await ok(f, at(`/plans/${newId}`), header());
    await ok(f, at(`/plans/${newId}/results`), resultsBody());
    expect((q(el, 'plan-version') as HTMLSelectElement).value).toBe(newId);
    expect(el.querySelectorAll('[data-testid="plan-table"] tbody tr').length).toBe(50);
  });

  it('un reenvío idéntico muestra que se reutilizó el plan y no sigue ningún trabajo', async () => {
    const { f, el } = await open('admin');
    await click(f, el, 'plan-generate');
    const post = http.expectOne((r) => r.method === 'POST' && r.url === `${API}/plans`);
    await ok(f, post, { plan_id: PLAN_ID, job_id: 'job-0', status: 'completed', reused: true });
    expect(txt(el, 'plan-reused')).toContain('se reutilizó');
    await ok(f, at('/plans'), [planRef()]);
    await ok(f, at(`/plans/${PLAN_ID}`), header());
    await ok(f, at(`/plans/${PLAN_ID}/results`), resultsBody());
  });

  it('un error 422 se explica en palabras y permite reintentar con una sola petición', async () => {
    const { f, el } = await open('admin');
    await click(f, el, 'plan-generate');
    const post = http.expectOne((r) => r.method === 'POST');
    await fail(f, post, 422, { error: { code: 'ENTRADA_INVALIDA', message: 'La fecha de decisión no puede ser anterior al conteo.' } });
    expect(txt(el, 'plan-gen-error')).toContain('El servidor no aceptó los datos del plan');
    expect(txt(el, 'plan-gen-error')).toContain('La fecha de decisión no puede ser anterior al conteo.');
    await click(f, el, 'plan-retry');
    const again = http.expectOne((r) => r.method === 'POST');
    again.flush({ plan_id: PLAN_ID, job_id: 'j', status: 'completed', reused: true });
    await settle(f);
    await ok(f, at('/plans'), [planRef()]);
    await ok(f, at(`/plans/${PLAN_ID}`), header());
    await ok(f, at(`/plans/${PLAN_ID}/results`), resultsBody());
    expect(q(el, 'plan-gen-error')).toBeNull();
  });

  it('un trabajo fallido se dice en palabras sencillas y ofrece Reintentar', async () => {
    const { f, el } = await open('admin');
    await click(f, el, 'plan-generate');
    await ok(f, http.expectOne((r) => r.method === 'POST'), { plan_id: 'plan-x', job_id: 'job-9', status: 'queued', reused: false });
    await ok(f, at('/jobs/job-9'), { job_id: 'job-9', type: 'generate_plan', status: 'failed', error: { code: 'X' } });
    expect(txt(el, 'plan-job-status')).toBe('No se pudo completar');
    expect(txt(el, 'plan-job-error')).toContain('Puedes intentarlo de nuevo');
    expect(q(el, 'plan-retry')).toBeTruthy();
  });

  it('con plan vacío (SIN_PLAN) el administrador ve el formulario', async () => {
    const { el } = await open('admin', { plans: { items: [], unavailable_reason: 'SIN_PLAN' }, skip: 'plan' });
    expect(el.textContent).toContain('Todavía no se generó un plan para este mes');
    expect(q(el, 'plan-form')).toBeTruthy();
    expect(el.querySelectorAll('.btn:not(.secondary)').length).toBe(1);
  });
});
