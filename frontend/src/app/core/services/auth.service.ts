import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, catchError, map, of, tap } from 'rxjs';
import { AppError, Session } from '../models';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private http = inject(HttpClient);
  readonly session = signal<Session | null>(null);
  readonly notice = signal<string | null>(null);

  get csrfToken(): string | null {
    return this.session()?.csrf_token ?? null;
  }
  get isAdmin(): boolean {
    return this.session()?.role === 'admin';
  }

  me(): Observable<Session> {
    return this.http.get<Session>(`${environment.apiBase}/auth/me`, { withCredentials: true }).pipe(tap((s) => this.session.set(s)));
  }

  check(): Observable<boolean> {
    return this.me().pipe(
      map(() => true),
      catchError((e: AppError) => {
        if (e.status === 401) {
          this.session.set(null);
          return of(false);
        }
        throw e;
      }),
    );
  }

  login(username: string, password: string): Observable<Session> {
    return this.http
      .post<Session>(`${environment.apiBase}/auth/login`, { username, password }, { withCredentials: true })
      .pipe(tap((s) => { this.session.set(s); this.notice.set(null); }));
  }

  logout(): Observable<void> {
    return this.http.post<void>(`${environment.apiBase}/auth/logout`, {}, { withCredentials: true }).pipe(
      tap(() => this.session.set(null)),
      catchError((e: AppError) => {
        if (e.status === 401) { this.session.set(null); return of(undefined); }
        throw e;
      }),
    );
  }

  clear(notice: string | null = null) {
    this.session.set(null);
    this.notice.set(notice);
  }
}
