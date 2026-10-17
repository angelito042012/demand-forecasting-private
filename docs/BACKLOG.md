# Backlog de ejecución

Estado al 17/10: T08R aceptado; R05/R06 cerrados. T10/9596d26 revisado: requiere **T10R (ETAPA_09_CLAUDE.md, REVISION_CODEX_09.md), R07–R10** antes de aceptación. Codex119 pruebas verdes y cuatro casos de fallo adicionales reproducidos. Azure estudiantes y Atlas Free ya creados, sin despliegue/conexión verificados ni presupuesto de bolsillo; BD459,39MB requiere plan de capacidad. Agosto reservado; fechas de tabla son objetivos, no evidencia. Ver ESTADO/TRASPASO.

T01 está parcial; T03 fue aceptado para las seis fuentes auditadas tras corregir R01–R03. T02A tiene archivos y controles de importación, pero no conciliación con un reporte externo de la MYPE. Las reglas de datos están definidas en DECISIONES_DATOS.md. T04–T07 aceptados como desarrollo. T08 y lectura T09 aceptados tras T08R; T10 y posteriores pendientes. Método operativo v1 promedio_28; RF comparador, no ganador. Congelación final documentada en T08 antes de abrir agosto. Las horas son estimaciones, no resultados ni compromisos de los integrantes. Ver estimación global en ANALISIS_Y_PLAN.md.

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
| T10 | Flujo local construido; T10R pendiente R07–R10, ETAPA_09_CLAUDE.md | T06–T08 | Fabricio y Rogelio | 20 | A11; cierre regresiones de concurrencia/recuperación |
| T11 | Despliegue de prueba, backups y restauración | Accesos, T08–T10 | Fabricio | 21 | A12–A13 |
| T12 | Evaluación final reservada e impacto | T06–T07 congelados | Blanca y Mauro | 21 | Informe reproducible sin cambiar selección |
| T13 | Revisión independiente y aceptación | T09–T12 | Fabricio / quality-reviewer | 22 | A14, sin críticos |
| T14 | Informe, manual, fuentes y video | Evidencia acumulada | Milton y equipo | 23 | Anexos y conclusiones verificables |
| T15 | Versión final y entrega | T13–T14 | Rogelio y Milton | 23, 18:00 Lima | Repositorio, URL, copia recuperable |

Antes de marcar una tarea completa: enlazar evidencia, pruebas ejecutadas, versión del código y limitaciones. Si una dependencia falta, marcar bloqueada y avanzar en una tarea independiente; no convertirla en completada por tener una pantalla de ejemplo.
