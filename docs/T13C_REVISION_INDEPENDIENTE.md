# T13C — Revision independiente post-T12

Fecha: 2026-11-06. Revision de coherencia del codigo, documentacion y estado general
tras completar la parametrizacion del pipeline (T12, commit `a409bd1`) y la actualizacion
de manuales (commit `e6029bc`).

**Alcance:** verificacion automatizada; no reemplaza la aceptacion humana (A14, pendiente).

---

## 1. Coherencia documentacion vs codigo

### 1.1 Constantes parametrizadas (DICCIONARIO_VARIABLES §1)

| Variable | Archivo:linea | Valor en codigo | Valor en doc | Estado |
|---|---|---|---|---|
| `OCTOBER_NAME` | `dataset_v2.py:38` | `"octubre.xlsx"` | `"octubre.xlsx"` | OK |
| `OCTOBER_WINDOW` | `dataset_v2.py:39` | `(2026-10-01, 2026-10-20)` | `(2026-10-01, 2026-10-20)` | OK |
| `CUTOFF` | `dataset_v2.py:40` | `2026-10-20` | `2026-10-20` | OK |
| `PARTIAL_DATE` | `dataset_v2.py:41` | `"2026-10-21"` | `"2026-10-21"` | OK |
| `AS_OF_LOCAL` | `reconstructed.py:31` | `"2026-10-20T23:59:59-05:00"` | `"2026-10-20T23:59:59-05:00"` | OK |
| `BASE_AS_OF_LOCAL` | `reconstructed.py:32` | `"2026-10-18T17:00:00-05:00"` | `"2026-10-18T17:00:00-05:00"` | OK |
| `LAST_FULL_DAY` | `sql21_prepare.py:27` | `date(2026, 10, 20)` | `2026-10-20` | OK |

**7/7 constantes verificadas.** Lineas corregidas en esta revision (estaban desfasadas en 1).

### 1.2 Argumentos CLI (MANUAL_OPERACION §10)

| Modulo | Argumentos documentados | Presentes en argparse | Estado |
|---|---|---|---|
| `dataset_v2.py` | `--book-name`, `--book-window`, `--partial-date-value` | L225, L226-227, L228-229 | OK |
| `reconstructed.py` | `--as-of-local`, `--base-as-of-local` | L287, L288 | OK |
| `sql21_prepare.py` | `--last-full-day` | L307 | OK |

**6/6 argumentos CLI verificados.**

### 1.3 Funciones de metricas (EVALUACION_T06_T07_METRICAS)

| Funcion | Archivo:linea | Estado |
|---|---|---|
| `stats()` | `metrics.py:17` | OK |
| `add_stats()` | `metrics.py:30` | OK |
| `finalize()` | `metrics.py:38` | OK |

### 1.4 Documentos referenciados desde manuales

Los 8 documentos referenciados en las nuevas secciones de MANUAL_OPERACION §11
y MANUAL_USUARIO existen en el repositorio:

- `docs/DICCIONARIO_VARIABLES.md` — OK
- `docs/EVALUACION_T06_T07_METRICAS.md` — OK
- `docs/T12_RESULTADOS.md` — OK
- `docs/T22_ALCANCE_DATOS_Y_PLAN.md` — OK
- `docs/DECISIONES_DATOS.md` — OK
- `docs/T06_PROTOCOLO.md` — OK
- `docs/T13_GUION_ACEPTACION.md` — OK
- `docs/MODELOS_Y_METODO_OPERATIVO.md` — OK
- `docs/DEMOSTRACION_3110044.md` — OK

## 2. Tests

### 2.1 Suite de tests

- **1050 tests recopilados** (pytest, 82 archivos en `tests/`)
- Subconjunto ejecutado (modulos parametrizados): **58 passed, 1 skipped, 0 failed** (4.96 s)
  - `tests/plan/test_dataset_v2.py` — 24 passed
  - `tests/inventory/test_reconstructed.py` — 26 passed, 1 skipped
  - `tests/forecast/test_baselines_metrics.py` — 8 passed

### 2.2 Lint (ruff)

- `pipeline/plan/dataset_v2.py` — limpio
- `pipeline/inventory/reconstructed.py` — limpio
- `scripts/sql21_prepare.py` — limpio

## 3. Estado del repositorio

| Metrica | Valor |
|---|---|
| Commits en master | 163 |
| Ultimo commit | `e6029bc` (T12: manuales y recorrido equipo entrante) |
| Archivos Python | 215 |
| Documentos (.md) | 80 |
| Tests recopilados | 1050 |

## 4. Hallazgos

### 4.1 Corregido en esta revision

| Hallazgo | Severidad | Accion |
|---|---|---|
| Lineas de `dataset_v2.py` en DICCIONARIO_VARIABLES desfasadas en 1 (37-40 → 38-41) | Menor | Corregido |

### 4.2 Pendientes (no bloqueantes, preexistentes)

| Hallazgo | Severidad | Nota |
|---|---|---|
| A14 — aceptacion humana | Bloqueante para cierre formal | Requiere a Rogelio con la interfaz nueva |
| A13 — HTTPS y cinco usuarios en nube | Media | Requiere entorno publicado |
| Credencial Atlas expuesta sin rotar | Seguridad (pospuesta) | Decision del titular, posterior al 23/10 |
| Features: 18 grupos conceptuales → 24 columnas reales (`FEATURE_NAMES`) | Informativo | No es error: lag0..lag6 son 7 columnas de un mismo grupo |

## 5. Conclusion

La revision independiente no encontro defectos criticos. La documentacion nueva
(DICCIONARIO_VARIABLES, EVALUACION_T06_T07_METRICAS, manuales actualizados, recorrido
del equipo entrante) es coherente con el codigo. Los tests de los modulos parametrizados
pasan sin errores. El unico hallazgo fue una imprecision menor en numeros de linea,
corregida en esta misma revision.

**Pendientes ajenos a esta revision:** aceptacion humana (A14), pruebas en nube (A13)
y rotacion de credencial Atlas.
