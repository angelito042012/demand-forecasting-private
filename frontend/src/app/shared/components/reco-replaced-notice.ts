import { Component, computed, input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { RunQuality } from '../../core/models';
import { isRunInvalid } from './notices';

/**
 * UX01: aviso breve cuando la API marca el análisis como reemplazado o no válido (calidad publicada junto a las sugerencias).
 * Conserva el enlace al análisis corregido y el motivo (plegado).
 */
@Component({
  selector: 'app-reco-replaced-notice',
  imports: [RouterLink],
  template: `
    @if (invalid()) {
      <div class="notice danger" role="alert" data-testid="superseded-banner">
        <strong>Esta versión fue reemplazada. No uses sus sugerencias.</strong>
        @if (supersededBy(); as id) {
          <a [routerLink]="['/corridas']" [queryParams]="{ run: id }" data-testid="superseded-link">Ver el análisis corregido</a>
        }
        @if (reason(); as why) { <details class="tech"><summary>Motivo</summary><p data-testid="superseded-reason">{{ why }}</p></details> }
      </div>
    }
  `,
})
export class RecoReplacedNotice {
  run = input<RunQuality | null | undefined>(null);
  invalid = computed(() => isRunInvalid(this.run()));
  supersededBy = computed(() => this.run()?.quality_issue?.superseded_by ?? null);
  reason = computed(() => { const q = this.run()?.quality_issue; return q?.reason ?? q?.message ?? null; });
}
