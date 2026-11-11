import { Injectable } from '@angular/core';
import { ApiBase, Query } from './api-base';
import { ForecastPage, RecoPage, Recommendation, BacktestItem, BacktestDetail, BacktestView, Page } from '../models';

export interface ForecastQuery {
  run_id?: string; level: 'sku' | 'categoria'; sku?: string; categoria?: string; cohorte?: string;
  from?: string; to?: string; page: number; page_size: number; sort?: string;
}

export interface RecoQuery {
  run_id?: string; categoria?: string; sku?: string; status?: 'ok' | 'sin_snapshot' | ''; only_orders?: boolean;
  no_orders?: boolean;
  page: number; page_size: number; sort?: string;
}

@Injectable({ providedIn: 'root' })
export class ForecastService extends ApiBase {
  forecasts(q: ForecastQuery) { return this.get<ForecastPage>('/forecasts', { ...q } as Query); }
  recommendations(q: RecoQuery) { return this.get<RecoPage>('/recommendations', { ...q } as Query); }
  recommendation(sku: string, run_id?: string, almacen = '1') {
    return this.get<Recommendation>(`/recommendations/${encodeURIComponent(sku)}`, { run_id, almacen });
  }
  backtests(run_id?: string) { return this.get<BacktestItem[] | Page<BacktestItem>>('/backtests', { run_id }); }
  backtest(id: string, view: BacktestView = 'all') {
    return this.get<BacktestDetail>(`/backtests/${encodeURIComponent(id)}`, { view });
  }
}
