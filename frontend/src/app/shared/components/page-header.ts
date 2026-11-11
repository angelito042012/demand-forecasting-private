import { Component, input } from '@angular/core';

/** Encabezado común de pantalla: un título claro y una línea de propósito. */
@Component({
  selector: 'app-page-header',
  template: `
    <header class="ph">
      <h1 data-testid="page-title">{{ title() }}</h1>
      @if (lead(); as l) { <p class="lead" data-testid="page-lead">{{ l }}</p> }
      <ng-content />
    </header>
  `,
  styles: `.ph { margin: 0.2rem 0 1rem; }`,
})
export class PageHeader {
  title = input.required<string>();
  lead = input<string | null>(null);
}
