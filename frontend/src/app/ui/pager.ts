import { Component, computed, input, output } from '@angular/core';

@Component({
  selector: 'app-pager',
  template: `
    <nav class="pg" aria-label="Paginación">
      <button type="button" data-testid="prev" [disabled]="page() <= 1" (click)="go.emit(page() - 1)">Anterior</button>
      <span data-testid="pg-info">Página {{ page() }} de {{ pages() }} · {{ total() }} registro(s)</span>
      <button type="button" data-testid="next" [disabled]="!hasMore()" (click)="go.emit(page() + 1)">Siguiente</button>
    </nav>
  `,
  styles: `.pg { display: flex; gap: 1rem; align-items: center; margin: 0.5rem 0; }`,
})
export class Pager {
  page = input.required<number>();
  pageSize = input.required<number>();
  total = input.required<number>();
  hasMore = input.required<boolean>();
  go = output<number>();
  pages = computed(() => Math.max(1, Math.ceil(this.total() / this.pageSize())));
}
