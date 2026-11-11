import { Component, computed, inject, signal } from '@angular/core';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { filter } from 'rxjs';
import { AuthService } from './core/services/auth.service';
import { DemoMode } from './core/interceptors';
import { DemoBanner } from './shared/components/notices';
import { ButtonModule } from 'primeng/button';
import { ToolbarModule } from 'primeng/toolbar';
import { DrawerModule } from 'primeng/drawer';
import { AvatarModule } from 'primeng/avatar';
import { RippleModule } from 'primeng/ripple';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, DemoBanner, ButtonModule, ToolbarModule, DrawerModule, AvatarModule, RippleModule],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  protected readonly auth = inject(AuthService);
  protected readonly demo = inject(DemoMode);
  private router = inject(Router);
  protected readonly menuOpen = signal(false);
  private readonly url = signal('');
  protected readonly onInventory = computed(() => /^\/inventario(\/|\?|$)/.test(this.url()));
  protected readonly onPlan = computed(() => /^\/planificar(\/|\?|$)/.test(this.url()));
  protected readonly ownNotice = computed(() => /^\/(planificar|pronosticos|existencias|sistema|ayuda|acceso)(\/|\?|$)/.test(this.url()));
  protected readonly onHistoricalSales = computed(() => /^\/(cargas|resumen)(\/|\?|$)/.test(this.url()));
  protected readonly onStock = computed(() => /^\/existencias(\/|\?|$)/.test(this.url()));
  protected readonly onAcademic = computed(() => /^\/recomendaciones(\/|\?|$)/.test(this.url()));
  protected readonly onCurrentPlan = computed(() => /^\/(inicio|pronosticos)(\/|\?|$)/.test(this.url()));

  protected readonly userInitial = computed(() => {
    const s = this.auth.session();
    return s ? s.username.charAt(0).toUpperCase() : '?';
  });

  constructor() {
    this.router.events.pipe(filter((e): e is NavigationEnd => e instanceof NavigationEnd)).subscribe((e) => { this.menuOpen.set(false); this.url.set(e.urlAfterRedirects); });
  }

  protected toggleMenu() { this.menuOpen.update((v) => !v); }

  protected logout() {
    const done = () => this.router.navigate(['/acceso']);
    this.auth.logout().subscribe({ next: done, error: () => { this.auth.clear('No se pudo confirmar la salida; si el servicio no responde, cierre el navegador.'); done(); } });
  }
}
