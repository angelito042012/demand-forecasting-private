# Limitaciones y mejoras futuras

**Fecha:** 2026-11-10
**Proyecto:** Sistema de previsión de demanda y compras — Capstone

---

## 1. Limitaciones del sistema actual

### 1.1 Datos

| Limitación | Impacto | Referencia |
|---|---|---|
| Datos de ventas disponibles solo hasta septiembre 2026 | El pronóstico para noviembre usa datos históricos sin las ventas más recientes (oct–nov) | `BACKLOG_OPERATIVO.md` §Tarea 3 |
| Stock basado en conteo único del 18/10/2026 | No refleja movimientos posteriores al conteo; existencia reconstruida, no dinámica | `REVISION_CONTEO_50_20261018.md` |
| 13 discrepancias de inventario sin resolver | Diferencias entre conteo y kardex no explicadas por la empresa | `DISCREPANCIAS_INVENTARIO_ESCENARIOS.md` |
| Ventas censuradas por stock desconocido | Si un producto estuvo agotado, las ventas registradas subestiman la demanda real | `DECISIONES_DATOS.md` |
| Solo 50 productos con conteo físico de ~5,000 SKUs | Rotación y stock solo calculables para el subconjunto contado | `INDICADOR_ROTACION.md` |

### 1.2 Modelo

| Limitación | Impacto | Referencia |
|---|---|---|
| Método operativo es promedio_28 (media móvil de 28 días) | No captura estacionalidad, tendencias ni eventos especiales | `MODELOS_Y_METODO_OPERATIVO.md` |
| RF y XGBoost no mejoraron al promedio_28 en evaluación | Modelos complejos no aportaron valor adicional con estos datos | `T12_RESULTADOS.md`, `EVALUACION_T06_T07_METRICAS.md` |
| WAPE de 0.37–0.43 según origen | Error significativo a nivel de SKU individual; más preciso por categoría | `T19_REPORTE.md` |
| Sin validación con datos fuera de muestra recientes | Evaluación T12 usa datos hasta julio; septiembre es revalidación, no prueba independiente | `T12_PROTOCOLO.md` |

### 1.3 Operación

| Limitación | Impacto | Referencia |
|---|---|---|
| Importación de datos es manual (CLI) | No hay integración automática con el sistema de la empresa | `MANUAL_OPERACION.md` |
| Scheduler existe pero está deshabilitado | No regenera el plan automáticamente; requiere activación manual | `ACTIVACION_SCHEDULER.md` |
| Política de reposición propuesta, no validada | Basada en supuestos del equipo, no en entrevista con el responsable de compras | `POLITICA_REPOSICION_PROPUESTA.md` |
| Sin alertas ni notificaciones implementadas | El operador debe consultar activamente; no recibe avisos de stock bajo o plan vencido | `ACTIVACION_SCHEDULER.md` §6 |

### 1.4 Infraestructura

| Limitación | Impacto | Referencia |
|---|---|---|
| IP de salida de Azure Container Apps es dinámica | Cada despliegue puede requerir actualizar Atlas Network Access | `TRASPASO.md` (22/10) |
| `TRUSTED_PROXIES` vacío en producción | Rate-limit no distingue clientes detrás del proxy de Azure | `T22_TRUSTED_PROXIES_Y_CREDENCIAL.md` |
| Credencial de Atlas expuesta sin rotar | Riesgo de acceso no autorizado hasta que se ejecute la rotación | `PROCEDIMIENTO_ROTACION_CREDENCIAL.md` |
| Base de datos en Atlas M0 (free tier, 512 MB) | Limita volumen de datos históricos almacenables (~460 MB actualmente) | `ESTADO.md` |

---

## 2. Mejoras futuras propuestas

### 2.1 Corto plazo (inmediatas, sin la empresa)

| Mejora | Esfuerzo | Beneficio |
|---|---|---|
| Migrar credenciales de Atlas/Azure a cuenta de Milton | 2-3 horas | Autonomía del equipo, credencial rotada |
| Grabar video de sustentación | 2-3 horas | Requisito de evaluación |
| Completar artículo científico | 4-6 horas | Requisito de evaluación |

### 2.2 Mediano plazo (con datos de la empresa)

| Mejora | Esfuerzo | Beneficio |
|---|---|---|
| Importar ventas de octubre–noviembre | 30 min (CLI existe) | Pronóstico actualizado para diciembre |
| Validar política de reposición con la empresa | 1-2 horas (entrevista) | Comparación justa contra política real |
| Activar scheduler con fuente de stock estable | 1 hora (config + restart) | Regeneración automática diaria |
| Resolver 13 discrepancias de inventario | Depende de la empresa | Stock más preciso |

### 2.3 Largo plazo (evolución del sistema)

| Mejora | Complejidad | Beneficio |
|---|---|---|
| Integración directa con sistema de la empresa (API o BD) | Alta | Elimina importación manual |
| Modelos con estacionalidad (Prophet, LSTM) | Media | Mejor captura de patrones cíclicos |
| Dashboard de monitoreo de métricas en tiempo real | Media | Detección temprana de degradación del pronóstico |
| Módulo de alertas (email/WhatsApp) por stock bajo | Media | Reposición proactiva |
| Expansión a todos los SKUs (no solo 50) | Media | Cobertura completa del catálogo |
| Multi-almacén | Alta | Soporte para operaciones distribuidas |
