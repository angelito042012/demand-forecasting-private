import { Injectable } from '@angular/core';
import { ApiBase } from './api-base';
import { GroupBy, SalesSummary } from '../models';

@Injectable({ providedIn: 'root' })
export class SalesService extends ApiBase {
  summary(from: string, to: string, group_by: GroupBy, categoria?: string) {
    return this.get<SalesSummary>('/sales/summary', { from, to, group_by, categoria });
  }
}
