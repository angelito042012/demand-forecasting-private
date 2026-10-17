# T10 Contrato: carga web, cola durable, generación del método operativo y temporizador (v1)

Fecha: 17/10/2026. Extiende `docs/T08_CONTRATO.md` (sesión, errores, paginación, procedencia, colecciones de corridas) sin romper el historial T08R. Alcance: flujo administrativo **carga → trabajo → corrida publicada** en la demostración local. No hay despliegue, no se abre agosto, no se modifica `docs/SELECCION_CONGELADA.md` ni se repiten experimentos T06/T07. Configuración de política del servidor: `config/t10_config.json`.

## 1. Garantías de concurrencia (ya implementadas y probadas antes de este contrato)

- **Login**: `backend/app/auth/budget.py`. Reserva ATÓMICA de cupos (un documento por clave, `find_one_and_update` con pipeline) *antes* de verificar la contraseña; un fallo conserva su cupo, un éxito lo devuelve; el contador queda acotado al límite, de modo que una ráfaga paralela del mismo usuario/origen no valida más intentos que los permitidos (probado con 120 hilos y 60 peticiones simultáneas a un Uvicorn real). 429 + `Retry-After` y errores genéricos sin cambio; `--no-proxy-headers` local. Ventana fija (límite conocido: hasta 2 × límite en el cambio de ventana).
- **Cola** (`pipeline/jobs/queue.py`): colección `jobs`; transiciones por CAS sobre `{owner, generation, status=running}`; `claim` atómico; `heartbeat` renueva el lease; el trabajador obsoleto recibe `LostOwnership` en heartbeat/complete/fail.
- **Publicación** (`pipeline/publish/protocol.py`): propiedad por intento (`owner`, `generation`, lease renovable en `runs`), hijos aislados por intento (`run_id = "<run_id>~g<generation>"`), `guard` antes de cada lote/validación/promoción, promoción atómica por CAS (`complete_run` fija `children_ref`), puntero activo monótono, limpieza solo del propio espacio y `purge_orphans`. Los lectores consultan los hijos de `children_ref` y exponen siempre el `run_id` público.

## 2. Trabajos (`jobs`)

| Campo | Significado |
|---|---|
| `job_id` | uuid hex único |
| `type` | `import_excel` \| `generate_run` (lista cerrada) |
| `status` | `queued` \| `running` \| `completed` \| `failed` (sin otros estados) |
| `idempotency_key` | único; encolar dos veces la misma entrada devuelve el mismo trabajo |
| `input` / `public` | `input` es interno (rutas privadas, hashes); `public` es lo único que la API muestra |
| `created_by`, `created_at`, `updated_at`, `started_at`, `finished_at` | UTC |
| `attempts`, `max_attempts` (5, `cola.max_intentos`; el reintento por `PUBLICACION_EN_CURSO` espera 65 s, > lease de 60 s), `available_at` | reintentos con backoff; solo errores transitorios reintentan |
| `owner`, `generation`, `worker_id`, `lease_expires_at`, `heartbeat_at` | propiedad/fencing |
| `stage`, `progress` | etapas y conteos reales (nunca porcentajes inventados) |
| `result` | resultado público (ver §3/§4) |
| `error` | `{code, message (saneado ≤ 300), retryable, attempt, at}` |

Transiciones: `queued → running` (claim) `→ completed`; `running → queued` (fallo transitorio con intentos restantes, `available_at = ahora + backoff`); `running → failed` (error permanente, intentos agotados o `WORKER_PERDIDO`); `running` con lease vencido puede ser reclamado por otro worker (`generation + 1`). El error público nunca incluye trazas, rutas ni URIs.

### Tipos y entradas
- **`import_excel`**: `input = {upload_sha256, upload_path (relativa a data/private/uploads), size_bytes, month (detectado), label}`; clave `import:<sha256>`.
- **`generate_run`**: `input = {origin: "YYYY-MM-DD", horizon_days: 21, method: "promedio_28"}`; clave `gen:<origin>:<horizon>:<method>:<generador>:<digest de fuentes aprobadas ≤ origen>` (o la cabecera `Idempotency-Key` del administrador, que se une a la anterior): entradas distintas nunca comparten clave; una fuente nueva cambia el digest.

## 3. API (todas bajo `/api/v1`)

| Ruta | Permiso | Entrada | Salida |
|---|---|---|---|
| `POST /imports` | admin + sesión + CSRF (+Origin) | `multipart/form-data` campo `file` (.xlsx) | **202** `{job_id, status, upload:{sha256_short,size_bytes,month,label}, reused:bool}`; mismo archivo ⇒ mismo `job_id` |
| `POST /runs` | admin + CSRF | JSON `{origin, horizon_days?=21, method?="promedio_28"}` (modelo tipado, campos extra prohibidos) | **202** `{job_id, status, origin, horizon_days, method}`; origen fuera de [`origen_minimo`, `origen_maximo`] o horizonte > 21 ⇒ 422 `CORTE_FUERA_DE_RANGO`; método no permitido ⇒ 422 |
| `GET /runs/options` | lector/admin | — | `{origin_min, origin_max, origin_default, horizon_max, methods, development_policy:true}` |
| `GET /jobs` | admin | `page,page_size,status,type` | lista paginada de `public_job` |
| `GET /jobs/{job_id}` | admin | — | `public_job` + enlaces: `links:{import:"/imports/<id>", run:"/runs/<id>"}` cuando existan |
| `GET /imports`, `/runs`, … | como T08 | | las corridas generadas aparecen con `kind="generated_baseline"` |

- `lector` recibe 403 en cualquier mutación y en `/jobs`; sin sesión 401; sin CSRF 403. El navegador **no** puede enviar rutas, comandos, módulos, URI ni configuración arbitraria: solo los campos tipados anteriores.
- Las peticiones **no ejecutan** parsers largos, generación ni publicación: validan estructura ligera, escriben el archivo en el directorio privado (nombre `<sha256>.xlsx`, no servido), encolan y devuelven 202.
- Subidas (límites en `t10_config.json`): extensión `.xlsx` + firma ZIP real; ≤ 25 MiB comprimidos; ≤ 250 MiB expandidos y ≤ 200 entradas (anti zip-bomb, medidos sin descomprimir a memoria); sin `vbaProject.bin`/macros ni enlaces externos; `xl/workbook.xml` presente; encabezados de `REQUIRED_HEADERS` del importador; mes detectado en marzo–julio 2026; el nombre del cliente es solo una etiqueta saneada. Rechazos claros: 413 tamaño, 415 formato, 422 contenido/encabezados/mes.

## 4. Worker y procesamiento

`python -m pipeline.jobs.worker [--once] [--poll-seconds N] [--worker-id ID]`: independiente de HTTP; reclama atómicamente, mantiene un latido (hilo) que renueva el lease, procesa tipos permitidos y deja estado recuperable si se interrumpe. No usa `BackgroundTasks` ni listas en memoria como cola. Un solo worker es el modo por defecto; la exclusión soporta dos procesos.

### `import_excel` (reutiliza el importador schema2 y las reglas R01–R04)
1. Reverifica sha256 y estructura; pre-escaneo completo de fechas: cualquier fecha fuera de marzo–julio 2026 (o agosto) ⇒ error de datos permanente `FECHAS_FUERA_DE_ALCANCE`.
2. Si el sha256 ya es una fuente conocida (importación completada) ⇒ `completed` con `result.outcome="sin_cambios"` (no-op del importador; hashes/conteos/fingerprint anteriores intactos).
3. Si el mes ya tiene una fuente aprobada distinta ⇒ **no se importa ni se aprueba**: error permanente `MES_CON_FUENTE_APROBADA` (cuarentena lógica; el archivo queda en `data/private/uploads`), con mensaje que remite al procedimiento de `docs/REMEDIACION_FUENTES.md`. No contamina el dataset anterior.
4. Si no, `import_workbook(..., expected_month)`: ventas y notas de crédito separadas, conflictos, rechazos por motivo; `result = {outcome:"importado", import_id, estado, filas_leidas, ventas, notas_credito, rechazadas, rechazos_por_motivo, insertadas, ya_existentes, en_conflicto}`.
Límite actual: la sustitución de una fuente aprobada por otra no está soportada (una fuente aprobada por mes, ver `REVISION_CODEX_03`); requiere remediación en base nueva.

### `generate_run` (método operativo `promedio_28`)
- Entrada de datos: historia aprobada **solo hasta el origen** (`load_training_data(db, origin, start=2026-03-01)`, fuentes aprobadas, máscara, catálogo al origen). Nunca lee ventas posteriores al origen; los datos futuros no son cero: `observed = null`, `evaluable = false`.
- Pronóstico: `promedio_28` por (sku, almacén) = media de las observaciones útiles de la ventana de 28 días (señales exactas de `pipeline/publish/signals.py`), constante para h = 1…21; categorías = suma de los SKU del catálogo al origen; cohortes por regla T05 al origen; control `cero` derivado. `rf_categoria_distribuido` solo si existe un resultado histórico compatible (origen 10/07 y fingerprint/universo iguales a G4 del manifiesto T07 verificado); en otro caso `null` (comparador no disponible).
- Recomendaciones (hipotéticas, inventario simulado): snapshot histórico T07 `L7_S7_promedio_28` al cierre del origen (`día = origen − 2026-06-01`), tránsito = Σ pedidos emitidos − Σ recibidos hasta ese día, señal exacta del mismo origen, objetivo = `ceil(14·media + 7·media)` exacto (lógica común de `pipeline/publish/builders.py`). Solo los 3 347 SKU del universo simulado; el resto `sin_snapshot` (nunca stock 0). Si falta el artefacto verificado, se publican los pronósticos y el motivo de ausencia (`ARTEFACTO_SIMULACION_NO_DISPONIBLE`). Se verifican checksum, índice natural, origen y universo antes de usarlo.
- Corrida: `kind="generated_baseline"`, `run_id = gen-<AAAAMMDD>-<fingerprint12>`, `run_label = "Corrida de desarrollo generada por la aplicación con origen DD/MM/AAAA"`, `method.chosen="promedio_28"`, `provenance_notes`, manifiesto de fuentes (fingerprint de entrenamiento y sha256 de las fuentes), código (commit + hash del generador), configuración y señales. Identidad estable = tipo + origen + horizonte + método + parámetros + versión del generador + fingerprint de entrenamiento + fingerprint de señales + referencia al snapshot. Misma entrada ⇒ misma corrida; no se altera una corrida `completed`.
- Publicación con `publish_prepared` (propiedad por intento, validación de conteos/coherencia: categorías = suma de SKU, recomendaciones recalculables, sin campos futuros) y puntero monótono. Fallo ⇒ último válido intacto.
- Política (servidor): origen ∈ [2026-06-01, 2026-07-10], horizonte ≤ 21 ⇒ todo objetivo ≤ 2026-07-31. Origen de demostración 10/07. Agosto no se carga ni consulta.
- Generación y publicación se ejecutan solo en el worker; no reentrena RF/XGBoost ni repite folds.

## 5. Temporizador (`python -m pipeline.jobs.scheduler`)

`--once [--now ISO] [--interval-minutes N]` ejecuta un tick; `--loop` repite cada intervalo (proceso opcional, deshabilitado por defecto). Un tick calcula la ranura UTC, inserta un documento en `scheduler_ticks` con índice único por ranura (dos ticks simultáneos ⇒ uno gana; el otro registra "ranura ya procesada") y encola el mismo tipo `generate_run` con la clave estándar (sin duplicados). Origen elegible = `min(fecha de negocio Lima de la ranura, origen_maximo)` acotado a `origen_minimo`; si esa corrida ya existe ⇒ "sin cambios" y se conserva el resultado anterior. Ticks perdidos: se descartan (coalescente). No ejecuta experimentos ni el test final. Cronograma normal: diario 06:00 America/Lima (`intervalo_normal_minutos = 1440`); fechas de negocio en Lima, marcas técnicas en UTC. Prueba local con intervalo corto y reloj controlado.

## 6. Interfaz

Importaciones (admin): selector de archivo, envío con CSRF, seguimiento del trabajo (etapa/conteos reales), resultado (importado / sin cambios / rechazado con motivo legible) y enlace; lector sin controles de escritura (y 403 directo). Corridas (admin): origen permitido (de `/runs/options`), «Generar», trabajo en curso, enlace a la corrida `completed`. Corridas generadas: sin comparador u observaciones ⇒ texto «no disponible» (no ceros ni métricas inventadas); etiqueta de inventario simulado. Comparación: distinguir **origen**, **fechas objetivo** y **período de evaluación** (el origen G4 = 10/07 no significa que su evaluación termine el 10/07: objetivos y simulación llegan al 31/07). Recargar la página no pierde el trabajo (durable). Con la API caída no se activan mocks.

## 7. Operación local

`scripts/start-local.ps1` inicia API, frontend y worker (un solo worker); registra por proceso `{pid, hora de inicio, ejecutable}` y `scripts/stop-local.ps1` solo detiene un PID si hora de inicio y ejecutable coinciden (nunca por un PID reutilizado; no toca contenedores). El temporizador es opcional (`-Scheduler`) y su proceso queda registrado/visible. No se instalan tareas del sistema.

## 8. Semántica final tras T10R (R07–R10)

- **Limpieza de generaciones (R07).** `purge_orphans` nunca borra los hijos de una generación todavía reclamable sin antes **reservarla**: `reserve_abandoned` es un CAS `staging + generation + lease vencido/ausente → failed` (`error.code = INTENTO_ABANDONADO`; el documento de la corrida se conserva). Desde esa transición `guard`, `complete_run`, `insert_children` y la activación del intento antiguo fallan (`LostOwnership`). Si el dueño renovó o promovió primero, el CAS no coincide y los hijos se conservan. Se limpia sin reserva únicamente lo que ya no puede renovarse ni promoverse (generación superada, corrida `failed`, sin corrida). Nunca se tocan `children_ref`, corridas `completed`/`superseded` ni las históricas (ids sin `~g`). Una corrida `staging` con lease vencido y sin hijos también se reserva (queda `failed` con su motivo, no se borra). Es idempotente y tolera dos limpiadores y fallos parciales.
- **Toma de control (R08).** `claim_run` incluye en su CAS el `lease_expires_at` leído: si el dueño renovó entre la lectura y el CAS, no se le desplaza (`PublishInProgressError`).
- **Una fuente por mes (R09).** Colección `month_reservations` (`_id = "YYYY-MM"`, `sha256`, `owner`, `generation`, `state ∈ {importing, partial, approved}`, lease de 120 s). El handler `import_excel` reserva el mes **antes** de `import_workbook`; otra fuente en cualquier estado recibe `MES_CON_FUENTE_APROBADA` (mensaje legible; el archivo queda en cuarentena en el almacén privado; sin filas ni registro de importación). La misma fuente puede retomar (CAS sobre el lease leído; `IMPORTACION_EN_CURSO` retryable si el dueño sigue vivo). `import_workbook(fence=…)` comprueba/renueva la reserva (CAS por owner+generation) antes de cada lote, antes de escribir conflictos y antes de finalizar; un dueño desplazado recibe `LostReservation` (→ `IMPORTACION_CONCURRENTE`, retryable) y no escribe ni aprueba. Cierre: sin conflictos ⇒ `approved`; con conflictos ⇒ se libera (la fuente no queda aprobada); fallo antes de escribir ⇒ se libera; fallo con escrituras ⇒ `partial` (el mes **no** se libera para otra fuente; solo la misma fuente retoma; remediación privilegiada `month_lock.release_month`, ver `docs/REMEDIACION_FUENTES.md`). Límite: el importador por CLI no usa la reserva (uso administrativo serial).
- **Temporizador (R10).** La ranura `(intervalo, ranura)` se reserva con propietario y lease de 60 s. Una ranura `error`, o `procesando` con lease vencido, se **recupera** con CAS (dos timers: gana uno; el otro responde `ranura_en_proceso`/`ranura_ya_procesada`). El encolado usa la clave estándar `generate_run_key`: si el job ya existía (el proceso murió tras encolar), se reutiliza y la ranura termina como `recuperado`; nunca se duplica. Un timer obsoleto no puede sobrescribir la recuperación (`ranura_tomada`). `--loop` captura fallos de tick sin morir, acepta `--poll-seconds` y, solo para pruebas, `DF_TEST_TIME_SCALE`/`DF_TEST_CLOCK_START` (ignorados con `APP_ENV=production`). Sigue deshabilitado por defecto.
- **Sin cambios por T10R:** `activate_run=False` para las corridas de desarrollo (la histórica auditada sigue activa; enlaces y selector abren exactamente la generada elegida), fórmulas, cohortes, snapshot y resultados T07, selección congelada, agosto.

### Alcance de aceptación Codex10

R07–R10 cerrados para el flujo local actual. La valla comprueba propiedad antes de cada lote; no cancela un bulk ya emitido ni constituye transacción multidocumento. La reserva conserva la misma SHA durante recuperación, con upserts idempotentes. La CLI sin fence debe ejecutarse serialmente y nunca junto a cargas web/worker. La recuperación del timer presupone fuentes/config estables: antes de permitir cambiarlas mientras hay ticks incompletos, persistir en cada reserva el payload y clave de job originales y probar cambio de digest entre enqueue y finalización. Ver REVISION_CODEX_10.md; no generalizar «nunca duplica» a ese escenario todavía no habilitado.
