import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { RunChoice, isGenerated, kindLabel } from '../core/run-choice';
import { FormsModule } from '@angular/forms';
import { ApiService, ForecastQuery } from '../core/api.service';
import { load } from '../core/load';
import { ForecastItem, Page, RunSummary } from '../core/models';
import { StatePanel } from '../ui/state-panel';
import { Pager } from '../ui/pager';
import { fmtDate, fmtDec } from '../core/format';

export const NA = 'no disponible para esta corrida';
import { RunBanner, SupersededBanner } from '../ui/notices';

@Component({
  selector: 'app-forecasts-page',
  imports: [StatePanel, Pager, FormsModule, RunBanner, SupersededBanner],
  template: `
    <h2>Pronósticos</h2>
    @if (runs().length) {
      <label>Corrida
        <select data-testid="run-select" aria-label="Corrida" (change)="choice.set($any($event.target).value)">
          @for (r of runs(); track r.run_id) {
            <option [value]="r.run_id" [selected]="r.run_id === shownRun()?.run_id">{{ r.run_label }} · {{ kind(r.kind) }}{{ r.is_active ? ' · activa' : '' }}</option>
          }
        </select>
      </label>
      <span class="muted" data-testid="run-choice-note">La corrida elegida se conserva en Recomendaciones y Comparación (parámetro «run» de la dirección).</span>
    }
    @if (shownRun(); as r) {
      <app-superseded-banner [run]="r" />
      <app-run-banner [runLabel]="r.run_label" [cutoff]="r.cutoff" [age]="r.age_days_at_view" />
      @if (r.origin || r.target_start) {
        <p data-testid="run-dates">Origen: <strong>{{ d(r.origin ?? r.cutoff) }}</strong>@if (r.target_start) { · fechas objetivo: <strong>{{ d(r.target_start) }} al {{ d(r.target_end) }}</strong> }</p>
      }
    }
    <p class="notice info" data-testid="forecast-note">
      Cantidades en unidad base. Método elegido: promedio_28.
      @if (generated()) {
        Corrida generada por la aplicación: no hay ventas observadas posteriores al origen, por eso «observado» y «evaluable» figuran «{{ na }}» (no son cero).
        El comparador RF solo aparece si la corrida lo publica.
      } @else {
        Los valores «observado» existen solo porque la corrida es un backtest histórico (ventas observadas en Excel; pueden estar limitadas por stock).
        «rf_categoria_distribuido» es un comparador experimental que no ganó.
      }
      «cero» es solo una referencia de control. Los pronósticos no incluyen agosto.
    </p>
    <form class="filters" (ngSubmit)="apply()" aria-label="Filtros de pronósticos">
      <label>Nivel
        <select name="level" [(ngModel)]="f.level"><option value="sku">SKU</option><option value="categoria">Categoría</option></select>
      </label>
      <label>SKU <input name="sku" [(ngModel)]="f.sku" /></label>
      <label>Categoría <input name="cat" [(ngModel)]="f.categoria" /></label>
      <label>Cohorte <input name="coh" [(ngModel)]="f.cohorte" /></label>
      <label>Desde <input type="date" name="from" [(ngModel)]="f.from" max="2026-07-31" /></label>
      <label>Hasta <input type="date" name="to" [(ngModel)]="f.to" max="2026-07-31" /></label>
      <label>Orden
        <select name="sort" [(ngModel)]="f.sort">
          <option value="target_date">Fecha objetivo ↑</option><option value="-target_date">Fecha objetivo ↓</option>
          <option value="entity_id">Entidad ↑</option><option value="-entity_id">Entidad ↓</option>
          <option value="-pred_chosen">Pronóstico elegido ↓</option><option value="pred_chosen">Pronóstico elegido ↑</option>
        </select>
      </label>
      <button type="submit">Filtrar</button>
    </form>
    <app-state-panel [state]="l.state()" emptyText="Sin pronósticos para estos filtros." (retry)="l.reload()">
      @if (data(); as d) {
        @if (insufficient()) {
          <p class="notice warn" data-testid="insufficient">Datos insuficientes para evaluar algunas filas: se marcan «no evaluable» y no cuentan para la comparación.</p>
        }
        <div class="table-wrap" tabindex="0" role="region" aria-label="Tabla de pronósticos">
        <table data-testid="forecast-table">
          <thead>
            <tr><th scope="col">Entidad</th><th scope="col">Categoría</th><th scope="col">Cohorte</th><th scope="col">Fecha objetivo</th><th scope="col" class="num">h</th>
              <th scope="col" class="num">promedio_28 (elegido)</th>@if (hasRf()) { <th scope="col" class="num">RF distribuido (comparador)</th> }<th scope="col" class="num">cero (control)</th><th scope="col" class="num">Observado</th><th scope="col">Evaluable</th></tr>
          </thead>
          <tbody>
            @for (x of d.items; track x.entity_id + x.target_date) {
              <tr>
                <td>{{ x.entity_id }}</td><td>{{ x.categoria ?? '—' }}</td><td>{{ x.cohorte ?? '—' }}</td><td>{{ x.target_date }}</td><td class="num">{{ x.h }}</td>
                <td class="num">{{ dec(x.pred.promedio_28) }}</td>@if (hasRf()) { <td class="num">{{ x.pred.rf_categoria_distribuido === null ? na : dec(x.pred.rf_categoria_distribuido) }}</td> }<td class="num">{{ dec(x.pred.cero) }}</td>
                <td class="num" data-testid="observed">{{ x.observed === null || x.observed === undefined ? na : dec(x.observed) }}</td><td data-testid="evaluable">{{ x.evaluable === null || x.evaluable === undefined ? na : x.evaluable ? 'Sí' : 'No' }}</td>
              </tr>
            }
          </tbody>
        </table>
        </div>
        <app-pager [page]="d.page" [pageSize]="d.page_size" [total]="d.total" [hasMore]="d.has_more" (go)="go($event)" />
      }
    </app-state-panel>
  `,
})
export class ForecastsPage {
  private api = inject(ApiService);
  dec = (v: unknown) => fmtDec(v);
  na = NA;
  d = (v: string | undefined | null) => fmtDate(v);
  kind = (k: string | undefined) => kindLabel(k);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);
  /** Corrida elegida (parámetro de URL «run»); sin él, la activa. */
  choice = new RunChoice(this.route, this.router, this.destroyRef, () => { this.page.set(1); this.l.reload(); });
  f = { level: 'sku' as 'sku' | 'categoria', sku: '', categoria: '', cohorte: '', from: '', to: '', sort: 'target_date' };
  private page = signal(1);
  private pageSize = 50;
  private q = signal<ForecastQuery>({ level: 'sku', page: 1, page_size: this.pageSize, sort: 'target_date' });

  l = load<Page<ForecastItem>>(() => this.api.forecasts({ ...this.q(), run_id: this.choice.id() ?? undefined }), (d) => d.items.length === 0);
  data = computed(() => { const s = this.l.state(); return s.kind === 'data' ? s.data : null; });
  insufficient = computed(() => !this.generated() && (this.data()?.items ?? []).some((x) => x.evaluable === false || (x.evaluable === null && x.observed !== null)));
  /** El comparador RF solo se muestra si alguna fila trae valores. */
  hasRf = computed(() => (this.data()?.items ?? []).some((x) => x.pred.rf_categoria_distribuido !== null && x.pred.rf_categoria_distribuido !== undefined));
  run = load<Page<RunSummary>>(() => this.api.runs(1, 50), () => false);
  runs = computed(() => { const s = this.run.state(); return s.kind === 'data' ? s.data.items : []; });
  /** La corrida mostrada: la elegida o, por defecto, la activa. */
  shownRun = computed(() => {
    const id = this.choice.id();
    const rs = this.runs();
    return (id ? rs.find((r) => r.run_id === id) : rs.find((r) => r.is_active)) ?? null;
  });
  generated = computed(() => isGenerated(this.shownRun()?.kind));

  private build(page: number): ForecastQuery {
    const t = (v: string) => v.trim() || undefined;
    return {
      level: this.f.level, sku: t(this.f.sku), categoria: t(this.f.categoria), cohorte: t(this.f.cohorte),
      from: this.f.from || undefined, to: this.f.to || undefined, sort: this.f.sort, page, page_size: this.pageSize,
    };
  }
  apply() { this.page.set(1); this.q.set(this.build(1)); this.l.reload(); }
  go(p: number) { this.page.set(p); this.q.set({ ...this.q(), page: p }); this.l.reload(); }
}
