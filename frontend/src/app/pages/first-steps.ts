/**
 * UX01: los tres pasos de «Cómo empezar» (Inicio y Ayuda) y el recuerdo local de su cierre por usuario.
 * El cierre es solo una preferencia de la interfaz: no controla permisos ni oculta funciones.
 */
export const FIRST_STEPS: { title: string; text: string }[] = [
  { title: 'Elige un análisis', text: 'Empieza con el ejemplo que ya está en uso por defecto o cambia de análisis en «Mis análisis».' },
  { title: 'Consulta las ventas previstas', text: 'Elige un producto y revisa las unidades estimadas para las fechas del ejemplo.' },
  { title: 'Explora la reposición simulada', text: 'Abre una sugerencia para ver con qué se contó, qué se buscó cubrir y de dónde sale la cantidad.' },
];

const key = (user: string | null | undefined) => `ux01.comoempezar.cerrado.${user || 'anonimo'}`;

/** true si este usuario ya cerró la ayuda inicial en este navegador (si el almacenamiento falla, se vuelve a mostrar). */
export function onboardingClosed(user: string | null | undefined): boolean {
  try { return localStorage.getItem(key(user)) === '1'; } catch { return false; }
}
export function closeOnboarding(user: string | null | undefined): void {
  try { localStorage.setItem(key(user), '1'); } catch { /* sin almacenamiento: se mostrará de nuevo */ }
}
export function resetOnboarding(user: string | null | undefined): void {
  try { localStorage.removeItem(key(user)); } catch { /* sin almacenamiento */ }
}
