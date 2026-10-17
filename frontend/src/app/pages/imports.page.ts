import { Component, inject } from '@angular/core';
import { DataService } from '../core/data.service';
import { load } from '../core/load';
import { ImportRecord } from '../core/models';
import { StatePanel } from '../ui/state-panel';

@Component({
  selector: 'app-imports-page',
  imports: [StatePanel],
  template: `
    <h2>Cargas de datos</h2>
    <p>Contrato: GET /api/v1/imports/&#123;id&#125;. Pantalla de solo lectura (sin subida real aún).</p>
    <app-state-panel [state]="l.state()" (retry)="l.reload()">
      <table>
        <thead><tr><th>ID</th><th>Archivo</th><th>Estado</th><th>Incidencias</th></tr></thead>
        <tbody>
          @for (r of rows(); track r.id) {
            <tr><td>{{ r.id }}</td><td>{{ r.filename }}</td><td>{{ r.status }}</td><td>{{ r.errors.join('; ') || '—' }}</td></tr>
          }
        </tbody>
      </table>
    </app-state-panel>
  `,
})
export class ImportsPage {
  private ds = inject(DataService);
  l = load<ImportRecord>(() => this.ds.imports());
  rows() {
    const s = this.l.state();
    return s.kind === 'data' ? s.data : [];
  }
}
