import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { ApiService } from '../core/api.service';
import { load } from '../core/load';
import { AppError, ImportDetail, ImportItem, Page } from '../core/models';
import { AuthService } from '../core/auth.service';
import { JobBoard } from '../core/jobs';
import { JobsPanel } from '../ui/jobs-panel';
import { StatePanel } from '../ui/state-panel';
import { Pager } from '../ui/pager';
import { DataTree } from '../ui/data-tree';
import { fmtInt } from '../core/format';

export const MAX_UPLOAD_BYTES = 25 * 1024 * 1024;

/** Aviso temprano en el cliente; el servidor decide siempre. */
export function earlyWarning(f: { name: string; size: number } | null): string | null {
  if (!f) return null;
  if (!f.name.toLowerCase().endsWith('.xlsx')) return 'El archivo debe tener extensión .xlsx.';
  if (f.size > MAX_UPLOAD_BYTES) return 'El archivo supera 25 MiB; el servidor lo rechazará.';
  if (f.size === 0) return 'El archivo está vacío.';
  return null;
}

export function uploadErrorText(e: AppError): string {
  if (e.status === 413) return 'El servidor rechazó el archivo por tamaño (máximo 25 MiB).';
  if (e.status === 415) return 'El servidor rechazó el archivo: no es un .xlsx válido.';
  if (e.status === 422) return `El servidor rechazó el contenido del archivo: ${e.message}`;
  if (e.status === 403) return 'No tiene permiso para cargar archivos o su sesión no es válida para esta acción.';
  return e.message;
}

@Component({
  selector: 'app-imports-page',
  imports: [StatePanel, Pager, DataTree, JobsPanel],
  template: `
    <h2>Importaciones</h2>
    @if (isAdmin) {
      <section class="upload" aria-labelledby="h-up" data-testid="upload-section">
        <h3 id="h-up">Cargar un archivo Excel</h3>
        <p class="muted">Un archivo .xlsx mensual (marzo a julio de 2026; hasta 25 MiB). El navegador solo avisa de forma temprana: el servidor valida el contenido y decide. El procesamiento ocurre en segundo plano y puede recargar esta página sin perder el trabajo.</p>
        <form (submit)="$event.preventDefault(); upload()" aria-label="Cargar archivo">
          <label>Archivo .xlsx <input type="file" accept=".xlsx" data-testid="file-input" (change)="pick($event)" /></label>
          <button type="submit" data-testid="upload-btn" [disabled]="!file() || !!warning() || sending()">Subir y procesar</button>
        </form>
        @if (warning(); as w) { <p class="notice warn" role="alert" data-testid="file-warning">{{ w }}</p> }
        @if (uploadError(); as e) { <p class="notice danger" role="alert" data-testid="upload-error">{{ e }}</p> }
        @if (reusedNote()) { <p class="notice info" data-testid="reused-note">Este archivo ya había sido enviado: se sigue el mismo trabajo, no se duplica.</p> }
      </section>
      <h3>Trabajos de importación recientes</h3>
      <app-jobs-panel [jobs]="board.jobs()" [listError]="board.listError()" [pollError]="board.pollError()" (openImport)="openById($event)" />
    } @else {
      <p class="notice info" data-testid="readonly-note">Esta pantalla es de solo lectura para su rol. La carga de archivos está reservada al administrador.</p>
    }
    <app-state-panel [state]="l.state()" emptyText="Todavía no hay importaciones registradas." (retry)="l.reload()">
      @if (data(); as d) {
        <div class="table-wrap" tabindex="0" role="region" aria-label="Tabla de importaciones">
        <table data-testid="imports-table">
          <thead><tr><th scope="col">Archivo</th><th scope="col">Mes</th><th scope="col">Estado</th><th scope="col" class="num">Filas leídas</th><th scope="col" class="num">Ventas aceptadas</th><th scope="col" class="num">Notas de crédito</th><th scope="col" class="num">Rechazadas</th><th scope="col" class="num">Insertadas</th><th scope="col" class="num">Ya existentes</th><th scope="col" class="num">En conflicto</th><th scope="col"><span class="sr-only">Acción</span></th></tr></thead>
          <tbody>
            @for (r of d.items; track r.import_id) {
              <tr>
                <td>{{ r.archivo }}</td><td>{{ r.mes }}</td><td>{{ r.estado }}</td><td class="num">{{ int(r.filas_leidas) }}</td>
                <td class="num">{{ int(r.ventas_aceptadas) }}</td><td class="num">{{ int(r.notas_credito) }}</td><td class="num">{{ int(r.rechazadas) }}</td>
                <td class="num">{{ int(r.insertadas) }}</td><td class="num">{{ int(r.ya_existentes) }}</td><td class="num">{{ int(r.en_conflicto) }}</td>
                <td><button type="button" (click)="open(r)">Ver detalle</button></td>
              </tr>
            }
          </tbody>
        </table>
        </div>
        <app-pager [page]="d.page" [pageSize]="d.page_size" [total]="d.total" [hasMore]="d.has_more" (go)="go($event)" />
      }
    </app-state-panel>
    @if (selected(); as s) {
      <h3 data-testid="import-detail-title">Detalle de {{ s }}</h3>
      <app-state-panel [state]="detail.state()" (retry)="detail.reload()">
        <details class="tech" open><summary>Detalle técnico de la importación</summary><app-data-tree [value]="detailData()" /></details>
      </app-state-panel>
    }
  `,
  styles: `.upload { border: 1px solid var(--line); border-radius: 4px; padding: 0.5rem 0.9rem; margin: 0.6rem 0; } .sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }`,
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
  private selectedId = signal<string | null>(null);
  detail = load<ImportDetail>(() => this.api.importDetail(this.selectedId()!), () => false, false);
  detailData = computed(() => { const s = this.detail.state(); return s.kind === 'data' ? s.data : null; });

  go(p: number) { this.page.set(p); this.l.reload(); }
  open(r: ImportItem) { this.selected.set(r.archivo); this.selectedId.set(r.import_id); this.detail.reload(); }
  openById(id: string) { this.selected.set(id); this.selectedId.set(id); this.detail.reload(); }

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
