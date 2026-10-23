import { Component, computed, inject, signal } from '@angular/core';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { filter } from 'rxjs';
import { AuthService } from './core/auth.service';
import { DemoMode } from './core/demo';
import { DemoBanner } from './ui/notices';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, DemoBanner],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  protected readonly auth = inject(AuthService);
  protected readonly demo = inject(DemoMode);
  private router = inject(Router);
  /** Menú desplegable en pantallas estrechas; se cierra al navegar. */
  protected readonly menuOpen = signal(false);
  private readonly url = signal('');
  /** En «Inventario informado» la franja no puede decir «simulado»: esa pantalla muestra el conteo de la empresa. */
  protected readonly onInventory = computed(() => /^\/inventario(\/|\?|$)/.test(this.url()));
  /** T19: Planificar compras tampoco puede hablar de inventario simulado. */
  protected readonly onPlan = computed(() => /^\/planificar(\/|\?|$)/.test(this.url()));
  /** Pantallas con aviso propio de una línea (Compra recomendada, Ventas previstas, Existencias): no repiten la franja global. */
  protected readonly ownNotice = computed(() => /^\/(planificar|pronosticos|existencias|sistema|ayuda|acceso)(\/|\?|$)/.test(this.url()));
  /** Carga de datos y Ventas registradas: datos históricos del análisis (marzo–julio); no hablan de inventario simulado ni del plan operativo. */
  protected readonly onHistoricalSales = computed(() => /^\/(cargas|resumen)(\/|\?|$)/.test(this.url()));

  /** T20: «Existencias» (existencia reconstruida). */
  protected readonly onStock = computed(() => /^\/existencias(\/|\?|$)/.test(this.url()));
  /** T20: la evaluación histórica con inventario simulado está separada del flujo principal. */
  protected readonly onAcademic = computed(() => /^\/recomendaciones(\/|\?|$)/.test(this.url()));

  /** Inicio y Ventas previstas muestran el plan vigente (no el ejemplo histórico). */
  protected readonly onCurrentPlan = computed(() => /^\/(inicio|pronosticos)(\/|\?|$)/.test(this.url()));

  constructor() {
    this.router.events.pipe(filter((e): e is NavigationEnd => e instanceof NavigationEnd)).subscribe((e) => { this.menuOpen.set(false); this.url.set(e.urlAfterRedirects); });
  }

  protected toggleMenu() { this.menuOpen.update((v) => !v); }

  protected logout() {
    const done = () => this.router.navigate(['/acceso']);
    this.auth.logout().subscribe({ next: done, error: () => { this.auth.clear('No se pudo confirmar la salida; si el servicio no responde, cierre el navegador.'); done(); } });
  }
}
