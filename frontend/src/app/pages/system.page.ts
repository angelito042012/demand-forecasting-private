import { Component, computed, inject } from '@angular/core';
import { ApiService } from '../core/api.service';
import { load } from '../core/load';
import { Health } from '../core/models';
import { StatePanel } from '../ui/state-panel';

@Component({
  selector: 'app-system-page',
  imports: [StatePanel],
  template: `
    <h2>Estado del sistema</h2>
    <app-state-panel [state]="l.state()" (retry)="l.reload()">
      @if (info(); as h) {
        <ul data-testid="health">
          <li>Estado general: <strong>{{ h.status === 'ok' ? 'operativo' : 'degradado' }}</strong></li>
          <li>Base de datos: {{ h.database === 'ok' ? 'disponible' : 'no disponible' }}</li>
          <li>Versión de la API: {{ h.version }}</li>
        </ul>
        @if (h.status === 'degraded') {
          <p class="notice warn">El servicio funciona de forma parcial; algunas pantallas pueden fallar. Reintente más tarde.</p>
        }
      }
    </app-state-panel>
  `,
})
export class SystemPage {
  private api = inject(ApiService);
  l = load<Health>(() => this.api.health());
  info = computed(() => { const s = this.l.state(); return s.kind === 'data' ? s.data : null; });
}
