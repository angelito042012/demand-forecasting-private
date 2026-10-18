# Instrucciones compartidas para Codex en este proyecto

Prioridad posterior, 18/10: el usuario encargó directamente a Codex la preparación de los 14 Excel. Ya entregada en `docs/PREPARACION_DATOS_ACADEMICA_V1.md`; leerla antes de retomar. Originales intactos, grupo de 50 y saldo calculado bajo supuestos en paquete privado. No presentar cantidades generadas como conteos físicos. No usar el saldo retrospectivo para entrenamiento/backtests. Esta preparación no autoriza importación, repetir T12 ni publicar. Las autoridades UX posteriores siguen aceptadas; sus pasos humanos quedan pendientes.

Leer docs/PROTOCOLO_TRABAJO.md, docs/ESTADO.md, docs/TRASPASO.md, CLAUDE.md y docs/DECISIONES_DATOS.md antes de editar. Las decisiones más recientes del usuario prevalecen sobre registros históricos. No asumir que una sesión perdida borró los archivos.

El usuario designa Claude Code como ejecutor habitual y Codex como director/revisor. Cuando avise que Claude agotó su uso y pida continuar, Codex asume implementación, pruebas, datos, infraestructura y despliegue del encargo vigente, con las mismas reglas de aceptación. Al volver a Claude, actualizar el traspaso; no editar simultáneamente el mismo trabajo desde dos ejecutores principales. No hay conmutación automática ni garantía de un límite diario fijo.

Se autoriza delegación a agentes cuando haya subtareas independientes y sea útil. Máximo operativo habitual: tres trabajadores simultáneos. Asignar alcance de archivos; un integrador controla contratos y dependencias. Las definiciones de agentes/skills de Claude sirven como referencia de dominio y no se presumen funciones cargadas por Codex.

Autoridad vigente: REVISION_CODEX_17.md. ETAPA_17_CLAUDE.md ejecutada y UX01R/R17 aceptados localmente (48 pruebas propias dirigidas). No repetir el rediseño, R12–R17, modelos, T12 ni Azure. Siguiente puerta: nueva prueba de comprensión de Rogelio en la demo activa; aceptación humana pendiente hasta su respuesta real. Publicación ETAPA_15 permanece condicional, diferida y sin gasto/transferencias autorizados. Mantener df-demo/base común, usuarios/volúmenes y advertencias esenciales. Atender observaciones concretas nuevas sin iniciar rondas de corrección por rutina.

No alterar originales ni borrar la base v1. Reconstrucción nueva en v2, comparación y cambio local reversible forman parte del encargo. Commits locales para checkpoints están autorizados después de revisar exclusiones; no guardar secretos ni datos comerciales. Servicios de pago requieren presupuesto/acceso acordados. Preparar lo posible y pedir solo accesos realmente necesarios.

Actualizar TRASPASO.md por unidad de trabajo y ESTADO.md al terminar. Guardar evidencia de pruebas ejecutadas, no inferir éxitos por mensajes del ejecutor anterior. Conservar historial sin mezclarlo con el resumen vigente. No reiniciar el proyecto, descartar cambios ni repetir encargos cerrados para recuperar una conversación.
