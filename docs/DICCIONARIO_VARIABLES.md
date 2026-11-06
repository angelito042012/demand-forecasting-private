# Diccionario de variables del pipeline — con procedencia

Fecha: 2026-11-06. Cubre las constantes, features, metricas y parametros del pipeline
tal como existen en el codigo; no inventa valores no medidos.

---

## 1. Constantes de corte y fecha (parametrizadas)

Estas constantes estaban fijas en el codigo y fueron parametrizadas como argumentos
con valores por defecto. Los valores actuales corresponden al corte del 20/10/2026.

| Variable | Valor actual | Archivo | Proposito | Procedencia |
|---|---|---|---|---|
| `OCTOBER_NAME` | `"octubre.xlsx"` | `pipeline/plan/dataset_v2.py:38` | Nombre del libro de ventas del mes de corte | Nombre del archivo Excel entregado por la MYPE |
| `OCTOBER_WINDOW` | `(2026-10-01, 2026-10-20)` | `pipeline/plan/dataset_v2.py:39` | Ventana de fechas validas del libro | Primer dia del mes hasta ultimo dia completo |
| `CUTOFF` | `2026-10-20` | `pipeline/plan/dataset_v2.py:40` | Ultimo dia completo de ventas en el libro | Derivado de `OCTOBER_WINDOW[1]` |
| `PARTIAL_DATE` | `"2026-10-21"` | `pipeline/plan/dataset_v2.py:41` | Fecha del parcial (dia incompleto posterior al corte) | Dia siguiente al corte; datos extraidos de SQL |
| `AS_OF_LOCAL` | `"2026-10-20T23:59:59-05:00"` | `pipeline/inventory/reconstructed.py:31` | Cierre de la existencia reconstruida | Fin del dia del corte en zona America/Lima |
| `BASE_AS_OF_LOCAL` | `"2026-10-18T17:00:00-05:00"` | `pipeline/inventory/reconstructed.py:32` | Fecha/hora del conteo fisico base | Hora del conteo reportado por la MYPE (18/10 17:00) |
| `LAST_FULL_DAY` | `2026-10-20` | `scripts/sql21_prepare.py:27` | Ultimo dia completo para conciliacion SQL | Coincide con `CUTOFF`; se usa en la preparacion de datos |

## 2. Calendario y particion temporal

| Variable | Valor | Archivo | Proposito | Procedencia |
|---|---|---|---|---|
| `TIMEZONE` | `"America/Lima"` | `pipeline/data/calendar.py:14` | Zona horaria de negocio | Ubicacion de la MYPE |
| `EXCLUDED_DATES` | `{2026-04-03, 2026-04-12, 2026-06-07}` | `pipeline/data/calendar.py:16` | Dias excluidos del entrenamiento y metricas | Decision de datos (DECISIONES_DATOS.md); no implican cierre |
| `FINAL_TEST_START` | `2026-08-01` | `pipeline/data/calendar.py:20` | Inicio del bloque de evaluacion final (agosto) | Decision de particion temporal (T12) |
| `FINAL_TEST_END` | `2026-08-31` | `pipeline/data/calendar.py:21` | Fin del bloque de evaluacion final | Ultimo dia de agosto 2026 |
| `LAST_TRAIN_DATE` | `2026-07-31` | `pipeline/data/calendar.py:22` | Ultimo dia accesible para entrenamiento/validacion | Dia anterior al bloque de test final |
| `FIRST_REQUIRED_MONTH` | `"2026-03"` | `pipeline/data/sources.py:23` | Primer mes requerido para fuentes aprobadas | Primera fuente de datos disponible (marzo 2026) |
| `START` | `2026-03-01` | `pipeline/plan/normalize.py:20` | Inicio del periodo de datos academicos | Primer registro de ventas disponible |
| `END` | `2026-09-30` | `pipeline/plan/normalize.py:21` | Fin del periodo de datos academicos (v1) | Ultimo mes del paquete de 14 libros |
| `SELECTION_CUTOFF` | `2026-07-31` | `pipeline/plan/normalize.py:22` | Corte de seleccion del grupo de 50 productos | Coincide con LAST_TRAIN_DATE |

## 3. Features de ML (T06/T07)

Definidas en `pipeline/forecast/features.py`. Todas las features usan columnas
anteriores o iguales al origen del fold; no hay fuga temporal.

| Feature | Tipo | Descripcion | Procedencia |
|---|---|---|---|
| `h` | int | Horizonte de pronostico (1..21) | Parametro del fold |
| `lag0`..`lag6` | float | Valor observado en los dias (origen), (origen-1), ..., (origen-6) | Serie diaria de ventas |
| `lag_mismo_dia_1s` | float | Valor del mismo dia de la semana, 1 semana antes (ajustado por horizonte) | Serie diaria; `o + h - 7*ceil(h/7)` |
| `lag_mismo_dia_2s` | float | Idem, 2 semanas antes | Serie diaria |
| `media7` | float | Media de observaciones utilizables en los ultimos 7 dias | Ventas |
| `media28` | float | Media de observaciones utilizables en los ultimos 28 dias | Ventas |
| `desv28` | float | Desviacion estandar de los ultimos 28 dias | Ventas |
| `prop_ceros28` | float | Proporcion de ceros observados en los ultimos 28 dias | Ventas |
| `usables28` | float | Numero de observaciones utilizables en los ultimos 28 dias | Ventas |
| `dias_desde_ultima_venta` | float | Dias desde la ultima observacion positiva | Ventas |
| `historia_dias` | float | Dias naturales desde la primera observacion hasta el origen | Ventas |
| `media_historica` | float | Media de todas las observaciones historicas hasta el origen | Ventas |
| `dow` | float | Dia de la semana de la fecha objetivo (0=lunes) | Calendario |
| `dia_mes` | float | Dia del mes de la fecha objetivo | Calendario |
| `mes` | float | Mes de la fecha objetivo | Calendario |
| `cat_code` | int | Codigo de la categoria (vocabulario ajustado en train, -1=desconocido) | Catalogo |
| `cat_media28` | float | Media 28 dias de la categoria del producto | Serie de categoria |
| `alm_code` | int | Codigo del almacen (vocabulario ajustado en train, -1=desconocido) | Registro de ventas |

Constantes:
- `FEATURE_VERSION = "t07-1"` — etiqueta de la semantica de features
- `HORIZON_MAX = 21` — horizonte maximo del modelo
- `UNKNOWN_CODE = -1` — codigo para categorias/almacenes desconocidos en inferencia

## 4. Baselines (T05)

Definidos en `pipeline/forecast/baselines.py`. Horizonte h=1..H, emision unica al origen.

| Metodo | Definicion | Procedencia |
|---|---|---|
| `cero` | Siempre 0 | Referencia de control |
| `ultimo_dia` | Ultimo valor utilizable (puede ser 0 observado) | Serie diaria |
| `naive_semanal` | Dato de `t+h-7`; si no utilizable → `promedio_28`; si tampoco → NaN | Serie diaria |
| `promedio_28` | Media de observaciones utilizables de los 28 dias naturales previos al origen | Serie diaria |

## 5. Metodos ML (T06/T07)

| Metodo | Clase | Config | Nivel | Procedencia |
|---|---|---|---|---|
| `random_forest` | `sklearn.ensemble.RandomForestRegressor` | `config/t06_config.json` | SKU y categoria (T06); categoria (T07) | Congelado antes de evaluar |
| `xgboost` | `xgboost.XGBRegressor` | `config/t06_config.json` | SKU y categoria (T06) | Congelado antes de evaluar |
| `rf_distribuido` | RF por categoria distribuido a SKU por pesos | `config/t07_config.json` | SKU (via categoria) | T07: pesos por unidades positivas 28d |
| `promedio_28` (operativo) | Media de 28 dias, sin ML | N/A | SKU | Metodo operativo seleccionado (T12 WAPE 0.7810 vs RF 0.7910) |

## 6. Metricas (T05/T06/T07/T12)

Definidas en `pipeline/forecast/metrics.py`. Se calculan sobre estadisticos suficientes
acumulados, nunca promediando porcentajes.

| Metrica | Formula | Interpretacion | Notas |
|---|---|---|---|
| `MAE` | `sum_abs / n` | Error absoluto medio por linea-dia | |
| `RMSE` | `sqrt(sum_sq / n)` | Raiz del error cuadratico medio | |
| `WAPE` | `sum_abs / sum_a` (si `sum_a > 0`) | Error absoluto ponderado por volumen | Metrica primaria de seleccion |
| `MAPE` | `sum_ape / n_pos` (si `n_pos > 0`) | Error porcentual medio sobre reales positivos | Excluye ceros; reportar cobertura |
| `R²` | `1 - sum_sq / SST` (si `n >= 30` y `SST > 0`) | Varianza explicada | Indefinido si n < 30 o varianza nula |
| `sesgo_acumulado` | `sum_p - sum_a` | Sobre/subpronostico total | |
| `prop_subpronostico` | `n_under / n` | Proporcion de lineas donde prediccion < real | |
| `prop_sobrepronostico` | `n_over / n` | Proporcion de lineas donde prediccion > real | |

Estadisticos suficientes: `n`, `sum_a`, `sum_a2`, `sum_p`, `sum_abs`, `sum_sq`,
`n_under`, `n_over`, `n_exact`, `n_pos`, `sum_ape`, `n_zero`.

## 7. Parametros de modelo (congelados)

### T06 (SKU y categoria, h=1..7)

De `config/t06_config.json`:
- RF: `n_estimators=100, max_depth=12, min_samples_leaf=20, max_features=0.5, random_state=20261012, n_jobs=-1`
- XGB: `n_estimators=100, max_depth=6, learning_rate=0.1, subsample=0.8, colsample_bytree=0.8, min_child_weight=10, random_state=20261012, n_jobs=1`
- Origenes de entrenamiento: `paso_dias=7, origen_minimo_indice=27`
- Folds: F1 (corte 31/05), F2 (14/06), F3 (28/06), F4 (10/07)

### T07 (categoria→SKU, h=1..21)

De `config/t07_config.json`:
- RF categoria: `n_estimators=100, max_depth=12, min_samples_leaf=20, max_features=0.5, random_state=20261017, n_jobs=1`
- Origenes: `paso_dias=3, origen_minimo_indice=27, horizonte=21`
- Folds predictivos: G1 (31/05), G2 (14/06), G3 (28/06), G4 (10/07)
- Pesos de asignacion: unidades positivas 28d → fallback historico → fallback uniforme
- Costo unitario supuesto: `0.65 * mediana de precio base <= 31/05`
- Seleccion: vista `acum14`, cohorte primaria, mejora relativa >= 0.02, folds favorables >= 3

## 8. Reglas de seleccion

### T06 (docs/T06_PROTOCOLO.md)

| Parametro | Valor | Procedencia |
|---|---|---|
| `mejora_relativa_minima` | 0.02 | Protocolo preregistrado |
| `folds_favorables_minimos` | 3 | Protocolo preregistrado |
| `sesgo_relativo_maximo_abs` | 0.25 | Protocolo preregistrado |
| Vista primaria SKU | `diaria` | config/t06_config.json |
| Vista primaria categoria | `diaria` | config/t06_config.json |

### T07 (provisional)

| Parametro | Valor | Procedencia |
|---|---|---|
| `criterio_primario.H` | 14 | config/t07_config.json |
| `comparador` | `promedio_28` | config/t07_config.json |
| `mejora_relativa_minima` | 0.02 | config/t07_config.json |
| `folds_favorables_minimos` | 3 | config/t07_config.json |
| `sesgo_relativo_maximo_abs` | 0.25 | config/t07_config.json |

## 9. Simulacion de inventario (T07)

De `config/t07_config.json`:

| Parametro | Valor | Procedencia |
|---|---|---|
| Periodo | 2026-06-01 a 2026-07-31 | Datos de entrenamiento disponibles |
| Inicializacion hasta | 2026-05-31 | Corte del primer fold |
| Universo | SKU con primera venta <= 31/05 | Catalogo fijado |
| Escenario principal | L=7, S=7, R=7 | Supuesto de lead time y stock de seguridad |
| Stock inicial | `ceil(media_inicial * (L+R))` | Convencion homogenea entre politicas |
| Holding anual | 20% | Supuesto, no medido en la MYPE |
| Empaque minimo | 1 | Sin restriccion real conocida |
| Dia enmascarado | 2026-06-07 | EXCLUDED_DATES (DECISIONES_DATOS.md) |

## 10. Fuentes de datos

| Fuente | Archivos | Periodo | Procedencia |
|---|---|---|---|
| Libros de ventas (14) | marzo.xlsx .. octubre.xlsx (7 meses), setiembre.xlsx | 2026-03 a 2026-10 | Excel entregado por la MYPE |
| Parcial SQL 21/10 | CSV extraido de SQL Server | 2026-10-21 (incompleto) | `scripts/sql21_prepare.py` via `sqlcmd` |
| Conteo fisico | `conteo_reportado.csv` | 2026-10-18 17:00 | Conteo reportado por la MYPE |
| Informe SQL | `informe.json` | Conciliacion Excel-SQL | `scripts/sql21_prepare.py` |
| Existencias reconstruidas | `existencias.csv` + `manifest.json` | Cierre 2026-10-20 | Conteo + movimientos del kardex |

## 11. Colecciones de MongoDB

| Coleccion | Modulo | Contenido |
|---|---|---|
| `plan_datasets` | `pipeline/plan/dataset.py` | Cabeceras de datasets importados |
| `plan_sales` | `pipeline/plan/dataset.py` | Ventas normalizadas |
| `plan_purchases` | `pipeline/plan/dataset.py` | Compras normalizadas |
| `plan_credits` | `pipeline/plan/dataset.py` | Notas de credito |
| `plan_quarantine` | `pipeline/plan/dataset.py` | Registros en cuarentena |
| `plan_sales_partial` | `pipeline/plan/dataset_v2.py` | Parcial del dia posterior al corte |
| `inventory_reported_snapshots` | `pipeline/inventory/reconstructed.py` | Snapshots de inventario reportado |
| `inventory_reported_items` | `pipeline/inventory/reconstructed.py` | Items de inventario reportado |
| `inventory_reconstructed_snapshots` | `pipeline/inventory/reconstructed.py` | Snapshots de existencia reconstruida |
| `inventory_reconstructed_items` | `pipeline/inventory/reconstructed.py` | Items de existencia reconstruida |

## 12. Bases protegidas

`PROTECTED_DBS = {"demand_forecasting_dev", "demand_forecasting_v2", "demand_forecasting_pub"}`

Ninguna funcion de escritura opera sobre estas bases. Definidas en
`pipeline/plan/dataset.py` y `pipeline/inventory/reconstructed.py`.
