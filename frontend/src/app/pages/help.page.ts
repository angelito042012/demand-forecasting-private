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
        <li>No es tu inventario real en la evaluación académica: allí el inventario es simulado, con supuestos. Las existencias del plan vienen del conteo informado por la empresa y los movimientos del sistema.</li>
        <li>No ejecuta compras ni envía pedidos a proveedores: las cantidades recomendadas son una propuesta para que decidas.</li>
        <li>No pronostica las ventas de hoy: el plan usa ventas registradas hasta su fecha de corte (lo posterior es desconocido, no cero) y la evaluación académica trabaja con datos históricos de 2026.</li>
        <li>Consultar nunca crea trabajos ni cambia datos. Solo el administrador carga archivos o crea análisis.</li>
      </ul>
    </section>

    <section class="surface" aria-labelledby="h-upd" data-testid="help-plan-update">
      <h2 id="h-upd">Cómo se actualiza el plan de noviembre</h2>
      <p><strong>Lo que puede hacer el administrador desde la aplicación:</strong> generar una versión nueva del plan en «Compra recomendada» (decisión, plazos, reserva, compra mínima, múltiplo y pedidos por recibir). Si los datos y parámetros son idénticos, se reutiliza la versión existente.</p>
      <p><strong>Lo que requiere soporte técnico:</strong> incorporar ventas o existencias posteriores al 20/10/2026. Se concilian con la base de la empresa (solo lectura), se sellan como una versión nueva de los datos del plan y se publican en la nube. «Cargar datos» y «Crear análisis» <strong>no</strong> lo hacen: son para los análisis históricos académicos (marzo a julio de 2026; agosto queda reservado para la prueba final).</p>
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
