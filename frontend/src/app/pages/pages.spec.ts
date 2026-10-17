import { Type } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { DataService, MockScenario } from '../core/data.service';
import { ImportsPage } from './imports.page';
import { ForecastsPage } from './forecasts.page';
import { RecommendationsPage } from './recommendations.page';
import { SystemPage } from './system.page';
import { ageDays, isStale } from '../core/age';

const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function render(cmp: Type<unknown>, scenario: MockScenario, ms: number) {
  TestBed.configureTestingModule({ imports: [cmp] });
  TestBed.inject(DataService).scenario.set(scenario);
  const f = TestBed.createComponent(cmp);
  f.detectChanges();
  const el = f.nativeElement as HTMLElement;
  const initial = el.querySelector('[data-state]')?.getAttribute('data-state');
  await wait(ms);
  f.detectChanges();
  return { el, initial };
}

const pages: [string, Type<unknown>][] = [
  ['imports', ImportsPage],
  ['forecasts', ForecastsPage],
  ['recommendations', RecommendationsPage],
  ['system', SystemPage],
];

describe.each(pages)('%s', (_n, cmp) => {
  it('muestra carga y luego datos con insignia de demostración', async () => {
    const { el, initial } = await render(cmp, 'data', 600);
    expect(initial).toBe('loading');
    expect(el.querySelector('[data-state="data"]')).toBeTruthy();
    expect(el.textContent).toContain('DATOS DE DEMOSTRACIÓN – no son resultados reales');
  });
  it('muestra estado vacío', async () => {
    if (cmp === SystemPage) return; // health no tiene estado vacío
    const { el } = await render(cmp, 'empty', 600);
    expect(el.querySelector('[data-state="empty"]')).toBeTruthy();
  });
  it('muestra error con reintento', async () => {
    const { el } = await render(cmp, 'error', 600);
    expect(el.querySelector('[data-state="error"]')).toBeTruthy();
    expect(el.querySelector('button')?.textContent).toContain('Reintentar');
  });
});

describe('antigüedad', () => {
  const now = new Date('2026-03-01T00:00:00-05:00');
  it('calcula días y marca antiguo', () => {
    expect(ageDays('2026-02-02T08:00:00-05:00', now)).toBe(26);
    expect(isStale('2026-02-02T08:00:00-05:00', now)).toBe(true);
    expect(isStale('2026-02-28T08:00:00-05:00', now)).toBe(false);
    expect(isStale(null, now)).toBe(true);
  });
});
