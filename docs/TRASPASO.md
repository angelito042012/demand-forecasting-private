# Traspaso vigente

- Ejecutor: Claude Code (Sonnet 5.5), 17/10/2026. Tarea: T07 (ETAPA_05_CLAUDE.md). Estado: terminado y entregado a revisión de Codex; nada en curso; sin procesos propios en segundo plano (df-mongo-dev activo).
- Commits: 9419d2f (inferencia coherente), 325da2f (protocolo/config T07 antes de resultados), e3c38c3 (motor, pronóstico, pruebas), siguiente (cobertura/cohortes/lectura tras revisión independiente) y commit final de entrega (HEAD; `git log`). El manifiesto registra el commit de la ejecución.
- Pruebas: suite completa RUN_REALDATA=1 117 aprobadas, 0 omitidas, 346 s (antes de ajustes solo de reporte); después 16 pruebas (tests/sim + test_t07_functions) aprobadas y ejecución completa de scripts.run_t07 con repetición idéntica. Logs: `artifacts/private/t07/pytest_full.log`, `artifacts/private/t07_run.log`, `artifacts/private/t07_tests.log`. Angular no tocado en T07.
- Evidencia versionada: `docs/T07_PROTOCOLO.md`, `config/t07_config.json`, `docs/T07_RESULTADOS.md`, `T07_METRICAS.json`, `T07_MANIFIESTO.json`. Privada: `artifacts/private/t07/` (modelos, predicciones por fold, series de simulación).
- Resultado: RF distribuido no cumple la regla (WAPE H14 0,929 frente a 0,873 de promedio_28; 0/4 folds); promedio_28 supera al cero en acumulados. Simulación L=7,S=7: fill rate 0,741 / 0,797 / 0,809 (referencia fija / promedio_28 / RF) con más stock y compras en ese orden; nueve escenarios en T07_RESULTADOS.md. Etiqueta: inventario simulado con supuestos; no es inventario real.
- Base activa: demand_forecasting_v2. Agosto no consultado (ni ventas ni movimientos sintéticos).
- Bloqueos: ninguno. Pendientes: API funcional/autenticación, conexión de pantallas, publicación (sin cuenta/presupuesto), congelación de selección y prueba final de agosto tras revisión de Codex.
- Siguiente acción exacta: revisión de Codex de T07; luego integración/API y congelación de selección antes de abrir agosto.
- Reproducir: `.venv\Scripts\python.exe -m scripts.run_t07` (≈3 min) y `$env:RUN_REALDATA="1"; .venv\Scripts\python.exe -m pytest -q`.
