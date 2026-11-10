# Matriz de cobertura de requisitos

**Fecha:** 2026-11-10
**Proyecto:** Sistema de previsión de demanda y compras — Capstone
**Evaluación:** 13/11/2026

---

## Requisitos funcionales

| ID | Requisito | Módulo / Archivo | Prueba | Evidencia | Estado |
|---|---|---|---|---|---|
| RF01 | Importar datos de ventas desde Excel | `scripts/import_operativo.py` | `preview` valida sin escribir; `importar` carga | `docs/MANUAL_OPERACION.md` | Implementado |
| RF02 | Importar datos de stock desde Excel | `scripts/import_operativo.py` | Misma CLI con archivo de existencias | `docs/MANUAL_OPERACION.md` | Implementado |
| RF03 | Generar pronóstico de demanda (promedio_28) | `pipeline/plan/engine.py`, `pipeline/plan/sales.py` | `tests/plan/` (324 aprobadas) | `docs/T10_REPORTE.md`, `T19_REPORTE.md` | Implementado |
| RF04 | Calcular compra recomendada por producto | `pipeline/plan/engine.py` | Simulación con escenarios L7/L14 | `docs/T19_REPORTE.md`, `T22_PILOTO_COMPRA_RECOMENDADA.md` | Implementado |
| RF05 | Consultar ventas previstas por categoría | `backend/app/routes/`, `frontend/` | Frontend 280/280, build OK | `docs/UX01_REPORTE.md` | Implementado |
| RF06 | Consultar compra recomendada con filtros | `frontend/`, `backend/app/routes/` | Navegador 25/25 | `docs/T19_REPORTE.md` | Implementado |
| RF07 | Autenticación con roles (lector/admin) | `backend/app/auth/` | Tests backend, `seg_publica.mjs` | `docs/T08_REPORTE.md` | Implementado |
| RF08 | Consultar inventario informado | `backend/app/routes/inventory.py` | Tests inventario 99 aprobadas | `docs/T18_REPORTE.md` | Implementado |
| RF09 | Generar plan desde la interfaz web | `frontend/`, `backend/app/routes/` | Cola durable, worker | `docs/T10_REPORTE.md` | Implementado |
| RF10 | Cargar archivo Excel desde la interfaz | `backend/app/routes/uploads.py` | `e2e_publica2.mjs` | `docs/T20_REPORTE.md` | Implementado |
| RF11 | Calcular rotación de inventario | `scripts/calc_rotation.py` | Ejecutado contra df_test_local, 9 meses | `docs/INDICADOR_ROTACION.md`, `GUIA_PRUEBAS_V3.md` | Implementado |
| RF12 | Comparar política simulada vs propuesta | `scripts/compare_policies.py` | Ejecutado: fill_rate 0.94 vs 0.85 | `docs/COMPARACION_POLITICA_SIMULADA_VS_PROPUESTA.md` | Implementado |
| RF13 | Scheduler automático (opcional) | `pipeline/jobs/scheduler.py` | 9/9 tests unitarios | `docs/ACTIVACION_SCHEDULER.md` | Implementado (deshabilitado por defecto) |

## Requisitos no funcionales

| ID | Requisito | Cómo se cumple | Evidencia | Estado |
|---|---|---|---|---|
| RNF01 | Seguridad: sesión HttpOnly, CSRF, roles | Cookie Secure/SameSite, token CSRF, roles lector/admin | `seg_publica.mjs`, `seg_publica_resultado.json` | Cumplido |
| RNF02 | Datos protegidos: no exponer credenciales | `.env` excluido de git, credenciales en `artifacts/private/` | `.gitignore`, inspección manual | Cumplido |
| RNF03 | Idempotencia en importaciones | Clave de deduplicación por archivo + SHA | `scripts/import_operativo.py`, tests | Cumplido |
| RNF04 | Despliegue en contenedores | Docker Compose local + Azure Container Apps | `docker-compose.yml`, `docs/T20_PLAN_NUBE.md` | Cumplido (local + nube) |
| RNF05 | Respaldo y recuperación de datos | `scripts/backup_restore.py`, mongodump/restore | `docs/T11A_REPORTE.md`, `T11B_REPORTE.md` | Cumplido |
| RNF06 | HTTPS con certificado | Caddy (local: autofirmado, nube: Azure managed) | `deploy/Caddyfile` | Cumplido |
| RNF07 | Trazabilidad de generaciones | `scheduler_ticks`, `jobs`, clave de idempotencia | `docs/ACTIVACION_SCHEDULER.md` | Cumplido |

## Cobertura de pruebas

| Área | Tests | Resultado | Fecha |
|---|---|---|---|
| Pipeline/plan | 324 aprobadas, 3 omitidas | PASS | 18/10/2026 |
| Frontend | 280/280 + build | PASS | 18/10/2026 |
| Inventario | 99 aprobadas | PASS | 18/10/2026 |
| Scheduler | 9/9 | PASS | 10/11/2026 |
| Navegador (e2e) | 25/25 | PASS | 22/10/2026 |
| Seguridad (e2e) | 12/12 | PASS | 22/10/2026 |
| Recálculo independiente | 100/100 sin diferencias | PASS | 18/10/2026 |

## Requisitos pendientes de validación externa

| ID | Requisito | Bloqueado por | Documento con supuestos |
|---|---|---|---|
| RF-E01 | Política de reposición real de la empresa | Entrevista con responsable de compras | `POLITICA_REPOSICION_PROPUESTA.md` |
| RF-E02 | Fuente de stock para nuevos cortes | Decisión de la empresa (kardex vs conteo) | `RECOMENDACION_FUENTE_STOCK.md` |
| RF-E03 | Resolución de 13 discrepancias de inventario | Respuesta de la empresa | `DISCREPANCIAS_INVENTARIO_ESCENARIOS.md` |
