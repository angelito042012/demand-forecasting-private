import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { Role } from '../models';

export function roleGuard(...allowed: Role[]): CanActivateFn {
  return () => {
    const auth = inject(AuthService);
    const router = inject(Router);
    const session = auth.session();
    if (!session) return router.createUrlTree(['/acceso']);
    return allowed.includes(session.role) || router.createUrlTree(['/inicio']);
  };
}
