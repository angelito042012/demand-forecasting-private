# Estado vigente del proyecto

Actualizado el 17/10/2026, America/Lima. Entrega final: 23/10/2026. Claude Code ejecuta; Codex dirige/revisa. Un único ejecutor principal activo. Historial y detalles previos en HISTORIAL_ENTREGAS.md y revisiones 01–06.

## Punto de entrada y siguiente encargo

**T08 + lectura integrada T09 entregados a revisión de Codex (17/10/2026, Claude).** Siguiente: revisión de Codex; después integración restante (T10 carga/batch), ejecución final bajo la congelación revisada (T12), despliegue y respaldo (T11), aceptación humana e informe. Agosto sigue sin consultarse. Reporte de pruebas y límites: `docs/T08_REPORTE.md`; guía de uso local: `docs/GUIA_LOCAL.md`.

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

## T07 aceptado (17/10/2026): horizontes 10/14/21 y simulación junio-julio

- **Prerrequisito**: inferencia coherente (contexto: inicio/fin reales, dimensiones, entidades, vocabulario guardado con `Vocab.id`, versión de features `t07-1`, horizonte entrenado); paquetes T06 rechazados salvo `allow_legacy` (h≤7); rezagos h>7 con `o+h-7*ceil(h/7)`. Artefactos T06 intactos.
- **Protocolo/config**: comprometidos antes de resultados (325da2f), sin enmiendas. Código `pipeline/forecast/{features,models,t07}.py`, `pipeline/sim/engine.py`, `scripts/run_t07.py`.
- **Parte A (4 folds solapados de 21 días, SKU primaria, universo común)**: WAPE acumulado H=14: cero 1,000; promedio_28 **0,873**; referencia fija 31/05 1,035; RF distribuido 0,929 (mejora −6,5 %, 0/4 folds favorables, sesgo/obs +0,167). El candidato **no cumple** la regla provisional; también pierde en H10 y H21 y en categoría (RF 0,255 frente a 0,202 a H=14). `promedio_28` supera al cero en SKU acumulado (WAPE 0,930 a H=10, 0,873 a H=14, 0,837 a H=21); a nivel diario ningún método supera al cero.
- **Parte B (simulación 01/06–31/07, 3347 SKU, 27 combinaciones política×escenario)**: conservación por SKU/día y de sistema e identidad de valor verificadas (error máx. 1,2e-10). Escenario principal L=7, S=7: fill rate referencia fija 0,741, promedio_28 0,797, RF distribuido 0,809, con stock medio y compras crecientes en el mismo orden (RF +7,5 % stock y +4,0 % compras frente a promedio_28); la ventaja de servicio del RF es compatible con pedir más (sobrepronostica) y no es concluyente. Los nueve escenarios, cohortes y diferencias están en T07_RESULTADOS.md.
- **Pruebas**: suite completa `RUN_REALDATA=1` 117 aprobadas, 0 omitidas, 346 s (log `artifacts/private/t07/pytest_full.log`), ejecutada antes de ajustes solo de reporte; tras ellos se repitieron `tests/sim` y `test_t07_functions` (16 aprobadas) y la ejecución completa de `scripts.run_t07` (162 s, repetición idéntica). `ruff` limpio. Revisión independiente (agente quality-reviewer, solo lectura): sin fugas; sus hallazgos de reporte (cobertura, cohortes, rótulos, lectura servicio-inventario) se corrigieron; quedan como límites los menores del reporte.
- **Límites**: desarrollo con meses ya conocidos; demanda proxy; costos/holding/lead time supuestos; universo fijo al 31/05 (411 SKU posteriores excluidos, 3783 unidades); sin precio como feature; RF con 36 series; no demuestra impacto en la MYPE.

## Entrega T08 (17/10/2026): aplicación local autenticada con resultados persistidos

- **Ajustes del motor**: validación estricta de entradas y conservación diaria (`pipeline/sim/engine.py`); ecuaciones y resultados T07 sin cambio.
- **Contrato**: `docs/T08_CONTRATO.md` (sustituye API/persistencia históricas de `CONTRATOS.md`). **Congelación**: `docs/SELECCION_CONGELADA.md` + `config/seleccion_congelada.json` (método operativo `promedio_28`; RF comparador experimental; diseño de agosto fijado; **no ejecutada**, sin `run_final`, sin paquetes finales, sin leer agosto ni `reference_v1`).
- **Backend**: autenticación por cookie HttpOnly con CSRF, rate limit, roles admin/lector, CLI de alta de usuarios; rutas de lectura bajo `/api/v1` (importaciones, resumen de ventas ≤ 31/07, corridas, pronósticos, recomendaciones, backtests); agosto → 422. **Persistencia**: publicador versionado e idempotente (`scripts/publish_run.py`) con verificación de checksums y del código por commit. Corrida publicada en `demand_forecasting_v2`: `hist-20260710-52b01cd999dd` (76 587 pronósticos SKU, 756 de categoría, 3 647 recomendaciones de las cuales 300 sin inventario simulado, 1 backtest).
- **Frontend** conectado a la API (acceso, resumen, importaciones, corridas, pronósticos, recomendaciones con cálculo paso a paso, comparación, sistema); modo demostración solo con `?demo=1`, nunca como respaldo silencioso.
- **Pruebas**: suite integral 226 aprobadas, 0 omitidas (509 s); frontend 42 aprobadas y build correcto; **E2E en navegador real (Chrome + Playwright-core) 24/24** contra API y Mongo reales, incluidos sesión expirada, logout, 403/CSRF, agosto, inyección y API caída. Evidencia privada en `artifacts/private/t08/` (capturas, resultados, logs).
- **Defectos hallados en E2E y corregidos**: `[object Object]` en días excluidos, texto duplicado, mensaje de API caída.
- **Límites**: demostración local en HTTP; sin carga web ni ejecución de corridas desde la app; la recomendación es una sugerencia hipotética sobre una corrida histórica (99 días de antigüedad al consultarla) con inventario simulado; sin pruebas de carga/concurrencia/accesibilidad; despliegue, HTTPS y restauración pendientes.

## Límites y trabajo activo siguiente

- Inferencia coherente corregida/probada en T07. Al integrar, conservar alineación explícita de entidades y matrices. Motor actual con entradas válidas; endurecer contrato externo y añadir conservación diaria al chequeo automático, según REVISION_CODEX_06.md.
- T07 evaluó hasta 21 días y no respaldó RF distribuido como mejor pronóstico. Método operativo v1: promedio_28 SKU, categorías agregadas desde SKU; RF solo comparador experimental. Simulación inicializada <=31/05, sin parámetros futuros. Congelación final documentada en próximo incremento; agosto no autorizado todavía.
- Inventario reference_v1 ya existe, con 3758 SKU, 14338 movimientos y 6279 pedidos sintéticos. Es un escenario, no inventario real ni mejora demostrada. No consultar su trayectoria de agosto para este encargo.
- Frontend: navegación y cuatro pantallas con estados/mocks etiquetados; compila y tiene pruebas reportadas. Sin API real, autenticación ni revisión en navegador.
- Backend: healthcheck; faltan API funcional/autenticación, integración, corridas versionadas y publicación. Python 3.12, Angular 21, FastAPI/PyMongo/Mongo; contenedor df-mongo-dev útil. Sin cuentas Azure/Atlas ni presupuesto de nube acordado.

## Decisiones que permanecen cerradas

TIPO_DOC=7 son notas de crédito; no retorno físico automático. Excluir 03/04, 12/04 y 07/06/2026 sin comprimir calendario ni convertirlos en observaciones cero. Categoría por corte; conservar originales. Inventario sintético autorizado y etiquetado. Ventas observadas pueden estar censuradas por stock desconocido; no inferir causalidad o impacto real. Marzo-julio para desarrollo; agosto reservado hasta congelación posterior. Ver DECISIONES_DATOS.md.

## Continuidad

Siguiente ejecutor previsto Claude Code; revisar Git/procesos y ejecutar ETAPA_06_CLAUDE.md. Commits locales autorizados con secretos/datos privados excluidos. TRASPASO.md contiene el siguiente paso exacto. No hay alternancia automática de cuotas; el usuario avisa del cambio de ejecutor. Después de T07: integración/API/autenticación, evaluación final congelada, publicación, pruebas y documentación; cada hito necesita evidencia, no solo un mensaje de terminación.

## Revisión independiente T07 (Codex 06)

22 pruebas selectivas aprobadas en 2,44 s; estilo correcto. Hashes de config/código, dos artefactos y 13 modelos comprobados. Recorridas 293853 predicciones sin agosto ni claves duplicadas; 160 grupos de métricas SKU recalculados coincidentes. Las métricas de categoría no se recalcularon desde detalle fila a fila. NPZ: 27 combinaciones sobre 3347 SKU y 61 fechas, saldos diarios, recepción por lead time, revisiones, condiciones iniciales y métricas totales verificadas. No se reentrenó ni se repitió la prueba real costosa; suite 117 corresponde a Claude. Resumen privado artifacts/private/codex_review06_audit.json; revisión versionada REVISION_CODEX_06.md.

Interpretación: RF H14 WAPE 0,9292 frente a 0,8726 de promedio_28, 0/4 folds favorables. Su +1,17 puntos de fill rate en el escenario principal coincide con +7,5% stock y +4,0% compras: no ahorro ni mejora real demostrada. Antes de integración solo faltan endurecimientos pequeños del motor; no invalidan T07. T08/T09 integrados, T10, T11, T12 y cierre académico siguen pendientes.
