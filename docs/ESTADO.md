# Estado vigente del proyecto

Actualizado el 17/10/2026, America/Lima. Entrega final: 23/10/2026. Claude Code ejecuta; Codex dirige/revisa. Un único ejecutor principal activo. Historial y detalles previos en HISTORIAL_ENTREGAS.md y revisiones 01–05.

## Punto de entrada y siguiente encargo

**RETOMAR_CLAUDE.md → ETAPA_05_CLAUDE.md (T07)**, tras aceptar T06 al commit 3b11fbd en docs/REVISION_CODEX_05.md. Ejecutar primero el ajuste de inferencia, después protocolo/config antes de evaluar horizontes de protección 10/14/21 y simulación de junio-julio. No repetir T04–T06. Agosto sigue reservado; no entrenar/seleccionar con él ni abrir la prueba final en este encargo.

## Hitos aceptados

- Datos: seis Excel intactos en C:\Users\rogel\Documents\Datos. 87437 líneas =86877 ventas y 560 notas de crédito; 31 columnas homogéneas. No pedir reexportación.
- R01–R04/T03: importador schema2, identidad lógica y fuentes, conciliación, barrera de entrenamiento, fuentes aprobadas y remediación no destructiva. Límites y evidencia en revisiones anteriores.
- Mongo activa demand_forecasting_v2; comparación completa con v1 demand_forecasting_dev verificada. Ambas conservadas.
- T04: calendario/catálogo por corte y máscaras; 459375 filas SKU-día y 5441 categoría-día. 3758 SKU, demanda muy intermitente. Docs T04 y artefactos privados conservados.
- T05: cuatro baselines, cinco folds de siete días y cohortes temporales. Aceptado en REVISION_CODEX_04.md; resultados históricos conservados.
- T06: RF y XGBoost con protocolo previo y comparación sobre los mismos targets/baselines de T05. Aceptado como experimento de desarrollo en REVISION_CODEX_05.md. Precio no incorporado. Sin selección final para agosto.

## Resultado T06 y revisión independiente

- SKU primario, acumulado siete días: promedio_28 WAPE 0,992109; cero 1,000; XGBoost 1,017; RF 1,058. Ningún ML cumple la regla. Propuesta provisional promedio_28. Sesgos ML aproximadamente +2785/+6411 frente a **23026 unidades observadas**. WAPE es razón: 0,992 equivale a 99,2%.
- Categoría diaria: RF 0,394 frente a promedio_28 0,4025, ventaja relativa 2,07%, 3/5 folds; cumple por margen mínimo. RF semanal 0,217 es peor que naive 0,201 y promedio_28 0,202. No sustenta mejores pedidos SKU; el nuevo método de reparto requiere validación.
- Codex: 11 pruebas selectivas aprobadas (7 puras/modelos y 4 integración); estilo correcto. Hashes de código/config/predicciones verificados; 125391 filas sin fechas en agosto ni claves repetidas. Columnas originales T05 idénticas. Recalculados 36 grupos de métricas, coincidentes. No repitió el entrenamiento de siete minutos ni la suite integral.
- Claude reporta suite completa 94 aprobadas, 0 omitidas, 1 aviso (74 s); log artifacts/private/t06/pytest_full.log. Angular build y 15 pruebas aprobadas. Distinguir esos resultados de la revisión selectiva.
- Artefactos: docs/T06_PROTOCOLO.md, T06_RESULTADOS.md, T06_METRICAS.json, T06_MANIFIESTO.json y config/t06_config.json. Modelos/predicciones en artifacts/private/t06/, fuera de Git.

## Límites y trabajo activo siguiente

- Inferencia: validar fechas reales ctx.start/fin y uso del vocabulario guardado antes de API/simulador. Los folds T06 fueron coherentes; no se invalidan sus métricas. T07 lo corrige primero.
- T07 extiende el horizonte hasta 21 días; RF de categoría distribuido con pesos históricos es candidato nuevo, sin garantía de mejora. Simulación de desarrollo inicia con información <=31/05; no reutilizar parámetros de julio del escenario reference_v1 de agosto.
- Inventario reference_v1 ya existe, con 3758 SKU, 14338 movimientos y 6279 pedidos sintéticos. Es un escenario, no inventario real ni mejora demostrada. No consultar su trayectoria de agosto para este encargo.
- Frontend: navegación y cuatro pantallas con estados/mocks etiquetados; compila y tiene pruebas reportadas. Sin API real, autenticación ni revisión en navegador.
- Backend: healthcheck; faltan API funcional/autenticación, integración, corridas versionadas y publicación. Python 3.12, Angular 21, FastAPI/PyMongo/Mongo; contenedor df-mongo-dev útil. Sin cuentas Azure/Atlas ni presupuesto de nube acordado.

## Decisiones que permanecen cerradas

TIPO_DOC=7 son notas de crédito; no retorno físico automático. Excluir 03/04, 12/04 y 07/06/2026 sin comprimir calendario ni convertirlos en observaciones cero. Categoría por corte; conservar originales. Inventario sintético autorizado y etiquetado. Ventas observadas pueden estar censuradas por stock desconocido; no inferir causalidad o impacto real. Marzo-julio para desarrollo; agosto reservado hasta congelación posterior. Ver DECISIONES_DATOS.md.

## Continuidad

Siguiente ejecutor previsto Claude Code; revisar Git/procesos y ejecutar ETAPA_05_CLAUDE.md. Commits locales autorizados con secretos/datos privados excluidos. TRASPASO.md contiene el siguiente paso exacto. No hay alternancia automática de cuotas; el usuario avisa del cambio de ejecutor. Después de T07: integración/API/autenticación, evaluación final congelada, publicación, pruebas y documentación; cada hito necesita evidencia, no solo un mensaje de terminación.
