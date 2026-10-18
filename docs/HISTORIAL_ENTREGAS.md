# Historial de entregas anteriores

## Revisión Codex10: T10R aceptado y encargo T12 (17/10/2026)

Entrega 6212f6a revisada; T10/T10R aceptados para demostración local, R07–R10 cerrados. Codex ejecutó 59 pruebas selectivas aprobadas, sin omitidas, 43,65 s, incluida cadena continua timer/worker/Mongo real con reloj acelerado; ruff afectado limpio. Auditoría solo lectura conserva ambas históricas y hash de congelación; staging abandonado conservado como failed; tamaño 459,39 MB. No se abrió agosto en esta revisión. Límites: CLI serial sin concurrencia web y scheduler con fuentes/config estables. Encargo posterior ETAPA_10_CLAUDE.md autoriza evaluación final T12 dedicada bajo congelación, con preparación sellada antes de leer el test, sin re-selección; paquete local antes de integración/capacidad/despliegue. Revisiones y pruebas detalladas en REVISION_CODEX_10.md.

Se conserva el registro anterior al reinicio de sesión del 17/10/2026. Para el estado actual leer ESTADO.md.

# Estado vigente y traspaso

## Estado vigente tras la segunda revisión independiente de Codex

Las correcciones R01–R03 se aceptan para los seis archivos canónicos auditados. Codex ejecutó la suite completa con datos reales: 46 pruebas aprobadas, 1 aviso, 59,57 segundos; análisis de estilo correcto. La base v1 conserva 86 877 ventas y 560 créditos. Ver REVISION_CODEX_02.md.

Siguiente entrega: ETAPA_02_CLAUDE.md — reconstrucción no destructiva en base v2 y T04 (perfil, diccionario, serie diaria), incluyendo R04: impedir que filas de una carga fallida o parcial se usen silenciosamente para entrenamiento o catálogo. Reproducción independiente: importación failed tras persistir una venta; load_training_data devolvió esa venta parcial. Debe cerrarse antes de crear datos listos para modelos.

T03 aceptado dentro del alcance de fuentes canónicas, con limitaciones de conflictos documentadas; T01 sigue parcial por Angular. Base v2 todavía no preparada en el entorno principal. No se han entrenado modelos. Las secciones siguientes conservan el historial de entregas y pueden contener estados anteriores ya sustituidos por este resumen.

Actualizado en la segunda revisión del 16/10/2026. Este estado sustituye los bloqueos históricos que ya se resolvieron.

## Confirmado

Inicio desde cero; no había aplicación previa. Git local inicializado en esta carpeta, sin remoto. Seis Excel en C:\Users\rogel\Documents\Datos, todos con 31 columnas de detalle. Marzo-julio cambiaron; agosto no cambió. Auditoría de 87 437 filas completada; ver AUDITORIA_DATOS.md. Ya no se necesita reexportar marzo-julio.

Stack conservado: Angular, FastAPI/Python, PyMongo/MongoDB y Azure. Python 3.12.14 local con dependencias instaladas, importaciones comprobadas y pip check correcto en la preparación anterior. Claude Code 2.1.302 autenticado; Node 24.19.0 y Git disponibles. Cinco agentes y cuatro skills preparados. No se volvió a comprobar conectividad ni servicios en esta revisión de datos.

## Pendiente

Decisiones funcionales cerradas en DECISIONES_DATOS.md: notas de crédito confirmadas, tres días excluidos, categoría según corte temporal e inventario sintético autorizado. Falta implementar estas reglas en el importador y conciliar ventas. Datos operativos reales siguen desconocidos, pero no bloquean la evaluación de escenarios autorizada. Cifras antiguas del DOCX no conciliadas: usar auditoría vigente sin inventar su origen.

Angular pendiente por el último fallo ECONNRESET del registro npm. Docker instalado, motor no accesible en la última prueba. MongoDB sin servidor conectado. Usuario sin acceso Azure/Atlas. Definir remoto GitHub, disponibilidad del equipo y hora oficial de entrega.

## Próximas tareas autorizadas

1. T01/T03: completar entorno local, API base e importador idempotente sobre el formato real.
2. T02A/T04: manifiesto, conciliación, reglas de negativos/unidades y serie diaria con fechas de disponibilidad.
3. T05/T06: baselines y modelos con validación solo en marzo-julio; reservar agosto.
4. T02B: escenario sintético inicial ya generado; integrarlo y documentar supuestos. T07 comparará referencia sintética contra ML, sin afirmar mejora real.
5. Continuar con interfaz, API, pruebas e integración según backlog.

## Estado del producto

Aplicación aún no implementada en este paquete. No hay modelo entrenado, métricas predictivas, impacto de inventario ni despliegue. Esta entrega actualiza preparación y diagnóstico, sin afirmar avances de construcción.

## Formato de actualización

Fecha y responsable; tarea; archivos; pruebas ejecutadas y resultado; evidencia/version; bloqueos; siguiente entrega.

## Escenario inicial generado

Ubicación: data/synthetic/reference_v1. 3758 SKU de entrenamiento, 14338 movimientos simulados y 6279 pedidos simulados; 141 SKU nuevos en agosto excluidos (568 unidades de ventas proxy). Parámetros derivados únicamente de marzo-julio o fijados como supuestos. Balance validado cada día para cada SKU y stock no negativo. Esto es un generador de escenario y datos de apoyo, no la aplicación completa ni un experimento ML realizado.

## Primera entrega de Claude: T01/T03 y preparación T04 (16/10/2026, integrador Claude Sonnet 5.5; revisión pendiente de Codex)

**Hecho y verificado**
- MongoDB 8.3.8 local en contenedor Docker `df-mongo-dev` (imagen mongo:latest ya presente, digest sha256:5211c511…), enlazado solo a 127.0.0.1:27017, volumen `df_mongo_dev`, sin autenticación (solo desarrollo). No se tocó el contenedor `mi-mongodb` preexistente. Docker Desktop se inició manualmente.
- API: `backend/app/main.py`, `config.py`; `GET /api/v1/health` (sin URI ni datos; CORS restringido a ALLOWED_ORIGINS). Comprobado con uvicorn real: `status ok, database ok`. Sin auth ni más rutas (T08).
- Importador (delegado a data-engineer, revisado y reejecutado por el integrador): `pipeline/data/{importer,calendar,catalog,reconcile}.py`. Ventas, notas de crédito (TIPO_DOC=7) y rechazos en colecciones separadas; `linea_id` hash con ocurrencia k (sin deduplicar por ID_PEDIDO ni por valores); importes Decimal128; sin datos de clientes/vendedor/ubicación; recarga del mismo sha256 es no-op registrado; índices únicos; invariante filas = ventas + créditos + rechazos.
- Calendario: máscara EXCLUDED_DATES (2026-04-03, 04-12, 06-07) sin ceros ni eliminación; corte de entrenamiento 2026-07-31; catálogo de categoría por corte (SKU 16140041 → MAQUILLAJE PARA ROSTRO con datos reales, 3758 SKU).
- `pytest.ini` (pythonpath, markers mongo/realdata); paquetes `backend/`, `pipeline/`, `tests/`.

**Pruebas ejecutadas (por el integrador)**
- `RUN_REALDATA=1 pytest -q`: 19 passed, 1 warning (deprecación httpx/starlette), ~24 s. Incluye 3 de API, 15 de importador con fixtures sintéticas y 1 con los seis Excel reales en base temporal. Sin RUN_REALDATA el de datos reales se omite.
- `ruff check pipeline tests backend`: limpio. `scripts/generate_synthetic_inventory.py` (preexistente) tiene 9 avisos de estilo ruff, no tocado.
- Carga real en `demand_forecasting_dev` vía CLI y recarga: segunda corrida con insertadas=0 en los seis archivos. Totales en base: 86 877 ventas, 560 notas de crédito, 0 rechazos, 87 437 filas = coincide con AUDITORIA_DATOS.md.
- sha256 de los seis Excel idénticos antes y después (comparado por el integrador).

**Conteos por mes (ventas / créditos / rechazos; S/ ventas, S/ créditos, neto)**: marzo 14456/89/0; 426 456,21; −3 128,00; 423 328,21 · abril 13907/72/0; 429 609,99; −2 927,50; 426 682,49 · mayo 15380/78/0; 500 621,72; −2 769,38; 497 852,34 · junio 12510/81/0; 390 855,08; −9 680,60; 381 174,48 · julio 15678/112/0; 453 143,28; −4 548,76; 448 594,52 · agosto 14946/128/0; 422 736,88; −3 799,90; 418 936,98. Importes de reconcile() reportados por el agente; solo los conteos y totales de la base fueron recomprobados por el integrador. Rechazos 0: los datos cumplen todas las reglas; las reglas de rechazo están probadas solo con fixtures sintéticas.

**Bloqueos / pendientes**
- Angular NO instalado: `registry.npmjs.org` acepta TCP en 443 pero HTTPS agota el tiempo (npm ping y curl, 15–20 s). `scripts/prepare-frontend.ps1` no se ejecutó. No hay `frontend/`. Requiere red/proxy que funcione.
- La base contiene agosto (por mes/fecha). Los consumidores de entrenamiento deben filtrar `fecha <= 2026-07-31`; aún no hay un filtro forzado en código.
- Idempotencia con archivos solapados de otro sha256 se prueba solo con fixtures; límite documentado: asume que se repiten las primeras k líneas idénticas.
- Conciliación contra un reporte de control de la MYPE (T02A) sigue pendiente; no se integró data/synthetic (T02B). Sin autenticación, sin CI, sin remoto Git, sin commits (no solicitados).
- Marcador `realdata` registrado en pytest.ini por el integrador.

**No hecho por diseño**: ningún modelo entrenado, ninguna métrica predictiva, ningún uso de agosto para selección.

**Siguiente tarea vigente tras la revisión de Codex**: ejecutar SIGUIENTE_CLAUDE.md y corregir R01–R03 antes de completar T03 o avanzar al entrenamiento. T04 queda después de esta corrección; Angular continúa pendiente de conectividad.

## Revisión independiente de Codex de la primera entrega

Suite existente reproducida: 19 pruebas aprobadas, 1 aviso. Conteos e importes de ventas/créditos por mes contrastados directamente contra los seis Excel y coincidentes con la base actual. Las comprobaciones adicionales reprodujeron R01 (errores de escritura ocultados), R02 (identidad de créditos dependiente del nombre/fila) y R03 (conciliación incorrecta con fuentes solapadas). Ver REVISION_CODEX_01.md para reproducciones y criterios de corrección.

T03 queda pendiente de correcciones; T01 sigue parcial por Angular. Siguiente encargo: SIGUIENTE_CLAUDE.md. No iniciar entrenamiento. Los Excel y la base del proyecto no fueron modificados en la revisión; las bases de reproducción fueron aisladas y eliminadas al terminar.

## Segunda entrega: correcciones R01–R03 y barrera de corte temporal (16/10/2026, integrador Claude Sonnet 5.5; segunda revisión de Codex pendiente)

T03 **no se marca completo**: queda a la espera de la segunda revisión de Codex. No se entrenó ningún modelo ni se calculó ninguna métrica.

**Correcciones** (`pipeline/data/importer.py`, `reconcile.py`; diseño en `docs/ESTRATEGIA_CLAVES.md`)
- **R01**: `_run_bulk` solo recupera la clave duplicada 11000 (reintenta esa operación y verifica); validación (121), write concern y errores sin detalle lanzan `ImportWriteError` y dejan la carga `failed`. Cada lote se verifica contando documentos persistidos. Se conserva la recuperación tras escritura parcial.
- **R02**: `linea_id` v2 sin nombre de archivo ni fila (documento, almacén/SKU, cantidades e importes normalizados, ocurrencia `k`); la procedencia pasa a `sources[]` con todas las fuentes reconocidas. Documento ya cargado por otra fuente con líneas nuevas → conflicto en `import_conflicts` (no se inserta ni se sobrescribe; estado `completed_with_conflicts`, salida CLI 2). Una nota distinta en el mismo nombre y fila ya no se pierde; una reexportación renombrada o reordenada ya no se duplica.
- **R03**: conciliación en dos niveles: por importación (leídas = aceptadas + rechazadas; aceptadas = insertadas + existentes + conflictos; persistencia verificada vía `sources`) y conjunto lógico único (entre el máximo y la suma de líneas útiles). Se eliminó `cuadra_filas`. Las cargas fallidas se listan aparte (`cargas_no_completadas`) y no se presentan como conciliadas.
- **Esquema**: `schema_version=2`. El importador rechaza escribir sobre una base con documentos de esquema anterior (`IncompatibleSchemaError`). Por eso **`demand_forecasting_dev` (claves v1) no se migró ni se tocó**: 86 877 ventas, 560 créditos, 0 rechazos, `schema_version` 1 verificado al final. Migración propuesta (base nueva desde los Excel, comparar, cambiar solo con aprobación) en ESTRATEGIA_CLAVES.md; sin ejecutar.
- **Barrera de entrenamiento**: `pipeline/data/training_access.py` (`load_training_data`, `load_fold`, `load_final_test_sales`). Rechaza cortes > 2026-07-31 (`TrainingCutoffError`), filtra por fecha ≤ corte, construye el catálogo con el mismo corte, aplica la máscara de los tres días (calendario sin comprimir, sin ceros), excluye créditos del objetivo y da un `fingerprint`. Agosto solo con `frozen_selection_confirmed=True`. Es una convención verificada por pruebas: una consulta directa a Mongo puede saltarla (documentado).
- Healthcheck: la prueba de éxito ahora exige `status ok` (cliente simulado) y otra con Mongo real; se mantiene la de base no disponible.

**Pruebas ejecutadas por el integrador**
- Suite completa con `RUN_REALDATA=1`: **46 passed**, 1 warning (deprecación httpx/starlette), 50,5 s. `ruff check backend pipeline tests` limpio.
- Nuevas: 17 de regresión R01–R03 (`test_review01_regression.py`: error 121 real con validador de colección, write concern, lote mixto 11000+121, duplicado concurrente recuperado, duplicado persistente, escrituras perdidas, nota reexportada/renombrada/reordenada, nota distinta en mismo nombre y fila, documento corregido→conflicto y recarga, líneas idénticas legítimas, solapamiento, representación numérica y hora de fecha, esquema antiguo, conciliación tras reexportación, tras fallo+reintento y con conflictos), 8 de la barrera (`test_training_access.py`) y 1 de datos reales ampliada.
- Verificación de que las pruebas detectan el defecto: se revirtió temporalmente la distinción de errores (fallaron 2 de R01) y la detección de conflictos (fallaron 2 de R02/R03); código restaurado y suite en verde.
- Datos reales en base temporal creada desde cero, cargada y recargada (el test las elimina): 0 conflictos, 0 rechazos, `cuadra_importaciones` y `cuadra_conjunto_logico` verdaderos en los seis meses y sumas de ventas/créditos por mes iguales a las del reporte anterior (marzo 426 456,21/−3 128,00 … agosto 422 736,88/−3 799,90); `compare_with_audit` vacío. Barrera con datos reales: corte 2026-07-31 devuelve 71 931 ventas (marzo–julio, sin agosto), SKU 16140041 → MAQUILLAJE PARA ROSTRO, tres días enmascarados; corte 2026-08-31 rechazado.
- No quedan bases `df_test_*`. Los seis Excel conservan los sha256 registrados en la entrega anterior (comprobado al final).

**Diagnóstico acotado de npm (T01 sigue parcial)**: registro configurado `https://registry.npmjs.org/`, sin proxy en npm ni en el sistema, `strict-ssl=true` (no se tocó). DNS resuelve (104.16.8–10.34). `curl` a npm agota 15 s sin completar conexión; el mismo `curl` a `pypi.org` responde 200 (TLS 0,56 s), de modo que no es una falla general de HTTPS. Causa no determinada (posible filtrado/ruta hacia ese destino). No se desactivó TLS ni se usaron espejos. Angular sigue sin instalarse y no hay `frontend/`.

**Pendientes y límites**
- Resolución manual de conflictos (procedimiento no diseñado); una línea ausente en un archivo reemplazado no se detecta.
- Migración de `demand_forecasting_dev` a v2 sin ejecutar; ninguna colección derivada depende aún de ella.
- Sin conciliación contra reporte contable de la MYPE (T02A), sin integración de sintéticos, sin autenticación, sin commits.
- El realdata test usa los Excel en lectura y una base temporal; el aviso de deprecación persiste.

**Siguiente**: segunda revisión de Codex. Tras su aprobación, T04 (perfil, diccionario, serie diaria sobre `load_training_data`) y, con aprobación, la reconstrucción de la base v2.


## Entrega 17/10/2026 (Claude): R04, base v2 y T04 (pendiente de revisión de Codex)

- Código: `pipeline/data/sources.py` (nuevo), `training_access.py`, `catalog.py`, `reconcile.py`, `daily_series.py` (nuevo), `scripts/compare_v1_v2.py`, `scripts/build_t04.py`, `backend/app/config.py`, `.env.example`.
- Pruebas nuevas: `test_source_approval.py` (10: carga parcial, reintento completo una sola vez, conflicto abierto, procedencia inválida, meses ausentes, base vacía, invariancia ante carga fallida posterior al corte, agosto), `test_daily_series.py` (5). Suite completa con RUN_REALDATA=1: 65 aprobadas (tras revisión), 0 omitidas, 1 aviso.
- v2: 86 877 ventas / 560 créditos; comparación con v1 por mes: conteos, importes y líneas normalizadas idénticos; 0 conflictos, 0 rechazos, 0 duplicados. Recarga: no-op por sha256.
- T04: 459 375 filas SKU-día, 5 441 categoría-día; fingerprint de entrenamiento a07df648eeb5...; hashes de contenido estables en dos corridas.
- Cambio de API interna: `load_*` exigen fuentes aprobadas y por defecto los meses 2026-03..mes del corte; las pruebas sintéticas de un mes pasan `required_months` explícito.


## Traspaso de Claude previo a revisión T04

# Traspaso entre ejecutores

## Registro actual

- Ejecutor: Claude Code (Sonnet 5.5). Fecha: 17/10/2026, America/Lima. Tarea: ETAPA_02_CLAUDE.md (R04, base v2, T04).
- Punto de retoma encontrado: sin trabajador anterior activo; Mongo (df-mongo-dev) arriba; solo existía `demand_forecasting_dev` (v1: 86 877 ventas, 560 créditos); v2, R04 y T04 no existían en código ni datos; Git sin commits.
- Último paso terminado: R04 + v2 + T04 implementados, probados y comprometidos. Suite completa con `RUN_REALDATA=1`: 65 aprobadas, 0 omitidas, 1 aviso, 69 s. `ruff` limpio (backend, pipeline, tests, scripts/build_t04.py, scripts/compare_v1_v2.py).
- Paso en curso: ninguno de escritura. Revisión de solo lectura por quality-reviewer hecha; M1 (persistencia declarada vs real), M2 (una fuente por mes), M3 (día sin filas = SIN_REGISTROS_DIA, no cero) y M5 (texto del perfil) corregidos con pruebas. Quedan sin tratar, menores: catálogo ignora start, catálogo no excluye la máscara, unidad_base fuera del fingerprint, céntimos por truncado (importes con ≤2 decimales no verificado), bloqueo permanente sin ruta de remediación tras carga fallida de archivo reemplazado.
- Checkpoints Git locales: 8a34814 (estado recuperado, parcial), 425d663 (R04 + comparador + config v2), 05510d1 (T04). Un commit final de documentación sigue a este registro.
- Base activa: `demand_forecasting_v2` (config por defecto en `backend/app/config.py` y `.env.example`; el `.env` local no se leyó ni se imprimió: la configuración efectiva resuelta es v2). v1 conservada intacta.
- Revertir a v1: en `backend/app/config.py` (y `.env.example`) volver `mongodb_database` a `demand_forecasting_dev`, o fijar `MONGODB_DATABASE=demand_forecasting_dev` en el entorno. Nota: v1 tiene claves de esquema 1 y no pasa `check_schema` del importador ni la aprobación de fuentes (no tiene `sources`); sirve solo para consulta/comparación.
- Procesos: sin servidores propios en segundo plano. df-mongo-dev se dejó activo. No se tocaron otros contenedores.
- Evidencia (no versionada con datos comerciales): `artifacts/private/compare_v1_v2.json` (comparación y recarga), `artifacts/private/load_v2.log`, `artifacts/private/t04/` (series). Versionada: `docs/T04_*`.
- Bloqueos: ninguno de datos. Angular: `npm ping` al registro hoy responde (661 ms); no se intentó instalar; TLS sin tocar.
- Pendiente de revisión de Codex: R04 (`pipeline/data/sources.py`, `training_access.py`, `catalog.py`), v2 (comparación y configuración), T04 (`pipeline/data/daily_series.py`, `scripts/build_t04.py`, perfil/diccionario/firma).
- Siguiente acción exacta: tras la revisión de Codex, emitir el encargo T05 (baselines, folds sin fuga). No entrenar ni usar agosto antes.

## Reproducir

```
.venv\Scripts\python.exe -m scripts.compare_v1_v2 --reload C:\Users\rogel\Documents\Datos --out artifacts\private\compare_v1_v2.json
.venv\Scripts\python.exe -m scripts.build_t04
$env:RUN_REALDATA="1"; .venv\Scripts\python.exe -m pytest -q
```

## Actualización obligatoria durante el trabajo

Reemplazar el registro actual con hechos comprobados al cambiar de etapa o ejecutor. Conservar detalles anteriores relevantes en HISTORIAL_ENTREGAS.md.

Campos mínimos: ejecutor; fecha; tarea; último paso terminado; paso en curso; archivos; commit/checkpoint; comandos y resultado; evidencia; base activa; procesos útiles; bloqueos; siguiente acción exacta; pendiente de revisión.

No escribir claves, tokens o URI con credenciales. Si una prueba no se ejecutó o un proceso dejó de ser observable, indicarlo.

## Entrega 17/10/2026 (Claude): T05 baselines y validación temporal (pendiente de revisión de Codex)

- Código: `pipeline/forecast/{baselines,metrics,t05}.py`, `scripts/run_t05.py`, `config/t05_config.json`; detalles menores de datos en `catalog.py`, `training_access.py`, `daily_series.py`, `build_t04.py`.
- Protocolo congelado en d763bed antes de la primera ejecución; sin enmiendas. Cinco folds, cuatro baselines, SKU y categoría.
- Pruebas nuevas: 14 en tests/forecast (baselines, métricas ponderadas, cohortes, máscara, fallback, ausencia de fuga, repetición) y 4 de datos. Suite completa: 83 aprobadas.
- Resultado: SKU diario, ningún baseline vence al cero; categoría, los tres lo vencen. Referencia por regla previa: ultimo_dia. Ver T05_RESULTADOS.md.
- Angular 21.2.27 generado y compilado en frontend/ (sin pantallas ni ng test).


## Traspaso de T05 previo a revisión Codex

# Traspaso vigente

- Ejecutor: Claude Code (Sonnet 5.5), 17/10/2026, America/Lima. Tarea: T05 (ETAPA_03_CLAUDE.md), tras la aceptación de R04/v2/T04 por Codex (REVISION_CODEX_03.md).
- Último paso terminado: T05 ejecutado y documentado; Angular base generada y compilada. Nada en curso; sin procesos propios en segundo plano (df-mongo-dev sigue activo).
- Commits locales: d763bed (protocolo y config congelados ANTES de evaluar), 0ce411d (código y pruebas), commit de `scripts/run_t05.py` con lectura automática (el manifiesto registra el HEAD de la ejecución) y commit final de entrega (HEAD, ver `git log`).
- Pruebas: suite completa `RUN_REALDATA=1`: 83 aprobadas, 0 omitidas, 1 aviso, 71 s (log: `artifacts/private/t05/pytest_full.log`). `ruff` limpio. Repetición de la evaluación T05: predicciones y métricas idénticas. `ng test` de Angular no ejecutado.
- Evidencia versionada: `docs/T05_PROTOCOLO.md`, `config/t05_config.json`, `docs/T05_RESULTADOS.md`, `docs/T05_METRICAS.json`, `docs/T05_MANIFIESTO.json` (hashes de config, código, datos, fuentes y versiones), `docs/REMEDIACION_FUENTES.md`. Privada (fuera de Git): `artifacts/private/t05/predicciones.csv.gz`.
- Resultado resumido: en SKU diario ningún baseline supera al control cero (WAPE 1,43 / 1,63 / 1,54 frente a 1,00); en categoría los tres lo superan (WAPE ≈ 0,40–0,44). Referencia T06 por regla previa: `ultimo_dia`, con esa salvedad. Detalle en T05_RESULTADOS.md.
- Base activa: `demand_forecasting_v2`; v1 conservada (solo consulta). Fingerprint T04 actualizado (incluye unidad_base); hashes de contenido de las series sin cambio.
- Angular: `frontend/` con Angular CLI 21.2.27, `npm run build` correcto, `package-lock.json` conservado; sin pantallas.
- Bloqueos: ninguno.
- Siguiente acción exacta: revisión de Codex de T05; luego T06 (ML) comparando contra `ultimo_dia`, `promedio_28` y el control cero; agosto sigue reservado hasta congelar la selección.
- Reproducir: `.venv\Scripts\python.exe -m scripts.run_t05` y `$env:RUN_REALDATA="1"; .venv\Scripts\python.exe -m pytest -q`.

Campos mínimos al actualizar: ejecutor; fecha; tarea; último paso; paso en curso; archivos; commit; comandos y resultado; evidencia; base activa; procesos; bloqueos; siguiente acción; pendiente de revisión. No escribir claves ni URI con credenciales. Una prueba no ejecutada se indica como tal.

## Entrega 17/10/2026 (Claude): T06 ML frente a baselines (pendiente de revision de Codex)

- Protocolo 286017d, enmienda 1 (00e4e64). Codigo en pipeline/forecast/{features,models,t06}.py y scripts/run_t06.py; 11 pruebas nuevas de features/modelos/integracion (suite 94).
- SKU: ningun ML cumple la regla; categoria: RF cumple por margen minimo. Ver docs/T06_RESULTADOS.md.
- Frontend: navegacion y estados con mocks identificados; build y 15 pruebas.


## Traspaso T06 previo a revisión Codex 05

# Traspaso vigente

- Ejecutor: Claude Code (Sonnet 5.5), 17/10/2026. Tarea: T06 (ETAPA_04_CLAUDE.md), tras la aprobación de T05 por Codex (REVISION_CODEX_04.md).
- Último paso terminado: T06 ejecutado y documentado; frente web acotado entregado. Nada en curso; sin procesos propios en segundo plano (df-mongo-dev activo).
- Commits: 286017d (protocolo+config ANTES de evaluar), 2c52c73 (código y pruebas), 00e4e64 (enmienda 1: tolerancia numérica en la repetición), y el commit final de entrega (HEAD, ver `git log`; resultados y estado).
- Pruebas: suite completa `RUN_REALDATA=1`: 94 aprobadas, 0 omitidas, 1 aviso, 74 s (`artifacts/private/t06/pytest_full.log`). Angular: `npm run build` y `npm test` (15 aprobadas). `ruff` limpio. Repetición de F1 equivalente (dif. máx. 1,1e-13); baselines idénticos a T05.
- Evidencia versionada: `docs/T06_PROTOCOLO.md`, `config/t06_config.json`, `docs/T06_RESULTADOS.md`, `T06_METRICAS.json`, `T06_MANIFIESTO.json`. Privada: `artifacts/private/t06/` (predicciones, modelos joblib), `artifacts/private/t06_run.log`.
- Resultado: SKU (criterio semanal) ningún ML supera la regla; propuesta provisional `promedio_28`. Categoría: Random Forest cumple la regla diaria por margen mínimo (2,07 %, 3/5 folds) pero es peor que los baselines en el bloque semanal. Desarrollo, no prueba final; sin mejora de inventario.
- Base activa: `demand_forecasting_v2`. Agosto no leído.
- Bloqueos: ninguno. Pendientes: sin precio; horizonte >7 días no evaluado (T07); API real/autenticación; Angular sin probar en navegador.
- Siguiente acción exacta: revisión de Codex de T06; luego T07 (simulación con horizonte lead time + revisión) y decisión sobre congelar selección y abrir agosto.
- Reproducir: `.venv\Scripts\python.exe -m scripts.run_t06` (≈7 min) y `$env:RUN_REALDATA="1"; .venv\Scripts\python.exe -m pytest -q`.


## Revisión Codex 05 y encargo T07 (17/10/2026)

T06 aceptado como experimento de desarrollo al commit 3b11fbd. Once pruebas selectivas aprobadas; 36 grupos de métricas recalculados y hashes comprobados. Sin repetición del entrenamiento completo ni suite integral. Ver REVISION_CODEX_05.md. Siguiente: ETAPA_05_CLAUDE.md, horizontes 10/14/21 y simulación de desarrollo; agosto reservado.

## Entrega 17/10/2026 (Claude): T07 horizontes y simulacion (pendiente de revision de Codex)

- Protocolo 325da2f sin enmiendas. Codigo: pipeline/sim/engine.py, pipeline/forecast/t07.py, features/models (inferencia coherente), scripts/run_t07.py. Suite 117 + 16 posteriores.
- RF categoria distribuido no cumple la regla provisional; promedio_28 es la referencia provisional. Simulacion con 9 escenarios y 3 politicas; ventaja de servicio del RF no concluyente (mas stock y compras).


## Traspaso T07 previo a revisión Codex 06

# Traspaso vigente

- Ejecutor: Claude Code (Sonnet 5.5), 17/10/2026. Tarea: T07 (ETAPA_05_CLAUDE.md). Estado: terminado y entregado a revisión de Codex; nada en curso; sin procesos propios en segundo plano (df-mongo-dev activo).
- Commits: 9419d2f (inferencia coherente), 325da2f (protocolo/config T07 antes de resultados), e3c38c3 (motor, pronóstico, pruebas), siguiente (cobertura/cohortes/lectura tras revisión independiente) y commit final de entrega (HEAD; `git log`). El manifiesto registra el commit de la ejecución.
- Pruebas: suite completa RUN_REALDATA=1 117 aprobadas, 0 omitidas, 346 s (antes de ajustes solo de reporte); después 16 pruebas (tests/sim + test_t07_functions) aprobadas y ejecución completa de scripts.run_t07 con repetición idéntica. Logs: `artifacts/private/t07/pytest_full.log`, `artifacts/private/t07_run.log`, `artifacts/private/t07_tests.log`. Angular no tocado en T07.
- Evidencia versionada: `docs/T07_PROTOCOLO.md`, `config/t07_config.json`, `docs/T07_RESULTADOS.md`, `T07_METRICAS.json`, `T07_MANIFIESTO.json`. Privada: `artifacts/private/t07/` (modelos, predicciones por fold, series de simulación).
- Resultado: RF distribuido no cumple la regla (WAPE H14 0,929 frente a 0,873 de promedio_28; 0/4 folds); promedio_28 supera al cero en acumulados. Simulación L=7,S=7: fill rate 0,741 / 0,797 / 0,809 (referencia fija / promedio_28 / RF) con más stock y compras en ese orden; nueve escenarios en T07_RESULTADOS.md. Etiqueta: inventario simulado con supuestos; no es inventario real.
- Base activa: demand_forecasting_v2. Agosto no consultado (ni ventas ni movimientos sintéticos).
- Bloqueos: ninguno. Pendientes: API funcional/autenticación, conexión de pantallas, publicación (sin cuenta/presupuesto), congelación de selección y prueba final de agosto tras revisión de Codex.
- Siguiente acción exacta: revisión de Codex de T07; luego integración/API y congelación de selección antes de abrir agosto.
- Reproducir: `.venv\Scripts\python.exe -m scripts.run_t07` (≈3 min) y `$env:RUN_REALDATA="1"; .venv\Scripts\python.exe -m pytest -q`.


## Revisión Codex 06 (17/10/2026)

T07 aceptado al commit 5790103. Codex ejecutó 22 pruebas selectivas, comprobó hashes (13 modelos y dos archivos), recalculó 160 grupos SKU y saldos diarios/métricas totales en las 27 combinaciones. Sin reentrenar ni consultar base real. Ver REVISION_CODEX_06.md. Siguiente: ETAPA_06_CLAUDE.md, API/autenticación/persistencia y lectura web con corrida histórica al 10/07; congelación documentada sin abrir agosto.

## Entrega 17/10/2026 (Claude): T08 + lectura integrada T09 (pendiente de revision de Codex)

- Contrato T08, seleccion congelada (sin ejecutar), auth por cookie HttpOnly, publicador versionado, rutas de lectura, frontend conectado. Suite 226, frontend 42, E2E navegador 24/24. Detalle: docs/T08_REPORTE.md.


## Traspaso T08 previo a revisión Codex07

# Traspaso vigente

- Ejecutor: Claude Code, 17/10/2026. Tarea: T08 + lectura integrada T09 (ETAPA_06_CLAUDE.md), terminada y entregada a revisión de Codex. Nada en curso.
- Commits: d59703b (motor + contrato), c49160c (selección congelada), 03cf93c (auth), a442983 (frontend), ff8b030 (publicador/rutas), y el commit final de entrega (HEAD; ver `git log`).
- Pruebas: suite integral RUN_REALDATA=1 → 226 aprobadas, 0 omitidas, 509 s (`artifacts/private/t08/pytest_full.log`); frontend 42 aprobadas + build; E2E navegador real 24/24 (`artifacts/private/t08/e2e_resultado.json`, capturas en `artifacts/private/t08/screens/`, privadas). Reporte: `docs/T08_REPORTE.md`.
- Estado de la base real `demand_forecasting_v2`: ventas importadas + colecciones nuevas `runs`, `run_pointer`, `forecasts`, `recommendations`, `backtests`, `users` (demo_admin, demo_lector), `sessions`, `login_attempts`. Corrida activa `hist-20260710-52b01cd999dd`. Credenciales locales de demostración solo en `artifacts/private/t08/e2e_credentials.json` (no versionado, no impreso). v1 y Excel intactos.
- Procesos: al cerrar se detienen los propios con `scripts/stop-local.ps1`; para usar la app: `scripts/start-local.ps1` (ver `docs/GUIA_LOCAL.md`). df-mongo-dev sigue activo y no se tocó.
- Congelación: `docs/SELECCION_CONGELADA.md` + `config/seleccion_congelada.json`: preparada, NO ejecutada; agosto y reference_v1 sin consultar.
- Bloqueos: ninguno. Pendientes: T10 (carga web/batch), T11 (despliegue HTTPS, respaldo/restauración; requiere accesos de nube listados en la guía), T12 (ejecución final bajo congelación revisada), aceptación humana e informe.
- Siguiente acción exacta: revisión de Codex de T08; luego decidir T10 y la autorización de la ejecución final.


## Revisión Codex07: R05–R06 abiertos

118 pruebas seleccionadas aprobadas, pero auditoría independiente detectó225objetivos/118pedidos inflados por CSV de precisión reducida. Middleware Uvicorn reproduce IP manipulable por XFF. Catálogo/fuentes y métricas T07 coinciden hoy con referencias aprobadas. Ver REVISION_CODEX_07.md. T08 parcialmente verificado, no aceptado completo. Siguiente ETAPA_07_CLAUDE.md: precisión/publicación nueva, confianza de proxy y presentación acotada. Agosto reservado y T10 no iniciado.

## Entrega 17/10/2026 (Claude): correccion T08R (pendiente de revision de Codex)

- R05: senales exactas y corrida hist-20260710-4ea348836e35 (anterior superseded); auditoria independiente 0 diferencias, 582/2655. R06: --no-proxy-headers y prueba de cadena real. Presentacion legible. pytest 254, frontend 79, E2E 16/16. Detalle: docs/T08R_REPORTE.md.


## Traspaso T08R antes de revisión Codex08

# Traspaso vigente

- Ejecutor: Claude Code, 17/10/2026. Tarea: corrección T08R (ETAPA_07_CLAUDE.md; R05, R06, presentación) terminada y entregada a revisión de Codex. Nada en curso; procesos propios detenidos al cerrar.
- Commits: ac8ee8b (señales exactas R05, identidad t08r-1, anclaje, R06), 7fcc99c (auditoría independiente), e2cae1f (presentación) y el commit final de ajuste de contrato de UI + documentación (HEAD, ver `git log`).
- Corridas en demand_forecasting_v2: **activa** `hist-20260710-4ea348836e35` (válida: 582 pedidos/2 655 uds.; auditoría independiente 0 diferencias); `hist-20260710-52b01cd999dd` **superseded** (R05) conservada. Usuarios locales demo_admin/demo_lector (credenciales solo en `artifacts/private/t08/e2e_credentials.json`, no versionado).
- Pruebas: pytest 254 aprobadas, 3 omitidas (RUN_REALDATA, no repiten T07); frontend 79 + build; E2E Chrome T08R 16/16. Logs/capturas privados en `artifacts/private/t08r/`. Reporte: `docs/T08R_REPORTE.md`; auditoría: `docs/T08R_AUDITORIA.json`.
- Pendientes declarados: límite de login no atómico y lease de publicación sin fencing (antes de exposición pública/T10/T11); T10 carga web/batch; T11 despliegue/HTTPS/respaldo (requiere accesos de nube de `docs/GUIA_LOCAL.md`); T12 ejecución final bajo `SELECCION_CONGELADA` (no ejecutada; agosto sin abrir); aceptación humana.
- Siguiente acción exacta: revisión de Codex de T08R; después T10 y la autorización de la ejecución final en el orden que decida.
- Iniciar para demostrar: `powershell -File scripts/start-local.ps1` (API con `--no-proxy-headers`), detener con `scripts/stop-local.ps1`.


## Revisión Codex08 y encargo T10

T08R aceptado al commit 80117c0 para alcance local. R05/R06 cerrados: 31 pruebas selectivas aprobadas y auditoría de 3347 recomendaciones sin diferencias (582 positivas/2655 unidades); anterior sustituida conservada. Dos diagnósticos de estilo menores en script de auditoría pasan a limpieza T10. Sin repetir entrenamiento o navegador. Siguiente ETAPA_08_CLAUDE.md: concurrencia, carga web, cola/worker, generación baseline y timer local. Agosto reservado y nube sin gasto autorizado.


## T10 (17/10/2026): carga web, cola durable, generación y temporizador

Entregado para revisión: garantías de concurrencia, API de carga/corridas/trabajos, worker, generación `promedio_28`, temporizador y frontend admin. Pruebas: pytest 376 aprobadas/6 omitidas, vitest 106, E2E Chrome 16/16, realdata 3/3. Detalle y límites en `docs/T10_REPORTE.md`. Sin agosto, sin cambio de selección congelada, sin despliegue.

## Revisión Codex09 y encargo T10R (17/10/2026)

T10/9596d26 no aceptado todavía. 119 pruebas selectivas aprobadas y cuatro defectos adicionales reproducidos con Mongo real aislado: R07 limpieza/promoción (P1), R08 takeover tras renovación, R09 dos fuentes mensuales concurrentes y R10 tick incompleto sin recuperación (P2). Revisión docs/REVISION_CODEX_09.md; encargo correctivo ETAPA_09_CLAUDE.md. Sin código productivo modificado ni base principal alterada. Auditoría solo lectura confirma histórica activa e hijos intactos, hash congelado correcto y tamaño459,39MB tras T10. Decisión: generadas de desarrollo no activan puntero por defecto; evitar refactorización ajena. Azure estudiantes/Atlas Free ya creados según capturas, conexión/despliegue/capacidad pendientes y sin presupuesto de bolsillo. No se abrió agosto ni se inició T11/T12.


## T10R (17/10/2026): cierre de R07–R10

Entregado para revisión: limpieza de publicaciones con reserva CAS (R07), toma de control que respeta renovaciones (R08), reserva durable de una fuente por mes con valla de escritura (R09) y recuperación de ranuras del temporizador con prueba de `--loop` real (R10). Pruebas: 32 regresiones nuevas (fallaban antes), pytest completo 408 aprobadas/6 omitidas. Detalle y límites en `docs/T10R_REPORTE.md`. Sin agosto, sin cambio de selección congelada, sin despliegue.


## T12 (17/10/2026): evaluación final de agosto bajo selección congelada

Ejecutada una vez por fases: verificación de la congelación, preparación y sello de las predicciones ≤31/07 (86325a7), lectura de agosto por la ruta dedicada, evaluación predictiva fija (01–21/08), simulación secuencial (27 combinaciones), auditoría y reporte. Hallazgo primario: WAPE H14 SKU primaria promedio_28 0,7810 frente a RF 0,7910 y cero 1,0000; sin re-selección. 16 pruebas sintéticas nuevas; pytest 424 aprobadas/6 omitidas. Detalle en `docs/T12_RESULTADOS.md`. Sin despliegue.


## Revisión Codex11: resultados T12 validados y preparación T11A

17/10, entrega3f40176. Codex16pruebas sintéticas aprobadas sin omitidas,69,49s; ruff limpio. Auditoría propia recalcula WAPE H14 y reconstruye reales desde CSV mínimo, verifica9hashes/sello previo y27balances sin repetir evaluación real. R11 administrativo: audit/reporte no actualizan fases, estado completa=false; cerrar primero en ETAPA_11_CLAUDE.md sin repetir cálculos. Método promedio_28 permanece; no mejora RF ni impacto real demostrado. Siguiente T11A: integración final, contenedores, base nueva/capacidad, copia-restauración y plan de costo/accesos antes de despliegue. No cambios a artefactos finales ni DB original en esta revisión; evidencia en codex_review11_* privado.


## T11A (17/10/2026): preparación local del despliegue

R11 cerrado (siete fases, reconciliación sin recomputar). Paquete final T12 integrado localmente (publicador, API, UI; tres tipos de corrida separados). Base de publicación `demand_forecasting_pub` con capacidad medida (213,90 MB, 41,8 % de 512 MB), copia/restauración verificadas, contenedores con smoke 29/29 y plan Azure/Atlas con costos. pytest 511 aprobadas/7 omitidas, vitest 127, E2E Chrome 20/20. Sin recursos externos, sin transferencia de datos y sin despliegue. Detalle en `docs/T11A_REPORTE.md`.
