import { Component, input } from '@angular/core';
import { Provenance } from '../core/models';

@Component({
  selector: 'app-demo-badge',
  template: `
    @if (provenance() === 'DEMO_MOCK') {
      <span class="badge demo" role="note">DATOS DE DEMOSTRACIÓN – no son resultados reales</span>
    }
    @if (provenance() === 'SYNTHETIC_NOT_REAL_INVENTORY') {
      <span class="badge syn" role="note">SINTÉTICO – SYNTHETIC_NOT_REAL_INVENTORY: no es inventario real</span>
    }
  `,
  styles: `
    .badge { display: inline-block; padding: 0.25rem 0.6rem; border-radius: 4px; font-weight: 600; font-size: 0.85rem; }
    .demo { background: #fff3cd; color: #664d03; border: 1px solid #ffda6a; }
    .syn { background: #cfe2ff; color: #052c65; border: 1px solid #9ec5fe; }
  `,
})
export class DemoBadge {
  provenance = input.required<Provenance>();
}
