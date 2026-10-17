# Traspaso vigente

- Saliente: Codex, dirección/revisión, 17/10/2026 Lima. Próximo ejecutor Claude. Nada en curso; no se iniciaron servidores ni entrenamientos.
- Entrega revisada 960638d (T08), **aceptación completa pendiente R05–R06**. Revisión docs/REVISION_CODEX_07.md; encargo ETAPA_07_CLAUDE.md.
- Pruebas Codex: 118 selectivas aprobadas,1 aviso, 91.02 s y ruff correcto. Suite 226/frontend 42/Chrome 24 son evidencia Claude. No repetición de entrenamiento/suite real costosa.
- Auditoría real solo lectura: 3347 recomendaciones con snapshot;225 objetivos/118 pedidos inflados en 1 por precisión CSV. Fuentes/catálogo G4 y métricas T07 coinciden hoy con referencias aprobadas. Reproducción middleware confirmó IP controlable vía XFF.
- Evidencia privada: artifacts/private/codex_review07_audit.json, codex_review07_tests.xml, logs/capturas T08. No leer/imprimir e2e_credentials.json ni .env en el traspaso.
- Siguiente acción exacta: leer ETAPA_07_CLAUDE.md, comprobar Git/procesos; añadir regresión exacta que falle para R05 y corregir señal/publicación versionada. Después R06 y presentación; auditoría de 3347 SKU, pruebas pertinentes y navegador; entregar a revisión.
- Base activa demand_forecasting_v2; corrida actual hist-20260710-52b01cd999dd tiene recomendaciones defectuosas. Publicar nueva versión y marcar anterior sustituida, sin borrar evidencia/ventas/usuarios/v1. df-mongo-dev útil; procesos web/API de Claude detenidos, verificar al retomar.
- Agosto reservado, selección congelada sin ejecutar. No T10 ni entrenamiento T06/T07 en este encargo. Posteriores carga/batch, evaluación final, nube/restauración y cierre académico. Sin cuentas/presupuesto de nube.
