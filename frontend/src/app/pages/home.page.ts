import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ApiService } from '../core/api.service';
import { AuthService } from '../core/auth.service';
import { load } from '../core/load';
import { RunChoice, isFinal } from '../core/run-choice';
import { RunsStore } from '../core/runs-store';
import { RecoPage } from '../core/models';
import { fmtInt } from '../core/format';
import { analysisName, longDate } from '../core/ux-text';
import { PageHeader } from '../ui/page-header';
import { AnalysisBar } from '../ui/analysis-bar';
import { FIRST_STEPS, closeOnboarding, onboardingClosed } from './first-steps';

/** Inicio: orienta (para qué sirve, qué análisis se ve, tres tareas) sin tablas de calidad ni historial técnico. */
@Component({
  selector: 'app-home-page',
  imports: [RouterLink, PageHeader, AnalysisBar],
  template: `
    <app-page-header title="Explora las ventas previstas y una simulación de reposición"
      lead="Consulta cuánto se estimó vender y cómo se calculó una sugerencia de reposición con los datos del ejemplo." />
    <app-analysis-bar [runId]="choice.id()" />

    <section class="cards" aria-label="¿Qué quieres hacer?" data-testid="home-tasks">
      <article class="card" data-testid="task-forecast">
        <h2>Consultar ventas previstas</h2>
        <p>Elige un producto y revisa las unidades estimadas para las fechas del ejemplo.</p>
        <div class="actions"><a class="btn" [routerLink]="['/pronosticos']" queryParamsHandling="preserve" data-testid="go-forecasts">Ver previsión</a></div>
      </article>
      <article class="card" data-testid="task-reco">
        <h2>Entender una reposición</h2>
        <p>Revisa una sugerencia y los datos utilizados para calcularla.</p>
        <div class="actions"><a class="btn secondary" [routerLink]="['/recomendaciones']" queryParamsHandling="preserve" data-testid="go-reco">Explorar reposición simulada</a></div>
      </article>
      <article class="card" data-testid="task-plan">
        <h2>Planificar la compra de noviembre</h2>
        <p>Revisa cuántas unidades comprar por producto para cubrir el mes, con plazos de entrega de 7 y 14 días y supuestos a la vista.</p>
        <div class="actions"><a class="btn secondary" [routerLink]="['/planificar']" queryParamsHandling="preserve" data-testid="go-plan">Planificar compras</a></div>
      </article>
      <article class="card" data-testid="task-inventory">
        <h2>Consultar el inventario informado</h2>
        <p>Revisa las existencias que la empresa informó en su conteo del almacén principal. No es parte de la simulación.</p>
        <div class="actions"><a class="btn secondary" [routerLink]="['/inventario']" queryParamsHandling="preserve" data-testid="go-inventory">Ver inventario informado</a></div>
      </article>
      <article class="card" data-testid="task-runs">
        <h2>Consultar otro análisis</h2>
        <p>Cambia entre el ejemplo de julio y la evaluación de agosto.</p>
        <div class="actions"><a class="btn secondary" [routerLink]="['/corridas']" queryParamsHandling="preserve" data-testid="go-runs">Ver mis análisis</a></div>
      </article>
    </section>

    @switch (reco.state().kind) {
      @case ('data') {
        @if (figure(); as f) {
          <section class="surface" aria-label="Una cifra del análisis" data-testid="home-figure-box">
            <p><strong class="big" data-testid="home-figure">{{ f.count }}</strong> productos con sugerencia de reposición en el ejemplo</p>
            <p class="muted" data-testid="home-figure-context">{{ f.context }}</p>
          </section>
        } @else {
          <section class="surface" data-testid="home-figure-box">
            <p data-testid="home-no-orders">Este análisis no genera pedidos: sirve para comparar estimaciones con ventas registradas.</p>
          </section>
        }
      }
      @case ('error') {
        <p class="muted" role="status" data-testid="home-figure-error">No se pudo consultar la cifra de reposición. <button type="button" class="secondary small" (click)="reco.reload()">Reintentar</button></p>
      }
    }

    @if (!closed()) {
      <section class="surface" aria-labelledby="h-start" data-testid="onboarding">
        <h2 id="h-start">Cómo empezar</h2>
        <ol class="steps">
          @for (s of steps; track s.title) { <li><strong>{{ s.title }}.</strong> {{ s.text }}</li> }
        </ol>
        <p>
          <button type="button" class="secondary small" (click)="close()" data-testid="onboarding-close">Entendido, cerrar</button>
          <span class="muted"> Puedes volver a verlo desde <a [routerLink]="['/ayuda']" queryParamsHandling="preserve">Ayuda</a>.</span>
        </p>
      </section>
    }

    @if (isAdmin) {
      <section class="surface" aria-labelledby="h-adm" data-testid="home-admin">
        <h2 id="h-adm">Administración</h2>
        <p class="muted">Solo el administrador puede cargar datos o crear análisis.</p>
        <p class="toolbar-links">
          <a class="btn secondary" [routerLink]="['/cargas']" queryParamsHandling="preserve" data-testid="go-imports">Cargar datos</a>
          <a class="btn secondary" [routerLink]="['/crear-analisis']" queryParamsHandling="preserve" data-testid="go-create">Crear análisis</a>
        </p>
      </section>
    }
  `,
  styles: `
    .big { font-size: 1.6rem; }
    .toolbar-links { display: flex; flex-wrap: wrap; gap: 0.6rem; }
  `,
})
export class HomePage {
  private api = inject(ApiService);
  private auth = inject(AuthService);
  private store = inject(RunsStore);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);
  /** Solo orientación: el servidor decide los permisos. */
  isAdmin = this.auth.isAdmin;
  steps = FIRST_STEPS;
  private user = this.auth.session()?.username;
  closed = signal(onboardingClosed(this.user));

  choice = new RunChoice(this.route, this.router, this.destroyRef, () => this.reco.reload());
  /** Total del SERVIDOR de sugerencias con pedido en el análisis elegido (page_size=1: solo interesa `total`). */
  reco = load<RecoPage>(() => this.api.recommendations({ run_id: this.choice.id() ?? undefined, only_orders: true, page: 1, page_size: 1 }));

  figure = computed(() => {
    const s = this.reco.state();
    if (s.kind !== 'data') return null;
    const run = this.store.resolve(this.choice.id());
    if (s.data.unavailable_reason || (run && isFinal(run.kind))) return null;
    const used = run ? longDate(run.origin ?? run.cutoff) : '';
    const ctx = [
      run ? `Análisis: ${analysisName(run)}` : '',
      used ? `ventas utilizadas hasta el ${used}` : '',
      'inventario simulado; no son existencias reales',
    ].filter(Boolean).join(' · ');
    return { count: fmtInt(s.data.total), context: ctx };
  });

  close() { closeOnboarding(this.user); this.closed.set(true); }
}
