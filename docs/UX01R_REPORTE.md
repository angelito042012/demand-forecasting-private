# UX01R — Cierre de R17 y Evaluación comprensible

Fecha: 17/10/2026 (America/Lima). Encargo: `ETAPA_17_CLAUDE.md` / `REVISION_CODEX_16.md`. Se conserva el rediseño UX01; no se reinició el diseño, no se repitieron modelos, evaluación final ni suites amplias, no se tocó Azure ni datos fuera del equipo. **La aceptación humana sigue pendiente** (la observación de Rogelio «No comprendió el uso en su primera visita» continúa abierta hasta su nueva prueba).

## 1. R17 — lista de análisis sin bucle y con error visible

- **Causa:** `AnalysisBar` llamaba a `RunsStore.ensure()` dentro de un `effect`, y `ensure()` leía el estado reactivo y recargaba si había error: cada fallo de `/runs` reactivaba el efecto y lanzaba otra petición.
- **Corrección:** `ensure()` ya no es reactivo (se llama una vez desde el constructor) y no reintenta tras un error; solo `retry()`/`refresh()` explícitos vuelven a leer. La barra distingue **cargando**, **error** («No pudimos cargar tus análisis» + botón **Reintentar**, sin reemplazar lo elegido), **ningún análisis publicado** y **análisis inexistente** (si la lista tiene más de 50 y el id no está, dice que no puede confirmar si existe, en lugar de afirmar que no existe). Un único `RunsStore` comparte la carga entre consumidores. La caché se invalida cuando cambia la identidad de la sesión (otro usuario → nueva lectura).
- **Regresión definitiva** `frontend/src/app/pages/r17-runs-store.spec.ts` (6 pruebas: Inicio y Ventas previstas con 503, cero peticiones espontáneas, una petición por reintento explícito y recuperación, fallo persistente sin bucle, carga compartida, estados distintos, identidad). **Falla sin el arreglo** (3 fallidas con el comportamiento reactivo anterior: `artifacts/private/ux01r/r17_antes_del_arreglo.log`) y **pasa con él**. La prueba privada de Codex se incorporó con nombre definitivo.
- Límite que queda: `RunsStore` lee solo la primera página de 50 análisis; la demo tiene pocos. Antes de escalar el historial habría que leer el id elegido por separado.

## 2. Evaluación de resultados, simplificada (sin cambiar cifras)

- **Vista inicial:** pregunta, barra de análisis, alcance en palabras simples («productos con historia suficiente · acumulado de 14 días · N productos»), **una explicación** («…equivale a cerca del 78,1 % del volumen vendido; no significa 78,1 % de acierto. Es un error alto por producto»), los dos períodos con **etiquetas distintas** (Métrica del 01 al 14 de agosto; Bloque de prueba disponible del 01 al 21 de agosto, derivados de los datos publicados), **un** aviso breve y el botón **Ver cómo se evaluó**.
- **Detalle académico** (una sola sección expandible, cerrada al llegar): tabla del hallazgo primario, mejora relativa negativa, regla de selección, control cero, sesgos, cobertura, SKU nuevos, métodos de cálculo y las **advertencias completas publicadas por la API**, sin cambiar cifras ni orden. Las dos secciones («Estimaciones frente a ventas registradas», «Comparación de reposición simulada») son pestañas accesibles (flechas, Inicio, Fin); la de reposición lleva el aviso exacto de simulación junto al stock/costo/pedido. El umbral de la frase «error alto por producto» (WAPE ≥ 0,5) es un criterio **de presentación**, no un juicio de calidad.
- **Textos precisados:** «resultado agregado de 4 bloques» (no promedio); ventana de 28 días de calendario con días válidos incluidos los de venta cero, excluidos fuera y sin suponer 28 días de historia; el análisis creado «no incluye una evaluación contra ventas registradas, por diseño» (ya no se afirma que no existan ventas); H14 (01–14/08) frente al bloque de 21 días (01–21/08); y el espacio entre fecha y paréntesis en la barra común. El guion de aceptación verifica presencia de los tipos/identificadores y del puntero, no «tres» corridas.

## 3. Pruebas realmente ejecutadas

- **Frontend, suite completa** (porque cambian componentes comunes): 12 archivos, **234 pruebas aprobadas**, 0 fallos; **build de producción correcto**.
- **No repetidos:** backend (sin cambio de API), modelos, evaluación final, E2E de 51 pasos, rendimiento.
- **Comprobación acotada en producción** (`artifacts/private/ux01r/e2e_ux01r.mjs`, Chrome sobre `https://localhost:8443`, CSP intacta): **18/18**: Inicio; Evaluación con detalle cerrado y abierto (resumen sin tabla técnica ni lista de reglas, error alto dicho con claridad, períodos con etiquetas distintas, detalle con 78,1 % / 79,1 % / 100,0 %, mejora −1,3 %, «RF declarado ganador: no» y advertencias completas); pestañas por teclado con aviso de simulación; histórico con «resultado agregado de 4 bloques»; **error de carga simulado en el navegador** (`page.route`, sin detener ningún servicio) en Inicio y Ventas previstas: error visible, **1** petición, **+1** al pulsar Reintentar y recuperación; 375 px con detalle cerrado y abierto sin desplazamiento horizontal; foco visible; hoja de estilos sin `media=print`.
- Capturas (sin claves): `artifacts/private/ux01r/antes_evaluacion_1366.png` (antes) y `screens/despues_evaluacion_cerrado_1366.png`, `despues_evaluacion_abierto_1366.png`, `despues_evaluacion_reposicion_1366.png`, `despues_evaluacion_375.png`, `error_recuperable_inicio_1366.png`, `error_recuperable_previsiones_1366.png`.

## 4. Demostración actualizada

Imagen `df-app:ux01r-f95092f` (`sha256:d17041ecfeaa…`), construida desde el commit `f95092f`, en `https://localhost:8443` (solo 127.0.0.1), misma base `df_demo_20261017221940` (verificada en API y worker), health ok, histórica activa intacta, usuarios y volúmenes conservados (sin `down -v`). Hubo una interrupción breve al reemplazar la API: **recargar con Ctrl+F5 e ingresar de nuevo** si la página ya estaba abierta.

## 5. Límites

Sin lector de pantalla; tipografía de chips y notas pequeñas en 14–15 px; porcentajes de las tablas con el formato es-PE existente (`78.1 %`) y textos de ayuda con «0,78»; aceptación humana, A13 y publicación pendientes.
