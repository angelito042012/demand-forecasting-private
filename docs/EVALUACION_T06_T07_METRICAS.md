# Evaluacion T06/T07 y formalizacion de metricas

Fecha: 2026-11-06. Documenta el diseno experimental, las metricas y los resultados
de las evaluaciones T06/T07/T12 tal como existen en el codigo y en los archivos
de resultados. No inventa valores ni re-ejecuta experimentos.

**Restriccion:** los datos de agosto/T12 son evidencia historica cerrada; no deben
reutilizarse para ajustar modelos y presentarlos como nueva prueba (DIAGNOSTICO_Y_PLAN.md).

---

## 1. Diseno experimental

### 1.1 Particion temporal

| Bloque | Periodo | Uso |
|---|---|---|
| Entrenamiento | 2026-03-01 a corte del fold | Features, etiquetas, ajuste de modelos |
| Validacion (T05/T06) | 7 dias posteriores al corte (h=1..7) | Seleccion de metodo por fold |
| Validacion (T07) | 21 dias posteriores al corte (h=1..21) | Evaluacion predictiva y simulacion |
| Test final (T12) | 2026-08-01 a 2026-08-21 (prediccion) / 2026-08-31 (simulacion) | Evaluacion final bajo seleccion congelada |
| Reservado | Agosto completo | No accesible desde la ruta de entrenamiento |

Dias excluidos del entrenamiento y metricas (sin comprimir calendario):
2026-04-03, 2026-04-12, 2026-06-07 (DECISIONES_DATOS.md).

### 1.2 Folds de validacion cruzada temporal

**T05/T06** (h=1..7, config: `config/t05_config.json`, `config/t06_config.json`):

| Fold | Corte | Bloque de validacion |
|---|---|---|
| F1 | 2026-05-31 | 2026-06-01 a 2026-06-07 |
| F2 | 2026-06-14 | 2026-06-15 a 2026-06-21 |
| F3 | 2026-06-28 | 2026-06-29 a 2026-07-05 |
| F4 | 2026-07-12 | 2026-07-13 a 2026-07-19 |
| F5 | 2026-07-24 | 2026-07-25 a 2026-07-31 |

**T07** (h=1..21, config: `config/t07_config.json`):

| Fold | Corte | Bloque de validacion |
|---|---|---|
| G1 | 2026-05-31 | 2026-06-01 a 2026-06-21 |
| G2 | 2026-06-14 | 2026-06-15 a 2026-07-05 |
| G3 | 2026-06-28 | 2026-06-29 a 2026-07-19 |
| G4 | 2026-07-10 | 2026-07-11 a 2026-07-31 |

### 1.3 Cohortes

| Cohorte | Criterio | Procedencia |
|---|---|---|
| Primaria | historia >= 56 dias Y observaciones utilizables en 28 dias >= 21 | `config/t05_config.json` |
| Historia corta | Resto de entidades conocidas al corte | Complemento de primaria |
| Universo comun | Entidades donde TODOS los metodos core tienen prediccion | Interseccion |

### 1.4 Congelacion

La configuracion se congela ANTES de evaluar con datos de agosto:
- `config/seleccion_congelada.json` (sha256 verificado contra `.sha256`)
- Predicciones selladas antes de leer agosto (sello verificado en `pipeline/final/frozen.py`)
- Codigo experimental congelado byte a byte (motor de simulacion del commit e5466413)

## 2. Metodos evaluados

### 2.1 Baselines (T05)

| Metodo | Definicion | Horizonte |
|---|---|---|
| `cero` | Siempre 0 (control) | h=1..H |
| `ultimo_dia` | Ultimo valor utilizable antes del origen | h=1..7 |
| `naive_semanal` | Dato de t+h-7; fallback a promedio_28 | h=1..7 |
| `promedio_28` | Media de observaciones utilizables de los 28 dias anteriores | h=1..H |

### 2.2 Modelos ML (T06)

Nivel SKU y categoria, h=1..7.

| Modelo | Clase | Hiperparametros clave |
|---|---|---|
| Random Forest | `sklearn.ensemble.RandomForestRegressor` | `n_estimators=100, max_depth=12, min_samples_leaf=20, max_features=0.5, random_state=20261017` |
| XGBoost | `xgboost.XGBRegressor` | `n_estimators=150, max_depth=4, learning_rate=0.1, subsample=0.8, colsample_bytree=0.8, min_child_weight=5` |

Origenes de entrenamiento: paso 3 dias, origen minimo indice 27, alineados hacia atras.
Prediccion negativa: recorte a 0. Ausentes: NaN nativo (sin imputacion).

### 2.3 Modelo extendido (T07)

RF por categoria (h=1..21) distribuido a SKU por pesos de asignacion.

| Parametro | Valor |
|---|---|
| Modelo | RF categoria: `n_estimators=100, max_depth=12, random_state=20261017, n_jobs=1` |
| Horizonte | 1..21 dias |
| Distribucion | Unidades positivas 28d → historico → uniforme |
| Costo unitario supuesto | 0.65 * mediana de precio base <= 31/05 |
| Referencia fija | Prediccion emitida una vez al 31/05 (no actualizada) |

## 3. Metricas formalizadas

Fuente: `pipeline/forecast/metrics.py`. Las metricas se calculan sobre
**estadisticos suficientes acumulados** (ponderacion por conteos/unidades);
nunca promediando porcentajes.

### 3.1 Estadisticos suficientes

Para cada par (actual `a`, prediccion `p`), se acumulan:

| Estadistico | Formula | Papel |
|---|---|---|
| `n` | conteo de pares | Denominador de MAE, RMSE |
| `sum_a` | Σa | Denominador de WAPE; media de reales |
| `sum_a2` | Σa² | SST para R² |
| `sum_p` | Σp | Sesgo: sum_p - sum_a |
| `sum_abs` | Σ|p-a| | Numerador de MAE y WAPE |
| `sum_sq` | Σ(p-a)² | Numerador de RMSE y R² |
| `n_pos` | #{a > 0} | Denominador de MAPE |
| `sum_ape` | Σ(|p-a|/a) para a > 0 | Numerador de MAPE |
| `n_under` | #{p < a} | Proporcion de subpronostico |
| `n_over` | #{p > a} | Proporcion de sobrepronostico |
| `n_exact` | #{p = a} | Proporcion de acierto exacto |
| `n_zero` | #{a = 0} | Ceros reales excluidos de MAPE |

Los estadisticos se SUMAN entre folds/niveles; las metricas se calculan una
sola vez sobre los totales (`finalize(add_stats(...))`).

### 3.2 Metricas finales

| Metrica | Formula | Condicion | Interpretacion |
|---|---|---|---|
| **WAPE** | `sum_abs / sum_a` | `sum_a > 0` | Error relativo ponderado por volumen. **Metrica primaria de seleccion.** |
| **MAPE** | `sum_ape / n_pos` | `n_pos > 0` | Error porcentual medio sobre reales positivos. Reportar cobertura (`n_pos/n`). |
| **MAE** | `sum_abs / n` | `n > 0` | Error absoluto medio |
| **RMSE** | `sqrt(sum_sq / n)` | `n > 0` | Raiz del error cuadratico medio |
| **R²** | `1 - sum_sq / SST` | `n >= 30` y `SST > 1e-12` | Varianza explicada. Indefinido si n insuficiente o varianza nula. |
| **Sesgo** | `sum_p - sum_a` | siempre | Sobrepronostico (+) o subpronostico (-) total |

### 3.3 Vistas de agregacion

| Vista | Definicion | Uso |
|---|---|---|
| `diaria` | Un par (actual, prediccion) por entidad por dia del bloque | T05/T06 seleccion |
| `bloque7` | Suma acumulada de 7 dias por entidad | T06 seleccion SKU |
| `acum10` | Suma acumulada de 10 dias por entidad | T07/T12 |
| `acum14` | Suma acumulada de 14 dias por entidad | T07/T12 seleccion primaria |
| `acum21` | Suma acumulada de 21 dias por entidad | T07/T12 |

## 4. Reglas de seleccion preregistradas

### 4.1 T06 (docs/T06_PROTOCOLO.md)

Un modelo ML se declara ganador por nivel si cumple TODAS las condiciones:
1. `mejora_relativa_minima >= 0.02` (WAPE agregado vs mejor baseline)
2. `folds_favorables_minimos >= 3` (de 5 folds)
3. `|sesgo_relativo| <= 0.25` (sesgo / unidades observadas)

Sin ventaja: se propone el baseline no nulo con menor WAPE.

### 4.2 T07 (config/t07_config.json)

Criterio primario: `acum14`, cohorte primaria, universo comun.
Comparador: `promedio_28`. Mismos umbrales que T06.

## 5. Resultados T12 (evaluacion final — historica, cerrada)

Fuente: `docs/T12_RESULTADOS.md`. Un solo bloque 01-21/08, origen 31/07.
**No hay umbrales prometidos**; los resultados desfavorables se conservan.

### 5.1 Hallazgo predictivo primario (SKU, cohorte primaria, acum14, n=3401)

| Metodo | WAPE | MAE | RMSE | Sesgo | R² | MAPE (cobertura) |
|---|---|---|---|---|---|---|
| cero | 1.0000 | 3.048 | 9.356 | -10366 | -0.119 | 1.0000 (0.485) |
| **promedio_28** | **0.7810** | 2.380 | 7.288 | 212.5 | 0.321 | 0.9599 (0.485) |
| rf_distribuido | 0.7910 | 2.411 | 7.342 | 311.6 | 0.311 | 0.9709 (0.485) |

**Resultado: promedio_28 supera a RF** (mejora relativa RF = -0.0129; negativa = RF peor).
El metodo operativo no se modifica: promedio_28 permanece como metodo de pronostico.

### 5.2 Resultados por horizonte acumulado (SKU primaria)

| Horizonte | WAPE promedio_28 | WAPE RF | Mejora RF | R² promedio_28 | R² RF |
|---|---|---|---|---|---|
| acum10 | 0.8165 | 0.8308 | -0.0175 | 0.303 | 0.294 |
| acum14 | 0.7810 | 0.7910 | -0.0129 | 0.321 | 0.311 |
| acum21 | 0.7512 | 0.7590 | -0.0104 | 0.340 | 0.330 |

### 5.3 Resultados por categoria (acum14)

| Metodo | WAPE | R² |
|---|---|---|
| cero | 1.0000 | -0.167 |
| promedio_28 | 0.1170 | 0.994 |
| rf_categoria | 0.1166 | 0.994 |

A nivel categoria, RF y promedio_28 son practicamente iguales (WAPE 0.1166 vs 0.1170).
La diferencia se amplifica al distribuir a SKU por los pesos de asignacion.

### 5.4 Simulacion de inventario (L=7, S=7, total)

| Politica | Fill rate | Perdidas | Stock medio | Compras |
|---|---|---|---|---|
| referencia_fija | 0.7561 | 5813 | 12648 | 267440 |
| promedio_28 | 0.7792 | 5262 | 13881 | 309792 |
| rf_distribuido | 0.7812 | 5216 | 13973 | 326713 |

RF: +0.0019 fill rate vs promedio_28, pero +5.5% en compras desembolsadas.
Una ventaja de servicio acompanada de mas compras no se presenta como mejora.

### 5.5 Cobertura y limitaciones del test

- **Un solo bloque** de 21 dias: sin intervalo de confianza ni prueba de tres folds
- Demanda proxy = ventas observadas, censuradas por stock real desconocido
- Inventario simulado con supuestos (costos, holding 20%/365, lead time, seguridad)
- SKU nuevos (103, 353 unidades) informados aparte, sin historia inventada
- Catalogo al 31/07 sin corregir con agosto

## 6. Reproduccion

### 6.1 Archivos de codigo

| Modulo | Archivo | Funcion principal |
|---|---|---|
| Features | `pipeline/forecast/features.py` | `build_training()`, `build_matrix()` |
| Baselines | `pipeline/forecast/baselines.py` | `forecast_block()` |
| Modelos | `pipeline/forecast/models.py` | `fit_bundle()`, `predict_block()` |
| Metricas | `pipeline/forecast/metrics.py` | `stats()`, `finalize()`, `add_stats()` |
| T06 seleccion | `pipeline/forecast/t06.py` | `make_extras_fn()`, `select_models()` |
| T07 prediccion | `pipeline/forecast/t07.py` | `forecast_origin_t07()`, `eval_fold_predictions()` |
| T12 congelacion | `pipeline/final/frozen.py` | `verify_freeze()` |
| T12 calculos | `pipeline/final/core.py` | `fixed_predictions()`, `block_days()` |
| T12 orquestador | `pipeline/final/runner.py` | Orquesta todo el flujo T12 |
| T12 auditoria | `pipeline/final/audit.py` | Recomputa desde predicciones selladas |

### 6.2 Configuracion

| Archivo | Contenido |
|---|---|
| `config/t05_config.json` | Folds, cohortes, horizonte 7d, baselines |
| `config/t06_config.json` | Hiperparametros RF/XGB, origenes, regla de seleccion |
| `config/t07_config.json` | RF categoria, horizonte 21d, simulacion, seleccion provisional |
| `config/seleccion_congelada.json` | Seleccion congelada para T12 (sha256 verificado) |

### 6.3 Prerequisitos para reproduccion

1. Base de datos MongoDB con el dataset v1 importado (`pipeline/plan/dataset.py`)
2. Fuentes aprobadas para los meses requeridos (`pipeline/data/sources.py`)
3. Entorno Python 3.12 con las dependencias de `requirements.lock.txt`
4. Git con acceso al commit e5466413 (motor de simulacion congelado)

### 6.4 Advertencia

T12 es una evaluacion historica cerrada. Reproducirla con los mismos datos debe
dar resultados identicos (auditoria aprobada con tolerancia 1.09e-10). **No se debe
re-ejecutar con datos modificados ni presentar los resultados como nuevos.**
