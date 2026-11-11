import { Injectable, computed, inject } from '@angular/core';
import { ApiService } from './api.service';
import { AuthService } from './services/auth.service';
import { load } from './utils/load';
import { Page, RunSummary } from './models';

/**
 * UX01/R17: lista única de análisis (corridas) compartida por todas las pantallas. Una sola petición a /runs por usuario.
 * - `ensure()` NO es reactivo: no lee señales ni se vuelve a ejecutar por un cambio de estado. Un error de /runs queda
 *   visible y no genera peticiones nuevas hasta una acción explícita (`retry()`/`refresh()`).
 * - La caché se invalida cuando cambia la identidad de la sesión (otro usuario → nueva lectura).
 * - Solo se lee la primera página de 50 análisis (`hasMore` informa si hay más): un identificador ausente de esa página
 *   no se declara «inexistente» cuando `hasMore` es verdadero.
 * Cambiar la selección de la interfaz NO modifica la corrida «en uso por defecto» del servidor.
 */
@Injectable({ providedIn: 'root' })
export class RunsStore {
  private api = inject(ApiService);
  private auth = inject(AuthService);
  private loader = load<Page<RunSummary>>(() => this.api.runs(1, 50), () => false, false);
  private started = false;
  private owner: string | null | undefined = undefined;
  readonly state = this.loader.state;
  readonly runs = computed<RunSummary[]>(() => { const s = this.state(); return s.kind === 'data' ? s.data.items : []; });
  readonly hasMore = computed(() => { const s = this.state(); return s.kind === 'data' && s.data.has_more; });
  readonly defaultRun = computed(() => this.runs().find((r) => r.is_active) ?? null);

  /** Carga la lista una sola vez (por identidad). Sin reintentos automáticos: tras un error espera `retry()`. */
  ensure() {
    const who = this.auth.session()?.username ?? null;
    if (this.owner !== who) { this.owner = who; this.started = false; }
    if (!this.started) { this.started = true; this.loader.reload(); }
  }
  /** Reintento o actualización EXPLÍCITOS (botón «Reintentar», tras crear un análisis). */
  retry() { this.started = true; this.loader.reload(); }
  refresh() { this.retry(); }
  /** El análisis elegido en la dirección (`run`) o, sin él, el que está en uso por defecto. */
  resolve(id: string | null | undefined): RunSummary | null {
    return id ? (this.runs().find((r) => r.run_id === id) ?? null) : this.defaultRun();
  }
}
