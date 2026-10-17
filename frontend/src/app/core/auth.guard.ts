import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { catchError, map, of } from 'rxjs';
import { AuthService } from './auth.service';

/** Consulta GET /auth/me en cada navegación protegida; el servidor es la autoridad. */
export const authGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  return auth.check().pipe(
    map((ok) => (ok ? true : router.createUrlTree(['/acceso']))),
    // Red/503: la pantalla de acceso informa que el servicio no está disponible.
    catchError((e) => {
      auth.notice.set(e?.message ?? 'Servicio no disponible, reintente.');
      return of(router.createUrlTree(['/acceso']));
    }),
  );
};
