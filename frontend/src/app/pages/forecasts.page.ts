import { Component, inject } from '@angular/core';
import { DataService } from '../core/data.service';
import { load } from '../core/load';
import { ForecastRow, RunRecord } from '../core/models';
import { ageDays, isStale, STALE_DAYS } from '../core/age';
import { StatePanel } from '../ui/state-panel';

@Component({
  selector: 'app-forecasts-page',
  imports: [StatePanel],
  template: `
    <h2>Pronósticos</h2>
    <p>Contrato: GET /api/v1/runs y GET /api/v1/forecasts.</p>
    <h3>Corridas</h3>
    <app-state-panel [state]="runs.state()" (retry)="runs.reload()">
      <ul>
        @for (r of runRows(); track r.run_id) {
          <li [attr.data-run]="r.run_id">
            {{ r.run_id }} · {{ r.status }} · corte {{ r.cutoff }} ·
            @if (r.completed_at === null) {
              sin fecha de finalización
            } @else {
              antigüedad {{ age(r) }} día(s)
              @if (stale(r)) {
                <strong class="stale">RESULTADO ANTIGUO (más de {{ staleDays }} días, umbral supuesto)</strong>
              }
            }
          </li>
        }
      </ul>
    </app-state-panel>
    <h3>Pronósticos por entidad</h3>
    <app-state-panel [state]="fc.state()" (retry)="fc.reload()">
      <table>
        <thead><tr><th>Corrida</th><th>Entidad</th><th>Fecha objetivo</th><th>Cantidad</th><th>Modelo</th></tr></thead>
        <tbody>
          @for (f of fcRows(); track $index) {
            <tr><td>{{ f.run_id }}</td><td>{{ f.entity }}</td><td>{{ f.target_date }}</td><td>{{ f.quantity }}</td><td>{{ f.model }}</td></tr>
          }
        </tbody>
      </table>
    </app-state-panel>
  `,
  styles: `.stale { color: #b02a37; }`,
})
export class ForecastsPage {
  private ds = inject(DataService);
  staleDays = STALE_DAYS;
  runs = load<RunRecord>(() => this.ds.runs());
  fc = load<ForecastRow>(() => this.ds.forecasts());
  runRows() {
    const s = this.runs.state();
    return s.kind === 'data' ? s.data : [];
  }
  fcRows() {
    const s = this.fc.state();
    return s.kind === 'data' ? s.data : [];
  }
  age(r: RunRecord) {
    return ageDays(r.completed_at);
  }
  stale(r: RunRecord) {
    return isStale(r.completed_at);
  }
}
