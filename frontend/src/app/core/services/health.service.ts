import { Injectable } from '@angular/core';
import { ApiBase } from './api-base';
import { Health } from '../models';

@Injectable({ providedIn: 'root' })
export class HealthService extends ApiBase {
  health() { return this.get<Health>('/health'); }
}
