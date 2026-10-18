import { Component, computed, input, signal } from '@angular/core';
import { BacktestDetail, Cohorte, PredRow, SimBlock } from '../core/models';
import { COHORTES, POLICIES, PRED_COHORTES, SIM_LABELS, coverageOf, kindOf } from '../core/backtest';
import {
  FINAL_BASE, FINAL_METHOD_INFO, FINAL_VISTAS, blockOf, diffOf, finalCoverageRows, finalRows, newSkus, primaryFinding,
  scalarsOf, scenarioOf, serviceVsInventory, universe,
} from '../core/final-eval';
import { DASH, fmtDate, fmtDec, fmtInt, fmtPct, fmtPen, fmtPp } from '../core/format';
import { SimNotice } from '../ui/notices';

const NE = 'no evaluable';
/** Pares «política − comparación» publicados en la simulación del escenario elegido. */
const PAIRS: { policy: string; vs: string }[] = [
  { policy: 'referencia_fija', vs: 'promedio_28' },
  { policy: 'promedio_28', vs: 'referencia_fija' },
  { policy: 'rf_categoria_distribuido', vs: 'referencia_fija' },
  { policy: 'rf_categoria_distribuido', vs: 'promedio_28' },
];

/**
 * Vista «Evaluación final (T12)»: bloque único 01–21/08/2026 con origen 31/07/2026 y simulación secuencial de agosto.
 * Separada de la comparación T07 de desarrollo. Solo muestra lo que publica el documento del backtest `final_evaluation`.
 */
@Component({
  selector: 'app-final-evaluation',
  imports: [SimNotice],
  template: `
    <div data-testid="final-view">
      <h3 id="h-fin">Evaluación final (T12)</h3>
      <p class="notice info" data-testid="final-scope">
        Esta vista es distinta de la comparación de desarrollo T07. Compara un pronóstico fijado el
        <strong>{{ date(originIso()) }}</strong> con las ventas observadas del <strong>{{ date('2026-08-01') }} al {{ date('2026-08-21') }}</strong>
        (un solo bloque de 21 días), más una simulación de reposición del 01/08 al 31/08/2026. No hay umbrales prometidos ni se declara un método ganador.
      </p>

      <section aria-labelledby="h-prim" data-testid="final-primary">
        <h4 id="h-prim">Hallazgo primario</h4>
        <p>WAPE acumulado a 14 días, SKU-almacén, cohorte primaria, universo común
          (n = <strong data-testid="primary-n">{{ int(pf().n) }}</strong>).</p>
        <div class="table-wrap" tabindex="0" role="region" aria-label="Hallazgo primario">
          <table data-testid="primary-table">
            <thead><tr><th scope="col">Método</th><th scope="col" class="num">WAPE H14</th><th scope="col" class="num">Sesgo / observado</th></tr></thead>
            <tbody>
              <tr data-testid="primary-promedio"><th scope="row">Promedio de 28 días <span class="badge">método operativo</span></th><td class="num">{{ pct(pf().wape.promedio_28) }}</td><td class="num">{{ spct(pf().sesgoObs.promedio_28) }}</td></tr>
              <tr data-testid="primary-rf"><th scope="row">RF distribuido <span class="badge">comparador</span></th><td class="num">{{ pct(pf().wape.rf) }}</td><td class="num">{{ spct(pf().sesgoObs.rf) }}</td></tr>
              <tr data-testid="primary-cero"><th scope="row">Control cero <span class="badge">control</span></th><td class="num">{{ pct(pf().wape.cero) }}</td><td class="num">{{ DASH }}</td></tr>
            </tbody>
          </table>
        </div>
        <ul class="plain">
          <li data-testid="primary-mejora">Mejora relativa de RF frente a promedio_28: <strong>{{ spct(pf().mejora) }}</strong> (positiva = RF con menor WAPE; negativa = peor que promedio_28).</li>
          <li data-testid="primary-sesgo">Sesgo relativo publicado en la selección: <strong>{{ spct(pf().sesgoRelPublicado) }}</strong>.</li>
          <li data-testid="primary-winner">RF declarado ganador: <strong>{{ pf().rfDeclaredWinner === false ? 'no' : pf().rfDeclaredWinner === true ? 'sí (valor publicado)' : 'sin dato' }}</strong>. Con un solo bloque no hay inferencia de ganador; el método operativo no cambia por este resultado.</li>
          @if (pf().criterion; as c) { <li>Criterio primario: {{ c }}</li> }
          @if (pf().note; as n) { <li>{{ n }}</li> }
        </ul>
      </section>

      <section aria-labelledby="h-coh">
        <h4 id="h-coh">Resumen por cohorte (SKU-almacén, acumulado 14 días)</h4>
        <div class="table-wrap" tabindex="0" role="region" aria-label="Resumen por cohorte">
          <table data-testid="cohort-summary">
            <thead><tr><th scope="col">Cohorte</th><th scope="col">Método</th><th scope="col" class="num">n</th><th scope="col" class="num">WAPE</th></tr></thead>
            <tbody>
              @for (c of cohorts; track c.id) {
                @for (r of rows('sku', c.id, 'acum14'); track r.metodo) {
                  <tr [attr.data-testid]="'cs-' + c.id + '-' + r.metodo"><td>{{ c.label }}</td><td>{{ mlabel(r.metodo) }}</td><td class="num">{{ int(r.n) }}</td><td class="num">{{ wape(r) }}</td></tr>
                } @empty { <tr><td>{{ c.label }}</td><td colspan="3">Sin filas publicadas.</td></tr> }
              }
            </tbody>
          </table>
        </div>
        <p class="muted">La cohorte «historia_corta» agrupa SKU con poca historia al 31/07; sus resultados no se mezclan con la cohorte primaria.</p>
      </section>

      <section aria-labelledby="h-pt">
        <h4 id="h-pt">Precisión por horizonte</h4>
        <fieldset class="selectors" aria-label="Selección de resultados de la evaluación final">
          <legend>Resultados a mostrar</legend>
          <label for="f-level">Nivel
            <select id="f-level" data-testid="final-level" (change)="level.set($any($event.target).value)">
              <option value="sku" [selected]="level() === 'sku'">SKU-almacén</option>
              <option value="categoria" [selected]="level() === 'categoria'">Categoría (suma de pronósticos SKU)</option>
            </select>
          </label>
          <label for="f-coh">Cohorte
            <select id="f-coh" data-testid="final-coh" (change)="coh.set($any($event.target).value)">
              @for (c of cohorts; track c.id) { <option [value]="c.id" [selected]="c.id === coh()">{{ c.label }}</option> }
            </select>
          </label>
        </fieldset>
        @if (level() === 'categoria') {
          <p class="notice warn" data-testid="cat-note">Categoría = suma de unidades base heterogéneas: la cifra de una categoría mezcla productos con unidades distintas y solo sirve para comparar métodos entre sí.</p>
        }
        @for (v of vistas; track v.id) {
          @let rs = rows(level(), coh(), v.id);
          @if (rs.length) {
            <div class="table-wrap" tabindex="0" role="region" [attr.aria-label]="'Métricas ' + v.label">
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
        <h4 id="h-cov">Cobertura y SKU nuevos</h4>
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

      <section aria-labelledby="h-fsim" data-testid="final-sim">
        <h4 id="h-fsim">Simulación de reposición del 01/08 al 31/08/2026</h4>
        <app-sim-notice [scenarioId]="d().scenario_id ?? null" />
        <p class="notice warn" data-testid="final-sim-label">Todo lo de esta sección usa existencias, costos y plazos supuestos. La demanda es la venta observada (proxy), posiblemente limitada por stock; costos, plazos y seguridad son supuestos. No demuestra impacto real ni autoriza compras.</p>

        <fieldset class="selectors" aria-label="Cohorte de la simulación">
          <legend>Escenario principal (L{{ pL() }} / S{{ pS() }})</legend>
          <label for="fs-coh">Cohorte inicial
            <select id="fs-coh" data-testid="final-sim-coh" (change)="simCoh.set($any($event.target).value)">
              @for (c of allCohorts; track c.id) { <option [value]="c.id" [selected]="c.id === simCoh()">{{ c.label }}</option> }
            </select>
          </label>
        </fieldset>
        @if (main().some(hasBlock)) {
          <div class="table-wrap" tabindex="0" role="region" aria-label="Escenario principal">
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
        } @else { <p class="state" data-testid="final-sim-empty">Datos insuficientes: no hay simulación publicada para el escenario principal.</p> }

        <h5>Diferencias en el escenario principal (política − comparación; {{ clabel(simCoh()) }})</h5>
        <div class="table-wrap" tabindex="0" role="region" aria-label="Diferencias frente a la referencia y a promedio_28">
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

        <h5>Las 27 combinaciones (total): L × S × política</h5>
        <div class="table-wrap" tabindex="0" role="region" aria-label="Las 27 combinaciones de simulación">
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

        <h5 id="h-svc">Servicio frente a inventario: RF distribuido frente a promedio_28 (total)</h5>
        <div class="table-wrap" tabindex="0" role="region" aria-label="Servicio frente a inventario">
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
      </section>

      @if (assumptionList().length) {
        <details class="tech" data-testid="final-assumptions">
          <summary>Supuestos y límites</summary>
          <ul class="plain">@for (a of assumptionList(); track a) { <li>{{ a }}</li> }</ul>
        </details>
      }
    </div>
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
  originIso = computed(() => this.d().run?.cutoff ?? '2026-07-31');
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
