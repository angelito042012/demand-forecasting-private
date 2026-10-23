import { DOCUMENT } from '@angular/common';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { tap } from 'rxjs';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService } from '../core/api.service';
import { load } from '../core/load';
import { StockItem, StockPage as StockPageData, StockSnapshot } from '../core/models';
import { fmtInt } from '../core/format';
import { useWideMain } from '../core/wide-main';
import { PageHeader } from '../ui/page-header';
import { StatePanel } from '../ui/state-panel';
import { Pager } from '../ui/pager';
import { NOT_REPORTED, localDay, localStamp, qty } from './inventory.page';

/** «2026-10-21T16:26:38-05:00» → «21/10/2026 a las 16:26» (la hora local viene escrita en la respuesta). */
export function stampWords(iso: string | null | undefined): string {
  const s = localStamp(iso);
  return s ? s.replace(', ', ' a las ') : 'fecha no informada';
}

/** T20: «Existencias». Existencia reconstruida al cierre del 20/10 con su procedencia; solo lectura, ninguna cifra se calcula aquí. */
@Component({
  selector: 'app-stock-page',
  imports: [FormsModule, RouterLink, PageHeader, StatePanel, Pager],
  template: `
    <app-page-header title="Existencias" />

    @if (snap(); as s) {
      <section class="surface compact-card" aria-label="Existencia reconstruida" data-testid="stk-strip">
        <p><strong>Existencia reconstruida (no es simulada) al cierre del {{ closingDay() }}</strong> (conteo reportado {{ baseStamp() }} + movimientos del sistema)
          @if (warehouse()) { · {{ warehouse() }} }
          · Es una reconstrucción, no un conteo físico nuevo.
          @if (lastMovement()) { <span class="muted" data-testid="stk-age">Último movimiento del sistema considerado: {{ lastMovement() }}. Lo ocurrido después no está incluido.</span> }
        </p>
        <div class="orders-row">
          <span data-testid="stk-count-link">El conteo físico informado por la empresa es la base de esta reconstrucción.
            <a [routerLink]="['/inventario']" queryParamsHandling="preserve" data-testid="stk-to-count">Ver el conteo informado</a>.</span>
          @if (pendingConfirmations().length) {
            <details class="pending-inline" data-testid="stk-confirmations">
              <summary><strong>{{ pendingConfirmations().length }} {{ pendingConfirmations().length === 1 ? 'pendiente' : 'pendientes' }} de confirmar con la empresa</strong>{{ ' ' }}<span class="link-like">Ver detalle</span></summary>
              <ul class="plain">@for (c of pendingConfirmations(); track c.code) { <li [attr.data-code]="c.code">{{ c.text }}</li> }</ul>
            </details>
          }
        </div>
      </section>
    }

    @if (forbidden()) {
      <p class="notice danger" role="alert" data-testid="stk-forbidden">No tienes permiso para ver las existencias. Ingresa con otro usuario o avisa al administrador.</p>
    } @else {
      @if (snap()) {
        <section class="toolbar compact-bar" aria-label="Filtros de existencias">
          <form class="filters" (ngSubmit)="search()" aria-label="Buscar en las existencias">
            <label><span class="sr-only">Código o nombre</span><input name="q" [(ngModel)]="draft" autocomplete="off" maxlength="100" placeholder="Código o nombre…" data-testid="stk-q" /></label>
            <label class="check"><input type="checkbox" name="only" data-testid="stk-only-diff" [ngModel]="onlyDiff()" (ngModelChange)="setOnlyDiff($event)" /> Solo productos con diferencia</label>
            <button type="submit" class="btn small" data-testid="stk-search">Buscar</button>
            <button type="button" class="link-btn legend-link" data-testid="stk-legend-open" (click)="showLegend()">Cómo leer la tabla</button>
          </form>
        </section>
      }

      <app-state-panel [state]="l.state()" emptyText="Todavía no hay una existencia reconstruida cargada." (retry)="l.reload()">
        @if (data(); as d) {
          @if (d.items.length === 0) {
            <p class="state" data-testid="stk-no-match">Ningún producto coincide con la búsqueda o el filtro elegido.</p>
          } @else {
            <div class="table-wrap stk-wrap" tabindex="0" role="region" aria-label="Tabla de existencias. Si no caben todas las columnas, desplázate hacia los lados.">
              <table data-testid="stk-table" class="stk-table">
                <thead><tr>
                  <th scope="col" class="sticky-col">Producto</th>
                  <th scope="col" class="num">Conteo {{ baseShort() }}</th>
                  <th scope="col" class="num">Entradas</th>
                  <th scope="col" class="num">Salidas</th>
                  <th scope="col" class="num">Existencia al {{ closingShort() }}</th>
                  <th scope="col">Diferencia</th>
                </tr></thead>
                <tbody>
                  @for (r of d.items; track r.producto_id) {
                    <tr [attr.data-sku]="r.producto_id">
                      <td data-col="product" class="sticky-col"><strong data-col="code">{{ r.producto_id }}</strong> {{ r.producto }}
                        <span class="muted unit" data-col="unit"> · {{ r.unidad_descripcion || NOT_REPORTED }}</span></td>
                      <td class="num" data-col="base">{{ qty(r.base_count) }}</td>
                      <td class="num" data-col="in">{{ qty(r.movements?.entradas_cierre) }}</td>
                      <td class="num" data-col="out">{{ qty(r.movements?.salidas_cierre) }}</td>
                      <td class="num" data-col="free">{{ qty(r.libre) }}</td>
                      <td data-col="diff" class="diff-cell">
                        @if (r.discrepancy; as x) {
                          <span class="chip warn" data-testid="stk-diff-chip">Diferencia con el sistema</span>
                          <span data-testid="stk-diff-text">{{ diffText(r, x.difference, x.compared_at_local) }}</span>
                        }
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          }
          <app-pager [page]="d.page" [pageSize]="d.page_size" [total]="d.total" [hasMore]="d.has_more" (go)="go($event)" />
          <p class="table-meta" data-testid="stk-summary"><strong>{{ summary() }}</strong></p>
          <details class="help fold" data-testid="stk-legend" [open]="legendOpen()" (toggle)="legendOpen.set($any($event.target).open)">
            <summary>Cómo leer la tabla</summary>
            <ul class="plain">
              <li><strong>Conteo {{ baseShort() }}:</strong> conteo físico informado por la empresa ({{ baseStamp() }}), base de la reconstrucción.</li>
              <li><strong>Entradas / Salidas:</strong> movimientos registrados en el sistema desde el conteo hasta el cierre del {{ closingDay() }}.</li>
              <li><strong>Existencia al {{ closingShort() }}:</strong> conteo + entradas − salidas. Es la existencia inicial del plan de compra.</li>
              <li><strong>Diferencia:</strong> solo aparece en los productos donde el sistema y la reconstrucción no coinciden en la fecha del último movimiento; está pendiente de confirmar y no se ajustó ninguna cantidad.</li>
              <li data-testid="stk-units-note">La cantidad está en la presentación indicada de cada producto; no se multiplicó. Por eso no se muestra un total general de unidades.</li>
            </ul>
          </details>
        }
      </app-state-panel>

      @if (snap(); as s) {
        <details class="help fold" data-testid="stk-details">
          <summary>Cómo se reconstruyó</summary>
          <ul class="plain">
            <li>Regla: existencia al cierre = conteo base + entradas − salidas registradas hasta el cierre del {{ closingDay() }}.</li>
            <li>Conteo base: {{ baseStamp() }}.</li>
            <li>La comparación con el stock que indica el sistema se hace en la fecha del último movimiento ({{ lastMovement() || 'no informado' }}), no al cierre.</li>
            @if (s.rule) { <li data-testid="stk-rule">{{ s.rule }}</li> }
            <li>Identificador: <span data-testid="stk-snapshot-id">{{ s.snapshot_id }}</span></li>
          </ul>
        </details>
      }
    }
  `,
  styles: `
    .sr-only { position: absolute; width: 1px; height: 1px; margin: -1px; padding: 0; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0; }
    :host ::ng-deep .ph { margin: 0 0 0.4rem; }
    :host ::ng-deep .ph h1 { margin: 0; }
    .compact-card { padding: 0.35rem 0.9rem; margin: 0 0 0.4rem; font-size: 0.95rem; }
    .compact-card p { margin: 0.25rem 0; }
    .orders-row { display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.2rem 1rem; margin: 0.2rem 0; }
    .pending-inline { flex: 0 1 auto; margin: 0.1rem 0; padding: 0.1rem 0.6rem; background: var(--warn-bg); color: var(--warn-ink); border: 1px solid var(--warn-line); border-radius: var(--radius); }
    .pending-inline[open] { flex: 1 1 100%; }
    .pending-inline summary, .fold > summary { cursor: pointer; }
    .link-like { text-decoration: underline; color: var(--link); }
    .compact-bar { margin: 0.4rem 0; padding: 0.4rem 0.9rem; }
    .compact-bar .filters { gap: 0.4rem 1rem; align-items: center; }
    .compact-bar label { display: flex; align-items: center; gap: 0.4rem; font-size: 0.95rem; }
    .compact-bar input:not([type='checkbox']) { width: 12rem; min-height: 2.2rem; }
    .link-btn { background: none; border: 0; padding: 0; color: var(--link); text-decoration: underline; cursor: pointer; font: inherit; min-height: 0; }
    .legend-link { margin-left: auto; }
    .stk-wrap { max-height: none; margin: 0.4rem 0; }
    .stk-table { width: 100%; min-width: 52rem; font-size: 0.95rem; }
    .stk-table th, .stk-table td { padding: 0.4rem 0.5rem; }
    .stk-table thead th { white-space: normal; vertical-align: bottom; line-height: 1.25; position: static; }
    .stk-table td.num { white-space: normal; }
    .stk-table .sticky-col { position: sticky; left: 0; background: var(--surface); width: 20rem; min-width: 12rem; max-width: 24rem; box-shadow: 1px 0 0 var(--line); z-index: 2; }
    .stk-table thead th.sticky-col { z-index: 4; background: #e8ecf2; }
    .stk-table .unit { font-size: 0.9rem; }
    .stk-table .diff-cell { min-width: 16rem; }
    .table-meta { margin: 0.3rem 0; }
  `,
})
export class StockPage {
  private api = inject(ApiService);
  private doc = inject(DOCUMENT);
  private destroyRef = inject(DestroyRef);
  readonly NOT_REPORTED = NOT_REPORTED;
  readonly qty = qty;

  q = signal('');
  draft = '';
  onlyDiff = signal(false);
  page = signal(1);
  readonly pageSize = 50;
  snap = signal<StockSnapshot | null>(null);

  l = load<StockPageData>(
    () => this.api.stock({
      q: this.q() || undefined, view: this.onlyDiff() ? 'discrepancias' : undefined, page: this.page(), page_size: this.pageSize,
    }).pipe(tap((d) => { if (d.snapshot) this.snap.set(d.snapshot); })),
    (d) => !d.snapshot,
  );
  data = computed(() => { const s = this.l.state(); return s.kind === 'data' ? s.data : null; });
  forbidden = computed(() => { const s = this.l.state(); return s.kind === 'error' && (s.error.status === 403 || s.error.code === 'PROHIBIDO'); });

  constructor() { useWideMain(this.doc, this.destroyRef); }
  legendOpen = signal(false);
  showLegend() {
    this.legendOpen.set(true);
    setTimeout(() => { const d = this.doc.querySelector('[data-testid="stk-legend"]') as HTMLElement | null; d?.scrollIntoView?.({ block: 'center' }); (d?.querySelector('summary') as HTMLElement | null)?.focus(); }, 0);
  }
  /** «20/10/2026» → «20/10» (las fechas salen del plan, no están fijas). */
  private dm = (d: string | null | undefined) => (d && /^\d{2}\/\d{2}\/\d{4}$/.test(d) ? d.slice(0, 5) : d ?? '');
  closingShort = computed(() => this.dm(localDay(this.snap()?.as_of_local)) || 'cierre');
  baseShort = computed(() => this.dm(localDay(this.snap()?.base_count?.as_of_local)) || 'base');
  closingDay = computed(() => localDay(this.snap()?.as_of_local) ?? 'fecha no informada');
  baseStamp = computed(() => stampWords(this.snap()?.base_count?.as_of_local));
  baseDay = computed(() => localDay(this.snap()?.base_count?.as_of_local) ?? 'fecha no informada');
  lastMovement = computed(() => { const m = this.snap()?.movements?.last_movement_local; return m ? stampWords(m) : ''; });
  warehouse = computed(() => {
    const w = this.snap()?.warehouse;
    if (!w) return '';
    return typeof w === 'string' ? `almacén ${w}` : `${w.name} (almacén ${w.id})`;
  });
  lead = computed(() => this.snap()
    ? `Cuántas unidades de cada producto había al cierre del ${this.closingDay()}, y de dónde sale ese número.`
    : 'Cuántas unidades de cada producto había al cierre del día anterior a la compra recomendada.');
  pendingConfirmations = computed(() => (this.snap()?.confirmations ?? []).filter((c) => c.status === 'PENDIENTE'));
  summary = computed(() => {
    const d = this.data();
    const c = d?.snapshot?.counts;
    if (!d) return '';
    const base = c?.products !== undefined ? `${c.products} productos` : `${d.total} productos`;
    return c?.discrepancies !== undefined ? `${base} · ${c.discrepancies} con diferencia respecto al sistema` : base;
  });

  /** Texto de la diferencia en el producto afectado: la API entrega la diferencia (sistema − reconstruida) y la fecha. */
  diffText(r: StockItem, diff: number, at: string | undefined): string {
    const when = at ? stampWords(at) : 'la fecha del último movimiento';
    return `El sistema indica ${qty(r.system_stock_at_last_movement)} y la reconstrucción ${qty(r.reconstructed_at_last_movement)} al ${when} `
      + `(diferencia ${fmtInt(diff, true)}). Sin explicar: pendiente de confirmar con la empresa; no se ajustó ninguna cantidad.`;
  }

  setOnlyDiff(v: boolean) { this.onlyDiff.set(!!v); this.page.set(1); this.l.reload(); }
  search() { this.q.set(this.draft.trim()); this.page.set(1); this.l.reload(); }
  go(p: number) { this.page.set(p); this.l.reload(); }
}
