import { Component, computed, inject, signal } from '@angular/core';
import { ApiService } from '../core/api.service';
import { load } from '../core/load';
import { Page, RunDetail, RunSummary } from '../core/models';
import { StatePanel } from '../ui/state-panel';
import { Pager } from '../ui/pager';
import { DataTree } from '../ui/data-tree';
import { RunBanner } from '../ui/notices';

@Component({
  selector: 'app-runs-page',
  imports: [StatePanel, Pager, DataTree, RunBanner],
  template: `
    <h2>Corridas</h2>
    <p class="info">Solo se listan corridas completas ya publicadas. El servidor no reentrena ni simula al consultar; ejecutar corridas desde la aplicación llega con T10.</p>
    <app-state-panel [state]="l.state()" emptyText="No hay corridas publicadas." (retry)="l.reload()">
      @if (data(); as d) {
        <table data-testid="runs-table">
          <thead><tr><th>Corrida</th><th>Etiqueta</th><th>Corte</th><th>Publicada</th><th>Antigüedad (días)</th><th>Activa</th><th></th></tr></thead>
          <tbody>
            @for (r of d.items; track r.run_id) {
              <tr>
                <td>{{ r.run_id }}</td><td>{{ r.run_label }}</td><td>{{ r.cutoff }}</td><td>{{ r.published_at }}</td>
                <td>{{ r.age_days_at_view }}</td><td>{{ r.is_active ? 'Sí' : 'No' }}</td>
                <td><button type="button" (click)="open(r)">Ver detalle</button></td>
              </tr>
            }
          </tbody>
        </table>
        <app-pager [page]="d.page" [pageSize]="d.page_size" [total]="d.total" [hasMore]="d.has_more" (go)="go($event)" />
      }
    </app-state-panel>
    @if (selected()) {
      <h3>Detalle de la corrida</h3>
      <app-state-panel [state]="detail.state()" (retry)="detail.reload()">
        @if (det(); as r) {
          <app-run-banner [runLabel]="r.run_label" [cutoff]="r.cutoff" [age]="r.age_days_at_view" />
          <h4>Método</h4>
          <ul data-testid="method">
            <li>Método elegido: <strong>{{ r.method.chosen }}</strong> (media móvil de 28 días).</li>
            <li><strong>{{ r.method.comparator }}</strong>: comparador experimental que no ganó frente al método elegido.</li>
            <li>Referencia de control: «{{ r.method.control }}» (pronóstico igual a cero, derivado).</li>
            @if (r.method.note) { <li>{{ r.method.note }}</li> }
          </ul>
          @if (r.coverage; as c) {
            <h4>Cobertura</h4>
            <ul data-testid="coverage">
              <li>SKU pronosticados: {{ c.skus_pronosticados }}</li>
              <li>SKU con recomendación: {{ c.skus_con_recomendacion }}</li>
              <li>SKU sin inventario simulado: {{ c.skus_sin_snapshot }}</li>
              <li>Categorías: {{ c.categorias }}</li>
            </ul>
          }
          <h4>Documento completo publicado</h4>
          <app-data-tree [value]="r" />
        }
      </app-state-panel>
    }
  `,
  styles: `.info { background: #e2e3e5; padding: 0.4rem 0.7rem; border-radius: 4px; } table { display: block; overflow-x: auto; }`,
})
export class RunsPage {
  private api = inject(ApiService);
  page = signal(1);
  pageSize = 50;
  l = load<Page<RunSummary>>(() => this.api.runs(this.page(), this.pageSize), (d) => d.items.length === 0);
  data = computed(() => { const s = this.l.state(); return s.kind === 'data' ? s.data : null; });
  selected = signal<string | null>(null);
  detail = load<RunDetail>(() => this.api.runDetail(this.selected()!), () => false, false);
  det = computed(() => { const s = this.detail.state(); return s.kind === 'data' ? s.data : null; });
  go(p: number) { this.page.set(p); this.l.reload(); }
  open(r: RunSummary) { this.selected.set(r.run_id); this.detail.reload(); }
}
