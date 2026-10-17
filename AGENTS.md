# Instrucciones compartidas para Codex en este proyecto

Leer docs/PROTOCOLO_TRABAJO.md, docs/ESTADO.md, docs/TRASPASO.md, CLAUDE.md y docs/DECISIONES_DATOS.md antes de editar. Las decisiones más recientes del usuario prevalecen sobre registros históricos. No asumir que una sesión perdida borró los archivos.

El usuario designa Claude Code como ejecutor habitual y Codex como director/revisor. Cuando avise que Claude agotó su uso y pida continuar, Codex asume implementación, pruebas, datos, infraestructura y despliegue del encargo vigente, con las mismas reglas de aceptación. Al volver a Claude, actualizar el traspaso; no editar simultáneamente el mismo trabajo desde dos ejecutores principales. No hay conmutación automática ni garantía de un límite diario fijo.

Se autoriza delegación a agentes cuando haya subtareas independientes y sea útil. Máximo operativo habitual: tres trabajadores simultáneos. Asignar alcance de archivos; un integrador controla contratos y dependencias. Las definiciones de agentes/skills de Claude sirven como referencia de dominio y no se presumen funciones cargadas por Codex.

Autoridad técnica: leer el encargo vigente indicado en ESTADO.md. Ahora ETAPA_09_CLAUDE.md (T10R), tras revisar T10/9596d26 en REVISION_CODEX_09.md: corregir R07–R10 (limpieza/publicación, takeover, importación simultánea, recuperación del timer). No rehacer T10 ni repetir experimentos; agosto reservado y selección congelada intacta. T08R sigue aceptado. Mantener visible el inventario simulado. Azure for Students y Atlas Free ya creados; conexión/despliegue no verificados, sin gasto de bolsillo autorizado.

No alterar originales ni borrar la base v1. Reconstrucción nueva en v2, comparación y cambio local reversible forman parte del encargo. Commits locales para checkpoints están autorizados después de revisar exclusiones; no guardar secretos ni datos comerciales. Servicios de pago requieren presupuesto/acceso acordados. Preparar lo posible y pedir solo accesos realmente necesarios.

Actualizar TRASPASO.md por unidad de trabajo y ESTADO.md al terminar. Guardar evidencia de pruebas ejecutadas, no inferir éxitos por mensajes del ejecutor anterior. Conservar historial sin mezclarlo con el resumen vigente. No reiniciar el proyecto, descartar cambios ni repetir encargos cerrados para recuperar una conversación.
