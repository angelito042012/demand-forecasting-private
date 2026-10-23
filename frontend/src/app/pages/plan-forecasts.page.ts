import { DOCUMENT } from '@angular/common';
import { Component, DestroyRef, computed, effect, inject, signal, untracked } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService } from '../core/api.service';
import { CurrentPlanStore } from '../core/current-plan.store';
import { load } from '../core/load';
import { PlanResultsPage } from '../core/models';
import { fmtDate } from '../core/format';
import { longDate, monthName } from '../core/ux-text';
import { PageHeader } from '../ui/page-header';
import { StatePanel } from '../ui/state-panel';
import { Pager } from '../ui/pager';
import { NOT_COMPUTABLE, NOT_REPORTED, qtyText } from './plan-text';
import { localStamp } from './inventory.page';
import { useWideMain } from '../core/wide-main';

const SORTS: { value: string; label: string }[] = [
  { value: 'producto_id', label: 'Código (menor a mayor)' },
  { value: '-producto_id', label: 'Código (mayor a menor)' },
  { value: 'producto', label: 'Producto (A a Z)' },
  { value: '-forecast', label: 'Ventas previstas (más a menos)' },
  { value: 'libre', label: 'Existencias (menos a más)' },
];

/**
 * «Ventas previstas» del plan vigente: lee los resultados YA calculados del plan (misma fuente que «Compra recomendada»).
 * Ninguna cifra se calcula en el navegador.
 */
@Component({
  selector: 'app-plan-forecasts-page',
  imports: [FormsModule, RouterLink, PageHeader, StatePanel, Pager],
  template: `
    <app-page-header title="Ventas previstas" />

    <app-state-panel [state]="store.state()" emptyText="Todavía no se generó un plan de compra, así que no hay ventas previstas para mostrar." (retry)="store.reload()">
      @if (cur(); as c) {
        <p class="notice info compact" data-testid="fc-notice" role="note"><strong>Plan de {{ monthText() }} vigente.</strong> La previsión es una proyección bajo supuestos, no ventas observadas.</p>
        <section class="surface compact-card" aria-label="Plan vigente" data-testid="fc-source">
          <p data-testid="fc-version"><strong>Versión {{ c.ref.version ?? '—' }}</strong> · creado el {{ stamp(c.ref.created_at) }} · decisión de compra el {{ date(c.header.params?.decision_date ?? c.ref.decision_date) }} · mismo plan que «Compra recomendada».</p>
          <ul class="plain provenance" data-testid="fc-provenance">
            <li data-testid="fc-sales"><span class="chip ok">Dato real</span> Ventas registradas hasta el <strong>{{ longDate(cutoff()) }}</strong>.</li>
            <li data-testid="fc-stock"><span class="chip">Dato de la empresa</span> {{ stockText() }}</li>
            <li data-testid="fc-projection"><span class="chip warn">Proyección</span> Promedio de los últimos 28 días de ventas válidas; no son ventas observadas.</li>
            <li data-testid="fc-assumption"><span class="chip info">Supuesto</span> Lo ocurrido después del corte es desconocido, no cero.</li>
          </ul>
        </section>
      }
    </app-state-panel>

    @if (forbidden()) {
      <p class="notice danger" role="alert" data-testid="fc-forbidden">No tienes permiso para ver las ventas previstas. Ingresa con otro usuario o avisa al administrador.</p>
    } @else if (cur()) {
      <section class="toolbar compact-bar" aria-label="Filtros de ventas previstas" data-testid="fc-filters">
        <form class="filters" (ngSubmit)="search()" aria-label="Buscar productos">
          <label><span class="sr-only">Código o nombre</span><input name="q" [(ngModel)]="draft" autocomplete="off" maxlength="100" placeholder="Código o nombre…" data-testid="fc-q" /></label>
          <label>Orden
            <select name="sort" data-testid="fc-sort" [ngModel]="sort()" (ngModelChange)="setSort($event)">
              @for (o of sorts; track o.value) { <option [value]="o.value">{{ o.label }}</option> }
            </select>
          </label>
          <button type="submit" class="btn small" data-testid="fc-search">Buscar</button>
          <button type="button" class="link-btn legend-link" data-testid="fc-legend-open" (click)="showLegend()">Cómo leer la tabla</button>
        </form>
      </section>

      <app-state-panel [state]="res.state()" emptyText="Este plan no tiene productos." (retry)="res.reload()">
        @if (results(); as d) {
          @if (d.items.length === 0) {
            <p class="state" data-testid="fc-no-match">Ningún producto coincide con la búsqueda.</p>
          } @else {
            <div class="table-wrap fc-wrap" tabindex="0" role="region" aria-label="Ventas previstas por producto. Si no caben todas las columnas, desplázate hacia los lados.">
              <table data-testid="fc-table" class="fc-table">
                <thead><tr>
                  <th scope="col" class="sticky-col">Producto</th>
                  <th scope="col" class="num">Venta prevista del mes</th>
                  <th scope="col" class="num">Por día</th>
                  <th scope="col">Últimos 28 días</th>
                  <th scope="col" class="num">Existencias</th>
                  <th scope="col">Compra</th>
                </tr></thead>
                <tbody>
                  @for (r of d.items; track r.producto_id) {
                    <tr [attr.data-sku]="r.producto_id">
                      <td data-col="product" class="sticky-col"><strong data-col="code">{{ r.producto_id }}</strong> {{ r.producto }}
                        <span class="muted unit"> · {{ r.unidad_descripcion || NOT_REPORTED }}</span></td>
                      <td class="num" data-col="forecast">{{ qty(r.forecast?.month_total) }}</td>
                      <td class="num" data-col="daily">{{ qty(r.forecast?.daily) }}</td>
                      <td data-col="window">
                        @if (r.forecast?.window_start && r.forecast?.window_end) {
                          {{ date(r.forecast?.window_start) }} al {{ date(r.forecast?.window_end) }}{{ r.forecast?.days_valid !== undefined ? ' · ' + r.forecast?.days_valid + ' días válidos' : '' }}
                        } @else { {{ NOT_COMPUTABLE }} }
                      </td>
                      <td class="num" data-col="stock">{{ qty(r.count_stock.libre, NOT_REPORTED) }}</td>
                      <td><a class="small" [routerLink]="['/planificar']" [queryParams]="{ q: r.producto_id }" data-testid="fc-to-plan" [attr.aria-label]="'Ver compra recomendada de ' + r.producto">Ver compra</a></td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          }
          <app-pager [page]="d.page" [pageSize]="d.page_size" [total]="d.total" [hasMore]="d.has_more" (go)="go($event)" />
          <p class="muted table-meta" data-testid="fc-summary">{{ d.total }} {{ d.total === 1 ? 'producto' : 'productos' }} en este plan.</p>
          <details class="help fold" data-testid="fc-legend" [open]="legendOpen()" (toggle)="legendOpen.set($any($event.target).open)">
            <summary>Cómo leer la tabla</summary>
            <ul class="plain">
              <li><strong>Venta prevista del mes:</strong> unidades que se estima vender en el mes, <strong>sin limitar por stock</strong>.</li>
              <li><strong>Por día:</strong> promedio diario usado para la previsión.</li>
              <li><strong>Últimos 28 días:</strong> ventana de ventas válidas que alimenta el promedio; no son ventas observadas del mes previsto y pueden estar limitadas por falta de stock.</li>
              <li><strong>Existencias:</strong> {{ stockText() }}</li>
              <li data-testid="fc-units-note">Las cantidades están en la presentación indicada de cada producto; no se multiplicaron, por eso no hay un total general.</li>
              <li>La cantidad a comprar se explica en «Compra recomendada».</li>
            </ul>
          </details>
        }
      </app-state-panel>
    }

    <p class="muted" data-testid="fc-academic">¿Buscas la evaluación histórica con datos del ejemplo? Está en
      <a [routerLink]="['/evaluacion/ventas-previstas']" data-testid="fc-to-academic">Evaluación académica: ventas previstas</a>.</p>
  `,
  styles: `
    .sr-only { position: absolute; width: 1px; height: 1px; margin: -1px; padding: 0; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0; }
    :host ::ng-deep .ph { margin: 0 0 0.4rem; }
    :host ::ng-deep .ph h1 { margin: 0; }
    .compact { padding: 0.4rem 0.9rem; margin: 0.4rem 0; font-size: 0.95rem; }
    .compact-card { padding: 0.35rem 0.9rem; margin: 0 0 0.4rem; font-size: 0.95rem; }
    .compact-card p { margin: 0.25rem 0; }
    .provenance { margin: 0.2rem 0; }
    .provenance li { margin: 0.15rem 0; }
    .compact-bar { margin: 0.4rem 0; padding: 0.4rem 0.9rem; }
    .compact-bar .filters { gap: 0.4rem 1rem; align-items: center; }
    .compact-bar label { display: flex; align-items: center; gap: 0.4rem; font-size: 0.95rem; }
    .compact-bar input { width: 12rem; min-height: 2.2rem; }
    .compact-bar select { min-height: 2.2rem; }
    .link-btn { background: none; border: 0; padding: 0; color: var(--link); text-decoration: underline; cursor: pointer; font: inherit; min-height: 0; }
    .legend-link { margin-left: auto; }
    .fc-wrap { max-height: none; margin: 0.4rem 0; }
    .fc-table { width: 100%; min-width: 52rem; font-size: 0.95rem; }
    .fc-table th, .fc-table td { padding: 0.4rem 0.5rem; }
    .fc-table thead th { white-space: normal; vertical-align: bottom; line-height: 1.25; position: static; }
    .fc-table td.num { white-space: normal; }
    .fc-table .sticky-col { position: sticky; left: 0; background: var(--surface); width: 20rem; min-width: 12rem; max-width: 24rem; box-shadow: 1px 0 0 var(--line); z-index: 2; }
    .fc-table thead th.sticky-col { z-index: 4; background: #e8ecf2; }
    .fc-table .unit { font-size: 0.9rem; }
    .table-meta { margin: 0.3rem 0; }
    .fold > summary { cursor: pointer; }
  `,
})
export class PlanForecastsPage {
  private api = inject(ApiService);
  private doc = inject(DOCUMENT);
  private destroyRef = inject(DestroyRef);
  readonly store = inject(CurrentPlanStore);
  readonly sorts = SORTS;
  readonly NOT_COMPUTABLE = NOT_COMPUTABLE;
  readonly NOT_REPORTED = NOT_REPORTED;
  readonly qty = qtyText;
  readonly longDate = longDate;
  readonly date = (iso: string | null | undefined) => fmtDate(iso);
  readonly pageSize = 50;

  q = signal('');
  draft = '';
  sort = signal('producto_id');
  page = signal(1);

  cur = this.store.plan;
  res = load<PlanResultsPage>(
    () => this.api.planResults(this.cur()!.ref.plan_id, { q: this.q(), sort: this.sort(), page: this.page(), page_size: this.pageSize }),
    () => false, false,
  );
  results = computed(() => { const s = this.res.state(); return s.kind === 'data' ? s.data : null; });
  forbidden = computed(() => [this.store.state(), this.res.state()]
    .some((s) => s.kind === 'error' && (s.error.status === 403 || s.error.code === 'PROHIBIDO')));

  cutoff = computed(() => { const h = this.cur()?.header; return h?.dates?.sales_cutoff ?? h?.dataset?.sales_cutoff ?? null; });
  monthText = computed(() => { const m = this.cur()?.month; const n = m ? monthName(`${m}-01`) : ''; return m ? (n ? `${n} de ${m.slice(0, 4)}` : m) : ''; });
  stockDay = computed(() => (localStamp(this.cur()?.header.snapshot?.as_of_local)?.split(',')[0]) ?? 'fecha no informada');
  stockText = computed(() => {
    const sn = this.cur()?.header.snapshot;
    const day = this.stockDay();
    return sn?.kind === 'RECONSTRUIDO'
      ? `Existencia inicial reconstruida al cierre del ${day} (conteo informado + movimientos del sistema).`
      : `Existencia inicial según el conteo informado por la empresa el ${day}.`;
  });
  stamp = (iso: string | undefined) => localStamp(iso)?.replace(', ', ' a las ') ?? 'fecha no informada';

  legendOpen = signal(false);
  showLegend() {
    this.legendOpen.set(true);
    setTimeout(() => { const d = this.doc.querySelector('[data-testid="fc-legend"]') as HTMLElement | null; d?.scrollIntoView?.({ block: 'center' }); (d?.querySelector('summary') as HTMLElement | null)?.focus(); }, 0);
  }

  constructor() {
    useWideMain(this.doc, this.destroyRef);
    this.store.ensure();
    // Cuando el plan vigente se resuelve, se piden sus resultados (las mismas filas que ve «Compra recomendada»).
    effect(() => { const id = this.cur()?.ref.plan_id; if (id) untracked(() => this.res.reload()); });
  }

  search() { this.q.set(this.draft.trim()); this.page.set(1); this.res.reload(); }
  setSort(v: string) { this.sort.set(v); this.page.set(1); this.res.reload(); }
  go(p: number) { this.page.set(p); this.res.reload(); }
}
