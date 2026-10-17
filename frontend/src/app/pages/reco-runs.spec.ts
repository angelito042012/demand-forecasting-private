import { RecommendationsPage } from './recommendations.page';
import { RunsPage } from './runs.page';
import { Recommendation, RecoPage } from '../core/models';
import { page } from '../testing/fixtures';
import { realRecoDetail, realRecoPage, realRunDetail, realRunSummary } from '../testing/real-shapes';
import { mountPage, reqOf, respond, visibleText } from '../testing/mount';

const SUPERSEDED = { status: 'superseded', validation_status: 'valid', quality_issue: { superseded_by: 'hist-20260710-NEW', reason: 'Error de redondeo en el objetivo' } };

async function openReco(list: RecoPage = realRecoPage, detail: Recommendation = realRecoDetail) {
  const m = mountPage(RecommendationsPage);
  await respond(m.f, reqOf(m.http, '/api/v1/recommendations'), list);
  (m.el.querySelector('[data-testid="reco-table"] tbody button') as HTMLButtonElement).click();
  await respond(m.f, reqOf(m.http, `/api/v1/recommendations/${list.items[0].sku}`), detail);
  return m;
}

describe('Recomendaciones: una sola explicación, enteros y formato', () => {
  it('la lista muestra stock, tránsito y pedido enteros y el valor en PEN con 2 decimales', async () => {
    const m = mountPage(RecommendationsPage);
    await respond(m.f, reqOf(m.http, '/api/v1/recommendations'), realRecoPage);
    const first = m.el.querySelector('[data-testid="reco-table"] tbody tr')!.textContent!.replace(/\s+/g, ' ');
    expect(first).toContain('26120367');
    expect(first).toContain('386.75 PEN');
    const cells = Array.from(m.el.querySelector('[data-testid="reco-table"] tbody tr')!.querySelectorAll('td')).map((c) => c.textContent!.trim());
    expect(cells.slice(3, 7)).toEqual(['0', '0', '70', '386.75 PEN']);
    const t = m.el.querySelector('[data-testid="reco-table"]')!.textContent!;
    expect(t).not.toMatch(/\d\.\d{4,}/);
    m.http.verify();
  });

  it('el detalle tiene UNA lista numerada visible; el texto técnico completo va plegado', async () => {
    const m = await openReco();
    const visibleLists = Array.from(m.el.querySelectorAll('ol')).filter((o) => !o.closest('details'));
    expect(visibleLists.length).toBe(1);
    expect(visibleLists[0].getAttribute('data-testid')).toBe('calc-steps');
    expect(visibleLists[0].querySelectorAll('li').length).toBe(9);
    const tech = m.el.querySelector('[data-testid="tech-details"]') as HTMLDetailsElement;
    expect(tech.open).toBe(false);
    expect(tech.textContent).toContain('explanation_steps');
    expect(tech.textContent).toContain('T07_L7_S7_promedio_28_2026-07-10');
    expect(tech.textContent).toContain('hist-20260710-52b01cd999dd');
    m.http.verify();
  });

  it('nunca muestra 4.9999999994 fuera del detalle plegado; los pasos usan enteros y ≤ 3 decimales', async () => {
    const m = await openReco();
    const vis = visibleText(m.el);
    expect(vis).not.toContain('4.9999999994');
    expect(vis).not.toContain('4.99999');
    expect(vis).not.toMatch(/\d\.\d{4,}/);
    const steps = Array.from(m.el.querySelectorAll('[data-testid="calc-steps"] li')).map((x) => x.textContent!.replace(/\s+/g, ' '));
    expect(steps[0]).toContain('5 unidades');
    expect(steps[1]).toContain('2 unidades');
    expect(steps[2]).toContain('5 + 2 = 7 unidades');
    expect(steps[3]).toContain('0.357');
    expect(steps[4]).toContain('= 5 unidades');
    expect(steps[5]).toContain('= 2.5 unidades');
    expect(steps[6]).toContain('= 8 unidades');
    expect(steps[7]).toContain('= 1 unidades');
    expect(steps[8]).toContain('42.25 PEN');
    expect(m.el.querySelector('[data-testid="order-result"]')?.textContent).toBe('1 unidades base');
    // el valor exacto publicado no se pierde: está en el detalle plegado
    expect((m.el.querySelector('[data-testid="tech-details"]') as HTMLElement).textContent).toContain('4.999999999400001');
    m.http.verify();
  });

  it('con sum_28, days_28 y mean_28_exact muestra «12 unidades en 28 días útiles = 3/7 por día»', async () => {
    const exact: Recommendation = {
      ...realRecoDetail, sum_28: 12, days_28: 28, mean_28_exact: '3/7', mean_28: 0.4285714286,
      on_hand: 5, in_transit: 4, position: 9, forecast_14d: 5.9999999996, safety: 3.0000000002, target: 9, order_qty: 0, order_value_assumed: 0,
    };
    const m = await openReco(realRecoPage, exact);
    const steps = Array.from(m.el.querySelectorAll('[data-testid="calc-steps"] li')).map((x) => x.textContent!);
    expect(steps[3]).toContain('12 unidades en 28 días útiles = 3/7 por día');
    expect(steps[6]).toContain('= 9 unidades');
    expect(m.el.querySelector('[data-testid="incoherent"]')).toBeNull();
    expect(visibleText(m.el)).not.toContain('5.9999999996');
    m.http.verify();
  });
});

describe('Recomendaciones: corrida sustituida', () => {
  it('banner con el aviso, el motivo y el enlace a la corrida corregida (lista y detalle)', async () => {
    const list: RecoPage = { ...realRecoPage, run: { ...realRecoPage.run!, ...SUPERSEDED } };
    const detail: Recommendation = { ...realRecoDetail, run: { ...realRecoDetail.run!, ...SUPERSEDED } };
    const m = await openReco(list, detail);
    const banners = m.el.querySelectorAll('[data-testid="superseded-banner"]');
    expect(banners.length).toBe(2);
    const t = banners[0].textContent!;
    expect(t).toContain('Esta corrida fue sustituida por una corrección de precisión (recomendaciones con error de redondeo); no use sus pedidos');
    expect(t).toContain('Error de redondeo en el objetivo');
    const link = banners[0].querySelector('a[data-testid="superseded-link"]') as HTMLAnchorElement;
    expect(link.getAttribute('href')).toContain('run=hist-20260710-NEW');
    m.http.verify();
  });

  it('validation_status distinto de valid también activa el banner; una corrida válida no lo muestra', async () => {
    const bad: RecoPage = { ...realRecoPage, run: { ...realRecoPage.run!, validation_status: 'invalid' } };
    const m = mountPage(RecommendationsPage);
    await respond(m.f, reqOf(m.http, '/api/v1/recommendations'), bad);
    expect(m.el.querySelector('[data-testid="superseded-banner"]')).toBeTruthy();
    m.http.verify();
  });

  it('una corrida válida y completada no muestra el banner', async () => {
    const ok = mountPage(RecommendationsPage);
    await respond(ok.f, reqOf(ok.http, '/api/v1/recommendations'), { ...realRecoPage, run: { ...realRecoPage.run!, status: 'completed', validation_status: 'valid' } });
    expect(ok.el.querySelector('[data-testid="superseded-banner"]')).toBeNull();
    ok.http.verify();
  });
});

describe('Corridas: estado y motivo', () => {
  it('lista completada y sustituida con su estado y motivo', async () => {
    const m = mountPage(RunsPage);
    const old = { ...realRunSummary, run_id: 'hist-old', is_active: false, ...SUPERSEDED };
    await respond(m.f, reqOf(m.http, '/api/v1/runs'), page([realRunSummary, old]));
    const rows = m.el.querySelectorAll('[data-testid="runs-table"] tbody tr');
    expect(rows.length).toBe(2);
    expect(rows[0].querySelector('[data-testid="run-status"]')?.textContent).toBe('Completada');
    expect(rows[1].querySelector('[data-testid="run-status"]')?.textContent).toBe('Sustituida');
    expect(rows[1].querySelector('[data-testid="run-reason"]')?.textContent).toContain('Error de redondeo en el objetivo');
    expect(rows[0].textContent).toContain('10/07/2026');
    m.http.verify();
  });

  it('detalle de corrida sustituida: banner; documento completo y checksums plegados', async () => {
    const m = mountPage(RunsPage);
    await respond(m.f, reqOf(m.http, '/api/v1/runs'), page([realRunSummary]));
    (m.el.querySelector('[data-testid="runs-table"] button') as HTMLButtonElement).click();
    await respond(m.f, reqOf(m.http, `/api/v1/runs/${realRunSummary.run_id}`), { ...realRunDetail, ...SUPERSEDED });
    expect(m.el.querySelector('[data-testid="superseded-banner"]')).toBeTruthy();
    expect(m.el.querySelector('[data-testid="detail-status"]')?.textContent).toContain('Sustituida');
    const doc = m.el.querySelector('[data-testid="run-doc"]') as HTMLDetailsElement;
    expect(doc.open).toBe(false);
    expect(doc.textContent).toContain(realRunDetail.artifacts![0].sha256);
    expect(visibleText(m.el)).not.toContain(realRunDetail.artifacts![0].sha256);
    expect(m.el.querySelector('[data-testid="coverage"]')?.textContent).toContain('3,347');
    m.http.verify();
  });
});
