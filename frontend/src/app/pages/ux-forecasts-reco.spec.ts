// UX01: pruebas de «Ventas previstas» y «Reposición simulada» (sin backend real; fixtures de forma, no resultados).
import { Type } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting, TestRequest } from '@angular/common/http/testing';
import { Router, provideRouter } from '@angular/router';
import { apiInterceptor } from '../core/http.interceptor';
import { demoInterceptor } from '../core/demo';
import { AuthService } from '../core/auth.service';
import { ForecastsPage } from './forecasts.page';
import { RecommendationsPage } from './recommendations.page';
import { calcSteps, simpleSteps } from '../core/reco-calc';
import { Recommendation } from '../core/models';
import { forecast, page, recoNoSnap, recoOk, runSummary } from '../testing/fixtures';
import { realRecoDetail, realRecoPage, realRunSummary } from '../testing/real-shapes';
import { FINAL_ID, HIST_ID, finalForecasts, finalRecoPage, finalRun, genRun, histRun } from '../testing/final-shapes';
import { visibleText } from '../testing/mount';

interface M<T> { f: ComponentFixture<T>; http: HttpTestingController; el: HTMLElement }
let lastHttp: HttpTestingController | undefined;

async function mountAs<T>(cmp: Type<T>, url = '/x'): Promise<M<T>> {
  TestBed.configureTestingModule({
    imports: [cmp],
    providers: [provideHttpClient(withInterceptors([apiInterceptor, demoInterceptor])), provideHttpClientTesting(), provideRouter([{ path: '**', children: [] }])],
  });
  TestBed.inject(AuthService).session.set({ username: 'u', role: 'lector', csrf_token: 'c', expires_at: '2026-10-17T23:00:00Z' });
  await TestBed.inject(Router).navigateByUrl(url);
  const http = TestBed.inject(HttpTestingController);
  lastHttp = http;
  const f = TestBed.createComponent(cmp);
  f.detectChanges();
  return { f, http, el: f.nativeElement as HTMLElement };
}
const one = (http: HttpTestingController, path: string): TestRequest => http.expectOne((r) => r.url === path);
async function settle(f: ComponentFixture<unknown>) { f.detectChanges(); await f.whenStable(); f.detectChanges(); }
async function ok(f: ComponentFixture<unknown>, r: TestRequest, body: unknown) { r.flush(body as object); await settle(f); }
const q = (el: HTMLElement, id: string) => el.querySelector(`[data-testid="${id}"]`) as HTMLElement | null;
const txt = (el: HTMLElement, id: string) => (q(el, id)?.textContent ?? '').replace(/\s+/g, ' ').trim();
const click = async (f: ComponentFixture<unknown>, el: HTMLElement | null) => { (el as HTMLButtonElement).click(); await settle(f); };

afterEach(() => { lastHttp?.verify(); lastHttp = undefined; });

const genForecastRun = { ...runSummary, run_id: 'gen-1', kind: 'generated_baseline', is_active: false, origin: '2026-07-10', target_start: '2026-07-11', target_end: '2026-07-31', age_days_at_view: 3 };

describe('UX01 Ventas previstas', () => {
  it('un solo h1, barra de análisis, una sola petición a /runs; tabla corta con producto etiquetado, fecha en español y decimales', async () => {
    const m = await mountAs(ForecastsPage);
    await ok(m.f, one(m.http, '/api/v1/runs'), page([realRunSummary]));
    await ok(m.f, one(m.http, '/api/v1/forecasts'), page([{ ...forecast, sku: '1010004', entity_id: '1010004|1', categoria: 'HIGIENE CAPILAR', pred: { promedio_28: 2.5, rf_categoria_distribuido: 3, cero: 0 } }]));
    expect(m.el.querySelectorAll('h1').length).toBe(1);
    expect(txt(m.el, 'page-title')).toBe('Ventas previstas');
    expect(txt(m.el, 'analysis-name')).toBe('Ejemplo de julio');
    const cells = Array.from(m.el.querySelectorAll('[data-testid="forecast-table"] tbody tr td')).map((c) => c.textContent!.trim());
    expect(cells).toEqual(['Producto 1010004 · Higiene capilar', '11/07/2026', '2.5', '1']);
    const heads = Array.from(m.el.querySelectorAll('[data-testid="forecast-table"] thead th')).map((c) => c.textContent!.trim());
    expect(heads).toEqual(['Producto', 'Fecha', 'Cantidad estimada (unidades base)', 'Vendido (registrado)']);
    expect(txt(m.el, 'units-note')).toContain('unidades base');
    expect(txt(m.el, 'units-note')).toContain('28 días');
    expect(m.el.querySelector('[data-testid="forecast-help"] summary')?.textContent).toContain('Cómo leer esta tabla');
  });

  it('«Comparar métodos / ver detalles» muestra día de la previsión, tipo de historial, modelo experimental, control cero y evaluable', async () => {
    const m = await mountAs(ForecastsPage);
    await ok(m.f, one(m.http, '/api/v1/runs'), page([runSummary]));
    await ok(m.f, one(m.http, '/api/v1/forecasts'), page([forecast]));
    expect(txt(m.el, 'forecast-table')).not.toContain('Día de la previsión');
    expect(q(m.el, 'evaluable')).toBeNull();
    await click(m.f, q(m.el, 'toggle-details'));
    expect(q(m.el, 'toggle-details')!.getAttribute('aria-pressed')).toBe('true');
    const t = txt(m.el, 'forecast-table');
    for (const h of ['Día de la previsión', 'Tipo de historial', 'Modelo experimental', 'Control (siempre cero)', 'Evaluable', 'Identificador']) expect(t).toContain(h);
    expect(txt(m.el, 'evaluable')).toBe('Sí');
    const row = m.el.querySelector('[data-testid="forecast-table"] tbody tr')!.textContent!;
    expect(row).toContain('SKU-T1');
    expect(row).toContain('C1');
  });

  it('análisis creado: observado null NO es cero; mensaje claro y en detalles «no disponible», sin columna Vendido por defecto', async () => {
    const m = await mountAs(ForecastsPage, '/pronosticos?run=gen-1');
    await ok(m.f, one(m.http, '/api/v1/runs'), page([runSummary, genForecastRun]));
    const fr = one(m.http, '/api/v1/forecasts');
    expect(fr.request.params.get('run_id')).toBe('gen-1');
    await ok(m.f, fr, page([{ ...forecast, run_id: 'gen-1', observed: null, evaluable: null, pred: { promedio_28: 2.5, rf_categoria_distribuido: null, cero: 0 } }]));
    expect(txt(m.el, 'no-observed-note')).toContain('Aún no hay ventas registradas para comparar');
    expect(q(m.el, 'observed')).toBeNull();
    expect(q(m.el, 'insufficient')).toBeNull();
    expect(txt(m.el, 'analysis-name')).toContain('Análisis creado con ventas hasta el 10/07/2026');
    expect(txt(m.el, 'run-dates')).toContain('11/07/2026 al 31/07/2026');
    await click(m.f, q(m.el, 'toggle-details'));
    expect(txt(m.el, 'observed')).toBe('no disponible para esta corrida');
    expect(txt(m.el, 'evaluable')).toBe('no disponible para esta corrida');
    expect(txt(m.el, 'forecast-table')).not.toContain('Modelo experimental');
  });

  it('ejemplo histórico: un cero real sigue siendo 0; «no evaluable» no es 0; null no es 0', async () => {
    const m = await mountAs(ForecastsPage);
    await ok(m.f, one(m.http, '/api/v1/runs'), page([runSummary]));
    await ok(m.f, one(m.http, '/api/v1/forecasts'), page([
      { ...forecast, observed: 0, evaluable: true }, { ...forecast, entity_id: 'B', observed: null, evaluable: false }, { ...forecast, entity_id: 'C', observed: null, evaluable: null },
    ]));
    expect(Array.from(m.el.querySelectorAll('[data-testid="observed"]')).map((c) => c.textContent!.trim()))
      .toEqual(['0', 'no evaluable', 'no disponible para esta corrida']);
    expect(q(m.el, 'insufficient')).toBeTruthy();
  });

  it('evaluación: «Evaluación de agosto», advertencias visibles, tope 21/08 y filas con cohorte (en detalles); día sin registros = no evaluable', async () => {
    const m = await mountAs(ForecastsPage, '/pronosticos?run=' + FINAL_ID);
    await ok(m.f, one(m.http, '/api/v1/runs'), page([finalRun, histRun]));
    const fr = one(m.http, '/api/v1/forecasts');
    expect(fr.request.params.get('run_id')).toBe(FINAL_ID);
    await ok(m.f, fr, finalForecasts());
    expect(txt(m.el, 'analysis-name')).toBe('Evaluación de agosto');
    expect(m.el.textContent).not.toContain('T12');
    expect(txt(m.el, 'final-warnings')).toContain('WAPE no es exactitud');
    expect(txt(m.el, 'final-warnings')).toContain('no pronostica octubre');
    expect(txt(m.el, 'final-note')).toContain('no evaluable');
    expect(txt(m.el, 'final-note')).toContain('no pronostica octubre');
    expect((q(m.el, 'f-to') as HTMLInputElement).getAttribute('max')).toBe('2026-08-21');
    expect((q(m.el, 'f-from') as HTMLInputElement).getAttribute('min')).toBe('2026-08-01');
    expect(Array.from(m.el.querySelectorAll('[data-testid="observed"]')).map((c) => c.textContent!.trim())).toEqual(['2', 'no evaluable', '0']);
    await click(m.f, q(m.el, 'toggle-details'));
    expect(txt(m.el, 'forecast-table')).toContain('Modelo experimental');
  });

  it('no evaluación: tope 31/07 y sin advertencias de la evaluación', async () => {
    const m = await mountAs(ForecastsPage);
    await ok(m.f, one(m.http, '/api/v1/runs'), page([finalRun, histRun]));
    await ok(m.f, one(m.http, '/api/v1/forecasts'), page([]));
    expect((q(m.el, 'f-to') as HTMLInputElement).getAttribute('max')).toBe('2026-07-31');
    expect(q(m.el, 'final-warnings')).toBeNull();
    expect(txt(m.el, 'analysis-name')).toBe('Ejemplo de julio');
    expect(m.el.querySelector('[data-state="empty"]')?.textContent).toContain('No hay estimaciones');
  });

  it('«Ver por categoría» pide level=categoria desde la página 1 y rotula la categoría', async () => {
    const m = await mountAs(ForecastsPage);
    await ok(m.f, one(m.http, '/api/v1/runs'), page([runSummary]));
    await ok(m.f, one(m.http, '/api/v1/forecasts'), page([forecast]));
    expect(q(m.el, 'level-sku')!.getAttribute('aria-pressed')).toBe('true');
    await click(m.f, q(m.el, 'level-cat'));
    const r = one(m.http, '/api/v1/forecasts');
    expect(r.request.params.get('level')).toBe('categoria');
    expect(r.request.params.get('page')).toBe('1');
    await ok(m.f, r, page([{ ...forecast, level: 'categoria', entity_id: 'HIGIENE CAPILAR', sku: null, categoria: 'HIGIENE CAPILAR' }]));
    expect(q(m.el, 'level-cat')!.getAttribute('aria-pressed')).toBe('true');
    expect(m.el.querySelector('[data-testid="forecast-table"] tbody td')!.textContent).toBe('Higiene capilar');
    expect(txt(m.el, 'forecast-table')).toContain('Categoría');
  });

  it('el selector de análisis usa nombres comprensibles, conserva run en la URL, recarga desde la página 1 y no vuelve a pedir /runs', async () => {
    const m = await mountAs(ForecastsPage);
    await ok(m.f, one(m.http, '/api/v1/runs'), page([runSummary, genForecastRun]));
    const first = one(m.http, '/api/v1/forecasts');
    expect(first.request.params.has('run_id')).toBe(false);
    await ok(m.f, first, page([forecast]));
    const sel = q(m.el, 'run-select') as HTMLSelectElement;
    expect(Array.from(sel.options).map((o) => o.textContent)).toEqual(['Ejemplo de julio · en uso por defecto', 'Análisis creado con ventas hasta el 10/07/2026']);
    sel.value = 'gen-1';
    sel.dispatchEvent(new Event('change'));
    const again = one(m.http, '/api/v1/forecasts');
    expect(again.request.params.get('run_id')).toBe('gen-1');
    expect(again.request.params.get('page')).toBe('1');
    m.http.expectNone((r) => r.url === '/api/v1/runs');
    await ok(m.f, again, page([forecast]));
    expect(TestBed.inject(Router).url).toContain('run=gen-1');
  });

  it('filtros y paginación del servidor: código, categoría, fechas, tipo de historial (en más filtros)', async () => {
    const m = await mountAs(ForecastsPage);
    await ok(m.f, one(m.http, '/api/v1/runs'), page([runSummary]));
    await ok(m.f, one(m.http, '/api/v1/forecasts'), page([forecast], { total: 120, has_more: true }));
    await click(m.f, q(m.el, 'next'));
    const r2 = one(m.http, '/api/v1/forecasts');
    expect(r2.request.params.get('page')).toBe('2');
    await ok(m.f, r2, page([forecast], { page: 2, total: 120 }));
    const form = m.el.querySelector('form.filters') as HTMLFormElement;
    const set = (name: string, v: string) => { const i = form.querySelector(`[name="${name}"]`) as HTMLInputElement; i.value = v; i.dispatchEvent(new Event('input')); };
    set('sku', '1010004'); set('cat', 'HIGIENE'); set('coh', 'primaria'); set('from', '2026-07-12'); set('to', '2026-07-20');
    m.f.detectChanges();
    form.dispatchEvent(new Event('submit'));
    const r3 = one(m.http, '/api/v1/forecasts');
    const p = r3.request.params;
    expect([p.get('sku'), p.get('categoria'), p.get('cohorte'), p.get('from'), p.get('to'), p.get('page'), p.get('level')]).toEqual(['1010004', 'HIGIENE', 'primaria', '2026-07-12', '2026-07-20', '1', 'sku']);
    await ok(m.f, r3, page([forecast]));
  });

  it('error: mensaje, reintento válido y ninguna fila; no crea trabajos', async () => {
    const m = await mountAs(ForecastsPage);
    await ok(m.f, one(m.http, '/api/v1/runs'), page([runSummary]));
    one(m.http, '/api/v1/forecasts').flush({}, { status: 503, statusText: 'x' });
    await settle(m.f);
    expect(m.el.querySelector('[data-state="error"]')).toBeTruthy();
    expect(q(m.el, 'forecast-table')).toBeNull();
    await click(m.f, m.el.querySelector('[data-state="error"] button') as HTMLElement);
    await ok(m.f, one(m.http, '/api/v1/forecasts'), page([forecast]));
    expect(q(m.el, 'forecast-table')).toBeTruthy();
    m.http.expectNone((r) => r.method !== 'GET');
  });

  it('versión reemplazada: aviso breve en la pantalla', async () => {
    const m = await mountAs(ForecastsPage);
    await ok(m.f, one(m.http, '/api/v1/runs'), page([{ ...realRunSummary, status: 'superseded', quality_issue: { superseded_by: 'hist-NEW', reason: 'redondeo' } }]));
    await ok(m.f, one(m.http, '/api/v1/forecasts'), page([forecast]));
    expect(txt(m.el, 'analysis-replaced')).toContain('Esta versión fue reemplazada');
    expect(txt(m.el, 'forecast-replaced')).toContain('No uses sus resultados');
  });
});

describe('UX01 simpleSteps (helper puro)', () => {
  it('usa los valores de calcSteps: 5 + 2 = 7, objetivo 8, cantidad 1 (sin recalcular con redondeos)', () => {
    const c = calcSteps(realRecoDetail)!;
    const s = simpleSteps(realRecoDetail, c)!;
    expect(s.order).toBe(c.steps[7].value);
    expect(s.steps.map((x) => x.title)).toEqual(['Con qué se cuenta', 'Qué se busca cubrir', 'De dónde sale la cantidad']);
    expect(s.steps[0].lines).toEqual([
      'Disponible simulado: 5 unidades', 'Por recibir (simulado): 2 unidades', 'Suma de lo que se tiene o está por llegar: 5 + 2 = 7 unidades',
    ]);
    expect(s.steps[1].lines[0]).toContain('14 días (del 11/07/2026 al 24/07/2026): 5 unidades');
    expect(s.steps[1].lines[1]).toBe('Reserva de seguridad: 7 días de ventas = 2.5 unidades');
    expect(s.steps[1].lines[2]).toContain('8 unidades');
    expect(s.steps[2].lines[0]).toBe('Objetivo − lo que se tiene o está por llegar: 8 − 7');
    expect(s.steps[2].lines[1]).toContain('1 unidad ');
  });
  it('cantidad nunca negativa: posición mayor que el objetivo sugiere 0', () => {
    const r: Recommendation = { ...realRecoDetail, sum_28: 12, days_28: 28, mean_28_exact: '3/7', on_hand: 20, in_transit: 4, position: 24, target: 9, order_qty: 0, order_value_assumed: 0 };
    const s = simpleSteps(r)!;
    expect(s.order).toBe(0);
    expect(s.steps[2].lines[0]).toContain('9 − 24');
    expect(s.steps[2].lines[1]).toContain('0 unidades');
  });
  it('sin inventario simulado devuelve null (nunca stock cero)', () => {
    expect(simpleSteps(recoNoSnap)).toBeNull();
  });
});

describe('UX01 Reposición simulada', () => {
  async function open(list = realRecoPage, detail: Recommendation = realRecoDetail, url = '/recomendaciones') {
    const m = await mountAs(RecommendationsPage, url);
    await ok(m.f, one(m.http, '/api/v1/runs'), page([realRunSummary]));
    await ok(m.f, one(m.http, '/api/v1/recommendations'), list);
    (m.el.querySelector('[data-testid="reco-table"] tbody button') as HTMLButtonElement).click();
    await ok(m.f, one(m.http, `/api/v1/recommendations/${list.items[0].sku}`), detail);
    return m;
  }

  it('vista inicial: con sugerencia de reposición (status=ok, only_orders=true); las tres vistas con aria-pressed; un solo h1 y UN aviso de simulación', async () => {
    const m = await mountAs(RecommendationsPage);
    await ok(m.f, one(m.http, '/api/v1/runs'), page([realRunSummary]));
    const r = one(m.http, '/api/v1/recommendations');
    expect([r.request.params.get('status'), r.request.params.get('only_orders'), r.request.params.has('no_orders')]).toEqual(['ok', 'true', false]);
    await ok(m.f, r, realRecoPage);
    expect(m.el.querySelectorAll('h1').length).toBe(1);
    expect(txt(m.el, 'page-title')).toBe('Reposición simulada');
    expect(m.el.querySelectorAll('[data-testid="sim-notice"]').length).toBe(1);
    expect(txt(m.el, 'sim-notice')).toContain('Inventario simulado con supuestos; no corresponde al inventario real de la empresa');
    const pressed = Array.from(m.el.querySelectorAll('.seg button')).map((b) => `${b.textContent!.trim()}=${b.getAttribute('aria-pressed')}`);
    expect(pressed).toEqual(['Con sugerencia de reposición=true', 'Sin necesidad de reponer en el ejemplo=false', 'Sin datos de inventario=false']);
    expect(txt(m.el, 'analysis-name')).toBe('Ejemplo de julio');
  });

  it('tabla corta: producto etiquetado, disponible simulado y cantidad sugerida enteros; botón «Entender sugerencia»; por recibir y valor supuesto no están', async () => {
    const m = await mountAs(RecommendationsPage);
    await ok(m.f, one(m.http, '/api/v1/runs'), page([realRunSummary]));
    await ok(m.f, one(m.http, '/api/v1/recommendations'), realRecoPage);
    const heads = Array.from(m.el.querySelectorAll('[data-testid="reco-table"] thead th')).map((c) => c.textContent!.trim());
    expect(heads).toEqual(['Producto', 'Disponible simulado (unidades)', 'Cantidad sugerida (unidades base)', 'Acción']);
    const cells = Array.from(m.el.querySelector('[data-testid="reco-table"] tbody tr')!.querySelectorAll('td')).map((c) => c.textContent!.trim());
    expect(cells).toEqual(['Producto 26120367 · Productos de tinturacion', '0', '70', 'Entender sugerencia']);
    expect(m.el.querySelector('[data-testid="reco-table"]')!.textContent).not.toContain('PEN');
  });

  it('totales solo del servidor: «120 productos» con la etiqueta de la vista aunque la página traiga 2 filas', async () => {
    const m = await mountAs(RecommendationsPage);
    await ok(m.f, one(m.http, '/api/v1/runs'), page([realRunSummary]));
    await ok(m.f, one(m.http, '/api/v1/recommendations'), page([recoOk, { ...recoOk, sku: 'B' }], { total: 120, has_more: true }));
    expect(txt(m.el, 'reco-total')).toBe('120 productos en «Con sugerencia de reposición».');
    await click(m.f, q(m.el, 'next'));
    const r2 = one(m.http, '/api/v1/recommendations');
    expect(r2.request.params.get('page')).toBe('2');
    expect(r2.request.params.get('only_orders')).toBe('true');
    await ok(m.f, r2, page([recoOk], { page: 2, total: 120 }));
  });

  it('«Sin necesidad de reponer»: filtro del SERVIDOR (status=ok, no_orders=true, sin only_orders); la página no se filtra en el cliente', async () => {
    const m = await mountAs(RecommendationsPage);
    await ok(m.f, one(m.http, '/api/v1/runs'), page([realRunSummary]));
    await ok(m.f, one(m.http, '/api/v1/recommendations'), page([recoOk]));
    await click(m.f, q(m.el, 'view-sin_necesidad'));
    const r = one(m.http, '/api/v1/recommendations');
    expect([r.request.params.get('status'), r.request.params.get('no_orders'), r.request.params.has('only_orders'), r.request.params.get('page')]).toEqual(['ok', 'true', false, '1']);
    // el servidor devuelve una fila con cantidad 0: se muestra tal cual (0 real, no desconocido)
    await ok(m.f, r, page([{ ...recoOk, order_qty: 0 }], { total: 7 }));
    expect(q(m.el, 'view-sin_necesidad')!.getAttribute('aria-pressed')).toBe('true');
    expect(txt(m.el, 'reco-total')).toContain('7 productos en «Sin necesidad de reponer en el ejemplo»');
    expect(m.el.querySelectorAll('[data-testid="reco-table"] tbody tr').length).toBe(1);
  });

  it('«Sin datos de inventario»: status=sin_snapshot; la fila dice qué falta, no muestra 0 ni pedido y su botón abre el motivo', async () => {
    const m = await mountAs(RecommendationsPage);
    await ok(m.f, one(m.http, '/api/v1/runs'), page([realRunSummary]));
    await ok(m.f, one(m.http, '/api/v1/recommendations'), page([recoOk]));
    await click(m.f, q(m.el, 'view-sin_datos'));
    const r = one(m.http, '/api/v1/recommendations');
    expect([r.request.params.get('status'), r.request.params.has('only_orders'), r.request.params.has('no_orders')]).toEqual(['sin_snapshot', false, false]);
    await ok(m.f, r, page([recoNoSnap]));
    const ns = q(m.el, 'sin-snapshot')!;
    expect(ns.textContent).toContain('Sin datos de inventario');
    expect(ns.textContent).toContain('Qué información falta: SIN_INVENTARIO_SIMULADO_AL_10_07');
    expect(ns.textContent!.toLowerCase()).toContain('no se supone stock cero');
    expect(ns.textContent).not.toMatch(/\b0\b/);
    (ns.querySelector('button') as HTMLButtonElement).click();
    await ok(m.f, one(m.http, '/api/v1/recommendations/SKU-NEW'), recoNoSnap);
    expect(q(m.el, 'calc-steps')).toBeNull();
    expect(q(m.el, 'simple-steps')).toBeNull();
    expect(q(m.el, 'order-result')).toBeNull();
    expect(txt(m.el, 'detail-nosnap')).toContain('No se supone stock cero');
  });

  it('buscar por código y categoría conserva la vista elegida y se envía al servidor', async () => {
    const m = await mountAs(RecommendationsPage);
    await ok(m.f, one(m.http, '/api/v1/runs'), page([realRunSummary]));
    await ok(m.f, one(m.http, '/api/v1/recommendations'), page([recoOk]));
    const form = m.el.querySelector('form.filters') as HTMLFormElement;
    const set = (name: string, v: string, ev = 'input') => { const i = form.querySelector(`[name="${name}"]`) as HTMLInputElement; i.value = v; i.dispatchEvent(new Event(ev)); };
    set('sku', '1010004'); set('cat', 'CAT-T'); set('sort', '-order_qty', 'change');
    m.f.detectChanges();
    form.dispatchEvent(new Event('submit'));
    const r = one(m.http, '/api/v1/recommendations');
    const p = r.request.params;
    expect([p.get('sku'), p.get('categoria'), p.get('status'), p.get('only_orders'), p.get('sort')]).toEqual(['1010004', 'CAT-T', 'ok', 'true', '-order_qty']);
    await ok(m.f, r, page([recoOk]));
  });

  it('vista vacía: mensaje con acción (las otras vistas siguen accesibles), no un total inventado', async () => {
    const m = await mountAs(RecommendationsPage);
    await ok(m.f, one(m.http, '/api/v1/runs'), page([realRunSummary]));
    await ok(m.f, one(m.http, '/api/v1/recommendations'), page([]));
    expect(m.el.querySelector('[data-state="empty"]')?.textContent).toContain('ningún producto tiene sugerencia de reposición');
    expect(q(m.el, 'reco-total')).toBeNull();
    expect(m.el.querySelectorAll('.seg button').length).toBe(3);
  });

  it('error: se muestra y se puede reintentar', async () => {
    const m = await mountAs(RecommendationsPage);
    await ok(m.f, one(m.http, '/api/v1/runs'), page([realRunSummary]));
    one(m.http, '/api/v1/recommendations').flush({}, { status: 503, statusText: 'x' });
    await settle(m.f);
    expect(m.el.querySelector('[data-state="error"]')).toBeTruthy();
    expect(q(m.el, 'reco-table')).toBeNull();
    await click(m.f, m.el.querySelector('[data-state="error"] button') as HTMLElement);
    await ok(m.f, one(m.http, '/api/v1/recommendations'), realRecoPage);
    expect(q(m.el, 'reco-table')).toBeTruthy();
  });

  it('detalle: título del producto, resultado destacado, fecha del inventario y tres pasos con los valores reales', async () => {
    const m = await open();
    expect(txt(m.el, 'detail-title')).toBe('Producto 1010004 · Higiene capilar');
    expect(txt(m.el, 'result-headline')).toContain('En este ejemplo se sugieren 1 unidad');
    expect(txt(m.el, 'result-headline')).toContain('10/07/2026');
    expect(txt(m.el, 'order-result')).toBe('1 unidad');
    expect(q(m.el, 'reco-detail')!.getAttribute('aria-live')).toBe('polite');
    const steps = Array.from(m.el.querySelectorAll('[data-testid="simple-steps"] > li')).map((x) => x.textContent!.replace(/\s+/g, ' ').trim());
    expect(steps.length).toBe(3);
    expect(steps[0]).toContain('Con qué se cuenta');
    expect(steps[0]).toContain('5 + 2 = 7 unidades');
    expect(steps[1]).toContain('Qué se busca cubrir');
    expect(steps[1]).toContain('Reserva de seguridad: 7 días de ventas = 2.5 unidades');
    expect(steps[2]).toContain('De dónde sale la cantidad');
    expect(steps[2]).toContain('8 − 7');
    expect(q(m.el, 'incoherent')).toBeNull();
    expect(visibleText(m.el)).not.toMatch(/\d\.\d{4,}/);
    m.http.verify();
  });

  it('«Ver cálculo completo y supuestos» (plegado) conserva los 9 pasos, las verificaciones, fechas, plazo, modelo, almacén y el bloque técnico', async () => {
    const m = await open();
    const full = q(m.el, 'full-calc') as HTMLDetailsElement;
    expect(full.open).toBe(false);
    expect(full.querySelector('summary')!.textContent).toContain('Ver cálculo completo y supuestos');
    expect(full.querySelectorAll('[data-testid="calc-steps"] li').length).toBe(9);
    expect(full.textContent).toContain('posición coherente · objetivo coherente · cantidad coherente');
    const d = txt(m.el, 'reco-dates');
    for (const s of ['10/07/2026', 'plazo de entrega 7 días', 'revisión cada 7 días', 'modelo promedio_28', 'almacén 1']) expect(d).toContain(s);
    const tech = q(m.el, 'tech-details') as HTMLDetailsElement;
    expect(tech.open).toBe(false);
    expect(tech.textContent).toContain('4.999999999400001');
    expect(tech.textContent).toContain('explanation_steps');
    expect(tech.textContent).toContain('T07_L7_S7_promedio_28_2026-07-10');
    expect(tech.textContent).toContain('SYNTHETIC_NOT_REAL_INVENTORY');
    // los valores exactos no salen del bloque plegable
    expect(visibleText(m.el)).not.toContain('4.999999999400001');
    expect(Array.from(m.el.querySelectorAll('ol')).filter((o) => !o.closest('details')).map((o) => o.getAttribute('data-testid'))).toEqual(['simple-steps']);
  });

  it('valores que no cuadran con la fórmula: aviso de error visible', async () => {
    const bad: Recommendation = { ...realRecoDetail, order_qty: 5 };
    const m = await open(realRecoPage, bad);
    expect(txt(m.el, 'incoherent')).toContain('no cuadran con la fórmula');
    expect(txt(m.el, 'full-calc')).toContain('cantidad NO coherente');
  });

  it('el detalle pide el análisis elegido (run) y «Cerrar detalle» lo oculta', async () => {
    const m = await mountAs(RecommendationsPage, '/recomendaciones?run=gen-1');
    await ok(m.f, one(m.http, '/api/v1/runs'), page([runSummary, genRun]));
    const list = one(m.http, '/api/v1/recommendations');
    expect(list.request.params.get('run_id')).toBe('gen-1');
    await ok(m.f, list, { ...page([{ ...recoOk, run_id: 'gen-1' }]), run: { ...runSummary, run_id: 'gen-1' } });
    expect(txt(m.el, 'reco-header')).toContain('11/07/2026 al 24/07/2026');
    (m.el.querySelector('[data-testid="reco-table"] tbody button') as HTMLButtonElement).click();
    const d = one(m.http, '/api/v1/recommendations/SKU-T1');
    expect(d.request.params.get('run_id')).toBe('gen-1');
    await ok(m.f, d, { ...recoOk, run_id: 'gen-1' });
    expect(m.el.querySelectorAll('[data-testid="calc-steps"] li').length).toBe(9);
    await click(m.f, q(m.el, 'close-detail'));
    expect(q(m.el, 'reco-detail')).toBeNull();
    expect(q(m.el, 'change-run')!.getAttribute('href')).toContain('run=gen-1');
  });

  it('versión reemplazada (calidad publicada con las sugerencias): aviso breve, enlace al corregido y motivo plegado, en lista y detalle', async () => {
    const SUP = { status: 'superseded', validation_status: 'valid', quality_issue: { superseded_by: 'hist-20260710-NEW', reason: 'Error de redondeo en el objetivo' } };
    const m = await open({ ...realRecoPage, run: { ...realRecoPage.run!, ...SUP } }, { ...realRecoDetail, run: { ...realRecoDetail.run!, ...SUP } });
    const banners = m.el.querySelectorAll('[data-testid="superseded-banner"]');
    expect(banners.length).toBe(2);
    expect(banners[0].textContent).toContain('Esta versión fue reemplazada. No uses sus sugerencias.');
    expect(banners[0].textContent).toContain('Error de redondeo en el objetivo');
    expect((banners[0].querySelector('[data-testid="superseded-link"]') as HTMLAnchorElement).getAttribute('href')).toContain('run=hist-20260710-NEW');
    expect(visibleText(m.el)).not.toContain('Error de redondeo');
  });

  it('evaluación sin pedidos: mensaje corto, botón «Abrir el ejemplo con reposición simulada» (run explícito), código plegado, sin tabla ni filtros', async () => {
    const m = await mountAs(RecommendationsPage, '/recomendaciones?run=' + FINAL_ID);
    await ok(m.f, one(m.http, '/api/v1/runs'), page([finalRun, histRun]));
    const r = one(m.http, '/api/v1/recommendations');
    expect(r.request.params.get('run_id')).toBe(FINAL_ID);
    await ok(m.f, r, finalRecoPage());
    expect(txt(m.el, 'reco-unavailable-text')).toContain('La evaluación de agosto compara estimaciones con ventas registradas; no genera pedidos');
    const link = q(m.el, 'see-run') as HTMLAnchorElement;
    expect(link.textContent!.trim()).toBe('Abrir el ejemplo con reposición simulada');
    expect(link.getAttribute('href')).toContain('run=' + HIST_ID);
    expect(txt(m.el, 'reco-reason-code')).toBe('RECOMENDACION_NO_VALIDADA_PARA_ESTE_ORIGEN');
    expect(visibleText(m.el)).not.toContain('RECOMENDACION_NO_VALIDADA');
    expect(q(m.el, 'reco-table')).toBeNull();
    expect(q(m.el, 'reco-detail')).toBeNull();
    expect(m.el.querySelector('form.filters')).toBeNull();
    expect(m.el.querySelector('.seg')).toBeNull();
    expect(visibleText(m.el)).toContain('Inventario simulado con supuestos; no corresponde al inventario real de la empresa');
  });

  it('sin see_run no inventa un enlace', async () => {
    const m = await mountAs(RecommendationsPage, '/recomendaciones?run=' + FINAL_ID);
    await ok(m.f, one(m.http, '/api/v1/runs'), page([finalRun]));
    await ok(m.f, one(m.http, '/api/v1/recommendations'), finalRecoPage(null));
    expect(q(m.el, 'see-run')).toBeNull();
    expect(q(m.el, 'no-see-run')).toBeTruthy();
  });
});
