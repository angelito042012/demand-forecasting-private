import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../core/auth.service';
import { AppError } from '../core/models';
import { PageHeader } from '../ui/page-header';

@Component({
  selector: 'app-login-page',
  imports: [FormsModule, PageHeader],
  template: `
    <app-page-header title="Acceso" lead="Ingresa con el usuario que te dio el administrador." />
    @if (auth.notice(); as n) {
      <p class="notice warn" role="alert" data-testid="notice">{{ n }}</p>
    }
    <form class="surface" (ngSubmit)="submit()" autocomplete="on" aria-label="Ingresar">
      <label>Usuario <input name="username" [(ngModel)]="username" autocomplete="username" required /></label>
      <label>Contraseña <input name="password" type="password" [(ngModel)]="password" autocomplete="current-password" required /></label>
      <button type="submit" class="btn" [disabled]="busy() || !username || !password">Ingresar</button>
    </form>
    @if (error(); as e) {
      <p class="notice danger" role="alert" data-testid="login-error">{{ message(e) }}</p>
    }
    <p class="muted">¿No tienes usuario? Pídeselo al administrador: no hay registro público.</p>
  `,
  styles: `
    form { display: grid; gap: 0.8rem; max-width: 24rem; }
  `,
})
export class LoginPage {
  protected auth = inject(AuthService);
  private router = inject(Router);
  username = '';
  password = '';
  busy = signal(false);
  error = signal<AppError | null>(null);

  message(e: AppError) {
    if (e.status === 401) return 'Usuario o contraseña incorrectos. Revisa los datos e inténtalo de nuevo.';
    return `${e.message} Si el problema continúa, avisa al administrador.`;
  }

  submit() {
    this.busy.set(true);
    this.error.set(null);
    this.auth.login(this.username.trim(), this.password).subscribe({
      next: () => {
        this.password = '';
        this.busy.set(false);
        this.router.navigate(['/inicio']);
      },
      error: (e: AppError) => {
        this.password = '';
        this.busy.set(false);
        this.error.set(e);
      },
    });
  }
}
