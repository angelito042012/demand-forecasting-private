import { DestroyRef, signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';

/**
 * Corrida elegida, compartida entre pantallas mediante el parámetro de URL `run`.
 * Sin parámetro, la API usa la corrida activa. Pronósticos, Recomendaciones y Comparación leen el mismo parámetro;
 * el menú lo conserva al cambiar de pantalla (queryParamsHandling = preserve).
 */
export class RunChoice {
  readonly id = signal<string | null>(null);

  constructor(private route: ActivatedRoute, private router: Router, destroyRef: DestroyRef, private onChange: () => void) {
    this.id.set(route.snapshot.queryParamMap.get('run') || null);
    const sub = route.queryParamMap.subscribe((q) => {
      const v = q.get('run') || null;
      if (v !== this.id()) { this.id.set(v); this.onChange(); }
    });
    destroyRef.onDestroy(() => sub.unsubscribe());
  }

  /** Elige una corrida (o null para la activa), la refleja en la URL y avisa a la pantalla. */
  set(id: string | null) {
    const v = id || null;
    if (v === this.id()) return;
    this.id.set(v);
    void this.router.navigate([], { relativeTo: this.route, queryParams: { run: v }, queryParamsHandling: 'merge', replaceUrl: true });
    this.onChange();
  }
}

export const KIND_LABELS: Record<string, string> = {
  historical_development: 'Histórica de desarrollo (T07)',
  generated_baseline: 'Generada por la aplicación',
  final_evaluation: 'Evaluación final (T12)',
};
export function kindLabel(kind: string | undefined | null): string {
  return kind ? (KIND_LABELS[kind] ?? kind) : '—';
}
export const isGenerated = (kind: string | undefined | null) => kind === 'generated_baseline';
export const isFinal = (kind: string | undefined | null) => kind === 'final_evaluation';
