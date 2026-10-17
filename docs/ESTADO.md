# Estado vigente del proyecto

Actualizado el 17/10/2026, America/Lima. Entrega final: 23/10/2026. Claude Code ejecuta; Codex dirige/revisa. Un único ejecutor principal activo. Historial y detalles previos en HISTORIAL_ENTREGAS.md y revisiones 01–05.

## Punto de entrada y siguiente encargo

**T07 entregado a revisión de Codex (17/10/2026, Claude).** Siguiente: revisión de T07 y, después, integración/API, congelación de selección y prueba final controlada de agosto en el orden que Codex decida. Agosto sigue sin consultarse. Evidencia: `docs/T07_PROTOCOLO.md`, `T07_RESULTADOS.md`, `T07_METRICAS.json`, `T07_MANIFIESTO.json`, `config/t07_config.json`; privado: `artifacts/private/t07/`.

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

## Entrega T07 (17/10/2026): horizontes 10/14/21 y simulación junio-julio, pendiente de revisión

- **Prerrequisito**: inferencia coherente (contexto: inicio/fin reales, dimensiones, entidades, vocabulario guardado con `Vocab.id`, versión de features `t07-1`, horizonte entrenado); paquetes T06 rechazados salvo `allow_legacy` (h≤7); rezagos h>7 con `o+h-7*ceil(h/7)`. Artefactos T06 intactos.
- **Protocolo/config**: comprometidos antes de resultados (325da2f), sin enmiendas. Código `pipeline/forecast/{features,models,t07}.py`, `pipeline/sim/engine.py`, `scripts/run_t07.py`.
- **Parte A (4 folds solapados de 21 días, SKU primaria, universo común)**: WAPE acumulado H=14: cero 1,000; promedio_28 **0,873**; referencia fija 31/05 1,035; RF distribuido 0,929 (mejora −6,5 %, 0/4 folds favorables, sesgo/obs +0,167). El candidato **no cumple** la regla provisional; también pierde en H10 y H21 y en categoría (RF 0,255 frente a 0,202 a H=14). `promedio_28` supera al cero en SKU acumulado (WAPE 0,930 a H=10, 0,873 a H=14, 0,837 a H=21); a nivel diario ningún método supera al cero.
- **Parte B (simulación 01/06–31/07, 3347 SKU, 27 combinaciones política×escenario)**: conservación por SKU/día y de sistema e identidad de valor verificadas (error máx. 1,2e-10). Escenario principal L=7, S=7: fill rate referencia fija 0,741, promedio_28 0,797, RF distribuido 0,809, con stock medio y compras crecientes en el mismo orden (RF +7,5 % stock y +4,0 % compras frente a promedio_28); la ventaja de servicio del RF es compatible con pedir más (sobrepronostica) y no es concluyente. Los nueve escenarios, cohortes y diferencias están en T07_RESULTADOS.md.
- **Pruebas**: suite completa `RUN_REALDATA=1` 117 aprobadas, 0 omitidas, 346 s (log `artifacts/private/t07/pytest_full.log`), ejecutada antes de ajustes solo de reporte; tras ellos se repitieron `tests/sim` y `test_t07_functions` (16 aprobadas) y la ejecución completa de `scripts.run_t07` (162 s, repetición idéntica). `ruff` limpio. Revisión independiente (agente quality-reviewer, solo lectura): sin fugas; sus hallazgos de reporte (cobertura, cohortes, rótulos, lectura servicio-inventario) se corrigieron; quedan como límites los menores del reporte.
- **Límites**: desarrollo con meses ya conocidos; demanda proxy; costos/holding/lead time supuestos; universo fijo al 31/05 (411 SKU posteriores excluidos, 3783 unidades); sin precio como feature; RF con 36 series; no demuestra impacto en la MYPE.

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
