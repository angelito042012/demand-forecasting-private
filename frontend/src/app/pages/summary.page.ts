import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../core/api.service';
import { load } from '../core/load';
import { GroupBy, SalesSummary } from '../core/models';
import { StatePanel } from '../ui/state-panel';
import { ObservedNotice } from '../ui/notices';

@Component({
  selector: 'app-summary-page',
  imports: [StatePanel, ObservedNotice, FormsModule],
  template: `
    <h2>Resumen de ventas y calidad de datos</h2>
    <app-observed-notice />
    <p class="hint">Agosto de 2026 está reservado para la prueba final: el servidor no entrega ventas posteriores al 31/07/2026.</p>
    <form class="filters" (ngSubmit)="apply()">
      <label>Desde <input type="date" name="from" [(ngModel)]="from" max="2026-07-31" /></label>
      <label>Hasta <input type="date" name="to" [(ngModel)]="to" max="2026-07-31" /></label>
      <label>Agrupar por
        <select name="group" [(ngModel)]="group">
          <option value="month">Mes</option><option value="day">Día</option><option value="category">Categoría</option>
        </select>
      </label>
      <label>Categoría <input name="cat" [(ngModel)]="categoria" /></label>
      <button type="submit">Consultar</button>
    </form>
    <app-state-panel [state]="l.state()" emptyText="No hay ventas en el rango consultado." (retry)="l.reload()">
      @if (data(); as d) {
        <p>Periodo {{ d.from }} a {{ d.to }} · unidades en «{{ d.unit }}» · moneda {{ d.currency }}</p>
        <table data-testid="sales-table">
          <thead><tr><th>{{ keyHeader() }}</th><th>Líneas de venta</th><th>Unidades (unidad base)</th><th>Importe (PEN)</th></tr></thead>
          <tbody>
            @for (i of d.items; track i.key) {
              <tr><td>{{ i.key }}</td><td>{{ i.lineas_venta }}</td><td>{{ i.unidades }}</td><td>{{ i.importe_pen }}</td></tr>
            }
          </tbody>
        </table>
        <h3>Notas de crédito (informadas aparte, no netas)</h3>
        <p data-testid="credit-notes">{{ d.notas_credito.lineas }} línea(s) · importe {{ d.notas_credito.importe_pen }} PEN. No se infiere devolución física.</p>
        <h3>Días excluidos del análisis</h3>
        <p data-testid="excluded">{{ d.excluded_days.length ? excludedText(d.excluded_days) : 'Ninguno en el rango.' }}</p>
      }
    </app-state-panel>
  `,
  styles: `.filters { display: flex; flex-wrap: wrap; gap: 0.8rem; align-items: end; margin: 0.6rem 0; } label { display: grid; gap: 0.2rem; } .hint { font-size: 0.85rem; color: #555; }`,
})
export class SummaryPage {
  excludedText(days: { fecha: string; motivo: string }[]) {
    return days.map((d) => d.fecha + ' (' + d.motivo + ')').join('; ');
  }

  private api = inject(ApiService);
  from = '2026-06-01';
  to = '2026-07-31';
  group: GroupBy = 'month';
  categoria = '';
  private applied = signal({ from: this.from, to: this.to, group: this.group, categoria: this.categoria });
  l = load<SalesSummary>(() => {
    const a = this.applied();
    return this.api.salesSummary(a.from, a.to, a.group, a.categoria.trim() || undefined);
  }, (d) => d.items.length === 0 && d.notas_credito.lineas === 0);
  data = computed(() => { const s = this.l.state(); return s.kind === 'data' ? s.data : null; });
  keyHeader = () => ({ day: 'Día', month: 'Mes', category: 'Categoría' })[this.applied().group];
  apply() {
    this.applied.set({ from: this.from, to: this.to, group: this.group, categoria: this.categoria });
    this.l.reload();
  }
}
