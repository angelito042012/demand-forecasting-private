import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../core/services/auth.service';
import { AppError } from '../core/models';
import { InputTextModule } from 'primeng/inputtext';
import { PasswordModule } from 'primeng/password';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { MessageModule } from 'primeng/message';

@Component({
  selector: 'app-login-page',
  imports: [FormsModule, InputTextModule, PasswordModule, ButtonModule, CardModule, MessageModule],
  template: `
    <div class="login-container">
      <p-card class="login-card">
        <ng-template #header>
          <div class="login-header">
            <i class="pi pi-lock"></i>
            <h1>Acceso</h1>
            <p>Ingresa con el usuario que te dio el administrador.</p>
          </div>
        </ng-template>
        @if (auth.notice(); as n) {
          <p-message severity="warn" [text]="n" data-testid="notice" styleClass="w-full mb-3" />
        }
        <form (ngSubmit)="submit()" autocomplete="on" aria-label="Ingresar" class="login-form">
          <div class="field">
            <label for="username">Usuario</label>
            <input pInputText id="username" name="username" [(ngModel)]="username" autocomplete="username" required class="w-full" />
          </div>
          <div class="field">
            <label for="password">Contraseña</label>
            <p-password id="password" name="password" [(ngModel)]="password" autocomplete="current-password" required [feedback]="false" [toggleMask]="true" styleClass="w-full" inputStyleClass="w-full" />
          </div>
          <p-button type="submit" label="Ingresar" icon="pi pi-sign-in" [disabled]="busy() || !username || !password" [loading]="busy()" styleClass="w-full" />
        </form>
        @if (error(); as e) {
          <p-message severity="error" [text]="message(e)" data-testid="login-error" styleClass="w-full mt-3" />
        }
        <ng-template #footer>
          <p class="login-footer"><i class="pi pi-info-circle mr-1"></i> ¿No tienes usuario? Pídeselo al administrador: no hay registro público.</p>
        </ng-template>
      </p-card>
    </div>
  `,
  styles: `
    .login-container { display: flex; justify-content: center; align-items: flex-start; padding: 2rem 1rem; }
    .login-card { width: 100%; max-width: 26rem; }
    .login-header { text-align: center; padding: 2rem 1.5rem 0.5rem; }
    .login-header i { font-size: 2.5rem; color: var(--accent); margin-bottom: 0.5rem; display: block; }
    .login-header h1 { font-size: 1.5rem; margin: 0.5rem 0 0.3rem; }
    .login-header p { color: var(--muted); margin: 0; }
    .login-form { display: grid; gap: 1rem; }
    .field { display: grid; gap: 0.3rem; }
    .field label { font-weight: 600; font-size: 0.95rem; }
    .login-footer { text-align: center; color: var(--muted); font-size: 0.9rem; margin: 0; }
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
