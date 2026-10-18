import { Routes } from '@angular/router';
import { authGuard } from './core/auth.guard';

/**
 * UX01: los nombres de ruta heredados se conservan (enlaces y parámetro `run`); solo cambian los textos del menú.
 * resumen = Ventas registradas · cargas = Cargar datos/Datos cargados · corridas = Mis análisis · pronosticos = Ventas previstas
 * recomendaciones = Reposición simulada · comparacion = Evaluación de resultados · sistema = Estado del sistema.
 */
export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'inicio' },
  { path: 'acceso', title: 'Acceso', loadComponent: () => import('./pages/login.page').then((m) => m.LoginPage) },
  {
    path: '',
    canActivate: [authGuard],
    children: [
      { path: 'inicio', title: 'Inicio', loadComponent: () => import('./pages/home.page').then((m) => m.HomePage) },
      { path: 'ayuda', title: 'Ayuda', loadComponent: () => import('./pages/help.page').then((m) => m.HelpPage) },
      { path: 'resumen', title: 'Ventas registradas', loadComponent: () => import('./pages/summary.page').then((m) => m.SummaryPage) },
      { path: 'cargas', title: 'Datos cargados', loadComponent: () => import('./pages/imports.page').then((m) => m.ImportsPage) },
      { path: 'crear-analisis', title: 'Crear análisis', loadComponent: () => import('./pages/create-run.page').then((m) => m.CreateRunPage) },
      { path: 'corridas', title: 'Mis análisis', loadComponent: () => import('./pages/runs.page').then((m) => m.RunsPage) },
      { path: 'pronosticos', title: 'Ventas previstas', loadComponent: () => import('./pages/forecasts.page').then((m) => m.ForecastsPage) },
      { path: 'recomendaciones', title: 'Reposición simulada', loadComponent: () => import('./pages/recommendations.page').then((m) => m.RecommendationsPage) },
      { path: 'comparacion', title: 'Evaluación de resultados', loadComponent: () => import('./pages/comparison.page').then((m) => m.ComparisonPage) },
      { path: 'sistema', title: 'Estado del sistema', loadComponent: () => import('./pages/system.page').then((m) => m.SystemPage) },
    ],
  },
  { path: '**', redirectTo: 'inicio' },
];
