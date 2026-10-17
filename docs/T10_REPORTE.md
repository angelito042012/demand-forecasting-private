# T10 — Reporte: carga web, cola durable, generación promedio_28 y temporizador

Fecha: 17/10/2026 (Lima). Alcance: **demostración local**, sin despliegue ni gasto en nube. Agosto de 2026 **no se abrió**; `docs/SELECCION_CONGELADA.md` y `config/seleccion_congelada.json` no se modificaron; no se repitió ningún entrenamiento. Contrato: `docs/T10_CONTRATO.md`; configuración: `config/t10_config.json`.

## 1. Qué se construyó (hechos verificados)

| Área | Entregable | Dónde |
|---|---|---|
| Presupuesto de login atómico | Reserva por documento único (ventana fija, contador acotado, reserva antes de verificar la contraseña, reembolso al acertar) | `backend/app/auth/budget.py`, `routers/auth.py` |
| Cola durable | Colección `jobs` (queued/running/completed/failed), lease, latido, generación (fencing), reintento con backoff, `LostOwnership` | `pipeline/jobs/queue.py` |
| Publicación con propiedad | Hijos aislados por intento (`<run_id>~g<n>`), promoción por CAS (`children_ref`), puntero activo monótono, purga de huérfanos | `pipeline/publish/protocol.py`, `publisher.py` |
| API | `POST /api/v1/imports` (multipart .xlsx), `POST /api/v1/runs`, `GET /jobs`, `GET /jobs/{id}`; admin + CSRF + Origin; 202 + `job_id`; lector 403 | `backend/app/routers/{imports,runs,jobs}.py`, `uploads.py` |
| Validación del Excel | 25 MiB comprimido / 250 MiB expandido, límite de entradas, sin macros ni enlaces externos, encabezados, solo 2026-03..07, agosto rechazado | `pipeline/jobs/xlsx_check.py`, `handlers.py` |
| Importación | Handler `import_excel`: mismo archivo ⇒ `sin_cambios`; otra fuente para un mes ya aprobado ⇒ `MES_CON_FUENTE_APROBADA` (no se importa ni aprueba) | `pipeline/jobs/handlers.py` |
| Generación | `promedio_28` por SKU con señales exactas (`Fraction`), origen 2026-06-01..2026-07-10, horizonte ≤ 21; observado nulo; categorías = suma de SKU; comparador RF solo si el origen/fuentes coinciden con T07; recomendaciones solo desde el snapshot simulado T07 (L7/S7) con tránsito hasta el origen; `sin_snapshot` nunca es cero | `pipeline/generate/` |
| Worker | `python -m pipeline.jobs.worker [--once]`, latido en hilo, fencing, mantenimiento (agotados + huérfanos) | `pipeline/jobs/worker.py` |
| Temporizador | `python -m pipeline.jobs.scheduler --once|--loop --enable`; ranura UTC única; coalescencia; deshabilitado por defecto | `pipeline/jobs/scheduler.py` |
| Frontend | Carga, panel de trabajos con seguimiento, formulario de generación (solo admin), rótulos de origen/fechas objetivo/período de evaluación, valores no disponibles ≠ 0 | `frontend/src/app/…` |
| Operación | `start-local.ps1` lanza API + web + worker con registro de procesos (pid + hora de inicio + ejecutable); `stop-local.ps1` solo detiene lo registrado | `scripts/` |

Cambios de integración en esta entrega: la API y el temporizador usan **la misma función de clave** (`pipeline.jobs.keys.generate_run_key`); `DF_UPLOADS_DIR` (solo pruebas/operación) redirige el directorio privado de subidas; el lease de publicación bajó de 120 s a 60 s (igual al del trabajo); el reintento por `PUBLICACION_EN_CURSO` espera 65 s (config) y los intentos máximos son 5.

## 2. Pruebas realmente ejecutadas

- `pytest tests -q`: **376 aprobadas, 6 omitidas** (3 realdata de la generación + 3 anteriores sin `RUN_REALDATA`), 0 fallos (`artifacts/private/t10/pytest_full.log`).
- `RUN_REALDATA=1 pytest tests/generate/test_realdata_generation.py` (agente worker, base `df_test_*`, sin agosto): 3 aprobadas. Con origen 10/07 reproduce el fold G4: 3 647 SKU, 76 587 filas, `promedio_28` igual al CSV T07 (error relativo ≤ 4e-10); 3 347 recomendaciones con snapshot y 300 `sin_snapshot`; idénticas a la ruta histórica. Segunda publicación = `sin_cambios`.
- Frontend (vitest): 106 aprobadas y build correcto (entrega del agente frontend, commit 03c93e5; no se repitió tras la integración porque no cambió el frontend).
- `ruff check pipeline tests backend`: limpio. `scripts/generate_synthetic_inventory.py` tiene 9 diagnósticos de estilo preexistentes, no tocados (pendiente menor).
- Cadena real Uvicorn + worker en procesos separados y base aislada: `tests/ops/test_t10_chain.py` (subida, duplicado, conflicto, corrupto, agosto, lector).
- Concurrencia determinista: `tests/backend/test_login_budget.py`, `tests/jobs/test_queue.py`, `tests/publish/test_protocol_concurrency.py`, dos procesos worker reales, reinicio tras matar el proceso.
- **E2E en Chrome real** contra API + web + worker + Mongo reales (`artifacts/private/t08/e2e/e2e_t10.mjs`): **16/16** (`artifacts/private/t10/e2e_t10_resultado.json`, capturas en `artifacts/private/t10/screens/`):
  1. Reenvío de `julio.xlsx` original ⇒ «Sin cambios»; hashes de fuentes, 86 877 ventas, 560 notas de crédito, fingerprint y número de importaciones idénticos antes/después.
  2. Archivo sintético de agosto rechazado en la petición, sin encolar.
  3. Generación al 10/07: corrida `gen-20260710-34443ba3c400` (77 343 pronósticos en hijos aislados `~g1`), el puntero activo sigue en la histórica `hist-20260710-4ea348836e35`.
  4. Pronósticos con etiqueta «generada por la aplicación» y observado «no disponible»; pedido del SKU 12040025 = media 3/7, objetivo 9, pedido 0, con la etiqueta de inventario simulado.
  5. Lector: sin formulario de carga ni de generación; `POST /runs` 403; `GET /jobs` 403.
  6. Recarga con trabajo en curso (sigue visible). Worker local-1 detenido a mitad de la generación (origen 03/07); local-2 lo toma al vencer el lease (intento 2) y deja **una** corrida completada, sin duplicados; el puntero y las corridas previas intactos.
- Temporizador con reloj controlado (`artifacts/private/t10/scheduler_demo.log`, base aislada): ranura nueva ⇒ `encolado`; misma ranura ⇒ `ranura_ya_procesada`; ranura siguiente ⇒ otro origen.

## 3. Hechos, decisiones y límites

- La corrida generada **no activa** el puntero por defecto (`activate_run=False`): decisión del agente worker para no desplazar la histórica auditada; se puede cambiar por parámetro. Pendiente de decisión de Codex.
- Las corridas generadas no tienen backtest propio (`GET /backtests` ⇒ 404 por diseño) ni métricas; el RF solo aparece cuando coincide con T07.
- Efecto en la base de demostración `demand_forecasting_v2`: además de las dos corridas históricas se publicaron corridas **generadas** (orígenes 10/07, 22/06, 25/06, 28/06, 30/06, 03/07, todas `completed`) y quedó una corrida `gen-20260620-d438bef389c9` en `staging` de un intento interrumpido al probar (el trabajo agotó intentos con 3 máx.). No es evidencia de mejora; son pruebas de la cadena. Las corridas históricas no se modificaron.
- Fallo encontrado y corregido durante el E2E: reintentos por `PUBLICACION_EN_CURSO` agotaban 3 intentos antes de vencer el lease (ver §1).
- El simulador de pedidos es de T07: si cambiaran las fuentes aprobadas, las recomendaciones salen marcadas `fuentes_coinciden_con_t07: false`. Cada generación verifica de nuevo los artefactos T07 (~8–16 s, sin caché).
- Limitaciones que **no** se resolvieron: `publisher.validate_published` y `validate.py` generado son dos validadores; el temporizador `--loop` no se ejecutó como servicio continuo (solo `--once`); no hay HTTPS, respaldo ni despliegue (T11); no se midió ningún resultado nuevo.
- No se afirma publicación, despliegue ni mejora real de inventario. Todo inventario es simulado con supuestos; no corresponde al inventario real de la empresa.

## 4. Siguiente acción

Revisión de Codex de T10 (commits en rama `master`). Después, a decisión de Codex: T11 (requiere accesos de nube, sin gasto autorizado) y T12 (evaluación final bajo la selección congelada, que abriría agosto).
