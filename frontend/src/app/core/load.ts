import { Observable } from 'rxjs';
import { signal, WritableSignal } from '@angular/core';
import { AppError, LoadState } from './models';

export interface Loader<T> {
  state: WritableSignal<LoadState<T>>;
  /** Vuelve a ejecutar la consulta (siempre con la fuente actual). */
  reload: () => void;
}

/**
 * Ejecuta una consulta y mantiene el estado cargando/error/vacío/datos.
 * `isEmpty` decide cuándo no hay datos; un error NUNCA se convierte en datos de relleno.
 */
export function load<T>(src: () => Observable<T>, isEmpty: (d: T) => boolean = () => false, autoStart = true): Loader<T> {
  const state = signal<LoadState<T>>({ kind: 'loading' });
  let ticket = 0;
  const reload = () => {
    const mine = ++ticket;
    state.set({ kind: 'loading' });
    src().subscribe({
      next: (d) => { if (mine === ticket) state.set(isEmpty(d) ? { kind: 'empty' } : { kind: 'data', data: d }); },
      error: (e: unknown) => {
        if (mine !== ticket) return;
        const err: AppError = isAppError(e) ? e : { status: 0, code: 'DESCONOCIDO', message: 'Ocurrió un error inesperado.' };
        state.set({ kind: 'error', error: err });
      },
    });
  };
  if (autoStart) reload();
  return { state, reload };
}

export function isAppError(e: unknown): e is AppError {
  return typeof e === 'object' && e !== null && 'code' in e && 'message' in e && 'status' in e;
}

export function dataOf<T>(s: LoadState<T>): T | null {
  return s.kind === 'data' ? s.data : null;
}
