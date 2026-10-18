import { Component, input } from '@angular/core';

/** UX01: conclusión corta al inicio de cada sección de la evaluación. Solo muestra texto ya calculado de los datos. */
@Component({
  selector: 'app-eval-conclusion',
  template: `
    <section class="surface concl" [attr.data-testid]="testid()" [attr.aria-label]="heading()">
      <h3>{{ heading() }}</h3>
      @if (scope(); as s) { <p class="muted" data-testid="eval-scope">{{ s }}</p> }
      @for (l of lines(); track $index) { <p>{{ l }}</p> }
    </section>
  `,
  styles: `
    .concl { border-left: 4px solid var(--accent); }
    h3 { margin-top: 0; }
  `,
})
export class EvalConclusion {
  heading = input('Conclusión');
  /** Alcance: nivel, tipo de historial, período y bloque. */
  scope = input<string | null>(null);
  lines = input<string[]>([]);
  testid = input('eval-conclusion');
}
