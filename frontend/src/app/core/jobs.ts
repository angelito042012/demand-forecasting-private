import { DestroyRef, signal } from '@angular/core';
import { ApiService } from './api.service';
import { AppError, JobStatus, JobType, PublicJob } from './models';
import { isAppError } from './utils/load';

export const POLL_MS = 2000;

export function isFinal(s: JobStatus | string | undefined): boolean {
  return s === 'completed' || s === 'failed';
}

export const STAGE_LABELS: Record<string, string> = {
  queued: 'En cola', running: 'En ejecución', validating: 'Validando el archivo', scanning: 'Revisando fechas',
  importing: 'Importando', reading: 'Leyendo el archivo', loading: 'Cargando historia', forecasting: 'Calculando las ventas previstas',
  recommending: 'Calculando la reposición simulada', publishing: 'Publicando', validating_publication: 'Validando la publicación',
};
export const PROGRESS_LABELS: Record<string, string> = {
  filas_leidas: 'Filas leídas', ventas: 'Ventas', notas_credito: 'Notas de crédito', rechazadas: 'Rechazadas', en_conflicto: 'En conflicto',
  insertadas: 'Insertadas', ya_existentes: 'Ya existentes', skus: 'Productos', skus_procesados: 'Productos procesados', pronosticos: 'Ventas previstas',
  recomendaciones: 'Sugerencias de reposición', categorias: 'Categorías',
};

export function stageLabel(j: PublicJob): string {
  if (j.stage) return STAGE_LABELS[j.stage] ?? j.stage;
  return STAGE_LABELS[j.status] ?? j.status;
}

/** Conteos reales publicados por el worker; solo valores escalares (nunca se calcula un porcentaje). */
export function progressEntries(j: PublicJob): [string, string][] {
  const p = j.progress;
  if (!p || typeof p !== 'object') return [];
  return Object.entries(p)
    .filter(([, v]) => typeof v === 'number' || typeof v === 'string')
    .map(([k, v]) => [PROGRESS_LABELS[k] ?? k, String(v)] as [string, string]);
}

export const STATUS_LABELS: Record<JobStatus, string> = { queued: 'Esperando turno', running: 'En curso', completed: 'Terminado', failed: 'No se pudo completar' };
export const TYPE_LABELS: Record<JobType, string> = { import_excel: 'Carga de un archivo Excel', generate_run: 'Creación de un análisis', generate_plan: 'Cálculo de un plan de compra' };

export const REJECT_MOTIVES: Record<string, string> = {
  FECHAS_FUERA_DE_ALCANCE: 'El archivo tiene fechas fuera del alcance del proyecto (enero a septiembre de 2026). No se cargó nada: revisa el mes del archivo.',
  MES_CON_FUENTE_APROBADA:
    'Ese mes ya tiene una fuente aprobada distinta. El archivo no se cargó ni sustituyó la fuente vigente: la sustitución no se hace desde esta pantalla y sigue el procedimiento de remediación documentado (docs/REMEDIACION_FUENTES.md).',
  ARCHIVO_INVALIDO: 'El archivo no es un Excel (.xlsx) válido o no tiene la estructura esperada. Revisa que sea el archivo mensual de ventas.',
  ARCHIVO_INVALIDO_O_CORRUPTO: 'El archivo no es un Excel (.xlsx) válido o está dañado.',
  ENCABEZADOS_INVALIDOS: 'El archivo no tiene los encabezados esperados.',
  WORKER_PERDIDO: 'El procesamiento se interrumpió y agotó sus reintentos. Puedes volver a intentarlo.',
  CORTE_FUERA_DE_RANGO: 'La fecha elegida está fuera del rango permitido. Elige otra fecha.',
  ARTEFACTO_SIMULACION_NO_DISPONIBLE: 'Falta el artefacto verificado de la simulación; se publican las ventas previstas sin sugerencias de reposición.',
};

export interface JobSummary {
  tone: 'run' | 'ok' | 'neutral' | 'bad';
  title: string;
  /** Explicación en español (motivo del rechazo o descripción). */
  detail?: string;
  /** Pares etiqueta / valor reales del resultado. */
  counts: [string, string][];
  rejectMotives: [string, number][];
  importId?: string;
  runId?: string;
}

/** Id al final de un enlace relativo del contrato («/imports/<id>», «/runs/<id>»). */
export function idFromLink(link: string | null | undefined): string | undefined {
  if (!link) return undefined;
  const last = link.split('/').filter(Boolean).pop();
  return last ? decodeURIComponent(last) : undefined;
}

/** Texto legible del estado/resultado de un trabajo. No inventa cifras: solo muestra lo que el trabajo publica. */
export function summarize(j: PublicJob): JobSummary {
  const base: JobSummary = { tone: 'neutral', title: '', counts: [], rejectMotives: [] };
  if (j.status === 'queued' || j.status === 'running') {
    return { ...base, tone: 'run', title: j.status === 'queued' ? 'Esperando turno' : 'En curso', counts: progressEntries(j) };
  }
  const isImport = j.type === 'import_excel';
  if (j.status === 'failed') {
    const code = j.error?.code ?? '';
    const known = REJECT_MOTIVES[code];
    const detail = known
      ?? (isImport
        ? 'El archivo no pudo cargarse. Revisa que sea el Excel mensual (.xlsx) y vuelve a intentarlo; si se repite, avisa al administrador.'
        : 'El análisis no pudo crearse. Vuelve a intentarlo; si se repite, avisa al administrador.');
    return { ...base, tone: 'bad', title: isImport && known ? 'Rechazado' : 'No se pudo completar', detail, importId: idFromLink(j.links?.import) };
  }
  const r = j.result ?? {};
  if (!isImport) {
    return { ...base, tone: 'ok', title: 'Análisis creado', runId: r.run_id ?? idFromLink(j.links?.run) };
  }
  const importId = r.import_id ?? idFromLink(j.links?.import);
  if (r.outcome === 'sin_cambios') {
    return { ...base, title: 'Sin cambios (archivo ya cargado)', detail: 'Este archivo ya estaba cargado; no se modificó ningún dato.', importId };
  }
  const counts: [string, string][] = [];
  const add = (label: string, v: unknown) => { if (typeof v === 'number') counts.push([label, String(v)]); };
  add('Filas leídas', r.filas_leidas); add('Ventas', r.ventas); add('Notas de crédito', r.notas_credito);
  add('Rechazadas', r.rechazadas); add('En conflicto', r.en_conflicto);
  const motives = Object.entries(r.rechazos_por_motivo ?? {}).filter(([, n]) => typeof n === 'number') as [string, number][];
  return { ...base, tone: 'ok', title: 'Importado', counts, rejectMotives: motives, importId };
}

/**
 * Tablero de trabajos de un tipo: carga los recientes (GET /jobs) y consulta cada trabajo
 * queued/running con GET /jobs/{id} cada 2 s. Se detiene al llegar a completed/failed y al destruir la página.
 */
export class JobBoard {
  readonly jobs = signal<PublicJob[]>([]);
  readonly listError = signal<AppError | null>(null);
  readonly pollError = signal<AppError | null>(null);
  readonly loading = signal(false);
  private timer: ReturnType<typeof setInterval> | null = null;
  private inflight = new Set<string>();
  private abandoned = new Set<string>();
  private dead = false;

  constructor(private api: ApiService, private type: JobType, private onFinished: (j: PublicJob) => void, destroyRef: DestroyRef) {
    destroyRef.onDestroy(() => this.stop());
  }

  loadRecent() {
    this.loading.set(true);
    this.api.jobs({ page: 1, page_size: 10, type: this.type }).subscribe({
      next: (p) => {
        this.loading.set(false);
        this.listError.set(null);
        for (const j of [...p.items].reverse()) this.upsert(j);
        this.ensurePolling();
        for (const j of this.active()) this.poll(j.job_id);
      },
      error: (e: unknown) => {
        this.loading.set(false);
        this.listError.set(toErr(e));
      },
    });
  }

  /** Empieza a seguir un trabajo recién creado: consulta de inmediato y luego cada 2 s. */
  track(jobId: string, status: JobStatus = 'queued') {
    this.upsert({ job_id: jobId, type: this.type, status });
    this.abandoned.delete(jobId);
    this.poll(jobId);
    this.ensurePolling();
  }

  stop() {
    this.dead = true;
    if (this.timer !== null) { clearInterval(this.timer); this.timer = null; }
  }

  private active(): PublicJob[] {
    return this.jobs().filter((j) => !isFinal(j.status) && !this.abandoned.has(j.job_id));
  }

  private upsert(j: PublicJob) {
    const cur = this.jobs();
    const i = cur.findIndex((x) => x.job_id === j.job_id);
    if (i < 0) { this.jobs.set([j, ...cur]); return; }
    const next = cur.slice();
    next[i] = { ...next[i], ...j };
    this.jobs.set(next);
  }

  private ensurePolling() {
    if (this.dead) return;
    const need = this.active().length > 0;
    if (need && this.timer === null) this.timer = setInterval(() => this.tick(), POLL_MS);
    if (!need && this.timer !== null) { clearInterval(this.timer); this.timer = null; }
  }

  private tick() {
    for (const j of this.active()) this.poll(j.job_id);
  }

  private poll(id: string) {
    if (this.inflight.has(id) || this.dead) return;
    this.inflight.add(id);
    this.api.job(id).subscribe({
      next: (j) => {
        this.inflight.delete(id);
        this.pollError.set(null);
        this.upsert(j);
        if (isFinal(j.status)) this.onFinished(j);
        this.ensurePolling();
      },
      error: (e: unknown) => {
        this.inflight.delete(id);
        const err = toErr(e);
        this.pollError.set(err);
        // Sin sesión, sin permiso o trabajo inexistente: seguir consultando no sirve.
        if ([401, 403, 404].includes(err.status)) { this.abandoned.add(id); this.ensurePolling(); }
      },
    });
  }
}

function toErr(e: unknown): AppError {
  return isAppError(e) ? e : { status: 0, code: 'DESCONOCIDO', message: 'Ocurrió un error inesperado.' };
}
