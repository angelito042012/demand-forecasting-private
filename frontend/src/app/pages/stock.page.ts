import { Component, computed, inject, signal } from '@angular/core';
import { tap } from 'rxjs';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService } from '../core/api.service';
import { load } from '../core/load';
import { StockItem, StockPage as StockPageData, StockSnapshot } from '../core/models';
import { fmtInt } from '../core/format';
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
    <app-page-header title="Existencias" [lead]="lead()" />

    @if (snap(); as s) {
      <p class="notice info" data-testid="stk-strip">
        <strong>Existencia reconstruida al cierre del {{ closingDay() }} (conteo reportado {{ baseStamp() }} + movimientos del sistema)</strong>
        @if (warehouse()) { · {{ warehouse() }} }
        · Es una reconstrucción, no un conteo físico nuevo.
      </p>
      @if (lastMovement()) {
        <p class="muted" data-testid="stk-age">Último movimiento del sistema considerado: {{ lastMovement() }}. Lo ocurrido después no está incluido.</p>
      }
      @if (pendingConfirmations().length) {
        <div class="notice warn" role="status" data-testid="stk-confirmations">
          <strong>Pendiente de confirmar con la empresa</strong>
          <ul class="plain">@for (c of pendingConfirmations(); track c.code) { <li [attr.data-code]="c.code">{{ c.text }}</li> }</ul>
        </div>
      }
      <p data-testid="stk-count-link">El conteo físico informado por la empresa es la base de esta reconstrucción.
        <a [routerLink]="['/inventario']" queryParamsHandling="preserve" data-testid="stk-to-count">Ver el conteo informado</a>.</p>
    }

    @if (forbidden()) {
      <p class="notice danger" role="alert" data-testid="stk-forbidden">No tienes permiso para ver las existencias. Ingresa con otro usuario o avisa al administrador.</p>
    } @else {
      @if (snap()) {
        <section class="toolbar" aria-label="Filtros de existencias">
          <form class="filters" (ngSubmit)="search()" aria-label="Buscar en las existencias">
            <label>Código o nombre <input name="q" [(ngModel)]="draft" autocomplete="off" maxlength="100" data-testid="stk-q" /></label>
            <label class="check"><input type="checkbox" name="only" data-testid="stk-only-diff" [ngModel]="onlyDiff()" (ngModelChange)="setOnlyDiff($event)" /> Solo productos con diferencia</label>
            <button type="submit" class="btn" data-testid="stk-search">Buscar</button>
          </form>
        </section>
      }

      <app-state-panel [state]="l.state()" emptyText="Todavía no hay una existencia reconstruida cargada." (retry)="l.reload()">
        @if (data(); as d) {
          <p data-testid="stk-summary"><strong>{{ summary() }}</strong></p>
          @if (d.items.length === 0) {
            <p class="state" data-testid="stk-no-match">Ningún producto coincide con la búsqueda o el filtro elegido.</p>
          } @else {
            <div class="table-wrap" tabindex="0" role="region" aria-label="Tabla de existencias">
              <table data-testid="stk-table">
                <thead><tr>
                  <th scope="col">Producto y presentación</th>
                  <th scope="col" class="num">Conteo base <small>({{ baseDay() }})</small></th>
                  <th scope="col" class="num">Entradas hasta el cierre</th>
                  <th scope="col" class="num">Salidas hasta el cierre</th>
                  <th scope="col" class="num">Existencia al cierre del {{ closingDay() }}</th>
                  <th scope="col">Diferencia con el sistema</th>
                </tr></thead>
                <tbody>
                  @for (r of d.items; track r.producto_id) {
                    <tr [attr.data-sku]="r.producto_id">
                      <td data-col="product"><strong data-col="code">{{ r.producto_id }}</strong> {{ r.producto }}
                        <span class="muted" data-col="unit"> · {{ r.unidad_descripcion || NOT_REPORTED }}</span></td>
                      <td class="num" data-col="base">{{ qty(r.base_count) }}</td>
                      <td class="num" data-col="in">{{ qty(r.movements?.entradas_cierre) }}</td>
                      <td class="num" data-col="out">{{ qty(r.movements?.salidas_cierre) }}</td>
                      <td class="num" data-col="free">{{ qty(r.libre) }}</td>
                      <td data-col="diff">
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
          <p class="muted" data-testid="stk-units-note">La cantidad está en la presentación indicada de cada producto; no se multiplicó. Por eso no se muestra un total general de unidades.</p>
        }
      </app-state-panel>

      @if (snap(); as s) {
        <details class="help" data-testid="stk-details">
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
})
export class StockPage {
  private api = inject(ApiService);
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
