import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { tap } from 'rxjs';
import { ApiService } from '../core/api.service';
import { AuthService } from '../core/auth.service';
import { load } from '../core/load';
import { JobBoard } from '../core/jobs';
import { isGenerated, kindLabel } from '../core/run-choice';
import { AppError, Page, RunDetail, RunOptions, RunQuality, RunSummary } from '../core/models';
import { fmtDate, fmtInt } from '../core/format';
import { StatePanel } from '../ui/state-panel';
import { Pager } from '../ui/pager';
import { DataTree } from '../ui/data-tree';
import { JobsPanel } from '../ui/jobs-panel';
import { RunBanner, SupersededBanner, isRunInvalid } from '../ui/notices';

@Component({
  selector: 'app-runs-page',
  imports: [StatePanel, Pager, DataTree, RunBanner, SupersededBanner, RouterLink, JobsPanel],
  template: `
    <h2>Corridas</h2>
    <p class="notice info">
      Solo se listan corridas ya publicadas. Consultar no reentrena ni simula. Las corridas «generadas por la aplicación» aplican el método
      operativo promedio_28 a la historia aprobada hasta el origen; no reentrenan RF/XGBoost ni tienen backtest propio.
    </p>
    @if (isAdmin) {
      <section class="gen" aria-labelledby="h-gen" data-testid="gen-section">
        <h3 id="h-gen">Generar una corrida de desarrollo</h3>
        <app-state-panel [state]="opt.state()" (retry)="opt.reload()">
          @if (options(); as o) {
            <form (submit)="$event.preventDefault(); generate()" aria-label="Generar corrida">
              <label>Origen (fecha de corte)
                <input type="date" name="origin" data-testid="origin" [min]="o.origin_min" [max]="o.origin_max" [value]="origin()" (input)="setOrigin($any($event.target).value)" />
              </label>
              <span data-testid="horizon">Horizonte: <strong>21 días</strong> (fijo)</span>
              <span data-testid="gen-method">Método: <strong>promedio_28</strong> (fijo)</span>
              <button type="submit" data-testid="generate-btn" [disabled]="!originOk() || sending()">Generar</button>
            </form>
            <p class="muted" data-testid="origin-range">Orígenes permitidos: {{ date(o.origin_min) }} a {{ date(o.origin_max) }} (política de desarrollo; agosto sigue reservado).</p>
            @if (origin() && !originOk()) { <p class="notice warn" role="alert" data-testid="origin-warning">Ese origen no está permitido.</p> }
          }
        </app-state-panel>
        @if (genError(); as e) { <p class="notice danger" role="alert" data-testid="gen-error">{{ e }}</p> }
        <h4>Trabajos de generación recientes</h4>
        <app-jobs-panel [jobs]="board.jobs()" [listError]="board.listError()" [pollError]="board.pollError()" />
      </section>
    }
    <app-state-panel [state]="l.state()" emptyText="No hay corridas publicadas." (retry)="l.reload()">
      @if (data(); as d) {
        <div class="table-wrap" tabindex="0" role="region" aria-label="Tabla de corridas">
          <table data-testid="runs-table">
            <thead>
              <tr><th scope="col">Corrida</th><th scope="col">Etiqueta</th><th scope="col">Tipo</th><th scope="col">Estado</th><th scope="col">Motivo</th><th scope="col">Corte</th><th scope="col">Publicada (UTC)</th><th scope="col" class="num">Antigüedad (días)</th><th scope="col">Activa</th><th scope="col"><span class="sr-only">Acción</span></th></tr>
            </thead>
            <tbody>
              @for (r of d.items; track r.run_id) {
                <tr>
                  <td><code>{{ r.run_id }}</code></td><td>{{ r.run_label }}</td><td data-testid="run-kind">{{ kind(r.kind) }}</td>
                  <td>
                    @if (invalid(r)) { <span class="badge bad" data-testid="run-status">Sustituida</span> }
                    @else { <span class="badge ok" data-testid="run-status">Completada</span> }
                  </td>
                  <td data-testid="run-reason">{{ reason(r) }}</td>
                  <td>{{ date(r.cutoff) }}</td><td>{{ r.published_at }}</td>
                  <td class="num">{{ int(r.age_days_at_view) }}</td><td>{{ r.is_active ? 'Sí' : 'No' }}</td>
                  <td><button type="button" (click)="open(r.run_id)" [attr.aria-label]="'Ver detalle de la corrida ' + r.run_id">Ver detalle</button></td>
                </tr>
              }
            </tbody>
          </table>
        </div>
        <app-pager [page]="d.page" [pageSize]="d.page_size" [total]="d.total" [hasMore]="d.has_more" (go)="go($event)" />
      }
    </app-state-panel>
    @if (selected()) {
      <h3>Detalle de la corrida</h3>
      <app-state-panel [state]="detail.state()" (retry)="detail.reload()">
        @if (det(); as r) {
          <app-superseded-banner [run]="r" />
          <app-run-banner [runLabel]="r.run_label" [cutoff]="r.cutoff" [age]="r.age_days_at_view" />
          <p data-testid="detail-status">Estado: <strong>{{ invalid(r) ? 'Sustituida' : 'Completada' }}</strong> · Tipo: <strong data-testid="detail-kind">{{ kind(r.kind) }}</strong>
            @if (invalid(r)) { · {{ reason(r) }} }
            @if (r.quality_issue?.superseded_by; as nxt) { · <a [routerLink]="['/corridas']" [queryParams]="{ run: nxt }">Abrir la corrida corregida</a> }
          </p>
          <h4>Fechas</h4>
          <ul class="plain" data-testid="run-dates">
            <li>Origen: <strong>{{ date(r.origin ?? r.cutoff) }}</strong> (último día con historia usada).</li>
            @if (r.target_start) { <li>Fechas objetivo: <strong>{{ date(r.target_start) }} al {{ date(r.target_end) }}</strong>@if (r.horizon_days) { ({{ r.horizon_days }} días) }.</li> }
            @if (evalPeriod(r); as ev) { <li>Período de evaluación: <strong>{{ ev }}</strong>.</li> }
            @else if (gen(r)) { <li>Período de evaluación: no aplica; esta corrida no tiene backtest propio ni ventas observadas posteriores al origen.</li> }
          </ul>
          <p>
            <a [routerLink]="['/pronosticos']" [queryParams]="{ run: r.run_id }" data-testid="to-forecasts">Ver pronósticos de esta corrida</a> ·
            <a [routerLink]="['/recomendaciones']" [queryParams]="{ run: r.run_id }" data-testid="to-reco">Ver recomendaciones de esta corrida</a> ·
            <a [routerLink]="['/comparacion']" [queryParams]="{ run: r.run_id }" data-testid="to-compare">Ver comparación</a>
          </p>
          @if (notes(r).length) {
            <h4>Notas de procedencia</h4>
            <ul class="plain" data-testid="provenance-notes">@for (n of notes(r); track $index) { <li>{{ n }}</li> }</ul>
          }
          <h4>Método</h4>
          <ul class="plain" data-testid="method">
            <li>Método elegido: <strong>{{ r.method.chosen }}</strong> (media móvil de 28 días).</li>
            @if (r.method.comparator) { <li><strong>{{ r.method.comparator }}</strong>: comparador experimental que no ganó frente al método elegido.</li> }
            @if (r.method.control) { <li>Referencia de control: «{{ r.method.control }}» (pronóstico igual a cero, derivado).</li> }
            @if (r.method.note) { <li>{{ r.method.note }}</li> }
          </ul>
          @if (r.coverage; as c) {
            <h4>Cobertura</h4>
            <ul class="plain" data-testid="coverage">
              <li>SKU pronosticados: {{ int(c.skus_pronosticados) }}</li>
              <li>SKU con recomendación: {{ int(c.skus_con_recomendacion) }}</li>
              <li>SKU sin inventario simulado: {{ int(c.skus_sin_snapshot) }}</li>
              <li>Categorías: {{ int(c.categorias) }}</li>
            </ul>
          }
          <details class="tech" data-testid="run-doc">
            <summary>Documento completo publicado (identificadores, fuentes, checksums)</summary>
            <app-data-tree [value]="r" />
          </details>
        }
      </app-state-panel>
    }
  `,
  styles: `
    .gen { border: 1px solid var(--line); border-radius: 4px; padding: 0.5rem 0.9rem; margin: 0.6rem 0; }
    .gen form { display: flex; gap: 1rem; flex-wrap: wrap; align-items: end; }
    .sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
  `,
})
export class RunsPage {
  private api = inject(ApiService);
  private route = inject(ActivatedRoute);
  private auth = inject(AuthService);
  private destroyRef = inject(DestroyRef);
  /** Solo cosmético: el servidor rechaza igual las escrituras del lector. */
  isAdmin = this.auth.isAdmin;
  page = signal(1);
  pageSize = 50;
  l = load<Page<RunSummary>>(() => this.api.runs(this.page(), this.pageSize), (d) => d.items.length === 0);
  data = computed(() => { const s = this.l.state(); return s.kind === 'data' ? s.data : null; });
  selected = signal<string | null>(null);
  detail = load<RunDetail>(() => this.api.runDetail(this.selected()!), () => false, false);
  det = computed(() => { const s = this.detail.state(); return s.kind === 'data' ? s.data : null; });

  // ---- Generación (admin) ----
  board = new JobBoard(this.api, 'generate_run', () => this.l.reload(), this.destroyRef);
  opt = load<RunOptions>(
    () => this.api.runOptions().pipe(tap((o) => { if (!this.origin()) this.origin.set(o.origin_default); })),
    () => false, false,
  );
  options = computed(() => { const s = this.opt.state(); return s.kind === 'data' ? s.data : null; });
  origin = signal('');
  sending = signal(false);
  genError = signal<string | null>(null);
  /** Solo valores dentro de [origin_min, origin_max] publicados por la API (el servidor revalida). */
  originOk = computed(() => {
    const o = this.options(); const v = this.origin();
    return !!o && /^\d{4}-\d{2}-\d{2}$/.test(v) && v >= o.origin_min && v <= o.origin_max;
  });

  constructor() {
    // Enlace desde el aviso de corrida sustituida: /corridas?run=<id> abre el detalle de la corrida corregida.
    this.route.queryParamMap.pipe(takeUntilDestroyed()).subscribe((q) => {
      const id = q.get('run');
      if (id && id !== this.selected()) this.open(id);
    });
    if (this.isAdmin) {
      this.board.loadRecent();
      this.opt.reload();
    }
  }

  setOrigin(v: string) { this.origin.set(v); this.genError.set(null); }

  generate() {
    const o = this.options();
    if (!o || !this.originOk() || this.sending()) return;
    this.sending.set(true);
    this.genError.set(null);
    this.api.createRun({ origin: this.origin(), horizon_days: 21, method: 'promedio_28' }).subscribe({
      next: (r) => { this.sending.set(false); this.board.track(r.job_id, r.status); },
      error: (e: AppError) => {
        this.sending.set(false);
        this.genError.set(
          e.code === 'CORTE_FUERA_DE_RANGO'
            ? `El origen elegido está fuera del rango permitido (${fmtDate(o.origin_min)} a ${fmtDate(o.origin_max)}).`
            : e.status === 422 ? `El servidor rechazó la solicitud: ${e.message}` : e.message,
        );
      },
    });
  }

  int = (v: unknown) => fmtInt(v);
  date = (v: string | null | undefined) => fmtDate(v);
  invalid = (r: RunQuality) => isRunInvalid(r);
  kind = (k: string | undefined) => kindLabel(k);
  gen = (r: RunDetail) => isGenerated(r.kind);
  evalPeriod(r: RunDetail): string | null {
    const e = r.evaluation_period as { start?: string; end?: string } | null | undefined;
    return e?.start && e?.end ? `${fmtDate(e.start)} al ${fmtDate(e.end)}` : null;
  }
  notes(r: RunDetail): string[] {
    const n = r.provenance_notes;
    return !n ? [] : Array.isArray(n) ? n : [n];
  }
  reason(r: RunSummary | RunDetail): string {
    if (!isRunInvalid(r)) return '—';
    const q = r.quality_issue;
    return q?.reason ?? q?.message ?? 'Sustituida por una corrección de precisión (recomendaciones con error de redondeo); no use sus pedidos.';
  }

  go(p: number) { this.page.set(p); this.l.reload(); }
  open(id: string) { this.selected.set(id); this.detail.reload(); }
}
