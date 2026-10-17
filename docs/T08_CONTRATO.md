# T08 Contrato de API, sesión, persistencia y publicación (v1)

Fecha: 17/10/2026. Sustituye lo que contradiga en `CONTRATOS.md` (la sección «API propuesta» y «Persistencia» pasan a ser históricas; las claves de venta del importador vigente son las de `docs/ESTRATEGIA_CLAVES.md`, esquema v2, no las claves antiguas). Alcance: demostración local con resultados **existentes** (corrida histórica de desarrollo al 10/07/2026). No hay carga web ni entrenamiento por HTTP (pendiente T10). Agosto está cerrado: ninguna ruta lee ventas con fecha > 2026-07-31.

Etiquetas obligatorias en la UI y en toda salida de corridas, recomendaciones y comparaciones:
- `run_label`: **Corrida histórica de desarrollo al 10/07/2026**.
- `provenance`: `SYNTHETIC_NOT_REAL_INVENTORY` y `scenario_id` en todo lo relacionado con stock, tránsito, costos y pedidos. Texto visible: **Inventario simulado con supuestos; no corresponde al inventario real de la empresa**.
- Las ventas observadas (`provenance=OBSERVED_EXCEL`) se distinguen siempre de stock/costos supuestos. Unidades: «unidad base»; moneda `PEN` solo en importes y costos supuestos.

## 1. Convenciones

- Base: `/api/v1`, JSON UTF-8. Fechas de negocio `YYYY-MM-DD` (America/Lima); instantes técnicos ISO-8601 UTC con `Z`.
- Error uniforme: `{"error": {"code": "<CODIGO>", "message": "<texto en español sin detalles internos>", "details": [...opcional...]}}`. Códigos: `NO_AUTENTICADO` 401, `SESION_EXPIRADA` 401, `PROHIBIDO` 403, `NO_ENCONTRADO` 404, `ENTRADA_INVALIDA` 422, `DEMASIADOS_INTENTOS` 429 (+`Retry-After`), `CSRF_INVALIDO` 403, `ORIGEN_NO_PERMITIDO` 403, `AGOSTO_RESERVADO` 422, `SERVICIO_NO_DISPONIBLE` 503. Nunca se devuelven trazas, rutas locales, URIs, hashes de contraseña ni tokens.
- Paginación: `page` (≥1, por defecto 1) y `page_size` (1–200, por defecto 50). Respuesta `{"items": [...], "page": n, "page_size": m, "total": t, "has_more": bool}`.
- Orden: parámetro `sort` solo de una lista permitida por ruta (`campo` o `-campo`); campos y filtros fuera de lista → 422. No se aceptan objetos Mongo ni operadores (`$`) en ningún parámetro; las consultas se construyen en el servidor con filtros validados y tipados.
- Fechas de consulta de ventas/pronósticos: rango máximo 400 días; cualquier fecha > 2026-07-31 → 422 `AGOSTO_RESERVADO` («agosto de 2026 está reservado para la prueba final»).
- Permisos: lectura = `lector` o `admin`; rutas `/admin/*` y mutaciones de usuarios = `admin`. Se comprueban en el servidor en cada petición.

## 2. Sesión y autenticación

- Solución: **cookie de sesión opaca** `df_session` con token aleatorio (`secrets.token_urlsafe(32)`, 256 bits); el servidor guarda solo `sha256(token)` en `sessions`. Atributos: `HttpOnly`, `SameSite=Strict`, `Path=/`, `Secure` salvo `COOKIE_SECURE=false` (excepción local explícita, solo con `APP_ENV=development`). Nunca en `localStorage`.
- Mismo origen: el navegador usa `http://localhost:4200`; el servidor de desarrollo de Angular hace proxy de `/api` hacia `http://127.0.0.1:8000`. CORS cerrado (sin `Access-Control-Allow-Origin: *`); solo `ALLOWED_ORIGINS` exactos, con credenciales.
- Vigencia: absoluta 8 h (`SESSION_ABSOLUTE_HOURS`), inactividad 1 h (`SESSION_IDLE_MINUTES`); validadas en el servidor con UTC; índice TTL sobre `expires_at`. Logout revoca (`revoked_at`) y borra la cookie. Un login exitoso crea sesión nueva (rotación) y revoca la sesión previa presentada, si la hay.
- CSRF: cada sesión tiene un `csrf_token` aleatorio (se guarda su hash). `POST/PUT/PATCH/DELETE` exigen cabecera `X-CSRF-Token` válida **y** comprobación de `Origin` (o `Referer`) contra `ALLOWED_ORIGINS`; `Content-Type: application/json` obligatorio en login y mutaciones. El login (sin sesión) exige `Origin` permitido y JSON.
- Contraseñas: `hashlib.scrypt` de la biblioteca estándar (N=2^15, r=8, p=1, sal aleatoria de 16 bytes, formato `scrypt$N$r$p$sal_b64$hash_b64`), comparación en tiempo constante; mínimo 12 caracteres. Sin contraseñas por defecto. Usuarios: `users` {`username` único en minúsculas, `password_hash`, `role` ∈ {`admin`,`lector`}, `active`, `created_at`, `schema_version`}. Alta: CLI local `python -m backend.cli create-user --username U --role admin|lector` (contraseña por `getpass` o variable `DF_NEW_PASSWORD`; nunca por argumento ni registrada) y `POST /admin/users` (admin, CSRF). No hay registro público.
- Rate limit de login en servidor (colección `login_attempts`, TTL 15 min): 5 fallos por (usuario, IP) y 20 por IP en 15 min → 429. Respuesta de credenciales incorrectas idéntica para usuario inexistente, inactivo o contraseña errónea (misma forma, cálculo de hash ficticio para igualar tiempo). Nunca se registran contraseñas ni tokens.

### Rutas de acceso

| Método y ruta | Permiso | Entrada | Salida |
|---|---|---|---|
| `GET /health` | público | — | `{"status":"ok"\|"degraded","database":"ok"\|"unavailable","version"}` (sin detalles) |
| `POST /auth/login` | público (+Origin, JSON, rate limit) | `{"username","password"}` | 200 + `Set-Cookie`; `{"username","role","csrf_token","expires_at"}` |
| `GET /auth/me` | sesión | — | `{"username","role","csrf_token","expires_at","idle_expires_at"}` |
| `POST /auth/logout` | sesión + CSRF | — | 204 (revoca y limpia cookie) |
| `GET /admin/users` | admin | paginación | usuarios sin hash |
| `POST /admin/users` | admin + CSRF | `{"username","role","password"}` | 201 `{"username","role"}` |

## 3. Rutas de datos (lectura; `lector` o `admin`)

Todas las respuestas de corrida incluyen `run_id`, `run_label`, `cutoff`, `generated_at`, `published_at`, `age_days_at_view` (días entre `cutoff` y hoy en Lima, mostrado aunque la publicación sea reciente) y `is_active`.

| Ruta | Parámetros (validados) | Respuesta |
|---|---|---|
| `GET /imports` | `page,page_size,mes` | cargas existentes: `import_id, archivo, mes, estado, filas_leidas, ventas_aceptadas, notas_credito, rechazadas, insertadas, ya_existentes, en_conflicto, iniciado_utc, finalizado_utc`. Sin filas ni datos de clientes. |
| `GET /imports/{import_id}` | — | lo anterior + `rechazos_por_motivo`, `conflictos_abiertos` (conteo), `sha256` abreviado, `incidencias` (solo códigos y conteos). 404 si no existe |
| `GET /sales/summary` | `from,to` (≤ 2026-07-31), `group_by` ∈ {`day`,`month`,`category`}, `categoria` opcional | `{"provenance":"OBSERVED_EXCEL","unit":"unidad base","currency":"PEN","from","to","items":[{"key","lineas_venta","unidades","importe_pen"}], "notas_credito":{"lineas","importe_pen"}, "excluded_days":[...]}`; las notas de crédito se informan aparte, no netas |
| `GET /runs` | `page,page_size,status`(solo `completed` se lista por defecto) | corridas completas; las incompletas nunca se devuelven |
| `GET /runs/{run_id}` | — | corrida con `method{chosen:"promedio_28",comparator:"rf_categoria_distribuido",control:"cero",note}`, `config`, `sources`, `artifacts` (nombre, sha256, tamaño; **sin rutas locales**), `code{commit}`, `counts`, `coverage{skus_pronosticados,skus_con_recomendacion,skus_sin_snapshot,categorias}`, `evaluation_period`, `provenance_notes` |
| `GET /forecasts` | `run_id` (por defecto la activa), `level` ∈ {`sku`,`categoria`}, `sku`, `categoria`, `cohorte`, `from,to`, `page,page_size`, `sort` ∈ {`target_date`,`-target_date`,`entity_id`,`-entity_id`,`pred_chosen`,`-pred_chosen`} | items: `{"run_id","level","entity_id","sku","almacen","categoria","cohorte","target_date","h","chosen_method":"promedio_28","pred":{"promedio_28","rf_categoria_distribuido","cero"},"observed","evaluable","provenance":"OBSERVED_EXCEL"}`; `observed` existe solo porque la corrida es un backtest histórico y se rotula así; cantidades en unidad base |
| `GET /recommendations` | `run_id`, `categoria`, `sku`, `status` ∈ {`ok`,`sin_snapshot`}, `only_orders` (bool), `page,page_size`, `sort` ∈ {`sku`,`-order_qty`,`order_qty`,`categoria`} | items con el cálculo (ver §5) |
| `GET /recommendations/{sku}` | `run_id`, `almacen` (por defecto `1`) | un item + `explanation` (texto paso a paso) |
| `GET /backtests` | `run_id` | lista: `backtest_id, kind, label, folds, created` |
| `GET /backtests/{backtest_id}` | `view` ∈ {`predictive`,`simulation`,`all`} | métricas T07 (backtest de desarrollo): predictivas por nivel/cohorte/método/vista (agregado de 4 folds solapados), selección provisional, cobertura; simulación de los nueve escenarios × 3 políticas (totales y cohortes), supuestos (`L,S,R,costo 65 %,holding 20 %/365`) y límites. Siempre con `scenario_id`, `provenance` y `disclaimer` |

El servidor **no reentrena ni simula** al consultar: solo lee documentos publicados.

## 4. Persistencia

Base `MONGODB_DATABASE` (por defecto `demand_forecasting_v2`). Colecciones nuevas (no se tocan `sales`, `credit_notes`, `imports`, `import_*`; v1 y Excel intactos). Todas con `schema_version: 1` y validación en el publicador; índices creados de forma idempotente (migración no destructiva `pipeline/publish/schema.py`).

| Colección | Contenido | Índices |
|---|---|---|
| `users`, `sessions`, `login_attempts` | ver §2 | `users.username` único; `sessions.token_hash` único + TTL `expires_at`; `login_attempts` TTL |
| `runs` | un documento por corrida: `run_id`, `status` ∈ {`staging`,`completed`,`failed`}, `kind:"historical_development"`, `run_label`, `idempotency_key` (único), `fingerprint`, `cutoff:"2026-07-10"`, `origin`, `target_start:"2026-07-11"`, `target_end:"2026-07-31"`, `horizon_days:21`, `generated_at` (UTC, de la fuente), `published_at`, `evaluation_period`, `method`, `config`, `sources`, `artifacts`, `code`, `counts`, `coverage`, `provenance_notes`, `error` | `run_id` único; `idempotency_key` único; `(status, cutoff)` |
| `run_pointer` | `{_id:"active", run_id, updated_at}` | — |
| `forecasts` | por (`run_id`,`level`,`entity_id`,`target_date`): `sku,almacen,categoria,cohorte,h,pred{...},observed,evaluable` | único `(run_id, level, entity_id, target_date)`; `(run_id, level, categoria, target_date)`; `(run_id, level, sku)` |
| `recommendations` | por (`run_id`,`sku`,`almacen`): ver §5 | único `(run_id, sku, almacen)`; `(run_id, categoria)`; `(run_id, status, order_qty)` |
| `backtests` | `backtest_id` único, `run_id`, `kind:"T07_desarrollo"`, secciones `predictive`, `simulation`, `selection`, `coverage`, `assumptions`, `disclaimer` | `backtest_id`; `run_id` |

**Publicación (staging lógico, sin transacciones multidocumento):** (1) verificar artefactos contra el manifiesto (sha256 y estructura; el código se verifica contra el commit registrado en el manifiesto, no contra el árbol actual); (2) crear `runs` con `status=staging` y `idempotency_key`; (3) insertar hijos con `run_id` nuevo; (4) validar conteos y coherencia (SKU con pronóstico, categorías = suma de SKU, recomendaciones recalculables); (5) pasar a `completed` y actualizar `run_pointer`. Si falla: `status=failed` + `error` genérico, el puntero no cambia y los lectores ignoran todo lo que no sea `completed`. Reintento con el mismo `idempotency_key` o `fingerprint` ya completado no duplica (devuelve el `run_id` existente); un `staging/failed` previo se limpia únicamente de sus propios hijos (por `run_id`) antes de reintentar. La CLI (`python -m scripts.publish_run`) es privilegiada y separada del HTTP; solo acepta una ruta de manifiesto en lista cerrada configurada, nunca rutas ni modelos enviados por usuarios.

## 5. Corrida histórica inicial y recomendación

**Corrida**: «histórica de desarrollo al 10/07/2026»: fold G4 de T07 (`corte 2026-07-10`, objetivos 2026-07-11…2026-07-31, 21 días), `predicciones_folds.csv.gz` (columnas `fold,entidad,cohorte,fecha,h,evaluable,real,pred_promedio_28,pred_referencia_fija_0531,pred_rf_distribuido`). Elegido: `promedio_28`; comparador experimental `rf_categoria_distribuido` (no ganó); control `cero` (pred = 0, derivado). Categorías agregadas **desde SKU** con el catálogo ≤ 10/07 (vía `load_training_data(db, 2026-07-10).catalog`, ruta aprobada); se suman `pred` y `observed` de los SKU del catálogo; SKU sin categoría → `DESCONOCIDA` (se informa, no se mezcla). `observed` y `evaluable` provienen del CSV (07/06 no cae en este bloque).

**Recomendación de vista previa** (sugerencia hipotética, fuera del calendario de revisión de T07; no es un pedido ejecutado ni una simulación nueva): `scenario_id = "T07_L7_S7_promedio_28_2026-07-10"`, snapshot al **cierre del 10/07/2026** de la trayectoria `L7_S7_promedio_28` de `simulacion_series.npz` (día índice 39 desde el 01/06):
- `on_hand` = saldo `on_hand[39]`.
- `in_transit` = Σ `ordered[0..39]` − Σ `received[0..39]` (pedidos emitidos hasta esa fecha menos recepciones hasta esa fecha; **no** el tránsito final del 31/07).
- `mean_28` = valor `pred_promedio_28` del SKU (media de 28 días conocida al origen 10/07).
- `forecast_14d` = Σ de los primeros 14 pronósticos (11/07…24/07) de `promedio_28` del SKU; `safety` = 7 × `mean_28`.
- `target` = `ceil(round(forecast_14d + safety, 9))`; `position` = `on_hand + in_transit`; `order_qty` = `max(0, target − position)` (empaque/mínimo 1, enteros).
- Costo: `unit_cost_assumed` (PEN, supuesto 65 % de la mediana de precio base ≤ 31/05) del vector `costo` del NPZ; `order_value_assumed = order_qty × unit_cost_assumed`.
- Documento: `{run_id, scenario_id, provenance:"SYNTHETIC_NOT_REAL_INVENTORY", snapshot_date, sku, almacen:"1", categoria, status:"ok"|"sin_snapshot", reason, on_hand, in_transit, position, mean_28, forecast_14d, safety, target, order_qty, horizon_days:14, lead_time_days:7, review_days:7, safety_days:7, unit_cost_assumed, currency:"PEN", unit:"unidad base", origin:"2026-07-10", forecast_from:"2026-07-11", forecast_to:"2026-07-24", model:"promedio_28", explanation_steps:[...]}`.
- Cobertura: el inventario simulado T07 solo existe para 3 347 SKU conocidos al 31/05. Los SKU adicionales del fold G4 se publican con `status="sin_snapshot"`, `reason="SIN_INVENTARIO_SIMULADO_AL_10_07: producto conocido despues del 31/05; no se supone stock cero"` y **sin** campos numéricos de stock/pedido (`null`).
- Los faltantes de ventas por stock real son desconocidos: la demanda proxy es venta observada; se explica en la pantalla.

## 6. Frontend (contrato de uso)

SPA Angular en `http://localhost:4200`, `/api` por proxy; sin `localStorage` para sesión; el guard de navegación consulta `GET /auth/me`; 401 → pantalla de acceso (mensaje «sesión vencida» si el código es `SESION_EXPIRADA`); 403 → mensaje de permiso; 503/red → «servicio no disponible, reintente». Modo demostración (mocks): solo con bandera explícita separada y rótulo visible; jamás como alternativa silenciosa cuando falla la API. Pantallas: acceso, resumen (ventas/calidad), importaciones, corridas, pronósticos (filtros SKU/categoría/cohorte/fechas, comparación promedio_28 vs RF vs cero, paginación), recomendaciones (cálculo paso a paso, cobertura, sin snapshot), comparación de políticas/backtests, sistema (salud). Todas muestran `run_label`, antigüedad y la etiqueta de inventario simulado donde aplique.

## 7. Pendiente explícito (T10)

Carga Excel por web, batch/timer, ejecución de corridas desde la aplicación y borrado/archivo de corridas. Hasta entonces la carga nueva sigue por CLI (`pipeline.data.importer`) y no hay botón que simule éxito.

## 8. Enmienda T08R (17/10/2026, correcciones R05 y R06)

**Señales exactas (R05).** La recomendación ya no usa la media de 10 cifras significativas del CSV T07. Se deriva de la historia aprobada ≤ origen: `sum_28` (texto exacto, p. ej. `"12"`), `days_28` (días útiles de la ventana de 28 días: ventas observadas y ceros observados; excluye días enmascarados y sin registros; no se asume 28), `mean_28_exact` (`"3/7"`), `target_raw_exact` (`"9"`, `"75/7"`) y `signals` (versión `exact-fraction-1`, ventana, fingerprint de entrenamiento y la media del CSV solo como **control de coherencia**, tolerancia relativa 1e-9). Objetivo = `ceil(14·media + 7·media)` en aritmética racional, sin redondeo previo ni epsilon; `mean_28`, `forecast_14d` y `safety` en coma flotante son solo de presentación. Los SKU `sin_snapshot` llevan estos campos en `null`.

**Identidad y versión.** La identidad de la corrida (`fingerprint`, `idempotency_key`, `run_id`) incluye `PUBLISHER_VERSION` (`t08r-1`), la referencia aprobada, el fingerprint de catálogo/fuentes y el fingerprint de las señales: mismos datos + código + versión ⇒ misma corrida al reintentar; corregir el algoritmo cambia la identidad. Antes de escribir se exige que el fingerprint de entrenamiento y las fuentes aprobadas coincidan con las del fold aceptado del manifiesto T07 y que `docs/T07_MANIFIESTO.json` y `docs/T07_METRICAS.json` coincidan con la referencia aprobada (commit `5790103…` y su contenido normalizado LF, fijados en `config/t08_publish.json`); recalcular el hash del archivo actual no cuenta como verificación.

**Corridas sustituidas.** `runs.status` admite `superseded` (con `superseded_by`, `superseded_at` y `quality_issue {code, message, superseded_by}`). Una corrida sustituida **no se borra ni se altera** (sus hijos quedan intactos), se puede consultar por `run_id` explícito (`/runs`, `/runs/{id}`, `/recommendations?run_id=…`, `/backtests`), pero no es la activa, y las respuestas de recomendaciones incluyen `validation_status` (`valid` | `superseded_precision_error`) por elemento y a nivel de respuesta, además de `run.status`/`run.quality_issue`. `GET /runs` lista `completed` y `superseded` (filtro `status` opcional). La interfaz debe mostrar el motivo (error de precisión en las recomendaciones) y no presentar sus pedidos como válidos.

**Proxy y límite de acceso (R06).** El servidor se inicia con `--no-proxy-headers`: el límite de intentos usa `request.client.host` y las cabeceras `X-Forwarded-For`/`Forwarded` enviadas por el cliente no deben alterarlo (Uvicorn las aplica por defecto desde loopback). Contrato para un despliegue futuro: si la API queda detrás de un proxy inverso, éste debe (1) ser el único origen de red que alcanza a la API, (2) sobrescribir —no añadir— `X-Forwarded-For` con la IP real del cliente, (3) configurarse con una lista explícita de proxies de confianza (`--forwarded-allow-ips <IP del proxy>`, nunca `*`), y (4) mantener `COOKIE_SECURE=true`. Hasta entonces `--no-proxy-headers`. Condición pendiente antes de exposición pública: el límite de intentos usa «contar y luego insertar» (no atómico) y la reserva de publicación usa un *lease* sin renovación; no son defectos demostrados en la CLI única/demostración local, pero hay que endurecerlos (operación atómica y prueba concurrente) en T10/T11.
