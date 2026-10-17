import { Component, inject, signal } from '@angular/core';
import { DataService } from '../core/data.service';
import { HealthInfo, LoadState } from '../core/models';
import { StatePanel } from '../ui/state-panel';

@Component({
  selector: 'app-system-page',
  imports: [StatePanel],
  template: `
    <h2>Estado del sistema</h2>
    <p>Contrato: GET /api/v1/health. No se llama a la API real.</p>
    <app-state-panel [state]="state()" (retry)="reload()">
      <p>Estado: {{ info()?.status }} · versión API: {{ info()?.api_version }}</p>
    </app-state-panel>
  `,
})
export class SystemPage {
  private ds = inject(DataService);
  state = signal<LoadState<HealthInfo>>({ kind: 'loading' });
  info() {
    const s = this.state();
    return s.kind === 'data' ? s.data : null;
  }
  constructor() {
    this.reload();
  }
  reload() {
    this.state.set({ kind: 'loading' });
    this.ds.health().subscribe({
      next: (r) => this.state.set({ kind: 'data', data: r.data, provenance: r.provenance }),
      error: (e: unknown) => this.state.set({ kind: 'error', message: e instanceof Error ? e.message : 'Error desconocido' }),
    });
  }
}
