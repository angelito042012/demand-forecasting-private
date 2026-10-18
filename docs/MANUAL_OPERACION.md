# Manual de operación (borrador)

Estado: borrador T14A, código de referencia `28a5f49` (18/10/2026). Todo lo descrito como probado se probó **en local**. Publicación en la nube: **pendiente de aprobación** (ver `docs/T11_PLAN_DESPLIEGUE.md`, propuesta no ejecutada). Fuentes: `docs/GUIA_LOCAL.md`, `docs/T11A_EMPAQUETADO.md`, `docs/T11B_ACTA_RECUPERACION_INTEGRAL.md`, `docs/T11B_GENERACION_CONTENEDOR.md`, `docs/T10_CONTRATO.md`, `docs/T11_CONTRATO.md`.

## 1. Dos escenarios: local y publicación

| | Escenario local (existe) | Publicación (no existe) |
|---|---|---|
| Ejecución | Scripts PowerShell + Mongo local; o compose de ensayo con proxy TLS autofirmado | Azure Container Apps + MongoDB Atlas (propuesta) |
| Base | `demand_forecasting_v2` (desarrollo) o copia restaurada | `demand_forecasting_pub` (nunca `_v2`/`_dev`) |
| HTTPS | HTTP local (`COOKIE_SECURE=false`, solo con `APP_ENV=development`) o TLS interno de Caddy | HTTPS de la plataforma (pendiente) |
| Estado | Probado en local | **[PENDIENTE: no existe publicación]** |

## 2. Arranque local (sin contenedores)

Requisitos: Windows, Python 3.12 en `.venv`, Node 24/npm 11, MongoDB en `127.0.0.1:27017` (contenedor `df-mongo-dev`; los scripts no lo crean ni lo detienen), `.env` local a partir de `.env.example` (no versionado, no imprimir).

1. Crear usuario (la contraseña se pide por consola):
   `.venv\Scripts\python.exe -m backend.cli create-user --username <usuario> --role admin` (o `--role lector`).
2. Publicar la corrida histórica (una vez, idempotente):
   `.venv\Scripts\python.exe -m scripts.publish_run --manifest t07` (opción `--supersede <run_id>` para sustituir una corrida con defecto).
3. Iniciar API, frontend y un worker: `powershell -File scripts/start-local.ps1` → API `http://127.0.0.1:8000/api/v1/health`, web `http://localhost:4200`. Registra los procesos en `artifacts/private/t08/procesos.json` (logs en `artifacts/private/t08`). Si ya existe ese registro el script se niega: ejecute antes `stop-local.ps1`.
4. Temporizador opcional (deshabilitado por defecto): `powershell -File scripts/start-local.ps1 -Scheduler -EnableScheduler [-SchedulerMinutes 1440]`.
5. Detener solo los procesos propios: `powershell -File scripts/stop-local.ps1`.

Worker manual: `.venv\Scripts\python.exe -m pipeline.jobs.worker --once` (una vuelta) o sin `--once` (continuo). Scheduler: `-m pipeline.jobs.scheduler --once` o `--loop --enable` (06:00 Lima, 1440 min; la misma ranura no duplica trabajos).
Carga masiva por CLI: `python -m pipeline.data.importer --source <carpeta> --db <base>`; es administrativa, **serial, nunca simultánea con cargas web/worker**.
Diagnóstico del entorno: `powershell -File scripts/doctor.ps1`.

## 3. Contenedores y compose (ensayo local, T11A/T11B)

Una imagen (`Dockerfile`, 3 etapas) con roles por comando: `api` (por defecto), `worker`/`worker-once`, `scheduler` (sale con código 3 salvo `DF_SCHEDULER_ENABLE=true`), `scheduler-once`, `cli …` (`python -m backend.cli`).

Variables obligatorias para el compose (nunca en archivos; `docker-compose.yml` usa `${VAR:?}` y falla si faltan): `MONGODB_URI` (usuario de aplicación y `authSource`), `MONGODB_DATABASE`, `AUTH_SECRET`, `MONGO_ROOT_USER`, `MONGO_ROOT_PASSWORD`, `MONGO_APP_USER`, `MONGO_APP_PASSWORD`. Opcionales: `ALLOWED_ORIGINS` (defecto `https://localhost:8443`), `DF_PROXY_PORT`, `DF_MONGO_IMAGE`, `DF_PROXY_IMAGE`, `DF_APP_CPUS`/`DF_APP_MEMORY` (defecto 0,5 CPU / 1 GiB). Genere valores aleatorios en su shell y expórtelos; no los escriba en el repositorio.

- Levantar: `docker compose -p df-t11a up -d --build` → `https://localhost:8443` (advertencia de certificado autofirmado: esperada).
- Crear usuarios: `docker compose exec -T -e DF_NEW_PASSWORD api df-entrypoint cli create-user --username U --role admin` (la contraseña sale del entorno).
- Scheduler (perfil, no arranca por defecto): `docker compose --profile scheduler up`.
- Detener conservando datos: `docker compose down`; borrar todo (incluye volúmenes): `docker compose down -v`.
- Topología: Mongo en red interna sin puertos; solo el proxy publica puerto, en `127.0.0.1`; volúmenes `mongo_data`, `df_data` (`/data`, subidas, compartido por API y worker), `caddy_data`; contenedores de solo lectura, sin capacidades, usuario 10001.
- Generación en contenedor: el **worker** necesita `DF_RUNTIME_REFERENCE_DIR=/reference` con el paquete de referencia montado **solo lectura** (`DF_RUNTIME_REFERENCE_HOST_DIR`, defecto `./artifacts/private/runtime_reference`). La API no lo monta. Construcción del paquete (usa Git local solo aquí): `python -m scripts.build_runtime_reference [--out ...] [--force]`. Si la variable está definida y el paquete es inválido, la generación falla con `REFERENCIA_INVALIDA` (no degrada en silencio); sin la variable, la corrida se publica sin comparador ni recomendaciones.

Medido en local (17–18/10/2026, una ejecución): generación real 22,2 s, memoria pico del worker ≈ 406 MiB con límite 1 GiB, sin OOM. No es prueba de carga ni de rendimiento en nube.

## 4. Variables de producción (sin valores)

Plantilla: `deploy/production.env.template`. Con `APP_ENV=production` el arranque es estricto y los mensajes nombran variables, nunca valores.

| Variable | Rol |
|---|---|
| `APP_ENV=production`, `APP_TIMEZONE=America/Lima` | Modo y zona |
| `MONGODB_URI` | URI con usuario de aplicación mínimo (readWrite sobre una base); secreto |
| `MONGODB_DATABASE` | Base de publicación; se rechazan `demand_forecasting_v2` y `_dev` |
| `AUTH_SECRET` | Aleatorio ≥ 32 caracteres; secreto |
| `ALLOWED_ORIGINS` | Orígenes https exactos, sin barra final |
| `TRUSTED_PROXIES` | IP/CIDR del salto de proxy; vacío = no confiar en `X-Forwarded-For` |
| `DF_UPLOADS_DIR` | Directorio de subidas compartido por API y worker (`/data/uploads`) |
| `DF_RUNTIME_REFERENCE_DIR` | Solo worker: paquete de referencia de solo lectura |
| `COOKIE_SECURE` | Debe ser `true` en producción |
| `DF_SCHEDULER_ENABLE` | `true` para habilitar el scheduler (por defecto no) |

Los secretos se entregan por el gestor de secretos de la plataforma, nunca por chat ni en el repositorio. No se lee `.env` en producción. Uvicorn se arranca siempre con `--no-proxy-headers`.

## 5. Worker y temporizador

El worker toma trabajos `import_excel` y `generate_run` de la cola en Mongo; sin worker activo los trabajos quedan «En cola». Es reiniciable: un trabajo interrumpido se reclama de nuevo (probado: intento 2 sin duplicados). Una solicitud idéntica reutiliza el mismo trabajo. El temporizador está **deshabilitado por defecto** y requiere fuentes y configuración estables durante recuperaciones.

## 6. Respaldo y restauración

Comando de nivel superior (Mongo + bundle privado de artefactos, lista cerrada `config/t11b_private_bundle.json`):

```
python -m scripts.backup_restore export-all  --db demand_forecasting_pub --out artifacts/private/t11b/respaldo --maintenance-confirmed
python -m scripts.backup_restore restore-all --from artifacts/private/t11b/respaldo --db df_restore_t11b_<ts> --dest artifacts/private/t11b/restaurado_<ts> [--report ruta.json]
```

Reglas:
1. **Mantenimiento obligatorio:** antes de `export-all`, detenga API, worker y scheduler (`stop-local.ps1`). `--maintenance-confirmed` es requisito; el comando además rechaza si hay corridas en `staging`, trabajos `running`, ticks en proceso o escrituras activas, y aborta si el contenido de alguna colección cambia durante el volcado (aun con el mismo conteo). Estos controles son barreras, no sustituyen detener los escritores.
2. `--out` debe ser un directorio nuevo o vacío. Un archivo de la lista cerrada ausente deja el respaldo `integro=false` y falla salvo `--allow-partial`; un respaldo parcial no se restaura.
3. `restore-all` exige una base destino **nueva y vacía**, distinta de `demand_forecasting_v2/_dev/_pub`, y un directorio `--dest` nuevo y vacío distinto de los originales y del bundle. Verifica hashes antes y después y ejecuta una prueba funcional del paquete. Informa por separado `mongo_ok`, `artefactos_ok` y `recuperacion_integral_ok` (true solo si ambos).
4. Se excluyen del respaldo `users`, `sessions`, `login_*`, `jobs` y `scheduler_ticks`: tras restaurar hay que **recrear usuarios**.
5. Existen también `export`, `restore` y `verify` (solo Mongo, T11A) con las mismas reglas de base nueva; use `export-all` para recuperación integral.

Medido en local (17/10/2026): export 40,6 s, bundle de 43 archivos (147 MB) íntegro, restauración Mongo 18,9 s (10/10 colecciones), bundle 43/43 hashes. El respaldo privado no debe subirse a Git ni compartirse sin acuerdo de destino y acceso.

## 7. Fallos típicos

| Problema | Causa probable | Acción |
|---|---|---|
| `start-local.ps1`: «Ya hay un registro de procesos» | Quedó `procesos.json` de una sesión anterior | `stop-local.ps1` (solo detiene procesos propios verificados) |
| Health `degraded` / base no disponible | Mongo detenido | Iniciar `df-mongo-dev`; los scripts no lo hacen |
| No se puede iniciar sesión | Sin usuario o 429 por intentos | `create-user`; esperar 15 min |
| Trabajo en cola sin avanzar | Worker no activo o fallido | Revisar `artifacts/private/t08/worker.err.log`; `-m pipeline.jobs.worker --once` |
| API de producción no arranca | Falta variable o frontend compilado, base prohibida, `COOKIE_SECURE`/`ALLOWED_ORIGINS` incorrectos | Leer el mensaje (nombra la variable) |
| Compose falla de inmediato | Variable obligatoria sin definir | Exportarla en el shell |
| `REFERENCIA_INVALIDA` | Paquete de referencia alterado o incompleto | Reconstruir con `build_runtime_reference` |
| `export-all` rechazado | Falta `--maintenance-confirmed`, hay escritores o directorio no vacío | Detener procesos; usar directorio vacío |
| Carga rechazada por mes con fuente aprobada | Fuente distinta ya aprobada | `docs/REMEDIACION_FUENTES.md` |

## 8. Pendiente para publicar

Nada de esto está hecho ni autorizado: cuota/permisos efectivos de Container Apps (el último preflight muestra Microsoft.App registrado y `ManagedEnvironmentCount` Brazil South 0/1; no demuestra despliegue), usuario mínimo y credencial rotada en Atlas, imagen en registro, montajes privados, HTTPS, CSRF/proxy en la plataforma, restauración en la plataforma, y aprobación del plan de costo (máximo propuesto US$ 20 con condiciones de detención). Ver `docs/T11_PLAN_DESPLIEGUE.md`.
