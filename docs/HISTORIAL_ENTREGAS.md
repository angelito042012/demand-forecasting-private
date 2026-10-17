# Historial de entregas anteriores

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
