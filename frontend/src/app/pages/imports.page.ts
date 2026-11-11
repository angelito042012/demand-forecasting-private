import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ApiService } from '../core/api.service';
import { load } from '../core/utils/load';
import { AppError, ImportDetail, ImportItem, Page } from '../core/models';
import { AuthService } from '../core/services/auth.service';
import { JobBoard } from '../core/jobs';
import { JobsPanel } from '../shared/components/jobs-panel';
import { PageHeader } from '../shared/components/page-header';
import { StatePanel } from '../shared/components/state-panel';
import { Pager } from '../shared/components/pager';
import { DataTree } from '../shared/components/data-tree';
import { fmtInt } from '../core/utils/format';
import { ButtonModule } from 'primeng/button';
import { MessageModule } from 'primeng/message';
import { TableModule } from 'primeng/table';
import { StepperModule } from 'primeng/stepper';
import { FileUploadModule } from 'primeng/fileupload';
import { PanelModule } from 'primeng/panel';

export const MAX_UPLOAD_BYTES = 25 * 1024 * 1024;

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
  imports: [RouterLink, PageHeader, StatePanel, Pager, DataTree, JobsPanel, ButtonModule, MessageModule, TableModule, StepperModule, FileUploadModule, PanelModule],
  template: `
    @if (isAdmin) {
      <app-page-header title="Cargar datos" lead="Sube el Excel mensual de ventas y revisa qué se aceptó. Cargar no crea análisis ni cambia los ya publicados." />
      <p-message severity="info" data-testid="imports-scope" styleClass="w-full mb-3">
        <div>
          <p><strong>Para qué sirve esta carga.</strong> Alimenta los <strong>análisis históricos</strong> del ejemplo (ventas de enero a septiembre de 2026). Los demás meses no se aceptan: es una regla del servidor.</p>
          <p><strong>No actualiza el plan de compra de noviembre.</strong> Ese plan usa ventas hasta el 20/10 y existencias al cierre del 20/10, y los incorpora el soporte técnico con un procedimiento aparte (ver Ayuda). Desde «Compra recomendada» el administrador sí puede generar otra versión del plan con otros parámetros.</p>
        </div>
      </p-message>

      <div class="stepper" aria-label="Pasos para cargar datos" data-testid="upload-steps">
        <div class="step"><span class="step-num">1</span> <strong>Elegir archivo</strong> <span class="muted">un Excel mensual (.xlsx)</span></div>
        <div class="step"><span class="step-num">2</span> <strong>Revisar el resultado</strong> <span class="muted">qué se aceptó y qué se rechazó</span></div>
        <div class="step"><span class="step-num">3</span> <strong>Consultar</strong> <span class="muted">las <a [routerLink]="['/resumen']" queryParamsHandling="preserve" data-testid="step-sales">ventas registradas</a> o la <a [routerLink]="['/evaluacion/ventas-previstas']" queryParamsHandling="preserve" data-testid="step-forecast">previsión del ejemplo</a></span></div>
      </div>

      <p-panel header="1. Elegir el archivo" data-testid="upload-section" styleClass="mb-3">
        <p class="muted">Un archivo .xlsx mensual con ventas de enero a septiembre de 2026 (hasta 25 MiB). El navegador solo avisa de forma temprana: el servidor revisa el contenido y decide. El procesamiento ocurre en segundo plano; puedes recargar esta página sin perder el trabajo.</p>
        <form class="flex flex-wrap align-items-center gap-3 mt-3" (submit)="$event.preventDefault(); upload()" aria-label="Cargar archivo">
          <label class="file-label">Archivo .xlsx <input type="file" accept=".xlsx" data-testid="file-input" (change)="pick($event)" /></label>
          <p-button type="submit" label="Subir y procesar" icon="pi pi-upload" [disabled]="!file() || !!warning() || sending()" [loading]="sending()" data-testid="upload-btn" />
        </form>
        @if (warning(); as w) { <p-message severity="warn" [text]="w" role="alert" data-testid="file-warning" styleClass="w-full mt-3" /> }
        @if (uploadError(); as e) { <p-message severity="error" [text]="e" role="alert" data-testid="upload-error" styleClass="w-full mt-3" /> }
        @if (reusedNote()) { <p-message severity="info" text="Este archivo ya había sido enviado: se sigue el mismo trabajo, no se duplica." data-testid="reused-note" styleClass="w-full mt-3" /> }
      </p-panel>
      <h2>2. Revisar el resultado</h2>
      <app-jobs-panel [jobs]="board.jobs()" [listError]="board.listError()" [pollError]="board.pollError()" (openImport)="openById($event)" />
    } @else {
      <app-page-header title="Datos cargados" lead="Archivos de ventas que ya se cargaron en la aplicación." />
      <p-message severity="info" text="Esta pantalla es de solo lectura: muestra los archivos ya cargados. Solo el administrador puede cargar archivos." data-testid="readonly-note" styleClass="w-full mb-3" />
    }

    <h2>Archivos cargados</h2>
    <app-state-panel [state]="l.state()" emptyText="Todavía no hay archivos cargados." (retry)="l.reload()">
      @if (data(); as d) {
        <p-table [value]="d.items" styleClass="p-datatable-sm p-datatable-striped" data-testid="imports-table">
          <ng-template #header>
            <tr>
              <th>Archivo</th><th>Mes</th><th>Estado</th>
              <th class="text-right">Ventas aceptadas</th><th class="text-right">Rechazadas</th><th><span class="sr-only">Acción</span></th>
            </tr>
          </ng-template>
          <ng-template #body let-r>
            <tr>
              <td>{{ r.archivo }}</td><td>{{ r.mes }}</td><td>{{ r.estado }}</td>
              <td class="text-right">{{ int(r.ventas_aceptadas) }}</td><td class="text-right">{{ int(r.rechazadas) }}</td>
              <td><p-button label="Ver detalle" icon="pi pi-eye" [text]="true" size="small" (onClick)="open(r)" [attr.aria-label]="'Ver detalle de ' + r.archivo" /></td>
            </tr>
          </ng-template>
        </p-table>
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
    .sr-only { position: absolute; width: 1px; height: 1px; margin: -1px; padding: 0; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0; }
    .stepper { display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 0.8rem 0 1rem; }
    .step { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); padding: 0.5rem 1rem; flex: 1; min-width: 12rem; display: flex; align-items: center; gap: 0.5rem; }
    .step-num { background: var(--accent); color: var(--accent-ink); width: 1.6rem; height: 1.6rem; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.85rem; flex-shrink: 0; }
    .file-label { font-weight: 600; }
  `,
})
export class ImportsPage {
  private api = inject(ApiService);
  private auth = inject(AuthService);
  private destroyRef = inject(DestroyRef);
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
  selected = signal<string | null>(null);
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
