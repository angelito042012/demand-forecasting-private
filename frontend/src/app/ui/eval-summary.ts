import { Component, input, output } from '@angular/core';

export interface EvalPeriod { label: string; testid: string }

/**
 * UX01R: vista inicial de la evaluación. Una explicación corta del resultado principal con su alcance en palabras sencillas,
 * un aviso breve y la acción «Ver cómo se evaluó». Solo muestra texto ya derivado de los datos publicados.
 */
@Component({
  selector: 'app-eval-summary',
  template: `
    <section class="surface summary" data-testid="eval-summary" aria-label="Resumen del resultado principal">
      @if (context(); as c) { <p class="muted" data-testid="final-scope">{{ c }}</p> }
      <p class="scope" data-testid="eval-scope-simple">{{ scope() }}</p>
      <p class="explain" data-testid="eval-explain">{{ explanation() }}</p>
      @if (periods().length) {
        <ul class="plain periods" data-testid="eval-periods">@for (p of periods(); track p.testid) { <li [attr.data-testid]="p.testid">{{ p.label }}</li> }</ul>
      }
      @if (notice(); as n) { <p class="notice warn" data-testid="eval-brief-notice">{{ n }}</p> }
      <p><button type="button" class="btn" data-testid="eval-open-detail" (click)="openDetail.emit()">Ver cómo se evaluó</button></p>
    </section>
  `,
  styles: `
    .summary { border-left: 4px solid var(--accent); }
    .scope { font-weight: 600; margin-top: 0; }
    .explain { font-size: 1.15em; }
    .periods { margin: 0.4rem 0; }
  `,
})
export class EvalSummary {
  /** Contexto de una línea (qué evaluación es). */
  context = input<string | null>(null);
  /** «productos con historia suficiente · acumulado de 14 días · N productos». */
  scope = input.required<string>();
  explanation = input.required<string>();
  periods = input<EvalPeriod[]>([]);
  /** Un solo aviso pertinente y breve. */
  notice = input<string | null>(null);
  openDetail = output<void>();
}
