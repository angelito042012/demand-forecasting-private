import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  BacktestDetail, BacktestItem, BacktestView, ForecastPage, GroupBy, Health, ImportDetail, ImportItem, Page,
  ImportAccepted, JobType, ReportedInventoryPage, ReportedSnapshotRef, ReportedView, PublicJob, Recommendation, RecoPage, RunAccepted, RunDetail, RunOptions, RunSummary, SalesSummary, JobStatus,
} from './models';

const BASE = '/api/v1';

export type Query = Record<string, string | number | boolean | null | undefined>;

/** Construye parámetros omitiendo vacíos. */
export function toParams(q: Query): HttpParams {
  let p = new HttpParams();
  for (const [k, v] of Object.entries(q)) {
    if (v === null || v === undefined || v === '' || v === false) continue;
    p = p.set(k, String(v));
  }
  return p;
}

export interface ForecastQuery {
  run_id?: string; level: 'sku' | 'categoria'; sku?: string; categoria?: string; cohorte?: string;
  from?: string; to?: string; page: number; page_size: number; sort?: string;
}
export interface RecoQuery {
  run_id?: string; categoria?: string; sku?: string; status?: 'ok' | 'sin_snapshot' | ''; only_orders?: boolean;
  /** UX01: solo SKU con inventario simulado y pedido sugerido 0 (filtro del servidor). */
  no_orders?: boolean;
  page: number; page_size: number; sort?: string;
}

export interface ReportedQuery { snapshot_id?: string; q?: string; view?: ReportedView; sort?: string; page: number; page_size: number }

@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);
  private get<T>(path: string, q: Query = {}): Observable<T> {
    return this.http.get<T>(`${BASE}${path}`, { params: toParams(q), withCredentials: true });
  }

  health() { return this.get<Health>('/health'); }
  imports(page: number, page_size: number, mes?: string) { return this.get<Page<ImportItem>>('/imports', { page, page_size, mes }); }
  importDetail(id: string) { return this.get<ImportDetail>(`/imports/${encodeURIComponent(id)}`); }
  salesSummary(from: string, to: string, group_by: GroupBy, categoria?: string) {
    return this.get<SalesSummary>('/sales/summary', { from, to, group_by, categoria });
  }
  runs(page: number, page_size: number) { return this.get<Page<RunSummary>>('/runs', { page, page_size }); }
  runDetail(id: string) { return this.get<RunDetail>(`/runs/${encodeURIComponent(id)}`); }
  forecasts(q: ForecastQuery) { return this.get<ForecastPage>('/forecasts', { ...q }); }
  recommendations(q: RecoQuery) { return this.get<RecoPage>('/recommendations', { ...q }); }
  recommendation(sku: string, run_id?: string, almacen = '1') {
    return this.get<Recommendation>(`/recommendations/${encodeURIComponent(sku)}`, { run_id, almacen });
  }
  backtests(run_id?: string) { return this.get<BacktestItem[] | Page<BacktestItem>>('/backtests', { run_id }); }
  backtest(id: string, view: BacktestView = 'all') {
    return this.get<BacktestDetail>(`/backtests/${encodeURIComponent(id)}`, { view });
  }

  // ---- T18: inventario informado (solo lectura) ----
  reportedInventory(q: ReportedQuery) { return this.get<ReportedInventoryPage>('/inventory/reported', { ...q, view: q.view === 'all' ? undefined : q.view }); }
  reportedInventorySnapshots() { return this.get<ReportedSnapshotRef[] | Page<ReportedSnapshotRef>>('/inventory/reported/snapshots'); }

  // ---- T10 ----
  runOptions() { return this.get<RunOptions>('/runs/options'); }
  jobs(q: { page: number; page_size: number; status?: JobStatus; type?: JobType }) { return this.get<Page<PublicJob>>('/jobs', { ...q }); }
  job(id: string) { return this.get<PublicJob>(`/jobs/${encodeURIComponent(id)}`); }
  /** Multipart: el navegador fija Content-Type con su boundary (nunca se establece a mano). */
  uploadImport(file: File): Observable<ImportAccepted> {
    const fd = new FormData();
    fd.append('file', file, file.name);
    return this.http.post<ImportAccepted>(`${BASE}/imports`, fd, { withCredentials: true });
  }
  createRun(body: { origin: string; horizon_days: number; method: string }): Observable<RunAccepted> {
    return this.http.post<RunAccepted>(`${BASE}/runs`, body, { withCredentials: true });
  }
}
