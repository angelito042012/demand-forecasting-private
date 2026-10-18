# T13A — Pruebas locales de uso, rendimiento y accesibilidad

Fecha: 18/10/2026 (America/Lima). **Todo es local** (Docker Desktop en el equipo de desarrollo): no acredita latencia ni comportamiento de Azure/Atlas, HTTPS externo (A13) ni aceptación humana (A14, **pendiente**). No se entrenó ningún modelo, no se repitió T12, no se tocó v1/v2/pub ni se usó Azure.

## 1. Montaje

- Stack `df-t13a` (compose de ensayo, mismos límites que el Bicep: **0,5 vCPU / 1 GiB** por contenedor; comprobado `NanoCpus=500000000`, `Memory=1073741824`), imagen única reconstruida con el código actual, proxy Caddy TLS autofirmado solo en `127.0.0.1`.
- Base **temporal nueva** `df_t13a_<fecha>` restaurada desde el respaldo verificado de T11A (19,4 s; 0 problemas; 213,5 MB = 41,7 % de 512 MB). Usuarios de prueba `admin_t13a` y `lector_t13a` con contraseñas aleatorias en un JSON privado. Al terminar: `docker compose down -v`, estado y credenciales de ensayo eliminados.
- Hardware: Windows 11, 12 CPU lógicas, Docker con 12 CPU y 7,9 GB de RAM para la VM (el límite efectivo de la API lo fija el cgroup de 0,5 vCPU / 1 GiB).
- Evidencia privada (fuera de Git): `artifacts/private/t13a/perf.json`, `e2e_t13a_resultado.json` (y `…_antes_fix_css.json`), `screens/`. Programas: `scripts/t13a_perf.py` (versionado) y `artifacts/private/t13a/{stack.py,e2e_t13a.mjs}`.

## 2. Rendimiento (lecturas paginadas, solo GET)

Método: `scripts/t13a_perf.py`; por consulta y nivel de concurrencia, **5 solicitudes de calentamiento descartadas** y **20 medidas por sesión**, páginas distintas, sesiones separadas (cada una con su login; 1 y 5 sesiones, hilos concurrentes en bucle cerrado), vía el proxy TLS local. 3 consultas representativas sobre la corrida histórica `hist-20260710-4ea348836e35` (3 647 SKU, 73 páginas de 50). Sin tormenta de peticiones ni evasión del límite de intentos. Con 20 muestras por sesión, el p95 es la 19.ª ordenada: **indicativo, no estadístico**.

| Consulta | Tamaño de página / respuesta | 1 sesión p50 / p95 (ms) | 5 sesiones p50 / p95 (ms) | Errores |
|---|---|---|---|---|
| `GET /forecasts?level=sku` | 50 filas / 19,4 KB | 99,1 / 172,6 | 177,7 / 373,0 | 0 |
| `GET /recommendations?only_orders=true` | 50 filas / 119,1 KB | 38,3 / 65,5 | 90,7 / 167,5 | 0 |
| `GET /recommendations/{sku}` (explicación) | 1 SKU / 4,2 KB | 13,9 / 24,0 | 26,0 / 88,2 | 0 |

- **Meta del contrato p95 < 2 s para lecturas precalculadas: cumplida en esta medición local** (peor caso 373 ms con 5 sesiones). No se cambió la meta.
- **Arranque en frío** (reinicio del contenedor de la API): `/health` disponible a los **6,1 s**; primera solicitud de cada consulta 181,5 ms (pronósticos), 30,0 ms (pedidos) y 15,4 ms (detalle). Aparte de las tablas anteriores.
- **Memoria:** pico de la API **91,4 MiB** (cgroup `memory.peak`) de 1 GiB tras todas las mediciones. **CPU:** el cgroup registró estrangulación (`nr_throttled` 150 de 647 periodos, ≈ 10,1 s acumulados) por el tope de 0,5 vCPU: coherente con que p50/p95 suban con 5 sesiones; no hubo errores ni reinicios.
- Límites: la consulta de pronósticos es la más pesada (p95 373 ms con 5 sesiones); no se midió carga mayor ni la latencia hacia Atlas (Mongo corre en un contenedor local); no se midió la generación de corridas aquí (ver T11B: 22,2 s, pico del worker 406 MiB).

## 3. Recorrido en navegador (Chrome real, 22 comprobaciones)

Resultado final: **22/22 aprobadas** (lector, administrador y pantalla de 375 px), sobre el stack en contenedores con la base restaurada. Primero se ejecutó con fallos que llevaron al defecto de la sección 4; ejecución con fallos conservada en `e2e_t13a_resultado_antes_fix_css.json`.

Nuevo en esta tanda (ejecutado contra la **imagen de producción** servida por el proxy, no contra el servidor de desarrollo): error de acceso con `role=alert`; primer Tab = «Saltar al contenido»; resumen; las tres corridas distinguidas (histórica activa, final, sustituida) y el lector sin generación/subida; detalle de la final (sello, auditoría); pronósticos con filtro por categoría (50 filas); recomendaciones con el rótulo de inventario simulado y la explicación paso a paso de un pedido (9 pasos); final sin recomendaciones inventadas (`RECOMENDACION_NO_VALIDADA_PARA_ESTE_ORIGEN`, 0 filas); comparación final sin ganador declarado y «WAPE no es exactitud»; comparación sin `run` = histórica T07; importaciones de solo lectura para el lector; **archivo de agosto rechazado** («Agosto de 2026 está reservado para la prueba final»); **generación 10/07 H21** desde la UI (primer envío: completada y corrida generada visible, 3→4 corridas; un envío posterior idéntico devolvió **el mismo trabajo ya completado**, sin duplicar, y la corrida histórica predeterminada siguió activa).

Reutilizado, no repetido: Chrome 20/20 de T11A (paquete final real sobre servidor de desarrollo), E2E de carga T10 (original sin cambios, reenvío) y generación en contenedor con verificación contra T07 (T11B). La subida de un `.xlsx` real aprobado («Sin cambios») no se repitió porque la base de publicación no contiene las importaciones de ventas.

## 4. Defecto encontrado y corregido (importante)

**En la imagen de producción las hojas de estilo globales no se aplicaban**: el compilado de Angular emitía `<link rel="stylesheet" media="print" onload="this.media='all'">` (carga diferida del CSS «no crítico»), y la política `script-src 'self'` impide ese manejador en línea, por lo que el CSS global quedaba en `media=print` (botones grises, tablas sin contenedor desplazable, desbordamiento horizontal de 904 px a 375 px). Las pruebas de navegador anteriores usaron el servidor de desarrollo, que no tiene ese comportamiento.

Corrección (mínima): `frontend/angular.json` (producción: `optimization.styles.inlineCritical = false` → `<link rel="stylesheet">` normal; la CSP no cambia) y `frontend/src/styles.scss` (`label`/`select`/`input` con `min-width:0; max-width:100%` y una columna `minmax(0,1fr)` para que un `<select>` con identificadores largos de corrida no ensanche la página). Verificado: enlace de estilos sin `media=print`, botones con el color de acento, 22/22 en el recorrido y **sin desbordamiento a 375 px** en resumen, corridas, pronósticos y recomendaciones. No se repitieron las pruebas unitarias de Angular (el cambio es de estilos/configuración de compilación); la imagen se reconstruyó correctamente.

## 5. Accesibilidad

**Revisión automatizada** (scripts propios en el navegador, por página; sin instalar catálogos de herramientas): todos los controles y enlaces tienen nombre accesible; sin ids duplicados; sin saltos de encabezado; `lang`/título presentes; contraste calculado de todo el texto visible ≥ 4,5:1 (3:1 en texto grande) con **una sola excepción: botones deshabilitados** (3,9:1; los controles deshabilitados quedan exentos de WCAG 1.4.3); foco visible mediante `:focus-visible` (contorno de 3 px). Tablas con `<th scope="col">`, `<caption>` en las de fases y contenedor desplazable con `tabindex=0 role=region aria-label`; errores con `role=alert`; detalle de la recomendación con `aria-live=polite`; enlace «Saltar al contenido».

**Falsos positivos descartados:** la comprobación de foco marcó los campos de fecha («Desde»/«Hasta»/«Origen»); al inspeccionarlos, el foco con teclado sí muestra contorno (`solid 3px`); lo marcado es el icono interno del selector de fecha del navegador (subcontrol sin `:focus-visible`).

**No verificado (límites):** lectura con lector de pantalla (NVDA/JAWS) no probada; zoom al 200 % y modo de contraste forzado no probados; tamaño de objetivos táctiles no medido; la prueba de pantalla pequeña es una sola anchura (375 px) en Chrome. Estas comprobaciones manuales quedan en `docs/T13_GUION_ACEPTACION.md` para quien acepte.

## 6. Pendiente (no cerrado por T13A)

- A13 (HTTPS externo y cinco usuarios en la nube) y rendimiento en la nube: dependen del despliegue, **no aprobado**.
- A14 y aceptación humana: **pendientes**; ver `docs/T13_GUION_ACEPTACION.md` (sin firmas ni participantes inventados).
- Revisión manual de accesibilidad con tecnologías de apoyo.
