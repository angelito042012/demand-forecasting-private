# T11A Empaquetado en contenedores y modo producción

Fecha: 17/10/2026. Alcance: preparación **local**. No hay recursos en la nube, ni imágenes en registros, ni datos fuera del equipo. Los datos del ensayo son sintéticos (un libro de 3 filas generado por las pruebas). Plan de nube: `docs/T11_PLAN_DESPLIEGUE.md`.

## Archivos

`Dockerfile`, `.dockerignore`, `docker-compose.yml` (solo ensayo), `deploy/entrypoint.sh`, `deploy/caddy/Caddyfile`, `deploy/mongo-init.js`, `deploy/production.env.template` (sin secretos), `infra/main.bicep` y `infra/main.parameters.example.json`, `backend/app/config.py`, `backend/app/hardening.py` (nuevo), `backend/app/main.py`, `pipeline/jobs/{worker,scheduler,handlers}.py`, `tests/backend/test_t11_production.py`, `tests/ops/test_t11_container.py`.

## Modo producción (`APP_ENV=production`)

- Arranque estricto: la API, el worker y el scheduler fallan si faltan `MONGODB_URI`, `MONGODB_DATABASE` (y, en API/worker, `DF_UPLOADS_DIR`); la API además exige `AUTH_SECRET` (≥ 32 car.), `ALLOWED_ORIGINS` (https exactos, sin barra final), `COOKIE_SECURE=true`; rechaza las bases `demand_forecasting_v2` y `demand_forecasting_dev`. Sin valores por defecto inseguros; no se lee `.env` (`Settings(_env_file=None)`). Los mensajes de error nombran variables, nunca valores.
- Cookies `Secure; HttpOnly; SameSite=Strict`, sin registro público (no existe ruta), sin CORS (mismo origen), `/docs` y `/openapi.json` desactivados, errores saneados (`ERROR_INTERNO`), cabeceras: CSP, X-Frame-Options, nosniff, Referrer-Policy, Permissions-Policy, COOP, HSTS, `Cache-Control: no-store` en `/api`.
- Límite de cuerpo: 25 MiB + 1 MiB de sobrecarga multipart (coherente con T10 `tam_max_comprimido_bytes`) y 1 MiB para JSON; 413 con envoltorio JSON, también con cuerpo troceado.
- `X-Forwarded-For`: `TRUSTED_PROXIES` (IP/CIDR, vacío por defecto = no se confía). Solo si el par TCP directo está en la lista se toma la primera IP no confiable desde la derecha; lo que antepone el cliente nunca cuenta. Uvicorn se arranca siempre con `--no-proxy-headers` (T08R §8 se mantiene).
- Angular compilado servido del mismo origen con fallback SPA; `/api/**` desconocida → 404 JSON (`NO_ENCONTRADO`), nunca `index.html`; recursos con extensión inexistentes → 404; sin salida del directorio; `/api/v1/health` intacto. Con producción y sin Angular compilado, la API no arranca.
- Worker y API usan la misma variable `DF_UPLOADS_DIR` (`pipeline/jobs/handlers.py::default_uploads_dir`).

## Imagen y roles

Una imagen (`Dockerfile`, 3 etapas: `node:24-slim` con `npm ci` + `ng build --configuration production`; `python:3.12-slim` instala `requirements.lock.txt` sin herramientas de desarrollo con `--no-deps` —en Linux xgboost declara además `nvidia-nccl`, solo GPU, no instalado—; imagen final usuario 10001, sin shell de login, HEALTHCHECK a `/api/v1/health`). Tamaño local 991 MB. Contexto en lista blanca (`.dockerignore`): sin datos, `.env`, `.git`, `.venv`, `node_modules`, `docs`, `tests`.

| Comando | Rol |
|---|---|
| `api` (por defecto) | uvicorn en :8000 |
| `worker` / `worker-once` | `python -m pipeline.jobs.worker` continuo / una vuelta |
| `scheduler` | sale con código 3 salvo `DF_SCHEDULER_ENABLE=true` (deshabilitado por defecto); `scheduler-once` para un tick |
| `cli …` | `python -m backend.cli` (p. ej. `create-user`, contraseña por `DF_NEW_PASSWORD`) |

## Ejecutar el stack local de ensayo

Variables obligatorias (el compose usa `${VAR:?}` y falla si faltan; nunca se escriben en archivos): `MONGODB_URI` (con usuario de aplicación y `authSource`), `MONGODB_DATABASE`, `AUTH_SECRET`, `MONGO_ROOT_USER`, `MONGO_ROOT_PASSWORD`, `MONGO_APP_USER`, `MONGO_APP_PASSWORD`. Opcionales: `ALLOWED_ORIGINS` (defecto `https://localhost:8443`), `DF_PROXY_PORT`, `DF_MONGO_IMAGE` (defecto `mongo:8.3.8`), `DF_PROXY_IMAGE` (`caddy:2.10-alpine`). Genere valores aleatorios en su shell y exporte las variables; luego `docker compose -p df-t11a up -d --build` y abra `https://localhost:8443` (certificado interno autofirmado de Caddy: advertencia esperada). Cree usuarios con `docker compose exec -T -e DF_NEW_PASSWORD api df-entrypoint cli create-user --username U --role admin` (la contraseña sale del entorno, no del argumento). Detener conservando datos: `docker compose down`; borrar todo: `docker compose down -v`.

Topología del compose: red `data` interna (sin salida a Internet) con mongo, api y worker; red `edge` (subred 172.31.250.0/24; proxy .2 fijo = `TRUSTED_PROXIES`, api .3) con proxy y api. Solo el proxy publica puerto, en `127.0.0.1`. Volúmenes nombrados: `mongo_data`, `df_data` (`/data`, subidas; compartido por api y worker), `caddy_data`. Contenedores con `read_only`, `cap_drop: ALL`, `no-new-privileges`. Caddy sobrescribe `X-Forwarded-For` con la IP remota. Scheduler: perfil `scheduler` (no se levanta por defecto).

**Límite de las subidas/modelos:** el volumen compartido lleva las subidas. Los artefactos privados de T07/T12 (modelos `.joblib`, NPZ, CSV) **no** se incluyen en la imagen ni en el volumen; la generación con modelos RF necesita montar ese almacén de solo lectura (decisión pendiente, `docs/T11_CONTRATO.md` §4). No se probó una corrida de generación en contenedor.

## Resultados reales

Pruebas ejecutadas (17/10/2026, Windows 11, Docker Desktop 29.7.2):

- `tests/backend/test_t11_production.py`: **28 pruebas pasan** (Mongo temporal `df_test_<uuid>`, sin Docker).
- `tests/ops/test_t11_container.py`: 4 pruebas estáticas pasan (Dockerfile, `.dockerignore`, texto del compose, `docker compose config` con variables ficticias y fallo sin variables) y el smoke con `RUN_CONTAINER_SMOKE=1`.
- **Smoke del stack real: 29/29 comprobaciones OK** (proyecto `df-t11a-<8 hex>`, base temporal `df_test_t11a_<8 hex>`, secretos y contraseñas aleatorios generados en la ejecución y no impresos; volúmenes eliminados al final). Cubre: health vía proxy TLS (`environment=production`), cabeceras, rutas Angular recargables (`/`, `/corridas`, `/pronosticos`, `/recomendaciones`) 200, `/api/v1/ruta-desconocida` → 404 JSON, login admin, cookie Secure+HttpOnly+SameSite=Strict, mutación sin CSRF → 403, subida sintética → 202, el worker la lleva a `completed`, 8 logins fallidos con `X-Forwarded-For` distinto → 401×5 y 429×3, subida presente en el volumen compartido, reemplazo de `api`+`worker` y `down`/`up` sin `-v` conservan subidas y trabajos, solo el proxy publica puertos (127.0.0.1), proceso uid 10001, sistema de archivos de solo lectura, el worker no sale a Internet, la imagen no contiene `.env`, HEALTHCHECK `healthy`, y los logs no contienen secretos. Evidencia: `artifacts/private/t11a/contenedores/smoke_resultado.json`, `smoke_logs.txt`, `build.log`.
- Regresión: ver informe de cierre (registrada en `artifacts/private/t11a/contenedores/regresion.txt`).

Limitaciones: el ensayo no reproduce el ingress de Azure ni Atlas; no se probó Azure Files (permisos SMB con uid 10001 `[NV]`); no se midió rendimiento ni una corrida de generación; ruff pasa sobre los archivos de este ámbito.
