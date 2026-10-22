import { Injectable, computed, inject, signal } from '@angular/core';
import { switchMap, of, map } from 'rxjs';
import { ApiService } from './api.service';
import { isAppError } from './load';
import { AppError, LoadState, PlanHeader, PlanInputs, PlanRef } from './models';

/** Regla ÚNICA para elegir el plan por defecto: el primer elemento de GET /plans del mes (la usa también «Compra recomendada»). */
export function defaultPlanId(items: PlanRef[] | undefined | null): string | null {
  return items?.[0]?.plan_id ?? null;
}

export interface CurrentPlan { month: string; ref: PlanRef; header: PlanHeader; inputs: PlanInputs }

/**
 * Plan de compra VIGENTE compartido por Inicio, Ventas previstas y Compra recomendada.
 * Solo lee lo ya calculado por el servidor (GET /plans/inputs, /plans, /plans/{id}); no calcula nada en el navegador.
 * Se resuelve una vez y se reutiliza; `invalidate()` fuerza una nueva lectura (p. ej. tras generar un plan).
 */
@Injectable({ providedIn: 'root' })
export class CurrentPlanStore {
  private api = inject(ApiService);
  readonly state = signal<LoadState<CurrentPlan>>({ kind: 'loading' });
  readonly plan = computed(() => { const s = this.state(); return s.kind === 'data' ? s.data : null; });
  private started = false;
  private ticket = 0;

  /** Carga si todavía no se cargó o si la última vez falló o quedó vacío. */
  ensure() {
    const k = this.state().kind;
    if (!this.started || k === 'error' || k === 'empty') this.reload();
  }
  invalidate() { this.started = false; }

  reload() {
    this.started = true;
    const mine = ++this.ticket;
    this.state.set({ kind: 'loading' });
    this.api.planInputs().pipe(
      switchMap((inputs) => {
        const month = inputs.defaults?.month;
        if (!month) return of<CurrentPlan | null>(null);
        return this.api.plans(month).pipe(
          map((r) => (Array.isArray(r) ? r : (r.items ?? []))),
          switchMap((items) => {
            const id = defaultPlanId(items);
            const ref = items.find((p) => p.plan_id === id);
            if (!id || !ref) return of<CurrentPlan | null>(null);
            return this.api.plan(id).pipe(map((header) => ({ month, ref, header, inputs })));
          }),
        );
      }),
    ).subscribe({
      next: (p) => { if (mine === this.ticket) this.state.set(p ? { kind: 'data', data: p } : { kind: 'empty' }); },
      error: (e: unknown) => {
        if (mine !== this.ticket) return;
        const err: AppError = isAppError(e) ? e : { status: 0, code: 'DESCONOCIDO', message: 'Ocurrió un error inesperado.' };
        this.state.set({ kind: 'error', error: err });
      },
    });
  }
}
