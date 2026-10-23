// T20: Compra recomendada (existencia reconstruida), comparación de versiones y Existencias.
// Los cuerpos reproducen la FORMA de docs/T20_CONTRATO_ACTUALIZACION_V2.md §3; las cifras son fixtures, no resultados reales.
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting, TestRequest } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { apiInterceptor } from '../core/http.interceptor';
import { AuthService } from '../core/auth.service';
import { routes } from '../app.routes';
import { PlanPage } from './plan.page';
import { StockPage } from './stock.page';

const API = '/api/v1';
const V1 = 'plan-2026-11-d20261018-aaaaaaaaaaaa';
const V2 = 'plan-2026-11-d20261021-bbbbbbbbbbbb';
let http: HttpTestingController;

const CLOSING = '2026-10-20T23:59:59-05:00';
const BASE = '2026-10-18T17:00:00-05:00';
const LAST = '2026-10-21T16:26:38-05:00';
const WH = { id: '1', name: 'Almacén Principal' };
const ORDERS_TEXT = 'No hay pedidos adicionales por recibir registrados en este plan; se supone que no llegan otros (supuesto, sin confirmar con la empresa).';
const CONF = [
  { code: 'COMPRAS_11452_11455', status: 'PENDIENTE', text: 'Confirmar si las compras 11452 y 11455 ya llegaron o siguen por recibir.' },
  { code: 'DIFERENCIAS_INVENTARIO', status: 'PENDIENTE', text: 'Hay productos con diferencia entre el sistema y la reconstrucción.', products: ['1000002'] },
];
const DISC = { difference: -3, system_stock: '37', reconstructed: '40', compared_at_local: LAST };

const summary = (id: string, version: number) => ({
  plan_id: id, month: '2026-11', decision_date: '2026-10-21', lead_days: [7, 14], status: 'completed', created_at: '2026-10-21T18:30:00-05:00',
  dataset_id: 'plds-x', snapshot_id: 'invrec-20261020-abc', counts: { products: 2 }, version,
});
const header = (id: string, version: number) => ({
  ...summary(id, version),
  dates: { sales_cutoff: '2026-10-20', count_date: '2026-10-20', count_as_of_local: CLOSING, decision_date: '2026-10-21', month_start: '2026-11-01', month_end: '2026-11-30' },
  params: { month: '2026-11', decision_date: '2026-10-21', lead_days: [7, 14], reserve_days: 7, min_order: 1, order_multiple: 1, pending_orders: [] },
  dataset: { dataset_id: 'plds-x', sales_cutoff: '2026-10-20' },
  snapshot: { snapshot_id: 'invrec-20261020-abc', as_of_local: CLOSING, warehouse: WH, kind: 'RECONSTRUIDO', base_count_as_of_local: BASE, last_movement_local: LAST, discrepancy_products: ['1000002'] },
  confirmations: CONF,
  assumptions: [{ code: 'PEDIDOS_PENDIENTES', nature: 'SUPUESTO', text: ORDERS_TEXT }],
  warnings: [], provenance: { initial_stock: 'EXISTENCIA_RECONSTRUIDA_CIERRE_2026-10-20' },
});
const scen = () => ({
  lead_days: 7, arrival_date: '2026-10-28', status: 'OK', reason: null, purchase_qty: 60, stock_month_start: '14', shortage_before_month: '0', shortage_month: '0', served_month: '60',
});
const item = (code: string, disc: object | null) => ({
  producto_id: code, producto: 'PRODUCTO ' + code, categoria: 'X', unidad_descripcion: 'Un frasco', status: 'OK',
  forecast: { daily: '2', month_total: '60', month_days: 30 }, count_stock: { libre: 40, as_of_local: CLOSING },
  stock_provenance: { kind: 'RECONSTRUIDO', base_count: 38, movements_net_to_closing: 2, discrepancy: disc },
  scenarios: { '7': scen(), '14': { ...scen(), arrival_date: '2026-11-04' } },
});
const results = (id: string) => ({
  plan: summary(id, 2), items: [item('1000001', null), item('1000002', DISC)], page: 1, page_size: 50, total: 2, has_more: false,
  status_counts: { all: 2, OK: 2, LLEGA_TARDE: 0, NO_LLEGA_A_TIEMPO: 0, NO_CALCULABLE: 0 },
});

async function settle(f: ComponentFixture<unknown>) { f.detectChanges(); await f.whenStable(); f.detectChanges(); }
async function ok(f: ComponentFixture<unknown>, r: TestRequest, b: unknown) { r.flush(b as object); await settle(f); }
const at = (path: string) => http.expectOne((r) => r.url === `${API}${path}`);
const q = (el: HTMLElement, id: string) => el.querySelector(`[data-testid="${id}"]`) as HTMLElement | null;
const txt = (el: HTMLElement, id: string) => (q(el, id)?.textContent ?? '').replace(/\s+/g, ' ').trim();
afterEach(() => http?.verify());

async function openPlan() {
  TestBed.configureTestingModule({
    imports: [PlanPage],
    providers: [provideHttpClient(withInterceptors([apiInterceptor])), provideHttpClientTesting(), provideRouter([{ path: '**', children: [] }])],
  });
  TestBed.inject(AuthService).session.set({ username: 'u', role: 'lector', csrf_token: 'c', expires_at: '2026-10-21T23:00:00Z' });
  http = TestBed.inject(HttpTestingController);
  const f = TestBed.createComponent(PlanPage);
  f.detectChanges();
  const el = f.nativeElement as HTMLElement;
  await ok(f, at('/plans/inputs'), {
    dataset: { dataset_id: 'plds-x', sales_cutoff: '2026-10-20' }, snapshot: { snapshot_id: 'invrec-20261020-abc', as_of_local: CLOSING, warehouse: WH, kind: 'RECONSTRUIDO' },
    defaults: { month: '2026-11', decision_date: '2026-10-21', lead_days: [7, 14], reserve_days: 7, min_order: 1, order_multiple: 1, pending_orders: [] },
    limits: { decision_min: '2026-10-21', decision_max: '2026-11-30', months: ['2026-11'], lead_min: 1, lead_max: 60, max_leads: 4, horizon_days: 120 },
  });
  await ok(f, at('/plans'), { items: [summary(V2, 2), summary(V1, 1)] });
  await ok(f, at(`/plans/${V2}`), header(V2, 2));
  await ok(f, at(`/plans/${V2}/results`), results(V2));
  return { f, el };
}

describe('T20 Compra recomendada con existencia reconstruida', () => {
  it('título, columnas, procedencia reconstruida y configuración de reposición', async () => {
    const { el } = await openPlan();
    expect(txt(el, 'page-title')).toBe('Compra recomendada');
    const heads = Array.from(el.querySelectorAll('[data-testid="plan-table"] thead th')).map((h) => (h.textContent ?? '').replace(/\s+/g, ' ').trim());
    expect(heads.some((h) => h.startsWith('Venta prevista del mes'))).toBe(true);
    expect(heads).toContain('Existencias');
    expect(heads).toContain('Stock al 1/11');
    expect(heads).toContain('Comprar');
    const src = txt(el, 'src-count');
    expect(src).toContain('Existencia reconstruida al cierre del 20/10/2026 (conteo reportado 18/10/2026 a las 17:00 + movimientos del sistema)');
    expect(src).not.toContain('Conteo reportado por la empresa:');
    expect(src).toContain('21/10/2026 a las 16:26');
    expect(txt(el, 'src-params')).toContain('Configuración de reposición');
    expect(txt(el, 'src-params')).toContain('sin confirmar con el proveedor');
  });

  it('el supuesto de pedidos es el texto de la API (sin afirmar que no existen pedidos)', async () => {
    const { el } = await openPlan();
    expect(txt(el, 'src-orders')).toContain(ORDERS_TEXT);
    expect(txt(el, 'src-orders')).toContain(ORDERS_TEXT);
    expect(el.textContent).not.toContain('En este escenario no llegan otros pedidos');
  });

  it('las confirmaciones PENDIENTES salen en un aviso único', async () => {
    const { el } = await openPlan();
    expect(el.querySelectorAll('[data-testid="plan-confirmations"]').length).toBe(1);
    const t = txt(el, 'plan-confirmations');
    expect(t).toContain('compras 11452 y 11455');
    expect(t).toContain('diferencia entre el sistema y la reconstrucción');
    expect(el.querySelectorAll('[data-testid="plan-confirmations"] li').length).toBe(2);
  });

  it('el indicador «Diferencia con el sistema» aparece solo en el producto con discrepancia (1 de 2)', async () => {
    const { f, el } = await openPlan();
    expect(el.querySelectorAll('[data-testid="plan-diff-chip"]').length).toBe(1);
    expect(el.querySelector('tr[data-sku="1000001"] [data-testid="plan-diff-chip"]')).toBeNull();
    const t = (el.querySelector('tr[data-sku="1000002"] [data-testid="plan-diff-text"]')?.textContent ?? '').replace(/\s+/g, ' ');
    expect(t).toContain('el sistema indica 37');
    expect(t).toContain('reconstruida es 40');
    expect(t).toContain('21/10/2026 a las 16:26');
    expect(t).toContain('no se ajustó ninguna cantidad');
    expect(f).toBeTruthy();
  });

  it('el panel del producto repite la diferencia solo para el afectado y muestra la procedencia', async () => {
    const { f, el } = await openPlan();
    (el.querySelector('tr[data-sku="1000001"] [data-testid="plan-understand"]') as HTMLElement).click();
    await settle(f);
    await ok(f, at(`/plans/${V2}/results/1000001`), { ...item('1000001', null), scenarios: item('1000001', null).scenarios });
    expect(q(el, 'ex-diff')).toBeNull();
    expect(txt(el, 'ex-prov')).toContain('Conteo base 38');
    expect(txt(el, 'plan-explain')).toContain('Existencia inicial (cierre del 20/10/2026): 40');
    (el.querySelector('tr[data-sku="1000002"] [data-testid="plan-understand"]') as HTMLElement).click();
    await settle(f);
    await ok(f, at(`/plans/${V2}/results/1000002`), item('1000002', DISC));
    expect(txt(el, 'ex-diff')).toContain('Diferencia con el sistema');
  });

  it('«Comparar con otra versión» llama a GET /plans/{a}/compare/{b} y muestra previsión y compra por producto con la nota de fechas', async () => {
    const { f, el } = await openPlan();
    expect(q(el, 'cmp-table')).toBeNull();
    (q(el, 'plan-compare-btn') as HTMLElement).click();
    await settle(f);
    const side = (m: string, p: number) => ({ forecast_daily: '2', month_total: m, libre: 40, purchase: { '7': p, '14': p + 10 }, status: 'OK' });
    await ok(f, at(`/plans/${V2}/compare/${V1}`), {
      base: { ...summary(V2, 2) }, other: { ...summary(V1, 1) }, summary: { products: 2 }, note: 'Existencias de fechas distintas.',
      items: [
        { producto_id: '1000001', producto: 'PRODUCTO 1000001', a: side('60', 50), b: side('55', 45), delta: { month_total: '5' } },
        { producto_id: '1000002', producto: 'PRODUCTO 1000002', a: side('60', 50), b: null },
      ],
    });
    expect(txt(el, 'cmp-note')).toContain('fechas distintas');
    const row = (el.querySelector('[data-testid="cmp-table"] tr[data-sku="1000001"]')?.textContent ?? '').replace(/\s+/g, ' ');
    expect(row).toContain('60 → 55');
    expect(row).toContain('50 → 45');
    expect(row).toContain('60 → 55');
    expect((el.querySelector('[data-testid="cmp-table"] tr[data-sku="1000002"] [data-col="forecast"]')?.textContent ?? '')).toContain('60 → No se puede calcular');
  });

  it('un error en la comparación se informa y permite reintentar', async () => {
    const { f, el } = await openPlan();
    (q(el, 'plan-compare-btn') as HTMLElement).click();
    await settle(f);
    at(`/plans/${V2}/compare/${V1}`).flush({ error: { code: 'X', message: 'x' } }, { status: 500, statusText: 'x' });
    await settle(f);
    expect(q(el, 'plan-compare')!.textContent).toContain('Reintentar');
    expect(q(el, 'cmp-table')).toBeNull();
  });
});

// ---------- Existencias ----------
const stockSnap = () => ({
  snapshot_id: 'invrec-20261020-abc', kind: 'EXISTENCIA_RECONSTRUIDA', version: 1, status: 'current', as_of_local: CLOSING, warehouse: WH,
  base_count: { snapshot_id: 'invrep-1', as_of_local: BASE }, movements: { from_local: BASE, closing_local: CLOSING, last_movement_local: LAST },
  counts: { products: 50, discrepancies: 1 }, rule: 'existencia = conteo + entradas - salidas', confirmations: CONF,
});
const sItem = (code: string, disc: object | null) => ({
  producto_id: code, producto: 'PRODUCTO ' + code, categoria: 'X', unidad_descripcion: 'Un frasco', libre: 40, base_count: 38,
  movements: { entradas_cierre: 5, salidas_cierre: 3, entradas_ultimo_mov: 5, salidas_ultimo_mov: 6 },
  reconstructed_at_last_movement: 37, system_stock_at_last_movement: disc ? 34 : 37, system_reserved: 0, discrepancy: disc,
});
const stockBody = (items = [sItem('1000001', null), sItem('1000002', { difference: -3, compared_at_local: LAST })]) => ({
  snapshot: stockSnap(), items, page: 1, page_size: 50, total: items.length, has_more: false,
});
async function openStock(b: unknown = stockBody()) {
  TestBed.configureTestingModule({
    imports: [StockPage],
    providers: [provideHttpClient(withInterceptors([apiInterceptor])), provideHttpClientTesting(), provideRouter([{ path: '**', children: [] }])],
  });
  http = TestBed.inject(HttpTestingController);
  const f = TestBed.createComponent(StockPage);
  f.detectChanges();
  const first = at('/stock');
  if (b !== null) await ok(f, first, b);
  return { f, el: f.nativeElement as HTMLElement, first };
}

describe('T20 Existencias', () => {
  it('muestra la existencia reconstruida con procedencia, confirmaciones y enlace al conteo informado', async () => {
    const { el, first } = await openStock();
    expect(first.request.params.has('view')).toBe(false);
    expect(txt(el, 'page-title')).toBe('Existencias');
    expect(txt(el, 'stk-strip')).toContain('Existencia reconstruida (no es simulada) al cierre del 20/10/2026 (conteo reportado 18/10/2026 a las 17:00 + movimientos del sistema)');
    expect(txt(el, 'stk-age')).toContain('21/10/2026 a las 16:26');
    // T22: encabezados cortos con fechas del plan, pendientes y leyenda plegados
    const sh = Array.from(el.querySelectorAll('[data-testid="stk-table"] thead th')).map((h) => (h.textContent ?? '').replace(/\s+/g, ' ').trim());
    expect(sh).toEqual(['Producto', 'Conteo 18/10', 'Entradas', 'Salidas', 'Existencia al 20/10', 'Diferencia']);
    expect((q(el, 'stk-confirmations') as HTMLDetailsElement).open).toBe(false);
    expect((q(el, 'stk-legend') as HTMLDetailsElement).open).toBe(false);
    expect(txt(el, 'stk-confirmations')).toContain('2 pendientes de confirmar con la empresa');
    expect(el.querySelectorAll('[data-testid="stk-confirmations"]').length).toBe(1);
    expect(el.querySelectorAll('[data-testid="stk-table"] tbody tr').length).toBe(2);
    const r = el.querySelector('tr[data-sku="1000001"]')!;
    expect(r.querySelector('[data-col="base"]')!.textContent).toContain('38');
    expect(r.querySelector('[data-col="in"]')!.textContent).toContain('5');
    expect(r.querySelector('[data-col="free"]')!.textContent).toContain('40');
    expect(txt(el, 'stk-summary')).toBe('50 productos · 1 con diferencia respecto al sistema');
    const link = q(el, 'stk-to-count') as HTMLAnchorElement;
    expect(link.getAttribute('href')).toContain('/inventario');
  });

  it('la diferencia aparece solo en el producto afectado', async () => {
    const { el } = await openStock();
    expect(el.querySelectorAll('[data-testid="stk-diff-chip"]').length).toBe(1);
    expect(el.querySelector('tr[data-sku="1000001"] [data-testid="stk-diff-chip"]')).toBeNull();
    const t = (el.querySelector('tr[data-sku="1000002"] [data-testid="stk-diff-text"]')?.textContent ?? '').replace(/\s+/g, ' ');
    expect(t).toContain('El sistema indica 34');
    expect(t).toContain('la reconstrucción 37');
    expect(t).toContain('diferencia -3');
  });

  it('«solo diferencias» pide view=discrepancias y vuelve a la página 1', async () => {
    const { f, el } = await openStock();
    const cb = q(el, 'stk-only-diff') as HTMLInputElement;
    cb.checked = true; cb.dispatchEvent(new Event('change')); await settle(f);
    const r = at('/stock');
    expect(r.request.params.get('view')).toBe('discrepancias');
    expect(r.request.params.get('page')).toBe('1');
    await ok(f, r, stockBody([sItem('1000002', { difference: -3, compared_at_local: LAST })]));
    expect(el.querySelectorAll('[data-testid="stk-table"] tbody tr').length).toBe(1);
  });

  it('sin existencia cargada: estado vacío', async () => {
    const a = await openStock({ snapshot: null, items: [], page: 1, page_size: 50, total: 0, has_more: false });
    expect(a.el.textContent).toContain('Todavía no hay una existencia reconstruida cargada');
  });

  it('con error del servidor: aviso con reintento y sin tabla', async () => {
    const b = await openStock(null);
    b.first.flush({ error: { code: 'X', message: 'x' } }, { status: 500, statusText: 'x' });
    await settle(b.f);
    expect(b.el.textContent).toContain('Reintentar');
    expect(q(b.el, 'stk-table')).toBeNull();
  });

  it('sin permiso: aviso de permiso', async () => {
    const c = await openStock(null);
    c.first.flush({ error: { code: 'PROHIBIDO', message: 'x' } }, { status: 403, statusText: 'x' });
    await settle(c.f);
    expect(q(c.el, 'stk-forbidden')).toBeTruthy();
  });
});

describe('T20 rutas', () => {
  it('Existencias es una ruta perezosa nueva y las rutas anteriores se mantienen', () => {
    const prot = routes.find((r) => r.canActivate)!;
    const get = (p: string) => prot.children!.find((c) => c.path === p)!;
    expect(get('existencias').title).toBe('Existencias');
    expect(get('planificar').title).toBe('Compra recomendada');
    expect(get('recomendaciones').title).toContain('Evaluación académica');
    expect(get('inventario').loadComponent).toBeTruthy();
  });
});

describe('Piloto de presentación de «Compra recomendada» (22/10)', () => {
  const before = (a: HTMLElement | null, b: HTMLElement | null) => !!a && !!b && !!(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);

  it('orden: cabecera, parámetros, pendientes, filtros y tabla antes que las explicaciones desplegables', async () => {
    const { f, el } = await openPlan();
    (el.querySelector('tr[data-sku="1000001"] [data-testid="plan-understand"]') as HTMLElement).click();
    await settle(f);
    await ok(f, at(`/plans/${V2}/results/1000001`), item('1000001', null));
    const order = ['plan-head', 'plan-params', 'plan-confirmations', 'plan-filters', 'plan-table', 'plan-explain', 'plan-source'].map((id) => q(el, id));
    order.forEach((n, i) => { expect(n).not.toBeNull(); if (i) expect(before(order[i - 1], n)).toBe(true); });
    expect(before(q(el, 'plan-table'), q(el, 'plan-compare'))).toBe(true);
  });

  it('cabecera breve: mes, versión, decisión, fecha de ventas y existencias con procedencia', async () => {
    const { el } = await openPlan();
    expect((q(el, 'plan-month') as HTMLSelectElement).selectedOptions[0].textContent?.trim()).toBe('noviembre de 2026');
    expect(q(el, 'plan-version')).not.toBeNull();   // con varias versiones el selector ya muestra la versión: no se repite en la cabecera
    expect(q(el, 'head-version')).toBeNull();
    expect(txt(el, 'head-decision')).toBe('21/10/2026');
    expect(txt(el, 'head-sales')).toBe('20/10/2026');
    expect(txt(el, 'head-stock')).toContain('cierre del 20/10/2026');
    expect(txt(el, 'head-stock')).toContain('reconstruida');
  });

  it('explicaciones largas, comparación y pendientes cerradas por defecto; el aviso de supuestos es uno solo', async () => {
    const { el } = await openPlan();
    for (const id of ['plan-source', 'plan-compare', 'plan-confirmations']) {
      const d = q(el, id) as HTMLDetailsElement;
      expect(d.tagName).toBe('DETAILS');
      expect(d.open).toBe(false);
    }
    expect((el.textContent ?? '').match(/Plan de compra bajo supuestos/g)?.length).toBe(1);
    expect(txt(el, 'plan-confirmations')).toContain('2 pendientes de confirmar');
    expect(txt(el, 'plan-confirmations')).toContain('1 diferencia de inventario');
    expect(txt(el, 'src-orders')).toContain('Supuesto');
    expect(txt(el, 'src-orders')).toContain('sin confirmar con la empresa');
  });

  it('singular y legible: «1 producto» y la aclaración de decimales y miles', async () => {
    const { f, el } = await openPlan();
    const one = { ...results(V2), items: [item('1000001', null)], total: 1 };
    (q(el, 'plan-search') as HTMLElement).click();
    await settle(f);
    await ok(f, at(`/plans/${V2}/results`), one);
    expect(txt(el, 'plan-summary')).toContain('1 producto en este plan');
    expect(txt(el, 'plan-summary')).not.toContain('1 productos');
    expect(txt(el, 'plan-legend')).toContain('Decimales y miles');
  });

  it('«Entender la compra» da primero compra, llegada y faltantes y después el cálculo; el foco pasa al título', async () => {
    const { f, el } = await openPlan();
    (el.querySelector('tr[data-sku="1000001"] [data-testid="plan-understand"]') as HTMLElement).click();
    await settle(f);
    const d = item('1000001', null);
    d.scenarios['7'] = { ...d.scenarios['7'], explanation: [{ label: 'Paso', text: 'x', value: '1' }] } as never;
    await ok(f, at(`/plans/${V2}/results/1000001`), d);
    const card = q(el, 'ex-lead-7')!;
    expect(before(q(card, 'ex-buy'), q(card, 'ex-served'))).toBe(true);
    expect(before(q(card, 'ex-served'), q(card, 'ex-steps-7'))).toBe(true);
    expect(card.textContent).toContain('Llega el');
    expect(before(card.querySelector('.verdict'), q(card, 'ex-buy'))).toBe(true);
    await new Promise((r) => setTimeout(r, 5));
    expect(document.activeElement?.id).toBe('h-explain');
  });

  it('la pantalla usa todo el ancho (clase wide en <main>) solo mientras está abierta', async () => {
    const main = document.createElement('main');
    document.body.appendChild(main);
    try {
      const { f } = await openPlan();
      expect(main.classList.contains('wide')).toBe(true);
      f.destroy();
      expect(main.classList.contains('wide')).toBe(false);
    } finally { main.remove(); }
  });

  it('la fecha del encabezado «Stock al 1/MM» sigue al mes del plan (no queda fija en noviembre)', async () => {
    const { f, el } = await openPlan();
    const heads = () => Array.from(el.querySelectorAll('[data-testid="plan-table"] thead th')).map((h) => (h.textContent ?? '').replace(/\s+/g, ' ').trim());
    expect(heads()).toContain('Stock al 1/11');
    const page = f.componentInstance as PlanPage;
    page.hdr.state.set({ kind: 'data', data: { ...header(V2, 2), month: '2026-12' } as never });
    await settle(f);
    expect(heads()).toContain('Stock al 1/12');
    expect(heads()).not.toContain('Stock al 1/11');
    expect(txt(el, 'plan-legend')).toContain('Stock al 1/12');
  });
});

describe('«Entender la compra»: resumen del cálculo y explicación del plazo largo (22/10)', () => {
  const steps = (need: string, stock: string, buy: string) => [
    { label: 'Necesidad total', text: 'x', value: need }, { label: 'Menos el stock S', text: 'y', value: stock }, { label: 'Compra propuesta', text: 'z', value: buy }];
  const late = () => {
    const d = item('1000001', null) as Record<string, unknown>;
    d['scenarios'] = {
      '7': { ...scen(), purchase_qty: 25, served_month: '18.214', shortage_before_month: '4.25', shortage_month: '0', explanation: steps('24.893', '0', '25') },
      '14': { ...scen(), arrival_date: '2026-11-04', status: 'LLEGA_TARDE', purchase_qty: 21, served_month: '16.393', shortage_before_month: '6.679', shortage_month: '1.821', explanation: steps('20.643', '0', '21') },
    };
    return d;
  };
  async function openDetail(detail: unknown) {
    const { f, el } = await openPlan();
    (el.querySelector('tr[data-sku="1000001"] [data-testid="plan-understand"]') as HTMLElement).click();
    await settle(f);
    await ok(f, at(`/plans/${V2}/results/1000001`), detail);
    return { f, el };
  }

  it('cada plazo muestra visibles compra, llegada, ventas atendibles y faltantes; el cálculo detallado está cerrado y el resumen es una frase', async () => {
    const { el } = await openDetail(late());
    for (const l of ['7', '14']) {
      const card = q(el, 'ex-lead-' + l)!;
      expect(txt(card, 'ex-buy')).toBe('Compra recomendada: ' + (l === '7' ? '25' : '21'));
      expect(card.textContent).toContain('Llega el');
      expect(txt(card, 'ex-served')).toContain('Ventas que podrían atenderse en este escenario');
      expect(txt(card, 'ex-served')).toContain('Faltante en el mes');
      const d = q(card, 'ex-calc-' + l) as HTMLDetailsElement;
      expect(d.tagName).toBe('DETAILS');
      expect(d.open).toBe(false);
      expect(d.querySelector('summary')?.textContent?.trim()).toBe('Ver cálculo detallado');
      expect(d.querySelectorAll('ol li').length).toBe(3);
    }
    expect(txt(q(el, 'ex-lead-7')!, 'ex-summary-7')).toBe('Cómo se calculó: Se necesitan 24.893 unidades desde la llegada hasta fin de mes más 7 días de reserva; no hay stock disponible al llegar para descontar, y la compra propuesta es 25.');
    expect(txt(q(el, 'ex-lead-14')!, 'ex-summary-14')).toContain('Se necesitan 20.643 unidades');
  });

  it('la compra a 14 días menor porque vende menos: nota generada de los resultados, no equivalente con ahorro', async () => {
    const { el } = await openDetail(late());
    const notes = Array.from(el.querySelectorAll('[data-testid="ex-compare-note"]'));
    expect(notes.length).toBe(1);
    const t = (notes[0].textContent ?? '').replace(/\s+/g, ' ');
    expect(t).toContain('Con el plazo de 14 días se compra menos (21 frente a 25 con 7 días)');
    expect(t).toContain('llega el 4 de noviembre de 2026');
    expect(t).toContain('1.821 unidades de las ventas previstas sin atender');
    expect(t).toContain('podrían atenderse 16.393 frente a 18.214');
    expect(t).toContain('No es una opción equivalente con ahorro');
  });

  it('sin llegada tardía (resultados iguales o plazo largo que no atiende menos) no hay nota', async () => {
    const { el } = await openDetail(item('1000001', null));
    expect(el.querySelector('[data-testid="ex-compare-note"]')).toBeNull();
    const d = late() as { scenarios: Record<string, Record<string, unknown>> };
    d.scenarios['14'] = { ...d.scenarios['14'], status: 'OK', purchase_qty: 30, served_month: '18.214', shortage_month: '0' };
    const second = await (async () => { TestBed.resetTestingModule(); return openDetail(d); })();
    expect(second.el.querySelector('[data-testid="ex-compare-note"]')).toBeNull();
  });
});
