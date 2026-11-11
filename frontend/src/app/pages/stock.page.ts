import { DOCUMENT } from '@angular/common';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { tap } from 'rxjs';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService } from '../core/api.service';
import { load } from '../core/utils/load';
import { StockItem, StockPage as StockPageData, StockSnapshot } from '../core/models';
import { fmtInt } from '../core/utils/format';
import { useWideMain } from '../core/utils/wide-main';
import { PageHeader } from '../shared/components/page-header';
import { StatePanel } from '../shared/components/state-panel';
import { Pager } from '../shared/components/pager';
import { NOT_REPORTED, localDay, localStamp, qty } from './inventory.page';
import { InputTextModule } from 'primeng/inputtext';
import { ButtonModule } from 'primeng/button';
import { CheckboxModule } from 'primeng/checkbox';
import { PanelModule } from 'primeng/panel';
import { TagModule } from 'primeng/tag';
import { MessageModule } from 'primeng/message';
import { TableModule } from 'primeng/table';

/** «2026-10-21T16:26:38-05:00» → «21/10/2026 a las 16:26» (la hora local viene escrita en la respuesta). */
export function stampWords(iso: string | null | undefined): string {
  const s = localStamp(iso);
  return s ? s.replace(', ', ' a las ') : 'fecha no informada';
}

@Component({
  selector: 'app-stock-page',
  imports: [FormsModule, RouterLink, PageHeader, StatePanel, Pager, InputTextModule, ButtonModule, CheckboxModule, PanelModule, TagModule, MessageModule, TableModule],
  template: `
    <app-page-header title="Existencias" />

    @if (snap(); as s) {
      <p-panel data-testid="stk-strip">
        <ng-template #header>
          <div class="flex align-items-center gap-2">
            <i class="pi pi-box"></i>
            <strong>Existencia reconstruida al cierre del {{ closingDay() }}</strong>
          </div>
        </ng-template>
        <p>(conteo reportado {{ baseStamp() }} + movimientos del sistema)
          @if (warehouse()) { · {{ warehouse() }} }
          · Es una reconstrucción, no un conteo físico nuevo.
          @if (lastMovement()) { <span class="muted" data-testid="stk-age">El plan usa la existencia al cierre del {{ closingDay() }}. Los movimientos posteriores, hasta el último del sistema ({{ lastMovement() }}), solo se usan para comparar con el stock del sistema y no cambian las cantidades; lo ocurrido después no está incluido.</span> }
        </p>
        <div class="orders-row">
          <span data-testid="stk-count-link">El conteo físico informado por la empresa es la base de esta reconstrucción.
            <a [routerLink]="['/inventario']" queryParamsHandling="preserve" data-testid="stk-to-count">Ver el conteo informado</a>.</span>
          @if (pendingConfirmations().length) {
            <p-message severity="warn" styleClass="w-full mt-2" data-testid="stk-confirmations">
              <strong>{{ pendingConfirmations().length }} {{ pendingConfirmations().length === 1 ? 'pendiente' : 'pendientes' }} de confirmar con la empresa</strong>
              <ul class="plain mt-1">@for (c of pendingConfirmations(); track c.code) { <li [attr.data-code]="c.code">{{ c.text }}</li> }</ul>
            </p-message>
          }
        </div>
      </p-panel>
    }

    @if (forbidden()) {
      <p-message severity="error" role="alert" data-testid="stk-forbidden" styleClass="w-full my-3" text="No tienes permiso para ver las existencias. Ingresa con otro usuario o avisa al administrador." />
    } @else {
      @if (snap()) {
        <div class="filter-bar" aria-label="Filtros de existencias">
          <form class="flex flex-wrap align-items-center gap-3" (ngSubmit)="search()" aria-label="Buscar en las existencias">
            <span class="p-input-icon-left">
              <i class="pi pi-search"></i>
              <input pInputText name="q" [(ngModel)]="draft" autocomplete="off" maxlength="100" placeholder="Código o nombre…" data-testid="stk-q" />
            </span>
            <div class="flex align-items-center gap-2">
              <p-checkbox name="only" data-testid="stk-only-diff" [ngModel]="onlyDiff()" (ngModelChange)="setOnlyDiff($event)" [binary]="true" inputId="only-diff" />
              <label for="only-diff" class="check-label">Solo productos con diferencia</label>
            </div>
            <p-button type="submit" label="Buscar" icon="pi pi-search" [outlined]="true" size="small" data-testid="stk-search" />
            <p-button type="button" label="Cómo leer la tabla" [link]="true" icon="pi pi-info-circle" (onClick)="showLegend()" data-testid="stk-legend-open" />
          </form>
        </div>
      }

      <app-state-panel [state]="l.state()" emptyText="Todavía no hay una existencia reconstruida cargada." (retry)="l.reload()">
        @if (data(); as d) {
          @if (d.items.length === 0) {
            <p-message severity="info" text="Ningún producto coincide con la búsqueda o el filtro elegido." data-testid="stk-no-match" styleClass="w-full my-3" />
          } @else {
            <p-table [value]="d.items" [scrollable]="true" scrollHeight="75vh" styleClass="p-datatable-sm p-datatable-striped" data-testid="stk-table">
              <ng-template #header>
                <tr>
                  <th pFrozenColumn style="min-width: 16rem">Producto</th>
                  <th class="text-right" style="min-width: 8rem">Conteo {{ baseShort() }}</th>
                  <th class="text-right" style="min-width: 6rem">Entradas</th>
                  <th class="text-right" style="min-width: 6rem">Salidas</th>
                  <th class="text-right" style="min-width: 10rem">Existencia al {{ closingShort() }}</th>
                  <th style="min-width: 16rem">Diferencia</th>
                </tr>
              </ng-template>
              <ng-template #body let-r>
                <tr [attr.data-sku]="r.producto_id">
                  <td pFrozenColumn><strong>{{ r.producto_id }}</strong> {{ r.producto }} <span class="muted text-sm"> · {{ r.unidad_descripcion || NOT_REPORTED }}</span></td>
                  <td class="text-right">{{ qty(r.base_count) }}</td>
                  <td class="text-right">{{ qty(r.movements?.entradas_cierre) }}</td>
                  <td class="text-right">{{ qty(r.movements?.salidas_cierre) }}</td>
                  <td class="text-right">{{ qty(r.libre) }}</td>
                  <td>
                    @if (r.discrepancy; as x) {
                      <p-tag severity="warn" value="Diferencia con el sistema" data-testid="stk-diff-chip" />
                      <span class="text-sm ml-2" data-testid="stk-diff-text">{{ diffText(r, x.difference, x.compared_at_local) }}</span>
                    }
                  </td>
                </tr>
              </ng-template>
            </p-table>
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
            <li>La existencia del plan es la del cierre del {{ closingDay() }}. La comparación con el stock que indica el sistema se hace en la fecha del último movimiento ({{ lastMovement() || 'no informado' }}); esos movimientos posteriores al cierre no se suman a la existencia del plan.</li>
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
    .orders-row { display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.2rem 1rem; margin: 0.2rem 0; }
    .filter-bar { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); padding: 0.6rem 1rem; margin: 0.6rem 0; }
    .check-label { font-weight: 500; cursor: pointer; }
    .table-meta { margin: 0.3rem 0; }
    .fold > summary { cursor: pointer; }
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

  diffText(r: StockItem, diff: number, at: string | undefined): string {
    const when = at ? stampWords(at) : 'la fecha del último movimiento';
    return `El sistema indica ${qty(r.system_stock_at_last_movement)} y la reconstrucción ${qty(r.reconstructed_at_last_movement)} al ${when} `
      + `(diferencia ${fmtInt(diff, true)}). Sin explicar: pendiente de confirmar con la empresa; no se ajustó ninguna cantidad.`;
  }

  setOnlyDiff(v: boolean) { this.onlyDiff.set(!!v); this.page.set(1); this.l.reload(); }
  search() { this.q.set(this.draft.trim()); this.page.set(1); this.l.reload(); }
  go(p: number) { this.page.set(p); this.l.reload(); }
}
