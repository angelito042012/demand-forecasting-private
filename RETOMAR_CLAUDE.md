# Recuperación de sesión y siguiente entrega

El usuario autoriza que Claude Code desarrolle el proyecto completo mediante encargos y revisiones de Codex. La fecha límite es el 23/10/2026, America/Lima. Partimos de los archivos actuales; no reiniciar el proyecto ni repetir análisis ya aceptados.

## Leer antes de actuar

Lee CLAUDE.md, docs/ESTADO.md, docs/TRASPASO.md, docs/PROTOCOLO_TRABAJO.md, docs/DECISIONES_DATOS.md, docs/REVISION_CODEX_02.md y ETAPA_02_CLAUDE.md. Consulta CONTRATOS.md y BACKLOG.md para los criterios del incremento. El historial de chat perdido se sustituye por estos archivos y por la inspección del repositorio.

## Paso 1 Recuperar el estado real

Revisa Git, cambios presentes y servicios del proyecto. Comprueba si algún trabajador anterior sigue activo antes de editar sus archivos. No asumas que la base v2 o T04 faltan solo porque no aparecen en un mensaje: verifica. Registra en TRASPASO.md lo encontrado y muestra al usuario una explicación breve del punto desde el que retomas. No pares a solicitar de nuevo las decisiones ya tomadas.

Revisa exclusiones y crea un checkpoint Git local del estado existente sin credenciales, datos comerciales ni artefactos privados. No sobrescribas avances ni uses reset para dejar la carpeta limpia. Las pruebas del último hito se registraron con 46 aprobadas; repetir verificaciones cuando hagan falta para confirmar cambios o entorno actual.

## Paso 2 Cerrar R04

Implementa la comprobación obligatoria de fuentes completas/aprobadas en la ruta de datos y catálogo. Una venta persistida por una carga fallida no puede entrar silenciosamente en entrenamiento. Añade pruebas de carga parcial, reintento completo, conflicto abierto, procedencia inválida, meses requeridos ausentes e invariancia temporal. Evita incluir agosto o datos posteriores al corte del fold.

## Paso 3 Preparar la base v2

Reconstruye desde los seis Excel en demand_forecasting_v2, si todavía no está preparada. Compara con v1 los conteos, importes y líneas normalizadas por mes; repite la carga y exige cero duplicados/conflictos. No tocar Excel ni borrar v1. Si todo coincide, configurar localmente v2 y documentar cómo revertir. Esta acción reversible ya forma parte del encargo autorizado; no solicitar otra vez aprobación para la preparación local.

## Paso 4 Completar T04

Genera perfil de calidad, diccionario y series diarias de marzo-julio con la ruta validada. Conserva calendario natural, tres días enmascarados y categoría al corte. Documenta cobertura, inicio de historia por producto, ceros observados, intermitencia, unidades y transformaciones. No transformar días anteriores a la primera observación del producto en demanda cero conocida. Firma el dataset con hashes, parámetros y manifiesto. Excluye los datos comerciales de Git.

## Paso 5 Verificar y entregar

Ejecuta pruebas relevantes y la suite completa con Mongo disponible y datos reales en bases temporales aisladas; informa cualquier skip o fallo. Verifica salud de API después de cambiar configuración. Actualiza ESTADO.md, TRASPASO.md, backlog y evidencia. Guarda un checkpoint local verificado y entrega el resumen a la persona usuaria para revisión de Codex.

Detente antes de entrenar modelos o usar agosto para selección. El próximo encargo de modelos se emitirá tras revisar T04. Angular sigue pendiente por la última falla de conexión con npm: registrar un diagnóstico limitado y continuar datos; no desactivar TLS.

## Continuidad

Puedes delegar tareas independientes a los agentes locales; evita edición concurrente de archivos compartidos. Guarda avances en TRASPASO.md durante el trabajo. Si una sesión o límite interrumpe la tarea, otro ejecutor continuará desde la última evidencia y el estado real. No prometer cambio automático de herramienta. El usuario avisará cuándo cambia de ejecutor.
