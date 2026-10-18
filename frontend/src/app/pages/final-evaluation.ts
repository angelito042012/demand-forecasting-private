import { Component, computed, input, signal } from '@angular/core';
import { BacktestDetail, Cohorte, PredRow, SimBlock } from '../core/models';
import { COHORTES, POLICIES, PRED_COHORTES, SIM_LABELS, coverageOf, kindOf } from '../core/backtest';
import {
  FINAL_BASE, FINAL_METHOD_INFO, FINAL_VISTAS, blockOf, diffOf, finalCoverageRows, finalRows, newSkus, primaryFinding,
  scalarsOf, scenarioOf, serviceVsInventory, universe,
} from '../core/final-eval';
import { DASH, fmtDate, fmtDec, fmtInt, fmtPct, fmtPen, fmtPp } from '../core/format';
import { FinalWarnings, SimNotice } from '../ui/notices';
import { EvalConclusion } from '../ui/eval-conclusion';
import { EvalSummary } from '../ui/eval-summary';
import { EvalTab, EvalTabs } from '../ui/eval-tabs';
import { NOT_EVALUABLE, WINDOW_NOTE, compareSentence, errorText, mainExplanation, metricPeriods, simConclusion, simpleScope } from './eval-text';

const NE = NOT_EVALUABLE;
/** Pares «política − comparación» publicados en la simulación del escenario elegido. */
const PAIRS: { policy: string; vs: string }[] = [
  { policy: 'referencia_fija', vs: 'promedio_28' },
  { policy: 'promedio_28', vs: 'referencia_fija' },
  { policy: 'rf_categoria_distribuido', vs: 'referencia_fija' },
  { policy: 'rf_categoria_distribuido', vs: 'promedio_28' },
];

/**
 * Vista «Evaluación de agosto» (T12): bloque único 01–21/08/2026 con origen 31/07/2026 y simulación secuencial de agosto.
 * Separada del ejemplo de julio (T07). Solo muestra lo que publica el documento del backtest `final_evaluation`.
 * UX01: cada sección empieza con una conclusión calculada de los datos; el detalle académico completo va plegado.
 */
@Component({
  selector: 'app-final-evaluation',
  imports: [SimNotice, EvalConclusion, EvalSummary, EvalTabs, FinalWarnings],
  template: `
    <div data-testid="final-view">
      <app-eval-tabs [tabs]="tabs" [(active)]="tab" label="Secciones de la evaluación de agosto" />

      <div role="tabpanel" id="panel-est" aria-labelledby="tab-est" tabindex="0" [hidden]="tab() !== 'est'" data-testid="panel-est">
      <section id="sec-estimaciones" aria-labelledby="h-est" data-testid="final-est">
        <h2 id="h-est">Estimaciones frente a ventas registradas</h2>
        <app-eval-summary [context]="contextText()" [scope]="simple()" [explanation]="explanation()" [periods]="periodItems()"
          [notice]="briefNotice" (openDetail)="openDetail()" />

        <details class="academic" id="academic-detail" data-testid="academic-detail" [open]="acOpen()" (toggle)="acOpen.set($any($event.target).open)">
          <summary id="academic-summary">Ver cómo se evaluó: detalle académico</summary>
          <app-final-warnings [warnings]="d().run?.warnings" />
          <app-eval-conclusion heading="Lectura de las cifras del hallazgo primario" testid="est-conclusion" [scope]="scopeText()" [lines]="estLines()" />
          <div data-testid="final-detail-est">

        <section aria-labelledby="h-prim" data-testid="final-primary">
          <h3 id="h-prim">Hallazgo primario</h3>
          <p>WAPE acumulado a 14 días, SKU-almacén (producto en un almacén), tipo de historial «primaria», universo común
            (n = <strong data-testid="primary-n">{{ int(pf().n) }}</strong>).</p>
          <div class="table-wrap" tabindex="0" role="region" aria-label="Hallazgo primario">
            <table data-testid="primary-table">
              <thead><tr><th scope="col">Método</th><th scope="col" class="num">Error absoluto (WAPE H14)</th><th scope="col" class="num">Sesgo / observado</th></tr></thead>
              <tbody>
                <tr data-testid="primary-promedio"><th scope="row">Promedio de 28 días <span class="badge">método operativo</span></th><td class="num">{{ err(pf().wape.promedio_28) }}</td><td class="num">{{ spct(pf().sesgoObs.promedio_28) }}</td></tr>
                <tr data-testid="primary-rf"><th scope="row">Modelo experimental (RF distribuido) <span class="badge">comparador</span></th><td class="num">{{ err(pf().wape.rf) }}</td><td class="num">{{ spct(pf().sesgoObs.rf) }}</td></tr>
                <tr data-testid="primary-cero"><th scope="row">Control cero <span class="badge">control</span></th><td class="num">{{ err(pf().wape.cero) }}</td><td class="num">{{ DASH }}</td></tr>
              </tbody>
            </table>
          </div>
          <ul class="plain">
            <li data-testid="primary-mejora">Mejora relativa del modelo experimental frente al promedio de 28 días: <strong>{{ spct(pf().mejora) }}</strong> (positiva = menor error que el promedio; negativa = peor que el promedio).</li>
            <li data-testid="primary-sesgo">Sesgo relativo publicado en la selección: <strong>{{ spct(pf().sesgoRelPublicado) }}</strong>.</li>
            <li data-testid="primary-winner">RF declarado ganador: <strong>{{ pf().rfDeclaredWinner === false ? 'no' : pf().rfDeclaredWinner === true ? 'sí (valor publicado)' : 'sin dato' }}</strong>. Con un solo bloque no hay inferencia de ganador; el método operativo no cambia por este resultado.</li>
            @if (pf().criterion; as c) { <li>Criterio primario: {{ c }}</li> }
            @if (pf().note; as n) { <li>{{ n }}</li> }
          </ul>
        </section>

          <section aria-labelledby="h-coh">
            <h3 id="h-coh">Resumen por tipo de historial (SKU-almacén, acumulado 14 días)</h3>
            <div class="table-wrap" tabindex="0" role="region" aria-label="Resumen por tipo de historial">
              <table data-testid="cohort-summary">
                <thead><tr><th scope="col">Tipo de historial</th><th scope="col">Método</th><th scope="col" class="num">n</th><th scope="col" class="num">WAPE</th></tr></thead>
                <tbody>
                  @for (c of cohorts; track c.id) {
                    @for (r of rows('sku', c.id, 'acum14'); track r.metodo) {
                      <tr [attr.data-testid]="'cs-' + c.id + '-' + r.metodo"><td>{{ c.label }}</td><td>{{ mlabel(r.metodo) }}</td><td class="num">{{ int(r.n) }}</td><td class="num">{{ wape(r) }}</td></tr>
                    } @empty { <tr><td>{{ c.label }}</td><td colspan="3">Sin filas publicadas.</td></tr> }
                  }
                </tbody>
              </table>
            </div>
            <p class="muted">El tipo «historia_corta» agrupa SKU con poca historia al 31/07; sus resultados no se mezclan con los del tipo primaria.</p>
          </section>

          <section aria-labelledby="h-pt">
            <h3 id="h-pt">Precisión por horizonte</h3>
            <fieldset class="toolbar selectors" aria-label="Selección de resultados de la evaluación de agosto">
              <legend>Resultados a mostrar</legend>
              <div class="filters">
                <label for="f-level">Nivel
                  <select id="f-level" data-testid="final-level" (change)="level.set($any($event.target).value)">
                    <option value="sku" [selected]="level() === 'sku'">SKU-almacén</option>
                    <option value="categoria" [selected]="level() === 'categoria'">Categoría (suma de pronósticos SKU)</option>
                  </select>
                </label>
                <label for="f-coh">Tipo de historial
                  <select id="f-coh" data-testid="final-coh" (change)="coh.set($any($event.target).value)">
                    @for (c of cohorts; track c.id) { <option [value]="c.id" [selected]="c.id === coh()">{{ c.label }}</option> }
                  </select>
                </label>
              </div>
            </fieldset>
            @if (level() === 'categoria') {
              <p class="notice warn" data-testid="cat-note">Categoría = suma de unidades base heterogéneas: la cifra de una categoría mezcla productos con unidades distintas y solo sirve para comparar métodos entre sí.</p>
            }
            @for (v of vistas; track v.id) {
              @let rs = rows(level(), coh(), v.id);
              @if (rs.length) {
                <div class="table-wrap" tabindex="0" role="region" [attr.aria-label]="'Métricas ' + v.label + ' (desplázate para ver todas las columnas)'">
                  <table [attr.data-testid]="'final-table-' + v.id">
                    <caption>{{ level() === 'sku' ? 'SKU-almacén' : 'Categoría' }} · {{ clabel(coh()) }} · {{ v.label }}</caption>
                    <thead>
                      <tr>
                        <th scope="col">Método</th><th scope="col" class="num">n</th><th scope="col" class="num">Unidades observadas</th><th scope="col" class="num">Unidades predichas</th>
                        <th scope="col" class="num">WAPE (%)</th><th scope="col" class="num">MAE</th><th scope="col" class="num">RMSE</th>
                        <th scope="col" class="num">Sesgo (unidades)</th><th scope="col" class="num">Sub / sobre</th>
                        <th scope="col" class="num">MAPE (reales &gt; 0)</th><th scope="col" class="num">R²</th><th scope="col" class="num">Cobertura</th>
                      </tr>
                    </thead>
                    <tbody>
                      @for (r of rs; track r.metodo) {
                        <tr [attr.data-testid]="'frow-' + v.id + '-' + r.metodo">
                          <th scope="row">{{ mlabel(r.metodo) }}<br /><span class="badge">{{ mrole(r.metodo) }}</span></th>
                          <td class="num">{{ int(r.n) }}</td>
                          @if (r.n > 0) {
                            <td class="num">{{ int(r.unidades_observadas) }}</td><td class="num">{{ int(r.unidades_predichas) }}</td>
                            <td class="num" data-testid="wape">{{ wape(r) }}</td>
                            <td class="num">{{ dec(r.MAE, 2) }}</td><td class="num">{{ dec(r.RMSE, 2) }}</td>
                            <td class="num">{{ sint(r.sesgo_acumulado) }}</td>
                            <td class="num">{{ pct(r.prop_subpronostico) }} / {{ pct(r.prop_sobrepronostico) }}</td>
                            <td class="num" data-testid="mape">@if (r.MAPE === null || r.MAPE === undefined) { {{ ne }} } @else { {{ pct(r.MAPE) }}<br /><small>cobertura {{ pct(r.MAPE_cobertura_reales_positivos) }}</small> }</td>
                            <td class="num" data-testid="r2">@if (r.R2 === null || r.R2 === undefined) { {{ ne }} } @else { {{ dec(r.R2, 3) }} }</td>
                            <td class="num">{{ cover(r) }}</td>
                          } @else { <td colspan="10" data-testid="f-n0">Sin datos evaluables en este corte (n = 0).</td> }
                        </tr>
                      }
                    </tbody>
                  </table>
                </div>
              } @else { <p class="state" [attr.data-testid]="'final-empty-' + v.id">Datos insuficientes: no hay métricas publicadas para {{ v.label }}.</p> }
            }
            <ul class="plain muted" data-testid="final-legend">
              <li><strong>WAPE no es exactitud</strong>: 0,78 significa error absoluto agregado equivalente al 78 % del volumen observado (menor es mejor). Puede superar 100 %.</li>
              <li>Sesgo = predicho − observado (negativo = se pronosticó de menos). «{{ ne }}» aparece cuando el cociente queda indefinido (por ejemplo, sin unidades observadas); no se reemplaza por cero.</li>
              <li>MAPE solo con ventas reales positivas y su cobertura; el R² se muestra «{{ ne }}» cuando queda indefinido.</li>
            </ul>
          </section>

          <section aria-labelledby="h-cov" data-testid="final-coverage">
            <h3 id="h-cov">Cobertura y SKU nuevos</h3>
            <ul class="plain">
              @for (c of covRows(); track c.cohorte + c.entidades) {
                <li data-testid="cov-row">SKU-almacén, {{ clabel(c.cohorte) }}: universo común <strong>{{ int(c.comunes ?? c.entidades) }}</strong> de {{ int(c.entidades) }} entidades · días evaluables del bloque: {{ int(c.dias_evaluables_21) }} de 21.</li>
              } @empty { <li>Sin cobertura SKU publicada.</li> }
              @for (c of covCat(); track c.cohorte + c.entidades) {
                <li data-testid="cov-row-cat">Categoría, {{ clabel(c.cohorte) }}: {{ int(c.comunes ?? c.entidades) }} de {{ int(c.entidades) }} categorías.</li>
              }
            </ul>
            @if (uni(); as u) {
              <ul class="plain" data-testid="final-universe">@for (kv of scalars(u); track kv[0]) { <li>{{ kv[0] }}: <strong>{{ kv[1] }}</strong></li> }</ul>
            }
            @if (nuevos(); as n) {
              <p data-testid="final-new-skus">SKU nuevos con venta en el bloque (primera venta posterior al 31/07), informados aparte y sin historia ni categoría inventadas:</p>
              <ul class="plain">@for (kv of scalars(n); track kv[0]) { <li>{{ kv[0] }}: <strong>{{ kv[1] }}</strong></li> }</ul>
            } @else { <p class="muted" data-testid="final-new-skus-missing">La API no publicó el resumen de SKU nuevos para esta evaluación.</p> }
          </section>

          <section aria-labelledby="h-met" data-testid="final-methods">
            <h3 id="h-met">Cómo se calcularon los métodos</h3>
            <ul class="plain">
              <li><strong>Promedio de 28 días</strong> (método operativo). {{ windowNote }}</li>
              <li><strong>Modelo experimental</strong> (RF distribuido por producto; RF por categoría en el nivel categoría): comparador; no se usa para decidir.</li>
              <li><strong>Control cero</strong>: estima cero unidades cada día; sirve solo como referencia.</li>
              <li>El pronóstico es un bloque fijo de 21 días desde el origen. Las métricas acumuladas (10, 14 y 21 días) y la diaria se calculan sobre los primeros días de ese bloque; no son bloques distintos.</li>
            </ul>
          </section>
          </div>
        </details>
      </section>
      </div>

      <div role="tabpanel" id="panel-rep" aria-labelledby="tab-rep" tabindex="0" [hidden]="tab() !== 'rep'" data-testid="panel-rep">
      <section id="sec-reposicion" aria-labelledby="h-fsim" data-testid="final-sim">
        <h2 id="h-fsim">Comparación de reposición simulada</h2>
        <app-sim-notice [scenarioId]="d().scenario_id ?? null" />
        <p class="notice warn" data-testid="final-sim-label">La demanda es la venta observada (proxy), posiblemente limitada por stock; existencias, costos, plazos y seguridad son supuestos. Más servicio puede ir con más stock y más compras: no es mejora neta ni impacto real, y no autoriza compras.</p>
        @if (simLines().length) {
          <app-eval-conclusion testid="sim-conclusion" [scope]="simScope()" [lines]="simLines()" />
        } @else { <p class="state" data-testid="final-sim-empty">Datos insuficientes: no hay simulación publicada para el escenario principal.</p> }

        <details class="help" data-testid="final-sim-detail">
          <summary>Ver detalle completo: escenario principal, diferencias y las 27 combinaciones</summary>
          <fieldset class="toolbar selectors" aria-label="Tipo de historial de la simulación">
            <legend>Escenario principal (L{{ pL() }} / S{{ pS() }})</legend>
            <div class="filters">
              <label for="fs-coh">Tipo de historial inicial
                <select id="fs-coh" data-testid="final-sim-coh" (change)="simCoh.set($any($event.target).value)">
                  @for (c of allCohorts; track c.id) { <option [value]="c.id" [selected]="c.id === simCoh()">{{ c.label }}</option> }
                </select>
              </label>
            </div>
          </fieldset>
          @if (main().some(hasBlock)) {
            <div class="table-wrap" tabindex="0" role="region" aria-label="Escenario principal (desplázate para ver todas las columnas)">
              <table data-testid="final-sim-main">
                <caption>L{{ pL() }} / S{{ pS() }} · {{ clabel(simCoh()) }}</caption>
                <thead><tr><th scope="col">Política</th><th scope="col" class="num">Servicio (fill rate)</th><th scope="col" class="num">Unidades perdidas</th><th scope="col" class="num">Stock medio (unid./día)</th><th scope="col" class="num">Stock final</th><th scope="col" class="num">Compras desembolsadas (PEN, supuesto)</th></tr></thead>
                <tbody>
                  @for (row of main(); track row.policy) {
                    <tr [attr.data-testid]="'fmain-' + row.policy">
                      <th scope="row">{{ plabel(row.policy) }}</th>
                      @if (row.block; as b) {
                        <td class="num">{{ pct(b['fill_rate']) }}</td><td class="num">{{ int(b['perdidas_unidades']) }}</td><td class="num">{{ int(b['stock_medio_unidades_por_dia']) }}</td>
                        <td class="num">{{ int(b['stock_final_unidades']) }}</td><td class="num">{{ pen(b['compras_desembolsadas_supuesto']) }}</td>
                      } @else { <td colspan="5">Sin resultados publicados.</td> }
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          } @else { <p class="state" data-testid="final-sim-empty-detail">Datos insuficientes: no hay simulación publicada para el escenario principal.</p> }

          <h3>Diferencias en el escenario principal (política − comparación; {{ clabel(simCoh()) }})</h3>
          <div class="table-wrap" tabindex="0" role="region" aria-label="Diferencias frente a la referencia y a promedio_28 (desplázate para ver todas las columnas)">
            <table data-testid="final-sim-diffs">
              <thead><tr><th scope="col">Política</th><th scope="col">Frente a</th><th scope="col" class="num">Δ servicio</th><th scope="col" class="num">Δ perdidas</th><th scope="col" class="num">Δ stock medio</th><th scope="col" class="num">Δ compras</th><th scope="col" class="num">Δ valor del stock final</th></tr></thead>
              <tbody>
                @for (p of pairs; track p.policy + p.vs) {
                  <tr [attr.data-testid]="'fdiff-' + p.policy + '-' + p.vs">
                    <th scope="row">{{ plabel(p.policy) }}</th><td>{{ plabel(p.vs) }}</td>
                    @if (diffMetrics(p.policy, p.vs); as m) {
                      <td class="num">{{ dd(m, 'fill_rate') }}</td><td class="num">{{ dd(m, 'perdidas_unidades') }}</td><td class="num">{{ dd(m, 'stock_medio_unidades_por_dia') }}</td>
                      <td class="num">{{ dd(m, 'compras_desembolsadas_supuesto') }}</td><td class="num">{{ dd(m, 'valor_stock_final_supuesto') }}</td>
                    } @else { <td colspan="5">Sin diferencia publicada.</td> }
                  </tr>
                }
              </tbody>
            </table>
          </div>
          <p class="muted">Diferencias absolutas con la variación relativa entre paréntesis. Mayor servicio vino con mayor stock y mayores compras; no se calcula ahorro ni utilidad.</p>

          <h3>Las 27 combinaciones (total): L × S × política</h3>
          <div class="table-wrap" tabindex="0" role="region" aria-label="Las 27 combinaciones de simulación (desplázate para ver todas las columnas)">
            <table data-testid="final-sim-27">
              <caption>Cada celda: servicio · unidades perdidas · stock medio (unid./día) · compras desembolsadas (PEN, supuesto)</caption>
              <thead><tr><th scope="col">L (días)</th><th scope="col">S (días)</th>@for (p of policies; track p.id) { <th scope="col">{{ p.label }}</th> }</tr></thead>
              <tbody>
                @for (c of combos(); track c.L + '-' + c.S) {
                  <tr [attr.data-testid]="'f27-' + c.L + '-' + c.S" [class.hl]="c.L === pL() && c.S === pS()">
                    <th scope="row">{{ c.L }}</th><td>{{ c.S }}</td>
                    @for (cell of c.cells; track cell.policy) { <td>{{ cell.text }}</td> }
                  </tr>
                }
              </tbody>
            </table>
          </div>
          <p class="muted" data-testid="combos-count">{{ combos().length * policies.length }} combinaciones publicadas de {{ Ls().length * Ss().length * policies.length }} esperadas.</p>

          <h3 id="h-svc">Servicio frente a inventario: modelo experimental frente a promedio_28 (total)</h3>
          <div class="table-wrap" tabindex="0" role="region" aria-label="Servicio frente a inventario (desplázate para ver todas las columnas)">
            <table data-testid="final-service-inventory">
              <thead><tr><th scope="col">L</th><th scope="col">S</th><th scope="col" class="num">Δ servicio</th><th scope="col" class="num">Δ stock medio (rel.)</th><th scope="col" class="num">Δ compras (rel.)</th><th scope="col" class="num">Δ perdidas (rel.)</th></tr></thead>
              <tbody>
                @for (s of svc(); track s.L + '-' + s.S) {
                  <tr [attr.data-testid]="'fsvc-' + s.L + '-' + s.S"><td>{{ s.L }}</td><td>{{ s.S }}</td><td class="num">{{ pp(s.dFill) }}</td><td class="num">{{ spct(s.dStockRel) }}</td><td class="num">{{ spct(s.dComprasRel) }}</td><td class="num">{{ spct(s.dPerdidasRel) }}</td></tr>
                }
              </tbody>
            </table>
          </div>
          <p class="muted">Una ventaja de servicio acompañada de más stock o más compras no se presenta como mejora; el desembolso y el costo consumido se muestran por separado.</p>

          <details class="tech" data-testid="final-sim-all">
            <summary>Todas las métricas del escenario principal ({{ clabel(simCoh()) }})</summary>
            <div class="table-wrap" tabindex="0" role="region" aria-label="Todas las métricas">
              <table>
                <thead><tr><th scope="col">Métrica</th>@for (p of policies; track p.id) { <th scope="col" class="num">{{ p.label }}</th> }</tr></thead>
                <tbody>@for (k of metricKeys(); track k) { <tr><th scope="row">{{ mlabelSim(k) }}</th>@for (row of main(); track row.policy) { <td class="num">{{ metric(row.block, k) }}</td> }</tr> }</tbody>
              </table>
            </div>
          </details>
          @if (d().disclaimer; as dis) { <p class="notice warn" data-testid="disclaimer">{{ dis }}</p> }
          @if (assumptionList().length) {
            <details class="tech" data-testid="final-assumptions">
              <summary>Supuestos y límites</summary>
              <ul class="plain">@for (a of assumptionList(); track a) { <li>{{ a }}</li> }</ul>
            </details>
          }
        </details>
      </section>
      </div>
    </div>
  `,
  styles: `
    .selectors legend { font-weight: 600; }
    section[id] { scroll-margin-top: 1rem; }
    .academic { margin: 0.75rem 0; border: 1px solid var(--line, #c9d1d9); border-radius: 8px; padding: 0.5rem 0.9rem; }
    .academic > summary { font-weight: 700; cursor: pointer; padding: 0.4rem 0; }
  `,
})
export class FinalEvaluation {
  d = input.required<BacktestDetail>();
  readonly DASH = DASH;
  readonly ne = NE;
  readonly vistas = FINAL_VISTAS;
  readonly cohorts = PRED_COHORTES;
  readonly allCohorts = COHORTES;
  readonly policies = POLICIES;
  readonly pairs = PAIRS;

  level = signal<'sku' | 'categoria'>('sku');
  coh = signal<string>('primaria');
  simCoh = signal<Cohorte>('total');

  pf = computed(() => primaryFinding(this.d()));
  readonly tabs: EvalTab[] = [
    { id: 'est', label: 'Estimaciones frente a ventas registradas', testid: 'jump-est' },
    { id: 'rep', label: 'Comparación de reposición simulada', testid: 'jump-rep' },
  ];
  tab = signal<string>('est');
  acOpen = signal(false);
  readonly windowNote = WINDOW_NOTE;
  /** Aviso breve de la vista inicial: la explicación ya dice que el error no es acierto; aquí, que no hay ganador. */
  readonly briefNotice = 'Con un solo bloque de prueba no se declara un método ganador; el método operativo no cambia por este resultado.';

  originIso = computed(() => this.d().run?.cutoff ?? null);
  /** Fechas del bloque evaluado: solo las publica el análisis (target_start/target_end o evaluation_period); sin respaldo escrito. */
  targetStart = computed(() => this.d().run?.target_start ?? (this.d().run?.evaluation_period?.['start'] as string | undefined) ?? null);
  targetEnd = computed(() => this.d().run?.target_end ?? (this.d().run?.evaluation_period?.['end'] as string | undefined) ?? null);
  /** Dos períodos distintos: la métrica H14 (primeros 14 días) y el bloque de prueba disponible (pronóstico fijo de 21 días). */
  periods = computed(() => metricPeriods('acum14', this.targetStart(), this.targetEnd()));
  periodItems = computed(() => [{ label: this.periods().metric, testid: 'period-metric' }, { label: this.periods().block, testid: 'period-block' }]);
  contextText = computed(() => `Esta es la evaluación de agosto, distinta del ejemplo de julio. Compara un pronóstico fijado el ${this.originIso() ? fmtDate(this.originIso()) : 'sin fecha publicada'} con las ventas registradas del bloque de prueba. Ya hay un resultado final disponible; no se generan pedidos ni recomendaciones.`);
  simple = computed(() => simpleScope('sku', 'primaria', 'acum14', fmtInt(this.pf().n)));
  explanation = computed(() => mainExplanation(this.pf().wape.promedio_28, 'sku', 'primaria', 'acum14'));
  principal = computed(() => this.d().assumptions?.escenario_principal ?? { L: 7, S: 7 });
  pL = computed(() => this.principal().L);
  pS = computed(() => this.principal().S);
  Ls = computed(() => this.d().assumptions?.L ?? [3, 7, 14]);
  Ss = computed(() => this.d().assumptions?.S ?? [0, 7, 14]);
  main = computed(() => POLICIES.map((p) => ({ policy: p.id, scenario: scenarioOf(this.d(), this.pL(), this.pS(), p.id), block: blockOf(this.d(), this.pL(), this.pS(), p.id, this.simCoh()) })));
  metricKeys = computed(() => { const f = this.main().find((r) => r.block)?.block; return f ? Object.keys(f) : []; });
  svc = computed(() => serviceVsInventory(this.d(), this.Ls(), this.Ss()));
  covRows = computed(() => finalCoverageRows(this.d(), 'sku'));
  covCat = computed(() => finalCoverageRows(this.d(), 'categoria'));
  nuevos = computed(() => newSkus(this.d()));
  uni = computed(() => universe(this.d()));

  /** «Ver cómo se evaluó»: abre el detalle académico de las estimaciones y lleva el foco a su rótulo. */
  openDetail() {
    this.tab.set('est');
    this.acOpen.set(true);
    queueMicrotask(() => {
      const s = document.getElementById('academic-summary');
      s?.scrollIntoView?.({ behavior: 'smooth', block: 'start' });
      s?.focus?.();
    });
  }

  /** Alcance exacto del hallazgo primario (fijo por contrato: WAPE H14, SKU-almacén, tipo de historial primaria, universo común). */
  scopeText = computed(() => `Alcance exacto: por producto y almacén (SKU-almacén) · tipo de historial «primaria» · acumulado de 14 días · universo común (n = ${fmtInt(this.pf().n)}). ${this.periods().metric}. ${this.periods().block}.`);
  /** Cifras del hallazgo primario, calculadas de los valores publicados; un error indefinido se rotula «no evaluable». */
  estLines = computed(() => {
    const p = this.pf();
    const lines = [
      `Error del promedio de 28 días (método operativo): ${errorText(p.wape.promedio_28)}. Error del modelo experimental: ${errorText(p.wape.rf)}. Control cero: ${errorText(p.wape.cero)}.`,
      compareSentence(p.wape.promedio_28, p.wape.rf),
    ];
    if (p.sesgoObs.promedio_28 !== null) lines.push(`Sesgo del promedio de 28 días: ${fmtPct(p.sesgoObs.promedio_28, true)} del volumen observado (negativo = se estimó de menos).`);
    else lines.push(`Sesgo del promedio de 28 días: ${NE}.`);
    return lines;
  });
  /** Conclusión de la reposición: escenario principal, total, modelo experimental frente al promedio de 28 días. */
  simLines = computed(() => {
    const rf = POLICIES[2].id;
    return simConclusion(blockOf(this.d(), this.pL(), this.pS(), FINAL_BASE, 'total'), blockOf(this.d(), this.pL(), this.pS(), rf, 'total'),
      diffOf(this.d(), this.pL(), this.pS(), rf, FINAL_BASE, 'total')?.metrics);
  });
  simScope = computed(() => `Alcance: escenario principal (plazo de entrega L${this.pL()} días, seguridad S${this.pS()} días) · todos los productos · inventario simulado de agosto de 2026.`);

  /** Combinaciones L × S con al menos una política publicada (total). */
  combos = computed(() => {
    const out: { L: number; S: number; cells: { policy: string; text: string }[] }[] = [];
    for (const L of this.Ls()) {
      for (const S of this.Ss()) {
        const cells = POLICIES.map((p) => {
          const b = blockOf(this.d(), L, S, p.id, 'total');
          return { policy: p.id, text: b ? `${fmtPct(b['fill_rate'])} · ${fmtInt(b['perdidas_unidades'])} · ${fmtInt(b['stock_medio_unidades_por_dia'])} · ${fmtPen(b['compras_desembolsadas_supuesto'])}` : 'sin dato' };
        });
        if (cells.some((c) => c.text !== 'sin dato')) out.push({ L, S, cells });
      }
    }
    return out;
  });
  assumptionList = computed(() => {
    const a = this.d().assumptions;
    if (!a) return [];
    const out: string[] = [];
    if (a['factor_costo_sobre_mediana_precio'] !== undefined) out.push(`Costo unitario supuesto = ${fmtPct(a['factor_costo_sobre_mediana_precio'])} de la mediana de precio base.`);
    if (a['holding_anual'] !== undefined) out.push(`Costo anual de mantener stock supuesto: ${fmtPct(a['holding_anual'])}.`);
    if (a.R !== undefined) out.push(`Revisión de pedidos cada ${a.R} días.`);
    if (typeof a.demanda === 'string') out.push(`Demanda: ${a.demanda}.`);
    return [...out, ...(a.limites ?? [])];
  });

  int = (v: unknown) => fmtInt(v);
  sint = (v: unknown) => fmtInt(v, true);
  dec = (v: unknown, n = 3) => fmtDec(v, n);
  pct = (v: unknown) => fmtPct(v);
  spct = (v: unknown) => fmtPct(v, true);
  pp = (v: unknown) => fmtPp(v);
  pen = (v: unknown) => fmtPen(v);
  /** Error absoluto publicado; indefinido = «no evaluable» (nunca 0). */
  err = (v: number | null | undefined) => errorText(v);
  date = (v: string | null | undefined) => fmtDate(v);
  scalars = (o: unknown) => scalarsOf(o);
  hasBlock = (r: { block: SimBlock | null }) => r.block !== null;
  rows = (level: 'sku' | 'categoria', coh: string, vista: string): PredRow[] => finalRows(this.d(), level, coh, vista);
  mlabel = (m: string) => FINAL_METHOD_INFO[m]?.label ?? m;
  mrole = (m: string) => FINAL_METHOD_INFO[m]?.role ?? '';
  clabel = (id: string) => COHORTES.find((c) => c.id === id)?.label ?? id;
  plabel = (id: string) => POLICIES.find((p) => p.id === id)?.label ?? id;
  mlabelSim = (k: string) => SIM_LABELS[k] ?? k;

  /** WAPE indefinido (sin unidades observadas) se rotula «no evaluable»; nunca se convierte en 0. */
  wape(r: PredRow): string { return r.WAPE === null || r.WAPE === undefined ? NE : fmtPct(r.WAPE); }
  cover(r: PredRow): string {
    const c = coverageOf(this.d(), this.level(), this.coh(), 'FINAL', r.metodo) ?? coverageOf(this.d(), this.level(), this.coh(), 'AGREGADO', r.metodo);
    return !c || c.universo === 0 ? DASH : `${fmtInt(c.conPrediccion)} de ${fmtInt(c.universo)}`;
  }
  metric(b: SimBlock | null, k: string): string {
    const v = b?.[k];
    switch (kindOf(k)) { case 'pct': return fmtPct(v); case 'pen': return fmtPen(v); default: return fmtInt(v); }
  }
  diffMetrics(policy: string, vs: string) {
    return diffOf(this.d(), this.pL(), this.pS(), policy, vs, this.simCoh())?.metrics ?? null;
  }
  dd(m: Record<string, { abs: number | null; rel: number | null }>, k: string): string {
    const x = m[k];
    if (!x || x.abs === null || x.abs === undefined) return DASH;
    const abs = kindOf(k) === 'pct' ? fmtPp(x.abs) : kindOf(k) === 'pen' || k === 'valor_stock_final_supuesto' ? fmtPen(x.abs, true) : fmtInt(x.abs, true);
    return x.rel === null || x.rel === undefined ? abs : `${abs} (${fmtPct(x.rel, true)})`;
  }
  readonly base = FINAL_BASE;
}
