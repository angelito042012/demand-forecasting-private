import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ApiService } from '../core/api.service';
import { load } from '../core/load';
import { AppError, ImportDetail, ImportItem, Page } from '../core/models';
import { AuthService } from '../core/auth.service';
import { JobBoard } from '../core/jobs';
import { JobsPanel } from '../ui/jobs-panel';
import { PageHeader } from '../ui/page-header';
import { StatePanel } from '../ui/state-panel';
import { Pager } from '../ui/pager';
import { DataTree } from '../ui/data-tree';
import { fmtInt } from '../core/format';

export const MAX_UPLOAD_BYTES = 25 * 1024 * 1024;

/** Aviso temprano en el cliente; el servidor decide siempre. */
export function earlyWarning(f: { name: string; size: number } | null): string | null {
  if (!f) return null;
  if (!f.name.toLowerCase().endsWith('.xlsx')) return 'El archivo debe tener extensión .xlsx. Elige el Excel mensual de ventas.';
  if (f.size > MAX_UPLOAD_BYTES) return 'El archivo supera 25 MiB; el servidor lo rechazará. Elige un archivo más pequeño.';
  if (f.size === 0) return 'El archivo está vacío. Elige otro archivo.';
  return null;
}

export function uploadErrorText(e: AppError): string {
  if (e.status === 413) return 'El servidor rechazó el archivo por tamaño (máximo 25 MiB). Elige un archivo más pequeño.';
  if (e.status === 415) return 'El servidor rechazó el archivo: no es un .xlsx válido. Elige el Excel mensual de ventas.';
  if (e.status === 422) return `El servidor rechazó el contenido del archivo: ${e.message} Revisa el archivo y vuelve a intentarlo.`;
  if (e.status === 403) return 'No tienes permiso para cargar archivos o tu sesión ya no es válida. Ingresa de nuevo con el usuario del administrador.';
  return `${e.message} Puedes volver a intentarlo.`;
}

@Component({
  selector: 'app-imports-page',
  imports: [RouterLink, PageHeader, StatePanel, Pager, DataTree, JobsPanel],
  template: `
    @if (isAdmin) {
      <app-page-header title="Cargar datos" lead="Sube el Excel mensual de ventas y revisa qué se aceptó. Cargar no crea análisis ni cambia los ya publicados." />
      <section class="notice info" data-testid="imports-scope" role="note">
        <p><strong>Para qué sirve esta carga.</strong> Alimenta los <strong>análisis históricos</strong> del ejemplo (ventas de marzo a julio de 2026). Agosto de 2026 queda reservado para la prueba final y los demás meses no se aceptan: es una regla del servidor, no un texto desactualizado.</p>
        <p><strong>No actualiza el plan de compra de noviembre.</strong> Ese plan usa ventas hasta el 20/10 y existencias al cierre del 20/10, y los incorpora el soporte técnico con un procedimiento aparte (ver Ayuda). Desde «Compra recomendada» el administrador sí puede generar otra versión del plan con otros parámetros.</p>
      </section>
      <ol class="stepper" aria-label="Pasos para cargar datos" data-testid="upload-steps">
        <li><strong>1. Elegir archivo</strong> <span class="muted">un Excel mensual (.xlsx)</span></li>
        <li><strong>2. Revisar el resultado</strong> <span class="muted">qué se aceptó y qué se rechazó</span></li>
        <li><strong>3. Consultar</strong> <span class="muted">las <a [routerLink]="['/resumen']" queryParamsHandling="preserve" data-testid="step-sales">ventas registradas</a> o la <a [routerLink]="['/evaluacion/ventas-previstas']" queryParamsHandling="preserve" data-testid="step-forecast">previsión del ejemplo</a></span></li>
      </ol>
      <section class="surface" aria-labelledby="h-up" data-testid="upload-section">
        <h2 id="h-up">1. Elegir el archivo</h2>
        <p class="muted">Un archivo .xlsx mensual con ventas de marzo a julio de 2026 (hasta 25 MiB). Agosto de 2026 está reservado: la carga general no acepta ventas de ese mes. El navegador solo avisa de forma temprana: el servidor revisa el contenido y decide. El procesamiento ocurre en segundo plano; puedes recargar esta página sin perder el trabajo.</p>
        <form class="filters" (submit)="$event.preventDefault(); upload()" aria-label="Cargar archivo">
          <label>Archivo .xlsx <input type="file" accept=".xlsx" data-testid="file-input" (change)="pick($event)" /></label>
          <button type="submit" class="btn" data-testid="upload-btn" [disabled]="!file() || !!warning() || sending()">Subir y procesar</button>
        </form>
        @if (warning(); as w) { <p class="notice warn" role="alert" data-testid="file-warning">{{ w }}</p> }
        @if (uploadError(); as e) { <p class="notice danger" role="alert" data-testid="upload-error">{{ e }}</p> }
        @if (reusedNote()) { <p class="notice info" data-testid="reused-note">Este archivo ya había sido enviado: se sigue el mismo trabajo, no se duplica.</p> }
      </section>
      <h2>2. Revisar el resultado</h2>
      <app-jobs-panel [jobs]="board.jobs()" [listError]="board.listError()" [pollError]="board.pollError()" (openImport)="openById($event)" />
    } @else {
      <app-page-header title="Datos cargados" lead="Archivos de ventas que ya se cargaron en la aplicación." />
      <p class="notice info" data-testid="readonly-note">Esta pantalla es de solo lectura: muestra los archivos ya cargados. Solo el administrador puede cargar archivos.</p>
    }
    <h2>Archivos cargados</h2>
    <app-state-panel [state]="l.state()" emptyText="Todavía no hay archivos cargados." (retry)="l.reload()">
      @if (data(); as d) {
        <div class="table-wrap" tabindex="0" role="region" aria-label="Tabla de archivos cargados">
        <table data-testid="imports-table">
          <thead><tr><th scope="col">Archivo</th><th scope="col">Mes</th><th scope="col">Estado</th><th scope="col" class="num">Ventas aceptadas</th><th scope="col" class="num">Rechazadas</th><th scope="col"><span class="sr-only">Acción</span></th></tr></thead>
          <tbody>
            @for (r of d.items; track r.import_id) {
              <tr>
                <td>{{ r.archivo }}</td><td>{{ r.mes }}</td><td>{{ r.estado }}</td>
                <td class="num">{{ int(r.ventas_aceptadas) }}</td><td class="num">{{ int(r.rechazadas) }}</td>
                <td><button type="button" class="secondary small" (click)="open(r)" [attr.aria-label]="'Ver detalle de ' + r.archivo">Ver detalle</button></td>
              </tr>
            }
          </tbody>
        </table>
        </div>
        <app-pager [page]="d.page" [pageSize]="d.page_size" [total]="d.total" [hasMore]="d.has_more" (go)="go($event)" />
      }
    </app-state-panel>
    @if (selected(); as s) {
      <h2 data-testid="import-detail-title">Detalle de {{ s }}</h2>
      @if (row(); as r) {
        <ul class="plain" data-testid="import-counts">
          <li>Filas leídas: <strong>{{ int(r.filas_leidas) }}</strong></li>
          <li>Notas de crédito: <strong>{{ int(r.notas_credito) }}</strong></li>
          <li>Insertadas: <strong>{{ int(r.insertadas) }}</strong> · ya existentes: <strong>{{ int(r.ya_existentes) }}</strong> · en conflicto: <strong>{{ int(r.en_conflicto) }}</strong></li>
        </ul>
      }
      <app-state-panel [state]="detail.state()" (retry)="detail.reload()">
        <details class="tech" open><summary>Detalles técnicos de la carga</summary><app-data-tree [value]="detailData()" /></details>
      </app-state-panel>
    }
  `,
  styles: `
    .stepper { display: grid; gap: 0.4rem; list-style: none; padding: 0; margin: 0.6rem 0 1rem; }
    .stepper li { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); padding: 0.5rem 0.9rem; }
  `,
})
export class ImportsPage {
  private api = inject(ApiService);
  private auth = inject(AuthService);
  private destroyRef = inject(DestroyRef);
  /** Solo cosmético: el servidor rechaza igual cualquier escritura del lector. */
  isAdmin = this.auth.isAdmin;
  file = signal<File | null>(null);
  warning = signal<string | null>(null);
  sending = signal(false);
  uploadError = signal<string | null>(null);
  reusedNote = signal(false);
  board = new JobBoard(this.api, 'import_excel', () => this.l.reload(), this.destroyRef);
  int = (v: unknown) => fmtInt(v);
  page = signal(1);
  pageSize = 50;
  l = load<Page<ImportItem>>(() => this.api.imports(this.page(), this.pageSize), (d) => d.items.length === 0);
  data = computed(() => { const s = this.l.state(); return s.kind === 'data' ? s.data : null; });
  /** Etiqueta mostrada del detalle abierto y su id. */
  selected = signal<string | null>(null);
  /** Fila de la lista del detalle abierto (null si se abrió desde un trabajo). */
  row = signal<ImportItem | null>(null);
  private selectedId = signal<string | null>(null);
  detail = load<ImportDetail>(() => this.api.importDetail(this.selectedId()!), () => false, false);
  detailData = computed(() => { const s = this.detail.state(); return s.kind === 'data' ? s.data : null; });

  go(p: number) { this.page.set(p); this.l.reload(); }
  open(r: ImportItem) { this.row.set(r); this.selected.set(r.archivo); this.selectedId.set(r.import_id); this.detail.reload(); }
  openById(id: string) { this.row.set(null); this.selected.set(id); this.selectedId.set(id); this.detail.reload(); }

  constructor() {
    if (this.isAdmin) this.board.loadRecent();
  }

  pick(ev: Event) {
    const f = (ev.target as HTMLInputElement).files?.[0] ?? null;
    this.file.set(f);
    this.warning.set(earlyWarning(f));
    this.uploadError.set(null);
    this.reusedNote.set(false);
  }

  upload() {
    const f = this.file();
    if (!f || this.warning() || this.sending()) return;
    this.sending.set(true);
    this.uploadError.set(null);
    this.api.uploadImport(f).subscribe({
      next: (r) => {
        this.sending.set(false);
        this.reusedNote.set(!!r.reused);
        this.board.track(r.job_id, r.status);
      },
      error: (e: AppError) => { this.sending.set(false); this.uploadError.set(uploadErrorText(e)); },
    });
  }
}
