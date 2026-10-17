import { Component, inject } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { DataService, MockScenario } from './core/data.service';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  protected readonly ds = inject(DataService);
  private router = inject(Router);
  protected readonly scenarios: { id: MockScenario; label: string }[] = [
    { id: 'data', label: 'Con datos demo' },
    { id: 'empty', label: 'Sin datos' },
    { id: 'error', label: 'Error' },
    { id: 'slow', label: 'Carga lenta' },
  ];
  protected setScenario(e: Event) {
    this.ds.scenario.set((e.target as HTMLSelectElement).value as MockScenario);
    // Recarga la ruta actual para volver a consultar el servicio.
    const url = this.router.url;
    this.router.navigateByUrl('/', { skipLocationChange: true }).then(() => this.router.navigateByUrl(url));
  }
}
