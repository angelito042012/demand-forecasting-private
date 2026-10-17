# Traspaso vigente

- Registro: Codex, 17/10/2026. Entrega revisada: T05, commit dff7d27; aprobación en REVISION_CODEX_04.md.
- Ejecutor previsto: Claude Code. Codex no implementó T06; preparó revisión y encargo.
- Verificación independiente: 14 pruebas focalizadas aprobadas; estilo correcto; hashes config/código/predicciones comprobados; 125391 predicciones sin agosto ni claves duplicadas; 24 grupos de métricas agregadas recalculados con coincidencia. Suite completa de 83: log de Claude, sin repetirla.
- Resultado: los baselines no nulos no superan cero en WAPE diario SKU; promedio_28 marginalmente mejor en bloque semanal; categorías con mejores resultados. ultimo_dia es referencia entre no nulos por regla preregistrada. No representa mejora de inventario.
- Encargo siguiente: ETAPA_04_CLAUDE.md (T06). Primer paso: protocolo/config de modelos, features, criterios y cómputo antes de ejecutar. Random Forest y un boosting acotados; cinco folds de T05, marzo-julio; todos los baselines como comparación.
- Criterio de evaluación de desarrollo: SKU por bloque semanal con cambio declarado previamente, métricas diarias conservadas; categoría criterio diario más bloque. No comparar universos distintos ni ocultar control cero o resultados desfavorables.
- Base activa registrada: demand_forecasting_v2; v1 conservada. Solo pruebas temporales se escribieron en esta revisión. No nueva carga/migración de datos reales.
- Angular base creada y compilada por Claude en T05. Se permite un frente web acotado independiente según el encargo, con mocks/demostración identificados.
- Datos/evidencia: artifacts/private/t05/predicciones.csv.gz; docs/T05_PROTOCOLO.md, T05_RESULTADOS.md, T05_METRICAS.json y T05_MANIFIESTO.json.
- Detener antes de abrir agosto o declarar selección final/impacto en inventarios. Entregar evidencias para revisión de Codex.
- Mantener este registro breve; logs extensos por ruta. Guardar checkpoints y actualizar el traspaso durante el trabajo.
