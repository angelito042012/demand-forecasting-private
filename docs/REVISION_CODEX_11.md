# Revisión T12: resultados validados; cierre de estado R11 pendiente

17/10/2026, Lima. Entrega revisada **3f40176**, código/protocolo/pruebas a39d3e9 y sello 86325a7. **Resultados científicos T12 validados**, sin re-selección ni repetición de la evaluación real. Falta corregir un defecto administrativo de checkpoints (R11) antes de declarar cerrado todo el runner. Se integra al comienzo del siguiente encargo `ETAPA_11_CLAUDE.md` (T11A: preparación local del despliegue), sin bloquear el trabajo independiente de empaquetado/capacidad.

## Evidencia propia de Codex

- **16 pruebas sintéticas T12 aprobadas, 0 omitidas, 69,49 s**, usando bases temporales Mongo. El primer intento sin permiso de red dio 9 aprobadas/7 omitidas; no se contó como suite completa. JUnit/log definitivo: `artifacts/private/codex_review11_verified_tests.xml` y `.log`. No se entrenaron modelos sobre datos reales ni se volvió a ejecutar prepare/evaluate del paquete final.
- Revisión metodológica independiente de predicción fija, simulación secuencial y referencias congeladas: matrices físicamente truncadas por revisión, etiquetas ≤origen, catálogo/universo/cohorte/costos iniciales de julio, baseline categoría=suma SKU, RF T07 sin cambios, motor experimental exacto, días sin cobertura/SKU nuevos separados. No se halló discrepancia material en los cálculos.
- Cronología Git/artefactos: código comprometido a39d3e9 a las17:52:30; preparación sellada17:52:53; commit del sello86325a7 a las17:53:05; lectura de agosto17:53:15. Cambios posteriores a3f40176 solo de documentación/resultados. Sello recalculado y los **9 hashes de artefactos privados coinciden**. Las cinco fases de cálculo registran un intento cada una. Es evidencia consistente con la ejecución declarada, no una garantía contra cualquier acceso externo ajeno al runner.
- Auditoría propia independiente en `artifacts/private/codex_review11_audit.py/.json`: reconstruyó los reales del bloque desde el CSV mínimo guardado y comprobó igualdad con NPZ; recalculó WAPE/MAE/RMSE/sesgo H14 desde matrices selladas, sin usar builders de métricas; categorías=sumSKU; revalidó **27 combinaciones** con saldos diarios/finales, demanda, tránsito, no negatividad, igualdad de stock inicial, compras y conservación de valor. Sin escribir en `artifacts/private/final/` ni consultar nuevamente agosto en Mongo.

## Resultados contrastados

Primaria SKU, universo común **3401**, observado H14 **10366 unidades**:

| Método | WAPE H14 recalculado | MAE | Sesgo acumulado |
|---|---|---|---|
| promedio_28 | 0,7809666216 | 2,3803293 | +212,5 |
| RF distribuido | 0,7910421821 | 2,4110389 | +311,5732 |
| cero | 1,0000000000 | 3,0479271 | −10366 |

RF tiene aproximadamente1,29% más WAPE que promedio_28; se conserva **promedio_28 como operativo**. WAPE no es «porcentaje de precisión»:0,781 significa error absoluto agregado equivalente al78,1% del volumen observado de ese grupo/horizonte. El error es elevado a nivel SKU; no afirmar que el sistema predice con gran precisión por funcionar técnicamente. La agregación por categoría mejora cifras pero mezcla unidades base de productos heterogéneos; explicitar ese límite.

Simulación L7/S7: fill rate referencia0,7561252, promedio0,7792415, RF0,7811713. Compras supuestas267439,991 /309791,5665 /326713,44875, respectivamente. RF gana apenas0,193 puntos porcentuales de servicio sobre promedio con aproximadamente5,46% más compras y0,66% más stock medio. No demuestra ahorro ni mejora real de la MYPE. Un bloque sin inferencia de ganador; demanda proxy, costos y existencias supuestos.

## R11 — P2: auditoría y reporte no completan sus checkpoints

`pipeline/final/runner.py:45` define siete fases, y `_end` requiere las siete para `completa=true`. Pero `pipeline/final/audit.py::run_audit` y `pipeline/final/report.py::write_report` no registran sus fases/errores en estado.json. El archivo real conserva **completa=false** y solo las cinco fases de cálculo aunque existan auditoría e informes correctos. La afirmación de cierre total no concuerda con el estado operativo.

Corregir el registro de inicio/fin/error/idempotencia de auditoría y reporte, y reconciliar el paquete existente ejecutando solo estas operaciones sobre los artefactos válidos. **No volver a preparar predicciones, leer agosto en Mongo ni evaluar/simular.** Registrar la corrección posterior y conservar los hashes de predicciones, modelo, reales, series y métricas de la ejecución original. Añadir regresiones: status final verdadero tras las siete fases, falso ante fallo de auditoría/reporte y reanudación sin invocar preparación/evaluación. No resolverlo editando a mano el booleano ni inventando fechas originales de fases ausentes.

## Dirección de T11

La base local sigue en torno a459,39MB. Inspección solo lectura por colección/corrida (`artifacts/private/codex_review11_capacity.json`): pronósticos267,06MB, recomendaciones66,43MB, ventas81,79MB antes de índices. Seis corridas generadas de prueba explican gran parte del crecimiento. Las dos históricas suman65,10MB BSON en pronósticos; no es necesario publicar todas las corridas de prueba para servir las evidencias académicas.

Preparar una **base nueva de publicación**, con todas las ventas/créditos y fuentes, corridas históricas pertinentes y paquete final, sin copiar sesiones/credenciales/jobs de pruebas; preservar íntegra la base original y archivar todos los resultados recuperables. Medir realmente tamaño+índices y margen tras restaurar. NPZ/modelos/logs no deben inflar Mongo; almacenamiento durable separado. La selección exacta se fija en manifiesto y no elimina evidencias locales ni resultados desfavorables.

El siguiente encargo prepara contenedores, integración del paquete final, copia/restauración local y plan de infraestructura/costo/accesos. **No autoriza aún crear recursos facturables, consumir crédito sin presupuesto concreto acordado, subir datos comerciales o desplegar.** La preparación debe quedar revisable antes de solicitar ese último paso. Cuentas ya creadas; no pedir nuevas altas o contraseñas por chat. Fecha límite23/10/2026.
