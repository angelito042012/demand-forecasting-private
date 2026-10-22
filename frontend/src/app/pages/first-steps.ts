/**
 * UX01: los tres pasos de «Cómo empezar» (Inicio y Ayuda) y el recuerdo local de su cierre por usuario.
 * El cierre es solo una preferencia de la interfaz: no controla permisos ni oculta funciones.
 */
export const FIRST_STEPS: { title: string; text: string }[] = [
  { title: 'Mira las ventas previstas', text: 'Revisa cuántas unidades se estima vender de cada producto en el mes del plan de compra vigente.' },
  { title: 'Revisa las existencias', text: 'Consulta cuántas unidades había al cierre de la fecha del plan y de dónde sale ese número.' },
  { title: 'Abre la compra recomendada', text: 'Mira cuántas unidades comprar con plazos de entrega de 7 y 14 días, y qué supuestos se usaron.' },
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
