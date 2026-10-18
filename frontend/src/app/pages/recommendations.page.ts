import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { RunChoice } from '../core/run-choice';
import { FormsModule } from '@angular/forms';
import { ApiService, RecoQuery } from '../core/api.service';
import { load } from '../core/load';
import { FINAL_UNAVAILABLE_REASON, RecoPage, Recommendation, RunSummary } from '../core/models';
import { calcSteps, simpleSteps } from '../core/reco-calc';
import { DASH, fmtDate, fmtInt, fmtPen } from '../core/format';
import { RunsStore } from '../core/runs-store';
import { analysisName, productLabel } from '../core/ux-text';
import { StatePanel } from '../ui/state-panel';
import { Pager } from '../ui/pager';
import { PageHeader } from '../ui/page-header';
import { AnalysisBar } from '../ui/analysis-bar';
import { SimNotice } from '../ui/notices';
import { RecoReplacedNotice } from '../ui/reco-replaced-notice';
import { isReplaced } from '../core/ux-text';

/** Vistas de la lista: todas se filtran en el servidor (nunca sobre la página recibida). */
export type RecoView = 'sugerencia' | 'sin_necesidad' | 'sin_datos';
export const RECO_VIEWS: { id: RecoView; label: string; empty: string }[] = [
  { id: 'sugerencia', label: 'Con sugerencia de reposición', empty: 'En este análisis ningún producto tiene sugerencia de reposición con estos filtros. Prueba otra vista o quita el código y la categoría.' },
  { id: 'sin_necesidad', label: 'Sin necesidad de reponer en el ejemplo', empty: 'Ningún producto cumple esta vista con estos filtros.' },
  { id: 'sin_datos', label: 'Sin datos de inventario', empty: 'Ningún producto sin datos de inventario con estos filtros.' },
];

function viewQuery(v: RecoView): Pick<RecoQuery, 'status' | 'only_orders' | 'no_orders'> {
  switch (v) {
    case 'sugerencia': return { status: 'ok', only_orders: true };
    case 'sin_necesidad': return { status: 'ok', no_orders: true };
    case 'sin_datos': return { status: 'sin_snapshot' };
  }
}

/**
 * UX01 «Reposición simulada»: tabla corta (producto, disponible simulado, cantidad sugerida) y, al abrir una sugerencia,
 * tres pasos sencillos con los valores reales del detalle; el cálculo completo y los supuestos quedan en un bloque plegable.
 */
@Component({
  selector: 'app-recommendations-page',
  imports: [StatePanel, Pager, FormsModule, SimNotice, RouterLink, PageHeader, AnalysisBar, RecoReplacedNotice],
  template: `
    <app-page-header title="Reposición simulada" lead="Cuántas unidades se sugeriría reponer de cada producto en el ejemplo, y cómo se calculó esa cantidad." />
    <app-analysis-bar [runId]="choice.id()" />
    @if (!barShowsReplaced()) { <app-reco-replaced-notice [run]="data()?.run" /> }
    <app-sim-notice [scenarioId]="scenarioId()" />

    @if (unavailable(); as u) {
      <section class="notice warn" data-testid="reco-unavailable" role="note" aria-labelledby="h-na">
        <h2 id="h-na">Este análisis no genera pedidos</h2>
        <p data-testid="reco-unavailable-text">{{ unavailableText() }}</p>
        @if (seeRun(); as sr) {
          <p><a class="btn" [routerLink]="['/recomendaciones']" [queryParams]="{ run: sr }" data-testid="see-run">Abrir el ejemplo con reposición simulada</a></p>
          <p class="muted">Cambia de análisis de forma explícita; las cifras de ambos no se mezclan.</p>
        } @else { <p class="muted" data-testid="no-see-run">La aplicación no indicó otro análisis con reposición simulada. Elige uno en «Mis análisis».</p> }
        <details class="tech">
          <summary>Detalle técnico</summary>
          <p>Motivo publicado: <code data-testid="reco-reason-code">{{ u }}</code> — {{ reasonText(u) }}</p>
        </details>
      </section>
    }
    @if (first(); as x) {
      <p class="muted" data-testid="reco-header">Ventas utilizadas hasta el <strong>{{ date(x.origin) }}</strong> · período a cubrir: <strong>{{ date(x.forecast_from) }} al {{ date(x.forecast_to) }}</strong> ·
        inventario simulado al cierre del {{ date(x.snapshot_date) }}.
        <a [routerLink]="['/corridas']" [queryParams]="choice.id() ? { run: choice.id() } : {}" data-testid="change-run">Elegir otro análisis</a>
      </p>
    }
    @if (!unavailable()) {
      <p class="muted" data-testid="reco-note">Son sugerencias hipotéticas con datos históricos: no son un pedido ni una compra real. Cantidades en unidad base.</p>

      <section class="toolbar" aria-label="Filtros de reposición simulada">
        <fieldset class="seg" aria-label="Vista">
          <legend>Vista</legend>
          @for (v of views; track v.id) {
            <button type="button" class="secondary" [attr.data-testid]="'view-' + v.id" [attr.aria-pressed]="view() === v.id" (click)="setView(v.id)">{{ v.label }}</button>
          }
        </fieldset>
        <form class="filters" (ngSubmit)="apply()" aria-label="Filtros de recomendaciones">
          <label>Código del producto <input name="sku" [(ngModel)]="f.sku" autocomplete="off" /></label>
          <label>Categoría <input name="cat" [(ngModel)]="f.categoria" autocomplete="off" /></label>
          <button type="submit" data-testid="reco-apply">Buscar</button>
          <details class="help more">
            <summary>Más filtros</summary>
            <label>Orden
              <select name="sort" [(ngModel)]="f.sort">
                <option value="sku">Código del producto</option><option value="categoria">Categoría</option>
                <option value="-order_qty">Cantidad sugerida ↓</option><option value="order_qty">Cantidad sugerida ↑</option>
              </select>
            </label>
          </details>
        </form>
      </section>
    }

    @if (selected(); as s) {
      <section class="detail" data-testid="reco-detail" aria-live="polite" aria-label="Detalle de la sugerencia">
        <app-state-panel [state]="detail.state()" (retry)="detail.reload()">
          @if (det(); as r) {
            <app-reco-replaced-notice [run]="r.run" />
            <h2 data-testid="detail-title">{{ product(r) }}</h2>
            @if (calc(); as c) {
              @if (!c.check.target || !c.check.position || !c.check.order) {
                <p class="notice danger" data-testid="incoherent" role="alert">Los valores publicados no cuadran con la fórmula; revise el análisis antes de usarlos.</p>
              }
              <p class="result" data-testid="result-headline">En este ejemplo se sugieren <strong data-testid="order-result">{{ units(r.order_qty) }}</strong>
                <span class="muted">(hipotético; inventario simulado al cierre del {{ date(r.snapshot_date) }})</span></p>
              @if (simple(); as sm) {
                <ol class="steps simple" data-testid="simple-steps">
                  @for (st of sm.steps; track st.n) {
                    <li><strong>{{ st.title }}</strong>
                      <ul class="plain">@for (ln of st.lines; track $index) { <li>{{ ln }}</li> }</ul>
                    </li>
                  }
                </ol>
              }
            } @else {
              <p class="notice warn" data-testid="detail-nosnap"><strong>Sin datos de inventario</strong> al {{ dayMonth(r.snapshot_date) }}. Qué información falta: {{ r.reason }}. No se supone stock cero y no se calcula una cantidad sugerida.</p>
            }
            <details class="help" data-testid="full-calc">
              <summary>Ver cálculo completo y supuestos</summary>
              @if (calc(); as c) {
                <ol class="steps" data-testid="calc-steps">
                  @for (st of c.steps; track st.n) {
                    <li><strong>{{ st.label }}:</strong> {{ st.text }}</li>
                  }
                </ol>
                <p>Verificaciones: posición {{ c.check.position ? 'coherente' : 'NO coherente' }} · objetivo {{ c.check.target ? 'coherente' : 'NO coherente' }} · cantidad {{ c.check.order ? 'coherente' : 'NO coherente' }} con la fórmula.</p>
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
                  <h3>Texto técnico del servidor (explanation_steps)</h3>
                  <ol class="steps">@for (line of explanationLines(); track $index) { <li>{{ line }}</li> }</ol>
                }
              </details>
            </details>
          }
          <p><button type="button" class="secondary small" (click)="close()" data-testid="close-detail">Cerrar detalle</button></p>
        </app-state-panel>
      </section>
    }

    <app-state-panel [state]="l.state()" [emptyText]="currentView().empty" (retry)="l.reload()">
      @if (data(); as d) {
       @if (!d.unavailable_reason) {
        <p data-testid="reco-total"><strong>{{ d.total }} {{ d.total === 1 ? 'producto' : 'productos' }}</strong> en «{{ currentView().label }}»@if (hasFilters()) { con los filtros aplicados }.</p>
        <div class="table-wrap" tabindex="0" role="region" aria-label="Tabla de reposición simulada">
          <table data-testid="reco-table">
            <thead>
              <tr>
                <th scope="col">Producto</th><th scope="col" class="num">Disponible simulado (unidades)</th>
                <th scope="col" class="num">Cantidad sugerida (unidades base)</th>
                <th scope="col"><span class="sr-only">Acción</span></th>
              </tr>
            </thead>
            <tbody>
              @for (r of d.items; track r.sku + r.almacen) {
                @if (r.status === 'ok') {
                  <tr>
                    <td>{{ product(r) }}</td>
                    <td class="num">{{ int(r.on_hand) }}</td><td class="num">{{ int(r.order_qty) }}</td>
                    <td><button type="button" class="secondary small" (click)="open(r)" [attr.aria-label]="'Entender la sugerencia de ' + product(r)">Entender sugerencia</button></td>
                  </tr>
                } @else {
                  <tr class="nosnap" data-testid="sin-snapshot">
                    <td>{{ product(r) }}</td>
                    <td colspan="2"><span class="chip warn">Sin datos de inventario</span> al {{ dayMonth(r.snapshot_date) }}. Qué información falta: {{ r.reason }}. No se supone stock cero.</td>
                    <td><button type="button" class="secondary small" (click)="open(r)" [attr.aria-label]="'Ver qué falta para ' + product(r)">Ver qué falta</button></td>
                  </tr>
                }
              }
            </tbody>
          </table>
        </div>
        <app-pager [page]="d.page" [pageSize]="d.page_size" [total]="d.total" [hasMore]="d.has_more" (go)="go($event)" />
        <details class="help" data-testid="reco-help">
          <summary>Cómo leer esta tabla</summary>
          <p>«Disponible simulado» es el inventario inventado con supuestos para ilustrar el cálculo; «por recibir» y el valor supuesto del pedido están en el detalle de cada sugerencia.
            La demanda usada es la venta registrada, que puede estar limitada por falta de stock. Costos supuestos en PEN.</p>
        </details>
       }
      }
    </app-state-panel>
  `,
  styles: `
    .detail { margin: 1rem 0; padding: 0.2rem 1rem 0.6rem; background: var(--surface); border: 1px solid var(--line); border-left: 4px solid var(--accent); border-radius: var(--radius); }
    .result { font-size: 1.15rem; }
    .simple > li { margin: 0.6rem 0; }
    .more { flex-basis: 100%; }
    .seg { margin-bottom: 0.8rem; }
  `,
})
export class RecommendationsPage {
  private api = inject(ApiService);
  private store = inject(RunsStore);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);
  /** Análisis elegido (parámetro de URL «run», compartido con las demás pantallas); sin él, el que está en uso por defecto. */
  choice = new RunChoice(this.route, this.router, this.destroyRef, () => { this.selected.set(null); this.q.set({ ...this.q(), page: 1 }); this.l.reload(); });
  views = RECO_VIEWS;
  /** Vista inicial: productos con sugerencia de reposición. */
  view = signal<RecoView>('sugerencia');
  currentView = computed(() => RECO_VIEWS.find((v) => v.id === this.view())!);
  f = { sku: '', categoria: '', sort: 'sku' };
  private pageSize = 50;
  private q = signal<RecoQuery>({ ...viewQuery('sugerencia'), page: 1, page_size: this.pageSize, sort: 'sku' });
  l = load<RecoPage>(() => this.api.recommendations({ ...this.q(), run_id: this.choice.id() ?? undefined }), (d) => d.items.length === 0 && !d.unavailable_reason);
  data = computed(() => { const s = this.l.state(); return s.kind === 'data' ? s.data : null; });
  first = computed(() => this.data()?.items[0] ?? null);
  dayMonth = (v: string | null | undefined) => fmtDate(v).slice(0, 5);
  scenarioId = computed(() => this.data()?.items[0]?.scenario_id ?? null);
  /** Motivo de no disponibilidad (evaluación): la API devuelve 200 con items vacío y este código. */
  unavailable = computed(() => this.data()?.unavailable_reason ?? null);
  seeRun = computed(() => this.data()?.see_run ?? null);
  unavailableText = computed(() => {
    const n = analysisName(this.store.resolve(this.choice.id() ?? this.data()?.run?.run_id ?? null) ?? (this.data()?.run as RunSummary | null | undefined) ?? null);
    const lower = n.charAt(0).toLowerCase() + n.slice(1);
    return `La ${lower} compara estimaciones con ventas registradas; no genera pedidos. No se muestran existencias ni pedidos en su lugar.`;
  });
  reasonText = (code: string) => code === FINAL_UNAVAILABLE_REASON
    ? 'la reposición no está validada para este origen: la evaluación compara pronósticos con ventas registradas y no genera pedidos.'
    : 'la API indicó que no hay recomendaciones disponibles para este análisis.';
  int = (v: unknown) => fmtInt(v);
  pen = (v: unknown) => fmtPen(v);
  date = (v: string | null | undefined) => fmtDate(v);
  product = (r: { sku: string; categoria: string | null }) => productLabel(r.sku, r.categoria);
  units = (n: number | null) => `${fmtInt(n)} ${n === 1 ? 'unidad' : 'unidades'}`;
  /** La barra de análisis ya avisa si el análisis elegido figura como reemplazado en la lista; el aviso propio cubre la calidad publicada con las sugerencias. */
  barShowsReplaced = computed(() => isReplaced(this.store.resolve(this.choice.id())));
  hasFilters = computed(() => !!(this.q().sku || this.q().categoria));

  selected = signal<string | null>(null);
  private selAlmacen = '1';
  detail = load<Recommendation>(() => this.api.recommendation(this.selected()!, this.choice.id() ?? this.data()?.run?.run_id ?? undefined, this.selAlmacen), () => false, false);
  det = computed(() => { const s = this.detail.state(); return s.kind === 'data' ? s.data : null; });
  calc = computed(() => { const r = this.det(); return r ? calcSteps(r) : null; });
  simple = computed(() => { const r = this.det(); return r ? simpleSteps(r, this.calc()) : null; });
  explanationLines = computed<string[]>(() => {
    const r = this.det();
    const e = r?.explanation_steps ?? r?.explanation;
    if (!e) return [];
    return Array.isArray(e) ? e : e.split('\n');
  });

  constructor() { this.store.ensure(); }

  /** Valores tal como los publica el servidor (sin redondear): no se pierden, pero no son la explicación principal. */
  exact(r: Recommendation): [string, string][] {
    const keys: (keyof Recommendation)[] = ['run_id', 'scenario_id', 'provenance', 'almacen', 'on_hand', 'in_transit', 'position', 'sum_28', 'days_28',
      'mean_28_exact', 'mean_28', 'forecast_14d', 'safety', 'target', 'order_qty', 'unit_cost_assumed', 'order_value_assumed'];
    return keys.filter((k) => r[k] !== undefined).map((k) => [k as string, r[k] === null ? DASH : String(r[k])]);
  }

  private build(): RecoQuery {
    const t = (v: string) => v.trim() || undefined;
    return { sku: t(this.f.sku), categoria: t(this.f.categoria), ...viewQuery(this.view()), sort: this.f.sort, page: 1, page_size: this.pageSize };
  }
  apply() { this.selected.set(null); this.q.set(this.build()); this.l.reload(); }
  setView(v: RecoView) { this.view.set(v); this.apply(); }
  go(p: number) { this.q.set({ ...this.q(), page: p }); this.l.reload(); }
  open(r: Recommendation) { this.selAlmacen = r.almacen; this.selected.set(r.sku); this.detail.reload(); }
  close() { this.selected.set(null); }
}
