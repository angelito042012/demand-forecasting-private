# Traspaso vigente

- Ejecutor: Claude Code, 17/10/2026. Tarea: corrección T08R (ETAPA_07_CLAUDE.md; R05, R06, presentación) terminada y entregada a revisión de Codex. Nada en curso; procesos propios detenidos al cerrar.
- Commits: ac8ee8b (señales exactas R05, identidad t08r-1, anclaje, R06), 7fcc99c (auditoría independiente), e2cae1f (presentación) y el commit final de ajuste de contrato de UI + documentación (HEAD, ver `git log`).
- Corridas en demand_forecasting_v2: **activa** `hist-20260710-4ea348836e35` (válida: 582 pedidos/2 655 uds.; auditoría independiente 0 diferencias); `hist-20260710-52b01cd999dd` **superseded** (R05) conservada. Usuarios locales demo_admin/demo_lector (credenciales solo en `artifacts/private/t08/e2e_credentials.json`, no versionado).
- Pruebas: pytest 254 aprobadas, 3 omitidas (RUN_REALDATA, no repiten T07); frontend 79 + build; E2E Chrome T08R 16/16. Logs/capturas privados en `artifacts/private/t08r/`. Reporte: `docs/T08R_REPORTE.md`; auditoría: `docs/T08R_AUDITORIA.json`.
- Pendientes declarados: límite de login no atómico y lease de publicación sin fencing (antes de exposición pública/T10/T11); T10 carga web/batch; T11 despliegue/HTTPS/respaldo (requiere accesos de nube de `docs/GUIA_LOCAL.md`); T12 ejecución final bajo `SELECCION_CONGELADA` (no ejecutada; agosto sin abrir); aceptación humana.
- Siguiente acción exacta: revisión de Codex de T08R; después T10 y la autorización de la ejecución final en el orden que decida.
- Iniciar para demostrar: `powershell -File scripts/start-local.ps1` (API con `--no-proxy-headers`), detener con `scripts/stop-local.ps1`.
