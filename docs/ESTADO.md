# Estado vigente del proyecto

Actualizado el 17/10/2026, Lima. Entrega final 23/10/2026. Claude ejecuta; Codex dirige/revisa. Un ejecutor principal activo. Historial anterior en HISTORIAL_ENTREGAS.md; revisiones 01–07.

## Siguiente encargo

**Corrección T08R (R05–R06 y presentación) entregada a revisión de Codex (17/10/2026, Claude).** No se inició T10 ni se abrió agosto. Tras la revisión, Codex emitirá carga/batch (T10) y la ejecución final bajo la congelación, en el orden que decida. Informe: `docs/T08R_REPORTE.md`; auditoría: `docs/T08R_AUDITORIA.json`.

## Hitos aceptados

- Datos: seis Excel intactos en C:\Users\rogel\Documents\Datos;87 437 líneas = 86 877 ventas + 560 notas de crédito. 31 columnas homogéneas. No pedir reexportación.
- Importador schema2, fuentes aprobadas, conciliación y barrera temporal R01–R04/T03 aceptados. Mongo activa demand_forecasting_v2; v1 demand_forecasting_dev conservada.
- T04: 459375 filas SKU-día y 5441 categoría-día; calendario natural/máscaras y catálogo por corte.
- T05–T07 aceptados como experimentos de desarrollo. RF y XGBoost no mejoraron referencia SKU T06; RF categoría distribuido tampoco en T07 (WAPE H14 .9292 frente a .8726,0/4 folds). Método operativo promedio_28, categoría agregada SKU; RF comparador, no ganador.
- Simulación T07 bajo supuestos:27 combinaciones,3347 SKU,61 días. Mayor servicio de RF coincide con más stock/compras; no impacto real demostrado. Auditoría Codex06 verificó160 grupos SKU y todos los saldos diarios.

## T08 construido (estado verificado)

- Backend con sesión HttpOnly/CSRF, roles admin/lector, CLI administrativa y API real de lectura (importaciones, resumen de ventas hasta julio, corridas, pronósticos, recomendaciones, backtests). No hay carga web ni ejecución de corridas desde la app (T10).
- Publicación versionada por CLI (`scripts/publish_run.py`, identidad `t08r-1`). Corridas: `hist-20260710-4ea348836e35` **activa y válida**; `hist-20260710-52b01cd999dd` **sustituida** (R05) y conservada. 76 587 pronósticos SKU, 756 de categoría, 3 647 recomendaciones (3 347 con snapshot, 300 sin snapshot, 582 con pedido positivo).
- Frontend conectado a todas las pantallas; mocks solo con `?demo=1` rotulado. Motor con validación de entradas y conservación diaria; ecuaciones y resultados T07 sin cambio.
- Selección congelada (`docs/SELECCION_CONGELADA.md`, `config/seleccion_congelada.json`): sin ejecutar, sin paquetes finales, sin autorización de agosto; no se modificó en T08R.
- Reportes de ejecuciones de Claude: T08 (suite 226, frontend 42, E2E 24/24) y T08R (abajo). Codex07 verificó 118 pruebas seleccionadas de T08 y su auditoría de recomendaciones.

## T08R: correcciones aplicadas (commit final de esta entrega; antecedente 960638d)

- **R05 (precisión)**: la recomendación usa ahora señales exactas (suma de unidades y días útiles de la ventana de 28 días, derivadas de ventas aprobadas ≤ 10/07, aritmética racional, sin épsilon); el CSV T07 solo es control de coherencia. Reproducido antes de corregir (registro `artifacts/private/t08r/r05_fallo_previo.log`). **Corrida corregida `hist-20260710-4ea348836e35`** (activa; identidad con versión `t08r-1` y señales). La anterior `hist-20260710-52b01cd999dd` se **conserva como `superseded`** (`quality_issue` R05, `superseded_by`); sus hijos no se alteraron y la API/UI la marcan como no válida.
- **Auditoría independiente** (`scripts/audit_recommendations.py`, sin builders ni helpers; agregación directa de ventas aprobadas + NPZ, enteros): 3 347 recomendaciones, **0 diferencias** de objetivo/posición/pedido; **582 sugerencias positivas / 2 655 unidades** (igual que la referencia de Codex) frente a 640/2 773 de la corrida anterior: 58 sugerencias y 118 unidades menos; la corrida anterior tenía 225 objetivos y 118 pedidos inflados en una unidad. Los 300 sin snapshot siguen con todo nulo.
- **Anclaje**: manifiesto y métricas T07 se verifican contra la referencia aprobada (commit `5790103…` + contenido normalizado) y fingerprint/fuentes del fold aceptado antes de escribir; alteraciones rechazadas con pruebas.
- **R06 (proxy)**: `scripts/start-local.ps1` inicia Uvicorn con `--no-proxy-headers`; prueba de la cadena real (servidor Uvicorn en puerto efimero y, en navegador, proxy de Angular): variar `X-Forwarded-For` ya no elude el límite (401×5 → 429); control que reproduce el defecto con proxy activo. Contrato de proxy confiable para despliegue en `T08_CONTRATO.md` §8.
- **Presentación**: Comparación abre con el escenario principal y tres políticas (servicio %, faltantes, stock medio, compras PEN, diferencias frente a promedio_28) con selectores L/S/cohorte, y precisión predictiva filtrable (nivel/cohorte/horizonte/fold); altura de página 2 317 px (antes 29 829); una sola explicación del pedido con números formateados; detalles técnicos plegados; banner de corrida sustituida; estilos globales y foco/teclado.
- **Pruebas ejecutadas**: pytest completo sin los tests de datos reales costosos (sin repetir T06/T07): **254 aprobadas, 3 omitidas** (las omitidas son pruebas con `RUN_REALDATA=1` que repetirían T07 de 509 s; no se ejecutaron) (`artifacts/private/t08r/pytest_afectadas.log`); frontend 79 aprobadas y build correcto; E2E navegador real (Chrome) de regresión **16/16** incluida la vista de la corrida sustituida, 582 sugerencias, SKU 12040025 (media 3/7, objetivo 9, pedido 0) y 12010025 (objetivo 3, pedido 2), comparación filtrada, límite con XFF por el proxy real, API caída (`artifacts/private/t08r/e2e_t08r_resultado.json`, capturas en `artifacts/private/t08r/screens/`, privadas).
- **Límites vigentes**: límite de login («contar y luego insertar») y *lease* de publicación sin fencing siguen sin endurecer: **condición antes de exposición pública / T10 / T11**; no se afirma resistencia a ráfagas. Demostración local HTTP; recomendaciones hipotéticas con inventario simulado; corrida de 99 días de antigüedad; sin pruebas de carga/accesibilidad medida; despliegue y restauración pendientes. La congelación (`SELECCION_CONGELADA`) no se modificó.

## Evidencia y entorno

REVISION_CODEX_07.md; artifacts/private/codex_review07_audit.json y codex_review07_tests.xml. Fuente de datos hasta10/07 leída sin modificar; pruebas usan df_test_* aisladas. No se consultó agosto ni reference_v1. Python 3.12, Angular 21,FastAPI/PyMongo/Mongo; df-mongo-dev útil. API/frontend detenidos por Claude al cerrar (`scripts/stop-local.ps1`). Credenciales locales privadas nunca se imprimen ni versionan. Guía docs/GUIA_LOCAL.md; scripts de inicio/parada existentes.

## Decisiones cerradas y pendientes posteriores

TIPO_DOC=7 son notas de crédito; no implican retorno físico. Excluir 03/04,12/04 y 07/06/2026 sin comprimir calendario ni escribir cero observado. Categoría por corte. Inventario sintético autorizado y etiquetado; ventas pueden estar censuradas por stock desconocido. Sin impacto real demostrado. Marzo-julio desarrollo; agosto reservado. Ver DECISIONES_DATOS.md.

Después de corregir y revisar T08: T10 carga web/batch/timer, T12 ejecución final bajo congelación, T11 HTTPS/despliegue/backup/restauración, pruebas de carga/accesibilidad/aceptación humana e informe. Sin cuentas Azure/Atlas ni presupuesto autorizado. No hay alternancia automática de cuotas; el usuario avisa del cambio. Commits locales autorizados con secretos/datos privados excluidos.
