import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService, ForecastQuery } from '../core/api.service';
import { load } from '../core/load';
import { ForecastItem, Page, RunSummary } from '../core/models';
import { StatePanel } from '../ui/state-panel';
import { Pager } from '../ui/pager';
import { RunBanner } from '../ui/notices';

@Component({
  selector: 'app-forecasts-page',
  imports: [StatePanel, Pager, FormsModule, RunBanner],
  template: `
    <h2>Pronósticos</h2>
    @if (activeRun(); as r) {
      <app-run-banner [runLabel]="r.run_label" [cutoff]="r.cutoff" [age]="r.age_days_at_view" />
    }
    <p class="info">
      Cantidades en unidad base. Los valores «observado» existen solo porque la corrida es un backtest histórico (ventas
      observadas en Excel; pueden estar limitadas por stock). Método elegido: promedio_28. «rf_categoria_distribuido» es un
      comparador experimental que no ganó; «cero» es solo una referencia de control. Los pronósticos no incluyen agosto.
    </p>
    <form class="filters" (ngSubmit)="apply()">
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
          <p class="warn" data-testid="insufficient">Datos insuficientes para evaluar algunas filas: se marcan «no evaluable» y no cuentan para la comparación.</p>
        }
        <table data-testid="forecast-table">
          <thead>
            <tr><th>Entidad</th><th>Categoría</th><th>Cohorte</th><th>Fecha objetivo</th><th>h</th>
              <th>promedio_28 (elegido)</th><th>RF distribuido (comparador)</th><th>cero (control)</th><th>Observado</th><th>Evaluable</th></tr>
          </thead>
          <tbody>
            @for (x of d.items; track x.entity_id + x.target_date) {
              <tr>
                <td>{{ x.entity_id }}</td><td>{{ x.categoria ?? '—' }}</td><td>{{ x.cohorte ?? '—' }}</td><td>{{ x.target_date }}</td><td>{{ x.h }}</td>
                <td>{{ x.pred.promedio_28 }}</td><td>{{ x.pred.rf_categoria_distribuido }}</td><td>{{ x.pred.cero }}</td>
                <td>{{ x.observed ?? '—' }}</td><td>{{ x.evaluable ? 'Sí' : 'No' }}</td>
              </tr>
            }
          </tbody>
        </table>
        <app-pager [page]="d.page" [pageSize]="d.page_size" [total]="d.total" [hasMore]="d.has_more" (go)="go($event)" />
      }
    </app-state-panel>
  `,
  styles: `
    .info { background: #e2e3e5; padding: 0.4rem 0.7rem; border-radius: 4px; }
    .filters { display: flex; flex-wrap: wrap; gap: 0.8rem; align-items: end; margin: 0.6rem 0; } label { display: grid; gap: 0.2rem; }
    .warn { color: #664d03; } table { display: block; overflow-x: auto; }
  `,
})
export class ForecastsPage {
  private api = inject(ApiService);
  f = { level: 'sku' as 'sku' | 'categoria', sku: '', categoria: '', cohorte: '', from: '', to: '', sort: 'target_date' };
  private page = signal(1);
  private pageSize = 50;
  private q = signal<ForecastQuery>({ level: 'sku', page: 1, page_size: this.pageSize, sort: 'target_date' });

  l = load<Page<ForecastItem>>(() => this.api.forecasts(this.q()), (d) => d.items.length === 0);
  data = computed(() => { const s = this.l.state(); return s.kind === 'data' ? s.data : null; });
  insufficient = computed(() => (this.data()?.items ?? []).some((x) => !x.evaluable));
  run = load<Page<RunSummary>>(() => this.api.runs(1, 50), () => false);
  activeRun = computed(() => {
    const s = this.run.state();
    return s.kind === 'data' ? (s.data.items.find((r) => r.is_active) ?? null) : null;
  });

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
