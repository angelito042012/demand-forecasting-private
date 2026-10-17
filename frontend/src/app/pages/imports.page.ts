import { Component, computed, inject, signal } from '@angular/core';
import { ApiService } from '../core/api.service';
import { load } from '../core/load';
import { ImportDetail, ImportItem, Page } from '../core/models';
import { StatePanel } from '../ui/state-panel';
import { Pager } from '../ui/pager';
import { DataTree } from '../ui/data-tree';

@Component({
  selector: 'app-imports-page',
  imports: [StatePanel, Pager, DataTree],
  template: `
    <h2>Importaciones</h2>
    <p class="info" data-testid="cli-note">
      Esta pantalla es de solo lectura. La carga de archivos nuevos sigue haciéndose por línea de comandos
      (<code>pipeline.data.importer</code>) hasta la tarea T10; aquí no hay botón de carga.
    </p>
    <app-state-panel [state]="l.state()" emptyText="Todavía no hay importaciones registradas." (retry)="l.reload()">
      @if (data(); as d) {
        <table data-testid="imports-table">
          <thead><tr><th>Archivo</th><th>Mes</th><th>Estado</th><th>Filas leídas</th><th>Ventas aceptadas</th><th>Notas de crédito</th><th>Rechazadas</th><th>Insertadas</th><th>Ya existentes</th><th>En conflicto</th><th></th></tr></thead>
          <tbody>
            @for (r of d.items; track r.import_id) {
              <tr>
                <td>{{ r.archivo }}</td><td>{{ r.mes }}</td><td>{{ r.estado }}</td><td>{{ r.filas_leidas }}</td>
                <td>{{ r.ventas_aceptadas }}</td><td>{{ r.notas_credito }}</td><td>{{ r.rechazadas }}</td>
                <td>{{ r.insertadas }}</td><td>{{ r.ya_existentes }}</td><td>{{ r.en_conflicto }}</td>
                <td><button type="button" (click)="open(r)">Ver detalle</button></td>
              </tr>
            }
          </tbody>
        </table>
        <app-pager [page]="d.page" [pageSize]="d.page_size" [total]="d.total" [hasMore]="d.has_more" (go)="go($event)" />
      }
    </app-state-panel>
    @if (selected(); as s) {
      <h3>Detalle de {{ s.archivo }}</h3>
      <app-state-panel [state]="detail.state()" (retry)="detail.reload()">
        <app-data-tree [value]="detailData()" />
      </app-state-panel>
    }
  `,
  styles: `.info { background: #e2e3e5; padding: 0.4rem 0.7rem; border-radius: 4px; } table { display: block; overflow-x: auto; }`,
})
export class ImportsPage {
  private api = inject(ApiService);
  page = signal(1);
  pageSize = 50;
  l = load<Page<ImportItem>>(() => this.api.imports(this.page(), this.pageSize), (d) => d.items.length === 0);
  data = computed(() => { const s = this.l.state(); return s.kind === 'data' ? s.data : null; });
  selected = signal<ImportItem | null>(null);
  detail = load<ImportDetail>(() => this.api.importDetail(this.selected()!.import_id), () => false, false);
  detailData = computed(() => { const s = this.detail.state(); return s.kind === 'data' ? s.data : null; });

  go(p: number) { this.page.set(p); this.l.reload(); }
  open(r: ImportItem) { this.selected.set(r); this.detail.reload(); }
}
