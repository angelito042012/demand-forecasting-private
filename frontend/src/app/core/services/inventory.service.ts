import { Injectable } from '@angular/core';
import { ApiBase, Query } from './api-base';
import { ReportedInventoryPage, ReportedSnapshotRef, ReportedView, Page, StockPage } from '../models';

export interface ReportedQuery { snapshot_id?: string; q?: string; view?: ReportedView; sort?: string; page: number; page_size: number }
export interface StockQuery { snapshot_id?: string; q?: string; view?: 'discrepancias'; sort?: string; page: number; page_size: number }

@Injectable({ providedIn: 'root' })
export class InventoryService extends ApiBase {
  reported(q: ReportedQuery) { return this.get<ReportedInventoryPage>('/inventory/reported', { ...q, view: q.view === 'all' ? undefined : q.view } as Query); }
  reportedSnapshots() { return this.get<ReportedSnapshotRef[] | Page<ReportedSnapshotRef>>('/inventory/reported/snapshots'); }
  stock(q: StockQuery) { return this.get<StockPage>('/stock', { ...q } as Query); }
}
