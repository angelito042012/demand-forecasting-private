import { Component, computed, inject } from '@angular/core';
import { ApiService } from '../core/api.service';
import { load } from '../core/utils/load';
import { Health } from '../core/models';
import { PageHeader } from '../shared/components/page-header';
import { StatePanel } from '../shared/components/state-panel';
import { ButtonModule } from 'primeng/button';
import { MessageModule } from 'primeng/message';
import { CardModule } from 'primeng/card';
import { TagModule } from 'primeng/tag';

@Component({
  selector: 'app-system-page',
  imports: [PageHeader, StatePanel, ButtonModule, MessageModule, CardModule, TagModule],
  template: `
    <app-page-header title="Estado del sistema" lead="Comprueba si el servicio y la base de datos están respondiendo." />
    <app-state-panel [state]="l.state()" (retry)="l.reload()">
      @if (info(); as h) {
        <p-card styleClass="mb-3">
          <ul class="list-none p-0 m-0 flex flex-column gap-2" data-testid="health">
            <li class="flex align-items-center gap-2">Estado general:
              <p-tag [severity]="h.status === 'ok' ? 'success' : 'warn'" [value]="h.status === 'ok' ? 'Funcionando' : 'Funcionando con fallas'" />
            </li>
            <li class="flex align-items-center gap-2">Base de datos:
              <p-tag [severity]="h.database === 'ok' ? 'success' : 'danger'" [value]="h.database === 'ok' ? 'Disponible' : 'No disponible'" />
            </li>
            <li class="text-color-secondary">Versión de la aplicación: {{ h.version }}</li>
          </ul>
          <div class="mt-3">
            <p-button label="Volver a comprobar" icon="pi pi-refresh" [outlined]="true" (onClick)="l.reload()" data-testid="recheck" />
          </div>
        </p-card>
        @if (h.status === 'degraded') {
          <p-message severity="warn" role="alert" data-testid="degraded" text="El servicio funciona de forma parcial y algunas pantallas pueden fallar. Vuelve a comprobar en unos minutos; si sigue igual, revisa los registros del servidor o avisa a quien mantiene la aplicación." styleClass="w-full" />
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
