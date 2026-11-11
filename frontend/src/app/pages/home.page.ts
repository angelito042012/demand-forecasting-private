import { Component, DestroyRef, computed, effect, inject, signal, untracked } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ApiService } from '../core/api.service';
import { AuthService } from '../core/services/auth.service';
import { CurrentPlanStore } from '../core/current-plan.store';
import { load } from '../core/utils/load';
import { RunChoice, isFinal } from '../core/run-choice';
import { RunsStore } from '../core/runs-store';
import { PlanResultsPage, RecoPage } from '../core/models';
import { fmtDate, fmtInt } from '../core/utils/format';
import { analysisName, longDate, monthName } from '../core/utils/ux-text';
import { PageHeader } from '../shared/components/page-header';
import { AnalysisBar } from '../shared/components/analysis-bar';
import { StatePanel } from '../shared/components/state-panel';
import { FIRST_STEPS, closeOnboarding, onboardingClosed } from './first-steps';
import { localStamp } from './inventory.page';
import { CardModule } from 'primeng/card';
import { ButtonModule } from 'primeng/button';
import { PanelModule } from 'primeng/panel';
import { TagModule } from 'primeng/tag';

/**
 * Inicio: resume el plan de compra VIGENTE (el mismo que abre «Compra recomendada» por defecto) y orienta con tareas simples.
 * La evaluación histórica con inventario simulado queda en una sección académica separada.
 */
@Component({
  selector: 'app-home-page',
  imports: [RouterLink, PageHeader, AnalysisBar, StatePanel, CardModule, ButtonModule, PanelModule, TagModule],
  template: `
    <app-page-header [title]="'Ventas previstas y compra recomendada para ' + monthWord()" />

    <app-state-panel [state]="store.state()" emptyText="Todavía no se generó un plan de compra. Cuando exista, aquí verás su resumen." (retry)="store.reload()">
      @if (cur(); as c) {
        <section class="surface plan-card" aria-labelledby="h-plan" data-testid="home-plan">
          <h2 id="h-plan">Plan de compra vigente</h2>
          <p data-testid="hp-version"><strong>Versión {{ c.ref.version ?? '—' }}</strong> del {{ stamp(c.ref.created_at) }} · decisión de compra el {{ date(c.header.params?.decision_date ?? c.ref.decision_date) }} · plazos de {{ leadText() }} días.</p>
          <ul class="plain prov" data-testid="hp-prov">
            <li data-testid="hp-cutoff"><p-tag severity="success" value="Dato real" /> Ventas registradas hasta el <strong>{{ longDate(cutoff()) }}</strong>. Lo posterior es desconocido, no cero.</li>
            <li data-testid="hp-stock"><p-tag severity="info" value="Dato de la empresa" /> {{ stockText() }}</li>
            <li data-testid="hp-projection"><p-tag severity="warn" value="Proyección" /> Promedio de los últimos 28 días; no son ventas observadas.</li>
          </ul>
          <app-state-panel [state]="res.state()" (retry)="res.reload()">
            @if (buyCounts(); as bc) {
              <p class="counts" data-testid="hp-counts">Productos con compra recomendada:
                @for (b of bc; track b.lead) { <strong>{{ b.n }}</strong> de {{ b.total }} con plazo de {{ b.lead }} días{{ $last ? '.' : ' · ' }} }
              </p>
            } @else {
              <p class="muted" data-testid="hp-counts-na">El conteo de productos con compra recomendada se ve en «Compra recomendada».</p>
            }
          </app-state-panel>
        </section>
      }
    </app-state-panel>

    <section class="task-grid" aria-label="¿Qué quieres hacer?" data-testid="home-tasks">
      <p-card data-testid="task-forecast">
        <ng-template #header>
          <div class="card-icon-row"><i class="pi pi-chart-bar"></i></div>
        </ng-template>
        <ng-template #title>Ventas previstas</ng-template>
        <ng-template #subtitle>Unidades que se estima vender de cada producto en el mes del plan.</ng-template>
        <ng-template #footer>
          <p-button label="Ver ventas previstas" icon="pi pi-arrow-right" iconPos="right" [routerLink]="['/pronosticos']" data-testid="go-forecasts" />
        </ng-template>
      </p-card>
      <p-card data-testid="task-inventory">
        <ng-template #header>
          <div class="card-icon-row"><i class="pi pi-box"></i></div>
        </ng-template>
        <ng-template #title>Existencias</ng-template>
        <ng-template #subtitle>Existencias al cierre de la fecha del plan y su procedencia.</ng-template>
        <ng-template #footer>
          <p-button label="Ver existencias" icon="pi pi-arrow-right" iconPos="right" [outlined]="true" [routerLink]="['/existencias']" data-testid="go-stock" />
        </ng-template>
      </p-card>
      <p-card data-testid="task-plan">
        <ng-template #header>
          <div class="card-icon-row"><i class="pi pi-shopping-cart"></i></div>
        </ng-template>
        <ng-template #title>Compra recomendada</ng-template>
        <ng-template #subtitle>Unidades a comprar por producto, con plazos de 7 y 14 días y supuestos a la vista.</ng-template>
        <ng-template #footer>
          <p-button label="Ver compra recomendada" icon="pi pi-arrow-right" iconPos="right" [outlined]="true" [routerLink]="['/planificar']" data-testid="go-plan" />
        </ng-template>
      </p-card>
      <p-card data-testid="task-runs">
        <ng-template #header>
          <div class="card-icon-row"><i class="pi pi-list"></i></div>
        </ng-template>
        <ng-template #title>Mis análisis</ng-template>
        <ng-template #subtitle>Consulta los análisis guardados.</ng-template>
        <ng-template #footer>
          <p-button label="Ver mis análisis" icon="pi pi-arrow-right" iconPos="right" [outlined]="true" [routerLink]="['/corridas']" queryParamsHandling="preserve" data-testid="go-runs" />
        </ng-template>
      </p-card>
    </section>

    <details class="surface fold" data-testid="home-academic">
      <summary><strong>Evaluación académica con datos históricos del ejemplo</strong> <span class="muted">(inventario simulado con supuestos; no representa las existencias actuales)</span></summary>
      <p class="muted">Esta sección es histórica y separada del plan de compra: usa un inventario simulado con supuestos y no representa las existencias actuales.</p>
      <app-analysis-bar [runId]="choice.id()" />
      <div class="cards">
        <article class="card" data-testid="task-reco">
          <h3>Entender una reposición</h3>
          <p>Revisa una sugerencia simulada y los datos utilizados para calcularla.</p>
          <div class="actions"><a class="btn secondary" [routerLink]="['/recomendaciones']" queryParamsHandling="preserve" data-testid="go-reco">Explorar reposición simulada</a></div>
        </article>
        <article class="card" data-testid="task-academic-forecast">
          <h3>Ventas previstas del ejemplo</h3>
          <p>La previsión histórica del análisis elegido.</p>
          <div class="actions"><a class="btn secondary" [routerLink]="['/evaluacion/ventas-previstas']" queryParamsHandling="preserve" data-testid="go-academic-forecasts">Ver previsión del ejemplo</a></div>
        </article>
        <article class="card" data-testid="task-academic-runs">
          <h3>Consultar otro análisis</h3>
          <p>Cambia entre el ejemplo de julio y la evaluación de agosto.</p>
          <div class="actions"><a class="btn secondary" [routerLink]="['/corridas']" queryParamsHandling="preserve" data-testid="go-academic-runs">Ver análisis históricos</a></div>
        </article>
      </div>

      @switch (reco.state().kind) {
        @case ('data') {
          @if (figure(); as f) {
            <div data-testid="home-figure-box">
              <p><strong class="big" data-testid="home-figure">{{ f.count }}</strong> productos con sugerencia de reposición en el ejemplo</p>
              <p class="muted" data-testid="home-figure-context">{{ f.context }}</p>
            </div>
          } @else {
            <div data-testid="home-figure-box">
              <p data-testid="home-no-orders">Este análisis no genera pedidos: sirve para comparar estimaciones con ventas registradas.</p>
            </div>
          }
        }
        @case ('error') {
          <p class="muted" role="status" data-testid="home-figure-error">No se pudo consultar la cifra de reposición. <button type="button" class="secondary small" (click)="reco.reload()">Reintentar</button></p>
        }
      }
    </details>

    @if (!closed()) {
      <details class="surface fold" data-testid="onboarding">
        <summary><strong>Cómo empezar</strong></summary>
        <ol class="steps">
          @for (s of steps; track s.title) { <li><strong>{{ s.title }}.</strong> {{ s.text }}</li> }
        </ol>
        <p>
          <button type="button" class="secondary small" (click)="close()" data-testid="onboarding-close">Entendido, cerrar</button>
          <span class="muted"> Puedes volver a verlo desde <a [routerLink]="['/ayuda']" queryParamsHandling="preserve">Ayuda</a>.</span>
        </p>
      </details>
    }

    @if (isAdmin) {
      <p-panel header="Administración" data-testid="home-admin">
        <p class="muted">Solo el administrador puede cargar datos o crear análisis.</p>
        <div class="flex flex-wrap gap-3 mt-3">
          <p-button label="Cargar datos" icon="pi pi-upload" [outlined]="true" [routerLink]="['/cargas']" queryParamsHandling="preserve" data-testid="go-imports" />
          <p-button label="Crear análisis" icon="pi pi-plus-circle" [outlined]="true" [routerLink]="['/crear-analisis']" queryParamsHandling="preserve" data-testid="go-create" />
        </div>
      </p-panel>
    }
  `,
  styles: `
    :host ::ng-deep .ph { margin: 0 0 0.5rem; }
    .plan-card { padding-top: 0.2rem; padding-bottom: 0.5rem; }
    .plan-card h2 { margin: 0.4rem 0 0.3rem; font-size: 1.2rem; }
    .plan-card p { margin: 0.3rem 0; }
    .prov { margin: 0.2rem 0; font-size: 0.95rem; }
    .prov li { margin: 0.15rem 0; display: flex; align-items: center; gap: 0.5rem; }
    .counts { font-size: 1.05rem; }
    .task-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr)); gap: 1rem; margin: 1rem 0; }
    .card-icon-row { padding: 1rem 1rem 0; }
    .card-icon-row i { font-size: 1.5rem; color: var(--accent); }
    :host ::ng-deep .task-grid .p-card { height: 100%; display: flex; flex-direction: column; }
    :host ::ng-deep .task-grid .p-card-body { flex: 1; display: flex; flex-direction: column; }
    :host ::ng-deep .task-grid .p-card-footer { margin-top: auto; }
    .fold > summary { cursor: pointer; }
    .big { font-size: 1.6rem; }
  `,
})
export class HomePage {
  private api = inject(ApiService);
  private auth = inject(AuthService);
  private store0 = inject(RunsStore);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);
  readonly store = inject(CurrentPlanStore);
  /** Solo orientación: el servidor decide los permisos. */
  isAdmin = this.auth.isAdmin;
  steps = FIRST_STEPS;
  private user = this.auth.session()?.username;
  closed = signal(onboardingClosed(this.user));

  // ---- plan vigente (misma fuente que «Compra recomendada» y «Ventas previstas») ----
  readonly longDate = longDate;
  readonly date = (iso: string | null | undefined) => fmtDate(iso);
  cur = this.store.plan;
  res = load<PlanResultsPage>(() => this.api.planResults(this.cur()!.ref.plan_id, { sort: 'producto_id', page: 1, page_size: 50 }), () => false, false);
  cutoff = computed(() => { const h = this.cur()?.header; return h?.dates?.sales_cutoff ?? h?.dataset?.sales_cutoff ?? null; });
  monthWord = computed(() => { const m = this.cur()?.month; return (m ? monthName(`${m}-01`) : '') || 'el mes del plan'; });
  leadText = computed(() => (this.cur()?.header.params?.lead_days ?? this.cur()?.ref.lead_days ?? []).join(' y '));
  stamp = (iso: string | undefined) => localStamp(iso)?.replace(', ', ' a las ') ?? 'fecha no informada';
  stockText = computed(() => {
    const sn = this.cur()?.header.snapshot;
    const day = localStamp(sn?.as_of_local)?.split(',')[0] ?? 'fecha no informada';
    return sn?.kind === 'RECONSTRUIDO'
      ? `Existencia inicial reconstruida al cierre del ${day} (conteo informado por la empresa más movimientos del sistema).`
      : `Existencia inicial según el conteo informado por la empresa el ${day}.`;
  });
  /** Productos con compra recomendada > 0 por plazo, contados sobre las filas del servidor (solo si llegaron todas). */
  buyCounts = computed(() => {
    const s = this.res.state();
    if (s.kind !== 'data' || s.data.has_more) return null;
    const leads = (this.cur()?.header.params?.lead_days ?? []).map(String);
    if (!leads.length) return null;
    return leads.map((l) => ({
      lead: l, total: s.data.items.length,
      n: s.data.items.filter((r) => { const v = r.scenarios[l]?.purchase_qty; return v !== null && v !== undefined && Number(v) > 0; }).length,
    }));
  });

  // ---- sección académica (histórica) ----
  choice = new RunChoice(this.route, this.router, this.destroyRef, () => this.reco.reload());
  /** Total del SERVIDOR de sugerencias con pedido en el análisis elegido (page_size=1: solo interesa `total`). */
  reco = load<RecoPage>(() => this.api.recommendations({ run_id: this.choice.id() ?? undefined, only_orders: true, page: 1, page_size: 1 }));

  figure = computed(() => {
    const s = this.reco.state();
    if (s.kind !== 'data') return null;
    const run = this.store0.resolve(this.choice.id());
    if (s.data.unavailable_reason || (run && isFinal(run.kind))) return null;
    const used = run ? longDate(run.origin ?? run.cutoff) : '';
    const ctx = [
      run ? `Análisis: ${analysisName(run)}` : '',
      used ? `ventas utilizadas hasta el ${used}` : '',
      'inventario simulado; no son existencias reales',
    ].filter(Boolean).join(' · ');
    return { count: fmtInt(s.data.total), context: ctx };
  });

  constructor() {
    this.store.ensure();
    effect(() => { const id = this.cur()?.ref.plan_id; if (id) untracked(() => this.res.reload()); });
  }

  close() { closeOnboarding(this.user); this.closed.set(true); }
}
