# Matriz de riesgos actualizada

**Fecha:** 2026-11-10
**Proyecto:** Sistema de previsión de demanda y compras — Capstone

---

## Riesgos técnicos

| # | Riesgo | Prob. | Impacto | Nivel | Mitigación | Estado |
|---|---|---|---|---|---|---|
| RT01 | Credencial de Atlas expuesta sin rotar | Baja | Alto | Alto | Procedimiento documentado (`PROCEDIMIENTO_ROTACION_CREDENCIAL.md`); migración a credenciales de Milton autorizada | **Activo** — pendiente ejecución |
| RT02 | IP de salida de Azure cambia y la app pierde conexión a Atlas | Media | Alto | Alto | Medir IP tras cada despliegue; añadir a Atlas Network Access antes de activar | Mitigado con procedimiento |
| RT03 | Datos de la empresa incompletos (faltan ventas oct–nov) | Alta | Medio | Alto | Pronóstico usa datos hasta septiembre; limitación documentada | Aceptado |
| RT04 | Fuente de stock no definida por la empresa | Alta | Medio | Alto | Recomendación documentada (Alt. A kardex); existencia reconstruida como alternativa | Aceptado |
| RT05 | Modelo promedio_28 no captura estacionalidad | Media | Medio | Medio | Seleccionado como método operativo por robustez; RF/XGBoost no mejoraron en evaluación T12 | Aceptado |
| RT06 | MongoDB local sin autenticación en desarrollo | Baja | Bajo | Bajo | Solo accesible en localhost; Docker sin `--auth` para pruebas; producción usa autenticación | Aceptado |
| RT07 | Scheduler activado sin datos actualizados genera planes obsoletos | Media | Medio | Medio | Deshabilitado por defecto; requiere `--enable` explícito; documentado en `ACTIVACION_SCHEDULER.md` | Mitigado |

## Riesgos de proyecto

| # | Riesgo | Prob. | Impacto | Nivel | Mitigación | Estado |
|---|---|---|---|---|---|---|
| RP01 | Equipo no completa residuales del informe antes del 13/11 | Media | Alto | Alto | Lista explícita con responsables en `BACKLOG_OPERATIVO.md` §Residuales | Activo |
| RP02 | Video de sustentación no grabado a tiempo | Media | Alto | Alto | Guion completo en `GUION_VIDEO.md`; solo falta grabar | Activo |
| RP03 | Empresa no valida política de reposición propuesta | Alta | Medio | Alto | Documentada como propuesta del equipo con supuestos; no como hecho validado | Aceptado |
| RP04 | Artículo científico no iniciado | Alta | Medio | Alto | Requiere redacción del equipo basada en evidencia del informe | **Activo** |
| RP05 | Despliegue en nube con credenciales de Rogelio puede dejar de funcionar | Media | Alto | Alto | Migración a credenciales de Milton autorizada por Rogelio | En proceso |

## Riesgos mitigados (cerrados)

| # | Riesgo original | Cómo se resolvió |
|---|---|---|
| RC01 | No hay CLI para importar datos nuevos | Tarea 1 completada: `import_operativo.py` |
| RC02 | No hay forma de comparar políticas | Tarea 8 completada: `compare_policies.py` |
| RC03 | No hay indicador de rotación | Tarea 9 completada: `calc_rotation.py` |
| RC04 | Manuales desactualizados | Tarea 12 completada: manuales actualizados |
| RC05 | Publicación de plan puede corromperse | R19 cerrado con 3 correcciones y tests de regresión |
| RC06 | No hay procedimiento para rotar credencial | Tarea 11 completada: procedimiento documentado |

## Resumen

| Categoría | Total | Activos | Mitigados | Aceptados |
|---|---|---|---|---|
| Técnicos | 7 | 1 | 2 | 4 |
| Proyecto | 5 | 3 | 0 | 2 |
| Cerrados | 6 | — | — | — |
