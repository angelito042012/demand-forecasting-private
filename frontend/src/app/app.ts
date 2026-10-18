import { Component, inject, signal } from '@angular/core';
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

  constructor() {
    this.router.events.pipe(filter((e) => e instanceof NavigationEnd)).subscribe(() => this.menuOpen.set(false));
  }

  protected toggleMenu() { this.menuOpen.update((v) => !v); }

  protected logout() {
    const done = () => this.router.navigate(['/acceso']);
    this.auth.logout().subscribe({ next: done, error: () => { this.auth.clear('No se pudo confirmar la salida; si el servicio no responde, cierre el navegador.'); done(); } });
  }
}
