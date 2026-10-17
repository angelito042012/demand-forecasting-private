# Estado vigente del proyecto

Actualizado el 17/10/2026, America/Lima, durante recuperación de sesión. Este resumen sustituye las instrucciones de etapas ya cerradas; el registro anterior se conserva en HISTORIAL_ENTREGAS.md.

## Objetivo y siguiente encargo

Sistema Demand Forecasting para la MYPE, entrega el 23/10/2026. Claude Code ejecuta; Codex dirige y revisa, y puede asumir ejecución cuando el usuario avise del cambio por límite de uso. Un solo ejecutor principal modifica el proyecto a la vez. Ver PROTOCOLO_TRABAJO.md.

**Punto de entrada para una sesión nueva: RETOMAR_CLAUDE.md. Encargo vigente: ETAPA_04_CLAUDE.md (T06, comparación de ML), tras REVISION_CODEX_04.md.** T05 aceptado al commit dff7d27. Se autoriza entrenamiento de ML solo con marzo-julio y protocolo previo. Agosto sigue reservado; no evaluar el test final ni declarar impacto de inventario.

## Hitos comprobados

- Análisis, alcance, arquitectura propuesta, contratos y plan existentes.
- Seis Excel de marzo-agosto en C:\Users\rogel\Documents\Datos; 31 columnas y 87 437 filas de datos auditadas. No pedir reexportación.
- API básica de salud, importador v2, conciliación, calendario/catálogo temporal y acceso de entrenamiento implementados.
- R01–R03 aceptados por Codex para los seis archivos canónicos. Última suite ejecutada por Codex en la revisión anterior: 46 aprobadas, un aviso, 59,57 segundos. Análisis de estilo correcto. No se repitió la suite en esta recuperación documental.
- Escenario de inventario sintético reference_v1 generado y validado; 3758 SKU, 14338 movimientos y 6279 pedidos simulados. No representa inventario real ni una mejora demostrada.
- Cinco agentes y cuatro skills de Claude presentes.

## Entrega R04 y T04 revisada por Codex el 17/10/2026

- **R04 (código)**: `pipeline/data/sources.py` aprueba fuentes (importación `completed`, sin conflicto OPEN). `load_training_data/load_fold/load_final_test_sales` y el catálogo leen solo líneas con fuente aprobada y detienen la construcción con `SourceApprovalError` ante carga fallida/parcial, conflicto abierto relevante, línea sin fuente válida, mes requerido (2026-03..mes del corte) sin fuente o base sin importaciones. El fingerprint ahora cubre filas (con categoría/almacén), catálogo, máscara, corte y manifiesto de fuentes. `reconcile` ya no da por buena una condición vacía.
- **Base v2 (preparada)**: `demand_forecasting_v2` reconstruida desde los seis Excel: 86 877 ventas y 560 créditos, 0 conflictos, 0 rechazos, 0 duplicados de `linea_id`; líneas normalizadas, conteos e importes por mes idénticos a v1 (`scripts/compare_v1_v2.py`). La recarga fue no-op por sha256 (0 inserciones). v1 (`demand_forecasting_dev`) intacta. Aplicación configurada localmente en v2 (`backend/app/config.py`, `.env.example`). Revertir: ver TRASPASO.md.
- **T04 (generado)**: series diarias SKU-almacén (459 375 filas) y por categoría (5 441), intermitencia, perfil, diccionario y firma: `docs/T04_PERFIL_CALIDAD.md|json`, `docs/T04_DICCIONARIO.md`, `docs/T04_FIRMA.json`; datos en `artifacts/private/t04/` (ignorado por Git). Reproducible: dos corridas dieron los mismos hashes.
- **Pruebas**: suite completa con `RUN_REALDATA=1`: 65 aprobadas, 0 omitidas, 1 aviso (httpx/Starlette), 69 s; `ruff` limpio en backend, pipeline, tests y scripts nuevos. Salud de la API con v2: 200 ok (cliente de prueba).
- **Hallazgos de datos clave** (medidos, ver perfil): un solo almacén y unidad UND; 3 días enmascarados sin registros en los Excel; 88 % de los días-par posteriores a la primera venta son cero observado; 2 568 de 3 758 pares son intermitentes y 729 irregulares; 357 SKU con <56 días de historia.

## T05 aceptado por Codex el 17/10/2026

- **Aceptado por Codex antes de esta entrega**: R04, base v2 (activa) y T04 (REVISION_CODEX_03.md).
- **Detalles menores cerrados**: `unidad_base` en el fingerprint; catálogo con `start` y máscara de la ventana de ventas; céntimos sin truncado (error si hay más de dos decimales); `SIN_REGISTROS_DIA` en diccionario y conservado en el agregado por categoría; remediación no destructiva en `docs/REMEDIACION_FUENTES.md`. Contenido de las series T04 sin cambios (mismos hashes); el fingerprint de entrenamiento cambió por incluir `unidad_base` (T04_FIRMA.json actualizado).
- **T05**: protocolo y configuración congelados y comprometidos (d763bed) antes de evaluar: `docs/T05_PROTOCOLO.md`, `config/t05_config.json`. Cinco folds de 7 días, cuatro baselines (cero, último día, naive semanal con fallback contabilizado, promedio 28 días), niveles SKU y categoría, cohorte primaria/historia corta/nuevos. Código en `pipeline/forecast/` y `scripts/run_t05.py`. Resultados: `docs/T05_RESULTADOS.md`, `T05_METRICAS.json`, `T05_MANIFIESTO.json`; predicciones fila a fila en `artifacts/private/t05/` (ignorado). Repetición idéntica verificada; agosto no se leyó.
- **Resultado, tal como salió**: en SKU-almacén diario (cohorte primaria, universo común, 104 533 filas) ningún baseline distinto de cero supera al control cero (WAPE cero 1,000; último día 1,431; naive 1,627; promedio 28 d 1,535). En el acumulado a 7 días solo promedio_28 queda marginalmente por debajo (0,992 frente a 1,000). En categoría los tres baselines superan al cero (WAPE diario 0,40–0,44 frente a 1,0; R² 0,76–0,83). Por la regla fijada de antemano la referencia para T06 es **ultimo_dia** (SKU, diario), pero su ventaja sobre el cero no existe a ese nivel: T06 debe comparar también contra el control cero y el acumulado a 7 días. Es un hallazgo descriptivo de cinco semanas con ventas posiblemente censuradas; no sustenta mejora de inventario.
- **Angular**: `scripts/prepare-frontend.ps1` funcionó (Angular CLI 21.2.27, Node 24.19.0, npm 11.17.0); `npm run build` compila (bundle principal 214 kB); `frontend/` con `package-lock.json` versionados. Sin pantallas; `ng test` no ejecutado.
- **Pruebas**: suite completa con `RUN_REALDATA=1`: 83 aprobadas, 0 omitidas, 1 aviso (httpx/Starlette), 71 s (log en `artifacts/private/t05/pytest_full.log`). `ruff` limpio en backend, pipeline, tests y scripts nuevos.

## Pendiente

- Ejecutar T06 según ETAPA_04_CLAUDE.md. No se han entrenado Random Forest ni boosting; agosto no se ha evaluado.
- Límites: un solo almacén/unidad; 5 folds de una semana; la cohorte primaria cuenta ceros observados como utilizables (según protocolo); sin inventario real; una fuente aprobada por mes; resolución de conflictos no implementada.
- Angular: pantallas y `ng test` pendientes.

## Entorno

Python 3.12; Git con checkpoints locales (ver TRASPASO.md). Contenedor df-mongo-dev activo con demand_forecasting_dev (v1) y demand_forecasting_v2 (activa). Sin cuentas Azure/Atlas. API sin autenticación completa.

## Decisiones que no deben preguntarse otra vez

TIPO_DOC=7 confirmado como notas de crédito; no implican retorno físico automático. Excluir 03/04, 12/04 y 07/06 de 2026 de entrenamiento/métricas sin comprimir calendario. Categorías por fecha de corte; conservar originales. Inventario sintético autorizado y etiquetado para escenarios. Marzo-julio para desarrollo; agosto reservado para prueba final. Ver DECISIONES_DATOS.md.

## Entregas posteriores

Después de aprobar T04: modelos de referencia y ML; simulación comparativa; API/interfaz/autenticación e integración; infraestructura y publicación; pruebas, documentación y entrega. Codex emitirá cada encargo con criterios verificables. No afirmar métricas o hitos antes de producir evidencia.

## Continuidad

TRASPASO.md contiene ejecutor previsto, último paso y próxima acción exacta. Actualizarlo durante el trabajo y al cambiar de herramienta. En caso de una interrupción abrupta, verificar cambios/procesos antes de confiar solo en el registro. No se configura cambio automático ni vigilancia de cuotas.

## Revisión independiente acotada de Codex

REVISION_CODEX_03.md: 14 pruebas de fuentes/invariancia y 6 de series aprobadas; estilo correcto. Hashes de los tres artefactos comprobados; 459375 filas SKU-día recorridas, máscaras y sumas mensuales verificadas contra el perfil. Las 65 pruebas completas son el resultado reportado por Claude, no una repetición de Codex. Esa revisión corresponde al hito anterior. Después se aceptó T05 en REVISION_CODEX_04.md; la próxima entrega vigente es T06.

## Revisión de T05

Codex aprobó 14 pruebas seleccionadas de baselines/métricas e integración; estilo correcto. Verificó hashes de config/código/predicciones y recorrió 125391 predicciones sin agosto ni targets duplicados. Recalculó 24 grupos de métricas agregadas del universo común, diarios y de bloque, con coincidencia. La suite completa de 83 aprobadas corresponde al log de Claude, sin repetición integral de Codex. Referencia no nula ultimo_dia; el control cero sigue mejor en WAPE diario SKU. No confundir selección preregistrada entre no nulos con superioridad global.
