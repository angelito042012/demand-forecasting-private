# T11 Contrato: publicación del paquete final, base de publicación y operación (v1)

Fecha: 17/10/2026. Extiende `docs/T08_CONTRATO.md` y `docs/T10_CONTRATO.md` sin romperlos. Alcance T11A: **preparación local** (no se crean recursos externos ni se transfieren datos). Inventario simulado con supuestos; no corresponde al inventario real de la empresa. Los datos son históricos (marzo–agosto de 2026); nada aquí pronostica octubre.

## 1. Tres tipos de corrida, nunca sustituidos entre sí

| `kind` | Qué es | Origen / período | Fuente | Fecha objetivo máxima |
|---|---|---|---|---|
| `historical_development` | backtest T07, fold G4, demostración de desarrollo (T08R) | origen 10/07/2026; objetivos hasta 31/07 | artefactos T07 verificados | 2026-07-31 |
| `generated_baseline` | `promedio_28` generado por la aplicación (T10), sin observados | origen elegido ≤ 10/07 | historia aprobada ≤ origen | 2026-07-31 |
| **`final_evaluation`** | evaluación final de T12: **predicción fija** origen 31/07 → bloque 01–21/08 y comparación con lo observado, más la **simulación secuencial** 01–31/08 como documento aparte | origen 31/07/2026; bloque 01–21/08/2026 | `artifacts/private/final/` (T12, 7 fases completas, auditoría aprobada) | **2026-08-21** (solo para esta corrida) |

Reglas: una corrida `final_evaluation` no activa el puntero, no reemplaza a la histórica ni a una generada y su `run_id` es `final-20260731-<12 hex del sello T12>`. La barrera general de carga/entrenamiento de agosto (`LAST_TRAIN_DATE`, `check_dates` global, límites HTTP de T10) **no cambia**: la API admite fechas ≤ 2026-08-21 únicamente al consultar una corrida cuyo `kind` sea `final_evaluation`, y nunca para corridas de otro tipo. Ningún endpoint ejecuta modelos, simulaciones ni experimentos; solo lee documentos ya publicados.

## 2. Documentos de la corrida final

**`runs`**: `kind="final_evaluation"`, `run_label="Evaluación final de agosto (origen 31/07/2026, bloque 01–21/08/2026)"`, `origin="2026-07-31"`, `cutoff="2026-07-31"`, `target_start="2026-08-01"`, `target_end="2026-08-21"`, `horizon_days=21`, `evaluation_period={start,end,single_block:true}`, `method={chosen:"promedio_28", comparator:"rf_categoria_distribuido", control:"cero", rf_declared_winner:false, category_baseline:"suma de pronósticos SKU"}`, `idempotency_key="final-eval:<sello_sha256>"`, `fingerprint` = fingerprint de entrenamiento T12, `sources` (meses 2026-03..08 con sha256), `artifacts` = referencias al archivo privado (`name, sha256, size_bytes`; sin binarios ni rutas), `code` (commits a39d3e9 código, 86325a7 sello, 71656c2 R11), `final_package` = `{seal_sha256, frozen_selection_sha256, phases:{siete}, corrections:[…], audit_ok}`, `counts={forecasts_sku, forecasts_categoria, recommendations:0, backtests:1}`, `coverage` (universo común, SKU nuevos, días evaluables, nota «un solo bloque»). `recommendations_unavailable_reason="RECOMENDACION_NO_VALIDADA_PARA_ESTE_ORIGEN"` y `see_run=<run histórica activa>`.

**`forecasts`** (hijos bajo `children_ref`, protocolo T10): mismo documento que T08 con `run_kind="final_evaluation"`; `level` sku/categoria; `pred={promedio_28, rf_categoria_distribuido, cero}` (sellados antes de leer agosto); `observed` = venta real del día (SKU conocido sin venta = 0 observado), `evaluable=false` para un día sin ningún registro del archivo; `cohorte` primaria/historia_corta; categoría = suma de SKU (unidades base heterogéneas); `target_date` ∈ [2026-08-01, 2026-08-21]. SKU nuevos (primera venta posterior al 31/07) **no** son filas: se resumen en `coverage`.

**`backtests`** (un documento, `kind="final_evaluation"`): `predictive` = métricas T12 (`predictivo.json`: SKU y categoría × primaria/historia corta × cero/promedio_28/RF × acum10/14/21/diaria, cobertura, SKU nuevos), `selection` = `{chosen:"promedio_28", rf_declared_winner:false, primary_criterion, primary:{WAPE_promedio_28, WAPE_rf_distribuido, WAPE_cero, mejora_relativa, sesgo_relativo}, note}`, `simulation` = 27 combinaciones (total y cohortes; diferencias en `simulation_differences`), `coverage`, `assumptions` (supuestos T07), `disclaimer`, `provenance="SYNTHETIC_NOT_REAL_INVENTORY"` (la simulación; las predicciones/observados son `OBSERVED_EXCEL`). Las revisiones de la simulación secuencial **no** se publican como predicciones fijas ni se mezclan con métricas T07.

**`recommendations`**: ninguna para la corrida final (la evaluación no crea pedidos operativos). La API responde la página vacía con `unavailable_reason` y `see_run`; no se usa el snapshot de otro día.

## 3. API (cambios mínimos, solo lectura)

- `GET /runs`, `/runs/{id}` incluyen `kind`, `evaluation_period`, `final_package` (resumen: sello, fases, auditoría, correcciones) y `warnings` (lista de textos obligatorios).
- `GET /forecasts?run=<final>` acepta `from/to` ≤ 2026-08-21 solo para esa corrida; rótulos: «WAPE no es exactitud: 0,78 = error absoluto equivalente al 78 % del volumen observado», «categoría = suma de unidades base heterogéneas», «un solo bloque».
- `GET /backtests/bt-<final run_id>` devuelve la comparación T12 con `view=predictive|simulation|all`.
- `GET /recommendations?run=<final>`: 200, `items=[]`, `unavailable_reason`, `see_run`.
- Roles: lector y admin leen; subir/generar siguen siendo solo admin. API caída ⇒ la UI muestra error de API (sin mocks).

## 4. Base de publicación y archivo

Base nueva `demand_forecasting_pub` (nombre documentado; **no** se activa en la base original ni se toca `demand_forecasting_v2`/`_dev`). Política (`config/t11_publication.json`):
- Copiar: `sales` (86 877), `credit_notes` (560), `imports` (completed/noop y su trazabilidad), `import_conflicts`/`import_rejects` (vacías), `month_reservations`, las dos corridas históricas con sus hijos (`hist-20260710-4ea348836e35` activa y `hist-20260710-52b01cd999dd` sustituida con su `quality_issue`), y la corrida final con su backtest.
- No copiar: `sessions`, `users`, `login_attempts`, `login_budget`, `jobs`, `scheduler_ticks`, las seis corridas generadas de prueba ni la corrida `gen-20260620…` fallida. Se **archivan** (hash + manifiesto) en el almacén privado, no se borran de v2.
- No insertar binarios: modelos `.joblib`, NPZ de simulación (~128 MB), CSV mínimos, logs y Excel viven en almacenamiento durable privado separado con hashes y política de acceso (nunca servidos públicamente).
- El puntero activo de la base nueva apunta a la histórica auditada; la final se abre por enlace/selector.
- Capacidad: medir datos+índices **después** de restaurar; objetivo ≤ 60 % de la cuota del clúster Free (512 MB) con proyección de nuevas corridas.

## 5. Operación (resumen; detalle en `T11_PLAN_DESPLIEGUE.md`)

Misma imagen para API y worker/scheduler; mismo origen HTTPS (cookies SameSite=Strict y CSRF); `APP_ENV=production` con cookies Secure; secretos solo por canal privado; `X-Forwarded-For` aceptado únicamente del salto de confianza documentado; subidas/modelos en almacén durable compartido por API y worker; el scheduler sigue deshabilitado por defecto.
