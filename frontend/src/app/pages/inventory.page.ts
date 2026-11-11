import { Component, computed, inject, signal } from '@angular/core';
import { tap } from 'rxjs';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService } from '../core/api.service';
import { load } from '../core/utils/load';
import { ReportedInventoryPage, ReportedSnapshot, ReportedSnapshotRef, ReportedView } from '../core/models';
import { fmtInt } from '../core/utils/format';
import { longDate } from '../core/utils/ux-text';
import { PageHeader } from '../shared/components/page-header';
import { StatePanel } from '../shared/components/state-panel';
import { Pager } from '../shared/components/pager';
import { ButtonModule } from 'primeng/button';
import { MessageModule } from 'primeng/message';
import { InputTextModule } from 'primeng/inputtext';

export const NOT_REPORTED = 'No informado';

/** «2026-10-18T17:00:00-05:00» → «18/10/2026, 17:00» (la hora local viene escrita en la respuesta; no se convierte de zona). */
export function localStamp(iso: string | null | undefined): string | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/.exec(iso ?? '');
  return m ? `${m[3]}/${m[2]}/${m[1]}, ${m[4]}:${m[5]}` : null;
}
/** «18/10/2026» a partir de la misma marca. */
export function localDay(iso: string | null | undefined): string | null {
  const s = localStamp(iso);
  return s ? s.split(',')[0] : null;
}
export function zoneLabel(tz: string | null | undefined): string {
  return tz === 'America/Lima' ? 'hora de Lima' : (tz || 'zona horaria no indicada');
}
/** null/ausente ⇒ «No informado»; 0 ⇒ «0». */
export function qty(v: number | null | undefined): string {
  return v === null || v === undefined ? NOT_REPORTED : fmtInt(v);
}

const SORTS: { value: string; label: string }[] = [
  { value: 'producto_id', label: 'Código (menor a mayor)' },
  { value: '-producto_id', label: 'Código (mayor a menor)' },
  { value: 'producto', label: 'Producto (A a Z)' },
  { value: '-producto', label: 'Producto (Z a A)' },
  { value: '-libre', label: 'Disponible (más a menos)' },
  { value: 'libre', label: 'Disponible (menos a más)' },
];
const VIEWS: { value: ReportedView; label: string }[] = [
  { value: 'all', label: 'Todos' },
  { value: 'with_stock', label: 'Con existencia' },
  { value: 'no_stock', label: 'Sin existencia' },
];

/** T18: inventario informado por la empresa (solo lectura). No es inventario simulado ni se mezcla con recomendaciones. */
@Component({
  selector: 'app-inventory-page',
  imports: [FormsModule, RouterLink, PageHeader, StatePanel, Pager, ButtonModule, MessageModule, InputTextModule],
  template: `
    <app-page-header title="Inventario informado por la empresa" [lead]="lead()" />

    @if (snap(); as s) {
      <p-message severity="info" data-testid="inv-strip" styleClass="w-full mb-2">
        <strong>Conteo del {{ stamp() }} ({{ zone() }}) · {{ s.warehouse.name }} (almacén {{ s.warehouse.id }})</strong>
        @if (!s.independent_verification) { · Informado por la empresa; no verificado de forma independiente }
      </p-message>
      <p-message severity="warn" data-testid="inv-gap" styleClass="w-full mb-2">
        Este inventario es del {{ day() }}.
        @if (salesEnd(); as e) {
          El histórico de ventas disponible termina el {{ e }}: faltan las ventas posteriores hasta el conteo (no son cero).
        } @else {
          No se pudo confirmar hasta qué fecha llega el histórico de ventas; las ventas posteriores a esa fecha faltan (no son cero).
        }
        Por eso no hay una recomendación de reposición actualizada a esa fecha; las recomendaciones históricas siguen en
        <a [routerLink]="['/recomendaciones']" queryParamsHandling="preserve" data-testid="inv-to-reco">Reposición simulada</a>.
        @if (pendingOrders()) { Pedidos por recibir: <strong>no informados</strong>. }
      </p-message>
    }

    @if (forbidden()) {
      <p-message severity="error" role="alert" data-testid="inv-forbidden" text="No tienes permiso para ver el inventario informado. Ingresa con otro usuario o avisa al administrador." styleClass="w-full mb-2" />
    } @else {
      @if (snap()) {
        <section class="toolbar" aria-label="Filtros del inventario informado">
          <fieldset class="seg" data-testid="inv-views">
            <legend>Ver</legend>
            @for (v of views; track v.value) {
              <button type="button" [attr.aria-pressed]="view() === v.value" [attr.data-testid]="'view-' + v.value" (click)="setView(v.value)">{{ v.label }}</button>
            }
          </fieldset>
          <form class="filters" (ngSubmit)="search()" aria-label="Buscar en el inventario informado">
            <label>Código o nombre <input name="q" [(ngModel)]="draft" autocomplete="off" maxlength="100" data-testid="inv-q" /></label>
            <label>Ordenar por
              <select name="sort" [ngModel]="sort()" (ngModelChange)="setSort($event)" data-testid="inv-sort">
                @for (o of sorts; track o.value) { <option [value]="o.value">{{ o.label }}</option> }
              </select>
            </label>
            <label>Filas por página
              <select name="ps" [ngModel]="pageSize()" (ngModelChange)="setSize($event)" data-testid="inv-size">
                @for (n of sizes; track n) { <option [ngValue]="n">{{ n }}</option> }
              </select>
            </label>
            <p-button type="submit" label="Buscar" icon="pi pi-search" data-testid="inv-search" />
          </form>
        </section>
      }

      <app-state-panel [state]="l.state()" emptyText="Todavía no se cargó el conteo de inventario." (retry)="l.reload()">
        @if (data(); as d) {
          <p data-testid="inv-summary"><strong>{{ summary() }}</strong></p>
          @if (d.items.length === 0) {
            <p class="state" data-testid="inv-no-match">Ningún producto coincide con la búsqueda o la vista elegida.</p>
          } @else {
            <div class="table-wrap" tabindex="0" role="region" aria-label="Tabla de inventario informado">
              <table data-testid="inv-table">
                <thead><tr>
                  <th scope="col">Código</th><th scope="col">Producto</th><th scope="col">Presentación</th>
                  <th scope="col" class="num">Disponible</th><th scope="col" class="num">Reservado</th><th scope="col" class="num">No vendible</th>
                </tr></thead>
                <tbody>
                  @for (r of d.items; track r.producto_id) {
                    <tr [attr.data-sku]="r.producto_id">
                      <td data-col="code">{{ r.producto_id }}</td>
                      <td data-col="name">{{ r.producto }}</td>
                      <td data-col="unit">{{ r.unidad_descripcion || NOT_REPORTED }}</td>
                      <td class="num" data-col="free">
                        {{ qty(r.libre) }}
                        @if (r.libre === 0) { <span class="chip warn" data-testid="no-stock-chip">Sin existencia</span> }
                      </td>
                      <td class="num" data-col="reserved">{{ qty(r.reservada) }}</td>
                      <td class="num" data-col="unsellable">{{ qty(r.no_vendible) }}</td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          }
          <app-pager [page]="d.page" [pageSize]="d.page_size" [total]="d.total" [hasMore]="d.has_more" (go)="go($event)" />
          <p class="muted" data-testid="inv-units-note">La cantidad está en la presentación indicada (p. ej. caja de 12, pack de 2); no se multiplicó. Por eso no se muestra un total general de unidades.</p>
        }
      </app-state-panel>

      @if (snap(); as s) {
        <details class="help" data-testid="inv-details">
          <summary>Detalles del conteo</summary>
          <ul class="plain">
            <li>Fuente: <span data-testid="inv-source">{{ s.source?.file || NOT_REPORTED }}</span> · huella {{ s.source?.sha256_short || NOT_REPORTED }}</li>
            <li>Versión: {{ s.version }} · identificador: <span data-testid="inv-snapshot-id">{{ s.snapshot_id }}</span></li>
            <li>Procedencia: {{ provenance() }}</li>
            @if (confirmations().length) {
              <li>Confirmaciones: <ul class="plain">@for (c of confirmations(); track c) { <li>{{ c }}</li> }</ul></li>
            }
            @if (s.declared_unknowns?.length) {
              <li data-testid="inv-unknowns">Desconocidos declarados (no son cero):
                <ul class="plain">@for (u of s.declared_unknowns; track u.code) { <li><strong>{{ u.code }}</strong>: {{ u.detail }}</li> }</ul>
              </li>
            }
          </ul>
        </details>
        @if (s.version > 1 || otherVersions().length) {
          <details class="help" data-testid="inv-versions" (toggle)="loadVersions()">
            <summary>Versiones anteriores del conteo</summary>
            <p class="muted">Se muestra la versión {{ s.version }}.</p>
            @if (versionsFailed()) { <p class="notice warn" role="status">No se pudo consultar la lista de versiones.</p> }
            <ul class="plain">
              @for (v of otherVersions(); track v.snapshot_id) {
                <li><button type="button" class="secondary small" (click)="pickVersion(v.snapshot_id)">Ver versión {{ v.version }}</button>
                  del {{ stampOf(v.as_of_local) }} · {{ v.status === 'current' ? 'vigente' : 'reemplazada' }}</li>
              }
            </ul>
          </details>
        }
      }
    }
  `,
})
export class InventoryPage {
  private api = inject(ApiService);
  readonly NOT_REPORTED = NOT_REPORTED;
  readonly qty = qty;
  readonly views = VIEWS;
  readonly sorts = SORTS;
  readonly sizes = [25, 50, 100, 200];

  view = signal<ReportedView>('all');
  q = signal('');
  draft = '';
  sort = signal('producto_id');
  page = signal(1);
  pageSize = signal(50);
  snapshotId = signal<string | undefined>(undefined);
  /** Último conteo conocido: la franja no desaparece mientras se recarga la tabla. */
  snap = signal<ReportedSnapshot | null>(null);
  private versions = signal<ReportedSnapshotRef[]>([]);
  versionsFailed = signal(false);
  private versionsAsked = false;

  l = load<ReportedInventoryPage>(
    () => this.api.reportedInventory({
      snapshot_id: this.snapshotId(), q: this.q(), view: this.view(), sort: this.sort(), page: this.page(), page_size: this.pageSize(),
    }).pipe(tap((d) => this.snap.set(d.snapshot))),
    (d) => !d.snapshot,
  );
  data = computed(() => {
    const s = this.l.state();
    return s.kind === 'data' ? s.data : null;
  });
  forbidden = computed(() => {
    const s = this.l.state();
    return s.kind === 'error' && (s.error.status === 403 || s.error.code === 'PROHIBIDO');
  });

  stamp = computed(() => localStamp(this.snap()?.as_of_local) ?? 'fecha no informada');
  day = computed(() => localDay(this.snap()?.as_of_local) ?? 'fecha no informada');
  zone = computed(() => zoneLabel(this.snap()?.timezone));
  lead = computed(() => {
    const s = this.snap();
    const st = localStamp(s?.as_of_local);
    if (!s || !st) return 'Existencias que la empresa informó para su almacén en un conteo con fecha.';
    const [d, t] = st.split(', ');
    return `Existencias que la empresa informó para ${s.warehouse.name} el ${d} a las ${t}.`;
  });
  salesEnd = computed(() => {
    const e = this.snap()?.context?.sales_history_end;
    const t = e ? longDate(e) : '—';
    return t === '—' ? null : t;
  });
  pendingOrders = computed(() => !!this.snap()?.declared_unknowns?.some((u) => u.code === 'PEDIDOS_PENDIENTES'));
  provenance = computed(() => {
    const d = this.data();
    return d?.provenance === 'INVENTARIO_INFORMADO_POR_LA_EMPRESA' ? 'inventario informado por la empresa' : (d?.provenance || NOT_REPORTED);
  });
  confirmations = computed(() => {
    const c = this.snap()?.confirmations;
    if (Array.isArray(c)) return c.map((x) => (typeof x === 'string' ? x : JSON.stringify(x)));
    if (c && typeof c === 'object') return Object.entries(c).map(([k, v]) => `${k}: ${String(v)}`);
    return [];
  });
  summary = computed(() => {
    const d = this.data();
    const c = d?.view_counts ?? (d?.snapshot ? { all: d.snapshot.counts.items, with_stock: d.snapshot.counts.with_stock, no_stock: d.snapshot.counts.no_stock } : null);
    return c ? `${c.all} productos · ${c.with_stock} con existencia · ${c.no_stock} sin existencia` : '';
  });
  otherVersions = computed(() => this.versions().filter((v) => v.snapshot_id !== this.snap()?.snapshot_id));
  stampOf = (iso: string) => localStamp(iso) ?? '—';

  private refetch() { this.l.reload(); }
  setView(v: ReportedView) { if (v === this.view()) return; this.view.set(v); this.page.set(1); this.refetch(); }
  search() { this.q.set(this.draft.trim()); this.page.set(1); this.refetch(); }
  setSort(v: string) { this.sort.set(v); this.page.set(1); this.refetch(); }
  setSize(n: number) { this.pageSize.set(Number(n)); this.page.set(1); this.refetch(); }
  go(p: number) { this.page.set(p); this.refetch(); }
  pickVersion(id: string) { this.snapshotId.set(id); this.page.set(1); this.refetch(); }

  loadVersions() {
    if (this.versionsAsked) return;
    this.versionsAsked = true;
    this.api.reportedInventorySnapshots().subscribe({
      next: (r) => this.versions.set(Array.isArray(r) ? r : (r?.items ?? [])),
      error: () => { this.versionsFailed.set(true); this.versionsAsked = false; },
    });
  }
}
