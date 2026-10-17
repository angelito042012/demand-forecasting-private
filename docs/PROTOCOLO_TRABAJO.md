# Dirección y continuidad del proyecto

Actualizado el 17/10/2026. Fecha límite: 23/10/2026, America/Lima. Este documento registra el acuerdo del usuario y el procedimiento de trabajo compartido entre ejecutores.

## Responsabilidades

Claude Code es el ejecutor habitual: implementa código, datos, modelos, interfaz, pruebas, infraestructura y despliegue dentro de los encargos emitidos. Codex dirige el proyecto, prepara encargos concretos, revisa evidencia y decide el siguiente incremento. Cuando el usuario informe que Claude alcanzó su límite, Codex puede asumir la ejecución; cuando informe el cambio inverso, se prepara el retorno a Claude.

El cambio no es automático ni depende de una vigilancia continua de límites. Los mensajes del usuario determinan cuándo rotar. No prometer un límite o reinicio diario fijo: la disponibilidad depende de cada servicio. El trabajo guardado en esta carpeta, Git y los registros permiten continuar aunque se pierda el historial de conversación.

## Un ejecutor principal activo

Mantener un único ejecutor principal editando la carpeta. Antes de cambiar de herramienta, comprobar si el anterior sigue trabajando, si dejó procesos en segundo plano y qué archivos está modificando. No detener bases, contenedores o servidores útiles solo por cambiar de chat. No interrumpir procesos ajenos al proyecto. Si no se puede confirmar que un trabajador terminó, evitar cambios concurrentes en sus archivos hasta aclararlo.

Cada ejecutor puede utilizar agentes especializados en tareas independientes, normalmente hasta tres trabajadores simultáneos, con ámbitos de archivos y contratos definidos. El integrador controla dependencias, configuración, contratos y merges. Las capacidades y configuración de agentes de cada herramienta se verifican en su entorno; las definiciones .claude/agents no se presumen nativas de Codex.

## Orden de lectura al retomar

1. RETOMAR_CLAUDE.md o el encargo actual indicado por el usuario.
2. docs/ESTADO.md, que contiene solo el estado vigente y la siguiente tarea.
3. docs/TRASPASO.md y docs/PROTOCOLO_TRABAJO.md.
4. El encargo y revisión señalados por ESTADO.md.
5. docs/DECISIONES_DATOS.md y los contratos pertinentes al trabajo.

El usuario y sus decisiones más recientes prevalecen sobre archivos históricos. Los encabezados de revisión y el estado vigente identifican qué encargos antiguos ya se ejecutaron. No repetir la etapa inicial ni rehacer R01–R03 si sus cambios siguen presentes y las verificaciones aplicables pasan.

## Antes de modificar

Comprobar archivos, Git, cambios pendientes, configuración efectiva sin imprimir secretos y servicios necesarios. Si el último registro no concuerda con el código, investigar y actualizar el estado con lo observado. Una sesión perdida no implica que el código se haya perdido ni que una tarea registrada como pendiente siga sin ejecutar: verificar.

La recuperación inicial ya produjo checkpoints y commits. Al retomar, comprobar el historial real y crear un checkpoint local solo si existen cambios que lo requieran, excluyendo secretos/datos comerciales. Un commit puede guardar trabajo parcial si se describe claramente como tal, sin afirmar que está aprobado o probado. No resetear ni descartar cambios pendientes. Los commits locales rutinarios forman parte de la trazabilidad autorizada; publicar un remoto o compartir datos exige conocer el destino y el acceso correspondiente.

## Durante cada entrega

Implementar incrementos revisables y comprobar invariantes de negocio. Actualizar TRASPASO.md después de una unidad pequeña de trabajo y antes de una operación larga o de cerrar la sesión. Registrar el último paso terminado y el siguiente exacto, incluso si el resultado es parcial o fallido. No esperar al último mensaje para dejar todo el contexto.

Si el límite llega de forma abrupta, el registro puede estar desactualizado. El siguiente ejecutor debe revisar cambios y procesos, y repetir solo las comprobaciones necesarias para determinar dónde continuar. No hay garantía de guardar un último mensaje después de agotarse la sesión.

## Al terminar o cambiar de ejecutor

Actualizar ESTADO.md, TRASPASO.md y el backlog con: tareas, archivos, comandos realmente ejecutados, resultados, evidencias, base/configuración activa, servicios/procesos relevantes, bloqueos y siguiente paso. Registrar commit si existe. Dejar identificado qué falta revisar por Codex. Conservar el historial en docs/HISTORIAL_ENTREGAS.md; no acumular estados antiguos contradictorios en el resumen vigente.

La siguiente entrega de desarrollo depende de la revisión de sus criterios de aceptación, no solo de un mensaje que diga que terminó. No repetir pruebas amplias si no hubo cambios o riesgos nuevos que lo justifiquen. No presentar pruebas omitidas como aprobadas.

## Alcance de autonomía

Preparación local, código, pruebas, reconstrucción no destructiva en una base nueva, configuración local reversible y commits locales se ejecutan dentro del encargo sin pedir confirmación repetida. Conservar Excel y la base v1. No borrar recursos antiguos ni tocar aplicaciones ajenas. La base v2 puede pasar a ser activa tras comparar y documentar cómo revertir.

El despliegue forma parte del objetivo global. Preparar código, scripts, configuración y comprobaciones. Si falta una cuenta o credencial, pedir solo ese acceso cuando sea necesario y avanzar en trabajo independiente. No contratar servicios ni generar gasto no acordado. No afirmar publicación mientras solo exista un plan o una ejecución local.

## Reglas de investigación vigentes

Marzo-julio: desarrollo y validación temporal. Agosto: prueba final bajo selección congelada, autorizada específicamente en ETAPA_10_CLAUDE.md (T12), no para re-selección ni para acceso general. Notas de crédito separadas, tres días excluidos sin comprimir calendario y catálogo por corte. El inventario sintético está autorizado para escenarios y debe identificarse como tal; no demuestra una mejora real de la MYPE. No usarlo para entrenar demanda. No repetir preguntas ya resueltas en DECISIONES_DATOS.md.

El encargo vigente se indica en ESTADO.md: **ETAPA_10_CLAUDE.md (T12)**. T08R y T10R aceptados (REVISION_CODEX_10.md); R05–R10 cerrados para alcance local. Ejecutar el protocolo final congelado con acceso dedicado a agosto y sin cambiar selección. T11 despliegue/HTTPS/restauración y aceptación humana siguen pendientes; no afirmar impacto real ni publicación. No ejecutar encargos históricos aceptados.
