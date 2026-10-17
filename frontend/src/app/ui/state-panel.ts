import { Component, input, output } from '@angular/core';
import { LoadState } from '../core/models';

@Component({
  selector: 'app-state-panel',
  template: `
    @switch (state().kind) {
      @case ('loading') {
        <p class="state" role="status" data-state="loading">Cargando…</p>
      }
      @case ('empty') {
        <p class="state" data-state="empty">{{ emptyText() }}</p>
      }
      @case ('error') {
        <div class="state err" role="alert" data-state="error" [attr.data-code]="code()">
          @if (code() === 'SESION_EXPIRADA') {
            <p>Su sesión venció. <a href="/acceso">Ingrese de nuevo</a>.</p>
          } @else {
            <p>{{ errorMessage() }}</p>
          }
          <button type="button" (click)="retry.emit()">Reintentar</button>
        </div>
      }
      @case ('data') {
        <div data-state="data"><ng-content /></div>
      }
    }
  `,
})
export class StatePanel {
  state = input.required<LoadState<unknown>>();
  emptyText = input('Sin datos para mostrar.');
  retry = output<void>();
  errorMessage() {
    const s = this.state();
    return s.kind === 'error' ? s.error.message : '';
  }
  code() {
    const s = this.state();
    return s.kind === 'error' ? s.error.code : '';
  }
}
