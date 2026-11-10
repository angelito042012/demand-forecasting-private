# Guía de pruebas y traspaso — Trabajo nuevo (v3)

**Fecha:** 2026-11-10
**Autor:** Equipo Capstone (sesión Claude, Milton como líder)
**Evaluación:** 13/11/2026

---

## 0. Alcance de los cambios

**Todo el trabajo nuevo es LOCAL.** No se tocó nada en la nube.

| Entorno | Estado | Qué tiene |
|---|---|---|
| **GitHub** (`master`) | Actualizado (commit `1ae03cb`) | Todos los scripts, docs y código nuevos |
| **MongoDB local** (`df_test_local`) | Docker `mongo:8.3.8` en `localhost:27017` | 130,747 docs de ventas (ene–sep), 50 productos de stock |
| **Azure Container Apps** | Sin cambios | Imagen `t22g-a9119ae`, base `demand_forecasting_pub` |
| **MongoDB Atlas** | Sin cambios | Base `demand_forecasting_pub` (~320 MB) |

**La imagen de Azure y Atlas NO conocen los scripts nuevos.** Para que funcionen en la nube habría que construir una imagen nueva, desplegarla y apuntar a la base correcta. Eso NO está autorizado ni es necesario para la evaluación.

---

## 1. Prerrequisitos

### 1.1 Entorno Python

```bash
# Activar el venv existente (Windows)
D:\PROYECTOS2\Entrega_equipo_20261023\trabajo\.venv\Scripts\activate

# Verificar desde la raíz del repo
cd D:\PROYECTOS2\Entrega_equipo_20261023\github_clean\repo
python -c "import pymongo; print(pymongo.version)"
```

### 1.2 MongoDB local (Docker)

```bash
# Verificar que Docker Desktop esté corriendo
docker ps

# Si el contenedor mongo no aparece, levantarlo:
docker run -d --name mongo-test -p 27017:27017 mongo:8.3.8
```

La base `df_test_local` ya debe estar cargada. Si no lo está, ejecutar el script de carga (ver §1.3).

### 1.3 Cargar datos de prueba (solo si la base está vacía)

El script de carga está en el scratchpad de la sesión de Claude. Si necesitas recrearlo:

```python
# Paso 1: Cargar ventas marzo–septiembre + stock (desde ventas.csv y existencias.csv)
# Usa el script load_test_data.py que carga plan_sales e inventory_reconstructed

# Paso 2: Cargar ventas enero–febrero (desde df_equipo_20261023135040.sales)
# Mapeo: sku→producto_id, cantidad_base→cantidad(float), tipo_doc→clase, almacen '001'→'1'
```

**Verificación rápida:**

```bash
python -c "
from pymongo import MongoClient
db = MongoClient('mongodb://127.0.0.1:27017')['df_test_local']
print('plan_sales:', db.plan_sales.estimated_document_count())
print('snapshots:', db.inventory_reconstructed_snapshots.estimated_document_count())
print('items:', db.inventory_reconstructed_items.estimated_document_count())
meses = sorted(set(f[:7] for f in db.plan_sales.distinct('fecha')))
print('Meses:', meses)
"
```

Resultado esperado:
- `plan_sales`: ~130,747
- `snapshots`: 1
- `items`: 50
- Meses: `['2026-01', '2026-02', ..., '2026-09']`

---

## 2. Pruebas por componente

### 2.1 Scheduler (Tarea 10) — Tests unitarios

**Qué es:** Temporizador opcional que ejecuta el pipeline de generación cada 24h. Deshabilitado por defecto. Soporta `--operational` para política operativa (sin tope de julio).

**Código:** `pipeline/jobs/scheduler.py` (263 líneas)
**Docs:** `docs/ACTIVACION_SCHEDULER.md`
**Tests:** `tests/jobs/test_scheduler.py` (9 tests)

```bash
python -m pytest tests/jobs/test_scheduler.py -v
```

**Resultado esperado:** 9/9 passed. Los tests cubren:
1. Scheduler deshabilitado por defecto
2. Aritmética de slots y origen
3. Dos ticks simultáneos no duplican
4. Muchos threads, mismo slot, sin duplicado
5. Nuevo slot → nuevo origen y job
6. Ticks perdidos se coalescen
7. Clave del scheduler = clave estándar
8. CLI `--once` con reloj controlado
9. Enqueue fallido marca el tick sin job fantasma

### 2.2 Rotación de inventario (Tarea 9)

**Qué es:** Calcula rotación de inventario (ventas/stock) por producto y categoría, con clasificación y días de cobertura.

**Código:** `scripts/calc_rotation.py` (261 líneas)
**Docs:** `docs/INDICADOR_ROTACION.md`

```bash
# Por producto (top 50)
python -m scripts.calc_rotation --db df_test_local --month 2026-09

# Por categoría
python -m scripts.calc_rotation --db df_test_local --month 2026-09 --by-category

# Formato JSON (todos los productos)
python -m scripts.calc_rotation --db df_test_local --month 2026-09 --format json

# Otro mes (ej. julio)
python -m scripts.calc_rotation --db df_test_local --month 2026-07
```

**Resultado esperado (septiembre):**
- 2,349 productos totales, 48 con stock
- Rotación global: ~1.89 (15.9 días cobertura)
- Distribución: 4 muy alta, 5 alta, 2 media, 8 baja, 29 muy baja, 2301 sin movimiento
- Sin errores de formato (el bug de `None` en `coverage_days()` fue corregido en `1ae03cb`)

**Qué verificar:**
- [ ] Ejecuta sin error para cada mes (enero a septiembre)
- [ ] La clasificación es coherente (rotación > 4 = muy alta, etc.)
- [ ] Formato JSON produce salida válida
- [ ] `--by-category` agrupa correctamente

### 2.3 Comparación de políticas (Tarea 8)

**Qué es:** Comparación justa entre política simulada (origen julio, datos históricos amplios) y propuesta (origen octubre, datos recientes), usando el mismo motor de simulación con variables controladas.

**Código:** `scripts/compare_policies.py` (261 líneas)
**Docs:** `docs/COMPARACION_POLITICA_SIMULADA_VS_PROPUESTA.md`

```bash
python -m scripts.compare_policies \
  --db df_test_local \
  --month 2026-09 \
  --origin-sim 2026-07-10 \
  --origin-prop 2026-10-20
```

**Resultado esperado:**
- 50 productos con stock y ventas
- Simulada (L7): fill_rate ~0.94
- Propuesta (L7): fill_rate ~0.85
- Diferencia coherente: simulada tiene ventana de pronóstico más amplia → mejor tasa de servicio
- JSON de salida con `L7` y `L14`

**Qué verificar:**
- [ ] Variables controladas: misma demanda total, mismo stock inicial
- [ ] La diferencia se explica solo por la ventana de pronóstico
- [ ] El JSON de salida es válido y contiene las métricas esperadas

**NOTA IMPORTANTE:** Este script usa datos de septiembre como "demanda real" y compara pronósticos con distintos orígenes. No es una prueba independiente — es un ejercicio académico con datos históricos ya vistos. El documento de diseño lo aclara.

### 2.4 Importación operativa (Tarea 1)

**Qué es:** CLI para recibir nuevos cortes de ventas y stock sin mongorestore.

**Código:** `scripts/import_operativo.py`
**Docs:** `docs/MANUAL_OPERACION.md` (sección de importación)

```bash
# Vista previa (no escribe nada)
python -m scripts.import_operativo preview --file ventas.xlsx --db df_test_local

# Importar (escribe en la base)
python -m scripts.import_operativo importar --file ventas.xlsx --db df_test_local
```

**ADVERTENCIA:** No ejecutar `importar` contra bases protegidas (`demand_forecasting_dev`, `demand_forecasting_v2`, `demand_forecasting_pub`). El código las bloquea explícitamente.

### 2.5 Tests generales del pipeline

```bash
# Tests del scheduler (ya cubierto arriba)
python -m pytest tests/jobs/ -v

# Tests del pipeline de planificación
python -m pytest tests/plan/ -v

# Tests de inventario
python -m pytest tests/inventory/ -v

# Todos los tests
python -m pytest tests/ -v --ignore=tests/backend
```

---

## 3. Documentación nueva

Cada tarea del backlog tiene su documento en `docs/`. Tabla de referencia:

| Tarea | Documento | Contenido |
|---|---|---|
| 1 | `MANUAL_OPERACION.md` (actualizado) | Procedimiento de importación operativa |
| 2 | `POLITICA_REPOSICION_PROPUESTA.md` | Política propuesta (supuestos, no validada) |
| 3 | `DISCREPANCIAS_INVENTARIO_ESCENARIOS.md` | 13 discrepancias + compras 11452/11455 |
| 4 | `RECOMENDACION_FUENTE_STOCK.md` | Alt. A (kardex) recomendada |
| 5 | `DICCIONARIO_VARIABLES.md` | Variables del pipeline con procedencia |
| 6+7 | `EVALUACION_T06_T07_METRICAS.md` | Reproducción de evaluación + métricas formalizadas |
| 8 | `COMPARACION_POLITICA_SIMULADA_VS_PROPUESTA.md` | Diseño metodológico de comparación justa |
| 9 | `INDICADOR_ROTACION.md` | Definición de rotación, variantes, interpretación |
| 10 | `ACTIVACION_SCHEDULER.md` | Prerrequisitos, pasos y trazabilidad |
| 11 | `PROCEDIMIENTO_ROTACION_CREDENCIAL.md` | 4 pasos para rotar la credencial de Atlas |
| 12 | Manuales actualizados | `MANUAL_OPERACION`, `MANUAL_USUARIO`, `DEMOSTRACION_3110044` |
| 13 | `documentacion/Correcciones_Informe_T13.md` | 35 correcciones aplicadas al informe |
| Backlog | `BACKLOG_OPERATIVO.md` | Estado consolidado de las 14 tareas |

---

## 4. Archivos nuevos en el repositorio

### Scripts (`scripts/`)

| Archivo | Tarea | Descripción |
|---|---|---|
| `import_operativo.py` | 1 | CLI: preview / importar / activar |
| `compare_policies.py` | 8 | Comparación justa con simulación |
| `calc_rotation.py` | 9 | Indicador de rotación de inventario |

### Código del pipeline modificado

| Archivo | Cambio |
|---|---|
| `pipeline/jobs/scheduler.py` | Flag `--operational` + `politica_operativa` |
| `config/t10_config.json` | Sección `politica_operativa` añadida |

### Tests

| Archivo | Cobertura |
|---|---|
| `tests/jobs/test_scheduler.py` | 9 tests del scheduler (incluye `--operational`) |

---

## 5. Estado del backlog

De 14 tareas:
- **12 completadas** (código + documentación)
- **1 lista para ejecutar** (tarea 14: grabar video, guion en `docs/GUION_VIDEO.md`)
- **Residuales del informe** delegados al equipo (abstract, cronograma, compromisos éticos individuales, anexos, índices)

Tareas bloqueadas por la empresa (pero documentadas con supuestos para la evaluación):
- 2, 3, 4: propuestas del equipo, pendientes de validación real
- 10: scheduler documentado pero no activado (requiere fuente de stock estable)
- 11: procedimiento listo, falta autorización de Rogelio

---

## 6. Qué NO se hizo (y por qué)

| Qué | Por qué |
|---|---|
| Desplegar a Azure | Sin autorización ni presupuesto; no es necesario para la evaluación |
| Tocar MongoDB Atlas | Sin autorización del titular (Rogelio) |
| Activar el scheduler en producción | Requiere fuente de stock estable (tarea 4 pendiente de la empresa) |
| Rotar la credencial de Atlas | Pendiente de autorización y acceso de Rogelio |
| Ejecutar comparación con datos de noviembre | No existen ventas de noviembre (el mes no ha terminado) |
| Reentrenar modelos | Prohibido: T12 es evaluación histórica cerrada |

---

## 7. Cómo retomar si se interrumpe

```bash
# 1. Ver estado de git
cd D:\PROYECTOS2\Entrega_equipo_20261023\github_clean\repo
git status
git log --oneline -5

# 2. Ver estado de Docker/MongoDB
docker ps  # debe aparecer mongo en puerto 27017

# 3. Verificar datos en la base
python -c "
from pymongo import MongoClient
db = MongoClient('mongodb://127.0.0.1:27017')['df_test_local']
print('plan_sales:', db.plan_sales.estimated_document_count())
print('snapshots:', db.inventory_reconstructed_snapshots.estimated_document_count())
"

# 4. Correr una prueba rápida
python -m scripts.calc_rotation --db df_test_local --month 2026-09
```

---

## 8. Commits relevantes

| Commit | Descripción |
|---|---|
| `114efcd` | T1: CLI de importación operativa |
| `a141922` | Backlog operativo inicial |
| `8a0959e` | T12 parcial: actualizar ESTADO y BACKLOG |
| `7e6b557` | Soporte formato alternativo Excel |
| `f266ed6` | Tareas 2-4, 8-11: documentación, scripts y código |
| `1ae03cb` | Fix: manejar rotación global None en formato de salida |
