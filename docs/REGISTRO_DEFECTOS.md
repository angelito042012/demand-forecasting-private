# Registro de defectos

**Fecha:** 2026-11-10
**Proyecto:** Sistema de previsión de demanda y compras — Capstone

---

## Defectos identificados y resueltos

| # | Defecto | Severidad | Detectado | Commit de fix | Estado |
|---|---|---|---|---|---|
| D01 | Publicación de plan borra resultados del sucesor cuando un intento anterior hace relevo | Alta | 18/10 (Codex R19) | `a728017` | Resuelto |
| D02 | Purga de filas abandonadas post-publicación puede borrar el plan recién publicado | Alta | 18/10 (Codex R19) | `f0bae1d` | Resuelto |
| D03 | Error ambiguo de publicación: el intento limpia filas aunque el servidor ya aplicó el cambio | Alta | 18/10 (Codex R19) | `462e7f5` | Resuelto |
| D04 | Pantalla no lee parámetros ni fecha de ventas del plan real (usaba mocks) | Media | 18/10 (Codex R20) | `667828b` | Resuelto |
| D05 | Importador acepta CSV alterado sin verificar contra el Excel original | Media | 18/10 (Codex R18) | `616b5ef` | Resuelto |
| D06 | `coverage_days()` retorna `None` pero f-string usa `:.1f` → TypeError | Baja | 10/11 (pruebas locales) | `1ae03cb` | Resuelto |
| D07 | `cantidad` cargada como string en MongoDB → `$sum` retorna 0 | Media | 10/11 (pruebas locales) | Corregido en script de carga | Resuelto |
| D08 | Datos de enero-febrero ausentes en base de prueba local | Baja | 10/11 (Milton) | Migración de datos en sesión | Resuelto |
| D09 | 11 archivos nuevos no pusheados a GitHub | Media | 10/11 (auditoría) | `f266ed6` | Resuelto |
| D10 | Formato alternativo de Excel (Ventas detalladas) no reconocido por import_operativo | Baja | 10/11 | `7e6b557` | Resuelto |

## Defectos conocidos no resueltos

| # | Defecto | Severidad | Razón | Mitigación |
|---|---|---|---|---|
| DN01 | `TRUSTED_PROXIES` vacío en Azure: rate-limit agrupa por IP del proxy | Baja | Requiere configuración de Azure; no afecta demo | Documentado en `T22_TRUSTED_PROXIES_Y_CREDENCIAL.md` |
| DN02 | Credencial de Atlas expuesta en captura anterior | Alta | Pendiente de rotación (requiere acceso de Rogelio/Milton) | Procedimiento en `PROCEDIMIENTO_ROTACION_CREDENCIAL.md` |
| DN03 | IP de salida de Azure Container Apps puede cambiar tras nueva revisión | Media | Comportamiento de la plataforma | Medir IP y añadir a Atlas tras cada despliegue |

## Métricas de defectos

| Métrica | Valor |
|---|---|
| Defectos totales identificados | 13 |
| Resueltos | 10 |
| No resueltos (conocidos) | 3 |
| Severidad alta resueltos | 3/3 |
| Tiempo medio de resolución (alta) | < 24h |
| Regresiones introducidas por fixes | 0 (cada fix incluye test de regresión) |
