import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';
import { toAppError } from '../utils/errors';

const MUTATIONS = ['POST', 'PUT', 'PATCH', 'DELETE'];

export const apiInterceptor: HttpInterceptorFn = (req, next) => {
  if (!req.url.startsWith('/api/')) return next(req);
  const auth = inject(AuthService);
  const router = inject(Router);
  const isLogin = req.url.endsWith('/auth/login');
  const isMe = req.url.endsWith('/auth/me');

  let r = req.clone({ withCredentials: true });
  const csrf = auth.csrfToken;
  if (MUTATIONS.includes(req.method) && !isLogin && csrf) {
    r = r.clone({ setHeaders: { 'X-CSRF-Token': csrf } });
  }
  return next(r).pipe(
    catchError((e: unknown) => {
      if (!(e instanceof HttpErrorResponse)) return throwError(() => e);
      const err = toAppError(e);
      if (err.status === 401 && !isLogin) {
        auth.clear(err.code === 'SESION_EXPIRADA' ? 'Su sesión venció. Ingrese de nuevo.' : null);
        if (!isMe) router.navigate(['/acceso']);
      }
      return throwError(() => err);
    }),
  );
};
