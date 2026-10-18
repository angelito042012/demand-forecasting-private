# Instrucciones compartidas para Codex en este proyecto

Leer docs/PROTOCOLO_TRABAJO.md, docs/ESTADO.md, docs/TRASPASO.md, CLAUDE.md y docs/DECISIONES_DATOS.md antes de editar. Las decisiones más recientes del usuario prevalecen sobre registros históricos. No asumir que una sesión perdida borró los archivos.

El usuario designa Claude Code como ejecutor habitual y Codex como director/revisor. Cuando avise que Claude agotó su uso y pida continuar, Codex asume implementación, pruebas, datos, infraestructura y despliegue del encargo vigente, con las mismas reglas de aceptación. Al volver a Claude, actualizar el traspaso; no editar simultáneamente el mismo trabajo desde dos ejecutores principales. No hay conmutación automática ni garantía de un límite diario fijo.

Se autoriza delegación a agentes cuando haya subtareas independientes y sea útil. Máximo operativo habitual: tres trabajadores simultáneos. Asignar alcance de archivos; un integrador controla contratos y dependencias. Las definiciones de agentes/skills de Claude sirven como referencia de dominio y no se presumen funciones cargadas por Codex.

Autoridad vigente: ETAPA_16_CLAUDE.md y docs/UX01_BRIEF.md. El usuario probó la demo y no comprende su uso: rediseñar interfaz, lenguaje y recorrido inicial antes de publicar. Implementación local autorizada, no solo maqueta/colores. R12–R16 aceptados localmente (REVISION_CODEX_13/15); no repetir modelos, T12 ni preflight Azure. Publicación condicional de ETAPA_15 diferida: no existe autorización de gasto/transferencias. Mantener demo df-demo y base común; preservar cifras y advertencias históricas/simuladas. Aceptación humana pendiente con observación de comprensión insuficiente; volver a probar tras UX01.

No alterar originales ni borrar la base v1. Reconstrucción nueva en v2, comparación y cambio local reversible forman parte del encargo. Commits locales para checkpoints están autorizados después de revisar exclusiones; no guardar secretos ni datos comerciales. Servicios de pago requieren presupuesto/acceso acordados. Preparar lo posible y pedir solo accesos realmente necesarios.

Actualizar TRASPASO.md por unidad de trabajo y ESTADO.md al terminar. Guardar evidencia de pruebas ejecutadas, no inferir éxitos por mensajes del ejecutor anterior. Conservar historial sin mezclarlo con el resumen vigente. No reiniciar el proyecto, descartar cambios ni repetir encargos cerrados para recuperar una conversación.
