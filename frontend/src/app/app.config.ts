import { ApplicationConfig, provideBrowserGlobalErrorListeners } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient, withInterceptors } from '@angular/common/http';

import { routes } from './app.routes';
import { apiInterceptor } from './core/http.interceptor';
import { demoInterceptor } from './core/demo';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes),
    // Orden: apiInterceptor (errores/CSRF) envuelve a demoInterceptor (inactivo salvo ?demo=1 en desarrollo).
    provideHttpClient(withInterceptors([apiInterceptor, demoInterceptor])),
  ],
};
