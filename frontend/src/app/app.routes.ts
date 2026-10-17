import { Routes } from '@angular/router';
import { authGuard } from './core/auth.guard';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'resumen' },
  { path: 'acceso', title: 'Acceso', loadComponent: () => import('./pages/login.page').then((m) => m.LoginPage) },
  {
    path: '',
    canActivate: [authGuard],
    children: [
      { path: 'resumen', title: 'Resumen', loadComponent: () => import('./pages/summary.page').then((m) => m.SummaryPage) },
      { path: 'cargas', title: 'Importaciones', loadComponent: () => import('./pages/imports.page').then((m) => m.ImportsPage) },
      { path: 'corridas', title: 'Corridas', loadComponent: () => import('./pages/runs.page').then((m) => m.RunsPage) },
      { path: 'pronosticos', title: 'Pronósticos', loadComponent: () => import('./pages/forecasts.page').then((m) => m.ForecastsPage) },
      { path: 'recomendaciones', title: 'Recomendaciones', loadComponent: () => import('./pages/recommendations.page').then((m) => m.RecommendationsPage) },
      { path: 'comparacion', title: 'Comparación', loadComponent: () => import('./pages/comparison.page').then((m) => m.ComparisonPage) },
      { path: 'sistema', title: 'Estado del sistema', loadComponent: () => import('./pages/system.page').then((m) => m.SystemPage) },
    ],
  },
  { path: '**', redirectTo: 'resumen' },
];
