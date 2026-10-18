// Pruebas T10 (sin backend real): importaciones, trabajos, generación de corridas, corrida elegida y rótulos de comparación.
import { Type } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting, TestRequest } from '@angular/common/http/testing';
import { Router, provideRouter } from '@angular/router';
import { apiInterceptor } from '../core/http.interceptor';
import { demoInterceptor } from '../core/demo';
import { AuthService } from '../core/auth.service';
import { Role, PublicJob } from '../core/models';
import { ImportsPage, earlyWarning } from './imports.page';
import { RunsPage } from './runs.page';
import { CreateRunPage } from './create-run.page';
import { ForecastsPage } from './forecasts.page';
import { RecommendationsPage } from './recommendations.page';
import { ComparisonPage } from './comparison.page';
import { summarize } from '../core/jobs';
import { forecast, page, recoOk, runSummary } from '../testing/fixtures';
import { realBacktest, realBacktestList, realRunSummary } from '../testing/real-shapes';
import { visibleText } from '../testing/mount';

interface M<T> { f: ComponentFixture<T>; http: HttpTestingController; el: HTMLElement }

let lastHttp: HttpTestingController | undefined;

async function mountAs<T>(cmp: Type<T>, role: Role | null, url = '/x'): Promise<M<T>> {
  TestBed.configureTestingModule({
    imports: [cmp],
    providers: [
      provideHttpClient(withInterceptors([apiInterceptor, demoInterceptor])), provideHttpClientTesting(),
      provideRouter([{ path: '**', children: [] }]),
    ],
  });
  const auth = TestBed.inject(AuthService);
  if (role) auth.session.set({ username: 'u', role, csrf_token: 'csrf-' + role, expires_at: '2026-10-17T23:00:00Z' });
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

function job(extra: Partial<PublicJob>): PublicJob {
  return { job_id: 'job-1', type: 'import_excel', status: 'queued', ...extra };
}
function pickFile(el: HTMLElement, name: string, size = 100) {
  const input = q(el, 'file-input') as HTMLInputElement;
  const file = new File([new Uint8Array(size)], name);
  Object.defineProperty(input, 'files', { value: [file], configurable: true });
  input.dispatchEvent(new Event('change'));
  return file;
}

afterEach(() => { vi.useRealTimers(); lastHttp?.verify(); lastHttp = undefined; });

describe('Importaciones: permisos de la interfaz', () => {
  it('el administrador ve el selector y los trabajos recientes; consulta /imports y /jobs', async () => {
    const m = await mountAs(ImportsPage, 'admin');
    await ok(m.f, one(m.http, '/api/v1/imports'), page([]));
    const jobs = one(m.http, '/api/v1/jobs');
    expect(jobs.request.params.get('type')).toBe('import_excel');
    await ok(m.f, jobs, page([]));
    expect(q(m.el, 'file-input')).toBeTruthy();
    expect(q(m.el, 'upload-btn')).toBeTruthy();
    expect(q(m.el, 'jobs-empty')).toBeTruthy();
    expect(q(m.el, 'readonly-note')).toBeNull();
  });

  it('el lector no ve selector, botón ni trabajos, y no consulta /jobs', async () => {
    const m = await mountAs(ImportsPage, 'lector');
    await ok(m.f, one(m.http, '/api/v1/imports'), page([]));
    expect(q(m.el, 'file-input')).toBeNull();
    expect(q(m.el, 'upload-section')).toBeNull();
    expect(q(m.el, 'readonly-note')).toBeTruthy();
    m.http.expectNone((r) => r.url === '/api/v1/jobs');
  });
});

describe('Importaciones: validación ligera en el cliente', () => {
  it('earlyWarning avisa extensión, tamaño y vacío; un .xlsx de tamaño normal no avisa', () => {
    expect(earlyWarning({ name: 'a.csv', size: 10 })).toContain('.xlsx');
    expect(earlyWarning({ name: 'a.xlsx', size: 25 * 1024 * 1024 + 1 })).toContain('25 MiB');
    expect(earlyWarning({ name: 'a.xlsx', size: 25 * 1024 * 1024 })).toBeNull();
    expect(earlyWarning({ name: 'A.XLSX', size: 5 })).toBeNull();
    expect(earlyWarning({ name: 'a.xlsx', size: 0 })).toContain('vacío');
  });

  it('un archivo con extensión incorrecta muestra aviso y deshabilita el envío (no hay POST)', async () => {
    const m = await mountAs(ImportsPage, 'admin');
    await ok(m.f, one(m.http, '/api/v1/imports'), page([]));
    await ok(m.f, one(m.http, '/api/v1/jobs'), page([]));
    pickFile(m.el, 'ventas.txt');
    await settle(m.f);
    expect(txt(m.el, 'file-warning')).toContain('.xlsx');
    expect((q(m.el, 'upload-btn') as HTMLButtonElement).disabled).toBe(true);
    m.http.expectNone((r) => r.method === 'POST');
  });
});

describe('Importaciones: envío multipart y seguimiento del trabajo', () => {
  it('POST /imports con FormData, X-CSRF-Token y sin Content-Type manual; sigue el trabajo cada 2 s y se detiene al completar', async () => {
    vi.useFakeTimers();
    const m = await mountAs(ImportsPage, 'admin');
    await ok(m.f, one(m.http, '/api/v1/imports'), page([]));
    await ok(m.f, one(m.http, '/api/v1/jobs'), page([]));
    const file = pickFile(m.el, 'ventas_julio.xlsx');
    await settle(m.f);
    (q(m.el, 'upload-btn') as HTMLButtonElement).click();

    const post = m.http.expectOne((r) => r.method === 'POST' && r.url === '/api/v1/imports');
    expect(post.request.body instanceof FormData).toBe(true);
    const sent = (post.request.body as FormData).get('file') as File;
    expect(sent.name).toBe(file.name);
    expect(post.request.headers.get('X-CSRF-Token')).toBe('csrf-admin');
    expect(post.request.headers.has('Content-Type')).toBe(false);
    expect(post.request.withCredentials).toBe(true);
    post.flush({ job_id: 'job-1', status: 'queued', upload: { month: '2026-07' }, reused: false }, { status: 202, statusText: 'Accepted' });
    await settle(m.f);

    // primera consulta inmediata: en ejecución con etapa y conteos reales
    await ok(m.f, one(m.http, '/api/v1/jobs/job-1'), job({ status: 'running', stage: 'importing', progress: { filas_leidas: 1200, ventas: 1100 } }));
    expect(txt(m.el, 'job-stage')).toContain('Importando');
    expect(txt(m.el, 'job-progress')).toContain('Filas leídas: 1200');
    expect(m.el.textContent).not.toMatch(/\d\s?%/);

    // sin nada pendiente antes de 2 s
    vi.advanceTimersByTime(1900);
    m.http.expectNone((r) => r.url === '/api/v1/jobs/job-1');
    vi.advanceTimersByTime(100);
    await ok(m.f, one(m.http, '/api/v1/jobs/job-1'), job({
      status: 'completed', result: { outcome: 'importado', import_id: 'imp-9', filas_leidas: 1500, ventas: 1400, notas_credito: 60, rechazadas: 30, en_conflicto: 2, rechazos_por_motivo: { FECHA_INVALIDA: 30 } },
    }));
    expect(txt(m.el, 'job-outcome')).toContain('Importado');
    const counts = txt(m.el, 'job-counts');
    for (const part of ['Filas leídas: 1500', 'Ventas: 1400', 'Notas de crédito: 60', 'Rechazadas: 30', 'En conflicto: 2']) expect(counts).toContain(part);
    expect(txt(m.el, 'job-motives')).toContain('FECHA_INVALIDA');
    expect(q(m.el, 'job-import-link')).toBeTruthy();
    // al terminar se recarga la lista de importaciones
    await ok(m.f, one(m.http, '/api/v1/imports'), page([]));

    // parada al estado final
    vi.advanceTimersByTime(10000);
    m.http.expectNone((r) => r.url.startsWith('/api/v1/jobs/'));

    // enlace al detalle de la importación
    (q(m.el, 'job-import-link') as HTMLButtonElement).click();
    await ok(m.f, one(m.http, '/api/v1/imports/imp-9'), { import_id: 'imp-9', archivo: 'x.xlsx', mes: '2026-07', estado: 'aprobada' });
    expect(txt(m.el, 'import-detail-title')).toContain('imp-9');
  });

  it('archivo repetido (reused) avisa que se sigue el mismo trabajo; «sin cambios» se muestra legible', async () => {
    vi.useFakeTimers();
    const m = await mountAs(ImportsPage, 'admin');
    await ok(m.f, one(m.http, '/api/v1/imports'), page([]));
    await ok(m.f, one(m.http, '/api/v1/jobs'), page([]));
    pickFile(m.el, 'ventas_julio.xlsx');
    await settle(m.f);
    (q(m.el, 'upload-btn') as HTMLButtonElement).click();
    m.http.expectOne((r) => r.method === 'POST').flush({ job_id: 'job-1', status: 'completed', reused: true }, { status: 202, statusText: 'Accepted' });
    await settle(m.f);
    expect(q(m.el, 'reused-note')).toBeTruthy();
    await ok(m.f, one(m.http, '/api/v1/jobs/job-1'), job({ status: 'completed', result: { outcome: 'sin_cambios', import_id: 'imp-1' } }));
    expect(txt(m.el, 'job-outcome')).toContain('Sin cambios (archivo ya cargado)');
    await ok(m.f, one(m.http, '/api/v1/imports'), page([]));
  });

  it.each([
    [413, 'tamaño'], [415, 'no es un .xlsx'], [422, 'contenido'],
  ])('error %i del servidor al subir muestra un mensaje en español', async (status, frag) => {
    const m = await mountAs(ImportsPage, 'admin');
    await ok(m.f, one(m.http, '/api/v1/imports'), page([]));
    await ok(m.f, one(m.http, '/api/v1/jobs'), page([]));
    pickFile(m.el, 'a.xlsx');
    await settle(m.f);
    (q(m.el, 'upload-btn') as HTMLButtonElement).click();
    m.http.expectOne((r) => r.method === 'POST').flush({ error: { code: 'ENTRADA_INVALIDA', message: 'Encabezados incorrectos' } }, { status, statusText: 'x' });
    await settle(m.f);
    expect(txt(m.el, 'upload-error')).toContain(frag);
    expect(q(m.el, 'job-status')).toBeNull();
  });
});

describe('Trabajos: mensajes por código de error', () => {
  const failed = (code: string, message = 'texto del servidor'): PublicJob => job({ status: 'failed', error: { code, message, retryable: false } });

  it('FECHAS_FUERA_DE_ALCANCE: rechazado, fechas fuera de marzo a julio', () => {
    const s = summarize(failed('FECHAS_FUERA_DE_ALCANCE'));
    expect(s.title).toBe('Rechazado');
    expect(s.detail).toContain('fechas fuera del alcance');
  });
  it('MES_CON_FUENTE_APROBADA: rechazado, remite a la remediación documentada', () => {
    const s = summarize(failed('MES_CON_FUENTE_APROBADA'));
    expect(s.title).toBe('Rechazado');
    expect(s.detail).toContain('fuente aprobada');
    expect(s.detail).toContain('remediación documentado');
  });
  it('archivo inválido, WORKER_PERDIDO y código desconocido (con el mensaje saneado del servidor)', () => {
    expect(summarize(failed('ARCHIVO_INVALIDO')).detail).toContain('Excel');
    expect(summarize(failed('WORKER_PERDIDO')).detail).toContain('interrumpió');
    const u = summarize(failed('OTRO_CODIGO', 'detalle saneado'));
    expect(u.title).toBe('No se pudo completar');
    // el texto principal no repite el código ni el párrafo del servidor: esos van en «Detalles técnicos del trabajo»
    expect(u.detail).not.toContain('OTRO_CODIGO');
    expect(u.detail).not.toContain('detalle saneado');
    expect(u.detail).toContain('avisa al administrador');
  });

  it('el código y el mensaje originales del servidor quedan en los detalles técnicos plegados del trabajo', async () => {
    const m = await mountAs(ImportsPage, 'admin');
    await ok(m.f, one(m.http, '/api/v1/imports'), page([]));
    await ok(m.f, one(m.http, '/api/v1/jobs'), page([failed('OTRO_CODIGO', 'detalle saneado')]));
    const tech = q(m.el, 'job-tech-job-1') as HTMLDetailsElement;
    expect(tech.open).toBe(false);
    expect(tech.textContent).toContain('OTRO_CODIGO');
    expect(tech.textContent).toContain('detalle saneado');
    expect(visibleText(m.el)).not.toContain('OTRO_CODIGO');
  });

  it('un trabajo fallido se pinta en pantalla con su motivo y sin enlace de corrida', async () => {
    const m = await mountAs(ImportsPage, 'admin');
    await ok(m.f, one(m.http, '/api/v1/imports'), page([]));
    await ok(m.f, one(m.http, '/api/v1/jobs'), page([failed('MES_CON_FUENTE_APROBADA')]));
    expect(txt(m.el, 'job-status')).toBe('No se pudo completar');
    expect(txt(m.el, 'job-outcome')).toContain('Rechazado');
    expect(txt(m.el, 'job-outcome')).toContain('remediación');
  });

  it('error al leer /jobs: mensaje de error, sin datos de relleno ni modo demostración', async () => {
    const m = await mountAs(ImportsPage, 'admin');
    await ok(m.f, one(m.http, '/api/v1/imports'), page([]));
    one(m.http, '/api/v1/jobs').flush({}, { status: 503, statusText: 'x' });
    await settle(m.f);
    expect(txt(m.el, 'jobs-error')).toContain('Servicio no disponible');
    expect(m.el.textContent).not.toContain('DEMOSTRACIÓN');
  });
});

describe('Importaciones: reanudación al recargar', () => {
  it('muestra trabajos recientes y retoma el seguimiento de queued/running; no consulta los terminados; se detiene al salir', async () => {
    vi.useFakeTimers();
    const m = await mountAs(ImportsPage, 'admin');
    await ok(m.f, one(m.http, '/api/v1/imports'), page([]));
    const recent = [
      job({ job_id: 'run-1', status: 'running', stage: 'scanning' }),
      job({ job_id: 'old-1', status: 'completed', result: { outcome: 'importado', import_id: 'i1', filas_leidas: 5, ventas: 4, notas_credito: 1, rechazadas: 0, en_conflicto: 0 } }),
    ];
    await ok(m.f, one(m.http, '/api/v1/jobs'), page(recent));
    expect(m.el.querySelectorAll('[data-testid^="job-"][data-status]').length).toBe(2);
    // se reanuda de inmediato solo el trabajo en curso
    await ok(m.f, one(m.http, '/api/v1/jobs/run-1'), job({ job_id: 'run-1', status: 'running', stage: 'importing', progress: { filas_leidas: 10 } }));
    expect(m.el.textContent).toContain('Importando');
    m.http.expectNone((r) => r.url === '/api/v1/jobs/old-1');
    vi.advanceTimersByTime(2000);
    m.http.expectOne('/api/v1/jobs/run-1').flush(job({ job_id: 'run-1', status: 'running' }));
    // salir de la página: se detiene el seguimiento
    m.f.destroy();
    vi.advanceTimersByTime(10000);
    m.http.expectNone((r) => r.url.startsWith('/api/v1/jobs/'));
  });
});

describe('Crear análisis: generación (admin)', () => {
  const options = { origin_min: '2026-06-01', origin_max: '2026-07-10', origin_default: '2026-07-10', horizon_max: 21, methods: ['promedio_28'], development_policy: true };
  async function open() {
    const m = await mountAs(CreateRunPage, 'admin');
    await ok(m.f, one(m.http, '/api/v1/jobs'), page([]));
    await ok(m.f, one(m.http, '/api/v1/runs/options'), options);
    return m;
  }

  it('el lector ve «Solo el administrador puede crear análisis», sin controles ni consultas a /jobs, /runs/options o /runs', async () => {
    const m = await mountAs(CreateRunPage, 'lector');
    await settle(m.f);
    expect(txt(m.el, 'admin-only')).toContain('Solo el administrador puede crear análisis');
    expect(q(m.el, 'gen-section')).toBeNull();
    expect(q(m.el, 'origin')).toBeNull();
    expect(q(m.el, 'generate-btn')).toBeNull();
    m.http.expectNone((r) => r.url === '/api/v1/jobs' || r.url === '/api/v1/runs/options' || r.url === '/api/v1/runs');
  });

  it('explica qué hará el botón y publica el rango permitido por la API (sin ampliarlo)', async () => {
    const m = await open();
    const t = visibleText(m.el).replace(/\s+/g, ' ');
    expect(t).toContain('Crea un análisis nuevo con el promedio de los últimos 28 días para las fechas elegidas; no reentrena modelos');
    expect(txt(m.el, 'origin-range')).toContain('1 de junio de 2026');
    expect(txt(m.el, 'origin-range')).toContain('10 de julio de 2026');
    expect(txt(m.el, 'generate-btn')).toBe('Crear análisis');
    // consultar la pantalla no crea trabajos
    m.http.expectNone((r) => r.method === 'POST');
  });

  it('formulario: min/max de /runs/options, horizonte 21 y método promedio_28 fijos; POST con el origen elegido', async () => {
    vi.useFakeTimers();
    const m = await open();
    const input = q(m.el, 'origin') as HTMLInputElement;
    expect(input.min).toBe('2026-06-01');
    expect(input.max).toBe('2026-07-10');
    expect(input.value).toBe('2026-07-10');
    expect(txt(m.el, 'horizon')).toContain('21');
    expect(txt(m.el, 'gen-method')).toContain('promedio_28');
    input.value = '2026-06-30';
    input.dispatchEvent(new Event('input'));
    await settle(m.f);
    (q(m.el, 'generate-btn') as HTMLButtonElement).click();
    const post = m.http.expectOne((r) => r.method === 'POST' && r.url === '/api/v1/runs');
    expect(post.request.body).toEqual({ origin: '2026-06-30', horizon_days: 21, method: 'promedio_28' });
    expect(post.request.headers.get('X-CSRF-Token')).toBe('csrf-admin');
    post.flush({ job_id: 'g1', status: 'queued', origin: '2026-06-30', horizon_days: 21, method: 'promedio_28' }, { status: 202, statusText: 'Accepted' });
    await settle(m.f);
    await ok(m.f, one(m.http, '/api/v1/jobs/g1'), job({ job_id: 'g1', type: 'generate_run', status: 'running', stage: 'forecasting', progress: { skus_procesados: 40 } }));
    expect(txt(m.el, 'job-progress')).toContain('Productos procesados: 40');
    vi.advanceTimersByTime(2000);
    await ok(m.f, one(m.http, '/api/v1/jobs/g1'), job({ job_id: 'g1', type: 'generate_run', status: 'completed', result: { run_id: 'gen-20260630-abc' } }));
    const link = q(m.el, 'job-run-link') as HTMLAnchorElement;
    expect(link.getAttribute('href')).toContain('run=gen-20260630-abc');
    expect(link.getAttribute('href')).toContain('/pronosticos');
    expect(txt(m.el, 'job-status')).toBe('Terminado');
    // confirmación en palabras sencillas con «Ver previsión» hacia el análisis creado
    expect(txt(m.el, 'gen-done')).toContain('Listo: el análisis se creó');
    const view = q(m.el, 'gen-view') as HTMLAnchorElement;
    expect(view.textContent).toContain('Ver previsión');
    expect(view.getAttribute('href')).toContain('/pronosticos');
    expect(view.getAttribute('href')).toContain('run=gen-20260630-abc');
    // la lista compartida de análisis se vuelve a leer
    await ok(m.f, one(m.http, '/api/v1/runs'), page([realRunSummary]));
    vi.advanceTimersByTime(6000);
    m.http.expectNone((r) => r.url.startsWith('/api/v1/jobs/'));
  });

  it('un origen fuera de rango no se puede enviar (botón deshabilitado, aviso)', async () => {
    const m = await open();
    const input = q(m.el, 'origin') as HTMLInputElement;
    input.value = '2026-08-05';
    input.dispatchEvent(new Event('input'));
    await settle(m.f);
    expect((q(m.el, 'generate-btn') as HTMLButtonElement).disabled).toBe(true);
    expect(q(m.el, 'origin-warning')).toBeTruthy();
  });

  it('422 CORTE_FUERA_DE_RANGO se muestra legible, sin seguir ningún trabajo', async () => {
    const m = await open();
    (q(m.el, 'generate-btn') as HTMLButtonElement).click();
    m.http.expectOne((r) => r.method === 'POST' && r.url === '/api/v1/runs')
      .flush({ error: { code: 'CORTE_FUERA_DE_RANGO', message: 'fuera' } }, { status: 422, statusText: 'x' });
    await settle(m.f);
    const t = txt(m.el, 'gen-error');
    expect(t).toContain('fuera del rango permitido');
    expect(t).toContain('1 de junio de 2026');
    expect(t).toContain('10 de julio de 2026');
    m.http.expectNone((r) => r.url.startsWith('/api/v1/jobs/'));
  });

  it('Mis análisis distingue el ejemplo histórico y los análisis creados, y el lector no ve «Crear»', async () => {
    const m = await mountAs(RunsPage, 'lector');
    const gen = { ...realRunSummary, run_id: 'gen-20260710-aaaaaaaaaaaa', kind: 'generated_baseline', is_active: false, run_label: 'Corrida de desarrollo generada por la aplicación con origen 10/07/2026' };
    await ok(m.f, one(m.http, '/api/v1/runs'), page([realRunSummary, gen]));
    const kinds = Array.from(m.el.querySelectorAll('[data-testid="run-kind"]')).map((c) => c.textContent);
    expect(kinds).toEqual(['Ejemplo histórico', 'Creado en la aplicación']);
    expect(q(m.el, 'to-create')).toBeNull();
    m.http.expectNone((r) => r.url === '/api/v1/jobs' || r.url === '/api/v1/runs/options');
  });
});

describe('Corridas generadas: valores no disponibles', () => {
  const genRun = { ...runSummary, run_id: 'gen-1', kind: 'generated_baseline', is_active: false, origin: '2026-07-10', target_start: '2026-07-11', target_end: '2026-07-31', run_label: 'Corrida de desarrollo generada por la aplicación con origen 10/07/2026', age_days_at_view: 3 };

  it('observed/evaluable/rf null: «no disponible para esta corrida», nunca 0; sin columna RF; etiqueta de run_label y fechas', async () => {
    const m = await mountAs(ForecastsPage, 'lector', '/pronosticos?run=gen-1');
    await ok(m.f, one(m.http, '/api/v1/runs'), page([runSummary, genRun]));
    const fr = one(m.http, '/api/v1/forecasts');
    expect(fr.request.params.get('run_id')).toBe('gen-1');
    const item = { ...forecast, run_id: 'gen-1', observed: null, evaluable: null, pred: { promedio_28: 2.5, rf_categoria_distribuido: null, cero: 0 } };
    await ok(m.f, fr, page([item]));
    expect(txt(m.el, 'no-observed-note')).toContain('Aún no hay ventas registradas para comparar');
    (q(m.el, 'toggle-details') as HTMLButtonElement).click();
    await settle(m.f);
    expect(txt(m.el, 'observed')).toBe('no disponible para esta corrida');
    expect(txt(m.el, 'evaluable')).toBe('no disponible para esta corrida');
    const row = txt(m.el, 'forecast-table');
    expect(row).not.toContain('Modelo experimental');
    expect(m.el.querySelector('[data-testid="forecast-table"] tbody tr')!.querySelectorAll('td').length).toBe(9);
    expect(txt(m.el, 'analysis-name')).toBe('Análisis creado con ventas hasta el 10/07/2026');
    expect(txt(m.el, 'run-dates')).toContain('10/07/2026');
    expect(txt(m.el, 'run-dates')).toContain('11/07/2026 al 31/07/2026');
    expect(q(m.el, 'insufficient')).toBeNull();
    expect(txt(m.el, 'forecast-note')).toContain('no son cero');
  });

  it('si la corrida publica valores de RF, el comparador se muestra', async () => {
    const m = await mountAs(ForecastsPage, 'lector', '/pronosticos?run=gen-1');
    await ok(m.f, one(m.http, '/api/v1/runs'), page([genRun]));
    await ok(m.f, one(m.http, '/api/v1/forecasts'), page([{ ...forecast, observed: null, evaluable: null, pred: { promedio_28: 2, rf_categoria_distribuido: 1.5, cero: 0 } }]));
    (q(m.el, 'toggle-details') as HTMLButtonElement).click();
    await settle(m.f);
    expect(txt(m.el, 'forecast-table')).toContain('Modelo experimental');
    expect(m.el.querySelector('[data-testid="forecast-table"] tbody tr')!.textContent).toContain('1.5');
  });

  it('una fila histórica con observado 0 sigue mostrando 0 (el cero real no se confunde con «no disponible»)', async () => {
    const m = await mountAs(ForecastsPage, 'lector');
    await ok(m.f, one(m.http, '/api/v1/runs'), page([runSummary]));
    await ok(m.f, one(m.http, '/api/v1/forecasts'), page([{ ...forecast, observed: 0, evaluable: true }]));
    expect(txt(m.el, 'observed')).toBe('0');
    (q(m.el, 'toggle-details') as HTMLButtonElement).click();
    await settle(m.f);
    expect(txt(m.el, 'evaluable')).toBe('Sí');
  });
});

describe('Corrida elegida: consistencia entre pantallas', () => {
  it('Pronósticos: sin parámetro usa la activa; el selector cambia la corrida, recarga desde la página 1 y actualiza la URL', async () => {
    const m = await mountAs(ForecastsPage, 'lector');
    const gen = { ...runSummary, run_id: 'gen-1', kind: 'generated_baseline', is_active: false, run_label: 'Generada 10/07' };
    await ok(m.f, one(m.http, '/api/v1/runs'), page([runSummary, gen]));
    const first = one(m.http, '/api/v1/forecasts');
    expect(first.request.params.has('run_id')).toBe(false);
    await ok(m.f, first, page([forecast]));
    const sel = q(m.el, 'run-select') as HTMLSelectElement;
    expect(sel.value).toBe('run-test-1');
    sel.value = 'gen-1';
    sel.dispatchEvent(new Event('change'));
    const again = one(m.http, '/api/v1/forecasts');
    expect(again.request.params.get('run_id')).toBe('gen-1');
    expect(again.request.params.get('page')).toBe('1');
    await ok(m.f, again, page([forecast]));
    expect(TestBed.inject(Router).url).toContain('run=gen-1');
  });

  it('Recomendaciones usa la MISMA corrida de la URL: lista y detalle piden run_id; origen y fechas objetivo visibles', async () => {
    const m = await mountAs(RecommendationsPage, 'lector', '/recomendaciones?run=gen-1');
    await ok(m.f, one(m.http, '/api/v1/runs'), page([runSummary, { ...runSummary, run_id: 'gen-1', kind: 'generated_baseline', is_active: false, origin: '2026-07-10' }]));
    const list = one(m.http, '/api/v1/recommendations');
    expect(list.request.params.get('run_id')).toBe('gen-1');
    await ok(m.f, list, { ...page([{ ...recoOk, run_id: 'gen-1' }]), run: { ...runSummary, run_id: 'gen-1', run_label: 'Generada 10/07', age_days_at_view: 2 } });
    const head = txt(m.el, 'reco-header');
    expect(head).toContain('10/07/2026');
    expect(head).toContain('11/07/2026 al 24/07/2026');
    expect(txt(m.el, 'analysis-name')).toBe('Análisis creado con ventas hasta el 10/07/2026');
    expect(txt(m.el, 'sim-notice')).toContain('Inventario simulado con supuestos; no corresponde al inventario real de la empresa');
    (m.el.querySelector('[data-testid="reco-table"] tbody button') as HTMLButtonElement).click();
    const d = one(m.http, '/api/v1/recommendations/SKU-T1');
    expect(d.request.params.get('run_id')).toBe('gen-1');
    await ok(m.f, d, { ...recoOk, run_id: 'gen-1' });
    expect(m.el.querySelectorAll('[data-testid="calc-steps"] li').length).toBe(9);
  });

  it('Comparación pide el backtest de la corrida elegida; sin backtest muestra «sin backtest» y enlaza al histórico T07', async () => {
    const m = await mountAs(ComparisonPage, 'lector', '/comparacion?run=gen-1');
    await ok(m.f, one(m.http, '/api/v1/runs'), page([realRunSummary, { ...runSummary, run_id: 'gen-1', kind: 'generated_baseline', is_active: false }]));
    const bt = one(m.http, '/api/v1/backtests');
    expect(bt.request.params.get('run_id')).toBe('gen-1');
    await ok(m.f, bt, page([]));
    const hist = m.http.expectOne((r) => r.url === '/api/v1/backtests' && !r.params.has('run_id'));
    await ok(m.f, hist, realBacktestList);
    expect(txt(m.el, 'no-backtest')).toContain('se creó en la aplicación y todavía no tiene una comparación con ventas registradas');
    expect(m.el.textContent).toContain('Este análisis no tiene una comparación con ventas registradas');
    expect(q(m.el, 'to-analyses')!.getAttribute('href')).toContain('/corridas');
    const link = q(m.el, 'hist-link') as HTMLAnchorElement;
    expect(link.getAttribute('href')).toContain('run=hist-20260710-52b01cd999dd');
  });
});

describe('Comparación: origen, fechas objetivo y período de evaluación', () => {
  it('rotula los tres por separado y ya no dice «hasta el 10/07/2026»', async () => {
    const m = await mountAs(ComparisonPage, 'lector');
    await ok(m.f, one(m.http, '/api/v1/runs'), page([realRunSummary]));
    await ok(m.f, one(m.http, '/api/v1/backtests'), realBacktestList);
    await ok(m.f, one(m.http, `/api/v1/backtests/${realBacktest.backtest_id}`), realBacktest);
    expect(txt(m.el, 'p-origin')).toBe('10/07/2026');
    expect(txt(m.el, 'p-target')).toBe('11/07/2026 al 31/07/2026');
    expect(txt(m.el, 'p-eval')).toBe('01/06/2026 al 31/07/2026');
    const t = m.el.textContent!;        // los períodos exactos están en el detalle académico
    // el origen se rotula «Ventas utilizadas hasta»; no se presenta como el fin del período de evaluación
    expect(t).not.toMatch(/evaluaci[óo]n[^.]{0,40}hasta el 10\/07\/2026/);
    expect(t).toContain('no es el fin de la evaluación');
    expect(txt(m.el, 'periods')).toContain('Período de evaluación de la comparación y de la simulación');
    expect(txt(m.el, 'periods')).toContain('Ventas utilizadas hasta');
  });
});
