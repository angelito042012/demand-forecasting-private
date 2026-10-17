# Traspaso vigente

- Ejecutor: Claude Code (Sonnet 5.5), 17/10/2026, America/Lima. Tarea: T05 (ETAPA_03_CLAUDE.md), tras la aceptación de R04/v2/T04 por Codex (REVISION_CODEX_03.md).
- Último paso terminado: T05 ejecutado y documentado; Angular base generada y compilada. Nada en curso; sin procesos propios en segundo plano (df-mongo-dev sigue activo).
- Commits locales: d763bed (protocolo y config congelados ANTES de evaluar), 0ce411d (código y pruebas), commit de `scripts/run_t05.py` con lectura automática (el manifiesto registra el HEAD de la ejecución) y commit final de entrega (HEAD, ver `git log`).
- Pruebas: suite completa `RUN_REALDATA=1`: 83 aprobadas, 0 omitidas, 1 aviso, 71 s (log: `artifacts/private/t05/pytest_full.log`). `ruff` limpio. Repetición de la evaluación T05: predicciones y métricas idénticas. `ng test` de Angular no ejecutado.
- Evidencia versionada: `docs/T05_PROTOCOLO.md`, `config/t05_config.json`, `docs/T05_RESULTADOS.md`, `docs/T05_METRICAS.json`, `docs/T05_MANIFIESTO.json` (hashes de config, código, datos, fuentes y versiones), `docs/REMEDIACION_FUENTES.md`. Privada (fuera de Git): `artifacts/private/t05/predicciones.csv.gz`.
- Resultado resumido: en SKU diario ningún baseline supera al control cero (WAPE 1,43 / 1,63 / 1,54 frente a 1,00); en categoría los tres lo superan (WAPE ≈ 0,40–0,44). Referencia T06 por regla previa: `ultimo_dia`, con esa salvedad. Detalle en T05_RESULTADOS.md.
- Base activa: `demand_forecasting_v2`; v1 conservada (solo consulta). Fingerprint T04 actualizado (incluye unidad_base); hashes de contenido de las series sin cambio.
- Angular: `frontend/` con Angular CLI 21.2.27, `npm run build` correcto, `package-lock.json` conservado; sin pantallas.
- Bloqueos: ninguno.
- Siguiente acción exacta: revisión de Codex de T05; luego T06 (ML) comparando contra `ultimo_dia`, `promedio_28` y el control cero; agosto sigue reservado hasta congelar la selección.
- Reproducir: `.venv\Scripts\python.exe -m scripts.run_t05` y `$env:RUN_REALDATA="1"; .venv\Scripts\python.exe -m pytest -q`.

Campos mínimos al actualizar: ejecutor; fecha; tarea; último paso; paso en curso; archivos; commit; comandos y resultado; evidencia; base activa; procesos; bloqueos; siguiente acción; pendiente de revisión. No escribir claves ni URI con credenciales. Una prueba no ejecutada se indica como tal.
