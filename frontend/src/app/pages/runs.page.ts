import { Component, DestroyRef, computed, inject, input, output, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ApiService } from '../core/api.service';
import { AuthService } from '../core/services/auth.service';
import { RunChoice, isFinal, isGenerated, kindLabel } from '../core/run-choice';
import { RunsStore } from '../core/runs-store';
import { FinalPackage, LoadState, RunDetail, RunSummary } from '../core/models';
import { fmtDate, fmtInt } from '../core/utils/format';
import { analysisName, analysisPurpose, isReplaced, kindWords, longDate, runStatusChip } from '../core/utils/ux-text';
import { PageHeader } from '../shared/components/page-header';
import { StatePanel } from '../shared/components/state-panel';
import { DataTree } from '../shared/components/data-tree';
import { FinalWarnings } from '../shared/components/notices';
import { CardModule } from 'primeng/card';
import { ButtonModule } from 'primeng/button';
import { TagModule } from 'primeng/tag';
import { MessageModule } from 'primeng/message';

function periodWords(r: Pick<RunSummary, 'target_start' | 'target_end'>): string {
  return r.target_start && r.target_end ? `del ${longDate(r.target_start)} al ${longDate(r.target_end)}` : '';
}

@Component({
  selector: 'app-run-tech',
  imports: [RouterLink, DataTree, FinalWarnings],
  template: `
    @let r = detail();
    <p data-testid="detail-status">Estado: <strong>{{ invalid() ? 'Versión reemplazada' : 'Completada' }}</strong> · Tipo: <strong data-testid="detail-kind">{{ kind(r.kind) }}</strong>
      · Identificador: <code data-testid="detail-id">{{ r.run_id }}</code>
      @if (invalid()) { · <span data-testid="detail-reason">{{ reason() }}</span> }
      @if (r.quality_issue?.superseded_by; as nxt) { · <a [routerLink]="['/corridas']" [queryParams]="{ run: nxt }">Abrir el análisis corregido</a> }
    </p>
    <p class="muted">Nombre original: {{ r.run_label }} · publicado (UTC): {{ r.published_at }} · antigüedad al consultar: {{ int(r.age_days_at_view) }} día(s)</p>
    @if (isFin(r.kind)) {
      <app-final-warnings [warnings]="r.warnings" />
      <section class="pkg" data-testid="final-package" aria-labelledby="h-pkg">
        <h4 id="h-pkg">Paquete de la evaluación final</h4>
        @if (r.final_package; as p) {
          <ul class="plain">
            <li>Sello del paquete: <code data-testid="pkg-seal">{{ seal(p) }}</code></li>
            <li data-testid="pkg-audit">Auditoría separada: <strong>{{ auditText(p) }}</strong></li>
          </ul>
          <div class="table-wrap" tabindex="0" role="region" aria-label="Fases del paquete final">
            <table data-testid="pkg-phases">
              <caption>Fases ({{ phases(p).length }})</caption>
              <thead><tr><th scope="col">Fase</th><th scope="col">Estado</th></tr></thead>
              <tbody>@for (ph of phases(p); track ph[0]) { <tr><td>{{ ph[0] }}</td><td>{{ ph[1] }}</td></tr> }</tbody>
            </table>
          </div>
          @if (corrections(p).length) {
            <h5>Correcciones técnicas posteriores</h5>
            <ul class="plain" data-testid="pkg-corrections">@for (c of corrections(p); track $index) { <li>{{ c }}</li> }</ul>
          } @else { <p class="muted" data-testid="pkg-no-corrections">Sin correcciones técnicas posteriores publicadas.</p> }
        } @else { <p class="muted" data-testid="pkg-missing">La API no publicó el resumen del paquete de este análisis.</p> }
      </section>
    }
    <h4>Fechas</h4>
    <ul class="plain" data-testid="run-dates">
      <li>Origen (ventas utilizadas hasta): <strong>{{ date(r.origin ?? r.cutoff) }}</strong> (último día con historia usada).</li>
      @if (r.target_start) { <li>Fechas objetivo: <strong>{{ date(r.target_start) }} al {{ date(r.target_end) }}</strong>@if (r.horizon_days) { ({{ r.horizon_days }} días) }.</li> }
      @if (evalPeriod(r); as ev) { <li>Período de evaluación: <strong>{{ ev }}</strong>.</li> }
      @else if (gen(r)) { <li>Período de evaluación: no aplica; este análisis no tiene comparación propia con ventas registradas ni ventas observadas posteriores al origen.</li> }
    </ul>
    @if (notes(r).length) {
      <h4>Notas de procedencia</h4>
      <ul class="plain" data-testid="provenance-notes">@for (n of notes(r); track $index) { <li>{{ n }}</li> }</ul>
    }
    <h4>Método</h4>
    <ul class="plain" data-testid="method">
      <li>Método elegido: <strong>{{ r.method.chosen }}</strong> (promedio de los últimos 28 días).</li>
      @if (isFin(r.kind) && r.method.comparator) { <li><strong>{{ r.method.comparator }}</strong>: comparador; con un solo bloque no se declara ganador (declarado ganador: {{ r.method.rf_declared_winner === false ? 'no' : 'sin dato' }}).</li> }
      @else if (r.method.comparator) { <li><strong>{{ r.method.comparator }}</strong>: comparador experimental que no ganó frente al método elegido.</li> }
      @if (r.method.control) { <li>Referencia de control: «{{ r.method.control }}» (estimación igual a cero, derivada).</li> }
      @if (r.method.note) { <li>{{ r.method.note }}</li> }
    </ul>
    @if (r.coverage && isFin(r.kind)) {
      <h4>Cobertura de la evaluación final</h4>
      <ul class="plain" data-testid="coverage">@for (kv of scalars(r.coverage); track kv[0]) { <li>{{ kv[0] }}: <strong>{{ kv[1] }}</strong></li> }</ul>
      <details class="tech"><summary>Cobertura completa tal como se publicó</summary><app-data-tree [value]="r.coverage" /></details>
    } @else if (r.coverage; as c) {
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
  `,
  styles: `.pkg { border: 1px solid var(--line); border-radius: var(--radius); padding: 0.3rem 0.9rem; margin: 0.6rem 0; }`,
})
export class RunTech {
  detail = input.required<RunDetail>();
  int = (v: unknown) => fmtInt(v);
  date = (v: string | null | undefined) => fmtDate(v);
  invalid = computed(() => isReplaced(this.detail()));
  kind = (k: string | undefined) => kindLabel(k);
  gen = (r: RunDetail) => isGenerated(r.kind);
  isFin = (k: string | undefined | null) => isFinal(k);
  reason = computed(() => {
    const q = this.detail().quality_issue;
    return q?.reason ?? q?.message ?? 'Reemplazada por una corrección de precisión; no uses sus sugerencias.';
  });
  seal = (p: FinalPackage) => p.seal_short || (p.seal_sha256 ? p.seal_sha256.slice(0, 12) : 'sin dato');
  auditText = (p: FinalPackage) => (p.audit_ok === true ? 'aprobada' : p.audit_ok === false ? 'NO aprobada' : 'sin dato');
  phases(p: FinalPackage): [string, string][] {
    return Object.entries(p.phases ?? {}).map(([k, v]) => [k, typeof v === 'string' ? v : (v?.estado ?? 'sin dato')]);
  }
  corrections(p: FinalPackage): string[] {
    return (p.corrections ?? []).map((c) => typeof c === 'string' ? c : this.scalars(c).map((kv) => `${kv[0]}: ${kv[1]}`).join(' · '));
  }
  scalars(o: object): [string, string][] {
    return Object.entries(o).filter(([, v]) => ['string', 'number', 'boolean'].includes(typeof v)).map(([k, v]) => [k, String(v)]);
  }
  evalPeriod(r: RunDetail): string | null {
    const e = r.evaluation_period as { start?: string; end?: string } | null | undefined;
    return e?.start && e?.end ? `${fmtDate(e.start)} al ${fmtDate(e.end)}` : null;
  }
  notes(r: RunDetail): string[] {
    const n = r.provenance_notes;
    return !n ? [] : Array.isArray(n) ? n : [n];
  }
}

@Component({
  selector: 'app-analysis-card',
  imports: [RouterLink, StatePanel, RunTech, CardModule, ButtonModule, TagModule, MessageModule],
  template: `
    @let r = run();
    <p-card [attr.data-testid]="'run-card-' + r.run_id" [styleClass]="consulting() ? 'border-primary' : ''">
      <ng-template #header>
        <div class="card-header">
          <h2 data-testid="run-name">{{ name() }}</h2>
          <div class="flex flex-wrap gap-2">
            <p-tag [severity]="tagSeverity()" [value]="chip().text" data-testid="run-status" />
            <p-tag severity="secondary" [value]="kindText()" data-testid="run-kind" />
            @if (consulting()) { <p-tag severity="info" value="Estás consultando este análisis" data-testid="run-consulting" /> }
          </div>
        </div>
      </ng-template>
      <p class="muted" data-testid="run-purpose">{{ purpose() }}</p>
      <p data-testid="run-used">Ventas utilizadas hasta el <strong>{{ used() }}</strong></p>
      @if (period(); as p) { <p data-testid="run-period">Período estimado: <strong>{{ p }}</strong></p> }
      @if (replaced()) {
        <p-message severity="error" role="alert" data-testid="replaced-notice" styleClass="w-full my-2">
          <strong>Esta versión fue reemplazada. No uses sus sugerencias.</strong>
          @if (r.quality_issue?.superseded_by; as nxt) { <a [routerLink]="['/corridas']" [queryParams]="{ run: nxt }" data-testid="replaced-link">Ver el análisis corregido</a> }
        </p-message>
      }
      <ng-template #footer>
        <div class="flex flex-wrap gap-2">
          <p-button label="Ver previsión" icon="pi pi-chart-bar" [outlined]="!primary()" [routerLink]="['/evaluacion/ventas-previstas']" [queryParams]="{ run: r.run_id }" data-testid="to-forecasts" />
          @if (!final()) { <p-button label="Ver reposición" icon="pi pi-box" [outlined]="true" [routerLink]="['/recomendaciones']" [queryParams]="{ run: r.run_id }" data-testid="to-reco" /> }
          <p-button label="Ver evaluación" icon="pi pi-check-circle" [outlined]="true" [routerLink]="['/comparacion']" [queryParams]="{ run: r.run_id }" data-testid="to-compare" />
          @if (!consulting()) { <p-button label="Elegir este análisis" icon="pi pi-check" [outlined]="true" (onClick)="pick.emit(r.run_id)" data-testid="choose" /> }
        </div>
      </ng-template>
    </p-card>
    <details class="tech" [attr.data-testid]="'tech-' + r.run_id" (toggle)="onToggle($event)">
      <summary>Detalles técnicos</summary>
      @if (opened()) {
        @if (detail(); as st) {
          <app-state-panel [state]="st" (retry)="techOpen.emit(r.run_id)">
            @if (doc(); as d) { <app-run-tech [detail]="d" /> }
          </app-state-panel>
        }
      }
    </details>
  `,
  styles: `
    .card-header { padding: 1rem 1rem 0; }
    .card-header h2 { margin: 0 0 0.5rem; font-size: 1.15rem; }
    :host ::ng-deep .border-primary { border: 2px solid var(--accent); }
  `,
})
export class AnalysisCard {
  run = input.required<RunSummary>();
  consulting = input(false);
  primary = input(false);
  detail = input<LoadState<RunDetail> | null | undefined>(null);
  pick = output<string>();
  techOpen = output<string>();
  opened = signal(false);

  name = computed(() => analysisName(this.run()));
  chip = computed(() => runStatusChip(this.run(), this.consulting()));
  kindText = computed(() => kindWords(this.run().kind));
  purpose = computed(() => analysisPurpose(this.run()));
  used = computed(() => longDate(this.run().origin ?? this.run().cutoff));
  period = computed(() => periodWords(this.run()));
  replaced = computed(() => isReplaced(this.run()));
  final = computed(() => isFinal(this.run().kind));
  reason = computed(() => {
    const q = this.run().quality_issue;
    return q?.reason ?? q?.message ?? 'Reemplazada por una corrección de precisión; no uses sus sugerencias.';
  });
  doc = computed(() => { const s = this.detail(); return s && s.kind === 'data' ? s.data : null; });
  tagSeverity = computed(() => {
    const t = this.chip().tone;
    return t === 'ok' ? 'success' : t === 'bad' ? 'danger' : 'info';
  });

  onToggle(ev: Event) {
    const open = (ev.target as HTMLDetailsElement).open;
    this.opened.set(open);
    if (open) this.techOpen.emit(this.run().run_id);
  }
}

@Component({
  selector: 'app-runs-page',
  imports: [RouterLink, PageHeader, StatePanel, AnalysisCard, ButtonModule],
  template: `
    <app-page-header title="Mis análisis"
      lead="Elige qué resultado quieres consultar. Elegir un análisis solo cambia lo que ves; no modifica cuál se usa por defecto." />
    @if (isAdmin) {
      <div class="mb-3">
        <p-button label="Crear un análisis nuevo" icon="pi pi-plus" [outlined]="true" [routerLink]="['/crear-analisis']" queryParamsHandling="preserve" data-testid="to-create" />
      </div>
    }
    <app-state-panel [state]="store.state()" (retry)="store.refresh()">
      @if (current().length === 0 && old().length === 0) {
        <p class="state" data-testid="runs-empty">Todavía no hay análisis publicados. @if (isAdmin) { <a [routerLink]="['/crear-analisis']">Crear un análisis</a> } @else { Pide al administrador que cree uno. }</p>
      }
      <section class="cards" aria-label="Análisis disponibles" data-testid="runs-list">
        @for (r of current(); track r.run_id) {
          <app-analysis-card [run]="r" [consulting]="consulting(r)" [primary]="r.is_active" [detail]="details()[r.run_id]"
            (pick)="choice.set($event)" (techOpen)="loadDetail($event)" />
        }
      </section>
      @if (hasMore()) { <p class="muted" data-testid="runs-more">Se muestran los primeros {{ shown() }} análisis publicados.</p> }
      @if (old().length) {
        <details class="help" data-testid="old-versions" [open]="oldOpen()">
          <summary>Ver versiones anteriores ({{ old().length }})</summary>
          <p class="muted">Son versiones reemplazadas por una corrección. Se conservan para consulta; no uses sus sugerencias.</p>
          <section class="cards" aria-label="Versiones anteriores">
            @for (r of old(); track r.run_id) {
              <app-analysis-card [run]="r" [consulting]="consulting(r)" [detail]="details()[r.run_id]"
                (pick)="choice.set($event)" (techOpen)="loadDetail($event)" />
            }
          </section>
        </details>
      }
    </app-state-panel>
  `,
})
export class RunsPage {
  private api = inject(ApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private auth = inject(AuthService);
  private destroyRef = inject(DestroyRef);
  protected store = inject(RunsStore);
  isAdmin = this.auth.isAdmin;
  choice = new RunChoice(this.route, this.router, this.destroyRef, () => undefined);
  details = signal<Record<string, LoadState<RunDetail>>>({});

  current = computed(() => {
    const l = this.store.runs().filter((r) => !isReplaced(r));
    return [...l.filter((r) => r.is_active), ...l.filter((r) => !r.is_active)];
  });
  old = computed(() => this.store.runs().filter((r) => isReplaced(r)));
  oldOpen = computed(() => { const id = this.choice.id(); return !!id && this.old().some((r) => r.run_id === id); });
  shown = computed(() => this.store.runs().length);
  hasMore = computed(() => { const s = this.store.state(); return s.kind === 'data' && s.data.has_more; });

  constructor() { this.store.ensure(); }

  consulting(r: RunSummary): boolean {
    const id = this.choice.id();
    return id ? r.run_id === id : r.is_active;
  }

  loadDetail(id: string) {
    const cur = this.details()[id];
    if (cur && cur.kind !== 'error') return;
    this.details.update((d) => ({ ...d, [id]: { kind: 'loading' } }));
    this.api.runDetail(id).subscribe({
      next: (data) => this.details.update((d) => ({ ...d, [id]: { kind: 'data', data } })),
      error: (error) => this.details.update((d) => ({ ...d, [id]: { kind: 'error', error } })),
    });
  }
}
