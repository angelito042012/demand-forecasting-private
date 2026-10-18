# T11B (R14): referencia de runtime sin Git y generación real en contenedor

Fecha: 17/10/2026 (Lima). Alcance: local. Sin nube, sin imágenes en registros, sin modelos entrenados ni T06/T07/T12 repetidos. Inventario simulado con supuestos; no corresponde al inventario real de la empresa.

## 1. Problema y solución

`pipeline/publish/source.py` verificaba T07 con `git show` (manifiesto aprobado, métricas, `config_sha256`, `codigo_sha256`). La imagen no contiene Git ni repositorio, de modo que en contenedor la referencia no se verificaba y el generador degradaba a «sin comparador / sin recomendaciones».

Solución: un **paquete de referencia de runtime** privado, construido una vez con Git local y verificado en runtime sin Git.

| Elemento | Dónde | Qué ancla |
|---|---|---|
| Ancla de confianza | `config/t08_publish.json` → `approved_reference` (viaja versionada con la imagen) | commit aprobado `5790103…` y sha256 normalizados (LF) de `T07_MANIFIESTO.json` y `T07_METRICAS.json` |
| Cadena | contenido de `files/docs/T07_MANIFIESTO.json` en el paquete | sha256 de CSV y NPZ, `config_sha256`, `codigo_sha256`, `git_commit` del código (`e546641…`), `agosto_usado=false` |
| Código y configuración | `files/<ruta>` (bytes exactos del blob del commit del manifiesto, 14 archivos + `config/t07_config.json`) | `codigo_sha256` se recalcula sobre este contenido (igual que `verify_code`), `config_sha256` igual que `verify_config` |
| Artefactos | `artifacts/predicciones_folds.csv.gz`, `artifacts/simulacion_series.npz` | sha256 del manifiesto |
| Índice | `manifest_referencia.json` | consistencia (commits y sha256 normalizados de cada archivo); **no autoriza nada por sí solo** |

Un hash recalculado sobre el paquete no lo autoriza: se compara con el ancla versionada y con la cadena del manifiesto aprobado. Todas las comprobaciones ocurren antes de leer CSV/NPZ para el generador (`verify_and_load_runtime` → `assemble_source`). Errores claros (`SourceVerificationError`): referencia aprobada distinta, `codigo_sha256`, `config_sha256`, `sha256 de <artefacto>`, «paquete de referencia incompleto: faltan …», índice ausente/ilegible.

**Selección de camino** (`pipeline/publish/source.py::verify_and_load`):
- `DF_RUNTIME_REFERENCE_DIR` definida y sin `root`/`code_repo` explícitos → paquete, **sin Git**.
- Variable ausente → verificador de desarrollo basado en Git, sin cambios (en un contenedor sin Git la referencia es opcional: la corrida declara «comparador no disponible: artefactos T07 no verificados» y publica sin recomendaciones).
- Variable definida pero paquete inválido → `GenerationError("REFERENCIA_INVALIDA", …)` en `pipeline/generate/baseline.py::_load_reference`: **no se degrada en silencio** una configuración explícita errónea.

Diferencia conocida: el sha256 de `T07_METRICAS.json` en `VerifiedSource.artifacts` es del blob LF (paquete) y en desarrollo del archivo de trabajo (CRLF en Windows), por lo que `source_fingerprint` difiere entre ambos caminos; no interviene en la identidad de las corridas generadas (usa solo los hashes del CSV/NPZ, idénticos).

## 2. Construir el paquete

```
python -m scripts.build_runtime_reference [--out artifacts/private/runtime_reference] [--force]
```
Usa Git local solo aquí; exige que manifiesto/métricas coincidan con el ancla versionada y con el commit aprobado, y que código/config coincidan con `codigo_sha256`/`config_sha256`. Resultado medido: 19 archivos, 7,6 MiB (`artifacts/private/runtime_reference/`, fuera de Git). Sin `.git`, `.env`, modelos `.joblib`, ventas ni credenciales.

## 3. Rutas y datos requeridos

| Contenedor | Variables | Montajes | Notas |
|---|---|---|---|
| API | las de T11A (`MONGODB_URI`, `MONGODB_DATABASE`, `AUTH_SECRET`, `ALLOWED_ORIGINS`, `DF_UPLOADS_DIR`) | `df_data:/data` | Solo valida y encola `generate_run`; **no** necesita el paquete (no se monta). |
| Worker | las mismas + `DF_RUNTIME_REFERENCE_DIR=/reference` | `df_data:/data`; paquete en `/reference` **solo lectura** (`${DF_RUNTIME_REFERENCE_HOST_DIR:-./artifacts/private/runtime_reference}`) | Lee ventas aprobadas de Mongo (≤ origen) y del paquete CSV/NPZ. No escribe en el paquete (FS raíz también de solo lectura). |

El almacén privado no se sirve por web: la API solo sirve el Angular compilado (`hardening.install_frontend`; sin `StaticFiles`/`mount`) y el paquete ni siquiera está montado en la API. Medido contra el proxy TLS del stack: `/manifest_referencia.json`, `/reference/…`, `/artifacts/…`, `/files/docs/T07_MANIFIESTO.json`, `/../reference/…` y `%2e%2e` devolvieron 404 JSON (`generacion/web_privado.json`; `/data/uploads/` devuelve la SPA, sin contenido de archivos).

Límites: `docker-compose.yml` fija `deploy.resources.limits` 0,5 CPU / 1 GiB para API y worker (`DF_APP_CPUS`, `DF_APP_MEMORY` los sobrescriben), equivalente a `infra/main.bicep` (0,5 / 1Gi).

## 4. Generación real medida (17/10/2026)

Entorno: imagen reconstruida (`docker build`, 25,8 s con caché), stack `df-t11b` (mongo 8.3.8, api, worker, proxy Caddy), Docker Desktop/Windows 11. Datos: **copia restaurada** `df_t11b_<ts>` desde `artifacts/private/t11a/backup` (restauración dentro de la red del stack con la propia imagen: ok=true, 0 problemas, 24,2 s incl. arranque del contenedor, 213,5 MB), usuarios de prueba nuevos con contraseñas aleatorias no impresas. No se tocó `demand_forecasting_v2/_dev/_pub`. Al terminar: `compose down -v` y borrado del archivo de secretos; solo se eliminaron contenedores, volúmenes y redes `df-t11b*`.

**Una generación real por HTTP**: login admin + CSRF → `POST /api/v1/runs {origin 2026-07-10, horizon_days 21, método promedio_28}` (202) → job → worker de la imagen.

| Medida | Resultado |
|---|---|
| Duración HTTP→completado | **22,2 s** (job: reclamado 00:34:33, completado 00:34:52 → 19 s en el worker; intento 1) |
| Memoria máxima del worker | **406,4 MiB** (cgroup `memory.peak`, incluye caché de páginas); `docker stats` muestreado cada ~1,5 s (14 muestras): máx. 370,2 MiB. CPU observada hasta ~50 % del único 0,5 vCPU limitado |
| Memoria máxima de la API | 128,1 MiB (cgroup); 61,2 MiB (`docker stats`) |
| OOM | `OOMKilled=false`, `oom_kill 0` en ambos, 0 reinicios. **1 GiB alcanza con ~40 % de uso (margen ≈ 2,5×)**; no hace falta ajustar plan/costo por memoria |

Verificación en la base restaurada (`generacion/auditoria_1.json`, `audit_compare.py`):
- Corrida `gen-20260710-34443ba3c400` `generated_baseline`, `completed`, `children_ref …~g1`; origen 10/07, fechas 11/07–31/07, horizonte 21; **3.647 SKU** × 21 = 76.587 pronósticos SKU + 756 de categoría (36 categorías); idéntico conjunto de claves que la histórica `hist-20260710-4ea348836e35`; `observed` nulo y `evaluable` falso en todas (no hay ventas futuras).
- Categorías = suma de SKU: diferencia máx. 4,3e-14 (promedio_28) y 2,2e-12 (RF).
- Comparador RF: 0 nulos; diferencia máx. 0,0 contra el CSV T07 del paquete (mismas claves) y contra la histórica; `promedio_28` difiere de la histórica/CSV como máximo 4,6e-10 (redondeo a 10 cifras del CSV; la corrida usa fracciones exactas).
- Recomendaciones: snapshot `T07_L7_S7_promedio_28_2026-07-10` (índice 39, fecha 10/07); 3.647 filas, 3.347 `ok`, 300 sin snapshot, **582 con pedido, 2.655 unidades**; 0 filas distintas frente a la histórica en 19 campos clave (estado, saldo, tránsito, suma/días 28, objetivo exacto, pedido, valor, escenario).
- Puntero activo intacto (`hist-20260710-4ea348836e35`, mismo `updated_at`); la generada no lo desplaza.

**Idempotencia y reinicio** (`generacion/idempotencia_reinicio.json`):
- Segundo pedido idéntico: 202 con el mismo `job_id`, `reused=true`; 0 cambios en corridas, puntero, pronósticos (311.724), recomendaciones (10.941) y trabajos.
- Reinicio del worker tras completar: 0 cambios.
- Reinicio **durante** una generación (origen 09/07, `docker kill` con el job `running`): reclamado de nuevo (intento 2, generación 2), completado a los ~90 s desde el pedido (incluye la espera de recuperación del arrendamiento); una sola corrida `gen-20260709-87ee274eb367`, pronósticos 311.724 + 76.188 + 756 = 388.668 y recomendaciones 10.941 + 3.628 = 14.569 (sin duplicados), 0 hijos huérfanos. Esa corrida usa su propio snapshot (09/07, índice 38) y declara «comparador no disponible: solo existe resultado del RF distribuido para el origen 10/07/2026». Nunca se usa el snapshot de otro día.

## 5. Pruebas

`tests/publish/test_runtime_reference.py` (22): paquete correcto verifica sin Git (PATH vacío) y coincide con el verificador de desarrollo; variable de entorno usa paquete; manifiesto/métricas/config/código alterados (también con índice actualizado), CSV y NPZ alterados, paquete incompleto (6 archivos), índice ausente/commit distinto/directorio inexistente, ancla versionada distinta, referencia opcional con motivo cuando falta la variable, `REFERENCIA_INVALIDA` si está definida y alterada, ausencia de rutas estáticas hacia el almacén. `tests/ops/test_t11b_generation.py`: montaje `:ro`, límites 0,5/1 GiB, API sin paquete, imagen sin referencia/Git. Resultados en el informe de entrega.

## 6. Límites

- Una sola ejecución medida (datos de 3.647 SKU); no es prueba de carga ni de concurrencia. Memoria/tiempo son de Docker Desktop local (otro hardware y E/S de Azure Files/Atlas darán otros tiempos; la latencia a Atlas no se midió).
- Los scripts de orquestación del ensayo (`artifacts/private/t11b/*.py`) son privados y no están versionados; la evidencia JSON sí está en `artifacts/private/t11b/generacion/`.
- El paquete debe reconstruirse si cambia `approved_reference` o el manifiesto T07; en Azure habrá que colocarlo en un almacén privado montado de solo lectura (decisión de despliegue pendiente; no se probó Azure Files).
- La imagen local `df-app:t11a-local` fue reconstruida con estos cambios (misma etiqueta).
