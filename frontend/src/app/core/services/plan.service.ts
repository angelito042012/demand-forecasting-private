import { Injectable } from '@angular/core';
import { ApiBase, Query } from './api-base';
import { PlanInputs, PlanRef, PlanList, PlanHeader, PlanResultsPage, PlanResultDetail, PlanCreateBody, PlanAccepted, PlanCompareResponse } from '../models';

export interface PlanQuery { q?: string; status?: string; sort?: string; page: number; page_size: number }

@Injectable({ providedIn: 'root' })
export class PlanService extends ApiBase {
  inputs() { return this.get<PlanInputs>('/plans/inputs'); }
  list(month?: string) { return this.get<PlanRef[] | PlanList>('/plans', { month }); }
  detail(id: string) { return this.get<PlanHeader>(`/plans/${encodeURIComponent(id)}`); }
  results(id: string, q: PlanQuery) { return this.get<PlanResultsPage>(`/plans/${encodeURIComponent(id)}/results`, { ...q } as Query); }
  result(id: string, producto_id: string) {
    return this.get<PlanResultDetail>(`/plans/${encodeURIComponent(id)}/results/${encodeURIComponent(producto_id)}`);
  }
  compare(a: string, b: string) {
    return this.get<PlanCompareResponse>(`/plans/${encodeURIComponent(a)}/compare/${encodeURIComponent(b)}`);
  }
  create(body: PlanCreateBody) {
    return this.post<PlanAccepted>('/plans', body);
  }
}
