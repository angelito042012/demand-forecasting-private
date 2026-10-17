# Traspaso vigente

- Ejecutor: Claude Code, 17/10/2026. **T12 (evaluación final de agosto bajo selección congelada) ejecutada una vez y entregada para revisión de Codex** (ETAPA_10_CLAUDE.md). Protocolo: `docs/T12_PROTOCOLO.md`; resultados: `docs/T12_RESULTADOS.md`, `T12_METRICAS.json`, `T12_MANIFIESTO.json`; sello previo: `docs/T12_SELLO.json` (commit 86325a7); código/pruebas: a39d3e9.
- Hallazgo primario: WAPE H14 SKU primaria común: promedio_28 0,7810, RF 0,7910, cero 1,0000. RF no mejora ni puede declararse ganador (un solo bloque); el método operativo no cambia. Simulación: más servicio coincide con más stock/compras. Detalle y límites en el reporte.
- Estado de ejecución: todas las fases completas (`artifacts/private/final/estado.json`), auditoría aprobada, sin repeticiones técnicas ni correcciones tras leer el test. Selección congelada, base v1/v2, Excel y puntero histórico intactos (solo lectura).
- No hecho: despliegue, T11, publicación del paquete en web/Mongo, aceptación humana. Azure for Students y Atlas Free sin conectar; sin presupuesto de bolsillo; base local 459,39 MB: T11 requiere plan de capacidad/restauración antes de publicar.
- Decisiones abiertas para Codex: (1) revisión de T12 y de la lectura de resultados; (2) cómo integrar el paquete final (importar solo el resumen vs. artefactos completos) con capacidad verificada; (3) T11/T13/T14/T15 antes del 23/10.
- Si se interrumpe: `git status`, `python -m scripts.run_final status`, leer `docs/T12_PROTOCOLO.md`; no repetir `evaluate` (las fases completas se reutilizan).
