import { Component, input, output } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AppError, PublicJob } from '../core/models';
import { STATUS_LABELS, TYPE_LABELS, stageLabel, summarize } from '../core/jobs';
import { fmtInt } from '../core/format';

/** Lista de trabajos recientes con etapa, conteos reales y resultado legible. Solo muestra lo que publica la API. */
@Component({
  selector: 'app-jobs-panel',
  imports: [RouterLink],
  template: `
    @if (listError(); as e) {
      <p class="state err" role="alert" data-testid="jobs-error">No se pudo leer la lista de trabajos: {{ e.message }}</p>
    }
    @if (pollError(); as e) {
      <p class="notice warn" role="status" data-testid="poll-error">No se pudo actualizar el estado del trabajo: {{ e.message }}</p>
    }
    @if (jobs().length === 0 && !listError()) {
      <p class="state" data-testid="jobs-empty">Todavía no hay trabajos registrados.</p>
    }
    @for (j of jobs(); track j.job_id) {
      @let s = summarize(j);
      <article class="job" [attr.data-testid]="'job-' + j.job_id" [attr.data-status]="j.status" aria-live="polite">
        <header>
          <strong>{{ typeLabel(j) }}</strong>
          <span class="badge" [class.ok]="j.status === 'completed'" [class.bad]="j.status === 'failed'" data-testid="job-status">{{ statusLabel(j) }}</span>
          <code>{{ j.job_id }}</code>
          @if (j.created_at) { <span class="muted">creado {{ j.created_at }}</span> }
        </header>
        @if (j.status === 'queued' || j.status === 'running') {
          <p data-testid="job-stage">Etapa: <strong>{{ stage(j) }}</strong>
            @if (j.attempts) { · intento {{ j.attempts }}@if (j.max_attempts) { de {{ j.max_attempts }} } }
          </p>
          @if (s.counts.length) {
            <ul class="plain" data-testid="job-progress">
              @for (c of s.counts; track c[0]) { <li>{{ c[0] }}: {{ c[1] }}</li> }
            </ul>
          }
        } @else {
          <p data-testid="job-outcome"><strong>{{ s.title }}</strong>@if (s.detail) { . {{ s.detail }} }</p>
          @if (s.counts.length) {
            <ul class="plain" data-testid="job-counts">
              @for (c of s.counts; track c[0]) { <li>{{ c[0] }}: {{ c[1] }}</li> }
            </ul>
          }
          @if (s.rejectMotives.length) {
            <ul class="plain" data-testid="job-motives">
              @for (m of s.rejectMotives; track m[0]) { <li>Rechazo «{{ m[0] }}»: {{ int(m[1]) }}</li> }
            </ul>
          }
          @if (s.importId) { <button type="button" data-testid="job-import-link" (click)="openImport.emit(s.importId!)">Ver detalle de la importación</button> }
          @if (s.runId) { <a data-testid="job-run-link" [routerLink]="['/corridas']" [queryParams]="{ run: s.runId }">Ver la corrida generada</a> }
        }
      </article>
    }
  `,
  styles: `
    .job { border: 1px solid var(--line); border-radius: 4px; padding: 0.5rem 0.8rem; margin: 0.5rem 0; }
    .job header { display: flex; gap: 0.6rem; flex-wrap: wrap; align-items: baseline; }
  `,
})
export class JobsPanel {
  jobs = input.required<PublicJob[]>();
  listError = input<AppError | null>(null);
  pollError = input<AppError | null>(null);
  openImport = output<string>();
  summarize = summarize;
  stage = stageLabel;
  int = (v: unknown) => fmtInt(v);
  typeLabel = (j: PublicJob) => TYPE_LABELS[j.type] ?? j.type;
  statusLabel = (j: PublicJob) => STATUS_LABELS[j.status] ?? j.status;
}
