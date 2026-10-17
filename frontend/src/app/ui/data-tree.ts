import { Component, input } from '@angular/core';

/**
 * Muestra tal cual un documento JSON publicado por el servidor (sin inventar ni recalcular métricas).
 * Objetos -> tabla clave/valor; listas de objetos -> tabla; otros valores -> texto.
 */
@Component({
  selector: 'app-data-tree',
  imports: [],
  template: `
    @if (isList(value())) {
      @if (isObjList(value())) {
        <div class="scroll">
          <table>
            <thead><tr>@for (c of columns(value()); track c) { <th>{{ c }}</th> }</tr></thead>
            <tbody>
              @for (row of asList(value()); track $index) {
                <tr>@for (c of columns(value()); track c) { <td>{{ cell(row, c) }}</td> }</tr>
              }
            </tbody>
          </table>
        </div>
      } @else {
        <span>{{ asList(value()).join(', ') }}</span>
      }
    } @else if (isObj(value())) {
      <dl>
        @for (k of keys(value()); track k) {
          <dt>{{ k }}</dt>
          <dd>
            @if (isPrimitive(get(value(), k))) { {{ get(value(), k) }} } @else { <app-data-tree [value]="get(value(), k)" /> }
          </dd>
        }
      </dl>
    } @else {
      <span>{{ value() }}</span>
    }
  `,
  styles: `
    dl { margin: 0 0 0 0.5rem; padding-left: 0.5rem; border-left: 2px solid #ddd; }
    dt { font-weight: 600; margin-top: 0.3rem; }
    dd { margin: 0 0 0 0.5rem; }
    .scroll { overflow-x: auto; }
  `,
})
export class DataTree {
  value = input<unknown>(null);
  isList(v: unknown): v is unknown[] { return Array.isArray(v); }
  isObj(v: unknown): v is Record<string, unknown> { return typeof v === 'object' && v !== null && !Array.isArray(v); }
  isPrimitive(v: unknown) { return v === null || typeof v !== 'object'; }
  isObjList(v: unknown) { return Array.isArray(v) && v.length > 0 && v.every((x) => this.isObj(x)); }
  asList(v: unknown) { return v as any[]; }
  keys(v: unknown) { return Object.keys(v as object); }
  get(v: unknown, k: string) { return (v as Record<string, unknown>)[k]; }
  columns(v: unknown): string[] {
    const set = new Set<string>();
    for (const r of v as Record<string, unknown>[]) Object.keys(r).forEach((k) => set.add(k));
    return [...set];
  }
  cell(row: unknown, c: string) {
    const x = (row as Record<string, unknown>)[c];
    return x !== null && typeof x === 'object' ? JSON.stringify(x) : (x ?? '—');
  }
}
