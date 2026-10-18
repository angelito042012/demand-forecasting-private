import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AuthService } from '../core/auth.service';
import { GLOSSARY } from '../core/ux-text';
import { PageHeader } from '../ui/page-header';
import { FIRST_STEPS, resetOnboarding } from './first-steps';

/** Ayuda: primeros pasos, glosario, límites de la aplicación y cómo leer el error WAPE. Solo lectura. */
@Component({
  selector: 'app-help-page',
  imports: [RouterLink, PageHeader],
  template: `
    <app-page-header title="Ayuda" lead="Primeros pasos, el significado de cada término y lo que esta aplicación no hace." />

    <section class="surface" aria-labelledby="h-steps" data-testid="help-steps">
      <h2 id="h-steps">Primeros pasos</h2>
      <ol class="steps">
        @for (s of steps; track s.title) { <li><strong>{{ s.title }}.</strong> {{ s.text }}</li> }
      </ol>
      <p>
        <button type="button" class="secondary" (click)="showAgain()" data-testid="onboarding-reset">Volver a mostrar «Cómo empezar» en Inicio</button>
        @if (reset()) { <span role="status" data-testid="onboarding-reset-done"> Listo: lo verás en <a [routerLink]="['/inicio']" queryParamsHandling="preserve">Inicio</a>.</span> }
      </p>
    </section>

    <section class="surface" aria-labelledby="h-not" data-testid="help-limits">
      <h2 id="h-not">Qué no hace esta aplicación</h2>
      <ul class="plain">
        <li>No es tu inventario real: el inventario del ejemplo es simulado, con supuestos.</li>
        <li>No ejecuta compras ni envía pedidos a proveedores: las cantidades sugeridas son un escenario para entender el cálculo.</li>
        <li>No pronostica las ventas de hoy ni de los próximos días: trabaja con datos históricos de 2026.</li>
        <li>Consultar nunca crea trabajos ni cambia datos. Solo el administrador carga archivos o crea análisis.</li>
      </ul>
    </section>

    <section class="surface" aria-labelledby="h-wape" data-testid="help-wape">
      <h2 id="h-wape">Cómo leer el error absoluto (WAPE)</h2>
      <p>Es la suma de los errores dividida entre las unidades vendidas. Un valor bajo indica menos error. Por ejemplo, un WAPE de 0,78 equivale a un error acumulado de alrededor del 78 % del volumen vendido; <strong>no significa 78 % de acierto</strong>.</p>
      <p class="muted">Cuando la comparación no se puede calcular, la pantalla dice «no evaluable»; eso no es un error cero.</p>
    </section>

    <section class="surface" aria-labelledby="h-gl" data-testid="help-glossary">
      <h2 id="h-gl">Glosario</h2>
      <dl class="kv">
        @for (g of glossary; track g.term) {
          <dt>{{ g.term }}</dt>
          <dd>{{ g.meaning }} <span class="muted">(Término técnico: {{ g.technical }})</span></dd>
        }
      </dl>
    </section>
  `,
})
export class HelpPage {
  private auth = inject(AuthService);
  steps = FIRST_STEPS;
  glossary = GLOSSARY;
  reset = signal(false);
  showAgain() { resetOnboarding(this.auth.session()?.username); this.reset.set(true); }
}
