# Traspaso vigente

- Registro: Codex, revisión de la entrega de Claude al commit 269e15b, 17/10/2026.
- Ejecutor previsto: Claude Code. Ninguna nueva implementación de T05 iniciada por Codex.
- Hito: R04/v2/T04 aceptados para seis fuentes canónicas. Ver docs/REVISION_CODEX_03.md.
- Verificación Codex: 20 pruebas seleccionadas aprobadas; estilo correcto; hashes de artefactos y controles de las 459375 filas SKU-día comprobados. Suite completa de 65: reportada por Claude, no repetida por Codex.
- Base activa registrada: demand_forecasting_v2, 86877 ventas y 560 créditos, comparada con v1 mediante evidencia guardada. v1 conservada. No se modificaron bases en esta revisión; pruebas de fuentes usaron bases temporales aisladas.
- Artefactos T04: artifacts/private/t04/; metadatos: docs/T04_FIRMA.json y docs/T04_PERFIL_CALIDAD.md.
- Nueva instrucción: ETAPA_03_CLAUDE.md. Primer paso: cerrar detalles menores de reutilización, después fijar protocolo antes de ejecutar baselines.
- Datos: cerca de 88% de ceros observados; baselines y cobertura deben tratar intermitencia y productos nuevos explícitamente. Cada fold reconstruye su conocimiento al corte; no reutilizar el catálogo/población final de julio para mayo/junio.
- Angular: npm ping reportado operativo; se permite intentar preparación/compilación en paralelo con archivos separados. No desactivar TLS; no bloquear T05 si falla.
- Salida esperada: baselines y folds en marzo-julio, métricas con cobertura y sesgo, pruebas/evidencia, hashes/commit y traspaso breve. No Random Forest/boosting ni apertura de agosto todavía.
- Registros extensos anteriores: docs/HISTORIAL_ENTREGAS.md. Mantener este archivo breve y actualizar durante el trabajo.
