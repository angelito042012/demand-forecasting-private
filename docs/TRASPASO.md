# Traspaso vigente

- Ejecutor: Claude Code, 17/10/2026. **T10 entregado para revisión de Codex** (ETAPA_08_CLAUDE.md); T08R aceptado (80117c0). Reporte: `docs/T10_REPORTE.md`; contrato: `docs/T10_CONTRATO.md`.
- Hecho: concurrencia (login atómico, cola con fencing, publicación por intento), API de carga/corridas/trabajos, validación de Excel, generación `promedio_28` exacta, worker, temporizador, frontend admin, registro de procesos. 376 pytest + 106 vitest + E2E Chrome 16/16; evidencias en `artifacts/private/t10/`.
- Decisiones abiertas para Codex: (1) ¿la corrida generada debe activar el puntero? (hoy no); (2) unificar validadores de publicación; (3) T11 requiere accesos de nube (ver GUIA_LOCAL) y presupuesto; (4) autorizar T12 (abre agosto).
- Base `demand_forecasting_v2`: corrida activa `hist-20260710-4ea348836e35`; hay corridas generadas de prueba y una en `staging` (`gen-20260620-…`). Agosto no consultado; selección congelada intacta.
- Procesos: `scripts/start-local.ps1` (API + web + worker, registro en `artifacts/private/t08/procesos.json`); `scripts/stop-local.ps1`. Credenciales demo solo en `artifacts/private/t08/e2e_credentials.json` (no versionado).
- Si se interrumpe: `git status`, `pytest tests -q`, revisar `docs/T10_REPORTE.md` §3.
