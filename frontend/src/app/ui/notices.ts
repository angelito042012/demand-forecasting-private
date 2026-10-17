import { Component, computed, input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { isStaleAge, STALE_DAYS } from '../core/age';
import { fmtDate } from '../core/format';
import { RunQuality, SIM_NOTICE } from '../core/models';

/** Aviso obligatorio en pantallas con stock, tránsito, costos o pedidos simulados. Los identificadores van plegados. */
@Component({
  selector: 'app-sim-notice',
  template: `
    <div class="notice sim" role="note" data-testid="sim-notice">
      <strong>{{ text }}.</strong>
      <details class="tech">
        <summary>Detalle técnico</summary>
        @if (scenarioId()) { <p>Escenario: <code data-testid="scenario-id">{{ scenarioId() }}</code></p> }
        <p>Procedencia: <code>SYNTHETIC_NOT_REAL_INVENTORY</code></p>
      </details>
    </div>
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
    <p class="notice warn" data-testid="run-banner">
      <strong data-testid="run-label">{{ runLabel() }}</strong>
      · corte {{ cutoffText() }} · antigüedad <span data-testid="age">{{ age() }}</span> día(s) al consultar
      @if (stale()) {
        <strong class="stale" data-testid="stale">Corrida antigua (más de {{ staleDays }} días; umbral supuesto de la interfaz)</strong>
      }
    </p>
  `,
})
export class RunBanner {
  runLabel = input.required<string>();
  cutoff = input.required<string>();
  age = input.required<number>();
  staleDays = STALE_DAYS;
  stale = computed(() => isStaleAge(this.age()));
  cutoffText = computed(() => fmtDate(this.cutoff()));
}

/** Aviso cuando la corrida fue sustituida por una corrección de precisión o no está validada. */
export function isRunInvalid(r: RunQuality | null | undefined): boolean {
  if (!r) return false;
  return r.status === 'superseded' || (r.validation_status !== undefined && r.validation_status !== null && r.validation_status !== 'valid');
}

@Component({
  selector: 'app-superseded-banner',
  imports: [RouterLink],
  template: `
    @if (invalid()) {
      <div class="notice danger" role="alert" data-testid="superseded-banner">
        <strong>Esta corrida fue sustituida por una corrección de precisión (recomendaciones con error de redondeo); no use sus pedidos.</strong>
        @if (supersededBy(); as id) {
          <a [routerLink]="['/corridas']" [queryParams]="{ run: id }" data-testid="superseded-link">Ver la corrida corregida</a>
        }
        @if (reason(); as why) { <p data-testid="superseded-reason">Motivo: {{ why }}</p> }
      </div>
    }
  `,
})
export class SupersededBanner {
  run = input<RunQuality | null | undefined>(null);
  invalid = computed(() => isRunInvalid(this.run()));
  supersededBy = computed(() => this.run()?.quality_issue?.superseded_by ?? null);
  reason = computed(() => {
    const q = this.run()?.quality_issue;
    return q?.reason ?? q?.message ?? null;
  });
}

@Component({
  selector: 'app-observed-notice',
  template: `<p class="notice ok" role="note">Ventas observadas (Excel, <code>OBSERVED_EXCEL</code>), en unidad base; importes en PEN. No incluyen stock ni costos supuestos. La venta observada puede estar limitada por falta de stock.</p>`,
})
export class ObservedNotice {}

@Component({
  selector: 'app-demo-banner',
  template: `<div class="demo-banner" role="alert" data-testid="demo-banner">MODO DEMOSTRACIÓN (?demo=1, solo desarrollo): datos ficticios, no son resultados reales.</div>`,
})
export class DemoBanner {}
