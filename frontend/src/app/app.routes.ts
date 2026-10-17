import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'cargas' },
  { path: 'cargas', title: 'Cargas de datos', loadComponent: () => import('./pages/imports.page').then((m) => m.ImportsPage) },
  { path: 'pronosticos', title: 'Pronósticos', loadComponent: () => import('./pages/forecasts.page').then((m) => m.ForecastsPage) },
  { path: 'recomendaciones', title: 'Recomendaciones', loadComponent: () => import('./pages/recommendations.page').then((m) => m.RecommendationsPage) },
  { path: 'sistema', title: 'Estado del sistema', loadComponent: () => import('./pages/system.page').then((m) => m.SystemPage) },
  { path: '**', redirectTo: 'cargas' },
];
