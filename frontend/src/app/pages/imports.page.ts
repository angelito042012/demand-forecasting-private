import { Component, computed, inject, signal } from '@angular/core';
import { ApiService } from '../core/api.service';
import { load } from '../core/load';
import { ImportDetail, ImportItem, Page } from '../core/models';
import { StatePanel } from '../ui/state-panel';
import { Pager } from '../ui/pager';
import { DataTree } from '../ui/data-tree';
import { fmtInt } from '../core/format';

@Component({
  selector: 'app-imports-page',
  imports: [StatePanel, Pager, DataTree],
  template: `
    <h2>Importaciones</h2>
    <p class="notice info" data-testid="cli-note">
      Esta pantalla es de solo lectura. La carga de archivos nuevos sigue haciéndose por línea de comandos
      (<code>pipeline.data.importer</code>) hasta la tarea T10; aquí no hay botón de carga.
    </p>
    <app-state-panel [state]="l.state()" emptyText="Todavía no hay importaciones registradas." (retry)="l.reload()">
      @if (data(); as d) {
        <div class="table-wrap" tabindex="0" role="region" aria-label="Tabla de importaciones">
        <table data-testid="imports-table">
          <thead><tr><th scope="col">Archivo</th><th scope="col">Mes</th><th scope="col">Estado</th><th scope="col" class="num">Filas leídas</th><th scope="col" class="num">Ventas aceptadas</th><th scope="col" class="num">Notas de crédito</th><th scope="col" class="num">Rechazadas</th><th scope="col" class="num">Insertadas</th><th scope="col" class="num">Ya existentes</th><th scope="col" class="num">En conflicto</th><th scope="col"><span class="sr-only">Acción</span></th></tr></thead>
          <tbody>
            @for (r of d.items; track r.import_id) {
              <tr>
                <td>{{ r.archivo }}</td><td>{{ r.mes }}</td><td>{{ r.estado }}</td><td class="num">{{ int(r.filas_leidas) }}</td>
                <td class="num">{{ int(r.ventas_aceptadas) }}</td><td class="num">{{ int(r.notas_credito) }}</td><td class="num">{{ int(r.rechazadas) }}</td>
                <td class="num">{{ int(r.insertadas) }}</td><td class="num">{{ int(r.ya_existentes) }}</td><td class="num">{{ int(r.en_conflicto) }}</td>
                <td><button type="button" (click)="open(r)">Ver detalle</button></td>
              </tr>
            }
          </tbody>
        </table>
        </div>
        <app-pager [page]="d.page" [pageSize]="d.page_size" [total]="d.total" [hasMore]="d.has_more" (go)="go($event)" />
      }
    </app-state-panel>
    @if (selected(); as s) {
      <h3>Detalle de {{ s.archivo }}</h3>
      <app-state-panel [state]="detail.state()" (retry)="detail.reload()">
        <details class="tech" open><summary>Detalle técnico de la importación</summary><app-data-tree [value]="detailData()" /></details>
      </app-state-panel>
    }
  `,
  styles: `.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }`,
})
export class ImportsPage {
  private api = inject(ApiService);
  int = (v: unknown) => fmtInt(v);
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
