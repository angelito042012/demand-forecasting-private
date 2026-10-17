# Instrucciones compartidas para Codex en este proyecto

Leer docs/PROTOCOLO_TRABAJO.md, docs/ESTADO.md, docs/TRASPASO.md, CLAUDE.md y docs/DECISIONES_DATOS.md antes de editar. Las decisiones más recientes del usuario prevalecen sobre registros históricos. No asumir que una sesión perdida borró los archivos.

El usuario designa Claude Code como ejecutor habitual y Codex como director/revisor. Cuando avise que Claude agotó su uso y pida continuar, Codex asume implementación, pruebas, datos, infraestructura y despliegue del encargo vigente, con las mismas reglas de aceptación. Al volver a Claude, actualizar el traspaso; no editar simultáneamente el mismo trabajo desde dos ejecutores principales. No hay conmutación automática ni garantía de un límite diario fijo.

Se autoriza delegación a agentes cuando haya subtareas independientes y sea útil. Máximo operativo habitual: tres trabajadores simultáneos. Asignar alcance de archivos; un integrador controla contratos y dependencias. Las definiciones de agentes/skills de Claude sirven como referencia de dominio y no se presumen funciones cargadas por Codex.

Autoridad técnica: leer el encargo vigente indicado en ESTADO.md. Ahora ETAPA_05_CLAUDE.md (T07), tras aceptar T06 en REVISION_CODEX_05.md. Corregir coherencia de inferencia y evaluar horizontes 10/14/21 y simulación junio-julio con protocolo previo; agosto reservado. No repetir etapas cerradas. Verificar código vivo antes de retomar. No entrenar hasta aprobar datos; agosto sigue reservado. Mantener siempre visible el carácter sintético del inventario generado.

No alterar originales ni borrar la base v1. Reconstrucción nueva en v2, comparación y cambio local reversible forman parte del encargo. Commits locales para checkpoints están autorizados después de revisar exclusiones; no guardar secretos ni datos comerciales. Servicios de pago requieren presupuesto/acceso acordados. Preparar lo posible y pedir solo accesos realmente necesarios.

Actualizar TRASPASO.md por unidad de trabajo y ESTADO.md al terminar. Guardar evidencia de pruebas ejecutadas, no inferir éxitos por mensajes del ejecutor anterior. Conservar historial sin mezclarlo con el resumen vigente. No reiniciar el proyecto, descartar cambios ni repetir encargos cerrados para recuperar una conversación.
