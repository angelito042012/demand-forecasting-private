import { Injectable } from '@angular/core';
import { ApiBase } from './api-base';
import { Page, PublicJob, JobStatus, JobType } from '../models';

@Injectable({ providedIn: 'root' })
export class JobService extends ApiBase {
  list(q: { page: number; page_size: number; status?: JobStatus; type?: JobType }) { return this.get<Page<PublicJob>>('/jobs', { ...q }); }
  detail(id: string) { return this.get<PublicJob>(`/jobs/${encodeURIComponent(id)}`); }
}
