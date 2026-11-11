import { DestroyRef } from '@angular/core';

/**
 * Pantallas con tablas anchas: añaden la clase `wide` al <main> mientras están abiertas (ver app.scss).
 * Las demás pantallas conservan su ancho. Se llama desde el constructor del componente.
 */
export function useWideMain(doc: Document, destroyRef: DestroyRef): void {
  const main = doc.querySelector('main');
  main?.classList.add('wide');
  destroyRef.onDestroy(() => main?.classList.remove('wide'));
}
