import { Injectable } from '@angular/core';
import { ApiBase } from './api-base';
import { Page, RunSummary, RunDetail, RunAccepted, RunOptions } from '../models';

@Injectable({ providedIn: 'root' })
export class RunService extends ApiBase {
  list(page: number, page_size: number) { return this.get<Page<RunSummary>>('/runs', { page, page_size }); }
  detail(id: string) { return this.get<RunDetail>(`/runs/${encodeURIComponent(id)}`); }
  options() { return this.get<RunOptions>('/runs/options'); }
  create(body: { origin: string; horizon_days: number; method: string }) {
    return this.post<RunAccepted>('/runs', body);
  }
}
