# T11A — Reporte: R11, integración local del paquete final, contenedores, base de publicación, restauración y plan de despliegue

Fecha: 17/10/2026 (America/Lima). **No se creó ningún recurso externo, no se consumió crédito, no se transfirió ningún dato a la nube y no se desplegó nada.** Agosto solo se lee, como antes, desde los artefactos ya validados de T12; no se repitieron `prepare`/`evaluate`, T06/T07 ni entrenamientos. `demand_forecasting_v2` y `_dev` se leyeron sin modificarlas (9 corridas, 86 877 ventas y 608 286 pronósticos intactos). Inventario simulado con supuestos; no corresponde al inventario real de la empresa.

## 1. R11 — cierre fiel del estado final (commits 71656c2 y e1905cb)

- `auditoria` y `reporte` ahora registran inicio/fin/error/intentos en `estado.json` (clase `StateFile` compartida); `completa=true` solo con las **siete** fases; una auditoría no aprobada deja la fase en `error` y el reporte exige auditoría aprobada.
- 6 regresiones nuevas (`tests/final/test_t12_estado.py`); **4 fallaban con la versión anterior** (`artifacts/private/t11a/r11_pre_fix.log`). Cubren: siete fases ⇒ completa; fallo de auditoría o de reporte ⇒ `completa=false` sin reporte válido; recuperación sin invocar `load_final_test_sales`, `load_training_data`, `fixed_predictions`, `sequential_simulation` ni `forecast_origin_t07`; hashes originales intactos; reconciliación.
- **Reconciliación real** (`python -m scripts.run_final reconcile`): solo auditoría y reporte sobre los artefactos guardados. Registro de **corrección técnica posterior** en `estado.json` y `T12_MANIFIESTO.json` (`correcciones[0]`: commit base 71656c2, 17/10/2026 18:12 Lima). Las cinco fases de cálculo conservan sus fechas e intentos (sin inventar timestamps); los 9 hashes originales (predicciones, modelo, inicialización, reales, series, métricas, manifiesto, CSV mínimo) coinciden antes y después. Estado final: `completa=true`, siete fases. Antes/después en `artifacts/private/t11a/estado_antes_reconciliacion.json` y `estado_despues_reconciliacion.json`.

## 2. Contrato y paquete final integrado (docs/T11_CONTRATO.md)

- Tres tipos de corrida separados: `historical_development` (T07), `generated_baseline` (T10) y `final_evaluation` (T12). La final no activa el puntero ni sustituye nada; su id es `final-20260731-d587255d87fb` (sello T12 `d587255d…ce663`).
- Publicador `pipeline/publish/final_package.py` + `scripts/publish_final.py`: lee **solo** artefactos validados (siete fases, auditoría aprobada, sello e hashes), no importa sklearn ni lee agosto de Mongo, calcula la capacidad antes de insertar (31,90 MB BSON), publica con el protocolo T10R (staging, `children_ref`, CAS, `activate_run=False`) y es idempotente (2.ª y 3.ª ejecución = `sin_cambios`). Publicó 78 918 pronósticos SKU + 777 de categoría, 0 recomendaciones y 1 backtest; las categorías son la suma de SKU.
- API (solo lectura): `kind`, `evaluation_period`, `final_package` y cuatro advertencias obligatorias en las corridas; fechas hasta 2026-08-21 **solo** para una corrida `final_evaluation` (la barrera global de >31/07 sigue 422 `AGOSTO_RESERVADO` para histórica/generada); recomendaciones de la final: 200 con `items=[]`, `unavailable_reason=RECOMENDACION_NO_VALIDADA_PARA_ESTE_ORIGEN` y `see_run` (sin usar el snapshot de otro día). Ninguna ruta ejecuta modelos.
- UI: tipos de corrida rotulados, vista «Evaluación final (T12)» separada de T07 (hallazgo primario, H10/H14/H21/diaria, cohortes, cobertura/SKU nuevos, simulación 27 combinaciones, «servicio frente a inventario»), WAPE ≠ exactitud, resultados desfavorables visibles, sin ganador, recomendaciones con motivo y enlace a la demostración histórica. Corrección posterior a la entrega del agente: el sesgo relativo publicado llega como `{promedio_28, rf_distribuido}` y la vista lo leía como número; ahora muestra el del comparador RF.

## 3. Base de publicación, capacidad y restauración (docs/T11A_INVENTARIO_BD.md, docs/T11A_ACTA_RESTAURACION.md)

- Base nueva `demand_forecasting_pub` (50,95 s de copia desde v2 en solo lectura): ventas 86 877, créditos 560, importaciones 12, las dos corridas históricas con hijos (77 343 pronósticos y 3 647 recomendaciones cada una), la corrida final y 3 backtests; puntero → histórica auditada. **No** se copiaron sesiones (22), usuarios (2), jobs (8), `login_*` ni las 7 corridas generadas (se **archivan** con hashes en `artifacts/private/t11a/archivo/`, 19 archivos, 6,5 MB; nada se borró de v2).
- Copia de seguridad (18,91 s, 13,05 MB comprimidos, 10 colecciones, manifiesto sha256 `fa9561aa…434b`) y **restauración real** en una base distinta (17,91 s; 24,09 s con verificación): conteos, hash de contenido (10/10), índices, estado de corridas, `children_ref` con todos los hijos y 0 huérfanos, puntero, sin colecciones secretas; contenido idéntico al de `demand_forecasting_pub`.
- **Tamaño medido tras restaurar: 213,90 MB de datos+índices = 41,8 % de la cuota de 512 MB** (objetivo ≤ 60 %: cumple). (La base `demand_forecasting_pub` ocupa 224,96 MB por fragmentación de su historia de inserciones; la restaurada es la cifra de planificación.) Por disco comprimido 49,99 MB (9,8 %). Una segunda restauración de verificación (para la demostración) dio 213,67 MB.
- Proyección medida: histórica ≈42 MB, generada ≈44,8 MB, final ≈37,9 MB por corrida. Margen hasta el 60 %: ≈93 MB (≈2 corridas generadas más). Propuesta no ejecutada si hiciera falta espacio: archivar la sustituida `hist-…52b01cd999dd` (≈41 MB).
- Modelos, NPZ de simulación (~128 MB), CSV mínimos, logs y Excel **no** están en Mongo: almacenamiento privado separado con hashes.

## 4. Empaquetado y producción (docs/T11A_EMPAQUETADO.md)

- `APP_ENV=production` falla al arrancar sin `MONGODB_URI`, `MONGODB_DATABASE`, `AUTH_SECRET` (≥ 32), `ALLOWED_ORIGINS` (https) y `DF_UPLOADS_DIR`; rechaza v2/dev y `COOKIE_SECURE=false`; sin registro público ni CORS; cabeceras de seguridad; errores saneados; cuerpo 25 MiB (subidas) / 1 MiB (JSON); `X-Forwarded-For` solo desde `TRUSTED_PROXIES` (vacío por defecto); Angular compilado servido del mismo origen con fallback SPA y `/api/**` desconocida ⇒ 404 JSON. Worker y scheduler exigen URI y base explícitas en producción y el worker usa el mismo `DF_UPLOADS_DIR` que la API. El validador de producción vive en `Settings.validate_production()` (no rompe la prueba preexistente).
- Imagen única (991 MB) multi-stage (Node `npm ci` + `ng build`, Python 3.12-slim con el lock, usuario no root, `HEALTHCHECK`) con roles `api`, `worker`, `worker-once`, `scheduler`, `scheduler-once`, `cli`. `docker-compose.yml` solo ensayo local (Mongo con `--auth`, red de datos interna, Caddy con TLS autofirmado, secretos aleatorios por entorno).
- **Smoke del stack real: 29 de 29** (`artifacts/private/t11a/contenedores/`): health por el proxy, rutas Angular recargables, `/api` desconocida ⇒ JSON, cookies Secure/HttpOnly/SameSite=Strict + CSRF, subida sintética procesada por el worker, 5×401 y luego 429 variando `X-Forwarded-For`, reemplazo de contenedores y `down/up` sin `-v` conservan subidas y trabajos, Mongo y worker no expuestos, proceso no root, FS de solo lectura, sin `.env` en la imagen, logs sin secretos.

## 5. Plan de despliegue y costos (docs/T11_PLAN_DESPLIEGUE.md)

Propuesta no ejecutada (Azure Container Apps Consumption en Brazil South + Azure Files + ACR Basic + Log Analytics + Atlas Free; `infra/main.bicep` compila con Bicep 0.48.1; sin `what-if` ni despliegue). Costo estimado (tarifas de la API pública de precios de Azure consultadas el 17/10/2026; **reverificar en la calculadora**): ≈ US$5–7 hasta el 23/10 (techo ≈ US$20 si todo estuviera siempre activo) y ≈ US$28–30/mes encendido (≈ US$11–13 con API que escala a cero + job cada 5 min). **No verificado**: egress y snapshots del share, un medidor «Environment Management Hour» (US$0,2/h ≈ US$144/mes, vigencia sept. 2026; el plan no usa endpoints privados), regiones permitidas en Azure for Students, IPs de egreso hacia Atlas, rango del salto del ingress para `TRUSTED_PROXIES`. Accesos mínimos y decisiones a aprobar: §13 del plan (login de solo lectura con device code, Contributor + User Access Administrator en un grupo de recursos nuevo, usuario de aplicación mínimo en Atlas con lista de IP, credencial rotada por canal privado).

## 6. Pruebas realmente ejecutadas

- `pytest tests`: **511 aprobadas, 7 omitidas** (6 `RUN_REALDATA` + el smoke de contenedores sin su bandera), 0 fallos (`artifacts/private/t11a/pytest_full.xml`). Aportes nuevos: R11 (6), publicador final (22), copia/restauración (13), API final (14), producción (28 + 4 estáticas de contenedor).
- Frontend: `ng test` 127 aprobadas (21 nuevas) y build de producción correcto.
- Smoke de contenedor real: 29/29 (con `RUN_CONTAINER_SMOKE=1`).
- **E2E en Chrome real con el paquete final real** (`e2e_t11a.mjs`, API + proxy de desarrollo + worker sobre una copia restaurada de la base de publicación, usuarios de prueba separados, ids exactos): **20/20** (`artifacts/private/t11a/e2e_t11a_resultado.json`, capturas en `screens/`): tipos de corrida y activa histórica; cifras de la UI iguales a `T12_METRICAS.json` (78,1 % / 79,1 % / 100,0 %, n = 3 401, mejora −1,3 % visible, «RF declarado ganador: no»); comparación sin `run` = T07 (no se mezclan); pronósticos 01–21/08 y recarga de ruta; recomendaciones no disponibles con motivo y enlace a la histórica; barreras de fechas (422/200/422), 404 JSON, lector sin poder generar (403), 777 filas de categoría; con la API detenida no hay datos inventados (error).
- No se repitieron T06/T07, `prepare`/`evaluate` ni los 4 folds.

## 7. Límites y pendientes reales

- **Nada está desplegado ni publicado en la nube.** Contenedores locales no equivalen a despliegue.
- Costos: cifras de una API pública de precios, sin cotización de la cuenta; varios ítems **no verificados** (arriba).
- Generación dentro del contenedor no probada (los artefactos T07/T12 no van en la imagen; una corrida con RF necesitaría montarlos de solo lectura).
- Atlas Free: 512 MB, 100 ops/s y 10 GB/semana de transferencia **[V]**; sin peering ni endpoints privados; la conexión de la aplicación no se probó (sin credencial). Rotación de la contraseña expuesta en captura: la gestiona el usuario por canal privado.
- Crear el usuario administrador de la base de publicación por el canal seguro (las copias no incluyen usuarios).
- Sigue pendiente la aceptación humana (T13) y los entregables T14/T15.

## 8. Siguiente paso

Revisión de Codex de T11A. La autorización de aprovisionamiento debe darse sobre el plan concreto (recursos, región, costo máximo, pasos) de `docs/T11_PLAN_DESPLIEGUE.md`, antes de crear recursos, subir imágenes o transferir datos.
