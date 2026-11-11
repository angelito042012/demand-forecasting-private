import { inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export type Query = Record<string, string | number | boolean | null | undefined>;

export function toParams(q: Query): HttpParams {
  let p = new HttpParams();
  for (const [k, v] of Object.entries(q)) {
    if (v === null || v === undefined || v === '' || v === false) continue;
    p = p.set(k, String(v));
  }
  return p;
}

export abstract class ApiBase {
  protected http = inject(HttpClient);

  protected get<T>(path: string, q: Query = {}): Observable<T> {
    return this.http.get<T>(`${environment.apiBase}${path}`, { params: toParams(q), withCredentials: true });
  }

  protected post<T>(path: string, body: unknown): Observable<T> {
    return this.http.post<T>(`${environment.apiBase}${path}`, body, { withCredentials: true });
  }
}
