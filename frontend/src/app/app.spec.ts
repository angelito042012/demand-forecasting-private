import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { App } from './app';
import { routes } from './app.routes';

describe('App shell', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [App], providers: [provideRouter(routes)] }).compileComponents();
  });
  it('renderiza título y 4 enlaces de menú', async () => {
    const f = TestBed.createComponent(App);
    await f.whenStable();
    const el = f.nativeElement as HTMLElement;
    expect(el.querySelector('h1')?.textContent).toContain('Pronóstico de demanda');
    expect(el.querySelectorAll('nav a').length).toBe(4);
  });
  it('rutas son lazy (loadComponent)', () => {
    expect(routes.filter((r) => r.loadComponent).length).toBe(4);
  });
});
