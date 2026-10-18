import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { RunChoice, kindLabel } from '../core/run-choice';
import { FormsModule } from '@angular/forms';
import { ApiService, RecoQuery } from '../core/api.service';
import { load } from '../core/load';
import { FINAL_UNAVAILABLE_REASON, RecoPage, Recommendation } from '../core/models';
import { calcSteps } from '../core/reco-calc';
import { DASH, fmtDate, fmtInt, fmtPen } from '../core/format';
import { StatePanel } from '../ui/state-panel';
import { Pager } from '../ui/pager';
import { RunBanner, SimNotice, SupersededBanner } from '../ui/notices';

@Component({
  selector: 'app-recommendations-page',
  imports: [StatePanel, Pager, FormsModule, SimNotice, RunBanner, SupersededBanner, RouterLink],
  template: `
    <h2>Recomendaciones de reposición (vista previa)</h2>
    <app-sim-notice [scenarioId]="scenarioId()" />
    @if (run(); as r) {
      <app-superseded-banner [run]="r" />
      <app-run-banner [runLabel]="r.run_label" [cutoff]="r.cutoff" [age]="r.age_days_at_view" [kind]="r.kind" />
    }
    @if (unavailable(); as u) {
      <section class="notice warn" data-testid="reco-unavailable" role="note" aria-labelledby="h-na">
        <h3 id="h-na">Esta corrida no tiene recomendaciones de compra</h3>
        <p>
          La corrida elegida es <strong>{{ kindText(run()?.kind) }}</strong>. Motivo publicado: <code data-testid="reco-reason-code">{{ u }}</code> —
          {{ reasonText(u) }} No se muestran existencias, pedidos ni valores de ningún otro día en su lugar.
        </p>
        @if (seeRun(); as sr) {
          <p><a [routerLink]="['/recomendaciones']" [queryParams]="{ run: sr }" data-testid="see-run">Ver la demostración histórica de recomendaciones</a>
            (<code>{{ sr }}</code>; inventario simulado, no es un pedido real).</p>
        } @else { <p class="muted" data-testid="no-see-run">La API no indicó una corrida histórica alternativa.</p> }
      </section>
    }
    @if (first(); as x) {
      <p data-testid="reco-header">Origen del pronóstico: <strong>{{ date(x.origin) }}</strong> · fechas objetivo: <strong>{{ date(x.forecast_from) }} al {{ date(x.forecast_to) }}</strong> ·
        inventario simulado al cierre del {{ date(x.snapshot_date) }}.
        <a [routerLink]="['/corridas']" data-testid="change-run">Cambiar de corrida</a>
        @if (choice.id()) { (corrida elegida en la dirección: <code>{{ choice.id() }}</code>) } @else { (corrida activa) }
      </p>
    }
    @if (!unavailable()) {
    <p class="notice info">
      Sugerencia hipotética calculada sobre la corrida seleccionada (histórica de desarrollo o generada por la aplicación); no es un pedido ejecutado ni una compra real.
      Cantidades en «unidad base»; costos supuestos en PEN. La demanda usada es la venta observada, que puede estar limitada por stock.
    </p>
    }
    @if (!unavailable()) {
    <form class="filters" (ngSubmit)="apply()" aria-label="Filtros de recomendaciones">
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
    }
    <app-state-panel [state]="l.state()" emptyText="Sin recomendaciones para estos filtros." (retry)="l.reload()">
      @if (data(); as d) {
       @if (!d.unavailable_reason) {
        <div class="table-wrap" tabindex="0" role="region" aria-label="Tabla de recomendaciones">
          <table data-testid="reco-table">
            <thead>
              <tr>
                <th scope="col">SKU</th><th scope="col">Categoría</th><th scope="col">Estado</th>
                <th scope="col" class="num">Stock simulado (unidades)</th><th scope="col" class="num">Tránsito simulado (unidades)</th>
                <th scope="col" class="num">Pedido (unidad base)</th><th scope="col" class="num">Valor del pedido (PEN, supuesto)</th>
                <th scope="col"><span class="sr-only">Acción</span></th>
              </tr>
            </thead>
            <tbody>
              @for (r of d.items; track r.sku + r.almacen) {
                @if (r.status === 'ok') {
                  <tr>
                    <td>{{ r.sku }}</td><td>{{ r.categoria ?? '—' }}</td><td>Con inventario simulado</td>
                    <td class="num">{{ int(r.on_hand) }}</td><td class="num">{{ int(r.in_transit) }}</td>
                    <td class="num">{{ int(r.order_qty) }}</td><td class="num">{{ pen(r.order_value_assumed) }}</td>
                    <td><button type="button" (click)="open(r)" [attr.aria-label]="'Ver cálculo del SKU ' + r.sku">Ver cálculo</button></td>
                  </tr>
                } @else {
                  <tr class="nosnap" data-testid="sin-snapshot">
                    <td>{{ r.sku }}</td><td>{{ r.categoria ?? '—' }}</td>
                    <td colspan="5">Sin inventario simulado al {{ dayMonth(r.snapshot_date) }}. {{ r.reason }}.</td>
                    <td><button type="button" (click)="open(r)" [attr.aria-label]="'Ver motivo del SKU ' + r.sku">Ver motivo</button></td>
                  </tr>
                }
              }
            </tbody>
          </table>
        </div>
        <app-pager [page]="d.page" [pageSize]="d.page_size" [total]="d.total" [hasMore]="d.has_more" (go)="go($event)" />
       }
      }
    </app-state-panel>

    @if (selected(); as s) {
      <section class="detail" data-testid="reco-detail" aria-live="polite">
        <h3>Cómo se calculó el pedido del SKU {{ s }}</h3>
        <app-state-panel [state]="detail.state()" (retry)="detail.reload()">
          @if (det(); as r) {
            <app-superseded-banner [run]="r.run" />
            @if (calc(); as c) {
              <ol class="steps" data-testid="calc-steps">
                @for (st of c.steps; track st.n) {
                  <li><strong>{{ st.label }}:</strong> {{ st.text }}</li>
                }
              </ol>
              <p class="result">Pedido sugerido: <strong data-testid="order-result">{{ int(r.order_qty) }} unidades base</strong> (hipotético; inventario simulado).</p>
              @if (!c.check.target || !c.check.position || !c.check.order) {
                <p class="notice danger" data-testid="incoherent">Los valores publicados no cuadran con la fórmula; revise la corrida antes de usarlos.</p>
              }
            } @else {
              <p class="notice warn" data-testid="detail-nosnap">Sin inventario simulado al {{ dayMonth(r.snapshot_date) }}. {{ r.reason }}. No se supone stock cero y no se calcula pedido.</p>
            }
            <p data-testid="reco-dates">
              Fecha del inventario simulado: {{ date(r.snapshot_date) }} · origen del pronóstico: {{ date(r.origin) }} ·
              pronóstico del {{ date(r.forecast_from) }} al {{ date(r.forecast_to) }} · plazo de entrega {{ r.lead_time_days }} días ·
              revisión cada {{ r.review_days }} días · modelo {{ r.model }} · almacén {{ r.almacen }}
            </p>
            <details class="tech" data-testid="tech-details">
              <summary>Detalle técnico y valores exactos publicados</summary>
              <dl class="kv">
                @for (kv of exact(r); track kv[0]) { <dt>{{ kv[0] }}</dt><dd><code>{{ kv[1] }}</code></dd> }
              </dl>
              @if (explanationLines().length) {
                <h4>Texto técnico del servidor (explanation_steps)</h4>
                <ol class="steps">@for (line of explanationLines(); track $index) { <li>{{ line }}</li> }</ol>
              }
            </details>
          }
        </app-state-panel>
      </section>
    }
  `,
  styles: `
    .detail { margin-top: 1.2rem; border-top: 2px solid var(--line); }
    .result { font-size: 1.05rem; }
    .kv { display: grid; grid-template-columns: max-content 1fr; gap: 0.2rem 1rem; margin: 0; }
    .kv dt { font-weight: 600; } .kv dd { margin: 0; overflow-wrap: anywhere; }
    .sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
  `,
})
export class RecommendationsPage {
  private api = inject(ApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);
  /** Corrida elegida (parámetro de URL «run», compartido con Pronósticos y Comparación); sin él, la activa. */
  choice = new RunChoice(this.route, this.router, this.destroyRef, () => { this.selected.set(null); this.q.set({ ...this.q(), page: 1 }); this.l.reload(); });
  f = { sku: '', categoria: '', status: '' as '' | 'ok' | 'sin_snapshot', only_orders: false, sort: 'sku' };
  private pageSize = 50;
  private q = signal<RecoQuery>({ page: 1, page_size: this.pageSize, sort: 'sku' });
  l = load<RecoPage>(() => this.api.recommendations({ ...this.q(), run_id: this.choice.id() ?? undefined }), (d) => d.items.length === 0 && !d.unavailable_reason);
  data = computed(() => { const s = this.l.state(); return s.kind === 'data' ? s.data : null; });
  first = computed(() => this.data()?.items[0] ?? null);
  dayMonth = (v: string | null | undefined) => fmtDate(v).slice(0, 5);
  scenarioId = computed(() => this.data()?.items[0]?.scenario_id ?? null);
  run = computed(() => this.data()?.run ?? null);
  /** Motivo de no disponibilidad (evaluación final): la API devuelve 200 con items vacío y este código. */
  unavailable = computed(() => this.data()?.unavailable_reason ?? null);
  seeRun = computed(() => this.data()?.see_run ?? null);
  kindText = (k: string | undefined) => kindLabel(k);
  reasonText = (code: string) => code === FINAL_UNAVAILABLE_REASON
    ? 'la recomendación no está validada para este origen (31/07/2026): la evaluación final compara pronósticos con ventas observadas y no genera pedidos.'
    : 'la API indicó que no hay recomendaciones disponibles para esta corrida.';
  int = (v: unknown) => fmtInt(v);
  pen = (v: unknown) => fmtPen(v);
  date = (v: string | null | undefined) => fmtDate(v);

  selected = signal<string | null>(null);
  private selAlmacen = '1';
  detail = load<Recommendation>(() => this.api.recommendation(this.selected()!, this.choice.id() ?? this.data()?.run?.run_id ?? undefined, this.selAlmacen), () => false, false);
  det = computed(() => { const s = this.detail.state(); return s.kind === 'data' ? s.data : null; });
  calc = computed(() => { const r = this.det(); return r ? calcSteps(r) : null; });
  explanationLines = computed<string[]>(() => {
    const r = this.det();
    const e = r?.explanation_steps ?? r?.explanation;
    if (!e) return [];
    return Array.isArray(e) ? e : e.split('\n');
  });

  /** Valores tal como los publica el servidor (sin redondear): no se pierden, pero no son la explicación principal. */
  exact(r: Recommendation): [string, string][] {
    const keys: (keyof Recommendation)[] = ['run_id', 'scenario_id', 'provenance', 'almacen', 'on_hand', 'in_transit', 'position', 'sum_28', 'days_28',
      'mean_28_exact', 'mean_28', 'forecast_14d', 'safety', 'target', 'order_qty', 'unit_cost_assumed', 'order_value_assumed'];
    return keys.filter((k) => r[k] !== undefined).map((k) => [k as string, r[k] === null ? DASH : String(r[k])]);
  }

  apply() {
    const t = (v: string) => v.trim() || undefined;
    this.q.set({ sku: t(this.f.sku), categoria: t(this.f.categoria), status: this.f.status, only_orders: this.f.only_orders, sort: this.f.sort, page: 1, page_size: this.pageSize });
    this.l.reload();
  }
  go(p: number) { this.q.set({ ...this.q(), page: p }); this.l.reload(); }
  open(r: Recommendation) { this.selAlmacen = r.almacen; this.selected.set(r.sku); this.detail.reload(); }
}
