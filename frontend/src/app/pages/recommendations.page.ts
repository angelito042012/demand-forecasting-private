import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService, RecoQuery } from '../core/api.service';
import { load } from '../core/load';
import { Page, Recommendation } from '../core/models';
import { calcSteps } from '../core/reco-calc';
import { StatePanel } from '../ui/state-panel';
import { Pager } from '../ui/pager';
import { SimNotice } from '../ui/notices';

@Component({
  selector: 'app-recommendations-page',
  imports: [StatePanel, Pager, FormsModule, SimNotice],
  template: `
    <h2>Recomendaciones de reposición (vista previa)</h2>
    <app-sim-notice [scenarioId]="scenarioId()" />
    <p class="info">
      Sugerencia hipotética calculada sobre una corrida histórica de desarrollo; no es un pedido ejecutado ni una compra real.
      Cantidades en «unidad base»; costos supuestos en PEN. La demanda usada es la venta observada, que puede estar limitada por stock.
    </p>
    <form class="filters" (ngSubmit)="apply()">
      <label>SKU <input name="sku" [(ngModel)]="f.sku" /></label>
      <label>Categoría <input name="cat" [(ngModel)]="f.categoria" /></label>
      <label>Estado
        <select name="status" [(ngModel)]="f.status">
          <option value="">Todos</option><option value="ok">Con inventario simulado</option><option value="sin_snapshot">Sin inventario simulado</option>
        </select>
      </label>
      <label class="chk"><input type="checkbox" name="only" [(ngModel)]="f.only_orders" /> Solo con pedido</label>
      <label>Orden
        <select name="sort" [(ngModel)]="f.sort">
          <option value="sku">SKU</option><option value="categoria">Categoría</option>
          <option value="-order_qty">Pedido ↓</option><option value="order_qty">Pedido ↑</option>
        </select>
      </label>
      <button type="submit">Filtrar</button>
    </form>
    <app-state-panel [state]="l.state()" emptyText="Sin recomendaciones para estos filtros." (retry)="l.reload()">
      @if (data(); as d) {
        <table data-testid="reco-table">
          <thead><tr><th>SKU</th><th>Categoría</th><th>Estado</th><th>Stock simulado</th><th>Tránsito simulado</th><th>Pedido (unidad base)</th><th>Valor del pedido (PEN, supuesto)</th><th></th></tr></thead>
          <tbody>
            @for (r of d.items; track r.sku + r.almacen) {
              @if (r.status === 'ok') {
                <tr>
                  <td>{{ r.sku }}</td><td>{{ r.categoria ?? '—' }}</td><td>Con inventario simulado</td><td>{{ r.on_hand }}</td><td>{{ r.in_transit }}</td>
                  <td>{{ r.order_qty }}</td><td>{{ r.order_value_assumed ?? '—' }}</td>
                  <td><button type="button" (click)="open(r)">Ver cálculo</button></td>
                </tr>
              } @else {
                <tr class="nosnap" data-testid="sin-snapshot">
                  <td>{{ r.sku }}</td><td>{{ r.categoria ?? '—' }}</td>
                  <td colspan="5">Sin inventario simulado al 10/07. {{ r.reason }}. No se supone stock cero.</td>
                  <td><button type="button" (click)="open(r)">Ver motivo</button></td>
                </tr>
              }
            }
          </tbody>
        </table>
        <app-pager [page]="d.page" [pageSize]="d.page_size" [total]="d.total" [hasMore]="d.has_more" (go)="go($event)" />
      }
    </app-state-panel>

    @if (selected(); as s) {
      <section class="detail" data-testid="reco-detail">
        <h3>Detalle de {{ s }}</h3>
        <app-state-panel [state]="detail.state()" (retry)="detail.reload()">
          @if (det(); as r) {
            <app-sim-notice [scenarioId]="r.scenario_id" />
            @if (calc(); as c) {
              <ol data-testid="calc-steps">
                @for (st of c.steps; track st.label) {
                  <li><strong>{{ st.label }}</strong>: {{ st.value }} {{ st.unit }} <small>({{ st.formula }})</small></li>
                }
              </ol>
              @if (!c.check.target || !c.check.position || !c.check.order) {
                <p class="warn" data-testid="incoherent">Los valores publicados no cuadran con la fórmula; revise la corrida antes de usarlos.</p>
              }
              <p>Costo unitario supuesto: {{ r.unit_cost_assumed }} {{ r.currency }} (65 % de la mediana de precio base hasta el 31/05).
                Valor del pedido supuesto: {{ r.order_value_assumed ?? '—' }} {{ r.currency }}.</p>
            } @else {
              <p class="warn" data-testid="detail-nosnap">Sin inventario simulado al 10/07. {{ r.reason }}. No se supone stock cero y no se calcula pedido.</p>
            }
            <p data-testid="reco-dates">
              Fecha del inventario simulado: {{ r.snapshot_date }} · origen del pronóstico: {{ r.origin }} ·
              pronóstico de {{ r.forecast_from }} a {{ r.forecast_to }} · plazo de entrega {{ r.lead_time_days }} d · revisión cada {{ r.review_days }} d ·
              modelo {{ r.model }} · almacén {{ r.almacen }}
            </p>
            @if (explanation(); as e) { <pre class="expl">{{ e }}</pre> }
          }
        </app-state-panel>
      </section>
    }
  `,
  styles: `
    .info { background: #e2e3e5; padding: 0.4rem 0.7rem; border-radius: 4px; }
    .filters { display: flex; flex-wrap: wrap; gap: 0.8rem; align-items: end; margin: 0.6rem 0; } label { display: grid; gap: 0.2rem; }
    .chk { display: flex; gap: 0.3rem; align-items: center; } .warn { color: #664d03; } .nosnap { background: #fff3cd; }
    table { display: block; overflow-x: auto; } .detail { margin-top: 1rem; border-top: 2px solid #ccc; } .expl { white-space: pre-wrap; background: #f8f9fa; padding: 0.5rem; }
  `,
})
export class RecommendationsPage {
  private api = inject(ApiService);
  f = { sku: '', categoria: '', status: '' as '' | 'ok' | 'sin_snapshot', only_orders: false, sort: 'sku' };
  private pageSize = 50;
  private q = signal<RecoQuery>({ page: 1, page_size: this.pageSize, sort: 'sku' });
  l = load<Page<Recommendation>>(() => this.api.recommendations(this.q()), (d) => d.items.length === 0);
  data = computed(() => { const s = this.l.state(); return s.kind === 'data' ? s.data : null; });
  scenarioId = computed(() => this.data()?.items[0]?.scenario_id ?? null);

  selected = signal<string | null>(null);
  private selAlmacen = '1';
  detail = load<Recommendation>(() => this.api.recommendation(this.selected()!, undefined, this.selAlmacen), () => false, false);
  det = computed(() => { const s = this.detail.state(); return s.kind === 'data' ? s.data : null; });
  calc = computed(() => { const r = this.det(); return r ? calcSteps(r) : null; });
  explanation = computed(() => {
    const e = this.det()?.explanation ?? this.det()?.explanation_steps;
    return Array.isArray(e) ? e.join('\n') : (e ?? null);
  });

  apply() {
    const t = (v: string) => v.trim() || undefined;
    this.q.set({ sku: t(this.f.sku), categoria: t(this.f.categoria), status: this.f.status, only_orders: this.f.only_orders, sort: this.f.sort, page: 1, page_size: this.pageSize });
    this.l.reload();
  }
  go(p: number) { this.q.set({ ...this.q(), page: p }); this.l.reload(); }
  open(r: Recommendation) { this.selAlmacen = r.almacen; this.selected.set(r.sku); this.detail.reload(); }
}
