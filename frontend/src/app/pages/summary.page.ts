import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../core/api.service';
import { load } from '../core/utils/load';
import { GroupBy, SalesSummary } from '../core/models';
import { StatePanel } from '../shared/components/state-panel';
import { PageHeader } from '../shared/components/page-header';
import { fmtDate, fmtInt, fmtPen } from '../core/utils/format';
import { categoryLabel, longDate, monthName } from '../core/utils/ux-text';
import { ObservedNotice } from '../shared/components/notices';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { TableModule } from 'primeng/table';

@Component({
  selector: 'app-summary-page',
  imports: [StatePanel, ObservedNotice, FormsModule, PageHeader, ButtonModule, InputTextModule, TableModule],
  template: `
    <app-page-header title="Ventas registradas" lead="Ventas reales ya cargadas, en unidades y soles; sirven de base para las estimaciones." />
    <app-observed-notice />
    <form class="toolbar filters" (ngSubmit)="apply()" aria-label="Filtros de las ventas registradas">
      <label>Desde <input type="date" name="from" [(ngModel)]="from" max="2026-09-30" /></label>
      <label>Hasta <input type="date" name="to" [(ngModel)]="to" max="2026-09-30" /></label>
      <label>Agrupar por
        <select name="group" [(ngModel)]="group">
          <option value="month">Mes</option><option value="day">Día</option><option value="category">Categoría</option>
        </select>
      </label>
      <label>Categoría <input pInputText name="cat" [(ngModel)]="categoria" placeholder="Todas" /></label>
      <p-button type="submit" label="Consultar" icon="pi pi-search" />
    </form>
    <app-state-panel [state]="l.state()" emptyText="No hay ventas registradas en el rango consultado. Prueba con otras fechas o quita el filtro de categoría." (retry)="l.reload()">
      @if (data(); as d) {
        <p data-testid="sales-scope">Ventas del {{ date(d.from) }} al {{ date(d.to) }} · cantidades en «{{ d.unit }}» · importes en soles ({{ d.currency }}).</p>
        <p-table [value]="d.items" styleClass="p-datatable-sm p-datatable-striped" data-testid="sales-table">
          <ng-template #header>
            <tr><th>{{ keyHeader() }}</th><th class="text-right">Líneas de venta</th><th class="text-right">Unidades (unidad base)</th><th class="text-right">Importe (PEN)</th></tr>
          </ng-template>
          <ng-template #body let-i>
            <tr><td><strong>{{ keyText(i.key) }}</strong></td><td class="text-right">{{ int(i.lineas_venta) }}</td><td class="text-right">{{ int(i.unidades) }}</td><td class="text-right">{{ pen(i.importe_pen) }}</td></tr>
          </ng-template>
        </p-table>
        <h2>Notas de crédito (informadas aparte, no netas)</h2>
        <p data-testid="credit-notes">{{ int(d.notas_credito.lineas) }} línea(s) · importe {{ pen(d.notas_credito.importe_pen) }}. No se infiere devolución física.</p>
        <h2>Días excluidos del análisis</h2>
        @if (d.excluded_days.length) {
          <ul class="plain" data-testid="excluded">
            @for (x of d.excluded_days; track x.fecha) { <li><strong>{{ day(x.fecha) }}</strong>: {{ x.motivo }}</li> }
          </ul>
        } @else {
          <p data-testid="excluded">Ninguno en el rango.</p>
        }
      }
    </app-state-panel>
  `,
})
export class SummaryPage {
  int = (v: unknown) => fmtInt(v);
  pen = (v: unknown) => fmtPen(v);
  date = (v: string | null | undefined) => fmtDate(v);
  day = (v: string) => longDate(v);

  private api = inject(ApiService);
  from = '2026-01-01';
  to = '2026-09-30';
  group: GroupBy = 'month';
  categoria = '';
  private applied = signal({ from: this.from, to: this.to, group: this.group, categoria: this.categoria });
  l = load<SalesSummary>(() => {
    const a = this.applied();
    return this.api.salesSummary(a.from, a.to, a.group, a.categoria.trim() || undefined);
  }, (d) => d.items.length === 0 && d.notas_credito.lineas === 0);
  data = computed(() => { const s = this.l.state(); return s.kind === 'data' ? s.data : null; });
  keyHeader = () => ({ day: 'Día', month: 'Mes', category: 'Categoría' })[this.applied().group];
  keyText(key: string): string {
    switch (this.applied().group) {
      case 'month': { const m = monthName(`${key}-01`); return m ? `${m.charAt(0).toUpperCase()}${m.slice(1)} de ${key.slice(0, 4)}` : key; }
      case 'day': return longDate(key) === '—' ? key : longDate(key);
      default: return categoryLabel(key);
    }
  }
  apply() {
    this.applied.set({ from: this.from, to: this.to, group: this.group, categoria: this.categoria });
    this.l.reload();
  }
}
