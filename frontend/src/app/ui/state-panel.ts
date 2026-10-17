import { Component, input, output } from '@angular/core';
import { LoadState } from '../core/models';
import { DemoBadge } from './demo-badge';

@Component({
  selector: 'app-state-panel',
  imports: [DemoBadge],
  template: `
    @switch (state().kind) {
      @case ('loading') {
        <p class="st" role="status" data-state="loading">Cargando…</p>
      }
      @case ('empty') {
        <p class="st" data-state="empty">Sin datos para mostrar.</p>
      }
      @case ('error') {
        <div class="st err" role="alert" data-state="error">
          <p>Error: {{ errorMessage() }}</p>
          <button type="button" (click)="retry.emit()">Reintentar</button>
        </div>
      }
      @case ('data') {
        <div data-state="data">
          @if (provenance(); as p) {
            <app-demo-badge [provenance]="p" />
          }
          <ng-content />
        </div>
      }
    }
  `,
  styles: `
    .st { padding: 1rem; border: 1px dashed #999; border-radius: 4px; }
    .err { border-color: #b02a37; color: #842029; }
  `,
})
export class StatePanel {
  state = input.required<LoadState<unknown>>();
  retry = output<void>();
  errorMessage() {
    const s = this.state();
    return s.kind === 'error' ? s.message : '';
  }
  provenance() {
    const s = this.state();
    return s.kind === 'data' ? s.provenance : null;
  }
}
