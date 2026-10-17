# Traspaso vigente

- Ejecutor: Claude Code (Sonnet 5.5), 17/10/2026. Tarea: T06 (ETAPA_04_CLAUDE.md), tras la aprobación de T05 por Codex (REVISION_CODEX_04.md).
- Último paso terminado: T06 ejecutado y documentado; frente web acotado entregado. Nada en curso; sin procesos propios en segundo plano (df-mongo-dev activo).
- Commits: 286017d (protocolo+config ANTES de evaluar), 2c52c73 (código y pruebas), 00e4e64 (enmienda 1: tolerancia numérica en la repetición), y el commit final de entrega (HEAD, ver `git log`; resultados y estado).
- Pruebas: suite completa `RUN_REALDATA=1`: 94 aprobadas, 0 omitidas, 1 aviso, 74 s (`artifacts/private/t06/pytest_full.log`). Angular: `npm run build` y `npm test` (15 aprobadas). `ruff` limpio. Repetición de F1 equivalente (dif. máx. 1,1e-13); baselines idénticos a T05.
- Evidencia versionada: `docs/T06_PROTOCOLO.md`, `config/t06_config.json`, `docs/T06_RESULTADOS.md`, `T06_METRICAS.json`, `T06_MANIFIESTO.json`. Privada: `artifacts/private/t06/` (predicciones, modelos joblib), `artifacts/private/t06_run.log`.
- Resultado: SKU (criterio semanal) ningún ML supera la regla; propuesta provisional `promedio_28`. Categoría: Random Forest cumple la regla diaria por margen mínimo (2,07 %, 3/5 folds) pero es peor que los baselines en el bloque semanal. Desarrollo, no prueba final; sin mejora de inventario.
- Base activa: `demand_forecasting_v2`. Agosto no leído.
- Bloqueos: ninguno. Pendientes: sin precio; horizonte >7 días no evaluado (T07); API real/autenticación; Angular sin probar en navegador.
- Siguiente acción exacta: revisión de Codex de T06; luego T07 (simulación con horizonte lead time + revisión) y decisión sobre congelar selección y abrir agosto.
- Reproducir: `.venv\Scripts\python.exe -m scripts.run_t06` (≈7 min) y `$env:RUN_REALDATA="1"; .venv\Scripts\python.exe -m pytest -q`.
