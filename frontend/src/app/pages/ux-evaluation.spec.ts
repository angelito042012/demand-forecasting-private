// Pruebas UX01 de «Evaluación de resultados» (/comparacion) y «Ventas registradas» (/resumen).
// Los datos son las formas del contrato (testing/real-shapes.ts y final-shapes.ts); las pruebas de evaluación final usan cifras
// inventadas de FORMA, no resultados de T12. Se conserva la semántica científica: error alto sin insignia, null = «no evaluable» ≠ 0,
// sin ganador declarado, MAPE con cobertura, R² indefinido y la evaluación de agosto sin pedidos ni recomendaciones.
import { Type } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting, TestRequest } from '@angular/common/http/testing';
import { Router, provideRouter } from '@angular/router';
import { apiInterceptor } from '../core/interceptors';
import { demoInterceptor } from '../core/interceptors';
import { ComparisonPage } from './comparison.page';
import { SummaryPage } from './summary.page';
import { fmtInt, fmtPct, fmtPen } from '../core/utils/format';
import { page } from '../testing/fixtures';
import { realBacktest, realBacktestList, realRunSummary } from '../testing/real-shapes';
import { FINAL_ID, finalBacktest, finalBacktestList, finalRun, genRun, histRun } from '../testing/final-shapes';
import { visibleText } from '../testing/mount';
import { BacktestDetail, FINAL_WARNINGS, RunSummary } from '../core/models';
import { predRows } from '../core/backtest';

interface M<T> { f: ComponentFixture<T>; http: HttpTestingController; el: HTMLElement }
let lastHttp: HttpTestingController | undefined;

async function mountAt<T>(cmp: Type<T>, url: string): Promise<M<T>> {
  TestBed.configureTestingModule({
    imports: [cmp],
    providers: [provideHttpClient(withInterceptors([apiInterceptor, demoInterceptor])), provideHttpClientTesting(), provideRouter([{ path: '**', children: [] }])],
  });
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
async function choose(f: ComponentFixture<unknown>, el: HTMLElement, id: string, v: string) {
  const s = q(el, id) as HTMLSelectElement; s.value = v; s.dispatchEvent(new Event('change')); await settle(f);
}
afterEach(() => { lastHttp?.verify(); lastHttp = undefined; });

/** Evaluación del ejemplo histórico (sin parámetro run). */
async function openHist(detail: BacktestDetail = realBacktest, runs: RunSummary[] = [realRunSummary]) {
  const m = await mountAt(ComparisonPage, '/comparacion');
  await ok(m.f, one(m.http, '/api/v1/runs'), page(runs));
  await ok(m.f, one(m.http, '/api/v1/backtests'), realBacktestList);
  await new Promise((r) => setTimeout(r, 0));
  await ok(m.f, one(m.http, `/api/v1/backtests/${realBacktest.backtest_id}`), detail);
  return m;
}
/** Evaluación de agosto (run = final). */
async function openFinal(detail: BacktestDetail = finalBacktest) {
  const m = await mountAt(ComparisonPage, '/comparacion?run=' + FINAL_ID);
  await ok(m.f, one(m.http, '/api/v1/runs'), page([finalRun, histRun]));
  await ok(m.f, one(m.http, '/api/v1/backtests'), finalBacktestList);
  await new Promise((r) => setTimeout(r, 0));
  await ok(m.f, one(m.http, `/api/v1/backtests/${finalBacktest.backtest_id}`), detail);
  return m;
}
const clone = <T>(x: T): T => JSON.parse(JSON.stringify(x));
const aggRow = (d: BacktestDetail, level: 'sku' | 'categoria', coh: string, metodo: string) =>
  predRows(d, level, coh, 'acum14', 'AGREGADO').find((r) => r.metodo === metodo)!;

describe('UX01 Evaluación: encabezado, secciones y conclusión', () => {
  it('un solo h1, la pregunta de propósito, la barra de análisis y las dos secciones en orden', async () => {
    const m = await openHist();
    expect(m.el.querySelectorAll('h1').length).toBe(1);
    expect(txt(m.el, 'page-title')).toBe('Evaluación de resultados');
    expect(txt(m.el, 'page-lead')).toBe('¿Qué tan cerca estuvieron las estimaciones de las ventas registradas?');
    expect(txt(m.el, 'analysis-name')).toBe('Ejemplo de julio');
    const h2 = Array.from(m.el.querySelectorAll('h2')).map((h) => h.textContent!.trim());
    expect(h2).toEqual(['Estimaciones frente a ventas registradas', 'Comparación de reposición simulada']);
    expect(q(m.el, 'jump-est')).toBeTruthy();
    expect(q(m.el, 'jump-rep')).toBeTruthy();
  });

  it('el ejemplo histórico dice que no incluye agosto y nunca «agosto sigue reservado»', async () => {
    const m = await openHist();
    const t = visibleText(m.el);
    expect(t).toContain('Este ejemplo no incluye agosto');
    expect(t).not.toContain('agosto sigue reservado');
    expect(t).not.toContain('MODO DEMOSTRACIÓN');
  });

  it('la conclusión se calcula de los datos elegidos: valores, lectura llana, comparación y «no ganó»', async () => {
    const m = await openHist();
    const b = aggRow(realBacktest, 'sku', 'primaria', 'promedio_28');
    const e = aggRow(realBacktest, 'sku', 'primaria', 'rf_distribuido');
    const c = txt(m.el, 'est-conclusion');
    // vista inicial: una explicación corta con el error como % del volumen vendido, no como acierto
    const ex = txt(m.el, 'eval-explain');
    expect(ex).toContain(`el error absoluto del promedio de 28 días equivale a cerca del ${fmtPct(b.WAPE)} del volumen vendido; no significa ${fmtPct(b.WAPE)} de acierto`);
    expect(ex).toContain('Es un error alto por producto');
    expect(txt(m.el, 'eval-scope-simple')).toContain(`productos con historia suficiente · acumulado de 14 días · ${fmtInt(b.n)} productos`);
    expect(c).toContain(`Error del modelo experimental: ${fmtPct(e.WAPE)}`);
    expect(c).toContain('por producto');
    expect(c).toContain('Cohorte primaria');
    expect(c).toContain('Acumulado 14 días');
    // error mayor del experimental: se dice «mayor», sin insignia de calidad
    expect(e.WAPE).toBeGreaterThan(b.WAPE as number);
    expect(c).toContain('error mayor que el promedio de 28 días');
    expect(c).toContain('El modelo experimental no ganó');
    expect(c).toContain('No se declaró ganador experimental');
    expect(c).toContain('el método operativo no cambia');
    // cifras clave: sesgo y cobertura legibles
    const key = txt(m.el, 'key-promedio_28');
    expect(key).toContain(fmtPct(b.WAPE));
    expect(key).toContain(fmtInt(b.n));
    expect(key).toMatch(/[\d,]+ de [\d,]+ \([\d.]+ %\)/);
    expect(q(m.el, 'key-promedio_28')!.querySelector('[data-testid="key-bias"]')!.textContent).toMatch(/^[+-]?[\d.,]+ %$/);
    expect(q(m.el, 'key-rf_distribuido')).toBeTruthy();
  });

  it('no impone «RF siempre peor»: si el modelo experimental tiene menor error, la conclusión lo dice así', async () => {
    const copy = clone(realBacktest);
    const r = aggRow(copy, 'sku', 'primaria', 'rf_distribuido');
    r.WAPE = 0.5;     // dato de prueba: menor que el del promedio
    const m = await openHist(copy);
    const c = txt(m.el, 'est-conclusion');
    expect(c).toContain('error menor que el promedio de 28 días');
    expect(c).not.toContain('error mayor');
    expect(c).toContain('No se declaró ganador experimental');       // el método operativo no cambia
    expect(txt(m.el, 'key-rf_distribuido')).toContain(fmtPct(0.5));
  });

  it('cambiar de nivel cambia el alcance y las cifras de la conclusión (no es una frase fija)', async () => {
    const m = await openHist();
    await choose(m.f, m.el, 'pred-level', 'categoria');
    const b = aggRow(realBacktest, 'categoria', 'primaria', 'promedio_28');
    const c = txt(m.el, 'est-conclusion');
    expect(c).toContain('por categoría');
    expect(txt(m.el, 'eval-explain')).toContain(`cerca del ${fmtPct(b.WAPE)} del volumen vendido`);
    expect(b.WAPE).toBeLessThan(0.5);
    expect(txt(m.el, 'eval-explain')).not.toContain('error alto');      // la etiqueta «alto» depende del valor publicado (20 % < 50 %)
    expect(txt(m.el, 'eval-scope-simple')).toContain('categorías de productos con historia suficiente');
    expect(txt(m.el, 'key-promedio_28')).toContain(fmtPct(b.WAPE));
    expect(q(m.el, 'key-rf_categoria')).toBeTruthy();
    await choose(m.f, m.el, 'pred-vista', 'acum10');
    expect(txt(m.el, 'est-conclusion')).toContain('Acumulado 10 días');
    expect(txt(m.el, 'eval-scope-simple')).toContain('acumulado de 10 días');
  });

  it('WAPE indefinido (null) = «no evaluable» en la conclusión y en las cifras; nunca 0 ni una insignia favorable', async () => {
    const copy = clone(realBacktest);
    aggRow(copy, 'sku', 'primaria', 'promedio_28').WAPE = null;
    aggRow(copy, 'sku', 'primaria', 'rf_distribuido').WAPE = null;
    const m = await openHist(copy);
    const c = txt(m.el, 'est-conclusion');
    expect(c).toContain('Error del promedio de 28 días (método elegido): no evaluable');
    expect(txt(m.el, 'eval-explain')).toContain('no es evaluable');
    expect(txt(m.el, 'eval-explain')).not.toContain('de acierto');
    expect(c).toContain('No se puede comparar');
    expect(c).not.toMatch(/\b0[.,]0 %/);
    expect(q(m.el, 'key-promedio_28')!.querySelector('[data-testid="key-error"]')!.textContent!.trim()).toBe('no evaluable');
    expect(q(m.el, 'key-rf_distribuido')!.querySelector('[data-testid="key-error"]')!.textContent!.trim()).toBe('no evaluable');
    expect(m.el.querySelector('.badge.ok[data-testid^="key"]')).toBeNull();
  });

  it('sin datos evaluables (n = 0) se rotula así, sin cifras inventadas', async () => {
    const m = await openHist();
    await choose(m.f, m.el, 'pred-level', 'categoria');
    await choose(m.f, m.el, 'pred-coh', 'historia_corta');
    expect(txt(m.el, 'key-promedio_28')).toContain('sin datos evaluables');
    expect(txt(m.el, 'est-conclusion')).toContain('no evaluable');
  });

  it('el detalle académico completo está plegado y fácil de encontrar, con MAPE+cobertura, R² indefinido y los resultados desfavorables', async () => {
    const copy = clone(realBacktest);
    const z = aggRow(copy, 'sku', 'primaria', 'cero');
    z.R2 = null; z.R2_nota = 'varianza observada nula';
    const m = await openHist(copy);
    // UNA sección académica rotulada, plegada; el detalle de reposición conserva su propio pliegue
    const acad = q(m.el, 'academic-detail') as HTMLDetailsElement;
    expect(acad.open).toBe(false);
    expect(acad.querySelector('summary')!.textContent).toContain('Ver cómo se evaluó: detalle académico');
    const helps = Array.from(m.el.querySelectorAll('details.help')) as HTMLDetailsElement[];
    expect(helps.length).toBe(1);
    for (const h of helps) { expect(h.open).toBe(false); expect(h.querySelector('summary')!.textContent).toContain('Ver detalle completo'); }
    const pred = q(acad as HTMLElement, 'detail-pred')!;
    expect(pred).toBeTruthy();
    const methods = Array.from(pred.querySelectorAll('[data-testid="pred-table"] tbody tr')).map((r) => r.getAttribute('data-testid'));
    expect(methods).toEqual(['pred-row-promedio_28', 'pred-row-rf_distribuido', 'pred-row-referencia_fija_0531', 'pred-row-cero']);
    expect(pred.querySelector('[data-testid="pred-row-promedio_28"] [data-testid="mape"]')!.textContent).toMatch(/cobertura [\d.]+ % de los casos/);
    expect(pred.querySelector('[data-testid="pred-row-cero"] [data-testid="r2"]')!.textContent).toContain('no evaluable');
    expect(pred.querySelector('[data-testid="pred-row-cero"] [data-testid="r2"]')!.textContent).toContain('varianza observada nula');
    expect(pred.textContent).toContain('no ganó');
    // los datos técnicos (identificadores, JSON) siguen fuera del contenido visible
    expect(visibleText(m.el)).not.toContain(realBacktest.backtest_id!);
  });
});

describe('UX01 Evaluación: reposición simulada', () => {
  it('muestra el aviso exacto de simulación, la conclusión calculada y no atribuye impacto real', async () => {
    const m = await openHist();
    const t = visibleText(m.el);
    expect(t).toContain('Inventario simulado con supuestos; no corresponde al inventario real de la empresa');
    const block = (policy: string) => realBacktest.simulation!.find((s) => s.L === 7 && s.S === 7 && s.policy === policy)!.total;
    const c = txt(m.el, 'sim-conclusion');
    expect(c).toContain(fmtPct(block('promedio_28')['fill_rate']));
    expect(c).toContain(fmtPct(block('rf_categoria_distribuido')['fill_rate']));
    expect(c).toContain('Es una simulación con inventario, costos y plazos supuestos; no se atribuye un impacto real');
    expect(c).toMatch(/Más servicio (vino acompañado de más stock o más compras|puede ir con más stock y más compras)/);
    expect(t).toContain('27 combinaciones');
    expect(t).not.toMatch(/ahorro de \d|mejora real de/);
  });

  it('un escenario sin simulación publicada dice «datos insuficientes» y no inventa conclusión', async () => {
    const m = await openHist();
    await choose(m.f, m.el, 'sel-L', '14');
    expect(txt(m.el, 'sim-empty')).toContain('Datos insuficientes');
    expect(q(m.el, 'sim-conclusion')).toBeNull();
    expect(m.el.querySelector('[data-testid="sim-table"]')).toBeNull();
  });

  it('cambiar el escenario cambia la conclusión de la simulación', async () => {
    const m = await openHist();
    const before = txt(m.el, 'sim-conclusion');
    await choose(m.f, m.el, 'sel-L', '3');
    await choose(m.f, m.el, 'sel-S', '0');
    const after = txt(m.el, 'sim-conclusion');
    expect(after).not.toBe(before);
    expect(after).toContain('plazo de entrega L3 días, seguridad S0 días');
  });
});

describe('UX01 Evaluación de agosto (final)', () => {
  it('conclusión del hallazgo primario con lectura llana, sin ganador y sin «agosto sigue reservado»', async () => {
    const m = await openFinal();
    const c = txt(m.el, 'est-conclusion');
    expect(c).toContain(`Error del promedio de 28 días (método operativo): ${fmtPct(0.5)}`);
    expect(c).toContain(`Error del modelo experimental: ${fmtPct(0.6)}`);
    expect(txt(m.el, 'eval-explain')).toContain(`equivale a cerca del ${fmtPct(0.5)} del volumen vendido; no significa ${fmtPct(0.5)} de acierto`);
    expect(txt(m.el, 'eval-brief-notice')).toContain('no se declara un método ganador');
    expect(txt(m.el, 'eval-brief-notice')).toContain('el método operativo no cambia');
    expect(c).toContain('error mayor que el promedio de 28 días');
    expect(c).toContain('por producto y almacén');
    expect(c).toContain(`n = ${fmtInt(1000)}`);
    const t = visibleText(m.el);
    expect(t).not.toContain('agosto sigue reservado');
    expect(t).toContain('Ya hay un resultado final disponible');
    expect(txt(m.el, 'analysis-name')).toBe('Evaluación de agosto');
    expect(txt(m.el, 'primary-winner')).toContain('RF declarado ganador: no');
  });

  it('las cuatro advertencias obligatorias siguen visibles; sin pedidos ni recomendaciones', async () => {
    const m = await openFinal();
    const w = visibleText(q(m.el, 'final-warnings')!);
    for (const t of FINAL_WARNINGS) expect(w).toContain(t);
    expect(q(m.el, 'reco-table')).toBeNull();
    expect(visibleText(m.el)).toContain('no se generan pedidos ni recomendaciones');
    expect(m.el.querySelector('a[href*="recomendaciones"]')).toBeNull();
  });

  it('error indefinido del modelo experimental = «no evaluable» (no 0) en la conclusión y la tabla primaria', async () => {
    const copy = clone(finalBacktest);
    copy.selection!.primary!.WAPE_rf_distribuido = null;
    for (const r of copy.predictive!.sku!) if (r.metodo === 'rf_distribuido' && r.cohorte === 'primaria' && r.vista === 'acum14') r.WAPE = null;
    const m = await openFinal(copy);
    expect(txt(m.el, 'est-conclusion')).toContain('Error del modelo experimental: no evaluable');
    expect(txt(m.el, 'eval-explain')).toContain(`cerca del ${fmtPct(0.5)}`);
    expect(txt(m.el, 'est-conclusion')).toContain('No se puede comparar');
    expect(txt(m.el, 'primary-rf')).toContain('no evaluable');
  });

  it('la reposición simulada de agosto: aviso, conclusión sin impacto real y detalle (27 combinaciones) plegado', async () => {
    const m = await openFinal();
    const vis = visibleText(m.el);
    expect(vis).toContain('Inventario simulado con supuestos; no corresponde al inventario real de la empresa');
    expect(txt(m.el, 'sim-conclusion')).toContain('no se atribuye un impacto real');
    expect(txt(m.el, 'sim-conclusion')).toContain('plazo de entrega L7 días, seguridad S7 días');
    const det = q(m.el, 'final-sim-detail') as HTMLDetailsElement;
    expect(det.open).toBe(false);
    expect(det.querySelectorAll('[data-testid="final-sim-27"] tbody tr').length).toBe(9);
    expect(txt(m.el, 'combos-count')).toContain('27 combinaciones publicadas de 27');
    expect(det.textContent).toContain('no se presenta como mejora');
  });

  it('el detalle completo del análisis predictivo (cobertura, SKU nuevos, H10/H14/H21/diaria) sigue disponible, plegado', async () => {
    const m = await openFinal();
    const det = q(m.el, 'academic-detail') as HTMLDetailsElement;
    expect(det.open).toBe(false);
    expect(det.contains(q(m.el, 'final-detail-est'))).toBe(true);
    for (const v of ['acum10', 'acum14', 'acum21', 'diaria']) expect(det.querySelector(`[data-testid="final-table-${v}"]`)).toBeTruthy();
    expect(det.querySelector('[data-testid="final-coverage"]')!.textContent).toContain('skus_nuevos_con_venta_en_bloque: 7');
    expect(det.querySelector('[data-testid="final-legend"]')!.textContent).toContain('WAPE no es exactitud');
  });
});

describe('UX01 Evaluación: sin evaluación, errores y análisis reemplazado', () => {
  it('un análisis creado en la aplicación sin comparación: mensaje claro con enlace a «Mis análisis»', async () => {
    const m = await mountAt(ComparisonPage, '/comparacion?run=gen-test-1');
    await ok(m.f, one(m.http, '/api/v1/runs'), page([histRun, genRun]));
    const bt = one(m.http, '/api/v1/backtests');
    expect(bt.request.params.get('run_id')).toBe('gen-test-1');
    await ok(m.f, bt, page([]));
    await ok(m.f, m.http.expectOne((r) => r.url === '/api/v1/backtests' && !r.params.has('run_id')), realBacktestList);
    expect(txt(m.el, 'no-backtest')).toContain('Este análisis se creó en la aplicación y todavía no tiene una comparación con ventas registradas');
    const link = q(m.el, 'to-analyses') as HTMLAnchorElement;
    expect(link.getAttribute('href')).toContain('/corridas');
    expect((q(m.el, 'hist-link') as HTMLAnchorElement).getAttribute('href')).toContain('run=' + realRunSummary.run_id);
    expect(q(m.el, 'sim-table')).toBeNull();
    expect(q(m.el, 'est-conclusion')).toBeNull();
    expect(m.el.querySelectorAll('h1').length).toBe(1);
  });

  it('sin ninguna comparación publicada: estado vacío con acción hacia «Mis análisis»', async () => {
    const m = await mountAt(ComparisonPage, '/comparacion');
    await ok(m.f, one(m.http, '/api/v1/runs'), page([histRun]));
    await ok(m.f, one(m.http, '/api/v1/backtests'), page([]));
    expect(m.el.querySelector('[data-state="empty"]')).toBeTruthy();
    expect(txt(m.el, 'no-backtest')).toContain('Todavía no hay una comparación con ventas registradas publicada');
    expect(q(m.el, 'to-analyses')).toBeTruthy();
  });

  it('error de la API: mensaje con «Reintentar», sin resultados de relleno', async () => {
    const m = await mountAt(ComparisonPage, '/comparacion');
    await ok(m.f, one(m.http, '/api/v1/runs'), page([histRun]));
    one(m.http, '/api/v1/backtests').flush({ error: { code: 'SERVICIO_NO_DISPONIBLE', message: 'caído' } }, { status: 503, statusText: 'x' });
    await settle(m.f);
    expect(m.el.querySelector('[data-state="error"] button')?.textContent).toContain('Reintentar');
    expect(q(m.el, 'est-conclusion')).toBeNull();
    expect(q(m.el, 'sim-conclusion')).toBeNull();
  });

  it('un análisis reemplazado se avisa con claridad en la barra', async () => {
    const replaced: RunSummary = { ...realRunSummary, status: 'superseded', validation_status: 'superseded', quality_issue: { superseded_by: 'hist-corregido' } };
    const m = await openHist(realBacktest, [replaced]);
    expect(txt(m.el, 'analysis-replaced')).toContain('Esta versión fue reemplazada. No uses sus sugerencias');
    expect((q(m.el, 'analysis-corrected') as HTMLAnchorElement).getAttribute('href')).toContain('run=hist-corregido');
  });
});

describe('UX01 Ventas registradas (/resumen)', () => {
  const summary = {
    provenance: 'OBSERVED_EXCEL', unit: 'unidad base', currency: 'PEN', from: '2026-06-01', to: '2026-07-31',
    items: [{ key: '2026-06', lineas_venta: 1200, unidades: 3400, importe_pen: 5600.5 }, { key: '2026-07', lineas_venta: 1, unidades: 2, importe_pen: 3 }],
    notas_credito: { lineas: 4, importe_pen: 5 },
    excluded_days: [{ fecha: '2026-06-07', motivo: 'excluido del entrenamiento y métricas; no se informa como venta cero' }],
  };
  async function openSummary(body: object = summary) {
    const m = await mountAt(SummaryPage, '/resumen');
    await ok(m.f, one(m.http, '/api/v1/sales/summary'), body);
    return m;
  }

  it('título, propósito, aviso de observadas y sin ser la bienvenida', async () => {
    const m = await openSummary();
    expect(m.el.querySelectorAll('h1').length).toBe(1);
    expect(txt(m.el, 'page-title')).toBe('Ventas registradas');
    expect(txt(m.el, 'page-lead')).toBe('Ventas reales ya cargadas, en unidades y soles; sirven de base para las estimaciones.');
    expect(m.el.textContent).toContain('OBSERVED_EXCEL');
    expect((m.el.querySelector('input[name="to"]') as HTMLInputElement).getAttribute('max')).toBe('2026-09-30');
    expect((m.el.querySelector('input[name="from"]') as HTMLInputElement).getAttribute('max')).toBe('2026-09-30');
    expect(m.el.querySelectorAll('.btn').length).toBe(1);          // una sola acción primaria
  });

  it('tabla con fechas en español e importes en PEN, solo con lo que devuelve la API (sin totales propios)', async () => {
    const m = await openSummary();
    const rows = Array.from(m.el.querySelectorAll('[data-testid="sales-table"] tbody tr')).map((r) => r.textContent!.replace(/\s+/g, ' ').trim());
    expect(rows.length).toBe(2);
    expect(rows[0]).toContain('Junio de 2026');
    expect(rows[0]).toContain(fmtInt(1200));
    expect(rows[0]).toContain(fmtInt(3400));
    expect(rows[0]).toContain(fmtPen(5600.5));
    expect(m.el.querySelector('[data-testid="sales-table"] tfoot')).toBeNull();
    expect(txt(m.el, 'sales-scope')).toContain('01/06/2026 al 31/07/2026');
    expect(m.el.querySelector('.table-wrap')).toBeTruthy();
  });

  it('notas de crédito aparte (sin inferir devolución física) y días excluidos con su motivo, en español', async () => {
    const m = await openSummary();
    expect(txt(m.el, 'credit-notes')).toContain('4 línea(s)');
    expect(txt(m.el, 'credit-notes')).toContain(fmtPen(5));
    expect(txt(m.el, 'credit-notes')).toContain('No se infiere devolución física');
    expect(m.el.textContent).toContain('no netas');
    expect(txt(m.el, 'excluded')).toContain('7 de junio de 2026');
    expect(txt(m.el, 'excluded')).toContain('no se informa como venta cero');
  });

  it('agrupa por día y por categoría con claves legibles; el filtro de categoría viaja al servidor', async () => {
    const m = await mountAt(SummaryPage, '/resumen');
    await ok(m.f, one(m.http, '/api/v1/sales/summary'), summary);
    (m.el.querySelector('select[name="group"]') as HTMLSelectElement).value = 'category';
    (m.el.querySelector('select[name="group"]') as HTMLSelectElement).dispatchEvent(new Event('change'));
    const cat = m.el.querySelector('input[name="cat"]') as HTMLInputElement;
    cat.value = 'HIGIENE'; cat.dispatchEvent(new Event('input'));
    await settle(m.f);
    (m.el.querySelector('form') as HTMLFormElement).dispatchEvent(new Event('submit'));
    const r = one(m.http, '/api/v1/sales/summary');
    expect(r.request.params.get('group_by')).toBe('category');
    expect(r.request.params.get('categoria')).toBe('HIGIENE');
    await ok(m.f, r, { ...summary, items: [{ key: 'HIGIENE CAPILAR', lineas_venta: 1, unidades: 2, importe_pen: 3 }] });
    expect(m.el.querySelector('[data-testid="sales-table"] thead th')!.textContent).toContain('Categoría');
    expect(m.el.querySelector('[data-testid="sales-table"] tbody th')!.textContent).toBe('Higiene capilar');
  });

  it('sin ventas en el rango: estado vacío con indicación de qué hacer', async () => {
    const m = await openSummary({ ...summary, items: [], notas_credito: { lineas: 0, importe_pen: 0 }, excluded_days: [] });
    expect(m.el.querySelector('[data-state="empty"]')!.textContent).toContain('No hay ventas registradas en el rango consultado');
    expect(m.el.querySelector('[data-state="empty"]')!.textContent).toContain('Prueba con otras fechas');
  });

  it('error del servidor (p. ej. rango fuera de alcance): mensaje y reintento, sin tabla', async () => {
    const e = await mountAt(SummaryPage, '/resumen');
    one(e.http, '/api/v1/sales/summary').flush({ error: { code: 'FUERA_DE_RANGO', message: 'La fecha solicitada excede el último día de datos permitido.' } }, { status: 422, statusText: 'x' });
    await settle(e.f);
    expect(e.el.querySelector('[data-state="error"] button')?.textContent).toContain('Reintentar');
    expect(e.el.querySelector('[data-testid="sales-table"]')).toBeNull();
  });
});

// ---- UX01R: vista inicial comprensible, detalle académico único, pestañas y precisiones de lenguaje ----
const click = async (m: M<unknown>, id: string) => { (q(m.el, id) as HTMLElement).click(); await settle(m.f); };
const keydown = async (m: M<unknown>, id: string, key: string) => {
  (q(m.el, id) as HTMLElement).dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true })); await settle(m.f);
};

describe('UX01R Evaluación: vista inicial', () => {
  it('ejemplo histórico: pregunta, una explicación, n, UN aviso breve y «Ver cómo se evaluó»; el detalle académico queda cerrado', async () => {
    const m = await openHist();
    const b = aggRow(realBacktest, 'sku', 'primaria', 'promedio_28');
    expect(txt(m.el, 'page-lead')).toBe('¿Qué tan cerca estuvieron las estimaciones de las ventas registradas?');
    const sum = q(m.el, 'eval-summary')!;
    expect(sum.querySelectorAll('.notice').length).toBe(1);                         // no cuatro cajas
    expect(txt(m.el, 'eval-explain')).toContain(`cerca del ${fmtPct(b.WAPE)} del volumen vendido; no significa ${fmtPct(b.WAPE)} de acierto`);
    expect(txt(m.el, 'eval-scope-simple')).toContain(`${fmtInt(b.n)} productos`);
    expect(txt(m.el, 'eval-brief-notice')).toContain('se solapan');
    expect(txt(m.el, 'eval-open-detail')).toBe('Ver cómo se evaluó');
    expect((q(m.el, 'academic-detail') as HTMLDetailsElement).open).toBe(false);
    // el hallazgo detallado no se repite en la vista inicial: la tabla clave y las reglas viven dentro del detalle
    expect(sum.textContent).not.toContain('Sesgo');
    expect(q(m.el, 'academic-detail')!.contains(q(m.el, 'key-table'))).toBe(true);
  });

  it('«Ver cómo se evaluó» abre el detalle académico y vuelve a la pestaña de estimaciones', async () => {
    const m = await openHist();
    await click(m, 'jump-rep');
    expect((q(m.el, 'panel-rep') as HTMLElement).hidden).toBe(false);
    await click(m, 'jump-est');
    await click(m, 'eval-open-detail');
    const acad = q(m.el, 'academic-detail') as HTMLDetailsElement;
    expect(acad.open).toBe(true);
    expect((q(m.el, 'panel-est') as HTMLElement).hidden).toBe(false);
    expect(acad.textContent).toContain('Cómo leer estos resultados');
  });

  it('evaluación de agosto: n, explicación con alcance en palabras simples y un aviso; sin las cuatro advertencias a la vista', async () => {
    const m = await openFinal();
    const sum = q(m.el, 'eval-summary')!;
    expect(txt(m.el, 'eval-scope-simple')).toBe(`productos con historia suficiente · acumulado de 14 días · ${fmtInt(1000)} productos`);
    expect(txt(m.el, 'eval-explain')).toContain('Para los productos con historia suficiente, acumulando 14 días, el error absoluto del promedio de 28 días');
    expect(txt(m.el, 'eval-explain')).toContain('Es un error alto por producto');         // 50 % publicado: no se oculta que es alto
    expect(sum.querySelectorAll('.notice').length).toBe(1);
    expect(sum.textContent).not.toContain('suma de unidades base heterogéneas');
    expect(sum.textContent).not.toContain('no pronostica octubre');
    const acad = q(m.el, 'academic-detail') as HTMLDetailsElement;
    expect(acad.open).toBe(false);
    expect(acad.contains(q(m.el, 'final-warnings'))).toBe(true);
    expect(acad.contains(q(m.el, 'primary-table'))).toBe(true);
  });

  it('abierto, el detalle conserva hallazgo primario, advertencias completas, mejora negativa, sesgos, control cero y las 27 combinaciones', async () => {
    const m = await openFinal();
    await click(m, 'eval-open-detail');
    const acad = q(m.el, 'academic-detail') as HTMLDetailsElement;
    expect(acad.open).toBe(true);
    const w = txt(m.el, 'final-warnings');
    for (const t of FINAL_WARNINGS) expect(w).toContain(t);
    expect(txt(m.el, 'primary-promedio')).toContain(fmtPct(0.5));
    expect(txt(m.el, 'primary-cero')).toContain(fmtPct(1));
    expect(txt(m.el, 'primary-mejora')).toContain(fmtPct(-0.2, true));        // desfavorable: se conserva el signo
    expect(txt(m.el, 'primary-sesgo')).toContain(fmtPct(0.04, true));
    expect(txt(m.el, 'primary-winner')).toContain('RF declarado ganador: no');
    expect(acad.textContent).toContain('ventana de 28 días de calendario');
    expect(acad.textContent).toContain('incluidos los de venta cero');
    expect(acad.textContent).not.toContain('últimos 28 días con ventas registradas');
    await click(m, 'jump-rep');
    expect(m.el.querySelectorAll('[data-testid="final-sim-27"] tbody tr').length).toBe(9);
  });

  it('métrica H14 y bloque de 21 días con etiquetas distintas y fechas derivadas de los datos publicados', async () => {
    const m = await openFinal();
    expect(txt(m.el, 'period-metric')).toBe('Métrica del 01 al 14 de agosto');
    expect(txt(m.el, 'period-block')).toBe('Bloque de prueba disponible del 01 al 21 de agosto');
    const sc = txt(m.el, 'est-conclusion');
    expect(sc).toContain('Métrica del 01 al 14 de agosto');
    expect(sc).toContain('Bloque de prueba disponible del 01 al 21 de agosto');
    expect(sc).not.toMatch(/ventas registradas del 01\/08\/2026 al 21\/08\/2026/);   // el WAPE H14 no se adjudica al bloque completo
  });

  it('otras fechas publicadas: las etiquetas las siguen (no están escritas fijas)', async () => {
    const other = clone(finalBacktest);
    other.run!.target_start = '2026-09-03'; other.run!.target_end = '2026-09-23';
    const m = await openFinal(other);
    expect(txt(m.el, 'period-metric')).toBe('Métrica del 03 al 16 de septiembre');
    expect(txt(m.el, 'period-block')).toBe('Bloque de prueba disponible del 03 al 23 de septiembre');
  });

  it('sin fechas publicadas: «primeros 14 días del bloque» y fechas no publicadas; no se inventan', async () => {
    const copy = clone(finalBacktest);
    copy.run!.target_start = null; copy.run!.target_end = null; copy.run!.evaluation_period = null;
    const m = await openFinal(copy);
    expect(txt(m.el, 'period-metric')).toContain('Métrica de los primeros 14 días del bloque');
    expect(txt(m.el, 'period-block')).toContain('fechas no publicadas');
    expect(txt(m.el, 'period-metric') + txt(m.el, 'period-block')).not.toContain('agosto');
  });

  it('WAPE indefinido en la final: la explicación dice «no es evaluable» y no habla de acierto ni de 0', async () => {
    const copy = clone(finalBacktest);
    copy.selection!.primary!.WAPE_promedio_28 = null;
    for (const r of copy.predictive!.sku!) if (r.metodo === 'promedio_28' && r.cohorte === 'primaria' && r.vista === 'acum14') r.WAPE = null;
    const m = await openFinal(copy);
    expect(txt(m.el, 'eval-explain')).toContain('no es evaluable');
    expect(txt(m.el, 'eval-explain')).not.toContain('de acierto');
    expect(txt(m.el, 'primary-promedio')).toContain('no evaluable');
    expect(txt(m.el, 'est-conclusion')).toContain('Error del promedio de 28 días (método operativo): no evaluable');
  });
});

describe('UX01R Evaluación: pestañas y advertencias por sección', () => {
  it('roles tablist/tab/tabpanel enlazados; solo el panel activo es visible', async () => {
    const m = await openFinal();
    expect(m.el.querySelectorAll('[role="tablist"]').length).toBe(1);
    const tabs = Array.from(m.el.querySelectorAll('[role="tab"]')) as HTMLElement[];
    expect(tabs.map((t) => t.textContent!.trim())).toEqual(['Estimaciones frente a ventas registradas', 'Comparación de reposición simulada']);
    expect(tabs.map((t) => t.getAttribute('aria-selected'))).toEqual(['true', 'false']);
    expect(tabs.map((t) => t.getAttribute('tabindex'))).toEqual(['0', '-1']);
    for (const t of tabs) {
      const panel = m.el.querySelector('#' + t.getAttribute('aria-controls')!) as HTMLElement;
      expect(panel.getAttribute('role')).toBe('tabpanel');
      expect(panel.getAttribute('aria-labelledby')).toBe(t.id);
    }
    expect((q(m.el, 'panel-est') as HTMLElement).hidden).toBe(false);
    expect((q(m.el, 'panel-rep') as HTMLElement).hidden).toBe(true);
  });

  it('teclado: flechas, Fin e Inicio cambian de pestaña y el foco sigue a la seleccionada', async () => {
    const m = await openFinal();
    document.body.appendChild(m.el);
    try {
      await keydown(m, 'jump-est', 'ArrowRight');
      expect(q(m.el, 'jump-rep')!.getAttribute('aria-selected')).toBe('true');
      expect((q(m.el, 'panel-rep') as HTMLElement).hidden).toBe(false);
      expect((q(m.el, 'panel-est') as HTMLElement).hidden).toBe(true);
      await new Promise((r) => setTimeout(r, 0));
      expect(document.activeElement).toBe(q(m.el, 'jump-rep'));
      await keydown(m, 'jump-rep', 'ArrowRight');                     // da la vuelta
      expect(q(m.el, 'jump-est')!.getAttribute('aria-selected')).toBe('true');
      await keydown(m, 'jump-est', 'End');
      expect(q(m.el, 'jump-rep')!.getAttribute('aria-selected')).toBe('true');
      await keydown(m, 'jump-rep', 'Home');
      expect(q(m.el, 'jump-est')!.getAttribute('aria-selected')).toBe('true');
      await keydown(m, 'jump-est', 'ArrowLeft');
      expect(q(m.el, 'jump-rep')!.getAttribute('aria-selected')).toBe('true');
    } finally { m.el.remove(); }
  });

  it('las advertencias completas de la final solo están en la sección de estimaciones; la reposición lleva su aviso de simulación', async () => {
    const m = await openFinal();
    expect(q(m.el, 'panel-rep')!.querySelector('[data-testid="final-warnings"]')).toBeNull();
    expect(q(m.el, 'panel-est')!.querySelector('[data-testid="final-warnings"]')).toBeTruthy();
    const rep = q(m.el, 'panel-rep')!;
    expect(rep.querySelector('[data-testid="sim-notice"]')!.textContent).toContain('Inventario simulado con supuestos; no corresponde al inventario real de la empresa');
    expect(txt(m.el, 'final-sim-label')).toContain('Más servicio puede ir con más stock y más compras');
    expect(txt(m.el, 'final-sim-label')).toContain('no es mejora neta ni impacto real');
    expect(rep.querySelector('[data-testid="sim-conclusion"]')).toBeTruthy();
    expect(q(m.el, 'reco-table')).toBeNull();
    expect(m.el.querySelector('a[href*="recomendaciones"]')).toBeNull();
  });

  it('ejemplo histórico: pestañas y aviso de simulación en la sección de reposición', async () => {
    const m = await openHist();
    expect(m.el.querySelectorAll('[role="tab"]').length).toBe(2);
    await keydown(m, 'jump-est', 'ArrowRight');
    const rep = q(m.el, 'panel-rep') as HTMLElement;
    expect(rep.hidden).toBe(false);
    expect(rep.querySelector('[data-testid="sim-notice"]')!.textContent).toContain('Inventario simulado con supuestos; no corresponde al inventario real de la empresa');
    expect(rep.querySelector('[data-testid="sim-conclusion"]')).toBeTruthy();
    expect((q(m.el, 'panel-est') as HTMLElement).hidden).toBe(true);
  });
});

describe('UX01R Evaluación: precisiones de lenguaje', () => {
  it('el agregado se llama «resultado agregado de 4 bloques», no «promedio de 4 bloques» ni «promedio de folds»', async () => {
    const m = await openHist();
    expect(txt(m.el, 'est-conclusion')).toContain('resultado agregado de 4 bloques solapados (G1 a G4)');
    expect(txt(m.el, 'eval-scope-simple')).toContain('resultado agregado de 4 bloques');
    const t = m.el.textContent!;
    expect(t).not.toContain('promedio de 4 bloques');
    expect(t).not.toMatch(/promedio de (los )?(folds|bloques)/i);
    await choose(m.f, m.el, 'pred-fold', 'G4');
    expect(txt(m.el, 'est-conclusion')).toContain('bloque G4');
    expect(txt(m.el, 'eval-scope-simple')).toContain('bloque G4');
  });

  it('la ventana de 28 días se explica como calendario con días válidos, ceros incluidos y días excluidos fuera', async () => {
    const m = await openHist();
    const lim = txt(m.el, 'limits');
    expect(lim).toContain('ventana de 28 días de calendario');
    expect(lim).toContain('se usan los días válidos, incluidos los de venta cero; los días excluidos no cuentan');
    expect(lim).toContain('No toda serie tiene 28 días de historia');
    expect(m.el.textContent).not.toContain('últimos 28 días con ventas registradas');
  });

  it('un análisis generado sin evaluación: no afirma que no existan ventas posteriores; dice que no incluye evaluación, por diseño', async () => {
    const m = await mountAt(ComparisonPage, '/comparacion?run=gen-test-1');
    await ok(m.f, one(m.http, '/api/v1/runs'), page([histRun, genRun]));
    await ok(m.f, one(m.http, '/api/v1/backtests'), page([]));
    await ok(m.f, m.http.expectOne((r) => r.url === '/api/v1/backtests' && !r.params.has('run_id')), realBacktestList);
    const t = txt(m.el, 'no-backtest');
    expect(t).toContain('no incluye una evaluación contra ventas registradas, por diseño');
    expect(t).not.toMatch(/No hay ventas posteriores|no existen ventas/i);
    expect(q(m.el, 'eval-summary')).toBeNull();
    expect(q(m.el, 'sim-conclusion')).toBeNull();
  });

  it('la final no genera pedidos y ningún valor de reposición aparece sin su aviso', async () => {
    const m = await openFinal();
    expect(visibleText(m.el)).toContain('no se generan pedidos ni recomendaciones');
    const rep = q(m.el, 'panel-rep')!;
    expect(rep.querySelector('[data-testid="final-sim-main"]')).toBeTruthy();
    expect(rep.querySelector('[data-testid="sim-notice"]')).toBeTruthy();
  });
});
