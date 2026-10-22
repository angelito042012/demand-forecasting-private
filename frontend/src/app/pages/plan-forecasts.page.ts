import { Component, computed, effect, inject, signal, untracked } from '@angular/core';
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
    <app-page-header title="Ventas previstas"
      lead="Cuántas unidades se estima vender de cada producto en el mes del plan de compra vigente." />

    <app-state-panel [state]="store.state()" emptyText="Todavía no se generó un plan de compra, así que no hay ventas previstas para mostrar." (retry)="store.reload()">
      @if (cur(); as c) {
        <section class="surface" aria-labelledby="h-fc-src" data-testid="fc-source">
          <h2 id="h-fc-src">Plan vigente: {{ monthText() }}</h2>
          <p data-testid="fc-version"><strong>Versión {{ c.ref.version ?? '—' }}</strong> · creado el {{ stamp(c.ref.created_at) }} · decisión de compra el {{ date(c.header.params?.decision_date ?? c.ref.decision_date) }}.
            Es el mismo plan que se abre por defecto en «Compra recomendada».</p>
          <ul class="plain" data-testid="fc-provenance">
            <li data-testid="fc-sales"><span class="chip ok">Dato real</span> Ventas registradas hasta el <strong>{{ longDate(cutoff()) }}</strong>.</li>
            <li data-testid="fc-stock"><span class="chip">Dato de la empresa</span> {{ stockText() }}</li>
            <li data-testid="fc-projection"><span class="chip warn">Proyección</span> Calculada con el promedio de los últimos 28 días de ventas válidas; no son ventas observadas y pueden estar limitadas por falta de stock.</li>
            <li data-testid="fc-assumption"><span class="chip info">Supuesto</span> Lo ocurrido después del corte es desconocido, no cero. La cantidad a comprar se explica en «Compra recomendada».</li>
          </ul>
        </section>
      }
    </app-state-panel>

    @if (forbidden()) {
      <p class="notice danger" role="alert" data-testid="fc-forbidden">No tienes permiso para ver las ventas previstas. Ingresa con otro usuario o avisa al administrador.</p>
    } @else if (cur()) {
      <section class="toolbar" aria-label="Filtros de ventas previstas" data-testid="fc-filters">
        <form class="filters" (ngSubmit)="search()" aria-label="Buscar productos">
          <label>Código o nombre <input name="q" [(ngModel)]="draft" autocomplete="off" maxlength="100" data-testid="fc-q" /></label>
          <label>Ordenar por
            <select name="sort" data-testid="fc-sort" [ngModel]="sort()" (ngModelChange)="setSort($event)">
              @for (o of sorts; track o.value) { <option [value]="o.value">{{ o.label }}</option> }
            </select>
          </label>
          <button type="submit" class="btn small" data-testid="fc-search">Buscar</button>
        </form>
      </section>

      <app-state-panel [state]="res.state()" emptyText="Este plan no tiene productos." (retry)="res.reload()">
        @if (results(); as d) {
          @if (d.items.length === 0) {
            <p class="state" data-testid="fc-no-match">Ningún producto coincide con la búsqueda.</p>
          } @else {
            <p class="muted" data-testid="fc-summary">{{ d.total }} productos en este plan.</p>
            <div class="table-wrap" tabindex="0" role="region" aria-label="Ventas previstas por producto">
              <table data-testid="fc-table">
                <thead><tr>
                  <th scope="col">Producto y presentación</th>
                  <th scope="col" class="num">Ventas previstas del mes <small>(sin limitar por stock)</small></th>
                  <th scope="col" class="num">Ventas previstas por día</th>
                  <th scope="col">Ventana de 28 días</th>
                  <th scope="col" class="num">Existencia inicial <small>({{ stockDay() }})</small></th>
                  <th scope="col">Compra</th>
                </tr></thead>
                <tbody>
                  @for (r of d.items; track r.producto_id) {
                    <tr [attr.data-sku]="r.producto_id">
                      <td data-col="product"><strong data-col="code">{{ r.producto_id }}</strong> {{ r.producto }}
                        <span class="muted"> · {{ r.unidad_descripcion || NOT_REPORTED }}</span></td>
                      <td class="num" data-col="forecast">{{ qty(r.forecast?.month_total) }}</td>
                      <td class="num" data-col="daily">{{ qty(r.forecast?.daily) }}</td>
                      <td data-col="window">
                        @if (r.forecast?.window_start && r.forecast?.window_end) {
                          {{ date(r.forecast?.window_start) }} al {{ date(r.forecast?.window_end) }}{{ r.forecast?.days_valid !== undefined ? ' · ' + r.forecast?.days_valid + ' días válidos' : '' }}
                        } @else { {{ NOT_COMPUTABLE }} }
                      </td>
                      <td class="num" data-col="stock">{{ qty(r.count_stock.libre, NOT_REPORTED) }}</td>
                      <td><a class="small" [routerLink]="['/planificar']" [queryParams]="{ q: r.producto_id }" data-testid="fc-to-plan" [attr.aria-label]="'Ver compra recomendada de ' + r.producto">Ver compra recomendada</a></td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          }
          <app-pager [page]="d.page" [pageSize]="d.page_size" [total]="d.total" [hasMore]="d.has_more" (go)="go($event)" />
          <p class="muted" data-testid="fc-units-note">Las cantidades están en la presentación indicada de cada producto; no se multiplicaron, por eso no hay un total general.</p>
        }
      </app-state-panel>
    }

    <p class="muted" data-testid="fc-academic">¿Buscas la evaluación histórica con datos del ejemplo? Está en
      <a [routerLink]="['/evaluacion/ventas-previstas']" data-testid="fc-to-academic">Evaluación académica: ventas previstas</a>.</p>
  `,
})
export class PlanForecastsPage {
  private api = inject(ApiService);
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
      ? `Existencia inicial reconstruida al cierre del ${day} (conteo informado por la empresa más movimientos del sistema).`
      : `Existencia inicial según el conteo informado por la empresa el ${day}.`;
  });
  stamp = (iso: string | undefined) => localStamp(iso)?.replace(', ', ' a las ') ?? 'fecha no informada';

  constructor() {
    this.store.ensure();
    // Cuando el plan vigente se resuelve, se piden sus resultados (las mismas filas que ve «Compra recomendada»).
    effect(() => { const id = this.cur()?.ref.plan_id; if (id) untracked(() => this.res.reload()); });
  }

  search() { this.q.set(this.draft.trim()); this.page.set(1); this.res.reload(); }
  setSort(v: string) { this.sort.set(v); this.page.set(1); this.res.reload(); }
  go(p: number) { this.page.set(p); this.res.reload(); }
}
