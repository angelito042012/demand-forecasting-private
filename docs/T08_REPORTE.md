# T08 + integración de lectura T09: reporte de pruebas y limitaciones

Fecha: 17/10/2026, America/Lima. Demostración **local** con resultados **existentes** de desarrollo (corrida histórica al 10/07/2026). No es un despliegue, no hay carga web ni ejecución de corridas desde la aplicación (T10), y todo inventario es **simulado con supuestos; no corresponde al inventario real de la empresa**. Agosto no se consultó.

## Qué se construyó

| Parte | Archivos principales |
|---|---|
| Ajustes del motor (límites señalados por Codex) | `pipeline/sim/engine.py`: validación estricta de entradas (L, forma, finitud, enteros, días de revisión y objetivos) y conservación **diaria** del saldo; 21 pruebas nuevas en `tests/sim/test_engine.py`. Ecuaciones y resultados T07 sin cambio. |
| Contrato | `docs/T08_CONTRATO.md` (API, sesión, errores, paginación, persistencia, publicación, recomendación) |
| Selección congelada (sin ejecutar) | `docs/SELECCION_CONGELADA.md`, `config/seleccion_congelada.json` y `.sha256` |
| Autenticación | `backend/app/auth/*`, `routers/auth.py`, `routers/admin.py`, `backend/cli.py`: cookie de sesión HttpOnly/SameSite=Strict, token de 256 bits (solo su sha256 en Mongo), CSRF por sesión + Origin + JSON, expiración absoluta (8 h) e inactividad (1 h), revocación, rotación, rate limit en servidor, scrypt (biblioteca estándar), roles `admin`/`lector`, sin registro público ni credenciales por defecto |
| Persistencia | `pipeline/publish/*`, `scripts/publish_run.py`, `config/t08_publish.json`: publicador idempotente staging→completed con verificación de checksums y del código **por commit**; índices únicos; lectores ignoran corridas incompletas |
| API de lectura | `backend/app/routers/{imports,sales,runs,forecasts,recommendations,backtests}.py`, `backend/app/data/*`: filtros tipados, `sort` de lista cerrada, sin operadores Mongo, agosto rechazado |
| Frontend | `frontend/src/app/*`: acceso, resumen, importaciones, corridas, pronósticos, recomendaciones (cálculo paso a paso), comparación, sistema; modo demostración solo con `?demo=1` y rótulo visible |
| Operación local | `scripts/start-local.ps1`, `scripts/stop-local.ps1`, `docs/GUIA_LOCAL.md`, `.env.example` |

La corrida publicada en `demand_forecasting_v2`: `hist-20260710-52b01cd999dd` (fold G4 de T07, objetivos 11–31/07): 76 587 pronósticos SKU, 756 de categoría (36 × 21, agregados desde SKU con catálogo ≤ 10/07), 3 647 recomendaciones (3 347 con inventario simulado, 640 con pedido > 0; 300 `sin_snapshot` sin stock supuesto) y un backtest T07 (27 combinaciones). Método elegido `promedio_28`; RF «comparador experimental que no ganó»; `cero` control.

## Flujo demostrado en navegador real

Chrome del sistema (Playwright-core 1.64, instalado fuera del repositorio en `artifacts/private/t08/e2e/`), contra API (uvicorn) y Mongo reales, proxy de Angular en `localhost:4200`. 24 comprobaciones, 24 aprobadas (`artifacts/private/t08/e2e_resultado.json`; capturas en `artifacts/private/t08/screens/`, privadas):
ruta protegida → acceso; credenciales incorrectas (mensaje genérico); login; cookie HttpOnly/SameSite=Strict, no legible por JS ni en Web Storage; corridas con etiqueta y antigüedad (99 días al consultar); detalle de corrida; pronósticos con filtros de nivel y SKU (21 días de un SKU); recomendaciones con etiqueta de inventario simulado y `scenario_id`, SKU sin snapshot sin stock cero, cálculo paso a paso (stock 5, tránsito 2, pedido 1; se verificó a mano contra el NPZ); comparación (27 combinaciones, RF no ganó, más servicio con más stock); importaciones sin botón de carga; **sesión expirada** (vencida en Mongo) → vuelve a acceso con «Su sesión venció»; logout revoca (API 401); lector → 403 en `/admin/users`; mutación sin CSRF → 403; agosto → 422; operador Mongo en parámetro → 422; **API caída** → «Servicio no disponible» sin datos falsos.

Defectos encontrados por el E2E y corregidos: el resumen mostraba `[object Object]` en días excluidos; texto duplicado «No se supone stock cero»; con la API caída el proxy de desarrollo devolvía un 500 sin JSON y la pantalla decía «error inesperado» (ahora «Servicio no disponible, reintente»).

## Pruebas ejecutadas (resultados reales)

- Suite integral con `RUN_REALDATA=1` (backend, pipeline, simulación, tests de datos reales): **226 aprobadas, 0 omitidas, 1 aviso** (deprecación httpx/Starlette), 509 s; log `artifacts/private/t08/pytest_full.log`.
- Frontend: `npm run build` correcto; `npm test` 42 aprobadas (Vitest + HttpTestingController).
- Agentes: auth 33 pruebas, persistencia/rutas 54 (informes de los agentes; la suite integral las incluye).
- `ruff` limpio sobre backend, pipeline, tests y scripts nuevos.
- La CLI `python -m backend.cli create-user` se ejecutó desde terminal (usuarios locales de demostración; las contraseñas no se imprimen ni se versionan, están en `artifacts/private/t08/e2e_credentials.json`, local).

## Limitaciones y pendientes (honestos)

- Es una demostración local sobre HTTP (`COOKIE_SECURE=false` solo con `APP_ENV=development`); en HTTPS debe ser `true`. El rate limit usa `request.client.host`; detrás de un proxy hay que revisar `X-Forwarded-For`.
- El cálculo de la recomendación usa el promedio de 28 días con la precisión del CSV de T07 (10 cifras significativas): en un caso límite de exactos enteros podría diferir en una unidad de la política simulada; se redondea a 9 decimales antes del techo como en el motor.
- La recomendación es una sugerencia hipotética fuera del calendario de revisión original (no es un pedido ni una simulación nueva).
- `/imports` lista `agosto.xlsx` sin cifras y marcado `reservado_prueba_final` (la carga existe en la base; no se leen sus ventas).
- Pruebas de concurrencia de publicadores no ejecutadas; carga/rendimiento no medidos (A13 pendiente); accesibilidad y diseño sin revisar; las capturas son privadas.
- La congelación de la evaluación final **no se ejecutó**: no hay `scripts/run_final.py`, no se entrenaron paquetes finales, no se leyó agosto ni `reference_v1`.
- Pendientes posteriores: carga web y batch/timer (T10), ejecución final bajo congelación revisada (T12), despliegue HTTPS y copia/restauración (T11), aceptación humana e informe. Lista de accesos de nube necesarios: `docs/GUIA_LOCAL.md` (sin contratar nada ni solicitar secretos por chat).
- La aplicación completa no está terminada: esto es el núcleo local de lectura autenticada.
