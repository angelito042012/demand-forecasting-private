# Traspaso vigente

- Ejecutor: Claude Code, 17/10/2026. Tarea en curso: T10 (ETAPA_08_CLAUDE.md): carga web, cola durable, generación promedio_28 y temporizador. T08R aceptado (80117c0).
- Hecho y comprometido: (1) garantías de concurrencia: login con reserva atómica (`backend/app/auth/budget.py`), cola durable (`pipeline/jobs/queue.py`), publicación con propiedad por intento/fencing (`pipeline/publish/protocol.py`, lectores por `children_ref`), pruebas deterministas de dos workers; (2) contrato `docs/T10_CONTRATO.md` y `config/t10_config.json`; (3) registro de procesos con hora de inicio/ejecutable en start/stop-local.
- En curso: tres agentes con ámbitos disjuntos (API/subidas; worker/generador/temporizador; frontend). Después: integrar, E2E en navegador con worker real, auditoría, reporte T10, docs.
- Base real demand_forecasting_v2: corrida activa hist-20260710-4ea348836e35 (publicada con el código anterior; sigue válida y auditada). Agosto no consultado. Procesos propios: ninguno en ejecución.
- Si la sesión se interrumpe: `git status` (archivos de los agentes sin commit), ejecutar pruebas por ámbito y continuar la integración.
