import { Component, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ApiService } from '../core/api.service';
import { load } from '../core/load';
import { Page, RunDetail, RunQuality, RunSummary } from '../core/models';
import { fmtDate, fmtInt } from '../core/format';
import { StatePanel } from '../ui/state-panel';
import { Pager } from '../ui/pager';
import { DataTree } from '../ui/data-tree';
import { RunBanner, SupersededBanner, isRunInvalid } from '../ui/notices';

@Component({
  selector: 'app-runs-page',
  imports: [StatePanel, Pager, DataTree, RunBanner, SupersededBanner, RouterLink],
  template: `
    <h2>Corridas</h2>
    <p class="notice info">Solo se listan corridas ya publicadas. El servidor no reentrena ni simula al consultar; ejecutar corridas desde la aplicación llega con T10.</p>
    <app-state-panel [state]="l.state()" emptyText="No hay corridas publicadas." (retry)="l.reload()">
      @if (data(); as d) {
        <div class="table-wrap" tabindex="0" role="region" aria-label="Tabla de corridas">
          <table data-testid="runs-table">
            <thead>
              <tr><th scope="col">Corrida</th><th scope="col">Etiqueta</th><th scope="col">Estado</th><th scope="col">Motivo</th><th scope="col">Corte</th><th scope="col">Publicada (UTC)</th><th scope="col" class="num">Antigüedad (días)</th><th scope="col">Activa</th><th scope="col"><span class="sr-only">Acción</span></th></tr>
            </thead>
            <tbody>
              @for (r of d.items; track r.run_id) {
                <tr>
                  <td><code>{{ r.run_id }}</code></td><td>{{ r.run_label }}</td>
                  <td>
                    @if (invalid(r)) { <span class="badge bad" data-testid="run-status">Sustituida</span> }
                    @else { <span class="badge ok" data-testid="run-status">Completada</span> }
                  </td>
                  <td data-testid="run-reason">{{ reason(r) }}</td>
                  <td>{{ date(r.cutoff) }}</td><td>{{ r.published_at }}</td>
                  <td class="num">{{ int(r.age_days_at_view) }}</td><td>{{ r.is_active ? 'Sí' : 'No' }}</td>
                  <td><button type="button" (click)="open(r.run_id)" [attr.aria-label]="'Ver detalle de la corrida ' + r.run_id">Ver detalle</button></td>
                </tr>
              }
            </tbody>
          </table>
        </div>
        <app-pager [page]="d.page" [pageSize]="d.page_size" [total]="d.total" [hasMore]="d.has_more" (go)="go($event)" />
      }
    </app-state-panel>
    @if (selected()) {
      <h3>Detalle de la corrida</h3>
      <app-state-panel [state]="detail.state()" (retry)="detail.reload()">
        @if (det(); as r) {
          <app-superseded-banner [run]="r" />
          <app-run-banner [runLabel]="r.run_label" [cutoff]="r.cutoff" [age]="r.age_days_at_view" />
          <p data-testid="detail-status">Estado: <strong>{{ invalid(r) ? 'Sustituida' : 'Completada' }}</strong>
            @if (invalid(r)) { · {{ reason(r) }} }
            @if (r.quality_issue?.superseded_by; as nxt) { · <a [routerLink]="['/corridas']" [queryParams]="{ run: nxt }">Abrir la corrida corregida</a> }
          </p>
          <h4>Método</h4>
          <ul class="plain" data-testid="method">
            <li>Método elegido: <strong>{{ r.method.chosen }}</strong> (media móvil de 28 días).</li>
            <li><strong>{{ r.method.comparator }}</strong>: comparador experimental que no ganó frente al método elegido.</li>
            <li>Referencia de control: «{{ r.method.control }}» (pronóstico igual a cero, derivado).</li>
            @if (r.method.note) { <li>{{ r.method.note }}</li> }
          </ul>
          @if (r.coverage; as c) {
            <h4>Cobertura</h4>
            <ul class="plain" data-testid="coverage">
              <li>SKU pronosticados: {{ int(c.skus_pronosticados) }}</li>
              <li>SKU con recomendación: {{ int(c.skus_con_recomendacion) }}</li>
              <li>SKU sin inventario simulado: {{ int(c.skus_sin_snapshot) }}</li>
              <li>Categorías: {{ int(c.categorias) }}</li>
            </ul>
          }
          <details class="tech" data-testid="run-doc">
            <summary>Documento completo publicado (identificadores, fuentes, checksums)</summary>
            <app-data-tree [value]="r" />
          </details>
        }
      </app-state-panel>
    }
  `,
  styles: `.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }`,
})
export class RunsPage {
  private api = inject(ApiService);
  private route = inject(ActivatedRoute);
  page = signal(1);
  pageSize = 50;
  l = load<Page<RunSummary>>(() => this.api.runs(this.page(), this.pageSize), (d) => d.items.length === 0);
  data = computed(() => { const s = this.l.state(); return s.kind === 'data' ? s.data : null; });
  selected = signal<string | null>(null);
  detail = load<RunDetail>(() => this.api.runDetail(this.selected()!), () => false, false);
  det = computed(() => { const s = this.detail.state(); return s.kind === 'data' ? s.data : null; });

  constructor() {
    // Enlace desde el aviso de corrida sustituida: /corridas?run=<id> abre el detalle de la corrida corregida.
    this.route.queryParamMap.pipe(takeUntilDestroyed()).subscribe((q) => {
      const id = q.get('run');
      if (id && id !== this.selected()) this.open(id);
    });
  }

  int = (v: unknown) => fmtInt(v);
  date = (v: string | null | undefined) => fmtDate(v);
  invalid = (r: RunQuality) => isRunInvalid(r);
  reason(r: RunSummary | RunDetail): string {
    if (!isRunInvalid(r)) return '—';
    const q = r.quality_issue;
    return q?.reason ?? q?.message ?? 'Sustituida por una corrección de precisión (recomendaciones con error de redondeo); no use sus pedidos.';
  }

  go(p: number) { this.page.set(p); this.l.reload(); }
  open(id: string) { this.selected.set(id); this.detail.reload(); }
}
