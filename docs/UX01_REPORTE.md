# UX01 — Reporte del rediseño para comprender la aplicación

Fecha: 17/10/2026 (America/Lima). Encargo: `ETAPA_16_CLAUDE.md` y `docs/UX01_BRIEF.md`. **Observación de Rogelio (abierta):** «No comprendió el uso en su primera visita». Es una observación de uso, no un defecto de cálculo demostrado ni una nueva aceptación; seguirá abierta hasta que Rogelio vuelva a probar. Aceptación humana: **pendiente**. No se publicó nada en Azure, no se transfirieron datos, no se repitieron modelos ni evaluación final.

## 1. Qué cambió y por qué

| Antes | Ahora |
|---|---|
| Menú técnico (Resumen, Importaciones, Corridas, Pronósticos, Recomendaciones, Comparación, Sistema) y bienvenida con tabla de calidad de datos | **Inicio** con propósito, franja de contexto («Ejemplo con datos históricos de 2026. El inventario es simulado…»), tres tareas con botón real y «Cómo empezar» cerrable; menú de 4 tareas (Inicio, Ventas previstas, Reposición simulada, Mis análisis) + «Más» (Ventas registradas, Evaluación de resultados, Datos cargados, Ayuda) + Administración (Cargar datos, Crear análisis, Estado del sistema) |
| Corridas con 10 columnas, identificadores partidos en líneas, detalle con JSON | **Mis análisis**: tarjetas con nombre derivado de los datos («Ejemplo de julio», «Evaluación de agosto»), ventas utilizadas hasta, período estimado, estado y acciones; versiones reemplazadas solo tras «Ver versiones anteriores»; detalle técnico plegado |
| Pronósticos con 10 columnas (h, cohorte, RF, cero…) | **Ventas previstas**: producto, fecha, cantidad estimada y, si existe, vendido registrado; «Comparar métodos / ver detalles» recupera todas las columnas |
| Recomendaciones con 8 columnas y 4 avisos apilados | **Reposición simulada**: tres vistas (con sugerencia / sin necesidad de reponer / sin datos de inventario) filtradas en el servidor, tabla de 4 columnas, «Entender sugerencia» en tres pasos + «Ver cálculo completo y supuestos» (los mismos 8–9 pasos y la misma aritmética) |
| Comparación académica de primera mano | **Evaluación de resultados**: pregunta, conclusión corta calculada de los datos (error en lenguaje llano, «no significa X % de acierto», sin ganador), dos secciones y «Ver detalle completo» con todo el detalle académico, incluidos los resultados desfavorables |
| Resumen de ventas como portada | **Ventas registradas** (menú «Más») |
| Generación dentro de «Corridas» | **Crear análisis** (administrador) y **Cargar datos** en 3 pasos; el lector ve «solo el administrador» sin controles |

Trazabilidad (qué se movió y qué se conserva) en `docs/UX01_DECISIONES.md` §4. Se conservaron: cálculos, resultados, métodos, fechas, rutas internas y parámetro `run`, permisos (el servidor decide), advertencias esenciales (simulación con la frase exacta, WAPE no es exactitud, un solo bloque de 21 días sin ganador, categoría = suma heterogénea, «no evaluable»/null ≠ 0, sin recomendaciones en la evaluación, versión reemplazada). Los nombres de análisis, períodos y estados salen de los datos de la API (tipo, fechas), no están escritos para tres registros concretos.

## 2. Extensión mínima de la API (una)

`GET /recommendations?no_orders=true` (SKU con inventario simulado y pedido sugerido 0; incompatible con `only_orders`; excluye «sin snapshot»), necesaria para la vista «Sin necesidad de reponer» sin filtrar solo la página recibida. Prueba `tests/backend/test_data_api.py::test_recommendations_no_orders_view`. Sin cambios en contratos científicos ni en Mongo.

## 3. Pruebas realmente ejecutadas

- **Frontend (suite completa):** 11 archivos, **212 pruebas aprobadas**, 0 fallos (`ng test`); incluye pruebas nuevas de comportamiento (`ux-home-admin` 26, `ux-forecasts-reco` 29, `ux-evaluation` 26, shell/menú) y las existentes ajustadas **conservando las assertions de negocio** (permisos, selección entre análisis, resultados adversos, null/no evaluable ≠ 0, sin snapshot, evaluación sin recomendaciones, versiones reemplazadas, paginación/filtros, errores). **Build de producción:** correcto.
- **Backend:** `tests/backend` completo, **167 aprobadas** (`artifacts/private/ux01/pytest_backend.xml`), por el cambio de API; no se repitieron modelos, evaluación final ni suites de datos/ML.
- **E2E en Chrome sobre la imagen real servida por HTTPS local** (`https://localhost:8443`, CSP intacta, base común de la demo): **51/51 comprobaciones** (`artifacts/private/ux01/e2e_ux01_resultado.json`): primera visita, tres tareas de inicio, inicio→reposición con sugerencia→explicación en **2 acciones** (sin código de producto previo), cambio a la evaluación sin pedidos, conservación del análisis al navegar/volver/recargar, versiones reemplazadas rotuladas, lector sin mutaciones, administrador con carga (agosto rechazado) y creación de análisis, 1366 px, **375 px** (menú plegable) y **zoom 200 %** (viewport efectivo de 683 px) sin desplazamiento horizontal de la página; hoja de estilos sin `media=print/onload`.
- **Accesibilidad automatizada** (script propio, por pantalla y tamaño): todos los controles con nombre, sin ids duplicados, un `h1` por pantalla, sin saltos de encabezado, contraste calculado correcto (excluidos botones deshabilitados), foco visible al tabular. Capturas en `artifacts/private/ux01/screens/` (inicio, mis análisis, previsiones, reposición y detalle, evaluación, versiones anteriores, ayuda, ventas, cargar, crear, móvil y zoom).
- Omitido a propósito: suite general de datos/ML, rendimiento completo, Docker smoke completo.

## 4. Defectos encontrados y corregidos durante el E2E

Desplazamiento horizontal de la página en 375 px/zoom 200 % (rejilla del shell con `1fr`; corregido con `minmax(0,1fr)`); nombres accesibles del botón «Entender sugerencia» que no contenían el texto visible; encabezado `h1→h3` en Mis análisis; tamaños de letra de etiquetas/botones pequeños < 16 px (subidos); falta de espacio en la frase de resultado.

## 5. Límites

- No se probó con lector de pantalla (NVDA/JAWS); la revisión de accesibilidad es automatizada y la manual de teclado cubrió el orden de tabulación y el foco visible, no un recorrido completo.
- Chips, `code` y algunas notas pequeñas siguen en 14–15 px (rótulos, no cuerpo de texto).
- Las decimales de porcentajes de las tablas siguen el formato es-PE existente (`78.1 %`) mientras los textos de ayuda citan «0,78»; sin cambios de cálculo.
- El nombre «Ejemplo de julio» se deriva del mes de las ventas utilizadas; si hubiera más ejemplos de ese mes, compartirían nombre (se distinguen por fecha).
- La comprensión real depende de la nueva prueba de Rogelio (guion en `docs/T13_GUION_ACEPTACION.md`, «Prueba de comprensión»); no se infiere de los E2E.
- La demostración ahora incluye un análisis creado por el E2E (`gen-20260710-…`, ventas hasta el 10/07/2026); no cambia la corrida en uso por defecto ni la evaluación.

## 6. Demostración actualizada

Imagen `df-app:ux01-269a9cd` (`sha256:88dfaab2b229…`), construida desde el commit `269a9cd`, servida en `https://localhost:8443` (solo 127.0.0.1), misma base `df_demo_20261017221940` verificada (api y worker), health ok, histórica activa intacta. Hubo una interrupción breve (unos segundos) al reemplazar la API; **hay que recargar la página (Ctrl+F5) e ingresar de nuevo** si ya estaba abierta.
