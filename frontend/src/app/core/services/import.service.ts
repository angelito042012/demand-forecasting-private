import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiBase } from './api-base';
import { Page, ImportItem, ImportDetail, ImportAccepted } from '../models';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class ImportService extends ApiBase {
  list(page: number, page_size: number, mes?: string) { return this.get<Page<ImportItem>>('/imports', { page, page_size, mes }); }
  detail(id: string) { return this.get<ImportDetail>(`/imports/${encodeURIComponent(id)}`); }
  upload(file: File): Observable<ImportAccepted> {
    const fd = new FormData();
    fd.append('file', file, file.name);
    return this.http.post<ImportAccepted>(`${environment.apiBase}/imports`, fd, { withCredentials: true });
  }
}
