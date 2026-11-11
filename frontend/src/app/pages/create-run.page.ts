import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { tap } from 'rxjs';
import { ApiService } from '../core/api.service';
import { AuthService } from '../core/services/auth.service';
import { load } from '../core/utils/load';
import { JobBoard, summarize } from '../core/jobs';
import { RunsStore } from '../core/runs-store';
import { AppError, RunOptions } from '../core/models';
import { longDate } from '../core/utils/ux-text';
import { PageHeader } from '../shared/components/page-header';
import { StatePanel } from '../shared/components/state-panel';
import { JobsPanel } from '../shared/components/jobs-panel';
import { ButtonModule } from 'primeng/button';
import { MessageModule } from 'primeng/message';
import { PanelModule } from 'primeng/panel';

@Component({
  selector: 'app-create-run-page',
  imports: [RouterLink, PageHeader, StatePanel, JobsPanel, ButtonModule, MessageModule, PanelModule],
  template: `
    <app-page-header title="Crear análisis" lead="Crea un análisis histórico con el promedio de los últimos 28 días para las fechas elegidas; no reentrena modelos." />
    <p-message severity="info" data-testid="runs-scope" role="note" styleClass="w-full mb-3">
      <strong>Análisis histórico (académico), no el plan de compra.</strong> Las fechas permitidas (abajo), el horizonte de 21 días y el método son una regla del servidor: sirven para comparar estimaciones con ventas ya registradas. El plan operativo de noviembre se genera y consulta en «Compra recomendada».
    </p-message>
    @if (!isAdmin) {
      <p-message severity="info" role="status" data-testid="admin-only" text="Solo el administrador puede crear análisis." styleClass="w-full mb-3" />
      <p-button label="Ir a Mis análisis" icon="pi pi-list" [outlined]="true" [routerLink]="['/corridas']" queryParamsHandling="preserve" />
    } @else {
      <p-panel header="Elegir las ventas que se usarán" data-testid="gen-section" styleClass="mb-3">
        <app-state-panel [state]="opt.state()" (retry)="opt.reload()">
          @if (options(); as o) {
            <form class="flex flex-wrap align-items-center gap-3" (submit)="$event.preventDefault(); generate()" aria-label="Crear análisis">
              <label class="field">Ventas utilizadas hasta (fecha)
                <input type="date" name="origin" data-testid="origin" [min]="o.origin_min" [max]="o.origin_max" [value]="origin()" (input)="setOrigin($any($event.target).value)" />
              </label>
              <span data-testid="horizon">Período estimado: <strong>los 21 días siguientes</strong> (fijo)</span>
              <span data-testid="gen-method">Método: <strong>promedio de los últimos 28 días</strong> (promedio_28, fijo)</span>
              <p-button type="submit" label="Crear análisis" icon="pi pi-plus-circle" [disabled]="!originOk() || sending()" [loading]="sending()" data-testid="generate-btn" />
            </form>
            <p class="muted mt-2" data-testid="origin-range">Fechas permitidas en esta versión: del {{ date(o.origin_min) }} al {{ date(o.origin_max) }}. Agosto sigue reservado.</p>
            @if (origin() && !originOk()) { <p-message severity="warn" role="alert" data-testid="origin-warning" [text]="'Esa fecha no está permitida. Elige una fecha entre el ' + date(o.origin_min) + ' y el ' + date(o.origin_max) + '.'" styleClass="w-full mt-2" /> }
          }
        </app-state-panel>
        @if (genError(); as e) { <p-message severity="error" role="alert" data-testid="gen-error" [text]="e" styleClass="w-full mt-2" /> }
        @if (created(); as c) {
          <p-message severity="success" role="status" data-testid="gen-done" styleClass="w-full mt-3">
            <div>
              <p><strong>Listo: el análisis se creó.</strong> Ya puedes consultar sus ventas previstas.</p>
              <div class="flex flex-wrap gap-2 mt-2">
                <p-button label="Ver previsión" icon="pi pi-chart-bar" [outlined]="true" [routerLink]="['/evaluacion/ventas-previstas']" [queryParams]="{ run: c }" data-testid="gen-view" />
                <p-button label="Ver en Mis análisis" icon="pi pi-list" [outlined]="true" [routerLink]="['/corridas']" [queryParams]="{ run: c }" data-testid="gen-view-runs" />
              </div>
            </div>
          </p-message>
        }
      </p-panel>
      <h2>Trabajos recientes</h2>
      <app-jobs-panel [jobs]="board.jobs()" [listError]="board.listError()" [pollError]="board.pollError()" />
    }
  `,
  styles: `.field { display: grid; gap: 0.25rem; font-weight: 600; }`,
})
export class CreateRunPage {
  private api = inject(ApiService);
  private auth = inject(AuthService);
  private store = inject(RunsStore);
  private destroyRef = inject(DestroyRef);
  isAdmin = this.auth.isAdmin;

  board = new JobBoard(this.api, 'generate_run', (j) => {
    this.store.refresh();
    const id = j.status === 'completed' ? summarize(j).runId : undefined;
    if (id) this.created.set(id);
  }, this.destroyRef);
  opt = load<RunOptions>(
    () => this.api.runOptions().pipe(tap((o) => { if (!this.origin()) this.origin.set(o.origin_default); })),
    () => false, false,
  );
  options = computed(() => { const s = this.opt.state(); return s.kind === 'data' ? s.data : null; });
  origin = signal('');
  sending = signal(false);
  genError = signal<string | null>(null);
  created = signal<string | null>(null);
  originOk = computed(() => {
    const o = this.options(); const v = this.origin();
    return !!o && /^\d{4}-\d{2}-\d{2}$/.test(v) && v >= o.origin_min && v <= o.origin_max;
  });

  constructor() {
    if (this.isAdmin) {
      this.board.loadRecent();
      this.opt.reload();
    }
  }

  date = (v: string | null | undefined) => longDate(v);
  setOrigin(v: string) { this.origin.set(v); this.genError.set(null); }

  generate() {
    const o = this.options();
    if (!o || !this.originOk() || this.sending()) return;
    this.sending.set(true);
    this.genError.set(null);
    this.created.set(null);
    this.api.createRun({ origin: this.origin(), horizon_days: 21, method: 'promedio_28' }).subscribe({
      next: (r) => { this.sending.set(false); this.board.track(r.job_id, r.status); },
      error: (e: AppError) => {
        this.sending.set(false);
        this.genError.set(
          e.code === 'CORTE_FUERA_DE_RANGO'
            ? `La fecha elegida está fuera del rango permitido (del ${longDate(o.origin_min)} al ${longDate(o.origin_max)}). Elige otra fecha.`
            : e.status === 422 ? `El servidor no aceptó la solicitud: ${e.message}` : `${e.message} Puedes intentarlo de nuevo.`,
        );
      },
    });
  }
}
