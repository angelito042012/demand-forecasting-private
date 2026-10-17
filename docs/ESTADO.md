# Estado vigente del proyecto

Actualizado el 17/10/2026, America/Lima, durante recuperación de sesión. Este resumen sustituye las instrucciones de etapas ya cerradas; el registro anterior se conserva en HISTORIAL_ENTREGAS.md.

## Objetivo y siguiente encargo

Sistema Demand Forecasting para la MYPE, entrega el 23/10/2026. Claude Code ejecuta; Codex dirige y revisa, y puede asumir ejecución cuando el usuario avise del cambio por límite de uso. Un solo ejecutor principal modifica el proyecto a la vez. Ver PROTOCOLO_TRABAJO.md.

**Punto de entrada para una sesión nueva: RETOMAR_CLAUDE.md. Encargo vigente: ETAPA_03_CLAUDE.md (T05, baselines y folds temporales), emitido tras REVISION_CODEX_03.md.** R04, reconstrucción v2 y T04 aceptados para las fuentes canónicas. No repetir ETAPA_02. Agosto permanece reservado; todavía no iniciar T06.

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

## Pendiente

- T05 pendiente: aplicar ETAPA_03_CLAUDE.md. Cerrar los detalles menores de ventana/catalogo, unidad en firma, precisión monetaria y diccionario como parte del inicio de esa entrega. No se entrenaron modelos ni se evaluó agosto.
- Límites de R04: sin procedimiento de resolución de conflictos ni detección de líneas ausentes en un archivo reemplazado; la comprobación contra el manifiesto exacto de líneas sigue pendiente. Línea de recarga en v2 validada solo por no-op de sha256 (la idempotencia línea a línea está cubierta por pruebas en bases temporales).
- Angular: `npm ping` al registro funciona hoy (PONG 661 ms); no se intentó instalar. frontend/ sigue ausente.

## Entorno

Python 3.12 con dependencias locales; Git con checkpoints locales (ver TRASPASO.md). Contenedor df-mongo-dev activo en 127.0.0.1:27017 con bases demand_forecasting_dev (v1) y demand_forecasting_v2 (activa). Sin cuentas Azure/Atlas. API sin autenticación completa.

## Decisiones que no deben preguntarse otra vez

TIPO_DOC=7 confirmado como notas de crédito; no implican retorno físico automático. Excluir 03/04, 12/04 y 07/06 de 2026 de entrenamiento/métricas sin comprimir calendario. Categorías por fecha de corte; conservar originales. Inventario sintético autorizado y etiquetado para escenarios. Marzo-julio para desarrollo; agosto reservado para prueba final. Ver DECISIONES_DATOS.md.

## Entregas posteriores

Después de aprobar T04: modelos de referencia y ML; simulación comparativa; API/interfaz/autenticación e integración; infraestructura y publicación; pruebas, documentación y entrega. Codex emitirá cada encargo con criterios verificables. No afirmar métricas o hitos antes de producir evidencia.

## Continuidad

TRASPASO.md contiene ejecutor previsto, último paso y próxima acción exacta. Actualizarlo durante el trabajo y al cambiar de herramienta. En caso de una interrupción abrupta, verificar cambios/procesos antes de confiar solo en el registro. No se configura cambio automático ni vigilancia de cuotas.

## Revisión independiente acotada de Codex

REVISION_CODEX_03.md: 14 pruebas de fuentes/invariancia y 6 de series aprobadas; estilo correcto. Hashes de los tres artefactos comprobados; 459375 filas SKU-día recorridas, máscaras y sumas mensuales verificadas contra el perfil. Las 65 pruebas completas son el resultado reportado por Claude, no una repetición de Codex. Próxima entrega: T05; Angular puede prepararse en paralelo sin bloquear datos.
