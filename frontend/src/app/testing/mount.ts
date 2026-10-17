// Ayudas SOLO para pruebas: monta una página con HttpClient de prueba y responde a las peticiones.
import { Type } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting, TestRequest } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { apiInterceptor } from '../core/http.interceptor';
import { demoInterceptor } from '../core/demo';

export interface Mounted<T> { f: ComponentFixture<T>; http: HttpTestingController; el: HTMLElement }

export function mountPage<T>(cmp: Type<T>): Mounted<T> {
  TestBed.configureTestingModule({
    imports: [cmp],
    providers: [provideHttpClient(withInterceptors([apiInterceptor, demoInterceptor])), provideHttpClientTesting(), provideRouter([{ path: 'corridas', children: [] }])],
  });
  const http = TestBed.inject(HttpTestingController);
  const f = TestBed.createComponent(cmp);
  f.detectChanges();
  return { f, http, el: f.nativeElement as HTMLElement };
}

export const reqOf = (http: HttpTestingController, path: string): TestRequest => http.expectOne((r) => r.url === path);

export async function settle(f: ComponentFixture<unknown>) {
  f.detectChanges();
  await f.whenStable();
  f.detectChanges();
}

export async function respond(f: ComponentFixture<unknown>, r: TestRequest, body: unknown) {
  r.flush(body as object);
  await settle(f);
}

/** Cambia un <select> como lo haría el usuario. */
export async function choose(f: ComponentFixture<unknown>, el: HTMLElement, testid: string, value: string) {
  const sel = el.querySelector(`[data-testid="${testid}"]`) as HTMLSelectElement;
  sel.value = value;
  sel.dispatchEvent(new Event('change'));
  await settle(f);
}

/** Texto visible: sin el contenido de los <details> plegados (identificadores, JSON, checksums). */
export function visibleText(el: HTMLElement): string {
  const c = el.cloneNode(true) as HTMLElement;
  c.querySelectorAll('details').forEach((d) => d.remove());
  return c.textContent ?? '';
}
