import { Component, inject } from '@angular/core';
import { DataService } from '../core/data.service';
import { load } from '../core/load';
import { RecommendationRow } from '../core/models';
import { StatePanel } from '../ui/state-panel';
import { DemoBadge } from '../ui/demo-badge';

@Component({
  selector: 'app-recommendations-page',
  imports: [StatePanel, DemoBadge],
  template: `
    <h2>Recomendaciones y simulación</h2>
    <p>Contrato: GET /api/v1/recommendations. Todo stock mostrado es simulado.</p>
    <app-state-panel [state]="l.state()" (retry)="l.reload()">
      <table>
        <thead>
          <tr><th>SKU</th><th>Stock</th><th>Tránsito</th><th>Horizonte (d)</th><th>Pedido</th><th>Motivo</th><th>Origen</th></tr>
        </thead>
        <tbody>
          @for (r of rows(); track r.sku) {
            <tr>
              <td>{{ r.sku }}</td><td>{{ r.stock }}</td><td>{{ r.in_transit }}</td><td>{{ r.horizon_days }}</td>
              <td>{{ r.order_qty }}</td><td>{{ r.reason }}</td>
              <td><app-demo-badge [provenance]="r.provenance" /> {{ r.scenario_id }}</td>
            </tr>
          }
        </tbody>
      </table>
    </app-state-panel>
  `,
})
export class RecommendationsPage {
  private ds = inject(DataService);
  l = load<RecommendationRow>(() => this.ds.recommendations());
  rows() {
    const s = this.l.state();
    return s.kind === 'data' ? s.data : [];
  }
}
