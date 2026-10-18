import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { RunChoice, isFinal, isGenerated } from '../core/run-choice';
import { FormsModule } from '@angular/forms';
import { ApiService, ForecastQuery } from '../core/api.service';
import { load } from '../core/load';
import { ForecastItem, ForecastPage } from '../core/models';
import { RunsStore } from '../core/runs-store';
import { analysisName, categoryLabel, isReplaced, productLabel } from '../core/ux-text';
import { StatePanel } from '../ui/state-panel';
import { Pager } from '../ui/pager';
import { PageHeader } from '../ui/page-header';
import { AnalysisBar } from '../ui/analysis-bar';
import { fmtDate, fmtDec } from '../core/format';
import { FinalWarnings } from '../ui/notices';

export const NA = 'no disponible para esta corrida';

/**
 * UX01 «Ventas previstas»: tabla corta (producto, fecha, cantidad estimada y, si existen, ventas registradas). Las columnas
 * técnicas (día de la previsión, tipo de historial, modelo experimental, control cero, evaluable) están en «Comparar métodos / ver detalles».
 */
@Component({
  selector: 'app-forecasts-page',
  imports: [StatePanel, Pager, FormsModule, FinalWarnings, PageHeader, AnalysisBar],
  template: `
    <app-page-header title="Ventas previstas" lead="Unidades que se estima vender de cada producto o categoría en las fechas del análisis elegido." />
    <app-analysis-bar [runId]="choice.id()" />

    @if (final()) {
      <p class="notice info" data-testid="final-note">
        <strong>{{ name() }}.</strong> Cada fila compara la estimación fijada el {{ d(shownRun()?.origin ?? shownRun()?.cutoff) }} con la venta registrada
        ({{ d(shownRun()?.target_start) }} al {{ d(shownRun()?.target_end) }}). Un día sin ningún registro se rotula «no evaluable»; no es una venta cero.
        Son datos históricos: esta evaluación no pronostica octubre.
      </p>
      <app-final-warnings [warnings]="shownRun()?.warnings" />
    }
    @if (replaced()) {
      <p class="notice danger" role="alert" data-testid="forecast-replaced">Esta versión fue reemplazada. No uses sus resultados.</p>
    }

    <section class="toolbar" aria-label="Filtros de ventas previstas">
      <form class="filters" (ngSubmit)="apply()" aria-label="Filtros de pronósticos">
        @if (runs().length) {
          <label>Análisis
            <select data-testid="run-select" aria-label="Análisis" (change)="choice.set($any($event.target).value)">
              @for (r of runs(); track r.run_id) {
                <option [value]="r.run_id" [selected]="r.run_id === shownRun()?.run_id">{{ nameOf(r) }}{{ r.is_active ? ' · en uso por defecto' : '' }}{{ replacedOf(r) ? ' · versión reemplazada' : '' }}</option>
              }
            </select>
          </label>
        }
        <label>Código del producto <input name="sku" [(ngModel)]="f.sku" autocomplete="off" /></label>
        <label>Categoría <input name="cat" [(ngModel)]="f.categoria" autocomplete="off" /></label>
        <label>Desde <input type="date" name="from" [(ngModel)]="f.from" [attr.min]="final() ? '2026-08-01' : null" [attr.max]="maxDate()" data-testid="f-from" /></label>
        <label>Hasta <input type="date" name="to" [(ngModel)]="f.to" [attr.min]="final() ? '2026-08-01' : null" [attr.max]="maxDate()" data-testid="f-to" /></label>
        <button type="submit" data-testid="f-apply">Buscar</button>
        <details class="help more">
          <summary>Más filtros</summary>
          <div class="filters">
            <label>Tipo de historial <input name="coh" [(ngModel)]="f.cohorte" list="cohortes" /></label>
            <datalist id="cohortes"><option value="primaria"></option><option value="historia_corta"></option></datalist>
            <label>Orden
              <select name="sort" [(ngModel)]="f.sort">
                <option value="target_date">Fecha ↑</option><option value="-target_date">Fecha ↓</option>
                <option value="entity_id">Producto ↑</option><option value="-entity_id">Producto ↓</option>
                <option value="-pred_chosen">Cantidad estimada ↓</option><option value="pred_chosen">Cantidad estimada ↑</option>
              </select>
            </label>
          </div>
        </details>
      </form>
      <fieldset class="seg" aria-label="Ver por">
        <legend>Ver por</legend>
        <button type="button" class="secondary" data-testid="level-sku" [attr.aria-pressed]="f.level === 'sku'" (click)="setLevel('sku')">Producto</button>
        <button type="button" class="secondary" data-testid="level-cat" [attr.aria-pressed]="f.level === 'categoria'" (click)="setLevel('categoria')">Categoría</button>
      </fieldset>
    </section>

    @if (shownRun(); as r) {
      <p class="muted" data-testid="run-dates">Ventas utilizadas hasta el <strong>{{ d(r.origin ?? r.cutoff) }}</strong>@if (r.target_start) { · fechas estimadas: <strong>{{ d(r.target_start) }} al {{ d(r.target_end) }}</strong> }</p>
    }

    <p class="muted" data-testid="units-note">
      Cantidades en <strong>unidades base</strong> (la unidad en que se registra la venta de cada producto). La cantidad estimada es la venta diaria que
      calcula el promedio de los últimos 28 días con ventas registradas.
    </p>

    <app-state-panel [state]="l.state()" emptyText="No hay estimaciones para estos filtros. Prueba quitar el código o ampliar las fechas." (retry)="l.reload()">
      @if (data(); as page) {
        @if (insufficient()) {
          <p class="notice warn" data-testid="insufficient">Datos insuficientes para evaluar algunas filas: se marcan «no evaluable» y no cuentan para la comparación.</p>
        }
        @if (generated() && !anyObserved()) {
          <p class="notice info" data-testid="no-observed-note">Aún no hay ventas registradas para comparar: este análisis se creó antes de que ocurrieran las ventas de esas fechas. No es un cero.</p>
        }
        <p><button type="button" class="secondary small" data-testid="toggle-details" [attr.aria-pressed]="details()" (click)="details.set(!details())">Comparar métodos / ver detalles</button></p>
        <div class="table-wrap" tabindex="0" role="region" aria-label="Tabla de ventas previstas">
        <table data-testid="forecast-table">
          <thead>
            <tr>
              <th scope="col">{{ f.level === 'categoria' ? 'Categoría' : 'Producto' }}</th><th scope="col">Fecha</th>
              <th scope="col" class="num">Cantidad estimada (unidades base)</th>
              @if (showObserved()) { <th scope="col" class="num">Vendido (registrado)</th> }
              @if (details()) {
                <th scope="col">Identificador</th><th scope="col">Tipo de historial</th><th scope="col" class="num">Día de la previsión</th>
                @if (hasRf()) { <th scope="col" class="num">Modelo experimental</th> }<th scope="col" class="num">Control (siempre cero)</th><th scope="col">Evaluable</th>
              }
            </tr>
          </thead>
          <tbody>
            @for (x of page.items; track x.entity_id + x.target_date) {
              <tr>
                <td>{{ who(x) }}</td><td>{{ d(x.target_date) }}</td>
                <td class="num">{{ dec(x.pred.promedio_28) }}</td>
                @if (showObserved()) { <td class="num" data-testid="observed">{{ observedText(x) }}</td> }
                @if (details()) {
                  <td>{{ x.entity_id }}</td><td>{{ x.cohorte ?? '—' }}</td><td class="num">{{ x.h }}</td>
                  @if (hasRf()) { <td class="num">{{ x.pred.rf_categoria_distribuido === null ? na : dec(x.pred.rf_categoria_distribuido) }}</td> }<td class="num">{{ dec(x.pred.cero) }}</td>
                  <td data-testid="evaluable">{{ x.evaluable === null || x.evaluable === undefined ? na : x.evaluable ? 'Sí' : 'No' }}</td>
                }
              </tr>
            }
          </tbody>
        </table>
        </div>
        <app-pager [page]="page.page" [pageSize]="page.page_size" [total]="page.total" [hasMore]="page.has_more" (go)="go($event)" />
      }
    </app-state-panel>

    <details class="help" data-testid="forecast-help">
      <summary>Cómo leer esta tabla</summary>
      <div data-testid="forecast-note">
        <p>Cantidades en unidad base. Método elegido: promedio de los últimos 28 días (promedio_28).</p>
        @if (final()) {
          <p>Hay dos tipos de historial: «primaria» e «historia_corta». «rf_categoria_distribuido» (modelo experimental) es el comparador y «cero» el control; con un solo bloque no se declara ganador.
            Las ventas registradas pueden estar limitadas por stock. En el nivel categoría, la estimación es la suma de las de cada producto (unidades base heterogéneas).
            Los productos nuevos (primera venta posterior al corte) no son filas: se resumen en la cobertura de la comparación.</p>
        } @else if (generated()) {
          <p>Análisis creado por la aplicación: no hay ventas registradas posteriores a la fecha de corte, por eso «vendido» y «evaluable» figuran «{{ na }}» (no son cero).
            El modelo experimental solo aparece si el análisis lo publica.</p>
        } @else {
          <p>Los valores «vendido» existen solo porque es un ejemplo histórico (ventas registradas en Excel; pueden estar limitadas por stock).
            «rf_categoria_distribuido» es un modelo experimental que no resultó mejor. Las estimaciones no incluyen agosto.</p>
        }
        <p>«cero» es solo una referencia de control. «Día de la previsión» indica cuántos días después de la fecha de corte cae la estimación.</p>
      </div>
    </details>
  `,
  styles: `
    .more { flex-basis: 100%; }
    .more .filters { margin: 0.3rem 0; }
  `,
})
export class ForecastsPage {
  private api = inject(ApiService);
  private store = inject(RunsStore);
  dec = (v: unknown) => fmtDec(v);
  na = NA;
  d = (v: string | undefined | null) => fmtDate(v);
  nameOf = (r: Parameters<typeof analysisName>[0]) => analysisName(r);
  replacedOf = (r: Parameters<typeof isReplaced>[0]) => isReplaced(r);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);
  /** Análisis elegido (parámetro de URL «run»); sin él, el que está en uso por defecto. */
  choice = new RunChoice(this.route, this.router, this.destroyRef, () => { this.page.set(1); this.l.reload(); });
  f = { level: 'sku' as 'sku' | 'categoria', sku: '', categoria: '', cohorte: '', from: '', to: '', sort: 'target_date' };
  details = signal(false);
  private page = signal(1);
  private pageSize = 50;
  private q = signal<ForecastQuery>({ level: 'sku', page: 1, page_size: this.pageSize, sort: 'target_date' });

  l = load<ForecastPage>(() => this.api.forecasts({ ...this.q(), run_id: this.choice.id() ?? undefined }), (d) => d.items.length === 0);
  data = computed(() => { const s = this.l.state(); return s.kind === 'data' ? s.data : null; });
  insufficient = computed(() => !this.generated() && (this.data()?.items ?? []).some((x) => x.evaluable === false || (x.evaluable === null && x.observed !== null)));
  /** El modelo experimental solo se muestra si alguna fila trae valores. */
  hasRf = computed(() => (this.data()?.items ?? []).some((x) => x.pred.rf_categoria_distribuido !== null && x.pred.rf_categoria_distribuido !== undefined));
  /** Hay al menos un valor registrado (cero real incluido) o un día marcado «no evaluable». */
  anyObserved = computed(() => (this.data()?.items ?? []).some((x) => (x.observed !== null && x.observed !== undefined) || x.evaluable === false));
  runs = computed(() => this.store.runs());
  /** El análisis mostrado: el elegido o, por defecto, el que está en uso. */
  shownRun = computed(() => this.store.resolve(this.choice.id()));
  name = computed(() => analysisName(this.shownRun()));
  replaced = computed(() => isReplaced(this.shownRun()));
  generated = computed(() => isGenerated(this.shownRun()?.kind));
  final = computed(() => isFinal(this.shownRun()?.kind));
  /** La columna «Vendido (registrado)» aparece si el análisis tiene ventas registradas o al abrir los detalles. */
  showObserved = computed(() => this.details() || !this.generated() || this.anyObserved());
  /** Última fecha objetivo admitida: 21/08/2026 solo para la evaluación; 31/07/2026 en las demás (agosto reservado). */
  maxDate = computed(() => (this.final() ? '2026-08-21' : '2026-07-31'));

  constructor() { this.store.ensure(); }

  /** «Producto 1010004 · Higiene capilar» (sin nombres inventados); en el nivel categoría, solo la categoría. */
  who(x: ForecastItem): string {
    return x.level === 'categoria' ? categoryLabel(x.categoria ?? x.entity_id) : productLabel(x.sku ?? x.entity_id, x.categoria);
  }

  /** Vendido (registrado): un día sin registros es «no evaluable» y un dato ausente es «sin dato»; ninguno es cero. */
  observedText(x: { observed?: number | null; evaluable?: boolean | null }): string {
    if (x.evaluable === false) return 'no evaluable';
    return x.observed === null || x.observed === undefined ? this.na : this.dec(x.observed);
  }

  private build(page: number): ForecastQuery {
    const t = (v: string) => v.trim() || undefined;
    return {
      level: this.f.level, sku: t(this.f.sku), categoria: t(this.f.categoria), cohorte: t(this.f.cohorte),
      from: this.f.from || undefined, to: this.f.to || undefined, sort: this.f.sort, page, page_size: this.pageSize,
    };
  }
  setLevel(level: 'sku' | 'categoria') { if (this.f.level !== level) { this.f.level = level; this.apply(); } }
  apply() { this.page.set(1); this.q.set(this.build(1)); this.l.reload(); }
  go(p: number) { this.page.set(p); this.q.set({ ...this.q(), page: p }); this.l.reload(); }
}
