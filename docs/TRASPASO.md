# Traspaso vigente

- Ejecutor: Claude Code, 17/10/2026. Tarea: T08 + lectura integrada T09 (ETAPA_06_CLAUDE.md), terminada y entregada a revisión de Codex. Nada en curso.
- Commits: d59703b (motor + contrato), c49160c (selección congelada), 03cf93c (auth), a442983 (frontend), ff8b030 (publicador/rutas), y el commit final de entrega (HEAD; ver `git log`).
- Pruebas: suite integral RUN_REALDATA=1 → 226 aprobadas, 0 omitidas, 509 s (`artifacts/private/t08/pytest_full.log`); frontend 42 aprobadas + build; E2E navegador real 24/24 (`artifacts/private/t08/e2e_resultado.json`, capturas en `artifacts/private/t08/screens/`, privadas). Reporte: `docs/T08_REPORTE.md`.
- Estado de la base real `demand_forecasting_v2`: ventas importadas + colecciones nuevas `runs`, `run_pointer`, `forecasts`, `recommendations`, `backtests`, `users` (demo_admin, demo_lector), `sessions`, `login_attempts`. Corrida activa `hist-20260710-52b01cd999dd`. Credenciales locales de demostración solo en `artifacts/private/t08/e2e_credentials.json` (no versionado, no impreso). v1 y Excel intactos.
- Procesos: al cerrar se detienen los propios con `scripts/stop-local.ps1`; para usar la app: `scripts/start-local.ps1` (ver `docs/GUIA_LOCAL.md`). df-mongo-dev sigue activo y no se tocó.
- Congelación: `docs/SELECCION_CONGELADA.md` + `config/seleccion_congelada.json`: preparada, NO ejecutada; agosto y reference_v1 sin consultar.
- Bloqueos: ninguno. Pendientes: T10 (carga web/batch), T11 (despliegue HTTPS, respaldo/restauración; requiere accesos de nube listados en la guía), T12 (ejecución final bajo congelación revisada), aceptación humana e informe.
- Siguiente acción exacta: revisión de Codex de T08; luego decidir T10 y la autorización de la ejecución final.
