import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { catchError, map, of } from 'rxjs';
import { AuthService } from '../services/auth.service';

export const authGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  return auth.check().pipe(
    map((ok) => (ok ? true : router.createUrlTree(['/acceso']))),
    catchError((e) => {
      auth.notice.set(e?.message ?? 'Servicio no disponible, reintente.');
      return of(router.createUrlTree(['/acceso']));
    }),
  );
};
