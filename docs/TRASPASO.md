# Traspaso vigente

- Responsable saliente: Codex, dirección/revisión, 17/10/2026, Lima. Próximo ejecutor: Claude Code. Nada en curso por Codex; esta revisión no inició entrenamientos ni procesos persistentes.
- Último paso: T07 aceptado al commit 5790103; revisión docs/REVISION_CODEX_06.md. Cambios de Codex: documentación y auditoría privada, sin modificar código funcional ni bases.
- Verificación independiente: 22 pruebas selectivas aprobadas; ruff correcto. Hashes código/config/artefactos y 13 modelos; 293853 predicciones, 160 grupos de métricas SKU recalculados; saldos diarios y métricas totales de las 27 combinaciones verificados. No se repitió entrenamiento ni integración real extensa. Las 117 pruebas completas son resultado de Claude.
- Evidencia: docs/T07_*, artifacts/private/t07/ y artifacts/private/codex_review06_audit.json. RF pierde contra promedio_28; mayor servicio simulado con más stock/compras no acredita mejor pronóstico ni impacto real.
- Base activa demand_forecasting_v2; v1/Excel conservados. df-mongo-dev útil, comprobar estado al retomar. Agosto reservado.
- Siguiente acción exacta: leer ETAPA_06_CLAUDE.md y verificar Git/procesos; endurecer entradas/chequeo diario del motor; fijar contrato antes de delegar backend, adaptador/persistencia y frontend.
- Encargo T08 + lectura T09: API autenticada, sesión/roles, persistencia de corrida histórica al 10/07 y pantallas reales. Congelar protocolo final/método promedio_28, RF comparador, sin ejecutar agosto. No reentrenar T06/T07.
- Bloqueos: ninguno para integración local. Azure/Atlas y presupuesto/accesos pendientes para publicación posterior; no contratar recursos. Backend actualmente healthcheck, frontend con mocks: no confundir con flujo integrado.
- Cierre esperado: evidencia API/permisos/publicación y navegador, guía de inicio, commit, ESTADO/TRASPASO/BACKLOG/HISTORIAL actualizados; entregar a revisión. Posteriores: carga web/batch, test final congelado, despliegue/restauración e informe.
