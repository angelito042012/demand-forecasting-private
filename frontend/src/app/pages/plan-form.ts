import { Component, OnInit, computed, input, output, signal } from '@angular/core';
import { PlanCreateBody, PlanInputs, PlanNature, PlanPendingOrder } from '../core/models';
import { fmtDate } from '../core/format';
import { longDate, monthName } from '../core/ux-text';
import { NATURE_LABELS } from './plan-text';

const ISO = /^\d{4}-\d{2}-\d{2}$/;
const INT = /^\d+$/;

/** Formulario del administrador: arma el cuerpo de POST /plans. La validación previa es ayuda; el servidor decide. */
@Component({
  selector: 'app-plan-form',
  template: `
    <section class="surface" aria-labelledby="h-plan-form" data-testid="plan-form">
      <h2 id="h-plan-form">Generar o cambiar un plan</h2>
      <p class="muted">Cambia los supuestos y genera un plan nuevo. Si los datos son idénticos a un plan existente, se reutiliza ese plan.</p>
      <form class="filters" (submit)="$event.preventDefault(); submit()" aria-label="Generar plan de compra">
        <label>Mes a cubrir
          <select name="month" data-testid="pf-month" [value]="month()" (change)="month.set($any($event.target).value)">
            @for (m of months(); track m) { <option [value]="m" [selected]="m === month()">{{ monthLabel(m) }}</option> }
          </select>
        </label>
        <label>Fecha de decisión
          <input type="date" name="decision" data-testid="pf-decision" [min]="limits()?.decision_min ?? null" [max]="limits()?.decision_max ?? null"
            [value]="decision()" (input)="decision.set($any($event.target).value)" />
        </label>
        <label>Plazos de entrega en días (hasta {{ limits()?.max_leads ?? 4 }}, separados por coma)
          <input type="text" name="leads" inputmode="numeric" autocomplete="off" data-testid="pf-leads" [value]="leadsText()" (input)="leadsText.set($any($event.target).value)" />
        </label>
        <label>Reserva al terminar el mes (días)
          <input type="number" name="reserve" min="0" max="30" step="1" data-testid="pf-reserve" [value]="reserve()" (input)="reserve.set($any($event.target).value)" />
        </label>
        <label>Compra mínima (unidades)
          <input type="number" name="min" min="1" step="1" data-testid="pf-min" [value]="minOrder()" (input)="minOrder.set($any($event.target).value)" />
        </label>
        <label>Múltiplo de compra (unidades)
          <input type="number" name="mult" min="1" step="1" data-testid="pf-multiple" [value]="multiple()" (input)="multiple.set($any($event.target).value)" />
        </label>
        <button type="submit" class="btn" data-testid="plan-generate" [disabled]="errors().length > 0 || sending()">Generar plan</button>
      </form>
      @if (errors().length) {
        <ul class="plain notice warn" role="status" data-testid="pf-errors">@for (e of errors(); track e) { <li>{{ e }}</li> }</ul>
      }

      <h3>Pedidos por recibir</h3>
      <p class="notice info" data-testid="pf-assumption">
        @if (orders().length === 0) { <strong>No llegan otros pedidos (supuesto).</strong> Por ahora no se declaró ninguno: no se informó si hay pedidos en camino, así que el plan supone que no llega ninguno. }
        @else { <strong>Se consideran los pedidos declarados abajo; no llegan otros adicionales (supuesto).</strong> }
      </p>
      @if (orders().length) {
        <ul class="plain" data-testid="pf-orders">
          @for (o of orders(); track $index) {
            <li data-testid="pf-order">
              Producto <strong>{{ o.producto_id }}</strong> · {{ o.units }} unidades · llega el {{ date(o.arrival_date) }} · {{ nature(o.nature) }}
              <button type="button" class="secondary small" data-testid="pf-order-remove" (click)="remove($index)">Quitar</button>
            </li>
          }
        </ul>
      }
      <div class="filters" role="group" aria-label="Añadir un pedido por recibir">
        <label>Código del producto
          <input type="text" name="ocode" autocomplete="off" maxlength="40" data-testid="po-code" [value]="oCode()" (input)="oCode.set($any($event.target).value)" />
        </label>
        <label>Unidades
          <input type="number" name="ounits" min="1" step="1" data-testid="po-units" [value]="oUnits()" (input)="oUnits.set($any($event.target).value)" />
        </label>
        <label>Fecha de llegada
          <input type="date" name="oarr" data-testid="po-arrival" [min]="orderMin()" [value]="oArrival()" (input)="oArrival.set($any($event.target).value)" />
        </label>
        <label>Naturaleza
          <select name="onat" data-testid="po-nature" [value]="oNature()" (change)="oNature.set($any($event.target).value)">
            <option value="REPORTADA" [selected]="oNature() === 'REPORTADA'">Reportada</option>
            <option value="ASUMIDA" [selected]="oNature() === 'ASUMIDA'">Asumida</option>
          </select>
        </label>
        <button type="button" class="secondary" data-testid="po-add" (click)="addOrder()">Agregar pedido</button>
      </div>
      @if (orderError(); as e) { <p class="notice warn" role="alert" data-testid="po-error">{{ e }}</p> }
    </section>
  `,
})
export class PlanForm implements OnInit {
  readonly inputs = input.required<PlanInputs>();
  readonly sending = input(false);
  readonly submitted = output<PlanCreateBody>();

  month = signal('');
  decision = signal('');
  leadsText = signal('');
  reserve = signal('');
  minOrder = signal('');
  multiple = signal('');
  orders = signal<PlanPendingOrder[]>([]);
  oCode = signal('');
  oUnits = signal('');
  oArrival = signal('');
  oNature = signal<PlanNature>('REPORTADA');
  orderError = signal<string | null>(null);

  limits = computed(() => this.inputs().limits ?? null);
  months = computed(() => this.limits()?.months ?? (this.month() ? [this.month()] : []));
  /** Un pedido por recibir debe llegar después de la fecha del conteo. */
  orderMin = computed(() => {
    const d = /^(\d{4}-\d{2}-\d{2})/.exec(this.inputs().snapshot?.as_of_local ?? '')?.[1];
    return d ? d : null;
  });

  readonly date = fmtDate;
  nature = (n: string) => NATURE_LABELS[n] ?? n;
  monthLabel = (m: string) => { const n = monthName(`${m}-01`); return n ? `${n} de ${m.slice(0, 4)}` : m; };

  ngOnInit() {
    const d = this.inputs().defaults;
    if (!d) return;
    this.month.set(d.month);
    this.decision.set(d.decision_date);
    this.leadsText.set(d.lead_days.join(', '));
    this.reserve.set(String(d.reserve_days));
    this.minOrder.set(String(d.min_order));
    this.multiple.set(String(d.order_multiple));
    this.orders.set([...(d.pending_orders ?? [])]);
  }

  private leads(): number[] | null {
    const parts = this.leadsText().split(/[\s,;]+/).filter(Boolean);
    if (!parts.length || !parts.every((p) => INT.test(p))) return null;
    return parts.map(Number);
  }

  errors = computed(() => {
    const e: string[] = [];
    const lim = this.limits();
    if (!this.month()) e.push('Elige el mes que quieres cubrir.');
    const dec = this.decision();
    if (!ISO.test(dec)) e.push('Indica la fecha de decisión.');
    else if (lim && (dec < lim.decision_min || dec > lim.decision_max)) {
      e.push(`La fecha de decisión debe estar entre el ${longDate(lim.decision_min)} y el ${longDate(lim.decision_max)}.`);
    }
    const ls = this.leads();
    const lmin = lim?.lead_min ?? 1; const lmax = lim?.lead_max ?? 60; const maxN = lim?.max_leads ?? 4;
    if (!ls) e.push('Escribe los plazos de entrega como números enteros de días, por ejemplo: 7, 14.');
    else if (ls.length > maxN || new Set(ls).size !== ls.length) e.push(`Indica entre 1 y ${maxN} plazos distintos.`);
    else if (ls.some((n) => n < lmin || n > lmax)) e.push(`Cada plazo debe estar entre ${lmin} y ${lmax} días.`);
    const r = this.reserve();
    if (!INT.test(r) || Number(r) > 30) e.push('La reserva debe ser un número entero de días entre 0 y 30.');
    if (!INT.test(this.minOrder()) || Number(this.minOrder()) < 1) e.push('La compra mínima debe ser un entero de 1 o más.');
    if (!INT.test(this.multiple()) || Number(this.multiple()) < 1) e.push('El múltiplo de compra debe ser un entero de 1 o más.');
    return e;
  });

  addOrder() {
    const code = this.oCode().trim();
    const units = this.oUnits();
    const arrival = this.oArrival();
    if (!code) return this.orderError.set('Indica el código del producto.');
    if (!INT.test(units) || Number(units) < 1) return this.orderError.set('Las unidades deben ser un entero de 1 o más.');
    if (!ISO.test(arrival)) return this.orderError.set('Indica la fecha de llegada: sin fecha no se admite el pedido.');
    const min = this.orderMin();
    if (min && arrival <= min) return this.orderError.set(`La llegada debe ser posterior a la fecha del conteo (${fmtDate(min)}).`);
    this.orderError.set(null);
    this.orders.update((o) => [...o, { producto_id: code, units: Number(units), arrival_date: arrival, nature: this.oNature() }]);
    this.oCode.set(''); this.oUnits.set(''); this.oArrival.set('');
  }

  remove(i: number) { this.orders.update((o) => o.filter((_, k) => k !== i)); }

  submit() {
    const ls = this.leads();
    if (this.errors().length || !ls || this.sending()) return;
    this.submitted.emit({
      month: this.month(), decision_date: this.decision(), lead_days: ls,
      reserve_days: Number(this.reserve()), min_order: Number(this.minOrder()), order_multiple: Number(this.multiple()),
      pending_orders: this.orders(),
    });
  }
}
