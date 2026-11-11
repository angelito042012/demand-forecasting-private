import { Component, ElementRef, inject, input, model } from '@angular/core';

export interface EvalTab { id: string; label: string; testid: string }

/**
 * UX01R: pestañas accesibles (tablist/tab) para separar «Estimaciones frente a ventas registradas» de la reposición simulada.
 * Solo gestiona la lista de pestañas y el teclado (flechas, Inicio, Fin); quien la usa pinta los paneles (role="tabpanel",
 * id «panel-<id>», aria-labelledby «tab-<id>») y oculta los que no están activos.
 */
@Component({
  selector: 'app-eval-tabs',
  template: `
    <div class="tabs" role="tablist" [attr.aria-label]="label()">
      @for (t of tabs(); track t.id; let i = $index) {
        <button type="button" role="tab" [id]="'tab-' + t.id" [attr.aria-selected]="active() === t.id" [attr.aria-controls]="'panel-' + t.id"
          [attr.tabindex]="active() === t.id ? 0 : -1" [attr.data-testid]="t.testid" [class.on]="active() === t.id"
          (click)="active.set(t.id)" (keydown)="key($event, i)">{{ t.label }}</button>
      }
    </div>
  `,
  styles: `
    .tabs { display: flex; flex-wrap: wrap; gap: 0.25rem; border-bottom: 2px solid var(--line, #c9d1d9); margin: 0.6rem 0 1rem; }
    button[role="tab"] { background: transparent; border: 1px solid transparent; border-bottom: 0; border-radius: 6px 6px 0 0; padding: 0.55rem 0.9rem; font: inherit; cursor: pointer; color: inherit; min-height: 2.75rem; }
    button[role="tab"].on { background: var(--soft, #eef2f6); border-color: var(--line, #c9d1d9); font-weight: 700; box-shadow: inset 0 -3px 0 var(--accent, #0b5cab); }
    button[role="tab"]:focus-visible { outline: 3px solid var(--accent, #0b5cab); outline-offset: 2px; }
  `,
})
export class EvalTabs {
  private host = inject<ElementRef<HTMLElement>>(ElementRef);
  tabs = input.required<EvalTab[]>();
  label = input('Secciones de la evaluación');
  active = model.required<string>();

  key(e: KeyboardEvent, i: number) {
    const n = this.tabs().length;
    let j: number | null = null;
    if (e.key === 'ArrowRight') j = (i + 1) % n;
    else if (e.key === 'ArrowLeft') j = (i - 1 + n) % n;
    else if (e.key === 'Home') j = 0;
    else if (e.key === 'End') j = n - 1;
    if (j === null) return;
    e.preventDefault();
    this.active.set(this.tabs()[j].id);
    queueMicrotask(() => (this.host.nativeElement.querySelectorAll('[role="tab"]')[j!] as HTMLElement | undefined)?.focus());
  }
}
