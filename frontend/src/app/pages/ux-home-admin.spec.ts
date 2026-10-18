// UX01 (agente A): Inicio, Ayuda, Mis análisis, Cargar datos / Datos cargados, Estado del sistema y Acceso.
// Fixtures de FORMA con números de prueba (testing/): no son resultados reales.
import { Type } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting, TestRequest } from '@angular/common/http/testing';
import { Router, provideRouter } from '@angular/router';
import { apiInterceptor } from '../core/http.interceptor';
import { demoInterceptor } from '../core/demo';
import { AuthService } from '../core/auth.service';
import { Role } from '../core/models';
import { GLOSSARY } from '../core/ux-text';
import { HomePage } from './home.page';
import { HelpPage } from './help.page';
import { RunsPage } from './runs.page';
import { ImportsPage } from './imports.page';
import { SystemPage } from './system.page';
import { LoginPage } from './login.page';
import { CreateRunPage } from './create-run.page';
import { page } from '../testing/fixtures';
import { realRunSummary } from '../testing/real-shapes';
import { FINAL_ID, finalRun, genRun, histRun } from '../testing/final-shapes';
import { visibleText } from '../testing/mount';

interface M<T> { f: ComponentFixture<T>; http: HttpTestingController; el: HTMLElement; router: Router }
let lastHttp: HttpTestingController | undefined;

async function mountAs<T>(cmp: Type<T>, role: Role | null, url = '/x', user = 'u'): Promise<M<T>> {
  TestBed.configureTestingModule({
    imports: [cmp],
    providers: [
      provideHttpClient(withInterceptors([apiInterceptor, demoInterceptor])), provideHttpClientTesting(),
      provideRouter([{ path: '**', children: [] }]),
    ],
  });
  if (role) TestBed.inject(AuthService).session.set({ username: user, role, csrf_token: 'csrf-' + role, expires_at: '2026-10-17T23:00:00Z' });
  const router = TestBed.inject(Router);
  await router.navigateByUrl(url);
  const http = TestBed.inject(HttpTestingController);
  lastHttp = http;
  const f = TestBed.createComponent(cmp);
  f.detectChanges();
  return { f, http, el: f.nativeElement as HTMLElement, router };
}
const one = (http: HttpTestingController, path: string): TestRequest => http.expectOne((r) => r.url === path);
async function settle(f: ComponentFixture<unknown>) { f.detectChanges(); await f.whenStable(); f.detectChanges(); }
async function ok(f: ComponentFixture<unknown>, r: TestRequest, body: unknown) { r.flush(body as object); await settle(f); }
const q = (el: HTMLElement, id: string) => el.querySelector(`[data-testid="${id}"]`) as HTMLElement | null;
const txt = (el: HTMLElement, id: string) => (q(el, id)?.textContent ?? '').replace(/\s+/g, ' ').trim();
const recoPage = (total: number, extra: object = {}) => ({ ...page([]), total, ...extra });

beforeEach(() => { try { localStorage.clear(); } catch { /* sin almacenamiento */ } });
afterEach(() => { vi.restoreAllMocks(); lastHttp?.verify(); lastHttp = undefined; });

/** Monta Inicio y responde a /runs y a la cifra de reposición. */
async function openHome(role: Role, url = '/inicio', total = 640, runs = [histRun, finalRun], user = 'u') {
  const m = await mountAs(HomePage, role, url, user);
  await ok(m.f, one(m.http, '/api/v1/runs'), page(runs));
  const reco = one(m.http, '/api/v1/recommendations');
  await ok(m.f, reco, recoPage(total));
  return { m, reco };
}

describe('Inicio: orientación', () => {
  it('título, explicación y tres tarjetas de tarea con un botón real y una sola acción principal', async () => {
    const { m } = await openHome('lector');
    expect(m.el.querySelectorAll('h1').length).toBe(1);
    expect(txt(m.el, 'page-title')).toBe('Explora las ventas previstas y una simulación de reposición');
    expect(txt(m.el, 'page-lead')).toBe('Consulta cuánto se estimó vender y cómo se calculó una sugerencia de reposición con los datos del ejemplo.');
    expect(m.el.querySelectorAll('[data-testid^="task-"]').length).toBe(3);
    const go = (id: string) => q(m.el, id) as HTMLAnchorElement;
    expect(go('go-forecasts').textContent).toContain('Ver previsión');
    expect(go('go-forecasts').getAttribute('href')).toContain('/pronosticos');
    expect(go('go-reco').textContent).toContain('Explorar reposición simulada');
    expect(go('go-reco').getAttribute('href')).toContain('/recomendaciones');
    expect(go('go-runs').textContent).toContain('Ver mis análisis');
    expect(go('go-runs').getAttribute('href')).toContain('/corridas');
    // una única acción principal visual en las tareas
    expect(m.el.querySelectorAll('[data-testid="home-tasks"] .btn:not(.secondary)').length).toBe(1);
    // el lector no ve administración
    expect(q(m.el, 'home-admin')).toBeNull();
  });

  it('las tarjetas conservan el análisis elegido (run) y la barra muestra su nombre y fechas', async () => {
    const { m, reco } = await openHome('lector', '/inicio?run=' + FINAL_ID);
    for (const id of ['go-forecasts', 'go-reco', 'go-runs']) {
      expect((q(m.el, id) as HTMLAnchorElement).getAttribute('href')).toContain('run=' + FINAL_ID);
    }
    expect(reco.request.params.get('run_id')).toBe(FINAL_ID);
    expect(txt(m.el, 'analysis-name')).toBe('Evaluación de agosto');
    expect(txt(m.el, 'analysis-used')).toContain('31/07/2026');
  });

  it('la cifra es el total del SERVIDOR (page_size=1), con universo, filtro y aviso de simulación; nunca la suma de la página', async () => {
    const m = await mountAs(HomePage, 'lector');
    await ok(m.f, one(m.http, '/api/v1/runs'), page([histRun]));
    const reco = one(m.http, '/api/v1/recommendations');
    expect(reco.request.params.get('only_orders')).toBe('true');
    expect(reco.request.params.get('page_size')).toBe('1');
    expect(reco.request.params.get('page')).toBe('1');
    await ok(m.f, reco, { ...page([{ order_qty: 999 }]), total: 640, has_more: true });
    expect(txt(m.el, 'home-figure')).toBe('640');
    expect(txt(m.el, 'home-figure-box')).toContain('productos con sugerencia de reposición en el ejemplo');
    const ctx = txt(m.el, 'home-figure-context');
    expect(ctx).toContain('Ejemplo de julio');
    expect(ctx).toContain('ventas utilizadas hasta el 10 de julio de 2026');
    expect(ctx).toContain('inventario simulado');
    expect(m.el.querySelector('table')).toBeNull();
  });

  it('en la evaluación no hay pedidos: no se muestra cifra y se explica', async () => {
    const m = await mountAs(HomePage, 'lector', '/inicio?run=' + FINAL_ID);
    await ok(m.f, one(m.http, '/api/v1/runs'), page([histRun, finalRun]));
    await ok(m.f, one(m.http, '/api/v1/recommendations'), recoPage(0, { unavailable_reason: 'La evaluación final no tiene recomendaciones', see_run: 'x' }));
    expect(q(m.el, 'home-figure')).toBeNull();
    expect(txt(m.el, 'home-no-orders')).toContain('no genera pedidos');
  });

  it('si la cifra falla se avisa con reintento y no se inventa ningún valor', async () => {
    const m = await mountAs(HomePage, 'lector');
    await ok(m.f, one(m.http, '/api/v1/runs'), page([histRun]));
    one(m.http, '/api/v1/recommendations').flush({}, { status: 503, statusText: 'x' });
    await settle(m.f);
    expect(q(m.el, 'home-figure')).toBeNull();
    expect(txt(m.el, 'home-figure-error')).toContain('No se pudo consultar la cifra');
    (q(m.el, 'home-figure-error')!.querySelector('button') as HTMLButtonElement).click();
    await ok(m.f, one(m.http, '/api/v1/recommendations'), recoPage(7));
    expect(txt(m.el, 'home-figure')).toBe('7');
  });

  it('el contenido visible no muestra identificadores ni tablas de calidad; el administrador ve sus accesos', async () => {
    const { m } = await openHome('admin');
    const t = visibleText(m.el);
    expect(t).not.toContain(histRun.run_id);
    expect(t).not.toMatch(/run_id|SYNTHETIC|T07|T12/);
    expect(m.el.querySelector('table')).toBeNull();
    expect((q(m.el, 'go-imports') as HTMLAnchorElement).getAttribute('href')).toContain('/cargas');
    expect((q(m.el, 'go-create') as HTMLAnchorElement).getAttribute('href')).toContain('/crear-analisis');
    m.http.expectNone((r) => r.method === 'POST');
  });
});

describe('Inicio: «Cómo empezar» cerrable y recordado', () => {
  it('muestra tres pasos, se cierra, se recuerda por usuario y vuelve desde Ayuda', async () => {
    const first = await openHome('lector', '/inicio', 5, [histRun], 'ana');
    expect(first.m.el.querySelectorAll('[data-testid="onboarding"] ol li').length).toBe(3);
    (q(first.m.el, 'onboarding-close') as HTMLButtonElement).click();
    await settle(first.m.f);
    expect(q(first.m.el, 'onboarding')).toBeNull();
    // las tarjetas y los análisis siguen disponibles: el cierre no oculta funciones
    expect(q(first.m.el, 'go-forecasts')).toBeTruthy();
    first.m.f.destroy();
    lastHttp?.verify();
    TestBed.resetTestingModule();

    // mismo usuario, otra visita: sigue cerrado
    const again = await openHome('lector', '/inicio', 5, [histRun], 'ana');
    expect(q(again.m.el, 'onboarding')).toBeNull();
    again.m.f.destroy();
    lastHttp?.verify();
    TestBed.resetTestingModule();

    // otro usuario del mismo navegador: lo ve de nuevo
    const other = await openHome('lector', '/inicio', 5, [histRun], 'beto');
    expect(q(other.m.el, 'onboarding')).toBeTruthy();
    other.m.f.destroy();
    lastHttp?.verify();
    TestBed.resetTestingModule();

    // Ayuda: siempre muestra los pasos y permite volver a mostrarlos en Inicio
    const help = await mountAs(HelpPage, 'lector', '/ayuda', 'ana');
    expect(help.el.querySelectorAll('[data-testid="help-steps"] ol li').length).toBe(3);
    (q(help.el, 'onboarding-reset') as HTMLButtonElement).click();
    await settle(help.f);
    expect(q(help.el, 'onboarding-reset-done')).toBeTruthy();
    help.f.destroy();
    TestBed.resetTestingModule();
    const back = await openHome('lector', '/inicio', 5, [histRun], 'ana');
    expect(q(back.m.el, 'onboarding')).toBeTruthy();
  });

  it('si el almacenamiento del navegador falla, la ayuda se muestra igual y cerrar no rompe la pantalla', async () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('bloqueado'); });
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('bloqueado'); });
    const { m } = await openHome('lector');
    expect(q(m.el, 'onboarding')).toBeTruthy();
    (q(m.el, 'onboarding-close') as HTMLButtonElement).click();
    await settle(m.f);
    expect(q(m.el, 'onboarding')).toBeNull();
  });
});

describe('Ayuda', () => {
  it('primeros pasos, glosario completo, límites de la aplicación y lectura del WAPE', async () => {
    const m = await mountAs(HelpPage, 'lector');
    expect(m.el.querySelectorAll('h1').length).toBe(1);
    expect(m.el.querySelectorAll('[data-testid="help-glossary"] dt').length).toBe(GLOSSARY.length);
    const limits = txt(m.el, 'help-limits');
    expect(limits).toContain('No es tu inventario real');
    expect(limits).toContain('No ejecuta compras');
    expect(limits).toContain('No pronostica las ventas de hoy');
    expect(txt(m.el, 'help-wape')).toContain('no significa 78 % de acierto');
    expect(txt(m.el, 'help-glossary')).toContain('SKU');
    m.http.expectNone(() => true);
  });
});

describe('Mis análisis', () => {
  const OLD = { ...realRunSummary, run_id: 'hist-old', is_active: false, status: 'superseded', quality_issue: { superseded_by: realRunSummary.run_id, reason: 'Error de redondeo en el objetivo' } };
  const cardIds = (el: HTMLElement) => Array.from(el.querySelectorAll('[data-testid^="run-card-"]')).map((c) => c.getAttribute('data-testid')!.replace('run-card-', ''));

  it('lista el ejemplo predeterminado, la evaluación y un análisis creado, con propósito y acciones por tipo', async () => {
    const m = await mountAs(RunsPage, 'lector');
    await ok(m.f, one(m.http, '/api/v1/runs'), page([finalRun, genRun, histRun]));
    expect(m.el.querySelectorAll('h1').length).toBe(1);
    expect(cardIds(m.el)).toEqual([histRun.run_id, FINAL_ID, genRun.run_id]);
    expect(txt(m.el, 'run-card-' + histRun.run_id)).toContain('En uso por defecto');
    expect(txt(m.el, 'run-card-' + FINAL_ID)).toContain('Permite comparar estimaciones con ventas registradas; no genera pedidos');
    expect(txt(m.el, 'run-card-' + FINAL_ID)).toContain('Evaluación');
    expect(q(m.el, 'run-card-' + FINAL_ID)!.querySelector('[data-testid="to-reco"]')).toBeNull();
    expect(q(m.el, 'run-card-' + genRun.run_id)!.querySelector('[data-testid="to-compare"]')).toBeTruthy();
    // una sola petición a /runs (lista compartida) y ningún trabajo
    m.http.expectNone((r) => r.url === '/api/v1/jobs' || r.url.startsWith('/api/v1/runs/'));
    // el identificador técnico no aparece en el contenido principal
    expect(visibleText(m.el)).not.toContain(FINAL_ID);
  });

  it('elegir un análisis navega con ?run=<id>; el elegido se rotula distinto de «En uso por defecto»', async () => {
    const m = await mountAs(RunsPage, 'lector');
    await ok(m.f, one(m.http, '/api/v1/runs'), page([histRun, genRun]));
    expect(q(q(m.el, 'run-card-' + histRun.run_id)!, 'run-consulting')).toBeTruthy();   // sin elección: el predeterminado
    expect(q(q(m.el, 'run-card-' + genRun.run_id)!, 'run-consulting')).toBeNull();
    (q(q(m.el, 'run-card-' + genRun.run_id)!, 'choose') as HTMLButtonElement).click();
    await settle(m.f);
    expect(m.router.url).toContain('run=' + genRun.run_id);
    const gen = q(m.el, 'run-card-' + genRun.run_id)!;
    expect(txt(gen, 'run-status')).toBe('Seleccionado para consultar');
    expect(q(gen, 'run-consulting')).toBeTruthy();
    expect(txt(q(m.el, 'run-card-' + histRun.run_id)!, 'run-status')).toBe('En uso por defecto');
    expect(q(q(m.el, 'run-card-' + histRun.run_id)!, 'run-consulting')).toBeNull();
    // enlaces a otras pantallas conservan el análisis elegido
    expect((q(gen, 'to-forecasts') as HTMLAnchorElement).getAttribute('href')).toContain('run=' + genRun.run_id);
  });

  it('las versiones reemplazadas solo están en «Ver versiones anteriores» (plegado) y llevan el aviso y el enlace a la corregida', async () => {
    const m = await mountAs(RunsPage, 'lector');
    await ok(m.f, one(m.http, '/api/v1/runs'), page([realRunSummary, OLD]));
    expect(cardIds(q(m.el, 'runs-list')!)).toEqual([realRunSummary.run_id]);
    const versions = q(m.el, 'old-versions') as HTMLDetailsElement;
    expect(versions.open).toBe(false);
    expect(versions.querySelector('summary')!.textContent).toContain('Ver versiones anteriores');
    expect(cardIds(versions)).toEqual(['hist-old']);
    expect(txt(versions, 'replaced-notice')).toContain('Esta versión fue reemplazada. No uses sus sugerencias');
    expect((q(versions, 'replaced-link') as HTMLAnchorElement).getAttribute('href')).toContain('run=' + realRunSummary.run_id);
    expect(txt(versions, 'run-status')).toBe('Versión reemplazada');
    expect(txt(versions, 'run-status')).not.toContain('uso por defecto');
  });

  it('si la dirección apunta a una versión reemplazada, las versiones anteriores se abren solas', async () => {
    const m = await mountAs(RunsPage, 'lector', '/corridas?run=hist-old');
    await ok(m.f, one(m.http, '/api/v1/runs'), page([realRunSummary, OLD]));
    expect((q(m.el, 'old-versions') as HTMLDetailsElement).open).toBe(true);
    expect(q(q(m.el, 'old-versions')!, 'run-consulting')).toBeTruthy();
    // el análisis vigente ya no figura como el consultado
    expect(q(q(m.el, 'run-card-' + realRunSummary.run_id)!, 'run-consulting')).toBeNull();
  });

  it('el detalle completo se pide solo al abrir «Detalles técnicos», y un error del detalle no inventa datos', async () => {
    const m = await mountAs(RunsPage, 'lector');
    await ok(m.f, one(m.http, '/api/v1/runs'), page([histRun]));
    m.http.expectNone((r) => r.url.startsWith('/api/v1/runs/'));
    const tech = q(m.el, 'tech-' + histRun.run_id) as HTMLDetailsElement;
    tech.open = true;
    tech.dispatchEvent(new Event('toggle'));
    await settle(m.f);
    one(m.http, '/api/v1/runs/' + histRun.run_id).flush({}, { status: 503, statusText: 'x' });
    await settle(m.f);
    expect(tech.querySelector('[data-state="error"]')).toBeTruthy();
    expect(q(m.el, 'detail-status')).toBeNull();
  });

  it('el administrador ve «Crear un análisis nuevo»; sin análisis, el vacío ofrece una acción válida', async () => {
    const m = await mountAs(RunsPage, 'admin');
    await ok(m.f, one(m.http, '/api/v1/runs'), page([]));
    expect((q(m.el, 'to-create') as HTMLAnchorElement).getAttribute('href')).toContain('/crear-analisis');
    expect(txt(m.el, 'runs-empty')).toContain('Crear un análisis');
    m.http.expectNone((r) => r.url === '/api/v1/jobs');
  });

  it('error al leer la lista: aviso con reintento y sin tarjetas', async () => {
    const m = await mountAs(RunsPage, 'lector');
    one(m.http, '/api/v1/runs').flush({}, { status: 503, statusText: 'x' });
    await settle(m.f);
    expect(m.el.querySelector('[data-state="error"]')).toBeTruthy();
    expect(m.el.querySelector('[data-testid^="run-card-"]')).toBeNull();
    (m.el.querySelector('[data-state="error"] button') as HTMLButtonElement).click();
    await ok(m.f, one(m.http, '/api/v1/runs'), page([histRun]));
    expect(cardIds(m.el)).toEqual([histRun.run_id]);
  });
});

describe('Cargar datos / Datos cargados', () => {
  const item = { import_id: 'imp-1', archivo: 'ventas_julio.xlsx', mes: '2026-07', estado: 'aprobada', filas_leidas: 1500, ventas_aceptadas: 1400, notas_credito: 60, rechazadas: 30, insertadas: 1400, ya_existentes: 0, en_conflicto: 2, iniciado_utc: '2026-10-17T10:00:00Z', finalizado_utc: null };

  it('administrador: 3 pasos, mensaje de agosto, selector y tabla corta con el resto en el detalle', async () => {
    const m = await mountAs(ImportsPage, 'admin');
    await ok(m.f, one(m.http, '/api/v1/imports'), page([item]));
    await ok(m.f, one(m.http, '/api/v1/jobs'), page([]));
    expect(txt(m.el, 'page-title')).toBe('Cargar datos');
    expect(m.el.querySelectorAll('[data-testid="upload-steps"] li').length).toBe(3);
    expect(txt(m.el, 'upload-section')).toContain('Agosto de 2026 está reservado');
    expect(q(m.el, 'file-input')).toBeTruthy();
    const heads = Array.from(m.el.querySelectorAll('[data-testid="imports-table"] thead th')).map((t) => t.textContent!.trim()).filter(Boolean);
    expect(heads).toEqual(['Archivo', 'Mes', 'Estado', 'Ventas aceptadas', 'Rechazadas', 'Acción']);
    expect(txt(m.el, 'imports-table')).not.toContain('1,500');            // filas leídas va en el detalle
    (m.el.querySelector('[data-testid="imports-table"] tbody button') as HTMLButtonElement).click();
    await ok(m.f, one(m.http, '/api/v1/imports/imp-1'), { ...item });
    const counts = txt(m.el, 'import-counts');
    expect(counts).toContain('Filas leídas: 1,500');
    expect(counts).toContain('Notas de crédito: 60');
    expect(counts).toContain('en conflicto: 2');
  });

  it('reenvío del mismo archivo: se sigue el mismo trabajo (idempotente) y «sin cambios» se dice en palabras sencillas', async () => {
    const m = await mountAs(ImportsPage, 'admin');
    await ok(m.f, one(m.http, '/api/v1/imports'), page([]));
    await ok(m.f, one(m.http, '/api/v1/jobs'), page([]));
    const input = q(m.el, 'file-input') as HTMLInputElement;
    Object.defineProperty(input, 'files', { value: [new File([new Uint8Array(10)], 'ventas_julio.xlsx')], configurable: true });
    input.dispatchEvent(new Event('change'));
    await settle(m.f);
    (q(m.el, 'upload-btn') as HTMLButtonElement).click();
    m.http.expectOne((r) => r.method === 'POST' && r.url === '/api/v1/imports').flush({ job_id: 'job-1', status: 'completed', reused: true }, { status: 202, statusText: 'Accepted' });
    await settle(m.f);
    expect(txt(m.el, 'reused-note')).toContain('no se duplica');
    await ok(m.f, one(m.http, '/api/v1/jobs/job-1'), { job_id: 'job-1', type: 'import_excel', status: 'completed', result: { outcome: 'sin_cambios', import_id: 'imp-1' } });
    expect(txt(m.el, 'job-status')).toBe('Terminado');
    expect(txt(m.el, 'job-outcome')).toContain('Este archivo ya estaba cargado; no se modificó ningún dato');
    await ok(m.f, one(m.http, '/api/v1/imports'), page([]));
  });

  it('lector: «Datos cargados», solo lectura comprensible, sin carga ni consulta de trabajos', async () => {
    const m = await mountAs(ImportsPage, 'lector');
    await ok(m.f, one(m.http, '/api/v1/imports'), page([item]));
    expect(txt(m.el, 'page-title')).toBe('Datos cargados');
    expect(txt(m.el, 'readonly-note')).toContain('solo lectura');
    expect(txt(m.el, 'readonly-note')).toContain('Solo el administrador puede cargar archivos');
    for (const id of ['upload-section', 'file-input', 'upload-btn', 'upload-steps']) expect(q(m.el, id)).toBeNull();
    expect(txt(m.el, 'imports-table')).toContain('ventas_julio.xlsx');
    m.http.expectNone((r) => r.url === '/api/v1/jobs');
  });

  it('error al leer la lista de archivos: aviso con reintento', async () => {
    const m = await mountAs(ImportsPage, 'lector');
    one(m.http, '/api/v1/imports').flush({}, { status: 503, statusText: 'x' });
    await settle(m.f);
    expect(m.el.querySelector('[data-state="error"]')?.textContent).toContain('Servicio no disponible');
    expect(m.el.querySelector('[data-state="error"] button')).toBeTruthy();
    expect(q(m.el, 'imports-table')).toBeNull();
  });
});

describe('Crear análisis: permisos y confirmación', () => {
  it('el lector no ve controles y el servidor sigue decidiendo (no hay POST)', async () => {
    const m = await mountAs(CreateRunPage, 'lector');
    await settle(m.f);
    expect(txt(m.el, 'admin-only')).toBe('Solo el administrador puede crear análisis.');
    expect(m.el.querySelectorAll('button, input').length).toBe(0);
    m.http.expectNone(() => true);
  });

  it('si el servidor rechaza al administrador (403) se muestra un mensaje con siguiente paso, sin crear trabajos', async () => {
    const m = await mountAs(CreateRunPage, 'admin');
    await ok(m.f, one(m.http, '/api/v1/jobs'), page([]));
    await ok(m.f, one(m.http, '/api/v1/runs/options'), { origin_min: '2026-06-01', origin_max: '2026-07-10', origin_default: '2026-07-10', horizon_max: 21, methods: ['promedio_28'] });
    (q(m.el, 'generate-btn') as HTMLButtonElement).click();
    m.http.expectOne((r) => r.method === 'POST' && r.url === '/api/v1/runs').flush({ error: { code: 'PROHIBIDO', message: 'x' } }, { status: 403, statusText: 'x' });
    await settle(m.f);
    expect(txt(m.el, 'gen-error')).toContain('No tiene permiso');
    expect(txt(m.el, 'gen-error')).toContain('Puedes intentarlo de nuevo');
    expect(q(m.el, 'gen-done')).toBeNull();
    m.http.expectNone((r) => r.url.startsWith('/api/v1/jobs/'));
  });

  it('un error al leer las fechas permitidas se avisa con reintento y no habilita la creación', async () => {
    const m = await mountAs(CreateRunPage, 'admin');
    await ok(m.f, one(m.http, '/api/v1/jobs'), page([]));
    one(m.http, '/api/v1/runs/options').flush({}, { status: 503, statusText: 'x' });
    await settle(m.f);
    expect(q(m.el, 'gen-section')!.querySelector('[data-state="error"]')).toBeTruthy();
    expect(q(m.el, 'generate-btn')).toBeNull();
  });
});

describe('Estado del sistema', () => {
  it('lenguaje claro; degradado con siguiente paso y «Volver a comprobar» que repite la consulta', async () => {
    const m = await mountAs(SystemPage, 'admin');
    await ok(m.f, one(m.http, '/api/v1/health'), { status: 'degraded', database: 'unavailable', version: 'v-test' });
    expect(txt(m.el, 'health')).toContain('funcionando con fallas');
    expect(txt(m.el, 'health')).toContain('no disponible');
    expect(txt(m.el, 'degraded')).toContain('Vuelve a comprobar');
    (q(m.el, 'recheck') as HTMLButtonElement).click();
    await ok(m.f, one(m.http, '/api/v1/health'), { status: 'ok', database: 'ok', version: 'v-test' });
    expect(txt(m.el, 'health')).toContain('funcionando');
    expect(q(m.el, 'degraded')).toBeNull();
  });
});

describe('Acceso', () => {
  async function submit(m: M<LoginPage>, status: number, body: object) {
    const set = (n: string, v: string) => { const i = m.el.querySelector(`[name="${n}"]`) as HTMLInputElement; i.value = v; i.dispatchEvent(new Event('input')); };
    set('username', 'ana'); set('password', 'clave');
    m.f.detectChanges();
    (m.el.querySelector('form') as HTMLFormElement).dispatchEvent(new Event('submit'));
    const r = one(m.http, '/api/v1/auth/login');
    if (status === 200) r.flush(body); else r.flush(body, { status, statusText: 'x' });
    await settle(m.f);
  }

  it('indica con qué usuario ingresar; tras ingresar va a Inicio', async () => {
    const m = await mountAs(LoginPage, null, '/acceso');
    expect(txt(m.el, 'page-lead')).toBe('Ingresa con el usuario que te dio el administrador.');
    const nav = vi.spyOn(m.router, 'navigate').mockResolvedValue(true);
    await submit(m, 200, { username: 'ana', role: 'lector', csrf_token: 'c', expires_at: '2026-10-17T23:00:00Z' });
    expect(nav).toHaveBeenCalledWith(['/inicio']);
  });

  it('errores con siguiente paso: credenciales incorrectas y servicio no disponible', async () => {
    const bad = await mountAs(LoginPage, null, '/acceso');
    await submit(bad, 401, { error: { code: 'NO_AUTENTICADO', message: 'x' } });
    expect(txt(bad.el, 'login-error')).toContain('Usuario o contraseña incorrectos. Revisa los datos');
    bad.f.destroy();
    lastHttp?.verify();
    TestBed.resetTestingModule();
    const down = await mountAs(LoginPage, null, '/acceso');
    await submit(down, 503, {});
    expect(txt(down.el, 'login-error')).toContain('Servicio no disponible');
    expect(txt(down.el, 'login-error')).toContain('avisa al administrador');
  });
});
