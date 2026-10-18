import { Component, computed, inject, input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { RunsStore } from '../core/runs-store';
import { fmtDate } from '../core/format';
import { ageWords, analysisName, isReplaced, kindWords, periodText, runStatusChip } from '../core/ux-text';

/**
 * Franja de contexto del análisis consultado: nombre, ventas utilizadas hasta, período estimado y estado, siempre en palabras
 * sencillas. Los identificadores quedan en «Detalles técnicos». Si el análisis fue reemplazado, el aviso es destacado y breve.
 */
@Component({
  selector: 'app-analysis-bar',
  imports: [RouterLink],
  template: `
    @if (run(); as r) {
      <section class="bar" data-testid="analysis-bar" aria-label="Análisis que estás consultando">
        <p class="line">
          <span class="lbl">Análisis:</span> <strong data-testid="analysis-name">{{ name() }}</strong>
          <span class="chip" [class.ok]="chip().tone === 'ok'" [class.info]="chip().tone === 'info'" [class.bad]="chip().tone === 'bad'" data-testid="analysis-status">{{ chip().text }}</span>
          <a [routerLink]="['/corridas']" [queryParams]="runId() ? { run: runId() } : {}" data-testid="analysis-change">Cambiar de análisis</a>
        </p>
        <p class="line">
          <span data-testid="analysis-used">Ventas utilizadas hasta el <strong>{{ used() }}</strong>{{ " " }}<span class="muted">({{ age() }}; datos históricos, no las ventas de hoy)</span></span>
          @if (period(); as p) { <span> · Período estimado: <strong data-testid="analysis-period">{{ p }}</strong></span> }
        </p>
        @if (replaced()) {
          <div class="notice danger" role="alert" data-testid="analysis-replaced">
            <strong>Esta versión fue reemplazada. No uses sus sugerencias.</strong>
            @if (correctedId(); as id) { <a [routerLink]="['/corridas']" [queryParams]="{ run: id }" data-testid="analysis-corrected">Ver el análisis corregido</a> }
            @if (reason(); as why) { <details class="tech"><summary>Motivo</summary><p data-testid="analysis-reason">{{ why }}</p></details> }
          </div>
        }
        <details class="tech">
          <summary>Detalles técnicos del análisis</summary>
          <p>Tipo: {{ kindText() }} · identificador: <code data-testid="analysis-id">{{ r.run_id }}</code> · tipo interno: <code>{{ r.kind }}</code></p>
        </details>
      </section>
    } @else if (status() === 'error') {
      <div class="notice danger" role="alert" data-testid="analysis-error">
        <p><strong>No pudimos cargar tus análisis.</strong> Revisa tu conexión o inténtalo en unos minutos; lo que elegiste no se cambió.</p>
        <button type="button" class="secondary small" data-testid="analysis-retry" (click)="retry()">Reintentar</button>
      </div>
    } @else if (status() === 'loading') {
      <p class="muted" role="status" data-testid="analysis-loading">Cargando el análisis…</p>
    } @else if (empty()) {
      <p class="notice info" role="status" data-testid="analysis-none">Todavía no hay análisis publicados para consultar.</p>
    } @else {
      <p class="notice warn" role="status" data-testid="analysis-missing">
        @if (more()) { No encontramos ese análisis entre los más recientes; no podemos confirmar si existe. } @else { No se encontró el análisis elegido. }
        <a [routerLink]="['/corridas']">Elegir otro análisis</a>
      </p>
    }
  `,
  styles: `
    .bar { background: var(--surface); border: 1px solid var(--line); border-left: 4px solid var(--accent); border-radius: var(--radius); padding: 0.6rem 1rem; margin: 0.4rem 0 1rem; }
    .line { margin: 0.25rem 0; display: flex; flex-wrap: wrap; gap: 0.3rem 0.6rem; align-items: baseline; }
    .lbl { color: var(--muted); }
    details { margin: 0.3rem 0 0; }
  `,
})
export class AnalysisBar {
  private store = inject(RunsStore);
  /** Valor del parámetro `run` de la dirección (null = el análisis en uso por defecto). */
  runId = input<string | null>(null);
  constructor() { this.store.ensure(); }
  retry() { this.store.retry(); }
  run = computed(() => this.store.resolve(this.runId()));
  status = computed(() => { const k = this.store.state().kind; return k === 'data' ? (this.store.runs().length ? 'ok' : 'empty') : k; });
  empty = computed(() => this.status() === 'empty');
  more = computed(() => this.store.hasMore());
  name = computed(() => analysisName(this.run()));
  chip = computed(() => { const r = this.run(); return r ? runStatusChip(r, !!this.runId()) : { text: '', tone: '' as const }; });
  used = computed(() => fmtDate(this.run()?.origin ?? this.run()?.cutoff));
  age = computed(() => ageWords(this.run()?.age_days_at_view));
  period = computed(() => { const r = this.run(); return r ? periodText(r) : ''; });
  replaced = computed(() => isReplaced(this.run()));
  correctedId = computed(() => this.run()?.quality_issue?.superseded_by ?? null);
  reason = computed(() => { const q = this.run()?.quality_issue; return q?.reason ?? q?.message ?? null; });
  kindText = computed(() => kindWords(this.run()?.kind));
}
