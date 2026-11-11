import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AuthService } from '../core/services/auth.service';
import { GLOSSARY } from '../core/utils/ux-text';
import { PageHeader } from '../shared/components/page-header';
import { FIRST_STEPS, resetOnboarding } from './first-steps';
import { AccordionModule } from 'primeng/accordion';
import { ButtonModule } from 'primeng/button';
import { TagModule } from 'primeng/tag';

@Component({
  selector: 'app-help-page',
  imports: [RouterLink, PageHeader, AccordionModule, ButtonModule, TagModule],
  template: `
    <app-page-header title="Ayuda" lead="Primeros pasos, el significado de cada término y lo que esta aplicación no hace." />

    <p-accordion [value]="['0']" [multiple]="true">
      <p-accordion-panel value="0" data-testid="help-steps">
        <p-accordion-header>Primeros pasos</p-accordion-header>
        <p-accordion-content>
          <ol class="steps">
            @for (s of steps; track s.title) { <li><strong>{{ s.title }}.</strong> {{ s.text }}</li> }
          </ol>
          <div class="flex align-items-center gap-3 mt-3">
            <p-button label="Volver a mostrar «Cómo empezar» en Inicio" icon="pi pi-refresh" [outlined]="true" (onClick)="showAgain()" data-testid="onboarding-reset" />
            @if (reset()) { <span role="status" data-testid="onboarding-reset-done">Listo: lo verás en <a [routerLink]="['/inicio']" queryParamsHandling="preserve">Inicio</a>.</span> }
          </div>
        </p-accordion-content>
      </p-accordion-panel>

      <p-accordion-panel value="1" data-testid="help-limits">
        <p-accordion-header>Qué no hace esta aplicación</p-accordion-header>
        <p-accordion-content>
          <ul class="help-list">
            <li><p-tag severity="warn" value="Simulado" /> No es tu inventario real en la evaluación académica: allí el inventario es simulado, con supuestos. Las existencias del plan vienen del conteo informado por la empresa y los movimientos del sistema.</li>
            <li><p-tag severity="info" value="Solo lectura" /> No ejecuta compras ni envía pedidos a proveedores: las cantidades recomendadas son una propuesta para que decidas.</li>
            <li><p-tag severity="info" value="Histórico" /> No pronostica las ventas de hoy: el plan usa ventas registradas hasta su fecha de corte (lo posterior es desconocido, no cero) y la evaluación académica trabaja con datos históricos de 2026.</li>
            <li><p-tag severity="success" value="Seguro" /> Consultar nunca crea trabajos ni cambia datos. Solo el administrador carga archivos o crea análisis.</li>
          </ul>
        </p-accordion-content>
      </p-accordion-panel>

      <p-accordion-panel value="2" data-testid="help-plan-update">
        <p-accordion-header>Cómo se actualiza el plan de noviembre</p-accordion-header>
        <p-accordion-content>
          <p><strong>Lo que puede hacer el administrador desde la aplicación:</strong> generar una versión nueva del plan en «Compra recomendada» (decisión, plazos, reserva, compra mínima, múltiplo y pedidos por recibir). Si los datos y parámetros son idénticos, se reutiliza la versión existente.</p>
          <p><strong>Lo que requiere soporte técnico:</strong> incorporar ventas o existencias posteriores al 20/10/2026. Se concilian con la base de la empresa (solo lectura), se sellan como una versión nueva de los datos del plan y se publican en la nube. «Cargar datos» y «Crear análisis» <strong>no</strong> lo hacen: son para los análisis históricos académicos (enero a septiembre de 2026).</p>
        </p-accordion-content>
      </p-accordion-panel>

      <p-accordion-panel value="3" data-testid="help-wape">
        <p-accordion-header>Cómo leer el error absoluto (WAPE)</p-accordion-header>
        <p-accordion-content>
          <p>Es la suma de los errores dividida entre las unidades vendidas. Un valor bajo indica menos error. Por ejemplo, un WAPE de 0,78 equivale a un error acumulado de alrededor del 78 % del volumen vendido; <strong>no significa 78 % de acierto</strong>.</p>
          <p class="muted">Cuando la comparación no se puede calcular, la pantalla dice «no evaluable»; eso no es un error cero.</p>
        </p-accordion-content>
      </p-accordion-panel>

      <p-accordion-panel value="4" data-testid="help-glossary">
        <p-accordion-header>Glosario</p-accordion-header>
        <p-accordion-content>
          <dl class="kv">
            @for (g of glossary; track g.term) {
              <dt>{{ g.term }}</dt>
              <dd>{{ g.meaning }} <span class="muted">(Término técnico: {{ g.technical }})</span></dd>
            }
          </dl>
        </p-accordion-content>
      </p-accordion-panel>
    </p-accordion>
  `,
  styles: `
    .help-list { list-style: none; padding: 0; margin: 0; display: grid; gap: 0.75rem; }
    .help-list li { display: flex; align-items: flex-start; gap: 0.5rem; }
    :host ::ng-deep .help-list .p-tag { flex-shrink: 0; margin-top: 2px; }
  `,
})
export class HelpPage {
  private auth = inject(AuthService);
  steps = FIRST_STEPS;
  glossary = GLOSSARY;
  reset = signal(false);
  showAgain() { resetOnboarding(this.auth.session()?.username); this.reset.set(true); }
}
