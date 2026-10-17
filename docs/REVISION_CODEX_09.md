# Revisión T10: correcciones de concurrencia pendientes

17/10/2026, Lima. Entrega revisada: **9596d26** y sus antecedentes T10, desde da759f0. **T10 construido, todavía no aceptado.** El flujo habitual funciona, pero faltan cuatro garantías ante intercalaciones o fallos. Encargo correctivo: `ETAPA_09_CLAUDE.md` (T10R). No repetir T10 desde cero.

## Hallazgos reproducidos

### R07 — P1: limpieza que borra resultados ya publicados

`pipeline/publish/protocol.py:198–207`: `purge_orphans` lee una generación staging con lease vencido y decide borrar sus hijos. Entre esa lectura y `delete_many`, el dueño puede ejecutar `guard`, `complete_run` y activar la corrida: estas operaciones no invalidan la decisión anterior de limpieza. La limpieza termina borrando los hijos ahora referenciados por `children_ref`.

Reproducción determinista con **Mongo real**, interponiendo la promoción después de la lectura y antes de borrar: corrida `completed`, puntero activo a ella, `children_ref=review09~g1`, y **cero hijos restantes** tras borrar un pronóstico, una recomendación y un backtest de prueba. No se tocó ninguna corrida real.

Antes de borrar una generación todavía reclamable, se necesita una transición/reserva atómica que impida su renovación/promoción, con CAS sobre propietario/generación/estado/lease. Si la renovación/promoción ganó, se conserva. Una segunda lectura sin exclusión no resuelve la carrera. Proteger también los hijos de las corridas históricas y sustituidas, y conservar compatibilidad con Mongo standalone.

### R08 — P2: toma de control que ignora una renovación

`pipeline/publish/protocol.py:90–94`: tras leer un lease vencido, `claim_run` hace CAS solo sobre `_id/status/generation`. Si el dueño renueva entre lectura y CAS, el contendiente igualmente obtiene generación 2. Reproducción Mongo real: renovación antes del CAS confirmada; resultado `claimed`, generación 2. Comparar también el lease leído o su expiración mediante una condición atómica apropiada; no desplazar un intento que renovó a tiempo para la decisión de toma de control.

### R09 — P2: dos fuentes mensuales aceptadas simultáneamente

`pipeline/jobs/handlers.py:184–194`: comprobar `approved_sources` antes de `import_workbook` no reserva el mes. En una base temporal vacía, dos archivos sintéticos distintos de marzo pasan el control simultáneamente y ambos terminan `completed`, con **dos fuentes aprobadas y 20 ventas**. La barrera posterior rechaza el dataset con `MES_CON_VARIAS_FUENTES`. Se mantiene el bloqueo científico, pero el flujo web contamina el conjunto y requiere remediación.

Hace falta exclusión durable por mes/fuente integrada con reintentos/propiedad, antes de escribir: una sola fuente puede ganar, la otra queda rechazada/en cuarentena sin sus filas. Probar además la vuelta tardía de un importador cuyo intento fue reemplazado; el fencing del documento `jobs` por sí solo no protege las escrituras dentro de `import_workbook`. La base actual ya tiene sus meses aprobados y esta prueba **no la alteró**.

### R10 — P2: una reserva de timer fallida impide reintentar

`pipeline/jobs/scheduler.py:87–104`: insertar `scheduler_ticks` y luego encolar no es una operación atómica. Si el enqueue falla, la ranura queda `error` (o `procesando` si muere el proceso). Al reintentarla, el índice único provoca `ranura_ya_procesada` sin revisar ese estado ni recuperar el trabajo. Reproducción Mongo real con fallo transitorio inyectado: segundo tick con `job_id=null`, **no vuelve a llamar a enqueue y hay cero trabajos**. Con intervalo normal puede perderse la ejecución del día.

Permitir recuperación segura de la reserva incompleta/error y reconciliación cuando el job sí se creó pero falló la actualización del tick. Usar la identidad única del job; completar el registro del tick sin crear dos trabajos. Probar dos timers y reinicio a ambos lados del enqueue.

## Evidencia y alcance de la revisión

- **84 pruebas aprobadas**, 0 omitidas, un aviso de httpx/Starlette, 46,37 s: API T10, handlers, cadena Uvicorn+worker real, generación y esquema generado. JUnit: `artifacts/private/codex_review09_verified_tests.xml`; log homónimo `.log`.
- **35 pruebas aprobadas**, 0 omitidas, 40,76 s: cola, worker, scheduler, protocolo concurrente y login atómico, con Mongo real. JUnit: `artifacts/private/codex_review09_concurrency_tests.xml`; log homónimo `.log`.
- **119 pruebas selectivas aprobadas en total**. Las reproducciones adicionales detectan intercalaciones no cubiertas por esas pruebas verdes.
- Repros privadas ejecutables y JSON: `artifacts/private/codex_review09_jobs_repro.py`, `codex_review09_jobs_audit.json`, `codex_review09_import_race.py`, `codex_review09_import_audit.json`. Solo bases `df_test_review09_*`, eliminadas al terminar, y libros sintéticos.
- Intentos previos de la revisión encontraron límites del entorno (socket bloqueado, temporales/rutas largas de Windows y política de ejecución de PowerShell). No se contaron como éxitos ni como fallos funcionales del producto. Se concedió red y se usó una ruta temporal corta para las 119 pruebas anteriores. Las tres pruebas de registro de procesos no se repitieron con éxito aquí; la evidencia de Claude permanece diferenciada.
- Se leyeron el reporte y logs de Claude: pytest 376/6 omitidas, generación real 3/3, frontend106/build y Chrome16/16 son **resultados del ejecutor**, no nuevos resultados propios. No se repitió Chrome ni entrenamiento/T06/T07 ni evaluación final.
- Auditoría **solo lectura** de la base principal: histórica activa completed, 77 343 pronósticos, 3 647 recomendaciones, un backtest, conteos coherentes; selección congelada conserva su sha256. JSON privado: `artifacts/private/codex_review09_db_audit.json`. No se leyó agosto ni se modificó esa base.

## Decisiones de dirección

1. Mantener **`activate_run=False`** para las corridas de desarrollo T10. El administrador abre la corrida generada por su enlace/selección; la histórica auditada continúa como predeterminada. No agregar cambio automático del puntero por finalizar una prueba. La política de una futura corrida operativa se decidirá tras la evaluación final.
2. Dos validadores no justifican una refactorización amplia ahora. Mantener sus contratos y regresiones; compartir solo invariantes necesarios para estas correcciones. Los nueve avisos de estilo preexistentes del generador sintético no bloquean T10R.
3. Completar una comprobación acotada de `--loop` con worker real en base aislada; no dejar un servicio persistente. Resolver/documentar la corrida staging de prueba mediante mantenimiento seguro, sin borrar evidencia ni históricos para ocultarla.
4. Cuentas actualizadas: Azure for Students muestra US$100 disponibles y vencimiento 17/10/2027; Atlas Free creado, clúster demand-forecasting-dev en São Paulo. No se verificó conexión de la aplicación ni despliegue. Rotación de la credencial mostrada en captura pendiente de confirmación; no copiarla a ningún documento. Sin presupuesto de bolsillo; no habilitar pago por uso ni recursos de pago sin acuerdo concreto.
5. **Tamaño actual medido: 416 361 718 bytes de datos + 43 028 480 de índices = 459 390 198 bytes (459,39 MB)**, 15 colecciones, tras las corridas de T10. Sustituye la medición anterior de 185,48 MB para planificar T11. No migrar automáticamente el histórico completo a Atlas: falta medir crecimiento/retención, restauración y contenido necesario. No borrar ventas, resultados desfavorables o evidencias para ajustar cuota.

Después de cerrar R07–R10: revisión breve de sus regresiones, T12 bajo congelación y T11 publicación/HTTPS/copia-restauración (con capacidad y accesos comprobados); aceptación humana/informe antes del 23/10. Este documento **no abre agosto ni autoriza despliegue**.
