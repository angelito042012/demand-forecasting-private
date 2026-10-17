# Estado vigente del proyecto

Actualizado el 17/10/2026, America/Lima, durante recuperación de sesión. Este resumen sustituye las instrucciones de etapas ya cerradas; el registro anterior se conserva en HISTORIAL_ENTREGAS.md.

## Objetivo y siguiente encargo

Sistema Demand Forecasting para la MYPE, entrega el 23/10/2026. Claude Code ejecuta; Codex dirige y revisa, y puede asumir ejecución cuando el usuario avise del cambio por límite de uso. Un solo ejecutor principal modifica el proyecto a la vez. Ver PROTOCOLO_TRABAJO.md.

**Punto de entrada para una sesión nueva: RETOMAR_CLAUDE.md.** El encargo técnico vigente es ETAPA_02_CLAUDE.md, detallado y aceptado para continuar en REVISION_CODEX_02.md: cerrar R04, reconstruir/comparar base v2 y completar T04. Detenerse antes de entrenar para revisión de Codex.

## Hitos comprobados

- Análisis, alcance, arquitectura propuesta, contratos y plan existentes.
- Seis Excel de marzo-agosto en C:\Users\rogel\Documents\Datos; 31 columnas y 87 437 filas de datos auditadas. No pedir reexportación.
- API básica de salud, importador v2, conciliación, calendario/catálogo temporal y acceso de entrenamiento implementados.
- R01–R03 aceptados por Codex para los seis archivos canónicos. Última suite ejecutada por Codex en la revisión anterior: 46 aprobadas, un aviso, 59,57 segundos. Análisis de estilo correcto. No se repitió la suite en esta recuperación documental.
- Escenario de inventario sintético reference_v1 generado y validado; 3758 SKU, 14338 movimientos y 6279 pedidos simulados. No representa inventario real ni una mejora demostrada.
- Cinco agentes y cuatro skills de Claude presentes.

## Pendiente inmediato

- R04: impedir que ventas/categorías persistidas por cargas fallidas o parciales entren silenciosamente en el dataset. Reproducción en REVISION_CODEX_02.md.
- Base v2: preparar en base nueva, comparar conteos/importes/líneas y repetir carga; cambiar configuración local solo tras controles correctos, conservando v1. No consta completada en archivos inspeccionados.
- T04: perfil, diccionario, series diarias y firma de dataset de marzo-julio. No se encontraron archivos nuevos que acrediten su ejecución durante esta recuperación; comprobar estado vivo al iniciar.
- Angular: última conexión a registro npm falló; frontend/ todavía ausente. No bloquear trabajo de datos por ello.

## Entorno y límites de esta recuperación

Python 3.12 y dependencias locales preparados previamente. Git inicializado, sin commits al inspeccionar el 17/10; archivos sin seguimiento. Crear checkpoint local revisando exclusiones antes de empezar desarrollo. API sin autenticación completa ni interfaz implementada. Usuario sin cuentas Azure/Atlas según último dato recibido.

La última base comprobada en la revisión anterior fue demand_forecasting_dev, esquema v1, con 86 877 ventas y 560 créditos. El contenedor utilizado fue df-mongo-dev. No se volvió a consultar MongoDB ni Docker en esta recuperación; comprobar si están activos y si ya existe v2 antes de actuar. No recrear recursos por suponerlos ausentes.

## Decisiones que no deben preguntarse otra vez

TIPO_DOC=7 confirmado como notas de crédito; no implican retorno físico automático. Excluir 03/04, 12/04 y 07/06 de 2026 de entrenamiento/métricas sin comprimir calendario. Categorías por fecha de corte; conservar originales. Inventario sintético autorizado y etiquetado para escenarios. Marzo-julio para desarrollo; agosto reservado para prueba final. Ver DECISIONES_DATOS.md.

## Entregas posteriores

Después de aprobar T04: modelos de referencia y ML; simulación comparativa; API/interfaz/autenticación e integración; infraestructura y publicación; pruebas, documentación y entrega. Codex emitirá cada encargo con criterios verificables. No afirmar métricas o hitos antes de producir evidencia.

## Continuidad

TRASPASO.md contiene ejecutor previsto, último paso y próxima acción exacta. Actualizarlo durante el trabajo y al cambiar de herramienta. En caso de una interrupción abrupta, verificar cambios/procesos antes de confiar solo en el registro. No se configura cambio automático ni vigilancia de cuotas.
