import { Injectable, computed, inject } from '@angular/core';
import { ApiService } from './api.service';
import { load } from './load';
import { Page, RunSummary } from './models';

/**
 * UX01: lista única de análisis (corridas) compartida por todas las pantallas. Una sola petición a /runs; las pantallas la
 * leen de aquí (nombres, fechas, estado) en lugar de repetirla. Cambiar la selección de la interfaz NO modifica la corrida
 * «en uso por defecto» del servidor: eso solo lo decide el puntero original.
 */
@Injectable({ providedIn: 'root' })
export class RunsStore {
  private api = inject(ApiService);
  private loader = load<Page<RunSummary>>(() => this.api.runs(1, 50), () => false, false);
  private started = false;
  readonly state = this.loader.state;
  readonly runs = computed<RunSummary[]>(() => { const s = this.state(); return s.kind === 'data' ? s.data.items : []; });
  readonly defaultRun = computed(() => this.runs().find((r) => r.is_active) ?? null);

  /** Carga la lista la primera vez (o tras un error); no repite la petición si ya hay datos. */
  ensure() {
    const s = this.state();
    if (!this.started || s.kind === 'error') { this.started = true; this.loader.reload(); }
  }
  /** Vuelve a leer la lista (p. ej. tras crear un análisis). */
  refresh() { this.started = true; this.loader.reload(); }
  /** El análisis elegido en la dirección (`run`) o, sin él, el que está en uso por defecto. */
  resolve(id: string | null | undefined): RunSummary | null {
    return id ? (this.runs().find((r) => r.run_id === id) ?? null) : this.defaultRun();
  }
}
