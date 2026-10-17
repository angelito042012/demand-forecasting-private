# Traspaso entre ejecutores

## Registro actual

- Fecha del registro: 17/10/2026, America/Lima.
- Ejecutora prevista: Claude Code. Codex preparó este registro; no se ha comprobado que una nueva sesión Claude esté ejecutando el encargo.
- Encargo: ETAPA_02_CLAUDE.md, revisado en docs/REVISION_CODEX_02.md.
- Último hito aceptado: R01–R03 para las seis fuentes canónicas. Suite verificada por Codex en la entrega anterior: 46 pruebas aprobadas y un aviso.
- Inspección de recuperación: existen API básica, importador v2, conciliación, calendario/catálogo y training_access.py. No se encontraron archivos de implementación de T04 ni de R04. Git no tiene commits; los archivos siguen sin seguimiento. No hay frontend/.
- Base activa registrada: demand_forecasting_dev con esquema v1. Última verificación anterior: 86 877 ventas y 560 notas de crédito. No se volvió a consultar MongoDB en esta recuperación; la nueva sesión debe comprobar el estado vivo.
- Base v2: no consta completada. Si existe ya, inspeccionarla antes de cargar o cambiar configuración.
- Servicios: df-mongo-dev fue el contenedor de desarrollo utilizado. Comprobar su estado actual sin recrear ni eliminar otros contenedores.
- Primer paso: revisar estado vivo, crear checkpoint local sin secretos y luego cerrar R04 con pruebas.
- Próximo paso tras R04: preparar/comparar v2 y completar perfil, diccionario y series diarias de marzo-julio.
- Detención de esta entrega: entregar evidencia para revisión de Codex antes de entrenar.

## Actualización obligatoria durante el trabajo

Reemplazar el registro actual con hechos comprobados al cambiar de etapa o ejecutor. Conservar detalles anteriores relevantes en HISTORIAL_ENTREGAS.md.

Campos mínimos: ejecutor; fecha; tarea; último paso terminado; paso en curso; archivos; commit/checkpoint; comandos y resultado; evidencia; base activa; procesos útiles; bloqueos; siguiente acción exacta; pendiente de revisión.

No escribir claves, tokens o URI con credenciales. Si una prueba no se ejecutó o un proceso dejó de ser observable, indicarlo.
