import { Component, computed, inject, signal } from '@angular/core';
import { map, tap } from 'rxjs';
import { ApiService } from '../core/api.service';
import { load } from '../core/load';
import { BacktestDetail, BacktestItem, BacktestView, Page } from '../core/models';
import { StatePanel } from '../ui/state-panel';
import { SimNotice } from '../ui/notices';
import { DataTree } from '../ui/data-tree';

@Component({
  selector: 'app-comparison-page',
  imports: [StatePanel, SimNotice, DataTree],
  template: `
    <h2>Comparación de métodos y políticas (backtests T07)</h2>
    <app-sim-notice [scenarioId]="scenario()" />
    <section class="limits" data-testid="limits">
      <h3>Cómo leer esta pantalla</h3>
      <ul>
        <li>Backtest histórico de desarrollo (corrida al 10/07/2026), no una prueba final: agosto sigue reservado.</li>
        <li>El método elegido es <strong>promedio_28</strong>. El comparador experimental <strong>rf_categoria_distribuido</strong> no ganó.</li>
        <li>Más nivel de servicio viene con más stock y más compras: la mejora de un indicador no es una ganancia neta sin mirar su costo.</li>
        <li>Los 4 pliegues (folds) se solapan; el agregado no es una evaluación independiente.</li>
        <li>La simulación (nueve escenarios × 3 políticas = 27 combinaciones) usa inventario, costos y plazos supuestos; no evidencia una mejora real para la empresa.</li>
        <li>La venta observada puede estar limitada por stock; los faltantes reales son desconocidos.</li>
        <li>El MAPE se reporta con su cobertura; el R² queda indefinido cuando corresponde.</li>
      </ul>
    </section>
    <app-state-panel [state]="list.state()" emptyText="No hay backtests publicados." (retry)="list.reload()">
      <label>Backtest
        <select data-testid="bt-select" (change)="pick($any($event.target).value)">
          @for (b of items(); track b.backtest_id) {
            <option [value]="b.backtest_id" [selected]="b.backtest_id === chosen()">{{ b.label }} ({{ b.kind }})</option>
          }
        </select>
      </label>
      <label>Vista
        <select data-testid="bt-view" (change)="setView($any($event.target).value)">
          <option value="all" [selected]="view() === 'all'">Todo</option>
          <option value="predictive" [selected]="view() === 'predictive'">Predictivo</option>
          <option value="simulation" [selected]="view() === 'simulation'">Simulación de políticas</option>
        </select>
      </label>
    </app-state-panel>
    @if (chosen()) {
      <app-state-panel [state]="detail.state()" emptyText="Datos insuficientes: el backtest no publicó resultados." (retry)="detail.reload()">
        @if (det(); as d) {
          @if (d.disclaimer) { <p class="disc" data-testid="disclaimer">{{ d.disclaimer }}</p> }
          <p>Procedencia: <code>{{ d.provenance ?? 'sin dato' }}</code> · escenario: <code>{{ d.scenario_id ?? 'sin dato' }}</code></p>
          <app-data-tree [value]="d" />
        }
      </app-state-panel>
    }
  `,
  styles: `
    .limits { background: #f8f9fa; border: 1px solid #ddd; padding: 0 1rem; border-radius: 4px; margin: 0.6rem 0; }
    .disc { background: #fff3cd; padding: 0.4rem 0.7rem; } label { display: inline-grid; gap: 0.2rem; margin-right: 1rem; }
  `,
})
export class ComparisonPage {
  private api = inject(ApiService);
  chosen = signal<string | null>(null);
  view = signal<BacktestView>('all');
  list = load<BacktestItem[]>(
    () => this.api.backtests().pipe(map((r) => (Array.isArray(r) ? r : (r as Page<BacktestItem>).items)),
      // Selecciona el primer backtest al llegar la lista.
      tap((items) => { if (items.length && !this.chosen()) { this.chosen.set(items[0].backtest_id); queueMicrotask(() => this.detail.reload()); } }),
    ),
    (d) => d.length === 0,
  );
  items = computed(() => { const s = this.list.state(); return s.kind === 'data' ? s.data : []; });
  detail = load<BacktestDetail>(() => this.api.backtest(this.chosen()!, this.view()), (d) => Object.keys(d).length === 0, false);
  det = computed(() => { const s = this.detail.state(); return s.kind === 'data' ? s.data : null; });
  scenario = computed(() => this.det()?.scenario_id ?? null);

  pick(id: string) { this.chosen.set(id); this.detail.reload(); }
  setView(v: string) { this.view.set(v as BacktestView); this.detail.reload(); }
}
