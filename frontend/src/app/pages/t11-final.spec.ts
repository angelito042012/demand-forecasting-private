// Pruebas T11A (sin backend real): evaluación final en Corridas, Pronósticos, Recomendaciones y Comparación.
// Los datos son fixtures de FORMA con números inventados (testing/final-shapes.ts); no son resultados de T12.
import { Type } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting, TestRequest } from '@angular/common/http/testing';
import { Router, provideRouter } from '@angular/router';
import { apiInterceptor } from '../core/http.interceptor';
import { demoInterceptor } from '../core/demo';
import { AuthService } from '../core/auth.service';
import { RunsPage } from './runs.page';
import { ForecastsPage } from './forecasts.page';
import { RecommendationsPage } from './recommendations.page';
import { ComparisonPage } from './comparison.page';
import { fmtInt, fmtPct, fmtPen, fmtPp } from '../core/format';
import { page } from '../testing/fixtures';
import { realBacktest, realBacktestList } from '../testing/real-shapes';
import { visibleText } from '../testing/mount';
import { FINAL_ID, HIST_ID, PHASES, SEAL, finalBacktest, finalBacktestList, finalForecasts, finalRecoPage, finalRun, genRun, histRun } from '../testing/final-shapes';
import { FINAL_WARNINGS, RunDetail } from '../core/models';

interface M<T> { f: ComponentFixture<T>; http: HttpTestingController; el: HTMLElement }
let lastHttp: HttpTestingController | undefined;

async function mountAs<T>(cmp: Type<T>, url = '/x'): Promise<M<T>> {
  TestBed.configureTestingModule({
    imports: [cmp],
    providers: [
      provideHttpClient(withInterceptors([apiInterceptor, demoInterceptor])), provideHttpClientTesting(),
      provideRouter([{ path: '**', children: [] }]),
    ],
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
async function choose(f: ComponentFixture<unknown>, el: HTMLElement, id: string, v: string) {
  const s = q(el, id) as HTMLSelectElement; s.value = v; s.dispatchEvent(new Event('change')); await settle(f);
}

afterEach(() => { lastHttp?.verify(); lastHttp = undefined; });

/** Abre «Detalles técnicos» del análisis (como lo haría el usuario) y responde al detalle completo. */
async function openTech(m: M<RunsPage>, id: string, detail: RunDetail) {
  const d = q(m.el, 'tech-' + id) as HTMLDetailsElement;
  d.open = true;
  d.dispatchEvent(new Event('toggle'));
  await ok(m.f, one(m.http, `/api/v1/runs/${id}`), detail);
}

describe('T11A Corridas: tipos y paquete de la evaluación final', () => {
  it('rotula histórica, generada y evaluación final; la final no figura como activa', async () => {
    const m = await mountAs(RunsPage);
    await ok(m.f, one(m.http, '/api/v1/runs'), page([finalRun, histRun, genRun]));
    // el análisis en uso por defecto va primero; la evaluación final nunca figura como «en uso por defecto»
    const cards = Array.from(m.el.querySelectorAll('[data-testid^="run-card-"]'));
    expect(cards.map((c) => c.querySelector('[data-testid="run-name"]')!.textContent)).toEqual(['Ejemplo de julio', 'Evaluación de agosto', 'Análisis creado con ventas hasta el 10/06/2026']);
    expect(cards.map((c) => c.querySelector('[data-testid="run-kind"]')!.textContent)).toEqual(['Ejemplo histórico', 'Evaluación', 'Creado en la aplicación']);
    const status = (i: number) => cards[i].querySelector('[data-testid="run-status"]')!.textContent;
    expect(status(0)).toBe('En uso por defecto');
    expect(status(1)).toBe('Disponible');
    const fin = cards[1];
    expect(fin.textContent).toContain('Permite comparar estimaciones con ventas registradas; no genera pedidos');
    expect(fin.querySelector('[data-testid="to-reco"]')).toBeNull();            // sin «Ver reposición» en la evaluación
    expect(fin.querySelector('[data-testid="to-forecasts"]')!.getAttribute('href')).toContain('run=' + FINAL_ID);
    expect(fin.querySelector('[data-testid="to-compare"]')).toBeTruthy();
    expect(cards[0].querySelector('[data-testid="to-reco"]')!.getAttribute('href')).toContain('run=' + HIST_ID);
    expect(cards[2].textContent).toContain('todavía no hay ventas registradas para comparar');   // sin backtest atribuido
    expect(cards[2].textContent).not.toContain('Permite comparar');
    expect(visibleText(m.el)).not.toContain(FINAL_ID);           // identificadores solo en detalles técnicos
  });

  it('el detalle de la final muestra sello corto, siete fases, auditoría aprobada, corrección R11 y advertencias', async () => {
    const m = await mountAs(RunsPage);
    await ok(m.f, one(m.http, '/api/v1/runs'), page([finalRun, histRun]));
    await openTech(m, FINAL_ID, { ...finalRun, fingerprint_short: 'f73f00a79ad0' } as RunDetail);
    expect(txt(m.el, 'detail-kind')).toBe('Evaluación final (T12)');
    expect(txt(m.el, 'pkg-seal')).toBe(SEAL.slice(0, 12));
    expect(txt(m.el, 'pkg-audit')).toContain('aprobada');
    const phases = Array.from(m.el.querySelectorAll('[data-testid="pkg-phases"] tbody tr')).map((r) => r.querySelector('td')!.textContent);
    expect(phases).toEqual(PHASES);
    expect(txt(m.el, 'pkg-corrections')).toContain('R11');
    const w = txt(m.el, 'final-warnings');
    for (const t of FINAL_WARNINGS) expect(w).toContain(t);
    expect(txt(m.el, 'run-dates')).toContain('01/08/2026 al 21/08/2026');
    expect(txt(m.el, 'method')).toContain('no se declara ganador');
  });

  it('la auditoría NO aprobada o ausente no se presenta como aprobada', async () => {
    const m = await mountAs(RunsPage, '/corridas?run=' + FINAL_ID);
    await ok(m.f, one(m.http, '/api/v1/runs'), page([finalRun]));
    await openTech(m, FINAL_ID, { ...finalRun, final_package: { ...finalRun.final_package, audit_ok: false, corrections: [] } } as RunDetail);
    expect(txt(m.el, 'pkg-audit')).toContain('NO aprobada');
    expect(q(m.el, 'pkg-no-corrections')).toBeTruthy();
  });

  it('una corrida histórica no muestra paquete final ni advertencias de la final', async () => {
    const m = await mountAs(RunsPage, '/corridas?run=' + HIST_ID);
    await ok(m.f, one(m.http, '/api/v1/runs'), page([histRun]));
    await openTech(m, HIST_ID, { ...histRun, method: { chosen: 'promedio_28', comparator: 'rf_categoria_distribuido', control: 'cero' } } as RunDetail);
    expect(q(m.el, 'final-package')).toBeNull();
    expect(q(m.el, 'final-warnings')).toBeNull();
  });

  it('API caída: error de API, sin datos de relleno', async () => {
    const m = await mountAs(RunsPage);
    one(m.http, '/api/v1/runs').flush({ error: { code: 'SERVICIO_NO_DISPONIBLE', message: 'caído' } }, { status: 503, statusText: 'x' });
    await settle(m.f);
    expect(q(m.el, 'runs-list')).toBeNull();
    expect(m.el.querySelector('[role="alert"]')).toBeTruthy();
  });
});

describe('T11A Pronósticos: evaluación final', () => {
  it('rango 01–21/08, advertencias, cohortes y día no evaluable rotulado (no cero)', async () => {
    const m = await mountAs(ForecastsPage, '/pronosticos?run=' + FINAL_ID);
    await ok(m.f, one(m.http, '/api/v1/runs'), page([finalRun, histRun]));
    const fr = one(m.http, '/api/v1/forecasts');
    expect(fr.request.params.get('run_id')).toBe(FINAL_ID);
    await ok(m.f, fr, finalForecasts());
    expect(txt(m.el, 'run-dates')).toContain('01/08/2026 al 21/08/2026');
    expect(txt(m.el, 'analysis-name')).toBe('Evaluación de agosto');
    const w = txt(m.el, 'final-warnings');
    expect(w).toContain('WAPE no es exactitud');
    expect(w).toContain('Categoría = suma de unidades base heterogéneas');
    expect(txt(m.el, 'final-note')).toContain('no evaluable');
    expect((q(m.el, 'f-to') as HTMLInputElement).getAttribute('max')).toBe('2026-08-21');
    expect((q(m.el, 'f-from') as HTMLInputElement).getAttribute('min')).toBe('2026-08-01');
    const obs = Array.from(m.el.querySelectorAll('[data-testid="observed"]')).map((c) => c.textContent!.trim());
    expect(obs).toEqual(['2', 'no evaluable', '0']);        // el cero real se conserva; el día sin registros NO es cero
    (q(m.el, 'toggle-details') as HTMLButtonElement).click();       // tipo de historial y modelo experimental: en «ver detalles»
    await settle(m.f);
    const cohortes = Array.from(m.el.querySelectorAll('[data-testid="forecast-table"] tbody tr')).map((r) => r.querySelectorAll('td')[5].textContent);
    expect(cohortes).toEqual(['primaria', 'historia_corta', 'primaria']);
    expect(txt(m.el, 'forecast-table')).toContain('Modelo experimental');
    expect(txt(m.el, 'forecast-note')).not.toContain('no incluyen agosto');
    expect(q(m.el, 'insufficient')).toBeTruthy();
  });

  it('una corrida no final conserva el tope del 31/07 y no muestra textos de la final', async () => {
    const m = await mountAs(ForecastsPage);
    await ok(m.f, one(m.http, '/api/v1/runs'), page([finalRun, histRun]));
    await ok(m.f, one(m.http, '/api/v1/forecasts'), page([]));
    expect((q(m.el, 'f-to') as HTMLInputElement).getAttribute('max')).toBe('2026-07-31');
    expect(q(m.el, 'final-warnings')).toBeNull();
    expect(txt(m.el, 'analysis-name')).toBe('Ejemplo de julio');
  });

  it('el selector de corrida rotula el tipo de cada opción', async () => {
    const m = await mountAs(ForecastsPage);
    await ok(m.f, one(m.http, '/api/v1/runs'), page([finalRun, histRun, genRun]));
    await ok(m.f, one(m.http, '/api/v1/forecasts'), page([]));
    const opts = Array.from(m.el.querySelectorAll('[data-testid="run-select"] option')).map((o) => o.textContent!);
    expect(opts[0]).toBe('Evaluación de agosto');
    expect(opts[1]).toBe('Ejemplo de julio · en uso por defecto');
    expect((q(m.el, 'run-select') as HTMLSelectElement).value).toBe(HIST_ID);
  });

  it('error de API: se muestra el error y ninguna fila', async () => {
    const m = await mountAs(ForecastsPage, '/pronosticos?run=' + FINAL_ID);
    await ok(m.f, one(m.http, '/api/v1/runs'), page([finalRun]));
    const r = one(m.http, '/api/v1/forecasts');
    r.flush({ error: { code: 'SERVICIO_NO_DISPONIBLE', message: 'caído' } }, { status: 503, statusText: 'x' });
    await settle(m.f);
    expect(q(m.el, 'forecast-table')).toBeNull();
    expect(m.el.querySelector('[role="alert"]')).toBeTruthy();
  });
});

describe('T11A Recomendaciones: evaluación final', () => {
  it('muestra el motivo de no disponibilidad y enlaza a la demostración histórica; no inventa stock ni pedidos', async () => {
    const m = await mountAs(RecommendationsPage, '/recomendaciones?run=' + FINAL_ID);
    await ok(m.f, one(m.http, '/api/v1/runs'), page([finalRun, histRun]));
    const r = one(m.http, '/api/v1/recommendations');
    expect(r.request.params.get('run_id')).toBe(FINAL_ID);
    await ok(m.f, r, finalRecoPage());
    expect(txt(m.el, 'reco-reason-code')).toBe('RECOMENDACION_NO_VALIDADA_PARA_ESTE_ORIGEN');
    expect(txt(m.el, 'reco-unavailable')).toContain('La evaluación de agosto compara estimaciones con ventas registradas; no genera pedidos');
    const link = q(m.el, 'see-run') as HTMLAnchorElement;
    expect(link.getAttribute('href')).toContain('run=' + HIST_ID);
    expect(q(m.el, 'reco-table')).toBeNull();
    expect(q(m.el, 'reco-detail')).toBeNull();
    expect(m.el.querySelector('form.filters')).toBeNull();
    expect(visibleText(m.el)).toContain('Inventario simulado con supuestos; no corresponde al inventario real de la empresa');
    expect(txt(m.el, 'analysis-name')).toBe('Evaluación de agosto');
  });

  it('sin see_run no inventa un enlace', async () => {
    const m = await mountAs(RecommendationsPage, '/recomendaciones?run=' + FINAL_ID);
    await ok(m.f, one(m.http, '/api/v1/runs'), page([finalRun, histRun]));
    await ok(m.f, one(m.http, '/api/v1/recommendations'), finalRecoPage(null));
    expect(q(m.el, 'see-run')).toBeNull();
    expect(q(m.el, 'no-see-run')).toBeTruthy();
  });

  it('una página vacía SIN motivo sigue siendo «sin recomendaciones» (estado vacío)', async () => {
    const m = await mountAs(RecommendationsPage);
    await ok(m.f, one(m.http, '/api/v1/runs'), page([histRun]));
    await ok(m.f, one(m.http, '/api/v1/recommendations'), page([]));
    expect(q(m.el, 'reco-unavailable')).toBeNull();
    expect(m.el.textContent).toContain('ningún producto tiene sugerencia de reposición');
  });
});

describe('T11A Comparación: evaluación final (T12) separada de T07', () => {
  async function openFinal() {
    const m = await mountAs(ComparisonPage, '/comparacion?run=' + FINAL_ID);
    await ok(m.f, one(m.http, '/api/v1/runs'), page([finalRun, histRun]));
    const list = one(m.http, '/api/v1/backtests');
    expect(list.request.params.get('run_id')).toBe(FINAL_ID);
    await ok(m.f, list, finalBacktestList);
    await new Promise((r) => setTimeout(r, 0));
    const d = one(m.http, `/api/v1/backtests/${finalBacktest.backtest_id}`);
    expect(d.request.params.get('view')).toBe('all');
    await ok(m.f, d, finalBacktest);
    return m;
  }

  it('no mezcla la vista T07: sin tabla T07, sin período 01/06–31/07 ni «agosto sigue reservado»', async () => {
    const m = await openFinal();
    expect(q(m.el, 'final-view')).toBeTruthy();
    expect(q(m.el, 'sim-table')).toBeNull();
    expect(q(m.el, 'pred-table')).toBeNull();
    expect(q(m.el, 'periods')).toBeNull();
    expect(q(m.el, 'limits')).toBeNull();
    const t = visibleText(m.el);
    expect(t).not.toContain('agosto sigue reservado');
    expect(t).not.toContain('01/06/2026');
    expect(t).toContain('Evaluación de agosto');
    expect(txt(m.el, 'bt-label')).toContain('Evaluación de agosto');
    expect(t).toContain('Ya hay un resultado final disponible');
  });

  it('hallazgo primario: WAPE H14 de promedio_28, RF y cero con n, mejora relativa, sesgo y sin ganador declarado', async () => {
    const m = await openFinal();
    expect(txt(m.el, 'primary-n')).toBe(fmtInt(1000));
    expect(txt(m.el, 'primary-promedio')).toContain(fmtPct(0.5));
    expect(txt(m.el, 'primary-rf')).toContain(fmtPct(0.6));
    expect(txt(m.el, 'primary-cero')).toContain(fmtPct(1));
    expect(txt(m.el, 'primary-mejora')).toContain(fmtPct(-0.2, true));
    expect(txt(m.el, 'primary-sesgo')).toContain(fmtPct(0.04, true));
    expect(txt(m.el, 'primary-winner')).toContain('RF declarado ganador: no');
    // sesgo/observado calculado de cifras publicadas de la fila: 500 / 5000 = 10,0 %
    expect(txt(m.el, 'primary-promedio')).toContain(fmtPct(0.1, true));
    expect(visibleText(m.el)).not.toMatch(/RF (es el )?ganador(?! declarado)/);
  });

  it('advertencias obligatorias y rótulo de inventario simulado', async () => {
    const m = await openFinal();
    const w = txt(m.el, 'final-warnings');
    for (const t of FINAL_WARNINGS) expect(w).toContain(t);
    const vis = visibleText(m.el);
    expect(vis).toContain('Inventario simulado con supuestos; no corresponde al inventario real de la empresa');
    expect(txt(m.el, 'final-legend')).toContain('WAPE no es exactitud');
  });

  it('tablas H10/H14/H21/diaria para SKU y categoría; historia corta; WAPE indefinido = «no evaluable» (no cero)', async () => {
    const m = await openFinal();
    for (const v of ['acum10', 'acum14', 'acum21', 'diaria']) {
      expect(q(m.el, `final-table-${v}`)).toBeTruthy();
      expect(m.el.querySelectorAll(`[data-testid="final-table-${v}"] tbody tr`).length).toBe(3);
    }
    expect(txt(m.el, 'frow-diaria-promedio_28')).toContain(fmtPct(1.5));    // WAPE > 100 % se muestra tal cual
    expect(q(m.el, 'cat-note')).toBeNull();
    await choose(m.f, m.el, 'final-level', 'categoria');
    expect(txt(m.el, 'cat-note')).toContain('Categoría = suma de unidades base heterogéneas');
    expect(txt(m.el, 'frow-acum14-rf_categoria')).toContain('RF por categoría');
    await choose(m.f, m.el, 'final-coh', 'historia_corta');
    const row = txt(m.el, 'frow-acum14-promedio_28');
    expect(row).toContain('no evaluable');
    expect(q(m.el, 'frow-acum14-promedio_28')!.querySelector('[data-testid="wape"]')!.textContent!.trim()).toBe('no evaluable');
    // cohorte historia corta (SKU) visible en el resumen
    expect(q(m.el, 'cs-historia_corta-promedio_28')).toBeTruthy();
    expect(q(m.el, 'cs-primaria-rf_distribuido')).toBeTruthy();
  });

  it('cobertura, universo común y SKU nuevos aparte', async () => {
    const m = await openFinal();
    const cov = txt(m.el, 'final-coverage');
    expect(cov).toContain(`universo común ${fmtInt(1000)} de ${fmtInt(1000)}`);
    expect(cov).toContain(`días evaluables del bloque: ${fmtInt(21)} de 21`);
    expect(cov).toContain('skus_nuevos_con_venta_en_bloque: 7');
    expect(txt(m.el, 'final-new-skus')).toContain('sin historia ni categoría inventadas');
  });

  it('simulación: escenario principal L7/S7, 27 combinaciones, diferencias y servicio frente a inventario', async () => {
    const m = await openFinal();
    expect(txt(m.el, 'final-sim')).toContain('L7 / S7');
    const main = m.el.querySelectorAll('[data-testid="final-sim-main"] tbody tr');
    expect(main.length).toBe(3);
    const b = finalBacktest.simulation!.find((s) => s.L === 7 && s.S === 7 && s.policy === 'rf_categoria_distribuido')!.total;
    const rf = txt(m.el, 'fmain-rf_categoria_distribuido');
    expect(rf).toContain(fmtPct(b['fill_rate'])); expect(rf).toContain(fmtInt(b['perdidas_unidades'])); expect(rf).toContain(fmtPen(b['compras_desembolsadas_supuesto']));
    expect(m.el.querySelectorAll('[data-testid="final-sim-27"] tbody tr').length).toBe(9);
    expect(txt(m.el, 'combos-count')).toContain('27 combinaciones publicadas de 27');
    // diferencias: las 4 parejas frente a referencia y promedio_28
    expect(m.el.querySelectorAll('[data-testid="final-sim-diffs"] tbody tr').length).toBe(4);
    const d = finalBacktest.simulation_differences!.find((x) => x.scenario === 'L7_S7' && x.policy === 'rf_categoria_distribuido' && x.vs === 'promedio_28' && x.cohorte === 'total')!;
    const dr = txt(m.el, 'fdiff-rf_categoria_distribuido-promedio_28');
    expect(dr).toContain(fmtPp(d.metrics['fill_rate'].abs));
    expect(dr).toContain(fmtPen(d.metrics['compras_desembolsadas_supuesto'].abs, true));
    // servicio frente a inventario: nueve escenarios
    expect(m.el.querySelectorAll('[data-testid="final-service-inventory"] tbody tr').length).toBe(9);
    expect(txt(m.el, 'fsvc-7-7')).toContain(fmtPct(d.metrics['compras_desembolsadas_supuesto'].rel, true));
    expect(txt(m.el, 'final-sim')).toContain('no se presenta como mejora');
    await choose(m.f, m.el, 'final-sim-coh', 'historia_corta');
    expect(m.el.querySelector('[data-testid="final-sim-main"] caption')!.textContent).toContain('Historia corta');
  });

  it('con un detalle sin simulación publica «datos insuficientes» (no ceros)', async () => {
    const m = await mountAs(ComparisonPage, '/comparacion?run=' + FINAL_ID);
    await ok(m.f, one(m.http, '/api/v1/runs'), page([finalRun, histRun]));
    await ok(m.f, one(m.http, '/api/v1/backtests'), finalBacktestList);
    await new Promise((r) => setTimeout(r, 0));
    await ok(m.f, one(m.http, `/api/v1/backtests/${finalBacktest.backtest_id}`), { ...finalBacktest, simulation: [], simulation_differences: [] });
    expect(q(m.el, 'final-sim-empty')).toBeTruthy();
    expect(q(m.el, 'final-sim-main')).toBeNull();
    expect(m.el.querySelectorAll('[data-testid="final-sim-27"] tbody tr').length).toBe(0);
  });

  it('sin corrida elegida abre el backtest T07 y deja la evaluación final como opción rotulada', async () => {
    const m = await mountAs(ComparisonPage);
    await ok(m.f, one(m.http, '/api/v1/runs'), page([finalRun, histRun]));
    const finalItem = { ...finalBacktestList.items[0], created: '2026-10-17T23:00:00Z' };
    await ok(m.f, one(m.http, '/api/v1/backtests'), page([finalItem, realBacktestList.items[0]]));
    await new Promise((r) => setTimeout(r, 0));
    const d = one(m.http, `/api/v1/backtests/${realBacktest.backtest_id}`);   // el T07, no el final
    await ok(m.f, d, realBacktest);
    expect(q(m.el, 'final-view')).toBeNull();
    expect(q(m.el, 'sim-table')).toBeTruthy();
    const opts = Array.from(m.el.querySelectorAll('[data-testid="bt-select"] option')).map((o) => o.textContent!);
    expect(opts[0]).toContain('Ejemplo de julio');
    expect(opts[1]).toContain('Evaluación de agosto');
  });

  it('error de API: se muestra el error, nunca resultados simulados', async () => {
    const m = await mountAs(ComparisonPage, '/comparacion?run=' + FINAL_ID);
    await ok(m.f, one(m.http, '/api/v1/runs'), page([finalRun, histRun]));
    one(m.http, '/api/v1/backtests').flush({ error: { code: 'SERVICIO_NO_DISPONIBLE', message: 'caído' } }, { status: 503, statusText: 'x' });
    await settle(m.f);
    expect(q(m.el, 'final-view')).toBeNull();
    expect(m.el.querySelector('[role="alert"]')).toBeTruthy();
  });
});
