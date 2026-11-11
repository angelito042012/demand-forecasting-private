// R17 (REVISION_CODEX_16): un fallo de /runs queda visible, no se reintenta solo, se recupera con «Reintentar» y se comparte una carga.
import { Type } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideRouter, Router } from '@angular/router';
import { HomePage } from './home.page';
import { ForecastsPage } from './forecasts.page';
import { AuthService } from '../core/services/auth.service';
import { RunsStore } from '../core/runs-store';
import { apiInterceptor } from '../core/interceptors';
import { page, runSummary, session } from '../testing/fixtures';

const RUNS = '/api/v1/runs';
const reply503 = { error: { code: 'SERVICIO_NO_DISPONIBLE', message: 'No disponible' } };

function setup(cmp: Type<unknown>, url = '/inicio') {
  TestBed.configureTestingModule({
    imports: [cmp],
    providers: [provideHttpClient(withInterceptors([apiInterceptor])), provideHttpClientTesting(), provideRouter([{ path: '**', children: [] }])],
  });
  TestBed.inject(AuthService).session.set(session);
  const http = TestBed.inject(HttpTestingController);
  return { http, ready: TestBed.inject(Router).navigateByUrl(url) };
}
const settle = async (f: { detectChanges(): void; whenStable(): Promise<unknown> }) => { f.detectChanges(); await f.whenStable(); f.detectChanges(); };
const answerSideRequests = (http: HttpTestingController) => {
  http.match((r) => r.url === '/api/v1/plans/inputs').forEach((r) => r.flush({}));
  http.match((r) => r.url === '/api/v1/recommendations').forEach((r) => r.flush({ items: [], total: 0, page: 1, page_size: 1, has_more: false }));
  http.match((r) => r.url === '/api/v1/forecasts').forEach((r) => r.flush({ items: [], total: 0, page: 1, page_size: 50, has_more: false }));
};

describe('R17 · lista de análisis', () => {
  for (const [nombre, cmp, url] of [['Inicio', HomePage, '/inicio'], ['Ventas previstas', ForecastsPage, '/pronosticos']] as const) {
    it(`${nombre}: un 503 queda visible con «Reintentar», sin peticiones espontáneas; el botón hace UNA y recupera`, async () => {
      const { http, ready } = setup(cmp, url);
      await ready;
      const f = TestBed.createComponent(cmp as Type<unknown>);
      f.detectChanges();
      answerSideRequests(http);
      http.expectOne((r) => r.url === RUNS).flush(reply503, { status: 503, statusText: 'Service Unavailable' });
      await settle(f);
      answerSideRequests(http);
      const el = f.nativeElement as HTMLElement;
      expect(http.match((r) => r.url === RUNS).length, 'peticiones espontáneas tras el error').toBe(0);
      expect(el.querySelector('[data-testid="analysis-error"]')?.textContent).toContain('No pudimos cargar tus análisis');
      expect(el.querySelector('[data-testid="analysis-missing"]'), 'un error no es «análisis inexistente»').toBeNull();
      await settle(f);
      expect(http.match((r) => r.url === RUNS).length, 'sigue sin reintentar solo').toBe(0);
      (el.querySelector('[data-testid="analysis-retry"]') as HTMLButtonElement).click();
      const again = http.match((r) => r.url === RUNS);
      expect(again.length, 'una petición por reintento explícito').toBe(1);
      again[0].flush(page([runSummary]));
      await settle(f);
      answerSideRequests(http);
      expect(el.querySelector('[data-testid="analysis-error"]')).toBeNull();
      expect(el.querySelector('[data-testid="analysis-name"]')?.textContent).toBeTruthy();
      http.verify();
    });
  }

  it('un fallo persistente tras reintentar sigue visible y no entra en bucle', async () => {
    const { http, ready } = setup(HomePage);
    await ready;
    const f = TestBed.createComponent(HomePage);
    f.detectChanges();
    answerSideRequests(http);
    http.expectOne((r) => r.url === RUNS).flush(reply503, { status: 503, statusText: 'x' });
    await settle(f);
    const el = f.nativeElement as HTMLElement;
    (el.querySelector('[data-testid="analysis-retry"]') as HTMLButtonElement).click();
    http.expectOne((r) => r.url === RUNS).flush(reply503, { status: 503, statusText: 'x' });
    await settle(f);
    expect(http.match((r) => r.url === RUNS).length).toBe(0);
    expect(el.querySelector('[data-testid="analysis-error"]')).not.toBeNull();
  });

  it('varios consumidores comparten una sola carga', async () => {
    const { http, ready } = setup(ForecastsPage, '/pronosticos');
    await ready;
    const f = TestBed.createComponent(ForecastsPage);
    f.detectChanges();
    answerSideRequests(http);
    const reqs = http.match((r) => r.url === RUNS);
    expect(reqs.length, 'barra + pantalla = una sola petición a /runs').toBe(1);
    reqs[0].flush(page([runSummary]));
    await settle(f);
    answerSideRequests(http);
    expect(http.match((r) => r.url === RUNS).length).toBe(0);
  });

  it('estados distintos: lista vacía, análisis inexistente y página incompleta (sin afirmar «no existe»)', async () => {
    const { http, ready } = setup(HomePage, '/inicio?run=run-que-no-existe');
    await ready;
    const f = TestBed.createComponent(HomePage);
    f.detectChanges();
    answerSideRequests(http);
    http.expectOne((r) => r.url === RUNS).flush(page([runSummary], { has_more: true, total: 60 }));
    await settle(f);
    const el = f.nativeElement as HTMLElement;
    expect(el.querySelector('[data-testid="analysis-error"]')).toBeNull();
    const store = TestBed.inject(RunsStore);
    expect(store.resolve('run-que-no-existe')).toBeNull();
    expect(store.hasMore()).toBe(true);
  });

  it('la caché se invalida al cambiar la identidad de la sesión', async () => {
    const { http } = setup(HomePage);
    const store = TestBed.inject(RunsStore);
    store.ensure();
    http.expectOne((r) => r.url === RUNS).flush(page([runSummary]));
    store.ensure();
    expect(http.match((r) => r.url === RUNS).length, 'mismo usuario: sin nueva lectura').toBe(0);
    TestBed.inject(AuthService).session.set({ ...session, username: 'otra_persona' });
    store.ensure();
    expect(http.match((r) => r.url === RUNS).length, 'otro usuario: nueva lectura').toBe(1);
  });
});
