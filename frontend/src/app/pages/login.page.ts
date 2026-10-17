import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../core/auth.service';
import { AppError } from '../core/models';

@Component({
  selector: 'app-login-page',
  imports: [FormsModule],
  template: `
    <h2>Acceso</h2>
    @if (auth.notice(); as n) {
      <p class="notice warn" role="alert" data-testid="notice">{{ n }}</p>
    }
    <form (ngSubmit)="submit()" autocomplete="on">
      <label>Usuario <input name="username" [(ngModel)]="username" autocomplete="username" required /></label>
      <label>Contraseña <input name="password" type="password" [(ngModel)]="password" autocomplete="current-password" required /></label>
      <button type="submit" [disabled]="busy() || !username || !password">Ingresar</button>
    </form>
    @if (error(); as e) {
      <p class="err" role="alert" data-testid="login-error">{{ message(e) }}</p>
    }
    <p class="hint">La cuenta la crea el administrador por línea de comandos; no hay registro público.</p>
  `,
  styles: `
    form { display: grid; gap: 0.6rem; max-width: 22rem; }
    label { display: grid; gap: 0.2rem; }
    .err { color: #842029; }
    .hint { font-size: 0.85rem; color: var(--muted); }
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
    if (e.status === 401) return 'Usuario o contraseña incorrectos.';
    return e.message;
  }

  submit() {
    this.busy.set(true);
    this.error.set(null);
    this.auth.login(this.username.trim(), this.password).subscribe({
      next: () => {
        this.password = '';
        this.busy.set(false);
        this.router.navigate(['/resumen']);
      },
      error: (e: AppError) => {
        this.password = '';
        this.busy.set(false);
        this.error.set(e);
      },
    });
  }
}
