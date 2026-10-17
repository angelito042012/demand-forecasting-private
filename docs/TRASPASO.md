# Traspaso vigente

- Ejecutor: Claude Code, 17/10/2026. **T10R entregado para revisión de Codex** (ETAPA_09_CLAUDE.md; revisión `docs/REVISION_CODEX_09.md`). Reporte: `docs/T10R_REPORTE.md`; semántica final: `docs/T10_CONTRATO.md` §8. T10 (9596d26) conservado, no rehecho.
- Hecho: R07 (reserva CAS antes de limpiar generaciones), R08 (toma de control con lease leído), R09 (reserva durable de una fuente por mes con valla de escritura), R10 (recuperación de ranuras del temporizador; `--loop` real probado). 408 pytest aprobadas / 6 omitidas; regresiones fallaban antes. Evidencias: `artifacts/private/t10r/`.
- Corrida staging `gen-20260620-…`: ahora `failed/INTENTO_ABANDONADO` (conservada); recuperación = nueva `Idempotency-Key` para el origen 20/06 (no ejecutada).
- Decisiones abiertas para Codex: (1) T12 (abre agosto) y T11 (accesos/capacidad: 459,39 MB, sin presupuesto de bolsillo); (2) reserva de mes también en el importador CLI; (3) validadores de publicación duplicados.
- Base `demand_forecasting_v2`: histórica activa `hist-20260710-4ea348836e35` intacta; hay corridas generadas de prueba (no evidencia de mejora). Agosto no consultado; selección congelada intacta. Sin procesos propios en ejecución.
- Si se interrumpe: `git status`, `pytest tests -q`, leer `docs/T10R_REPORTE.md`.
