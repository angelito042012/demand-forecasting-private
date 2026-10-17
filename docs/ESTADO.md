# Estado vigente del proyecto

Actualizado el 17/10/2026, Lima. Entrega final 23/10/2026. Claude ejecuta; Codex dirige/revisa. Un ejecutor principal activo. Historial anterior en HISTORIAL_ENTREGAS.md; revisiones 01–07.

## Siguiente encargo

**RETOMAR_CLAUDE.md → ETAPA_07_CLAUDE.md (corrección T08, R05–R06)**. T08 al commit 960638d está parcialmente verificado y pendiente de aceptación por defectos reproducidos en REVISION_CODEX_07.md. No empezar T10, reentrenar T06/T07 ni abrir agosto en este incremento.

## Hitos aceptados

- Datos: seis Excel intactos en C:\Users\rogel\Documents\Datos;87 437 líneas = 86 877 ventas + 560 notas de crédito. 31 columnas homogéneas. No pedir reexportación.
- Importador schema2, fuentes aprobadas, conciliación y barrera temporal R01–R04/T03 aceptados. Mongo activa demand_forecasting_v2; v1 demand_forecasting_dev conservada.
- T04: 459375 filas SKU-día y 5441 categoría-día; calendario natural/máscaras y catálogo por corte.
- T05–T07 aceptados como experimentos de desarrollo. RF y XGBoost no mejoraron referencia SKU T06; RF categoría distribuido tampoco en T07 (WAPE H14 .9292 frente a .8726,0/4 folds). Método operativo promedio_28, categoría agregada SKU; RF comparador, no ganador.
- Simulación T07 bajo supuestos:27 combinaciones,3347 SKU,61 días. Mayor servicio de RF coincide con más stock/compras; no impacto real demostrado. Auditoría Codex06 verificó160 grupos SKU y todos los saldos diarios.

## T08 construido y comprobaciones

- Backend con sesión HttpOnly/CSRF, roles admin/lector y CLI administrativa. API real de lectura de importaciones, resumen de ventas hasta julio, corridas, forecasts, recomendaciones y backtests. No hay carga web ni ejecución de corridas desde app.
- Publicación versionada por CLI; corrida histórica activa hist-20260710-52b01cd999dd.76587 pronósticos SKU,756 categoría,3647 recomendaciones (3347 con snapshot y 300 sin snapshot). **Sus recomendaciones tienen el defecto R05; no tratarlas como validadas**. Conservarlas para historial al publicar la corrección nueva.
- Frontend conectado con acceso/resumen/importaciones/corridas/pronósticos/recomendaciones/comparación/sistema. Mocks solo con demo explícito. Funciona técnicamente; presentación de comparación y decimales por mejorar.
- Motor: validación de entradas y conservación diaria añadidas en T08. Ecuaciones/resultados T07 sin cambio.
- Selección congelada documentada en docs/SELECCION_CONGELADA.md y config/seleccion_congelada.json; hash verificado por Codex. Protocolo razonable, **sin ejecutar**, sin paquetes finales y sin autorización de agosto. No modificar selección para resolver precisión/proxy/UI.
- Claude reporta suite 226 aprobadas/1 aviso, 509 s; frontend 42/build; Chrome E2E 24/24. Logs/capturas privados artifacts/private/t08/. Son resultados de Claude, no repetición del revisor.
- Codex07 ejecutó118 pruebas seleccionadas auth/API/publicación/motor,1 aviso, 91.02 s; ruff correcto. No reentrenó ni repitió Chrome. Revisó evidencia/capturas y realizó auditoría de recomendaciones con fuentes reales en modo lectura; tests en bases temporales.

## Defectos abiertos y siguiente corrección

- **R05**: media del CSV T07 con 10 cifras cambia el techo. Frente a sumas/días reales de 13/06–10/07:225 objetivos y118 pedidos inflados en 1. Corregir señales con precisión completa y publicación/identidad nueva, preservando anterior. Auditoría agregada de referencia: 640 sugerencias/2773 unidades frente a 582/2655 correctas. Probar con oráculo matemático independiente, no el mismo helper.
- **R06**: Uvicorn confía en XFF desde loopback y cambia la IP usada para login; reproducción dinámica confirmada. Desactivar proxy headers en demo local y probar la cadena HTTP real. Proxy público y límite atómico/concurrente requieren control antes de publicar.
- Anclar métricas/manifiesto aprobados y fingerprint de fuentes/catálogo antes de combinar. Hoy G4 coincide y T07_METRICAS sigue idéntico a 5790103; prevenir mezcla futura.
- UI: tabla de comparación filtrada y resumen principal, números legibles, detalles técnicos plegados; no cambiar resultados.

## Evidencia y entorno

REVISION_CODEX_07.md; artifacts/private/codex_review07_audit.json y codex_review07_tests.xml. Fuente de datos hasta10/07 leída sin modificar; pruebas usan df_test_* aisladas. No se consultó agosto ni reference_v1. Python 3.12, Angular 21,FastAPI/PyMongo/Mongo; df-mongo-dev útil. API/frontend detenidos por Claude al cerrar; Codex no inició servidores. Credenciales locales privadas nunca se imprimen ni versionan. Guía docs/GUIA_LOCAL.md; scripts de inicio/parada existentes.

## Decisiones cerradas y pendientes posteriores

TIPO_DOC=7 son notas de crédito; no implican retorno físico. Excluir 03/04,12/04 y 07/06/2026 sin comprimir calendario ni escribir cero observado. Categoría por corte. Inventario sintético autorizado y etiquetado; ventas pueden estar censuradas por stock desconocido. Sin impacto real demostrado. Marzo-julio desarrollo; agosto reservado. Ver DECISIONES_DATOS.md.

Después de corregir y revisar T08: T10 carga web/batch/timer, T12 ejecución final bajo congelación, T11 HTTPS/despliegue/backup/restauración, pruebas de carga/accesibilidad/aceptación humana e informe. Sin cuentas Azure/Atlas ni presupuesto autorizado. No hay alternancia automática de cuotas; el usuario avisa del cambio. Commits locales autorizados con secretos/datos privados excluidos.
