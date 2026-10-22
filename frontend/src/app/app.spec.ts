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
  it('sin sesión no muestra menú; el lector ve 5 tareas + 4 enlaces secundarios, sin administración', async () => {
    const f = TestBed.createComponent(App);
    await f.whenStable();
    const el = f.nativeElement as HTMLElement;
    expect(el.querySelector('[data-testid="context-strip"]')?.textContent).toContain('usan un inventario simulado');
    expect(el.querySelectorAll('nav a').length).toBe(0);
    TestBed.inject(AuthService).session.set(session);
    f.detectChanges();
    const links = Array.from(el.querySelectorAll('nav a')).map((a) => a.textContent?.trim());
    expect(links).toEqual(['Inicio', 'Ventas previstas', 'Existencias', 'Compra recomendada', 'Mis análisis', 'Ventas registradas', 'Evaluación de resultados', 'Evaluación académica', 'Datos cargados', 'Ayuda']);
    expect(el.querySelector('[data-testid="nav-cargar"]')).toBeNull();
    expect(el.querySelector('[data-testid="nav-crear"]')).toBeNull();
    expect(el.querySelector('[data-testid="user"]')?.textContent).toContain('ana');
  });
  it('el administrador ve además Cargar datos, Crear análisis y Estado del sistema', async () => {
    const f = TestBed.createComponent(App);
    await f.whenStable();
    TestBed.inject(AuthService).session.set({ ...session, role: 'admin' });
    f.detectChanges();
    const links = Array.from((f.nativeElement as HTMLElement).querySelectorAll('nav a')).map((a) => a.textContent?.trim());
    expect(links).toEqual(['Inicio', 'Ventas previstas', 'Existencias', 'Compra recomendada', 'Mis análisis', 'Ventas registradas', 'Evaluación de resultados', 'Evaluación académica', 'Ayuda', 'Cargar datos', 'Crear análisis', 'Estado del sistema']);
  });
  it('el menú móvil se abre y se cierra con el botón (aria-expanded)', async () => {
    const f = TestBed.createComponent(App);
    await f.whenStable();
    TestBed.inject(AuthService).session.set(session);
    f.detectChanges();
    const el = f.nativeElement as HTMLElement;
    const btn = el.querySelector('[data-testid="menu-toggle"]') as HTMLButtonElement;
    expect(btn.getAttribute('aria-expanded')).toBe('false');
    btn.click();
    f.detectChanges();
    expect(btn.getAttribute('aria-expanded')).toBe('true');
    expect(el.querySelector('nav')?.classList.contains('open')).toBe(true);
  });
  it('rótulo de demostración ausente por defecto (sin ?demo=1)', () => {
    expect(TestBed.inject(DemoMode).enabled).toBe(false);
    const f = TestBed.createComponent(App);
    f.detectChanges();
    expect((f.nativeElement as HTMLElement).querySelector('[data-testid="demo-banner"]')).toBeNull();
  });
  it('rutas protegidas por guard y perezosas', () => {
    const prot = routes.find((r) => r.canActivate)!;
    expect(prot.children!.filter((r) => r.loadComponent).length).toBe(13);
    expect(prot.children!.map((r) => r.path)).toEqual(expect.arrayContaining(['inicio', 'ayuda', 'crear-analisis', 'corridas', 'pronosticos', 'recomendaciones', 'comparacion', 'inventario', 'existencias', 'planificar', 'resumen', 'cargas', 'sistema']));
    expect(routes.find((r) => r.path === 'acceso')?.canActivate).toBeUndefined();
  });
});
