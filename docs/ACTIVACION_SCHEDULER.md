# Activación del scheduler con trazabilidad

**Estado: CONFIGURACIÓN DOCUMENTADA, NO ACTIVADA.** El scheduler existe (`pipeline/jobs/scheduler.py`) y está deshabilitado por defecto. Este documento describe cómo activarlo, qué trazabilidad genera y qué condiciones deben cumplirse.

**Fecha:** 2026-11-10
**Depende de:** Tareas 1 (CLI de importación — hecha) y 4 (fuente de stock — documentada con recomendación)

---

## 1. Estado actual del scheduler

| Aspecto | Valor | Fuente |
|---|---|---|
| Ubicación | `pipeline/jobs/scheduler.py` | Código |
| Habilitado | **No** (`enabled: false` en config) | `config/t10_config.json` §scheduler |
| Intervalo | 1440 minutos (24 horas) | Config |
| Hora de ejecución | 06:00 Lima (UTC-5) | Config |
| Política de ticks perdidos | Coalescente (solo ejecuta el slot actual, descarta anteriores) | Config + código |
| Mecanismo de deduplicación | Índice único en MongoDB por slot UTC (`floor(now_utc / interval)`) | Código |

### 1.1 Cómo funciona

1. El scheduler calcula el **slot UTC** actual: `floor(now_utc / intervalo_minutos)`.
2. Intenta insertar un documento con ese slot en la colección de trazabilidad.
3. Si el slot ya existe (índice único), no hay duplicado → no hace nada.
4. Si es nuevo, ejecuta el pipeline: importar datos → generar pronóstico → publicar plan.
5. La política coalescente significa que si el worker estuvo caído 3 días, al volver solo ejecuta el slot actual, no los 3 anteriores.

### 1.2 Origen elegible

El scheduler calcula el origen de datos como:

```
origen_elegible = min(fecha_negocio_Lima, origen_maximo)
```

Donde `origen_maximo` está en `config/t10_config.json`:
- Política de desarrollo: `2026-07-10` (datos hasta julio, para evaluación académica)
- Política operativa: sin límite explícito (usa la fecha de negocio del día)

## 2. Prerrequisitos para activar

### 2.1 Datos estables (tarea 4)

El scheduler regenera el plan automáticamente. Para que el plan sea útil:

- [ ] **Fuente de stock definida** — La empresa elige Alt. A (kardex), B (conteo) o C (sistema). Ver `docs/RECOMENDACION_FUENTE_STOCK.md`.
- [ ] **Datos importados** — Al menos un corte de ventas y stock importado con `scripts/import_operativo`.
- [ ] **Stock actualizado** — La existencia no debe ser la del 20/10 indefinidamente; necesita actualizarse con cada corte.

**Sin estos prerrequisitos, activar el scheduler generaría planes con datos desactualizados.**

### 2.2 Infraestructura

- [ ] **Worker Python ejecutándose** — El scheduler corre dentro del worker (`pipeline/jobs/scheduler.py`). En Docker Compose local es el servicio `worker`. En Azure es `dfpub-worker`.
- [ ] **MongoDB accesible** — Para la colección de trazabilidad y los datos del pipeline.
- [ ] **Configuración de política operativa** — `t10_config.json` §politica_operativa debe tener los meses correctos.

### 2.3 Verificación previa

- [ ] **`import_operativo preview`** ejecutado sin errores con los datos del nuevo corte.
- [ ] **`import_operativo importar`** completado al menos una vez.
- [ ] **`import_operativo activar`** generó un plan válido con métricas dentro de lo esperado.

## 3. Cómo activar

### 3.1 En la configuración

Editar `config/t10_config.json`:

```json
{
  "scheduler": {
    "enabled": true,
    "hora_lima": "06:00",
    "intervalo_minutos": 1440,
    "politica_tick_perdido": "coalescente"
  }
}
```

### 3.2 En Docker Compose local

El worker ya incluye el scheduler. Al cambiar `enabled` a `true` y reiniciar:

```bash
docker compose restart worker
```

El scheduler comenzará a ejecutar a las 06:00 Lima del día siguiente.

### 3.3 En Azure (producción)

El worker en Azure Container Apps ya tiene el código. Solo se necesita:

1. Actualizar la configuración (variable de entorno o archivo de config en el contenedor).
2. Reiniciar la revisión del container app:
   ```
   az containerapp revision restart -n dfpub-worker -g rg-demand-forecasting-pub --revision <nombre_revision>
   ```

## 4. Trazabilidad

### 4.1 Qué registra el scheduler

Cada ejecución inserta un documento en la colección `scheduler_runs`:

| Campo | Tipo | Descripción |
|---|---|---|
| `slot_utc` | int | Slot UTC calculado (deduplicación) |
| `started_at` | datetime | Inicio de la ejecución (UTC) |
| `finished_at` | datetime | Fin de la ejecución (UTC) |
| `status` | string | `success`, `error`, `skipped` |
| `origen` | date | Fecha de origen usada para el pronóstico |
| `policy` | string | `desarrollo` o `operativa` |
| `stats` | object | Métricas del pipeline (SKUs procesados, WAPE, etc.) |
| `error` | string | Mensaje de error si `status = error` |

### 4.2 Qué registra `import_operativo`

Cada importación (manual o futura automática) registra:

| Campo | Descripción |
|---|---|
| Fecha y hora de importación | Cuándo se ejecutó |
| Tipo de datos | Ventas, stock o ambos |
| Archivo origen | Nombre del archivo importado |
| Registros procesados | Cuántos se importaron |
| Período cubierto | Meses/fechas del nuevo corte |
| Base de datos destino | Dónde se guardaron |

### 4.3 Qué registra `activar`

La activación (generación de pronóstico + publicación del plan) registra:

| Campo | Descripción |
|---|---|
| Fecha de generación | Cuándo se ejecutó |
| Origen usado | Fecha de corte para el pronóstico |
| Método | `promedio_28` (operativo) |
| SKUs procesados | Cuántos productos se incluyeron |
| Plan publicado | ID o referencia del plan generado |

## 5. Flujo completo con trazabilidad

```
1. La empresa entrega libro de ventas + stock (manual)
   ↓
2. Operador ejecuta: import_operativo preview (validación)
   → Registro: qué se validó, errores encontrados
   ↓
3. Operador ejecuta: import_operativo importar (carga)
   → Registro: qué se importó, cuántos registros, a qué base
   ↓
4. Operador ejecuta: import_operativo activar (genera plan)
   → Registro: origen, método, SKUs, plan publicado
   ↓
5. [Futuro] Scheduler ejecuta automáticamente paso 4 cada 24h
   → Registro: slot, resultado, métricas
```

**Actualmente los pasos 2–4 son manuales.** El scheduler automatizaría solo el paso 4 (regenerar el plan con los datos más recientes). Los pasos 1–3 siguen siendo manuales porque requieren que la empresa entregue los archivos.

## 6. Monitoreo propuesto

### 6.1 Alertas (no implementadas, propuesta)

| Condición | Severidad | Acción |
|---|---|---|
| Scheduler no ejecutó en 48 horas | Alta | Verificar que el worker esté corriendo |
| Ejecución terminó con error | Alta | Revisar logs del worker |
| WAPE del plan > 20% (categoría) | Media | Revisar datos de entrada |
| 0 SKUs procesados | Alta | Verificar que hay datos importados |
| Stock no actualizado en > 30 días | Media | Solicitar nuevo corte a la empresa |

### 6.2 Consulta de trazabilidad

Para ver las últimas ejecuciones del scheduler:

```python
db.scheduler_runs.find().sort("started_at", -1).limit(10)
```

Para ver importaciones:

```python
db.import_log.find().sort("timestamp", -1).limit(10)
```

## 7. Limitaciones

1. **El scheduler no importa datos** — solo regenera el plan con lo que ya está en la base. Si los datos no se actualizan, regenera el mismo plan.
2. **No hay alerta implementada** — el monitoreo propuesto en §6.1 es una recomendación, no código funcional.
3. **Sin reintentos automáticos** — si falla, el slot se marca como error y no se reintenta hasta el siguiente slot (24h después).
4. **Depende del worker** — si el contenedor se detiene, el scheduler no ejecuta. La política coalescente evita acumulación pero pierde días.
5. **Sin notificación a la empresa** — el scheduler no envía correos ni mensajes. La empresa debe consultar la interfaz o el operador debe verificar.

## 8. Decisión pendiente

Activar el scheduler requiere:

1. **Decisión de la empresa sobre fuente de stock** (tarea 4) — sin datos actualizados, el scheduler genera planes con stock desactualizado.
2. **Compromiso de entrega periódica** — la empresa debe comprometerse a entregar libros de ventas con una frecuencia definida (mensual recomendado).
3. **Autorización para ejecutar en Azure** — si se quiere que corra en producción (no solo en local).

**Sin estos tres puntos, el scheduler puede activarse en la demo local como demostración técnica, pero no generaría valor operativo.**
