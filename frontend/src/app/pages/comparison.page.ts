import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { catchError, map, of, tap, throwError } from 'rxjs';
import { RunChoice, isFinal, isGenerated } from '../core/run-choice';
import { ApiService } from '../core/api.service';
import { RunsStore } from '../core/runs-store';
import { load } from '../core/load';
import { BacktestDetail, BacktestItem, Cohorte, Page, PredRow } from '../core/models';
import {
  AGREGADO, BASE_POLICY, COHORTES, METHOD_INFO, POLICIES, PRED_COHORTES, SIM_LABELS, SimRow, VISTAS,
  coverageOf, foldsOf, kindOf, predRows, simRows,
} from '../core/backtest';
import { DASH, fmtDate, fmtInt, fmtPct, fmtPen, fmtPp, fmtDec } from '../core/format';
import { analysisName, isReplaced } from '../core/ux-text';
import { StatePanel } from '../ui/state-panel';
import { FinalWarnings, SimNotice, SupersededBanner, isRunInvalid } from '../ui/notices';
import { PageHeader } from '../ui/page-header';
import { AnalysisBar } from '../ui/analysis-bar';
import { EvalConclusion } from '../ui/eval-conclusion';
import { FinalEvaluation } from './final-evaluation';
import { NOT_EVALUABLE, biasText, compareSentence, errorText, readingSentence, simConclusion } from './eval-text';

const EVAL_START = '2026-06-01';
const EVAL_END = '2026-07-31';
/** Método experimental comparado según el nivel (por producto: RF distribuido; por categoría: RF por categoría). */
const EXP_BY_LEVEL: Record<string, string> = { sku: 'rf_distribuido', categoria: 'rf_categoria' };

interface KeyRow { id: string; label: string; role: string; n: string; error: string; bias: string; coverage: string }

/** Suma días a una fecha AAAA-MM-DD (UTC, sin zona horaria local). */
function addDays(iso: string, n: number): string {
  const [y, m, d] = iso.split('-').map(Number);
  return new Date(Date.UTC(y, m - 1, d + n)).toISOString().slice(0, 10);
}

@Component({
  selector: 'app-comparison-page',
  imports: [StatePanel, SimNotice, SupersededBanner, RouterLink, FinalEvaluation, FinalWarnings, PageHeader, AnalysisBar, EvalConclusion],
  template: `
    <app-page-header title="Evaluación de resultados" lead="¿Qué tan cerca estuvieron las estimaciones de las ventas registradas?" />
    <app-analysis-bar [runId]="barRun()" />
    @if (showSuperseded()) { <app-superseded-banner [run]="run()" /> }

    <app-state-panel [state]="list.state()" [emptyText]="emptyText()" (retry)="list.reload()">
      @if (items().length > 1) {
        <label>Comparación que quieres ver
          <select data-testid="bt-select" aria-label="Comparación que quieres ver" (change)="pick($any($event.target).value)">
            @for (b of items(); track b.backtest_id) {
              <option [value]="b.backtest_id" [selected]="b.backtest_id === chosen()">{{ itemName(b) }}</option>
            }
          </select>
        </label>
      } @else if (items()[0]; as b) {
        <p class="muted" data-testid="bt-label">Comparación mostrada: {{ itemName(b) }}</p>
      }
    </app-state-panel>

    @if (list.state().kind === 'empty') {
      <section class="notice info" data-testid="no-backtest" aria-label="Sin comparación para este análisis">
        @if (choice.id()) {
          @if (generatedChoice()) {
            <p><strong>Este análisis se creó en la aplicación y todavía no tiene una comparación con ventas registradas.</strong> No hay ventas posteriores a la fecha utilizada que permitan medir el error.</p>
          } @else {
            <p><strong>Este análisis no tiene una comparación con ventas registradas.</strong></p>
          }
        } @else {
          <p><strong>Todavía no hay una comparación con ventas registradas publicada.</strong></p>
        }
        <p class="toolbar-links">
          <a class="btn secondary" [routerLink]="['/corridas']" [queryParams]="choice.id() ? { run: choice.id() } : {}" data-testid="to-analyses">Ir a «Mis análisis»</a>
          @if (histRun(); as h) { <a class="btn secondary" [routerLink]="['/comparacion']" [queryParams]="{ run: h }" data-testid="hist-link">Ver el análisis que sí tiene comparación</a> }
        </p>
      </section>
    }

    @if (chosen()) {
      <app-state-panel [state]="detail.state()" emptyText="La comparación no publicó resultados. Vuelve a «Mis análisis» y elige otro análisis." (retry)="detail.reload()">
        @if (det(); as d) {
          <nav class="seg" aria-label="Ir a una sección de la evaluación">
            <button type="button" (click)="jump('sec-estimaciones')" data-testid="jump-est">Estimaciones frente a ventas registradas</button>
            <button type="button" (click)="jump('sec-reposicion')" data-testid="jump-rep">Comparación de reposición simulada</button>
          </nav>

          @if (final()) {
            <app-final-warnings [warnings]="run()?.warnings" />
            @if (d.disclaimer) { <p class="notice warn" data-testid="disclaimer">{{ d.disclaimer }}</p> }
            <app-final-evaluation [d]="d" />
          } @else {
          <section id="sec-estimaciones" aria-labelledby="h-est" data-testid="sec-estimaciones">
            <h2 id="h-est">Estimaciones frente a ventas registradas</h2>
            <p>Resultados históricos de desarrollo, calculados sobre meses ya conocidos (junio y julio de 2026). Este ejemplo no incluye agosto: agosto se evalúa aparte.</p>
            <dl class="periods" data-testid="periods">
              <dt>Ventas utilizadas hasta</dt><dd data-testid="p-origin">{{ originText() }}</dd>
              <dt>Período estimado</dt><dd data-testid="p-target">{{ targetText() }}</dd>
              <dt>Período de evaluación de la comparación y de la simulación</dt><dd data-testid="p-eval">{{ evalText }}</dd>
            </dl>
            <p class="muted" data-testid="periods-note">«Ventas utilizadas hasta» es el último día con historia usada para estimar; no es el fin de la evaluación. Las estimaciones cubren el período estimado y la simulación de reposición recorre todo el período de evaluación.</p>

            @if (keyRows().length) {
              <app-eval-conclusion testid="est-conclusion" [scope]="scopeText()" [lines]="estLines()" />
              <div class="table-wrap" tabindex="0" role="region" aria-label="Error del método elegido y del modelo experimental (desplázate para ver todas las columnas)">
                <table data-testid="key-table">
                  <caption>Cifras clave del alcance elegido</caption>
                  <thead><tr>
                    <th scope="col">Método</th><th scope="col" class="num">Productos o categorías evaluados (n)</th>
                    <th scope="col" class="num">Error absoluto (% del volumen observado)</th>
                    <th scope="col" class="num">Sesgo (% del volumen observado; negativo = se estimó de menos)</th>
                    <th scope="col" class="num">Cobertura</th>
                  </tr></thead>
                  <tbody>
                    @for (k of keyRows(); track k.id) {
                      <tr [attr.data-testid]="'key-' + k.id">
                        <th scope="row">{{ k.label }}<br /><span class="badge">{{ k.role }}</span></th>
                        <td class="num">{{ k.n }}</td><td class="num" data-testid="key-error">{{ k.error }}</td>
                        <td class="num" data-testid="key-bias">{{ k.bias }}</td><td class="num">{{ k.coverage }}</td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            } @else {
              <p class="state" data-testid="est-empty">No hay cifras publicadas para este alcance. Cambia el nivel, el tipo de historial o el período.</p>
            }

            <fieldset class="toolbar selectors" aria-label="Elige qué comparación mostrar">
              <legend>Qué quieres ver</legend>
              <div class="filters">
                <label for="p-level">Nivel
                  <select id="p-level" data-testid="pred-level" (change)="level.set($any($event.target).value)">
                    <option value="sku" [selected]="level() === 'sku'">Producto (código del producto)</option>
                    <option value="categoria" [selected]="level() === 'categoria'">Categoría</option>
                  </select>
                </label>
                <label for="p-coh">Tipo de historial
                  <select id="p-coh" data-testid="pred-coh" (change)="predCoh.set($any($event.target).value)">
                    @for (c of predCohortes; track c.id) { <option [value]="c.id" [selected]="c.id === predCoh()">{{ c.label }}</option> }
                  </select>
                </label>
                <label for="p-vista">Período estimado
                  <select id="p-vista" data-testid="pred-vista" (change)="userVista.set($any($event.target).value)">
                    @for (v of vistas; track v.id) { <option [value]="v.id" [selected]="v.id === vista()">{{ v.label }}</option> }
                  </select>
                </label>
                <label for="p-fold">Bloque de evaluación
                  <select id="p-fold" data-testid="pred-fold" (change)="fold.set($any($event.target).value)">
                    @for (f of folds(); track f) { <option [value]="f" [selected]="f === fold()">{{ f === agregado ? 'Agregado (G1 a G4)' : f }}</option> }
                  </select>
                </label>
              </div>
            </fieldset>

            <section class="notice info" data-testid="limits" aria-labelledby="h-leer">
              <h3 id="h-leer">Cómo leer estos resultados</h3>
              <ul class="plain">
                <li>El método elegido es el <strong>promedio de los últimos 28 días</strong>. El <strong>modelo experimental</strong> (bosque aleatorio) se compara con él, pero no se usa para decidir.</li>
                <li>Los 4 bloques de evaluación (G1 a G4) se solapan: el agregado no es una evaluación independiente ni permite pruebas de significación.</li>
                <li>La venta observada puede estar limitada por falta de stock: los faltantes reales son desconocidos.</li>
                <li>Se muestran todos los resultados, también los desfavorables y el control «cero»; los selectores solo cambian qué parte se ve.</li>
              </ul>
            </section>

            <details class="help" data-testid="detail-pred">
              <summary>Ver detalle completo: todos los métodos y métricas</summary>
              @if (pred().length) {
                <div class="table-wrap" tabindex="0" role="region" aria-label="Tabla de métricas por método (desplázate para ver todas las columnas)">
                  <table data-testid="pred-table">
                    <caption>{{ level() === 'sku' ? 'Producto (SKU)' : 'Categoría' }} · {{ predCohLabel() }} · {{ vistaLabel() }} · {{ fold() === agregado ? 'agregado de 4 bloques solapados' : fold() }}</caption>
                    <thead>
                      <tr>
                        <th scope="col">Método</th><th scope="col" class="num">n</th>
                        <th scope="col" class="num">Unidades observadas</th><th scope="col" class="num">Unidades predichas</th>
                        <th scope="col" class="num">WAPE (%)</th><th scope="col" class="num">MAE</th><th scope="col" class="num">RMSE</th>
                        <th scope="col" class="num">Sesgo (unidades)</th><th scope="col" class="num">Subpronóstico</th><th scope="col" class="num">Sobrepronóstico</th>
                        <th scope="col" class="num">MAPE (reales &gt; 0)</th><th scope="col" class="num">R²</th><th scope="col" class="num">Cobertura</th>
                      </tr>
                    </thead>
                    <tbody>
                      @for (r of pred(); track r.metodo) {
                        <tr [attr.data-testid]="'pred-row-' + r.metodo" [class.hl]="r.metodo === base">
                          <th scope="row">{{ methodLabel(r.metodo) }}<br /><span class="badge">{{ methodRole(r.metodo) }}</span></th>
                          <td class="num">{{ int(r.n) }}</td>
                          @if (r.n > 0 && r.WAPE !== undefined) {
                            <td class="num">{{ int(r.unidades_observadas) }}</td>
                            <td class="num">{{ int(r.unidades_predichas) }}</td>
                            <td class="num" data-testid="wape">{{ r.WAPE === null ? noEval : pct(r.WAPE) }}</td>
                            <td class="num">{{ dec(r.MAE, 2) }}</td>
                            <td class="num">{{ dec(r.RMSE, 2) }}</td>
                            <td class="num">{{ signedInt(r.sesgo_acumulado) }}</td>
                            <td class="num">{{ pct(r.prop_subpronostico) }}</td>
                            <td class="num">{{ pct(r.prop_sobrepronostico) }}</td>
                            <td class="num" data-testid="mape">
                              @if (r.MAPE === null || r.MAPE === undefined) { no evaluable } @else {
                                {{ pct(r.MAPE) }}<br />
                                <small>cobertura {{ pct(r.MAPE_cobertura_reales_positivos) }} de los casos; {{ int(r.MAPE_ceros_excluidos) }} ceros excluidos</small>
                              }
                            </td>
                            <td class="num" data-testid="r2">
                              @if (r.R2 === null || r.R2 === undefined) { no evaluable @if (r.R2_nota) { <br /><small>{{ r.R2_nota }}</small> } } @else { {{ dec(r.R2, 3) }} }
                            </td>
                            <td class="num">{{ coverage(r) }}</td>
                          } @else {
                            <td colspan="11" data-testid="pred-n0">Sin datos evaluables en este corte (n = 0).</td>
                          }
                        </tr>
                      }
                    </tbody>
                  </table>
                </div>
              } @else {
                <p class="state" data-testid="pred-empty">Datos insuficientes: no hay métricas publicadas para esta combinación.</p>
              }
              <ul class="plain muted" data-testid="pred-legend">
                <li><strong>WAPE = error absoluto total / unidades observadas</strong> (se muestra en %; menor es mejor).</li>
                <li>Sesgo = unidades predichas − observadas (negativo = se pronosticó de menos). Subpronóstico / sobrepronóstico = proporción de casos por debajo / por encima de lo observado.</li>
                <li>MAPE solo se calcula con ventas reales positivas; se indica la cobertura de esos casos y cuántos ceros se excluyeron. El R² se muestra «no evaluable» cuando queda indefinido.</li>
                <li>Cobertura = entidades con predicción / universo común del corte. El agregado suma bloques solapados, no unidades únicas.</li>
                <li>Nombres técnicos: «modelo experimental» = RF (Random Forest) distribuido o por categoría; «tipo de historial» = cohorte; «bloque de evaluación» = fold.</li>
              </ul>
              @if (d.predictive?.nota; as n) { <p class="muted">{{ n }}</p> }
            </details>
          </section>

          <section id="sec-reposicion" aria-labelledby="h-sim" data-testid="sec-reposicion">
            <h2 id="h-sim">Comparación de reposición simulada</h2>
            <app-sim-notice [scenarioId]="scenario()" />
            <p>Cada política de pedidos se aplicó a un inventario simulado entre el 01/06 y el 31/07/2026.
              @if (isPrincipal()) { <span class="badge ok" data-testid="principal-badge">Escenario principal (L{{ L() }} / S{{ S() }})</span> }
              @else { <span class="badge" data-testid="principal-badge">Escenario L{{ L() }} / S{{ S() }}; el principal es L{{ principal().L }} / S{{ principal().S }}</span> }
            </p>
            @if (simLines().length) {
              <app-eval-conclusion testid="sim-conclusion" [scope]="simScope()" [lines]="simLines()" />
            } @else {
              <p class="state" data-testid="sim-empty">Datos insuficientes: no hay simulación publicada para L{{ L() }} / S{{ S() }}.</p>
            }
            <ul class="plain" data-testid="sim-limits">
              <li>Más nivel de servicio viene con más stock y más compras: una mejora en servicio no es una ganancia neta si no se mira su costo.</li>
              <li>La simulación (nueve escenarios × 3 políticas = 27 combinaciones) usa inventario, costos y plazos supuestos; no demuestra una mejora real para la empresa ni autoriza compras.</li>
            </ul>

            <fieldset class="toolbar selectors" aria-label="Elige el escenario de simulación">
              <legend>Escenario simulado</legend>
              <div class="filters">
                <label for="sel-l">Plazo de entrega L (días)
                  <select id="sel-l" data-testid="sel-L" (change)="userL.set(+$any($event.target).value)">
                    @for (x of Ls(); track x) { <option [value]="x" [selected]="x === L()">{{ x }}</option> }
                  </select>
                </label>
                <label for="sel-s">Seguridad S (días)
                  <select id="sel-s" data-testid="sel-S" (change)="userS.set(+$any($event.target).value)">
                    @for (x of Ss(); track x) { <option [value]="x" [selected]="x === S()">{{ x }}</option> }
                  </select>
                </label>
                <label for="sel-c">Tipo de historial
                  <select id="sel-c" data-testid="sel-coh" (change)="simCoh.set($any($event.target).value)">
                    @for (c of cohortes; track c.id) { <option [value]="c.id" [selected]="c.id === simCoh()">{{ c.label }}</option> }
                  </select>
                </label>
              </div>
            </fieldset>

            <details class="help" data-testid="detail-sim">
              <summary>Ver detalle completo: tres políticas, métricas y supuestos</summary>
              @if (sim().some(hasBlock)) {
                <div class="table-wrap" tabindex="0" role="region" aria-label="Tabla de políticas de reposición (desplázate para ver todas las columnas)">
                  <table data-testid="sim-table">
                    <caption>L{{ L() }} / S{{ S() }} · {{ cohLabel(simCoh()) }} · diferencias frente a promedio_28 en la misma cohorte</caption>
                    <thead>
                      <tr>
                        <th scope="col">Política</th>
                        <th scope="col" class="num">Servicio (% de la demanda atendida)</th>
                        <th scope="col" class="num">Faltantes (unidades perdidas)</th>
                        <th scope="col" class="num">Stock medio (unidades/día)</th>
                        <th scope="col" class="num">Compras desembolsadas (PEN, supuesto)</th>
                        <th scope="col" class="num">Dif. servicio</th>
                        <th scope="col" class="num">Dif. faltantes</th>
                        <th scope="col" class="num">Dif. stock medio</th>
                        <th scope="col" class="num">Dif. compras</th>
                      </tr>
                    </thead>
                    <tbody>
                      @for (row of sim(); track row.policy) {
                        <tr [attr.data-testid]="'sim-row-' + row.policy" [class.hl]="row.policy === base">
                          <th scope="row">{{ policyLabel(row.policy) }}<br /><span class="badge">{{ policyRole(row.policy) }}</span></th>
                          @if (row.block; as b) {
                            <td class="num">{{ pct(b['fill_rate']) }}</td>
                            <td class="num">{{ int(b['perdidas_unidades']) }}</td>
                            <td class="num">{{ int(b['stock_medio_unidades_por_dia']) }}</td>
                            <td class="num">{{ pen(b['compras_desembolsadas_supuesto']) }}</td>
                            @if (row.policy === base) {
                              <td class="num muted" colspan="4">base de comparación</td>
                            } @else {
                              <td class="num">{{ diff(row, 'fill_rate') }}</td>
                              <td class="num">{{ diff(row, 'perdidas_unidades') }}</td>
                              <td class="num">{{ diff(row, 'stock_medio_unidades_por_dia') }}</td>
                              <td class="num">{{ diff(row, 'compras_desembolsadas_supuesto') }}</td>
                            }
                          } @else {
                            <td colspan="8">Sin resultados publicados para esta combinación.</td>
                          }
                        </tr>
                      }
                    </tbody>
                  </table>
                </div>
                <p class="muted">
                  Servicio = unidades atendidas / demanda proxy. Las diferencias son «política − promedio_28»: puntos porcentuales para el servicio y
                  unidades o PEN para el resto, con la variación relativa entre paréntesis. Mayor servicio vino con mayor stock y mayores compras.
                  Stock, compras y costos son supuestos del simulador.
                </p>
                <details class="tech" data-testid="sim-all-metrics">
                  <summary>Todas las métricas de esta combinación (L{{ L() }} / S{{ S() }}, {{ cohLabel(simCoh()) }})</summary>
                  <div class="table-wrap" tabindex="0" role="region" aria-label="Todas las métricas de simulación">
                    <table>
                      <thead>
                        <tr><th scope="col">Métrica</th>@for (p of policies; track p.id) { <th scope="col" class="num">{{ p.label }}</th> }</tr>
                      </thead>
                      <tbody>
                        @for (k of metricKeys(); track k) {
                          <tr>
                            <th scope="row">{{ metricLabel(k) }}</th>
                            @for (row of sim(); track row.policy) { <td class="num">{{ metric(row, k) }}</td> }
                          </tr>
                        }
                      </tbody>
                    </table>
                  </div>
                </details>
                <details class="tech" data-testid="sim-tech">
                  <summary>Identificadores y datos técnicos de la simulación</summary>
                  <ul class="plain">
                    @for (row of sim(); track row.policy) { <li>{{ row.policy }}: <code>{{ row.scenario?.scenario_id ?? 'sin dato' }}</code></li> }
                    <li>Comparación: {{ d.label ?? 'sin dato' }} · <code>{{ d.backtest_id ?? 'sin dato' }}</code> · análisis <code>{{ d['run_id'] ?? 'sin dato' }}</code> · procedencia <code>{{ d.provenance ?? 'sin dato' }}</code></li>
                  </ul>
                  <pre>{{ simJson() }}</pre>
                </details>
              } @else {
                <p class="state" data-testid="sim-empty-detail">Datos insuficientes: no hay simulación publicada para L{{ L() }} / S{{ S() }}.</p>
              }
              @if (assumptionList().length) {
                <details class="tech" data-testid="assumptions">
                  <summary>Supuestos y límites de la simulación</summary>
                  <ul class="plain">@for (a of assumptionList(); track a) { <li>{{ a }}</li> }</ul>
                </details>
              }
              @if (d.disclaimer) { <p class="notice warn" data-testid="disclaimer">{{ d.disclaimer }}</p> }
            </details>
          </section>
          }
        }
      </app-state-panel>
    }
  `,
  styles: `
    .selectors select { min-width: 9rem; }
    .selectors legend { font-weight: 600; }
    .periods { display: grid; grid-template-columns: max-content 1fr; gap: 0.2rem 1rem; margin: 0.4rem 0; }
    .periods dt { font-weight: 600; } .periods dd { margin: 0; }
    @media (max-width: 700px) { .periods { grid-template-columns: 1fr; } }
    .toolbar-links { display: flex; flex-wrap: wrap; gap: 0.6rem; }
    .seg { margin: 0.6rem 0; }
    section[id] { scroll-margin-top: 1rem; }
    pre { white-space: pre-wrap; overflow-wrap: anywhere; background: var(--soft); padding: 0.5rem; max-height: 22rem; overflow: auto; font-size: 1rem; }
  `,
})
export class ComparisonPage {
  private api = inject(ApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);
  private runsStore = inject(RunsStore);
  /** Análisis elegido (parámetro de URL «run»); sin él, la comparación publicada por defecto. */
  choice = new RunChoice(this.route, this.router, this.destroyRef, () => { this.chosen.set(null); this.histRun.set(null); this.list.reload(); });
  histRun = signal<string | null>(null);
  readonly evalText = `${fmtDate(EVAL_START)} al ${fmtDate(EVAL_END)}`;
  readonly policies = POLICIES;
  readonly cohortes = COHORTES;
  readonly predCohortes = PRED_COHORTES;
  readonly vistas = VISTAS;
  readonly agregado = AGREGADO;
  readonly base = BASE_POLICY;
  readonly noEval = NOT_EVALUABLE;

  chosen = signal<string | null>(null);
  list = load<BacktestItem[]>(
    () => this.api.backtests(this.choice.id() ?? undefined).pipe(
      map((r) => (Array.isArray(r) ? r : (r as Page<BacktestItem>).items)),
      catchError((e: { status?: number }) => (this.choice.id() && e?.status === 404 ? of([] as BacktestItem[]) : throwError(() => e))),
      tap((items) => { if (!items.length && this.choice.id()) this.findHistorical(); }),
      // Selecciona la primera comparación al llegar la lista (la de desarrollo antes que la evaluación de agosto).
      tap((items) => { if (items.length && !this.chosen()) { this.chosen.set([...items].sort((a, b) => +isFinal(a.kind) - +isFinal(b.kind))[0].backtest_id); queueMicrotask(() => this.detail.reload()); } }),
    ),
    (d) => d.length === 0,
  );
  /** La evaluación de agosto va al final de la lista: por defecto se abre la comparación del ejemplo histórico. */
  items = computed(() => { const s = this.list.state(); return s.kind === 'data' ? [...s.data].sort((a, b) => +isFinal(a.kind) - +isFinal(b.kind)) : []; });
  final = computed(() => isFinal(this.det()?.kind));
  /** Nombre comprensible derivado de los datos del análisis (no escrito para registros concretos). */
  itemName = (b: BacktestItem) => {
    const known = this.runsStore.runs().find((r) => r.run_id === (b.run_id ?? b.run?.run_id));
    if (known) return analysisName(known);
    return analysisName({
      kind: isFinal(b.kind) ? 'final_evaluation' : 'historical_development', cutoff: b.run?.cutoff ?? '', run_label: b.run?.run_label ?? '',
      target_start: b.run?.target_start ?? undefined, target_end: b.run?.target_end ?? undefined, origin: b.run?.cutoff, is_active: !!b.run?.is_active,
    });
  };
  emptyText = computed(() => (this.choice.id() ? 'Este análisis no tiene una comparación con ventas registradas.' : 'Todavía no hay comparaciones publicadas.'));
  generatedChoice = computed(() => isGenerated(this.runsStore.resolve(this.choice.id())?.kind));
  // Siempre se pide la vista completa; los selectores solo filtran lo que se muestra.
  detail = load<BacktestDetail>(() => this.api.backtest(this.chosen()!, 'all'), (d) => Object.keys(d).length === 0, false);
  det = computed(() => { const s = this.detail.state(); return s.kind === 'data' ? s.data : null; });
  scenario = computed(() => this.det()?.scenario_id ?? null);
  run = computed(() => this.det()?.run ?? null);
  /** Análisis que describe la barra: el de la dirección (`run`) o, sin él, el de la comparación abierta. */
  barRun = computed<string | null>(() => this.choice.id() ?? this.det()?.run?.run_id ?? this.det()?.run_id ?? null);
  showSuperseded = computed(() => isRunInvalid(this.run()) && !isReplaced(this.runsStore.resolve(this.barRun())));
  /** Origen: corte de la corrida (valor publicado). */
  origin = computed(() => this.run()?.cutoff ?? null);
  originText = computed(() => (this.origin() ? fmtDate(this.origin()) : 'sin dato'));
  /** Período estimado: el publicado por el análisis; si falta, origen + 1 a origen + 21 (horizonte fijo de 21 días). */
  targetText = computed(() => {
    const r = this.run() as { target_start?: string; target_end?: string } | null;
    const o = this.origin();
    const a = r?.target_start ?? (o ? addDays(o, 1) : null);
    const b = r?.target_end ?? (o ? addDays(o, 21) : null);
    return a && b ? `${fmtDate(a)} al ${fmtDate(b)}` : 'sin dato';
  });
  private findHistorical() {
    this.api.backtests().subscribe({
      next: (r) => {
        const items = Array.isArray(r) ? r : (r as Page<BacktestItem>).items;
        const id = items[0]?.run_id ?? items[0]?.run?.run_id ?? null;
        this.histRun.set(id && id !== this.choice.id() ? id : null);
      },
      error: () => this.histRun.set(null),
    });
  }

  // Simulación: escenario principal por defecto (L7/S7 según los supuestos publicados).
  userL = signal<number | null>(null);
  userS = signal<number | null>(null);
  simCoh = signal<Cohorte>('total');
  principal = computed(() => this.det()?.assumptions?.escenario_principal ?? { L: 7, S: 7 });
  L = computed(() => this.userL() ?? this.principal().L);
  S = computed(() => this.userS() ?? this.principal().S);
  Ls = computed(() => this.det()?.assumptions?.L ?? [3, 7, 14]);
  Ss = computed(() => this.det()?.assumptions?.S ?? [0, 7, 14]);
  isPrincipal = computed(() => this.L() === this.principal().L && this.S() === this.principal().S);
  sim = computed<SimRow[]>(() => simRows(this.det(), this.L(), this.S(), this.simCoh()));
  metricKeys = computed(() => {
    const first = this.sim().find((r) => r.block)?.block;
    return first ? Object.keys(first) : [];
  });
  simJson = computed(() => JSON.stringify(this.sim().map((r) => ({ policy: r.policy, [this.simCoh()]: r.block, diferencias_vs_promedio_28: r.diff?.metrics ?? null })), null, 1));
  /** Conclusión de la simulación: modelo experimental frente al promedio de 28 días en el escenario y tipo de historial elegidos. */
  simLines = computed(() => {
    const rows = this.sim();
    const base = rows.find((r) => r.policy === BASE_POLICY);
    const exp = rows.find((r) => r.policy === POLICIES[2].id);
    return simConclusion(base?.block ?? null, exp?.block ?? null, exp?.diff?.metrics);
  });
  simScope = computed(() => `Alcance: plazo de entrega L${this.L()} días, seguridad S${this.S()} días · ${this.cohLabel(this.simCoh())} · inventario simulado del ${fmtDate(EVAL_START)} al ${fmtDate(EVAL_END)}.`);
  assumptionList = computed(() => {
    const a = this.det()?.assumptions;
    if (!a) return [];
    const out: string[] = [];
    if (a['factor_costo_sobre_mediana_precio'] !== undefined) out.push(`Costo unitario supuesto = ${fmtPct(a['factor_costo_sobre_mediana_precio'])} de la mediana de precio base.`);
    if (a['holding_anual'] !== undefined) out.push(`Costo anual de mantener stock supuesto: ${fmtPct(a['holding_anual'])}.`);
    if (a.R !== undefined) out.push(`Revisión de pedidos cada ${a.R} días.`);
    if (typeof a.demanda === 'string') out.push(`Demanda: ${a.demanda}.`);
    return [...out, ...(a.limites ?? [])];
  });
  selectionText = computed(() => {
    const s = this.det()?.selection;
    if (!s) return '';
    const parts: string[] = [];
    if (s.cumple_regla === false) parts.push('la regla provisional de selección no se cumplió');
    if (typeof s.mejora_relativa === 'number') parts.push(`mejora relativa publicada: ${fmtPct(s.mejora_relativa, true)}`);
    return parts.join('; ');
  });

  // Estimaciones frente a ventas registradas
  level = signal<'sku' | 'categoria'>('sku');
  predCoh = signal<string>('primaria');
  userVista = signal<string | null>(null);
  vista = computed(() => this.userVista() ?? (this.det()?.selection?.vista as string | undefined) ?? 'acum14');
  fold = signal<string>(AGREGADO);
  folds = computed(() => foldsOf(this.det()));
  pred = computed<PredRow[]>(() => predRows(this.det(), this.level(), this.predCoh(), this.vista(), this.fold()));
  private baseRow = computed(() => this.pred().find((r) => r.metodo === BASE_POLICY) ?? null);
  private expRow = computed(() => this.pred().find((r) => r.metodo === EXP_BY_LEVEL[this.level()]) ?? null);
  /** Error del método elegido y del modelo experimental para el alcance elegido (null = no evaluable). */
  private wapeOf = (r: PredRow | null): number | null => (r && r.n > 0 && typeof r.WAPE === 'number' ? r.WAPE : null);
  keyRows = computed<KeyRow[]>(() => [this.baseRow(), this.expRow()].filter((r): r is PredRow => r !== null).map((r) => ({
    id: r.metodo,
    label: r.metodo === BASE_POLICY ? 'Promedio de los últimos 28 días' : 'Modelo experimental',
    role: r.metodo === BASE_POLICY ? 'método elegido' : 'comparador; no se usa para decidir',
    n: this.int(r.n),
    error: r.n > 0 ? errorText(r.WAPE) : 'sin datos evaluables',
    bias: r.n > 0 ? biasText(r.sesgo_acumulado, r.unidades_observadas) : 'sin datos evaluables',
    coverage: this.coverage(r),
  })));
  scopeText = computed(() => {
    const nivel = this.level() === 'sku' ? 'por producto (código del producto)' : 'por categoría (suma de unidades de productos distintos)';
    const bloque = this.fold() === AGREGADO ? 'promedio de 4 bloques solapados (G1 a G4)' : `bloque ${this.fold()}`;
    return `Alcance: ${nivel} · ${this.predCohLabel()} · ${this.vistaLabel()} · ${bloque} · ventas registradas del ${this.evalText}.`;
  });
  estLines = computed(() => {
    const wb = this.wapeOf(this.baseRow()); const we = this.wapeOf(this.expRow());
    const lines = [
      `Error del promedio de los últimos 28 días (método elegido): ${errorText(wb)}. Error del modelo experimental: ${errorText(we)}.`,
      readingSentence(wb),
      compareSentence(wb, we),
    ];
    const sel = this.selectionText();
    const notMet = this.det()?.selection?.cumple_regla === false;
    lines.push(`${notMet ? 'El modelo experimental no ganó' : 'No hay un ganador experimental'}${sel ? ` (${sel})` : ''}. No se declaró ganador experimental; el método operativo no cambia por este resultado.`);
    return lines;
  });

  // Formato
  int = (v: unknown) => fmtInt(v);
  signedInt = (v: unknown) => fmtInt(v, true);
  dec = (v: unknown, n = 3) => fmtDec(v, n);
  pct = (v: unknown) => fmtPct(v);
  pen = (v: unknown) => fmtPen(v);
  hasBlock = (r: SimRow) => r.block !== null;
  cohLabel = (id: string) => COHORTES.find((c) => c.id === id)?.label ?? id;
  predCohLabel = () => this.cohLabel(this.predCoh());
  vistaLabel = () => VISTAS.find((v) => v.id === this.vista())?.label ?? this.vista();
  policyLabel = (id: string) => POLICIES.find((p) => p.id === id)?.label ?? id;
  policyRole = (id: string) => POLICIES.find((p) => p.id === id)?.role ?? '';
  methodLabel = (id: string) => METHOD_INFO[id]?.label ?? id;
  methodRole = (id: string) => METHOD_INFO[id]?.role ?? '';
  metricLabel = (k: string) => SIM_LABELS[k] ?? k;

  metric(row: SimRow, k: string): string {
    const v = row.block?.[k];
    switch (kindOf(k)) {
      case 'pct': return fmtPct(v);
      case 'pen': return fmtPen(v);
      default: return fmtInt(v);
    }
  }

  /** Diferencia frente a promedio_28: valor absoluto con formato de la métrica y variación relativa entre paréntesis. */
  diff(row: SimRow, k: string): string {
    const m = row.diff?.metrics?.[k];
    if (!m || m.abs === null || m.abs === undefined) return DASH;
    const abs = kindOf(k) === 'pct' ? fmtPp(m.abs) : kindOf(k) === 'pen' ? fmtPen(m.abs, true) : fmtInt(m.abs, true);
    return m.rel === null || m.rel === undefined ? abs : `${abs} (${fmtPct(m.rel, true)})`;
  }

  coverage(r: PredRow): string {
    const c = coverageOf(this.det(), this.level(), this.predCoh(), this.fold(), r.metodo);
    if (!c || c.universo === 0) return DASH;
    return `${fmtInt(c.conPrediccion)} de ${fmtInt(c.universo)} (${fmtPct(c.conPrediccion / c.universo)})`;
  }

  pick(id: string) { this.chosen.set(id); this.detail.reload(); }

  /** Lleva la vista a una sección (botones de «Ir a»); no cambia la dirección ni el análisis elegido. */
  jump(id: string) { document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
}
