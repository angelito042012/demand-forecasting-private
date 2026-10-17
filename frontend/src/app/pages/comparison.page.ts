import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { catchError, map, of, tap, throwError } from 'rxjs';
import { RunChoice } from '../core/run-choice';
import { ApiService } from '../core/api.service';
import { load } from '../core/load';
import { BacktestDetail, BacktestItem, Cohorte, Page, PredRow } from '../core/models';
import {
  AGREGADO, BASE_POLICY, COHORTES, METHOD_INFO, POLICIES, PRED_COHORTES, SIM_LABELS, SimRow, VISTAS,
  coverageOf, foldsOf, kindOf, predRows, simRows,
} from '../core/backtest';
import { DASH, fmtDate, fmtInt, fmtPct, fmtPen, fmtPp, fmtDec } from '../core/format';
import { StatePanel } from '../ui/state-panel';
import { RunBanner, SimNotice, SupersededBanner } from '../ui/notices';

const EVAL_START = '2026-06-01';
const EVAL_END = '2026-07-31';

/** Suma días a una fecha AAAA-MM-DD (UTC, sin zona horaria local). */
function addDays(iso: string, n: number): string {
  const [y, m, d] = iso.split('-').map(Number);
  return new Date(Date.UTC(y, m - 1, d + n)).toISOString().slice(0, 10);
}

@Component({
  selector: 'app-comparison-page',
  imports: [StatePanel, SimNotice, RunBanner, SupersededBanner, RouterLink],
  template: `
    <h2>Comparación de métodos y políticas</h2>
    <p>
      Resultados históricos de desarrollo, calculados sobre meses ya conocidos. No son una prueba final: agosto sigue reservado.
    </p>
    @if (chosen()) {
      <dl class="periods" data-testid="periods">
        <dt>Origen</dt><dd data-testid="p-origin">{{ originText() }}</dd>
        <dt>Fechas objetivo</dt><dd data-testid="p-target">{{ targetText() }}</dd>
        <dt>Período de evaluación del backtest y de la simulación</dt><dd data-testid="p-eval">{{ evalText }}</dd>
      </dl>
      <p class="muted" data-testid="periods-note">El origen es el último día con historia usada para pronosticar; no es el fin de la evaluación. Los pronósticos cubren las fechas objetivo y la simulación de reposición recorre todo el período de evaluación.</p>
    }
    <app-sim-notice [scenarioId]="scenario()" />
    @if (run(); as r) {
      <app-run-banner [runLabel]="r.run_label" [cutoff]="r.cutoff" [age]="r.age_days_at_view" />
      <app-superseded-banner [run]="r" />
    }
    <section class="notice info" data-testid="limits" aria-labelledby="h-leer">
      <h3 id="h-leer">Cómo leer esta pantalla</h3>
      <ul class="plain">
        <li>El método elegido es <strong>promedio de 28 días (promedio_28)</strong>. El comparador experimental <strong>RF</strong> (bosque aleatorio) <strong>no ganó</strong>:
          @if (selectionText(); as t) { {{ t }} }
        </li>
        <li>Más nivel de servicio viene con más stock y más compras: una mejora en servicio no es una ganancia neta si no se mira su costo.</li>
        <li>Los 4 pliegues (folds G1 a G4) se solapan; el agregado no es una evaluación independiente ni permite pruebas de significación.</li>
        <li>La simulación (nueve escenarios × 3 políticas = 27 combinaciones) usa inventario, costos y plazos supuestos; no demuestra una mejora real para la empresa ni autoriza compras.</li>
        <li>La demanda es la venta observada, que puede estar limitada por falta de stock: los faltantes reales son desconocidos.</li>
        <li>Se muestran todos los resultados, también los desfavorables y el control «cero»; los selectores solo cambian qué parte se ve.</li>
      </ul>
    </section>

    <app-state-panel [state]="list.state()" [emptyText]="choice.id() ? 'Sin backtest para esta corrida.' : 'No hay backtests publicados.'" (retry)="list.reload()">
      @if (items().length > 1) {
        <label>Backtest
          <select data-testid="bt-select" aria-label="Backtest" (change)="pick($any($event.target).value)">
            @for (b of items(); track b.backtest_id) {
              <option [value]="b.backtest_id" [selected]="b.backtest_id === chosen()">{{ b.label }}</option>
            }
          </select>
        </label>
      } @else if (items()[0]; as b) {
        <p class="muted" data-testid="bt-label">{{ b.label }}</p>
      }
    </app-state-panel>

    @if (choice.id() && list.state().kind === 'empty') {
      <p class="notice info" data-testid="no-backtest">
        La corrida elegida (<code>{{ choice.id() }}</code>) no tiene backtest propio: las corridas generadas por la aplicación no repiten experimentos y no hay ventas observadas posteriores a su origen.
        @if (histRun(); as h) { <a [routerLink]="['/comparacion']" [queryParams]="{ run: h }" data-testid="hist-link">Ver el backtest histórico T07</a> }
      </p>
    }
    @if (chosen()) {
      <app-state-panel [state]="detail.state()" emptyText="Datos insuficientes: el backtest no publicó resultados." (retry)="detail.reload()">
        @if (det(); as d) {
          @if (d.disclaimer) { <p class="notice warn" data-testid="disclaimer">{{ d.disclaimer }}</p> }

          <section aria-labelledby="h-sim">
            <h3 id="h-sim">Simulación de reposición: tres políticas</h3>
            <p>
              Cada fila es una política de pedidos aplicada a un inventario simulado entre el 01/06 y el 31/07/2026.
              @if (isPrincipal()) { <span class="badge ok" data-testid="principal-badge">Escenario principal (L{{ L() }} / S{{ S() }})</span> }
              @else { <span class="badge" data-testid="principal-badge">Escenario L{{ L() }} / S{{ S() }}; el principal es L{{ principal().L }} / S{{ principal().S }}</span> }
            </p>
            <fieldset class="selectors" aria-label="Selección de escenario de simulación">
              <legend>Escenario</legend>
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
              <label for="sel-c">Cohorte
                <select id="sel-c" data-testid="sel-coh" (change)="simCoh.set($any($event.target).value)">
                  @for (c of cohortes; track c.id) { <option [value]="c.id" [selected]="c.id === simCoh()">{{ c.label }}</option> }
                </select>
              </label>
            </fieldset>

            @if (sim().some(hasBlock)) {
              <div class="table-wrap" tabindex="0" role="region" aria-label="Tabla de políticas de reposición">
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
                  <li>Backtest: <code>{{ d.backtest_id ?? 'sin dato' }}</code> · corrida <code>{{ d['run_id'] ?? 'sin dato' }}</code> · procedencia <code>{{ d.provenance ?? 'sin dato' }}</code></li>
                </ul>
                <pre>{{ simJson() }}</pre>
              </details>
            } @else {
              <p class="state" data-testid="sim-empty">Datos insuficientes: no hay simulación publicada para L{{ L() }} / S{{ S() }}.</p>
            }

            @if (assumptionList().length) {
              <details class="tech" data-testid="assumptions">
                <summary>Supuestos y límites de la simulación</summary>
                <ul class="plain">@for (a of assumptionList(); track a) { <li>{{ a }}</li> }</ul>
              </details>
            }
          </section>

          <section aria-labelledby="h-pred">
            <h3 id="h-pred">Precisión de los pronósticos (backtest)</h3>
            <fieldset class="selectors" aria-label="Selección de resultados predictivos">
              <legend>Resultados a mostrar</legend>
              <label for="p-level">Nivel
                <select id="p-level" data-testid="pred-level" (change)="level.set($any($event.target).value)">
                  <option value="sku" [selected]="level() === 'sku'">SKU</option>
                  <option value="categoria" [selected]="level() === 'categoria'">Categoría</option>
                </select>
              </label>
              <label for="p-coh">Cohorte
                <select id="p-coh" data-testid="pred-coh" (change)="predCoh.set($any($event.target).value)">
                  @for (c of predCohortes; track c.id) { <option [value]="c.id" [selected]="c.id === predCoh()">{{ c.label }}</option> }
                </select>
              </label>
              <label for="p-vista">Horizonte (vista)
                <select id="p-vista" data-testid="pred-vista" (change)="userVista.set($any($event.target).value)">
                  @for (v of vistas; track v.id) { <option [value]="v.id" [selected]="v.id === vista()">{{ v.label }}</option> }
                </select>
              </label>
              <label for="p-fold">Pliegue (fold)
                <select id="p-fold" data-testid="pred-fold" (change)="fold.set($any($event.target).value)">
                  @for (f of folds(); track f) { <option [value]="f" [selected]="f === fold()">{{ f === agregado ? 'Agregado (G1 a G4)' : f }}</option> }
                </select>
              </label>
            </fieldset>

            @if (pred().length) {
              <div class="table-wrap" tabindex="0" role="region" aria-label="Tabla de métricas por método">
                <table data-testid="pred-table">
                  <caption>{{ level() === 'sku' ? 'SKU' : 'Categoría' }} · {{ predCohLabel() }} · {{ vistaLabel() }} · {{ fold() === agregado ? 'agregado de 4 folds solapados' : fold() }}</caption>
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
                          <td class="num" data-testid="wape">{{ pct(r.WAPE) }}</td>
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
            </ul>
            @if (d.predictive?.nota; as n) { <p class="muted">{{ n }}</p> }
          </section>
        }
      </app-state-panel>
    }
  `,
  styles: `
    .selectors select { min-width: 9rem; }
    .periods { display: grid; grid-template-columns: max-content 1fr; gap: 0.2rem 1rem; margin: 0.4rem 0; }
    .periods dt { font-weight: 600; } .periods dd { margin: 0; }
    pre { white-space: pre-wrap; overflow-wrap: anywhere; background: var(--soft); padding: 0.5rem; max-height: 22rem; overflow: auto; font-size: 0.8rem; }
  `,
})
export class ComparisonPage {
  private api = inject(ApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);
  /** Corrida elegida (parámetro de URL «run»); sin él, el backtest publicado por defecto. */
  choice = new RunChoice(this.route, this.router, this.destroyRef, () => { this.chosen.set(null); this.histRun.set(null); this.list.reload(); });
  histRun = signal<string | null>(null);
  readonly evalText = `${fmtDate(EVAL_START)} al ${fmtDate(EVAL_END)}`;
  readonly policies = POLICIES;
  readonly cohortes = COHORTES;
  readonly predCohortes = PRED_COHORTES;
  readonly vistas = VISTAS;
  readonly agregado = AGREGADO;
  readonly base = BASE_POLICY;

  chosen = signal<string | null>(null);
  list = load<BacktestItem[]>(
    () => this.api.backtests(this.choice.id() ?? undefined).pipe(
      map((r) => (Array.isArray(r) ? r : (r as Page<BacktestItem>).items)),
      catchError((e: { status?: number }) => (this.choice.id() && e?.status === 404 ? of([] as BacktestItem[]) : throwError(() => e))),
      tap((items) => { if (!items.length && this.choice.id()) this.findHistorical(); }),
      // Selecciona el primer backtest al llegar la lista.
      tap((items) => { if (items.length && !this.chosen()) { this.chosen.set(items[0].backtest_id); queueMicrotask(() => this.detail.reload()); } }),
    ),
    (d) => d.length === 0,
  );
  items = computed(() => { const s = this.list.state(); return s.kind === 'data' ? s.data : []; });
  // Siempre se pide la vista completa; los selectores solo filtran lo que se muestra.
  detail = load<BacktestDetail>(() => this.api.backtest(this.chosen()!, 'all'), (d) => Object.keys(d).length === 0, false);
  det = computed(() => { const s = this.detail.state(); return s.kind === 'data' ? s.data : null; });
  scenario = computed(() => this.det()?.scenario_id ?? null);
  run = computed(() => this.det()?.run ?? null);
  /** Origen: corte de la corrida (valor publicado). */
  origin = computed(() => this.run()?.cutoff ?? null);
  originText = computed(() => (this.origin() ? fmtDate(this.origin()) : 'sin dato'));
  /** Fechas objetivo: las publicadas por la corrida; si faltan, origen + 1 a origen + 21 (horizonte fijo de 21 días). */
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
    return parts.length ? parts.join('; ') + '.' : '';
  });

  // Predictivo
  level = signal<'sku' | 'categoria'>('sku');
  predCoh = signal<string>('primaria');
  userVista = signal<string | null>(null);
  vista = computed(() => this.userVista() ?? (this.det()?.selection?.vista as string | undefined) ?? 'acum14');
  fold = signal<string>(AGREGADO);
  folds = computed(() => foldsOf(this.det()));
  pred = computed<PredRow[]>(() => predRows(this.det(), this.level(), this.predCoh(), this.vista(), this.fold()));

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
}
