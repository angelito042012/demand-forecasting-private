import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../core/api.service';
import { load } from '../core/load';
import { GroupBy, SalesSummary } from '../core/models';
import { StatePanel } from '../ui/state-panel';
import { PageHeader } from '../ui/page-header';
import { fmtDate, fmtInt, fmtPen } from '../core/format';
import { categoryLabel, longDate, monthName } from '../core/ux-text';
import { ObservedNotice } from '../ui/notices';

/**
 * UX01 «Ventas registradas»: ventas reales ya cargadas, en unidades y soles. Solo muestra los agregados que devuelve la API
 * (por mes, día o categoría); no calcula totales propios. Agosto de 2026 no se entrega en esta vista de desarrollo.
 */
@Component({
  selector: 'app-summary-page',
  imports: [StatePanel, ObservedNotice, FormsModule, PageHeader],
  template: `
    <app-page-header title="Ventas registradas" lead="Ventas reales ya cargadas, en unidades y soles; sirven de base para las estimaciones." />
    <app-observed-notice />
    <p class="muted" data-testid="no-august">Esta vista de desarrollo no incluye ventas de agosto de 2026: el servidor no entrega ventas posteriores al 31/07/2026. Agosto se compara aparte, en «Evaluación de resultados».</p>
    <form class="toolbar filters" (ngSubmit)="apply()" aria-label="Filtros de las ventas registradas">
      <label>Desde <input type="date" name="from" [(ngModel)]="from" max="2026-07-31" /></label>
      <label>Hasta <input type="date" name="to" [(ngModel)]="to" max="2026-07-31" /></label>
      <label>Agrupar por
        <select name="group" [(ngModel)]="group">
          <option value="month">Mes</option><option value="day">Día</option><option value="category">Categoría</option>
        </select>
      </label>
      <label>Categoría <input name="cat" [(ngModel)]="categoria" placeholder="Todas" /></label>
      <button type="submit" class="btn">Consultar</button>
    </form>
    <app-state-panel [state]="l.state()" emptyText="No hay ventas registradas en el rango consultado. Prueba con otras fechas o quita el filtro de categoría." (retry)="l.reload()">
      @if (data(); as d) {
        <p data-testid="sales-scope">Ventas del {{ date(d.from) }} al {{ date(d.to) }} · cantidades en «{{ d.unit }}» · importes en soles ({{ d.currency }}).</p>
        <div class="table-wrap" tabindex="0" role="region" aria-label="Tabla de ventas registradas (desplázate para ver todas las columnas)">
        <table data-testid="sales-table">
          <thead><tr><th scope="col">{{ keyHeader() }}</th><th scope="col" class="num">Líneas de venta</th><th scope="col" class="num">Unidades (unidad base)</th><th scope="col" class="num">Importe (PEN)</th></tr></thead>
          <tbody>
            @for (i of d.items; track i.key) {
              <tr><th scope="row">{{ keyText(i.key) }}</th><td class="num">{{ int(i.lineas_venta) }}</td><td class="num">{{ int(i.unidades) }}</td><td class="num">{{ pen(i.importe_pen) }}</td></tr>
            }
          </tbody>
        </table>
        </div>
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
  /** Clave de la API en español: «2026-06» → «Junio de 2026»; «2026-06-07» → «7 de junio de 2026»; categoría legible. */
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
