import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { tap } from 'rxjs';
import { ApiService } from '../core/api.service';
import { AuthService } from '../core/auth.service';
import { load } from '../core/load';
import { JobBoard, summarize } from '../core/jobs';
import { RunsStore } from '../core/runs-store';
import { AppError, RunOptions } from '../core/models';
import { longDate } from '../core/ux-text';
import { PageHeader } from '../ui/page-header';
import { StatePanel } from '../ui/state-panel';
import { JobsPanel } from '../ui/jobs-panel';

/**
 * Crear análisis (solo administrador; el servidor decide). Se extrae de la antigua pantalla de corridas sin ampliar rangos
 * ni quitar controles: el origen solo puede estar dentro de [origin_min, origin_max] que publica la API.
 */
@Component({
  selector: 'app-create-run-page',
  imports: [RouterLink, PageHeader, StatePanel, JobsPanel],
  template: `
    <app-page-header title="Crear análisis" lead="Crea un análisis nuevo con el promedio de los últimos 28 días para las fechas elegidas; no reentrena modelos." />
    @if (!isAdmin) {
      <p class="notice info" role="status" data-testid="admin-only">Solo el administrador puede crear análisis.</p>
      <p><a class="btn secondary" [routerLink]="['/corridas']" queryParamsHandling="preserve">Ir a Mis análisis</a></p>
    } @else {
      <section class="surface" aria-labelledby="h-gen" data-testid="gen-section">
        <h2 id="h-gen">Elegir las ventas que se usarán</h2>
        <app-state-panel [state]="opt.state()" (retry)="opt.reload()">
          @if (options(); as o) {
            <form class="filters" (submit)="$event.preventDefault(); generate()" aria-label="Crear análisis">
              <label>Ventas utilizadas hasta (fecha)
                <input type="date" name="origin" data-testid="origin" [min]="o.origin_min" [max]="o.origin_max" [value]="origin()" (input)="setOrigin($any($event.target).value)" />
              </label>
              <span data-testid="horizon">Período estimado: <strong>los 21 días siguientes</strong> (fijo)</span>
              <span data-testid="gen-method">Método: <strong>promedio de los últimos 28 días</strong> (promedio_28, fijo)</span>
              <button type="submit" class="btn" data-testid="generate-btn" [disabled]="!originOk() || sending()">Crear análisis</button>
            </form>
            <p class="muted" data-testid="origin-range">Fechas permitidas en esta versión: del {{ date(o.origin_min) }} al {{ date(o.origin_max) }}. Agosto sigue reservado.</p>
            @if (origin() && !originOk()) { <p class="notice warn" role="alert" data-testid="origin-warning">Esa fecha no está permitida. Elige una fecha entre el {{ date(o.origin_min) }} y el {{ date(o.origin_max) }}.</p> }
          }
        </app-state-panel>
        @if (genError(); as e) { <p class="notice danger" role="alert" data-testid="gen-error">{{ e }}</p> }
        @if (created(); as c) {
          <div class="notice ok" role="status" data-testid="gen-done">
            <p><strong>Listo: el análisis se creó.</strong> Ya puedes consultar sus ventas previstas.</p>
            <p class="actions">
              <a class="btn secondary" [routerLink]="['/evaluacion/ventas-previstas']" [queryParams]="{ run: c }" data-testid="gen-view">Ver previsión</a>
              <a class="btn secondary" [routerLink]="['/corridas']" [queryParams]="{ run: c }" data-testid="gen-view-runs">Ver en Mis análisis</a>
            </p>
          </div>
        }
      </section>
      <h2>Trabajos recientes</h2>
      <app-jobs-panel [jobs]="board.jobs()" [listError]="board.listError()" [pollError]="board.pollError()" />
    }
  `,
  styles: `.actions { display: flex; flex-wrap: wrap; gap: 0.5rem; }`,
})
export class CreateRunPage {
  private api = inject(ApiService);
  private auth = inject(AuthService);
  private store = inject(RunsStore);
  private destroyRef = inject(DestroyRef);
  /** Solo orientación: el servidor rechaza igual las escrituras del lector. */
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
  /** Id del último análisis creado en esta pantalla (para ofrecer «Ver previsión»). */
  created = signal<string | null>(null);
  /** Solo valores dentro de [origin_min, origin_max] publicados por la API (el servidor revalida). */
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
