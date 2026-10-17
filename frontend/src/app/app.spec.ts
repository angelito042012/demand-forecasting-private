import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { App } from './app';
import { routes } from './app.routes';
import { AuthService } from './core/auth.service';
import { DemoMode } from './core/demo';
import { apiInterceptor } from './core/http.interceptor';
import { session } from './testing/fixtures';

describe('App shell', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [provideRouter(routes), provideHttpClient(withInterceptors([apiInterceptor])), provideHttpClientTesting()],
    }).compileComponents();
  });
  it('sin sesión no muestra menú; con sesión muestra 7 enlaces y usuario', async () => {
    const f = TestBed.createComponent(App);
    await f.whenStable();
    const el = f.nativeElement as HTMLElement;
    expect(el.querySelector('h1')?.textContent).toContain('Pronóstico de demanda');
    expect(el.querySelectorAll('nav a').length).toBe(0);
    TestBed.inject(AuthService).session.set(session);
    f.detectChanges();
    expect(el.querySelectorAll('nav a').length).toBe(7);
    expect(el.querySelector('[data-testid="user"]')?.textContent).toContain('ana');
  });
  it('rótulo de demostración ausente por defecto (sin ?demo=1)', () => {
    expect(TestBed.inject(DemoMode).enabled).toBe(false);
    const f = TestBed.createComponent(App);
    f.detectChanges();
    expect((f.nativeElement as HTMLElement).querySelector('[data-testid="demo-banner"]')).toBeNull();
  });
  it('rutas protegidas por guard y perezosas', () => {
    const prot = routes.find((r) => r.canActivate)!;
    expect(prot.children!.filter((r) => r.loadComponent).length).toBe(7);
    expect(routes.find((r) => r.path === 'acceso')?.canActivate).toBeUndefined();
  });
});
