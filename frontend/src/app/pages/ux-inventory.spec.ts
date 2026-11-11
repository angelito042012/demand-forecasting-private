// T18: «Inventario informado». Fixtures de FORMA con el esquema del contrato (docs/T18_CONTRATO_INVENTARIO_INFORMADO.md §4):
// no son resultados reales ni se prueban contra el backend.
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting, TestRequest } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { apiInterceptor } from '../core/interceptors';
import { InventoryPage } from './inventory.page';
import { routes } from '../app.routes';
import { visibleText } from '../testing/mount';

const URL = '/api/v1/inventory/reported';
let http: HttpTestingController;

function snapshot(over: object = {}, ctx: object | null = { sales_history_end: '2026-09-30' }) {
  return {
    snapshot_id: 'invrep-20261018T1700-a1-608d15a74a58', version: 1, status: 'current',
    as_of_local: '2026-10-18T17:00:00-05:00', as_of_utc: '2026-10-18T22:00:00Z', timezone: 'America/Lima',
    warehouse: { id: '1', name: 'Almacén Principal' }, nature: 'CONTEO_FISICO_REPORTADO_POR_USUARIO', independent_verification: false,
    source: { file: 'Solicitud_conteo_50_productos.xlsx', sha256_short: '608d15a74a58' },
    counts: { items: 50, with_stock: 48, no_stock: 2 },
    declared_unknowns: [{ code: 'BRECHA_OCTUBRE', detail: 'Ventas del 01 al 18/10 desconocidas' }, { code: 'PEDIDOS_PENDIENTES', detail: 'Pedidos por recibir no informados' }],
    ...(ctx ? { context: ctx } : {}), imported_at: '2026-10-18T23:00:00Z', ...over,
  };
}
function items(n = 50) {
  return Array.from({ length: n }, (_, i) => ({
    producto_id: String(3230000 + i).padStart(9, '0'), producto: `PRODUCTO DE PRUEBA ${i + 1}`, categoria: 'X', unidad_reporte: 'UND',
    unidad_descripcion: i === 1 ? 'Caja de 12' : 'Un frasco de 250 ML', libre: i < 2 ? 0 : i + 1, reservada: i === 5 ? null : 0, no_vendible: 0, fisica_total: i + 1,
  }));
}
function body(over: object = {}, snapOver: object = {}, ctx: object | null = { sales_history_end: '2026-09-30' }) {
  return {
    snapshot: snapshot(snapOver, ctx), items: items(), page: 1, page_size: 50, total: 50, has_more: false,
    view_counts: { all: 50, with_stock: 48, no_stock: 2 }, provenance: 'INVENTARIO_INFORMADO_POR_LA_EMPRESA',
    disclaimer: 'Inventario informado por la empresa (conteo del 18/10/2026 17:00, hora de Lima); no es inventario simulado ni se ha verificado de forma independiente.', ...over,
  };
}

async function settle(f: ComponentFixture<unknown>) { f.detectChanges(); await f.whenStable(); f.detectChanges(); }
const one = () => http.expectOne((r) => r.url === URL);
async function ok(f: ComponentFixture<unknown>, r: TestRequest, b: unknown) { r.flush(b as object); await settle(f); }
const q = (el: HTMLElement, id: string) => el.querySelector(`[data-testid="${id}"]`) as HTMLElement | null;
const txt = (el: HTMLElement, id: string) => (q(el, id)?.textContent ?? '').replace(/\s+/g, ' ').trim();

async function open(b: unknown = body()) {
  TestBed.configureTestingModule({
    imports: [InventoryPage],
    providers: [provideHttpClient(withInterceptors([apiInterceptor])), provideHttpClientTesting(), provideRouter([{ path: '**', children: [] }])],
  });
  http = TestBed.inject(HttpTestingController);
  const f = TestBed.createComponent(InventoryPage);
  f.detectChanges();
  const first = one();
  if (b !== undefined) await ok(f, first, b);
  return { f, el: f.nativeElement as HTMLElement, first };
}
afterEach(() => http?.verify());

describe('Inventario informado', () => {
  it('muestra los 50 productos con los ceros visibles y «Sin existencia» como etiqueta; sin total general', async () => {
    const { el, first } = await open();
    expect(first.request.params.get('page_size')).toBe('50');
    expect(first.request.params.has('view')).toBe(false);
    expect(el.querySelectorAll('h1').length).toBe(1);
    expect(txt(el, 'page-title')).toBe('Inventario informado por la empresa');
    expect(txt(el, 'page-lead')).toContain('18/10/2026 a las 17:00');
    expect(el.querySelectorAll('[data-testid="inv-table"] tbody tr').length).toBe(50);
    expect(el.querySelectorAll('[data-testid="no-stock-chip"]').length).toBe(2);
    const row0 = el.querySelector('tr[data-sku="003230000"]')!;
    expect(row0.querySelector('[data-col="code"]')!.textContent!.trim()).toBe('003230000');   // ceros conservados
    expect(row0.querySelector('[data-col="free"]')!.textContent).toMatch(/0\s*Sin existencia/);
    expect(el.querySelector('tr[data-sku="003230001"] [data-col="unit"]')!.textContent).toContain('Caja de 12');
    expect(txt(el, 'inv-summary')).toBe('50 productos · 48 con existencia · 2 sin existencia');
    expect(txt(el, 'inv-units-note')).toContain('no se multiplicó');
    expect(el.textContent).not.toMatch(/total general de unidades:|Total:/);
    expect(el.querySelectorAll('.btn').length).toBe(1);
    expect(el.querySelector('app-analysis-bar')).toBeNull();
  });

  it('null se muestra «No informado», distinto del 0 declarado', async () => {
    const { el } = await open();
    const nulo = el.querySelector('tr[data-sku="003230005"]')!;
    expect(nulo.querySelector('[data-col="reserved"]')!.textContent!.trim()).toBe('No informado');
    expect(nulo.querySelector('[data-col="unsellable"]')!.textContent!.trim()).toBe('0');
    const cero = el.querySelector('tr[data-sku="003230000"]')!;
    expect(cero.querySelector('[data-col="reserved"]')!.textContent!.trim()).toBe('0');
    expect(cero.querySelector('[data-col="free"]')!.textContent).not.toContain('No informado');
  });

  it('la fecha, hora y almacén salen de la respuesta; no dice «simulado»', async () => {
    const { f, el } = await open();
    expect(txt(el, 'inv-strip')).toContain('Conteo del 18/10/2026, 17:00 (hora de Lima) · Almacén Principal (almacén 1)');
    expect(txt(el, 'inv-strip')).toContain('Informado por la empresa; no verificado de forma independiente');
    expect(visibleText(el)).not.toMatch(/inventario simulado|conteo simulado/i);
    expect(visibleText(el).replace("Reposición simulada", "")).not.toMatch(/simulad/i);   // solo el nombre del enlace
    f.destroy();
    TestBed.resetTestingModule();
    http.verify();
    const other = await open(body({}, { as_of_local: '2026-11-02T09:30:00-05:00', warehouse: { id: '7', name: 'Almacén Norte' } }));
    expect(txt(other.el, 'inv-strip')).toContain('Conteo del 02/11/2026, 09:30 (hora de Lima) · Almacén Norte (almacén 7)');
    expect(txt(other.el, 'inv-gap')).toContain('Este inventario es del 02/11/2026');
  });

  it('un solo aviso: inventario del 18/10 frente a ventas hasta la fecha de la API; pedidos por recibir no informados; enlace a Reposición simulada', async () => {
    const { el } = await open();
    expect(el.querySelectorAll('[data-testid="inv-gap"]').length).toBe(1);
    const t = txt(el, 'inv-gap');
    expect(t).toContain('Este inventario es del 18/10/2026');
    expect(t).toContain('El histórico de ventas disponible termina el 30 de septiembre de 2026');
    expect(t).toContain('no son cero');
    expect(t).toContain('no hay una recomendación de reposición actualizada');
    expect(t).toContain('Pedidos por recibir: no informados');
    expect((q(el, 'inv-to-reco') as HTMLAnchorElement).getAttribute('href')).toContain('/recomendaciones');
  });

  it('si falta context.sales_history_end no se afirma ninguna fecha de corte', async () => {
    const { el } = await open(body({}, {}, null));
    const t = txt(el, 'inv-gap');
    expect(t).not.toContain('30 de septiembre');
    expect(t).not.toMatch(/termina el/);
    expect(t).toContain('No se pudo confirmar hasta qué fecha');
    expect(t).toContain('no son cero');
  });

  it('las vistas piden view al servidor, vuelven a la página 1 y marcan aria-pressed', async () => {
    const { f, el } = await open();
    expect(q(el, 'view-all')!.getAttribute('aria-pressed')).toBe('true');
    (q(el, 'view-no_stock') as HTMLButtonElement).click();
    const r = one();
    expect(r.request.params.get('view')).toBe('no_stock');
    expect(r.request.params.get('page')).toBe('1');
    await ok(f, r, body({ items: items(2), total: 2, view_counts: { all: 50, with_stock: 48, no_stock: 2 } }));
    expect(q(el, 'view-no_stock')!.getAttribute('aria-pressed')).toBe('true');
    expect(q(el, 'view-all')!.getAttribute('aria-pressed')).toBe('false');
    expect(el.querySelectorAll('[data-testid="inv-table"] tbody tr').length).toBe(2);
    expect(txt(el, 'inv-summary')).toBe('50 productos · 48 con existencia · 2 sin existencia');   // del servidor, no de la página
    (q(el, 'view-with_stock') as HTMLButtonElement).click();
    expect(one().request.params.get('view')).toBe('with_stock');
  });

  it('la búsqueda envía q al servidor; sin coincidencias se avisa sin tabla vacía', async () => {
    const { f, el } = await open();
    const input = q(el, 'inv-q') as HTMLInputElement;
    input.value = 'lanosterin';
    input.dispatchEvent(new Event('input'));
    (el.querySelector('form') as HTMLFormElement).dispatchEvent(new Event('submit'));
    const r = one();
    expect(r.request.params.get('q')).toBe('lanosterin');
    expect(r.request.params.get('page')).toBe('1');
    await ok(f, r, body({ items: [], total: 0 }));
    expect(q(el, 'inv-no-match')).toBeTruthy();
    expect(q(el, 'inv-table')).toBeNull();
    expect(q(el, 'inv-strip')).toBeTruthy();   // la franja no se pierde
  });

  it('el orden y la paginación son del servidor', async () => {
    const { f, el } = await open(body({ items: items(25), page_size: 25, has_more: true }));
    expect(txt(el, 'pg-info')).toContain('Página 1 de 2');
    (q(el, 'next') as HTMLButtonElement).click();
    const r = one();
    expect(r.request.params.get('page')).toBe('2');
    await ok(f, r, body({ items: items(25), page: 2, page_size: 25, has_more: false }));
    expect(txt(el, 'pg-info')).toContain('Página 2 de 2');
    const sel = q(el, 'inv-sort') as HTMLSelectElement;
    sel.value = '-libre';
    sel.dispatchEvent(new Event('change'));
    const r2 = one();
    expect(r2.request.params.get('sort')).toBe('-libre');
    expect(r2.request.params.get('page')).toBe('1');
    await ok(f, r2, body());
  });

  it('detalles plegados: fuente, huella, versión, identificador y desconocidos declarados', async () => {
    const { el } = await open();
    const d = q(el, 'inv-details') as HTMLDetailsElement;
    expect(d.open).toBe(false);
    expect(txt(el, 'inv-source')).toBe('Solicitud_conteo_50_productos.xlsx');
    expect(d.textContent).toContain('608d15a74a58');
    expect(txt(el, 'inv-snapshot-id')).toContain('invrep-20261018T1700-a1');
    expect(txt(el, 'inv-unknowns')).toContain('BRECHA_OCTUBRE');
    expect(q(el, 'inv-versions')).toBeNull();   // versión 1: nada que mostrar
  });

  it('con más de una versión muestra la consultada y carga las anteriores solo al abrir', async () => {
    const { f, el } = await open(body({}, { version: 2 }));
    http.expectNone((r) => r.url === URL + '/snapshots');
    const d = q(el, 'inv-versions') as HTMLDetailsElement;
    expect(d.textContent).toContain('Se muestra la versión 2');
    d.open = true;
    d.dispatchEvent(new Event('toggle'));
    await ok(f, http.expectOne(URL + '/snapshots'), [
      { snapshot_id: 'invrep-20261018T1700-a1-608d15a74a58', version: 2, status: 'current', as_of_local: '2026-10-18T17:00:00-05:00', warehouse: { id: '1', name: 'x' } },
      { snapshot_id: 'invrep-OLD', version: 1, status: 'superseded', as_of_local: '2026-10-18T17:00:00-05:00', warehouse: { id: '1', name: 'x' } },
    ]);
    expect(d.querySelectorAll('li').length).toBe(1);
    (d.querySelector('button') as HTMLButtonElement).click();
    expect(one().request.params.get('snapshot_id')).toBe('invrep-OLD');
  });

  it('sin snapshot: estado vacío claro, sin franja ni tabla', async () => {
    const { el } = await open({ snapshot: null, items: [], page: 1, page_size: 50, total: 0, has_more: false, unavailable_reason: 'SIN_INVENTARIO_INFORMADO' });
    expect(el.querySelector('[data-state="empty"]')!.textContent).toContain('Todavía no se cargó el conteo de inventario');
    expect(q(el, 'inv-strip')).toBeNull();
    expect(q(el, 'inv-table')).toBeNull();
    expect(q(el, 'inv-gap')).toBeNull();
  });

  it('error: aviso con «Reintentar» y una sola petición por reintento, sin inventar datos', async () => {
    TestBed.configureTestingModule({
      imports: [InventoryPage],
      providers: [provideHttpClient(withInterceptors([apiInterceptor])), provideHttpClientTesting(), provideRouter([{ path: '**', children: [] }])],
    });
    http = TestBed.inject(HttpTestingController);
    const f = TestBed.createComponent(InventoryPage);
    f.detectChanges();
    one().flush({}, { status: 503, statusText: 'x' });
    await settle(f);
    const el = f.nativeElement as HTMLElement;
    expect(el.querySelector('[data-state="error"]')).toBeTruthy();
    expect(q(el, 'inv-table')).toBeNull();
    (el.querySelector('[data-state="error"] button') as HTMLButtonElement).click();
    await ok(f, one(), body());
    expect(el.querySelectorAll('[data-testid="inv-table"] tbody tr').length).toBe(50);
    http.expectNone(() => true);
  });

  it('403: mensaje de permiso, sin controles ni tabla', async () => {
    TestBed.configureTestingModule({
      imports: [InventoryPage],
      providers: [provideHttpClient(withInterceptors([apiInterceptor])), provideHttpClientTesting(), provideRouter([{ path: '**', children: [] }])],
    });
    http = TestBed.inject(HttpTestingController);
    const f = TestBed.createComponent(InventoryPage);
    f.detectChanges();
    one().flush({ error: { code: 'PROHIBIDO', message: 'x' } }, { status: 403, statusText: 'x' });
    await settle(f);
    const el = f.nativeElement as HTMLElement;
    expect(txt(el, 'inv-forbidden')).toContain('No tienes permiso');
    expect(q(el, 'inv-table')).toBeNull();
    expect(el.querySelector('[data-state="error"]')).toBeNull();
  });

  it('solo lectura: ningún campo de edición ni petición de escritura', async () => {
    const { el } = await open();
    expect(el.querySelectorAll('input[type="file"], textarea').length).toBe(0);
    http.expectNone((r) => r.method !== 'GET');
  });
});

describe('Inventario informado: ruta y menú', () => {
  it('la ruta /inventario existe, es perezosa y se titula «Inventario informado»', () => {
    const prot = routes.find((r) => r.canActivate)!;
    const r = prot.children!.find((c) => c.path === 'inventario')!;
    expect(r.title).toBe('Inventario informado');
    expect(r.loadComponent).toBeTruthy();
  });
});
