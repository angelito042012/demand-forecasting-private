import { Component, computed, inject } from '@angular/core';
import { ApiService } from '../core/api.service';
import { load } from '../core/load';
import { Health } from '../core/models';
import { PageHeader } from '../ui/page-header';
import { StatePanel } from '../ui/state-panel';

@Component({
  selector: 'app-system-page',
  imports: [PageHeader, StatePanel],
  template: `
    <app-page-header title="Estado del sistema" lead="Comprueba si el servicio y la base de datos están respondiendo." />
    <app-state-panel [state]="l.state()" (retry)="l.reload()">
      @if (info(); as h) {
        <section class="surface">
          <ul class="plain" data-testid="health">
            <li>Estado general: <strong>{{ h.status === 'ok' ? 'funcionando' : 'funcionando con fallas' }}</strong></li>
            <li>Base de datos: <strong>{{ h.database === 'ok' ? 'disponible' : 'no disponible' }}</strong></li>
            <li class="muted">Versión de la aplicación: {{ h.version }}</li>
          </ul>
          <p><button type="button" class="secondary" (click)="l.reload()" data-testid="recheck">Volver a comprobar</button></p>
        </section>
        @if (h.status === 'degraded') {
          <p class="notice warn" role="alert" data-testid="degraded">El servicio funciona de forma parcial y algunas pantallas pueden fallar. Vuelve a comprobar en unos minutos; si sigue igual, revisa los registros del servidor o avisa a quien mantiene la aplicación.</p>
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
