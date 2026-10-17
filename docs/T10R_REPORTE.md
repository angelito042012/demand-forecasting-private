# T10R — Reporte: cierre de R07–R10 (concurrencia y recuperación)

Fecha: 17/10/2026 (Lima). Parte de la entrega T10 revisada (9596d26) y `docs/REVISION_CODEX_09.md`. No se rehízo T10, no se abrió agosto, no se tocó la selección congelada (sha256 de `docs/SELECCION_CONGELADA.md` idéntico al de 9596d26), no hubo despliegue ni gasto. Semántica final: `docs/T10_CONTRATO.md` §8.

## Correcciones

| Hallazgo | Defecto | Corrección | Regresiones |
|---|---|---|---|
| R07 (P1) | La limpieza leía una generación `staging` vencida y borraba sus hijos aunque el dueño renovara/promoviera entre la lectura y el borrado | `reserve_abandoned`: CAS `staging+generation+lease vencido → failed (INTENTO_ABANDONADO)` **antes** de borrar; el intento antiguo ya no puede renovar, completar, escribir ni activar; si ganó el dueño, se conserva. Corridas `completed`/`superseded`/históricas y `children_ref` nunca se tocan. Una corrida `staging` vencida sin hijos también se reserva (se conserva el documento). | `tests/publish/test_t10r_publication.py` (8 pruebas R07) |
| R08 (P2) | `claim_run` robaba una publicación aunque su dueño renovara entre la lectura y el CAS | El CAS incluye el `lease_expires_at` leído; si cambió, no se desplaza (`PublishInProgressError`) | mismo archivo (3 pruebas R08, incluye dos contendientes) |
| R09 (P2) | Dos archivos distintos del mismo mes pasaban el chequeo a la vez y ambos se aprobaban (2 fuentes, 20 ventas) | Reserva durable `month_reservations` (nuevo `pipeline/data/month_lock.py`) antes de escribir; `import_workbook(fence=…)` comprueba/renueva la reserva por lote y antes de finalizar; escritura parcial ⇒ el mes queda `partial` para esa fuente | `tests/jobs/test_t10r_import.py` (10 pruebas) |
| R10 (P2) | La ranura del temporizador `error`/`procesando` quedaba como «ya procesada» sin trabajo | Reserva con propietario y lease; recuperación por CAS; reutiliza el job existente por la clave estándar (`recuperado`); un timer obsoleto no pisa la recuperación | `tests/jobs/test_t10r_scheduler.py` (10 casos), `tests/ops/test_t10r_loop.py` |

Cambios acotados: `pipeline/publish/protocol.py`, `pipeline/data/importer.py` (parámetro `fence` y valla por contextvar; sin cambio de esquema, claves ni controles R01–R04), `pipeline/jobs/handlers.py`, `pipeline/jobs/scheduler.py`. Sin cambios en fórmulas, cohortes, snapshot, T07, frontend ni API.

## Pruebas realmente ejecutadas

- **Fallaban antes**: las regresiones se ejecutaron contra el código anterior — R07/R08: 7 fallos (`artifacts/private/t10r/pre_fix_publication.log`); R10: 9 fallos (`pre_fix_scheduler.log`); R09: 6 fallos, entre ellos el escenario sincronizado con dos fuentes aprobadas (`pre_fix_import.log`).
- **Después**: las 32 pruebas T10R aprobadas (JUnit `pytest_t10r.xml`) y la suite completa `pytest tests`: **408 aprobadas, 6 omitidas** (las 6 son `RUN_REALDATA`: 3 de generación y 3 anteriores; no se ejecutaron, no se repitió T06/T07), 0 fallos (`pytest_full.xml`). `ruff check pipeline tests backend` limpio.
- Intercalaciones cubiertas (Mongo real, hilos con compuertas deterministas): R07 — lectura → renovación/promoción/activación → borrado; reserva primero → dueño antiguo no puede renovar/completar/escribir/activar; dos limpiadores; intento antiguo que vuelve tras una nueva generación; fallo parcial de borrado y repetición idempotente; protección de completed/superseded/históricas. R08 — renovación entre lectura y CAS; toma legítima con lease vencido; dos contendientes. R09 — dos fuentes sincronizadas tras el chequeo (un ganador, 0 filas del perdedor, sin registro de importación del perdedor); reinicio a mitad de importación; reintento de la misma fuente (`ya_existentes` > 0, sin duplicados); retorno tardío del dueño anterior (antes de escribir y en medio de la importación); otra fuente durante la recuperación; fallo previo a escribir libera el mes; meses independientes; archivo ya conocido ⇒ `sin_cambios`. R10 — fallo transitorio de encolado, caída tras reservar, caída tras crear el job, fallo al guardar `job_id`, dos timers recuperando (parametrizado `error`/`procesando`), ranura completada repetida, coalescencia y fechas Lima/UTC.
- **`--loop` real** (`tests/ops/test_t10r_loop.py`, base aislada `df_test_*`, Mongo real, worker real y temporizador `--loop --enable --interval-minutes 60` como procesos continuos; reloj de prueba acelerado ×1800 desde 2026-06-20T20:00Z): 2 corridas generadas completadas (orígenes 20/06 y 21/06, creadas por `scheduler`), ranuras únicas, ranuras del mismo origen `sin_cambios`, temporizador vivo mientras corre y **ambos procesos terminados al final** (verificado en la prueba y con `Get-CimInstance` posterior: 0 procesos `pipeline.jobs`). Ventas sintéticas; ningún dato real.
- No se repitió el navegador ni el frontend (no cambió); la comprobación E2E de T10 (16/16) sigue siendo la de T10, no se reclama de nuevo.

## Corrida staging `gen-20260620-d438bef389c9` (investigación)

- **Hecho**: estaba `staging`, generación 1, intento 1, `lease_expires_at` vencido, sin hijos (los purgó la limpieza anterior) y sin `error`. Su trabajo (origen 20/06) terminó `failed` por `PUBLICACION_EN_CURSO` tras 3/3 intentos. Causa: durante la demostración T10 se detuvo el worker a mitad de la publicación; los reintentos (backoff 5/10 s) cayeron dentro del lease de 120 s y se agotaron antes de que venciera. El mantenimiento anterior borraba hijos pero no reconocía la corrida vencida.
- **Acción**: con el mantenimiento corregido (`worker --once`) la corrida pasó a `failed` con `error.code = INTENTO_ABANDONADO` (documento conservado). Antes/después en `artifacts/private/t10r/staging_0620_antes.json` y `_despues.json`: puntero activo, estados de las demás corridas, 608 286 pronósticos / 28 678 recomendaciones / 2 backtests totales, 86 877 ventas y 560 notas de crédito **idénticos**. No se borró ninguna corrida.
- **Ruta de recuperación**: volver a pedir la generación del 20/06 con una `Idempotency-Key` nueva (la clave del trabajo previo quedó `failed`); `claim_run` toma la corrida `failed` (generación 2) y publica en `…~g2`. No se ejecutó: no es necesaria para T10R y las corridas generadas son de prueba.
- Con T10R: `max_intentos` = 5 y espera de 65 s para `PUBLICACION_EN_CURSO`, más lease de publicación de 60 s, evitan que ese caso se repita.

## Límites y pendientes

- El importador por CLI (`import_workbook` sin `fence`) no usa la reserva; es uso administrativo serial. Pendiente menor si se quisiera exclusión también allí.
- Una reserva `partial` bloquea otras fuentes del mes hasta remediación privilegiada (`release_month`, sin API); es deliberado (no liberar un mes parcialmente escrito).
- El reloj acelerado del temporizador es un adaptador de prueba (`DF_TEST_TIME_SCALE`, ignorado con `APP_ENV=production`); el cron diario real de 06:00 Lima no se esperó.
- Dos validadores de publicación y los 9 avisos de estilo de `scripts/generate_synthetic_inventory.py` siguen como estaban (decisión de Codex).
- Evidencias: `artifacts/private/t10r/` (JUnit, logs pre-corrección, auditoría de integridad solo lectura `auditoria_integridad.json`, antes/después de staging).

## Siguiente paso

Revisión de Codex de T10R. T11 (nube; Azure for Students y Atlas Free sin conectar, 459,39 MB locales, sin presupuesto de bolsillo) y T12 (agosto) no se iniciaron.
