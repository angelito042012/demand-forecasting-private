import { ComparisonPage } from './comparison.page';
import { fmtInt, fmtPct, fmtPen, fmtPp } from '../core/format';
import { BacktestDetail } from '../core/models';
import { realBacktest, realBacktestList, realRunSummary } from '../testing/real-shapes';
import { page } from '../testing/fixtures';
import { choose, mountPage, reqOf, respond, visibleText, settle } from '../testing/mount';

/** La barra de análisis pide la lista de análisis (RunsStore); se responde para que no quede ninguna petición pendiente. */
async function runs(m: ReturnType<typeof mountPage<ComparisonPage>>) {
  await respond(m.f, reqOf(m.http, '/api/v1/runs'), page([realRunSummary]));
}

async function open(detail: BacktestDetail = realBacktest) {
  const m = mountPage(ComparisonPage);
  await runs(m);
  await respond(m.f, reqOf(m.http, '/api/v1/backtests'), realBacktestList);
  await new Promise((r) => setTimeout(r, 0));
  const d = reqOf(m.http, `/api/v1/backtests/${realBacktest.backtest_id}`);
  expect(d.request.params.get('view')).toBe('all');
  await respond(m.f, d, detail);
  return m;
}
const block = (L: number, S: number, policy: string, coh = 'total') =>
  realBacktest.simulation!.find((s) => s.L === L && s.S === S && s.policy === policy)![coh as 'total'];
const rowText = (el: HTMLElement, id: string) => (el.querySelector(`[data-testid="${id}"]`)?.textContent ?? '').replace(/\s+/g, ' ');

afterEach(() => { /* HttpTestingController se verifica en cada prueba */ });

describe('Comparación: escenario principal y políticas', () => {
  it('abre con L7/S7, cohorte total y las tres políticas en una tabla compacta', async () => {
    const m = await open();
    expect((m.el.querySelector('[data-testid="sel-L"]') as HTMLSelectElement).value).toBe('7');
    expect((m.el.querySelector('[data-testid="sel-S"]') as HTMLSelectElement).value).toBe('7');
    expect((m.el.querySelector('[data-testid="sel-coh"]') as HTMLSelectElement).value).toBe('total');
    expect(m.el.querySelector('[data-testid="principal-badge"]')?.textContent).toContain('Escenario principal (L7 / S7)');
    const rows = m.el.querySelectorAll('[data-testid="sim-table"] tbody tr');
    expect(rows.length).toBe(3);
    const ids = Array.from(rows).map((r) => r.getAttribute('data-testid'));
    expect(ids).toEqual(['sim-row-referencia_fija', 'sim-row-promedio_28', 'sim-row-rf_categoria_distribuido']);

    const b = block(7, 7, 'promedio_28');
    const t = rowText(m.el, 'sim-row-promedio_28');
    expect(t).toContain(fmtPct(b['fill_rate']));
    expect(t).toContain(fmtInt(b['perdidas_unidades']));
    expect(t).toContain(fmtInt(b['stock_medio_unidades_por_dia']));
    expect(t).toContain(fmtPen(b['compras_desembolsadas_supuesto']));
    expect(t).toContain('base de comparación');
  });

  it('muestra diferencias frente a promedio_28 (abs y rel) con formato', async () => {
    const m = await open();
    const diff = realBacktest.simulation_differences!.find((d) => d.scenario === 'L7_S7' && d.policy === 'referencia_fija' && d.cohorte === 'total' && d.vs === 'promedio_28')!;
    const t = rowText(m.el, 'sim-row-referencia_fija');
    expect(t).toContain(fmtPp(diff.metrics['fill_rate'].abs));
    expect(t).toContain(fmtPct(diff.metrics['fill_rate'].rel, true));
    expect(t).toContain(fmtPen(diff.metrics['compras_desembolsadas_supuesto'].abs, true));
    expect(t).toContain(fmtInt(diff.metrics['perdidas_unidades'].abs, true));
  });

  it('los selectores L, S y cohorte cambian el escenario sin volcar los nueve a la vez', async () => {
    const m = await open();
    await choose(m.f, m.el, 'sel-L', '3');
    await choose(m.f, m.el, 'sel-S', '0');
    expect(m.el.querySelector('[data-testid="principal-badge"]')?.textContent).toContain('el principal es L7 / S7');
    expect(m.el.querySelectorAll('[data-testid="sim-table"] tbody tr').length).toBe(3);
    expect(rowText(m.el, 'sim-row-promedio_28')).toContain(fmtPct(block(3, 0, 'promedio_28')['fill_rate']));
    expect(rowText(m.el, 'sim-row-referencia_fija')).toContain(fmtPen(block(3, 0, 'referencia_fija')['compras_desembolsadas_supuesto']));

    await choose(m.f, m.el, 'sel-coh', 'historia_corta');
    expect(rowText(m.el, 'sim-row-promedio_28')).toContain(fmtPct(block(3, 0, 'promedio_28', 'historia_corta')['fill_rate']));
    expect(m.el.querySelector('[data-testid="sim-table"] caption')?.textContent).toContain('Historia corta');

    // escenario no incluido en el fixture recortado: aviso de datos insuficientes, no ceros
    await choose(m.f, m.el, 'sel-L', '14');
    expect(m.el.querySelector('[data-testid="sim-empty"]')?.textContent).toContain('Datos insuficientes');
    m.http.verify();
  });

  it('conserva todas las métricas y los resultados desfavorables en detalles plegados', async () => {
    const m = await open();
    const all = m.el.querySelector('[data-testid="sim-all-metrics"]') as HTMLDetailsElement;
    expect(all.open).toBe(false);
    expect(all.textContent).toContain('Días-SKU con faltante');
    expect(all.textContent).toContain('Costo de mantener stock');
    // la política RF (que no ganó) sigue visible, con su rótulo
    expect(rowText(m.el, 'sim-row-rf_categoria_distribuido')).toContain('no ganó');
    m.http.verify();
  });
});

describe('Comparación: lenguaje sencillo y detalles técnicos', () => {
  it('muestra el aviso exacto de inventario simulado, fecha histórica, que RF no ganó, stock/compras y folds solapados', async () => {
    const m = await open();
    const t = visibleText(m.el);
    expect(t).toContain('Inventario simulado con supuestos; no corresponde al inventario real de la empresa');
    expect(t).toContain('10/07/2026');
    expect(t).toContain('Ejemplo de julio');
    expect(t).toContain('Ventas utilizadas hasta');
    expect(t).toContain('no ganó');
    expect(t).toContain('más stock y más compras');
    expect(t).toContain('se solapan');
    expect(t).toContain('Resultados históricos de desarrollo');
    expect(t).toContain('27 combinaciones');
    // el detalle académico completo (leyenda de métricas) sigue en la página, plegado y fácil de encontrar
    const detail = m.el.querySelector('[data-testid="detail-pred"]') as HTMLDetailsElement;
    expect(detail.classList.contains('help')).toBe(true);
    expect(detail.open).toBe(false);
    expect(detail.querySelector('summary')?.textContent).toContain('Ver detalle completo');
    expect(detail.querySelector('[data-testid="pred-legend"]')?.textContent).toContain('WAPE = error absoluto total / unidades observadas');
    m.http.verify();
  });

  it('IDs internos, JSON y checksums solo dentro de <details> plegados', async () => {
    const m = await open();
    const vis = visibleText(m.el);
    for (const secret of [realBacktest.backtest_id!, realBacktest.run_id!, 'T07_L7_S7_R7', 'SYNTHETIC_NOT_REAL_INVENTORY', '"fill_rate"']) {
      expect(vis).not.toContain(secret);
    }
    const tech = m.el.querySelector('[data-testid="sim-tech"]') as HTMLDetailsElement;
    expect(tech.open).toBe(false);
    expect(tech.textContent).toContain(realBacktest.backtest_id!);
    expect(tech.textContent).toContain('"fill_rate"');
    m.http.verify();
  });

  it('la pantalla es compacta: no vuelca el árbol completo (pocas filas de tabla)', async () => {
    const m = await open();
    // 3 políticas + 5 métodos como máximo en tablas visibles (+ cabeceras); las métricas completas están plegadas
    const visibleRows = Array.from(m.el.querySelectorAll('tr')).filter((r) => !r.closest('details')).length;
    expect(visibleRows).toBeLessThan(20);
    expect(m.el.querySelector('app-data-tree')).toBeNull();
    m.http.verify();
  });
});

describe('Comparación: precisión predictiva', () => {
  const metodos = (el: HTMLElement) => Array.from(el.querySelectorAll('[data-testid="pred-table"] tbody tr')).map((r) => r.getAttribute('data-testid'));

  it('por defecto: SKU, cohorte primaria, acumulado 14 días, agregado; WAPE en % con leyenda', async () => {
    const m = await open();
    expect((m.el.querySelector('[data-testid="pred-vista"]') as HTMLSelectElement).value).toBe('acum14');
    expect((m.el.querySelector('[data-testid="pred-fold"]') as HTMLSelectElement).value).toBe('AGREGADO');
    expect(metodos(m.el)).toEqual(['pred-row-promedio_28', 'pred-row-rf_distribuido', 'pred-row-referencia_fija_0531', 'pred-row-cero']);
    const r = realBacktest.predictive!.sku!.find((x) => x.fold === 'AGREGADO' && x.cohorte === 'primaria' && x.vista === 'acum14' && x.metodo === 'promedio_28')!;
    const t = rowText(m.el, 'pred-row-promedio_28');
    expect(t).toContain(fmtInt(r.n));
    expect(t).toContain(fmtInt(r.unidades_observadas));
    expect(t).toContain(fmtInt(r.unidades_predichas));
    expect(m.el.querySelector('[data-testid="pred-row-promedio_28"] [data-testid="wape"]')?.textContent).toBe(fmtPct(r.WAPE));
    expect(t).toContain(`cobertura ${fmtPct(r.MAPE_cobertura_reales_positivos)}`);
    expect(t).toContain(`${fmtInt(r.MAPE_ceros_excluidos)} ceros excluidos`);
    expect(t).toMatch(/[\d,]+ de [\d,]+ \([\d.]+ %\)/);
    // el control cero y el método que no ganó se muestran, con su rol
    expect(rowText(m.el, 'pred-row-cero')).toContain('control');
    expect(rowText(m.el, 'pred-row-rf_distribuido')).toContain('no ganó');
    m.http.verify();
  });

  it('cambia con nivel, horizonte, fold y cohorte', async () => {
    const m = await open();
    await choose(m.f, m.el, 'pred-level', 'categoria');
    expect(metodos(m.el)).toEqual(['pred-row-promedio_28', 'pred-row-rf_categoria', 'pred-row-cero']);

    await choose(m.f, m.el, 'pred-level', 'sku');
    await choose(m.f, m.el, 'pred-fold', 'G4');
    const g4 = realBacktest.predictive!.sku!.find((x) => x.fold === 'G4' && x.cohorte === 'primaria' && x.vista === 'acum14' && x.metodo === 'promedio_28')!;
    expect(m.el.querySelector('[data-testid="pred-row-promedio_28"] [data-testid="wape"]')?.textContent).toBe(fmtPct(g4.WAPE));
    expect(m.el.querySelector('[data-testid="pred-table"] caption')?.textContent).toContain('G4');

    await choose(m.f, m.el, 'pred-vista', 'acum10');
    const a10 = realBacktest.predictive!.sku!.find((x) => x.fold === 'G4' && x.cohorte === 'primaria' && x.vista === 'acum10' && x.metodo === 'promedio_28')!;
    expect(m.el.querySelector('[data-testid="pred-row-promedio_28"] [data-testid="wape"]')?.textContent).toBe(fmtPct(a10.WAPE));

    await choose(m.f, m.el, 'pred-vista', 'acum14');
    await choose(m.f, m.el, 'pred-fold', 'AGREGADO');
    await choose(m.f, m.el, 'pred-coh', 'historia_corta');
    expect(m.el.querySelector('[data-testid="pred-row-promedio_28"]')).toBeTruthy();
    // vista sin datos en el fixture recortado -> aviso explícito
    await choose(m.f, m.el, 'pred-vista', 'diaria');
    expect(m.el.querySelector('[data-testid="pred-empty"]')?.textContent).toContain('Datos insuficientes');
    m.http.verify();
  });

  it('filas con n = 0 se rotulan «sin datos evaluables», sin métricas inventadas', async () => {
    const m = await open();
    await choose(m.f, m.el, 'pred-level', 'categoria');
    await choose(m.f, m.el, 'pred-coh', 'historia_corta');
    const z = m.el.querySelector('[data-testid="pred-row-promedio_28"]')!;
    expect(z.textContent).toContain('Sin datos evaluables');
    expect(z.querySelector('[data-testid="wape"]')).toBeNull();
    m.http.verify();
  });

  it('R² null se muestra «no evaluable» (con su nota) y MAPE null también', async () => {
    const copy: BacktestDetail = JSON.parse(JSON.stringify(realBacktest));
    const row = copy.predictive!.sku!.find((x) => x.fold === 'AGREGADO' && x.cohorte === 'primaria' && x.vista === 'acum14' && x.metodo === 'cero')!;
    row.R2 = null; row.R2_nota = 'varianza observada nula';
    row.MAPE = null;
    const m = await open(copy);
    const r = m.el.querySelector('[data-testid="pred-row-cero"]')!;
    expect(r.querySelector('[data-testid="r2"]')?.textContent).toContain('no evaluable');
    expect(r.querySelector('[data-testid="r2"]')?.textContent).toContain('varianza observada nula');
    expect(r.querySelector('[data-testid="mape"]')?.textContent).toContain('no evaluable');
    // otra fila con R² definido se muestra como número
    expect(m.el.querySelector('[data-testid="pred-row-promedio_28"] [data-testid="r2"]')?.textContent).not.toContain('no evaluable');
    m.http.verify();
  });

  it('explica WAPE, MAPE (solo reales positivos), R² y cobertura', async () => {
    const m = await open();
    const leg = m.el.querySelector('[data-testid="pred-legend"]')!.textContent!;
    expect(leg).toContain('WAPE = error absoluto total / unidades observadas');
    expect(leg).toContain('MAPE solo se calcula con ventas reales positivas');
    expect(leg).toContain('no evaluable');
    m.http.verify();
  });
});

describe('Comparación: estados', () => {
  it('error 503 en el detalle: mensaje y reintento, sin tablas ni datos de relleno', async () => {
    const m = mountPage(ComparisonPage);
    await runs(m);
    await respond(m.f, reqOf(m.http, '/api/v1/backtests'), realBacktestList);
    await new Promise((r) => setTimeout(r, 0));
    const d = reqOf(m.http, `/api/v1/backtests/${realBacktest.backtest_id}`);
    d.flush({}, { status: 503, statusText: 'x' });
    await settle(m.f);
    expect(m.el.querySelector('[data-state="error"]')).toBeTruthy();
    expect(m.el.querySelector('[data-testid="sim-table"]')).toBeNull();
    expect(m.el.textContent).not.toMatch(/DEMOSTRACIÓN/);
    m.http.verify();
  });
  it('sin backtests publicados: estado vacío', async () => {
    const m = mountPage(ComparisonPage);
    await runs(m);
    await respond(m.f, reqOf(m.http, '/api/v1/backtests'), []);
    expect(m.el.querySelector('[data-state="empty"]')?.textContent).toContain('Todavía no hay comparaciones publicadas');
    // el vacío ofrece una acción válida: ir a «Mis análisis»
    expect(m.el.querySelector('[data-testid="to-analyses"]')?.getAttribute('href')).toContain('/corridas');
    m.http.verify();
  });
});
