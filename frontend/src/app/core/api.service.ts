import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import {
  BacktestDetail, BacktestItem, BacktestView, ForecastPage, GroupBy, Health, ImportDetail, ImportItem, Page,
  ImportAccepted, JobType, ReportedInventoryPage, ReportedSnapshotRef, PublicJob, Recommendation, RecoPage, RunAccepted, RunDetail, RunOptions, RunSummary, SalesSummary, JobStatus,
  PlanInputs, PlanList, PlanRef, PlanHeader, PlanResultsPage, PlanResultDetail, PlanCreateBody, PlanAccepted, PlanCompareResponse, StockPage,
} from './models';
import { HealthService } from './services/health.service';
import { ImportService } from './services/import.service';
import { SalesService } from './services/sales.service';
import { RunService } from './services/run.service';
import { ForecastService } from './services/forecast.service';
import { JobService } from './services/job.service';
import { InventoryService } from './services/inventory.service';
import { PlanService } from './services/plan.service';

export { toParams } from './services/api-base';
export type { Query } from './services/api-base';
export type { ForecastQuery, RecoQuery } from './services/forecast.service';
export type { PlanQuery } from './services/plan.service';
export type { StockQuery, ReportedQuery } from './services/inventory.service';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private _health = inject(HealthService);
  private _import = inject(ImportService);
  private _sales = inject(SalesService);
  private _run = inject(RunService);
  private _forecast = inject(ForecastService);
  private _job = inject(JobService);
  private _inventory = inject(InventoryService);
  private _plan = inject(PlanService);

  health() { return this._health.health(); }

  imports(page: number, page_size: number, mes?: string) { return this._import.list(page, page_size, mes); }
  importDetail(id: string) { return this._import.detail(id); }
  uploadImport(file: File): Observable<ImportAccepted> { return this._import.upload(file); }

  salesSummary(from: string, to: string, group_by: GroupBy, categoria?: string) {
    return this._sales.summary(from, to, group_by, categoria);
  }

  runs(page: number, page_size: number) { return this._run.list(page, page_size); }
  runDetail(id: string) { return this._run.detail(id); }
  runOptions() { return this._run.options(); }
  createRun(body: { origin: string; horizon_days: number; method: string }): Observable<RunAccepted> {
    return this._run.create(body);
  }

  forecasts(q: import('./services/forecast.service').ForecastQuery) { return this._forecast.forecasts(q); }
  recommendations(q: import('./services/forecast.service').RecoQuery) { return this._forecast.recommendations(q); }
  recommendation(sku: string, run_id?: string, almacen = '1') { return this._forecast.recommendation(sku, run_id, almacen); }
  backtests(run_id?: string) { return this._forecast.backtests(run_id); }
  backtest(id: string, view: BacktestView = 'all') { return this._forecast.backtest(id, view); }

  reportedInventory(q: import('./services/inventory.service').ReportedQuery) { return this._inventory.reported(q); }
  reportedInventorySnapshots() { return this._inventory.reportedSnapshots(); }
  stock(q: import('./services/inventory.service').StockQuery) { return this._inventory.stock(q); }

  jobs(q: { page: number; page_size: number; status?: JobStatus; type?: JobType }) { return this._job.list(q); }
  job(id: string) { return this._job.detail(id); }

  planInputs() { return this._plan.inputs(); }
  plans(month?: string) { return this._plan.list(month); }
  plan(id: string) { return this._plan.detail(id); }
  planResults(id: string, q: import('./services/plan.service').PlanQuery) { return this._plan.results(id, q); }
  planResult(id: string, producto_id: string) { return this._plan.result(id, producto_id); }
  comparePlans(a: string, b: string) { return this._plan.compare(a, b); }
  createPlan(body: PlanCreateBody): Observable<PlanAccepted> { return this._plan.create(body); }
}
