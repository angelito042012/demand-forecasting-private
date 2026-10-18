# Backlog de ejecución

**UX01R entregado (docs/UX01R_REPORTE.md; R17 cerrado, Evaluación simplificada); pendiente la nueva prueba de comprensión de Rogelio y la revisión de Codex.** R12–R16 aceptados localmente; no repetir. A13 (nube) y A14 (participación humana) pendientes; T14 debe reflejar las pantallas finales; T15 hasta el 23/10. Publicación en nube solo con autorización explícita.

Estado al 17/10: R12-R14 aceptados localmente; R15/R16 cerrados (T13B); demostración local activa en https://localhost:8443; publicación en nube pendiente de una única autorización (docs/T11_PLAN_DESPLIEGUE.md); aceptación humana (A14) y A13 pendientes; T14 final y T15 hasta el 23/10.

T01 está parcial; T03 aceptado para seis fuentes auditadas tras R01–R04. T02A tiene controles de importación pero no conciliación con reporte externo de la MYPE. T04–T07 aceptados como desarrollo; T08/T09/T10 aceptados para alcance local. Resultados T12 validados, cierre administrativo R11 pendiente; T11A es el encargo vigente, T11real/T13–T15 pendientes. Método operativo promedio_28; RF comparador, no ganador. Congelación registrada antes del test; no modificarla para acomodar resultados. Ver ANALISIS_Y_PLAN.md y DECISIONES_DATOS.md.

| ID | Entrega | Dependencia | Responsable / agente | Fecha objetivo | Aceptación |
|---|---|---|---|---|---|
| T01 | Adoptar repo, fijar versiones, estructura, CI básica | Ruta del repo o ausencia confirmada | Rogelio / principal | 17 | Instalación limpia y healthcheck |
| T02A | Ventas recibidas: conciliar y cerrar reglas de limpieza y uso | Archivos actuales + MYPE | Mauro / data-engineer | 17 | Manifiesto, conciliación, diccionario |
| T02B | Integrar escenario sintético ya generado y sus supuestos | reference_v1 y DECISIONES_DATOS.md | Rogelio | 17 | Procedencia visible, balance y cobertura |
| T03 | Importador validado e idempotente | T01, formato | Mauro / data-engineer | 17 | A01–A02 |
| T04 | Serie diaria, perfil y conciliación | T02A, T03 | Mauro / data-engineer | 18 | Totales y tratamiento de faltantes |
| T05 | Baselines, folds, features sin fuga | T04 | Blanca / forecasting | 18 | A03–A05 |
| T06 | RF y boosting, selección provisional; final pendiente | T05 | Blanca / forecasting | 19 | Registro de experimentos |
| T07 | Simulación de referencia sintética y política con ML | T02B, T05 | Rogelio / backend-inventory | 19 | A06–A08 |
| T08 | API autenticada y persistencia versionada | T01, contratos | Rogelio / backend-inventory | 20 | A09 |
| T09 | Pantallas conectadas, filtros y estados | T08; mocks antes | Fabricio / frontend | 20 | A10 |
| T10 | Flujo local aceptado tras T10R/6212f6a | T06–T08 | Fabricio y Rogelio | 20 | A11 local; revisión10 y59 pruebas |
| T11 | T11B vigente: R12–R14, generación en imagen/recuperación integral y preflight; despliegue pendiente | Accesos, T08–T10 | Fabricio | 21 | A12–A13 |
| T12 | Resultados validados por Codex11; cierre de checkpoints R11 pendiente | T06–T07 congelados; T10 aceptado | Blanca y Mauro | 21 | Predicción fija/simulación separadas, auditoría, sin re-selección |
| T13 | Revisión independiente y aceptación | T09–T12 | Fabricio / quality-reviewer | 22 | A14, sin críticos |
| T14 | Informe, manual, fuentes y video | Evidencia acumulada | Milton y equipo | 23 | Anexos y conclusiones verificables |
| T15 | Versión final y entrega | T13–T14 | Rogelio y Milton | 23, 18:00 Lima | Repositorio, URL, copia recuperable |

Antes de marcar una tarea completa: enlazar evidencia, pruebas ejecutadas, versión del código y limitaciones. Si una dependencia falta, marcar bloqueada y avanzar en una tarea independiente; no convertirla en completada por tener una pantalla de ejemplo.
