# Traspaso vigente

- Responsable saliente: Codex, dirección/revisión, 17/10/2026, America/Lima. Próximo ejecutor: Claude Code.
- Último paso: T06 aceptado como experimento al commit 3b11fbd; revisión docs/REVISION_CODEX_05.md. Nada implementado/reentrenado por Codex en esta revisión; solo documentos de revisión/continuidad.
- Verificación Codex: 11 pruebas selectivas aprobadas y estilo correcto; hashes comprobados, 125391 predicciones sin agosto ni claves duplicadas, identidad de columnas T05; 36 grupos de métricas recalculados coincidentes. Suite completa 94 y build/15 Angular son evidencia de Claude, no repetición independiente.
- Resultado: no ganador ML por SKU; promedio_28 provisional. RF categoría mejora diaria mínima, empeora acumulado semanal. No mejora de inventario demostrada.
- Base activa: demand_forecasting_v2; v1 y Excel preservados. df-mongo-dev útil. Claude indicó no dejar procesos propios; comprobar procesos al retomar. No hay entrenamiento iniciado por Codex.
- Siguiente acción exacta: leer ETAPA_05_CLAUDE.md; comprobar Git/servicios; corregir validación de contexto/vocabulario de inferencia. Después comprometer protocolo/config T07 antes de evaluar horizontes 10/14/21 y simular junio-julio.
- Alcance: referencia fija sintética, promedio_28 y RF categoría distribuido, mismos supuestos entre políticas; parámetros iniciales solo hasta 31/05. Nueve escenarios L=3/7/14 y S=0/7/14. Agosto reservado, sin selección final.
- Bloqueos: ninguno para desarrollo local. Falta cuenta/acceso/presupuesto para publicar posteriormente. Frontend sigue con mocks; API/auth/integración posteriores.
- Evidencia histórica: artifacts/private/t06/, docs/T06_*.md/json. Logs fuera del resumen. Mantener ESTADO/TRASPASO/HISTORIAL/BACKLOG y commits al cerrar T07; entregar a revisión.
