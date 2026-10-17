import { Component, computed, input } from '@angular/core';
import { isStaleAge, STALE_DAYS } from '../core/age';
import { SIM_NOTICE } from '../core/models';

/** Aviso obligatorio en pantallas con stock, tránsito, costos o pedidos simulados. */
@Component({
  selector: 'app-sim-notice',
  template: `
    <p class="sim" role="note" data-testid="sim-notice">
      <strong>{{ text }}.</strong>
      @if (scenarioId()) { Escenario: <code data-testid="scenario-id">{{ scenarioId() }}</code>. }
      <span class="mono">SYNTHETIC_NOT_REAL_INVENTORY</span>
    </p>
  `,
  styles: `
    .sim { background: #cfe2ff; color: #052c65; border: 1px solid #9ec5fe; padding: 0.4rem 0.7rem; border-radius: 4px; }
    .mono { font-family: monospace; font-size: 0.8rem; }
  `,
})
export class SimNotice {
  text = SIM_NOTICE;
  scenarioId = input<string | null>(null);
}

/** Etiqueta de corrida, fecha de corte y antigüedad (age_days_at_view del servidor). */
@Component({
  selector: 'app-run-banner',
  template: `
    <p class="run" data-testid="run-banner">
      <strong data-testid="run-label">{{ runLabel() }}</strong>
      · corte {{ cutoff() }} · antigüedad <span data-testid="age">{{ age() }}</span> día(s) al consultar
      @if (stale()) {
        <strong class="stale" data-testid="stale">CORRIDA ANTIGUA (más de {{ staleDays }} días; umbral supuesto de la interfaz)</strong>
      }
    </p>
  `,
  styles: `
    .run { background: #fff3cd; color: #664d03; border: 1px solid #ffda6a; padding: 0.4rem 0.7rem; border-radius: 4px; }
    .stale { color: #b02a37; margin-left: 0.5rem; }
  `,
})
export class RunBanner {
  runLabel = input.required<string>();
  cutoff = input.required<string>();
  age = input.required<number>();
  staleDays = STALE_DAYS;
  stale = computed(() => isStaleAge(this.age()));
}

@Component({
  selector: 'app-observed-notice',
  template: `<p class="obs" role="note">Ventas observadas (Excel, <span class="mono">OBSERVED_EXCEL</span>), en unidad base; importes en PEN. No incluyen stock ni costos supuestos. La venta observada puede estar limitada por falta de stock.</p>`,
  styles: `.obs { background: #d1e7dd; color: #0a3622; border: 1px solid #a3cfbb; padding: 0.4rem 0.7rem; border-radius: 4px; } .mono { font-family: monospace; font-size: 0.8rem; }`,
})
export class ObservedNotice {}

@Component({
  selector: 'app-demo-banner',
  template: `<div class="demo" role="alert" data-testid="demo-banner">MODO DEMOSTRACIÓN (?demo=1, solo desarrollo): datos ficticios, no son resultados reales.</div>`,
  styles: `.demo { background: #ffc107; color: #000; font-weight: 700; padding: 0.4rem 1rem; text-align: center; }`,
})
export class DemoBanner {}
