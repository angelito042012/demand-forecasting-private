import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { map, tap } from 'rxjs';
import { ApiService } from '../core/api.service';
import { AuthService } from '../core/auth.service';
import { JobBoard, STAGE_LABELS } from '../core/jobs';
import { load } from '../core/load';
import {
  AppError, JobType, PlanAccepted, PlanCompareResponse, StockDiscrepancyPlan, PlanCreateBody, PlanDailyRow, PlanHeader, PlanInputs, PlanList, PlanRef, PlanResultDetail,
  PlanResultsPage, PlanStep,
} from '../core/models';
import { fmtDate } from '../core/format';
import { jobStatusWords, longDate, monthName } from '../core/ux-text';
import { PageHeader } from '../ui/page-header';
import { StatePanel } from '../ui/state-panel';
import { Pager } from '../ui/pager';
import { PlanForm } from './plan-form';
import { localDay, localStamp, zoneLabel } from './inventory.page';
import { stampWords } from './stock.page';
import {
  NOT_COMPUTABLE, NOT_REPORTED, PENDING_NATURE, STATUS_FILTERS, purchaseText, qtyText, statusText, statusTone, stepValue,
} from './plan-text';

const SORTS: { value: string; label: string }[] = [
  { value: 'producto_id', label: 'Código (menor a mayor)' },
  { value: '-producto_id', label: 'Código (mayor a menor)' },
  { value: 'producto', label: 'Producto (A a Z)' },
  { value: '-forecast', label: 'Ventas previstas (más a menos)' },
  { value: 'libre', label: 'Stock del conteo (menos a más)' },
];

/** T19: Planificar compras. Muestra lo que entrega la API; ninguna cifra se calcula en el navegador. */
@Component({
  selector: 'app-plan-page',
  imports: [FormsModule, PageHeader, StatePanel, Pager, PlanForm],
  template: `
    <app-page-header title="Compra recomendada"
      lead="Revisa cuántas unidades comprar de cada producto para cubrir un mes, a partir de las ventas previstas, las existencias y el plazo de entrega." />

    <p class="notice warn" data-testid="plan-band" role="note"><strong>Plan de compra bajo supuestos.</strong>
      No es un pedido ejecutado ni una mejora comprobada: son unidades propuestas con datos hasta una fecha de corte, un conteo informado y parámetros que se pueden cambiar.</p>

    @if (forbidden()) {
      <p class="notice danger" role="alert" data-testid="plan-forbidden">No tienes permiso para ver los planes de compra. Ingresa con otro usuario o avisa al administrador.</p>
    } @else {
      <app-state-panel [state]="inp.state()" emptyText="No hay datos disponibles para planificar." (retry)="loadInputs()">
        @if (inputs(); as i) {
          @if (i.unavailable_reason || !i.dataset || !i.snapshot) {
            <p class="notice warn" role="status" data-testid="plan-unavailable">
              No se puede planificar todavía: falta {{ !i.dataset ? 'cargar las ventas' : 'cargar el conteo de inventario' }}.
            </p>
          }
          @if (cutoff(); as c) {
            <p class="notice warn" data-testid="plan-cutoff">
              Las ventas registradas terminan el <strong>{{ longDate(c) }}</strong>. Lo ocurrido después de esa fecha{{ gapMonth() ? ' (por ejemplo ' + gapMonth() + ')' : '' }} es desconocido, no es cero.
              @if (pendingNote(); as n) { <strong data-testid="plan-pending-note">{{ n }}</strong> }
            </p>
          }
          <section class="toolbar" aria-label="Elegir el plan" data-testid="plan-picker">
            <div class="filters">
              <label>Mes
                <select name="month" data-testid="plan-month" [ngModel]="month()" (ngModelChange)="setMonth($event)">
                  @for (m of monthOptions(); track m) { <option [value]="m">{{ monthLabel(m) }}</option> }
                </select>
              </label>
              @if (versions().length > 1) {
                <label>Versión del plan
                  <select name="ver" data-testid="plan-version" [ngModel]="planId()" (ngModelChange)="pickPlan($event)">
                    @for (v of versions(); track v.plan_id) { <option [value]="v.plan_id">{{ versionLabel(v) }}</option> }
                  </select>
                </label>
              }
            </div>
          </section>
        }
      </app-state-panel>

      <app-state-panel [state]="pl.state()" emptyText="Todavía no se generó un plan para este mes." (retry)="pl.reload()">
        @if (planId()) {
          <app-state-panel [state]="hdr.state()" (retry)="hdr.reload()">
            @if (header(); as h) {
              <section class="surface" aria-labelledby="h-src" data-testid="plan-source">
                <h2 id="h-src">De dónde sale este plan</h2>
                <ul class="plain">
                  <li data-testid="src-sales"><strong>Ventas reales:</strong> registradas hasta el {{ longDate(cutoff()) }}.</li>
                  @if (reconstructed()) {
                    <li data-testid="src-count"><strong>Existencia reconstruida al cierre del {{ countDay() }} (conteo reportado {{ baseStamp() }} + movimientos del sistema)</strong>{{ warehouseName() ? ' · ' + warehouseName() : '' }}.
                      El conteo lo informó la empresa y no se verificó de forma independiente; los movimientos vienen del sistema{{ lastMovement() ? ' hasta el ' + lastMovement() : '' }}.</li>
                  } @else {
                    <li data-testid="src-count"><strong>Conteo reportado por la empresa:</strong> {{ countStamp() }}{{ warehouseName() ? ' · ' + warehouseName() : '' }}. Lo informó la empresa y no se verificó de forma independiente.</li>
                  }
                  <li data-testid="src-projection"><strong>Proyección posterior:</strong> calculada con el promedio de los últimos 28 días de ventas; no son ventas observadas. Estima ventas registradas, que pueden haber estado limitadas por falta de stock.</li>
                  <li data-testid="src-params"><strong>Configuración de reposición</strong> (parámetros configurados por el administrador, no condiciones confirmadas del proveedor):
                    decisión de compra el {{ longDate(h.params?.decision_date ?? h.decision_date) }} · plazos de entrega de {{ leadText() }} días
                    @if (h.params; as p) {
                      · reserva de {{ p.reserve_days }} días · compra mínima {{ p.min_order }} · múltiplo {{ p.order_multiple }}
                    }
                  </li>
                  <li data-testid="src-orders"><strong>Pedidos por recibir:</strong> {{ pendingNote() }}
                    @if (pendingOrders().length) {
                      <ul class="plain" data-testid="src-pending">
                        @for (o of pendingOrders(); track $index) {
                          <li data-testid="src-pending-item">Producto <strong>{{ o.producto_id }}</strong> · {{ o.units }} unidades · llega el {{ shortDate(o.arrival_date) }} · {{ pendingNature(o.nature) }}</li>
                        }
                      </ul>
                    }
                  </li>
                </ul>
                @if (h.distances; as d) {
                  <p class="muted" data-testid="src-distance">
                    Distancia desde el último día con ventas:
                    @if (d.cutoff_to_count !== undefined) { el conteo es {{ d.cutoff_to_count }} días posterior; }
                    @if (d.cutoff_to_month_start !== undefined) { el mes empieza {{ d.cutoff_to_month_start }} días después; }
                    @if (d.cutoff_to_month_end !== undefined) { termina {{ d.cutoff_to_month_end }} días después. }
                    Cuanto más lejos del último dato, más incierta es la previsión.
                  </p>
                }
                @if (h.warnings?.length) {
                  <ul class="plain" data-testid="plan-warnings">@for (w of h.warnings; track w) { <li>{{ w }}</li> }</ul>
                }
                @if (pendingConfirmations().length) {
                  <div class="notice warn" role="status" data-testid="plan-confirmations">
                    <strong>Pendiente de confirmar con la empresa</strong>
                    <ul class="plain">@for (c of pendingConfirmations(); track c.code) { <li [attr.data-code]="c.code">{{ c.text }}</li> }</ul>
                  </div>
                }
                <details class="help" data-testid="plan-tech">
                  <summary>Detalles técnicos del plan</summary>
                  <ul class="plain">
                    <li>Identificador: {{ h.plan_id }}</li>
                    <li>Creado: {{ stampOf(h.created_at) }} · versión de datos: {{ h.dataset_id || 'no informada' }} · conteo: {{ h.snapshot_id || 'no informado' }}</li>
                    @for (a of h.assumptions ?? []; track a.text) { <li>Supuesto{{ a.nature ? ' (' + a.nature + ')' : '' }}: {{ a.text }}</li> }
                  </ul>
                </details>
              </section>
            }
          </app-state-panel>

          @if (versions().length > 1) {
            <section class="surface" aria-label="Comparar versiones" data-testid="plan-compare">
              <form class="filters" (submit)="$event.preventDefault(); compare()">
                <label>Versión con la que comparar
                  <select name="cmp" data-testid="plan-compare-with" [ngModel]="otherId() || otherVersions()[0]?.plan_id" (ngModelChange)="otherId.set($event)">
                    @for (v of otherVersions(); track v.plan_id) { <option [value]="v.plan_id">{{ versionLabel(v) }}</option> }
                  </select>
                </label>
                <button type="submit" class="secondary small" data-testid="plan-compare-btn" [disabled]="!otherVersions().length">Comparar con otra versión</button>
              </form>
              @if (compareOpen()) {
                <app-state-panel [state]="cmp.state()" emptyText="No hay productos para comparar." (retry)="cmp.reload()">
                  @if (compared(); as c) {
                    <p class="notice warn" data-testid="cmp-note" role="note">Las existencias de las dos versiones son de fechas distintas: cada una parte del cierre de su propia fecha de existencias, así que las diferencias de compra no se deben solo a la previsión.{{ c.note ? ' ' + c.note : '' }}</p>
                    <div class="table-wrap" tabindex="0" role="region" aria-label="Comparación de versiones del plan">
                      <table data-testid="cmp-table">
                        <caption class="muted">A = {{ sideLabel(c.base) }} · B = {{ sideLabel(c.other) }}</caption>
                        <thead><tr>
                          <th scope="col">Producto</th>
                          <th scope="col" class="num">Ventas previstas del mes (A → B)</th>
                          <th scope="col" class="num">Existencias (A → B)</th>
                          @for (l of cmpLeads(c); track l) { <th scope="col" class="num">Compra a {{ l }} días (A → B)</th> }
                        </tr></thead>
                        <tbody>
                          @for (r of c.items; track r.producto_id) {
                            <tr [attr.data-sku]="r.producto_id">
                              <td data-col="product"><strong>{{ r.producto_id }}</strong> {{ r.producto }}</td>
                              <td class="num" data-col="forecast">{{ pair(r.a?.month_total, r.b?.month_total) }}</td>
                              <td class="num" data-col="stock">{{ pair(r.a?.libre, r.b?.libre) }}</td>
                              @for (l of cmpLeads(c); track l) {
                                <td class="num" [attr.data-col]="'buy-' + l">{{ pair(r.a?.purchase?.[l], r.b?.purchase?.[l]) }}</td>
                              }
                            </tr>
                          }
                        </tbody>
                      </table>
                    </div>
                  }
                </app-state-panel>
              }
            </section>
          }

          <section class="toolbar" aria-label="Filtros de la tabla de compras" data-testid="plan-filters">
            <form class="filters" (ngSubmit)="search()" aria-label="Buscar en el plan">
              <label>Código o nombre <input name="q" [(ngModel)]="draft" autocomplete="off" maxlength="100" data-testid="plan-q" /></label>
              <label>Estado
                <select name="status" data-testid="plan-status" [ngModel]="status()" (ngModelChange)="setStatus($event)">
                  @for (s of statusFilters; track s.value) { <option [value]="s.value">{{ s.label }}{{ countOf(s.value) }}</option> }
                </select>
              </label>
              <label>Ordenar por
                <select name="sort" data-testid="plan-sort" [ngModel]="sort()" (ngModelChange)="setSort($event)">
                  @for (o of sorts; track o.value) { <option [value]="o.value">{{ o.label }}</option> }
                </select>
              </label>
              <button type="submit" class="small" [class.btn]="!isAdmin" [class.secondary]="isAdmin" data-testid="plan-search">Buscar</button>
            </form>
          </section>

          <app-state-panel [state]="res.state()" emptyText="Este plan no tiene productos." (retry)="res.reload()">
            @if (results(); as d) {
              @if (d.items.length === 0) {
                <p class="state" data-testid="plan-no-match">Ningún producto coincide con la búsqueda o el estado elegido.</p>
              } @else {
                <p class="muted" data-testid="plan-summary">{{ d.total }} productos en este plan.</p>
                <div class="table-wrap" tabindex="0" role="region" aria-label="Tabla del plan de compra">
                  <table data-testid="plan-table">
                    <thead>
                      <tr>
                        <th scope="col" rowspan="2">Producto y presentación</th>
                        <th scope="col" rowspan="2" class="num">Ventas previstas <small>(mes, sin limitar por stock)</small></th>
                        <th scope="col" rowspan="2" class="num">{{ reconstructed() ? 'Existencias' : 'Stock del conteo' }} <small>({{ reconstructed() ? 'cierre ' : '' }}{{ countDay() }})</small></th>
                        @for (l of leads(); track l) { <th scope="colgroup" colspan="4" [attr.data-lead]="l">Plazo de entrega de {{ l }} días</th> }
                      </tr>
                      <tr>
                        @for (l of leads(); track l) {
                          <th scope="col">Llega el</th><th scope="col" class="num">Stock al inicio del mes</th>
                          <th scope="col" class="num">Compra recomendada</th><th scope="col" class="num">Faltantes</th>
                        }
                      </tr>
                    </thead>
                    <tbody>
                      @for (r of d.items; track r.producto_id) {
                        <tr [attr.data-sku]="r.producto_id">
                          <td data-col="product">
                            <strong data-col="code">{{ r.producto_id }}</strong> {{ r.producto }}
                            <span class="muted" data-col="unit"> · {{ r.unidad_descripcion || NOT_REPORTED }}</span><br />
                            @if (r.stock_provenance?.discrepancy; as dx) {
                              <span class="chip warn" data-testid="plan-diff-chip">Diferencia con el sistema</span>
                              <span class="muted" data-testid="plan-diff-text"> {{ discText(dx) }}</span><br />
                            }
                            <button type="button" class="secondary small" data-testid="plan-understand" [attr.aria-label]="'Entender la compra de ' + r.producto" (click)="pick(r.producto_id)">Entender la compra</button>
                          </td>
                          <td class="num" data-col="forecast">{{ qty(r.forecast?.month_total) }}</td>
                          <td class="num" data-col="count">{{ qty(r.count_stock.libre, NOT_REPORTED) }}</td>
                          @for (l of leads(); track l) {
                            @if (r.scenarios[l]; as sc) {
                              <td [attr.data-col]="'arrival-' + l">{{ sc.arrival_date ? shortDate(sc.arrival_date) : 'No llega en el mes' }}</td>
                              <td class="num" [attr.data-col]="'start-' + l">{{ qty(sc.stock_month_start) }}</td>
                              <td class="num" [attr.data-col]="'buy-' + l">
                                @if (buy(sc); as b) { <strong>{{ b }}</strong><br /> }
                                <span [attr.class]="'chip ' + tone(sc.status)" [attr.data-status]="sc.status">{{ stat(sc) }}</span>
                              </td>
                              <td class="num" [attr.data-col]="'short-' + l">{{ shortages(sc) }}</td>
                            } @else {
                              <td colspan="4" [attr.data-col]="'none-' + l">{{ NOT_COMPUTABLE }}</td>
                            }
                          }
                        </tr>
                      }
                    </tbody>
                  </table>
                </div>
              }
              <app-pager [page]="d.page" [pageSize]="d.page_size" [total]="d.total" [hasMore]="d.has_more" (go)="go($event)" />
              <p class="muted" data-testid="plan-units-note">Las cantidades están en la presentación indicada de cada producto (caja, pack, frasco); no se multiplicaron. Por eso no se muestra un total general de unidades ni valores en dinero.</p>
              <p class="muted" data-testid="plan-forecast-note">«Ventas previstas del mes» es lo que se estima vender sin limitar por stock. Lo que sí podría atenderse con las existencias de cada plazo está en «Entender la compra».</p>
            }
          </app-state-panel>

          @if (sel(); as code) {
            <section class="surface" aria-labelledby="h-explain" data-testid="plan-explain">
              <h2 id="h-explain">Entender la compra</h2>
              <app-state-panel [state]="det.state()" (retry)="det.reload()">
                @if (detail(); as x) {
                  <p><strong>{{ x.producto_id }}</strong> {{ x.producto }} <span class="muted">· {{ x.unidad_descripcion || NOT_REPORTED }}</span></p>
                  <ul class="plain" data-testid="ex-forecast">
                    <li>Ventas previstas del mes, sin limitar por stock: <strong>{{ qty(x.forecast?.month_total) }}</strong>
                      @if (x.forecast; as fc) {
                        @if (fc.daily !== null && fc.daily !== undefined) { ({{ qty(fc.daily) }} por día }
                        @if (fc.sum_28 !== undefined && fc.days_valid !== undefined) { = {{ qty(fc.sum_28) }} unidades vendidas en {{ fc.days_valid }} días válidos }
                        @if (fc.daily !== null && fc.daily !== undefined) { ) }
                      }
                    </li>
                    <li>{{ reconstructed() ? 'Existencia inicial (cierre del ' + countDay() + ')' : 'Stock del conteo' }}: <strong>{{ qty(x.count_stock.libre, NOT_REPORTED) }}</strong>{{ reconstructed() ? '' : ' (' + countDay() + ')' }}.
                      @if (x.stock_provenance; as sp) {
                        @if (sp.base_count !== undefined && sp.base_count !== null) { <span data-testid="ex-prov">Conteo base {{ qty(sp.base_count) }}{{ sp.movements_net_to_closing !== undefined && sp.movements_net_to_closing !== null ? ' y movimientos netos hasta el cierre ' + qty(sp.movements_net_to_closing) : '' }}.</span> }
                      }
                    </li>
                    @if (x.stock_provenance?.discrepancy; as dx) {
                      <li data-testid="ex-diff"><span class="chip warn">Diferencia con el sistema</span> {{ discText(dx) }}</li>
                    }
                    @for (o of x.pending_orders ?? []; track $index) {
                      <li data-testid="ex-pending">Pedido por recibir de este producto: {{ o.units }} unidades el {{ shortDate(o.arrival_date) }}.</li>
                    }
                  </ul>
                  <div class="plan-cols">
                    @for (l of leadsOf(x); track l) {
                      @if (x.scenarios[l]; as sc) {
                        <article class="card" [attr.data-testid]="'ex-lead-' + l">
                          <h3>Plazo de {{ l }} días</h3>
                          <p><span [attr.class]="'chip ' + tone(sc.status)">{{ stat(sc) }}</span>
                            {{ sc.arrival_date ? 'Llega el ' + longDate(sc.arrival_date) : 'No llega dentro del mes' }}</p>
                          @if (sc.status === 'NO_LLEGA_A_TIEMPO' && sc.required_arrival_date) {
                            <p data-testid="ex-decide">Para que llegue el primer día del mes habría que decidir la compra el {{ longDate(sc.required_arrival_date) }}.</p>
                          }
                          <p data-testid="ex-buy">Compra recomendada: <strong>{{ buy(sc) ?? NOT_COMPUTABLE }}</strong></p>
                          @if (stepsFor(x, l); as steps) {
                            @if (steps.length) {
                              <ol class="steps" [attr.data-testid]="'ex-steps-' + l">
                                @for (s of steps; track $index) {
                                  <li><strong>{{ s.label }}</strong>@if (s.text) { : {{ s.text }} }@if (val(s.value)) { <span class="num"> = <strong>{{ val(s.value) }}</strong></span> }</li>
                                }
                              </ol>
                            } @else {
                              <p class="muted">La API no entregó el desglose de este plazo.</p>
                            }
                          }
                          <ul class="plain" data-testid="ex-served">
                            <li>Ventas previstas sin limitar por stock: {{ qty(x.forecast?.month_total) }}</li>
                            <li>Ventas que podrían atenderse en este escenario: <strong>{{ qty(sc.served_month) }}</strong></li>
                            <li>Faltante en el mes: {{ qty(sc.shortage_month) }}</li>
                          </ul>
                          <details class="help" [attr.data-testid]="'ex-daily-' + l">
                            <summary>Ver el día a día del plazo de {{ l }} días</summary>
                            @if (dailyFor(x, l); as rows) {
                              @if (rows.length) {
                                <div class="table-wrap" tabindex="0" role="region" [attr.aria-label]="'Serie diaria del plazo de ' + l + ' días'">
                                  <table>
                                    <caption class="muted">Cada día primero llegan los pedidos y después se consume la demanda.</caption>
                                    <thead><tr><th scope="col">Día</th><th scope="col" class="num">Al inicio</th><th scope="col" class="num">Llega</th>@if (hasAvailable(rows)) { <th scope="col" class="num">Disponible</th> }<th scope="col" class="num">Demanda</th><th scope="col" class="num">Atendida</th><th scope="col" class="num">Faltante</th><th scope="col" class="num">Al cierre</th></tr></thead>
                                    <tbody>
                                      @for (r of rows; track r.fecha) {
                                        <tr><th scope="row">{{ shortDate(r.fecha) }}</th><td class="num">{{ qty(r.inicio) }}</td><td class="num">{{ qty(r.recepciones) }}</td>@if (hasAvailable(rows)) { <td class="num">{{ qty(r.disponible) }}</td> }<td class="num">{{ qty(r.demanda) }}</td><td class="num">{{ qty(r.atendida) }}</td><td class="num">{{ qty(r.faltante) }}</td><td class="num">{{ qty(r.fin) }}</td></tr>
                                      }
                                    </tbody>
                                  </table>
                                </div>
                              } @else { <p class="muted">La API no entregó la serie diaria de este plazo.</p> }
                            }
                          </details>
                        </article>
                      }
                    }
                  </div>
                }
              </app-state-panel>
            </section>
          }
        }
      </app-state-panel>

      @if (isAdmin) {
        @if (genJob(); as j) {
          <section class="notice" [class.ok]="j.status === 'completed'" [class.danger]="j.status === 'failed'" [class.info]="j.status !== 'completed' && j.status !== 'failed'"
            role="status" data-testid="plan-job">
            <p><strong data-testid="plan-job-status">{{ jobWords(j.status) }}</strong>
              @if (j.status === 'queued' || j.status === 'running') { · {{ stageWords(j.stage) }} }</p>
            @if (j.status === 'completed') { <p>Listo: el plan se generó y ya se muestra arriba.</p> }
            @if (j.status === 'failed') {
              <p data-testid="plan-job-error">No se pudo generar el plan. Puedes intentarlo de nuevo; si se repite, avisa al administrador del sistema.</p>
              <button type="button" class="secondary small" data-testid="plan-retry" (click)="retryGenerate()">Reintentar</button>
            }
          </section>
        }
        @if (reusedNote()) {
          <p class="notice ok" role="status" data-testid="plan-reused">Ya existía un plan con exactamente estos datos: se reutilizó y no se calculó de nuevo.</p>
        }
        @if (genError(); as e) {
          <div class="notice danger" role="alert" data-testid="plan-gen-error">
            <p>{{ e }}</p>
            <button type="button" class="secondary small" data-testid="plan-retry" (click)="retryGenerate()">Reintentar</button>
          </div>
        }
        @if (inputs(); as i) {
          @if (i.dataset && i.snapshot && i.defaults) { <app-plan-form [inputs]="i" [sending]="sending()" (submitted)="generate($event)" /> }
        }
      }
    }
  `,
  styles: `
    .plan-cols { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 19rem), 1fr)); gap: 1rem; margin: 1rem 0; }
    td, th { vertical-align: top; }
  `,
})
export class PlanPage {
  private api = inject(ApiService);
  private auth = inject(AuthService);
  private destroyRef = inject(DestroyRef);
  /** Solo orientación: el servidor decide los permisos. */
  isAdmin = this.auth.isAdmin;

  readonly NOT_COMPUTABLE = NOT_COMPUTABLE;
  readonly NOT_REPORTED = NOT_REPORTED;
  readonly statusFilters = STATUS_FILTERS;
  readonly sorts = SORTS;
  readonly longDate = longDate;
  readonly qty = qtyText;
  readonly tone = statusTone;
  readonly val = stepValue;
  readonly pageSize = 50;

  month = signal('');
  planId = signal<string | null>(null);
  private wantPlan: string | null = null;
  q = signal('');
  draft = '';
  status = signal('');
  sort = signal('producto_id');
  page = signal(1);
  sel = signal<string | null>(null);

  inp = load<PlanInputs>(() => this.api.planInputs().pipe(tap((i) => {
    if (!this.month() && i.defaults?.month) this.month.set(i.defaults.month);
    this.pl.reload();
  })));
  inputs = computed(() => { const s = this.inp.state(); return s.kind === 'data' ? s.data : null; });

  versions = signal<PlanRef[]>([]);
  pl = load<PlanList>(
    () => this.api.plans(this.month() || undefined).pipe(
      map((r) => (Array.isArray(r) ? { items: r } : r)),
      tap((r) => {
        const items = r.items ?? [];
        this.versions.set(items);
        const keep = this.wantPlan && items.some((p) => p.plan_id === this.wantPlan) ? this.wantPlan : null;
        this.wantPlan = null;
        const chosen = keep ?? (items.some((p) => p.plan_id === this.planId()) ? this.planId() : items[0]?.plan_id ?? null);
        if (chosen !== this.planId()) this.clearPlan();
        this.planId.set(chosen);
        this.sel.set(null);
        if (chosen) { this.hdr.reload(); this.res.reload(); }
      }),
    ),
    (r) => !r.items?.length || r.unavailable_reason === 'SIN_PLAN',
    false,
  );
  hdr = load<PlanHeader>(() => this.api.plan(this.planId()!), () => false, false);
  header = computed(() => { const s = this.hdr.state(); return s.kind === 'data' ? s.data : null; });
  res = load<PlanResultsPage>(
    () => this.api.planResults(this.planId()!, { q: this.q(), status: this.status(), sort: this.sort(), page: this.page(), page_size: this.pageSize }),
    () => false, false,
  );
  results = computed(() => { const s = this.res.state(); return s.kind === 'data' ? s.data : null; });
  det = load<PlanResultDetail>(() => this.api.planResult(this.planId()!, this.sel()!), () => false, false);
  detail = computed(() => { const s = this.det.state(); return s.kind === 'data' ? s.data : null; });

  forbidden = computed(() => [this.inp.state(), this.pl.state(), this.hdr.state(), this.res.state()]
    .some((s) => s.kind === 'error' && (s.error.status === 403 || s.error.code === 'PROHIBIDO')));

  // ---- procedencia (todo viene de la API) ----
  /** Con un plan elegido, el corte es el DE ESE PLAN (nunca el del dataset más nuevo); sin plan, el de las entradas. */
  cutoff = computed(() => {
    if (this.planId()) { const h = this.header(); return h?.dates?.sales_cutoff ?? h?.dataset?.sales_cutoff ?? null; }
    return this.inputs()?.dataset?.sales_cutoff ?? null;
  });
  pendingOrders = computed(() => this.header()?.params?.pending_orders ?? []);
  /** T20: la existencia inicial es reconstruida (conteo base + movimientos del sistema). Solo lo dice la cabecera del plan. */
  reconstructed = computed(() => (this.planId() ? this.header()?.snapshot?.kind : this.inputs()?.snapshot?.kind) === 'RECONSTRUIDO');
  baseStamp = computed(() => stampWords(this.header()?.snapshot?.base_count_as_of_local));
  lastMovement = computed(() => { const m = this.header()?.snapshot?.last_movement_local; return m ? stampWords(m) : ''; });
  pendingConfirmations = computed(() => (this.header()?.confirmations ?? []).filter((c) => c.status === 'PENDIENTE'));
  discText(d: StockDiscrepancyPlan): string {
    const when = d.compared_at_local ? stampWords(d.compared_at_local) : 'la fecha del último movimiento';
    return `Al ${when} el sistema indica ${qtyText(d.system_stock, NOT_REPORTED)} y la existencia reconstruida es ${qtyText(d.reconstructed, NOT_REPORTED)} `
      + `(diferencia ${qtyText(d.difference, NOT_REPORTED)}). Pendiente de confirmar; no se ajustó ninguna cantidad.`;
  }
  /** Texto del supuesto de pedidos tal como lo entrega la API (solo existencia reconstruida y sin pedidos declarados). */
  private apiOrdersAssumption = computed(() => this.header()?.assumptions?.find((a) => a.code === 'PEDIDOS_PENDIENTES')?.text ?? null);
  /** Aviso de pedidos por recibir DERIVADO del plan elegido; null mientras el plan elegido no se cargó. */
  pendingNote = computed((): string | null => {
    if (!this.planId()) return 'En este escenario no llegan otros pedidos (supuesto).';
    const h = this.header();
    if (!h?.params) return null;
    const n = h.params.pending_orders.length;
    if (n === 0 && this.reconstructed() && this.apiOrdersAssumption()) return this.apiOrdersAssumption();
    if (n === 0) return 'En este escenario no llegan otros pedidos (supuesto).';
    const who = n === 1 ? 'Se considera 1 pedido por recibir declarado' : `Se consideran ${n} pedidos por recibir declarados`;
    return `${who} (producto, unidades, fecha de llegada y si es reportado o asumido) y no llegan otros adicionales (supuesto).`;
  });
  pendingNature = (n: string) => PENDING_NATURE[n] ?? n;
  private countIso = computed(() => this.header()?.snapshot?.as_of_local ?? this.inputs()?.snapshot?.as_of_local ?? null);
  countStamp = computed(() => {
    const s = localStamp(this.countIso());
    return s ? `${s.replace(', ', ' a las ')} (${zoneLabel('America/Lima')})` : 'fecha no informada';
  });
  countDay = computed(() => localDay(this.countIso()) ?? 'fecha no informada');
  gapMonth = computed(() => monthName(this.countIso()?.slice(0, 10)));
  warehouseName = computed(() => {
    const w = this.header()?.snapshot?.warehouse ?? this.inputs()?.snapshot?.warehouse;
    if (!w) return '';
    return typeof w === 'string' ? `almacén ${w}` : `${w.name} (almacén ${w.id})`;
  });
  leads = computed(() => {
    const h = this.header()?.params?.lead_days ?? this.header()?.lead_days;
    if (h?.length) return h.map(String);
    const first = this.results()?.items[0];
    return first ? Object.keys(first.scenarios).sort((a, b) => Number(a) - Number(b)) : [];
  });
  leadText = computed(() => this.leads().join(' y '));
  monthOptions = computed(() => this.inputs()?.limits?.months ?? (this.month() ? [this.month()] : []));

  monthLabel = (m: string) => { const n = monthName(`${m}-01`); return n ? `${n} de ${m.slice(0, 4)}` : m; };
  versionLabel = (v: PlanRef) => `Creado el ${this.stampOf(v.created_at)} · decisión el ${fmtDate(v.decision_date)} · plazos ${v.lead_days.join(' y ')} días`;
  stampOf = (iso: string | undefined) => localStamp(iso) ?? 'fecha no informada';
  shortDate = (iso: string | null | undefined) => fmtDate(iso);
  countOf(v: string) { const c = v ? this.results()?.status_counts?.[v as 'OK'] : undefined; return c === undefined ? '' : ` (${c})`; }

  planMonth = () => this.header()?.month ?? this.month();
  /** Estado en palabras sencillas del escenario. */
  stat(sc: Parameters<typeof statusText>[0]) { return statusText(sc, this.planMonth()); }
  buy = purchaseText;
  shortages(sc: { shortage_before_month: string | null; shortage_month: string | null }): string {
    if (sc.shortage_month === null && sc.shortage_before_month === null) return NOT_COMPUTABLE;
    const parts: string[] = [];
    if (sc.shortage_before_month !== null) parts.push(`Antes del mes: ${qtyText(sc.shortage_before_month)}`);
    if (sc.shortage_month !== null) parts.push(`En el mes: ${qtyText(sc.shortage_month)}`);
    return parts.join(' · ');
  }
  leadsOf(x: PlanResultDetail): string[] { return Object.keys(x.scenarios).sort((a, b) => Number(a) - Number(b)); }
  stepsFor(x: PlanResultDetail, l: string): PlanStep[] { return x.scenarios[l]?.explanation ?? []; }
  dailyFor(x: PlanResultDetail, l: string): PlanDailyRow[] { return x.scenarios[l]?.series ?? []; }
  hasAvailable(rows: PlanDailyRow[]): boolean { return rows.some((r) => r.disponible !== undefined && r.disponible !== null); }

  // ---- T20: comparar versiones ----
  otherId = signal<string>('');
  compareOpen = signal(false);
  otherVersions = computed(() => this.versions().filter((v) => v.plan_id !== this.planId()));
  cmp = load<PlanCompareResponse>(() => this.api.comparePlans(this.planId()!, this.otherId()), (r) => !r.items?.length, false);
  compared = computed(() => { const s = this.cmp.state(); return s.kind === 'data' ? s.data : null; });
  compare() {
    if (!this.planId()) return;
    const other = this.otherId() || this.otherVersions()[0]?.plan_id;
    if (!other) return;
    this.otherId.set(other);
    this.compareOpen.set(true);
    this.cmp.reload();
  }
  sideLabel(s: PlanCompareResponse['base']): string {
    if (!s) return 'versión no informada';
    const v = s.version ? `v${s.version}` : (s.plan_id ?? '');
    return `${v}${s.created_at ? ' del ' + this.stampOf(s.created_at) : ''}`;
  }
  cmpLeads(c: PlanCompareResponse): string[] {
    const set = new Set<string>();
    for (const r of c.items) { Object.keys(r.a?.purchase ?? {}).forEach((k) => set.add(k)); Object.keys(r.b?.purchase ?? {}).forEach((k) => set.add(k)); }
    return [...set].sort((x, y) => Number(x) - Number(y));
  }
  /** «A → B»; un lado ausente o null se dice «No se puede calcular» (nunca 0). */
  pair(a: unknown, b: unknown): string {
    const f = (v: unknown) => qtyText(v as string | number | null | undefined);
    return `${f(a)} → ${f(b)}`;
  }

  // ---- acciones de lectura ----
  loadInputs() { this.inp.reload(); }
  /** Nada del plan anterior sobrevive: producto abierto, detalle, cabecera y resultados. */
  private clearPlan() {
    this.sel.set(null);
    this.compareOpen.set(false);
    this.otherId.set('');
    this.hdr.state.set({ kind: 'loading' });
    this.res.state.set({ kind: 'loading' });
    this.det.state.set({ kind: 'loading' });
  }
  setMonth(m: string) { if (m === this.month()) return; this.month.set(m); this.clearPlan(); this.planId.set(null); this.versions.set([]); this.page.set(1); this.pl.reload(); }
  pickPlan(id: string) { if (id === this.planId()) return; this.clearPlan(); this.planId.set(id); this.page.set(1); this.hdr.reload(); this.res.reload(); }
  search() { this.q.set(this.draft.trim()); this.page.set(1); this.res.reload(); }
  setStatus(v: string) { this.status.set(v); this.page.set(1); this.res.reload(); }
  setSort(v: string) { this.sort.set(v); this.page.set(1); this.res.reload(); }
  go(p: number) { this.page.set(p); this.res.reload(); }
  pick(code: string) { this.sel.set(code); this.det.reload(); }

  // ---- administrador: generar plan ----
  sending = signal(false);
  genError = signal<string | null>(null);
  reusedNote = signal(false);
  private lastBody: PlanCreateBody | null = null;
  board = new JobBoard(this.api, 'generate_plan', (j) => {
    if (j.status === 'completed') this.refreshAfter(this.pendingPlan);
  }, this.destroyRef);
  private pendingPlan: string | null = null;
  genJob = computed(() => this.board.jobs()[0] ?? null);
  jobWords = jobStatusWords;
  stageWords = (s: string | null | undefined) => (s ? (STAGE_LABELS[s] ?? 'Calculando el plan') : 'Calculando el plan');

  private refreshAfter(planId: string | null) {
    this.wantPlan = planId;
    if (planId) this.page.set(1);
    this.pl.reload();
  }

  generate(body: PlanCreateBody) {
    if (this.sending()) return;
    this.lastBody = body;
    this.sending.set(true);
    this.genError.set(null);
    this.reusedNote.set(false);
    this.api.createPlan(body).subscribe({
      next: (r: PlanAccepted) => {
        this.sending.set(false);
        this.pendingPlan = r.plan_id;
        if (body.month !== this.month()) this.month.set(body.month);
        if (r.reused) {
          this.reusedNote.set(true);
          this.refreshAfter(r.plan_id);
        } else {
          this.board.track(r.job_id, r.status);
        }
      },
      error: (e: AppError) => {
        this.sending.set(false);
        const extra = (e.details ?? []).map((d) => (typeof d === 'string' ? d : '')).filter(Boolean).join(' ');
        this.genError.set(
          e.status === 422 ? `El servidor no aceptó los datos del plan: ${e.message}${extra ? ' ' + extra : ''} Corrige el formulario e inténtalo de nuevo.`
          : e.status === 403 ? 'No tienes permiso para generar planes. Solo el administrador puede hacerlo.'
          : `${e.message} Puedes intentarlo de nuevo.`,
        );
      },
    });
  }

  retryGenerate() { if (this.lastBody) this.generate(this.lastBody); }
}
