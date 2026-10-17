import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, catchError, map, of, tap } from 'rxjs';
import { AppError, Session } from './models';

const BASE = '/api/v1';

/** La sesión real es la cookie HttpOnly; aquí solo hay estado en memoria (incluido el csrf_token). */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private http = inject(HttpClient);
  readonly session = signal<Session | null>(null);
  /** Aviso a mostrar en la pantalla de acceso (p. ej. sesión vencida). */
  readonly notice = signal<string | null>(null);

  get csrfToken(): string | null {
    return this.session()?.csrf_token ?? null;
  }
  /** Solo cosmético: el servidor decide los permisos. */
  get isAdmin(): boolean {
    return this.session()?.role === 'admin';
  }

  me(): Observable<Session> {
    return this.http.get<Session>(`${BASE}/auth/me`, { withCredentials: true }).pipe(tap((s) => this.session.set(s)));
  }

  /** true si hay sesión; false si no. Otros errores (red/503) se propagan. */
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
      .post<Session>(`${BASE}/auth/login`, { username, password }, { withCredentials: true })
      .pipe(tap((s) => { this.session.set(s); this.notice.set(null); }));
  }

  logout(): Observable<void> {
    return this.http.post<void>(`${BASE}/auth/logout`, {}, { withCredentials: true }).pipe(
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
