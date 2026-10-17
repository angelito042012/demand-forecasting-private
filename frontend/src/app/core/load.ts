import { Observable } from 'rxjs';
import { signal, WritableSignal } from '@angular/core';
import { LoadState } from './models';
import { Result } from './data.service';

/** Carga un observable de lista en una señal LoadState (loading/error/empty/data). */
export function load<T>(src: () => Observable<Result<T[]>>): { state: WritableSignal<LoadState<T[]>>; reload: () => void } {
  const state = signal<LoadState<T[]>>({ kind: 'loading' });
  const reload = () => {
    state.set({ kind: 'loading' });
    src().subscribe({
      next: (r) => state.set(r.data.length === 0 ? { kind: 'empty' } : { kind: 'data', data: r.data, provenance: r.provenance }),
      error: (e: unknown) => state.set({ kind: 'error', message: e instanceof Error ? e.message : 'Error desconocido' }),
    });
  };
  reload();
  return { state, reload };
}
