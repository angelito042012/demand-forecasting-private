# T06 Protocolo de comparación de ML con referencias (congelado antes de evaluar)

Fecha: 17/10/2026, America/Lima. Configuración versionada: `config/t06_config.json` (t06-1). Documento y configuración se comprometen en Git antes de obtener resultados de ML. Solo marzo-julio; agosto no se lee ni se evalúa. Los cinco folds, el horizonte de 7 días, las cohortes, la máscara y el universo de targets son los de T05 (`config/t05_config.json`): se reutiliza la misma orquestación (`run_fold`/`evaluate_level`), de modo que reales, fechas y cobertura son idénticos; además se verifica contra `docs/T05_METRICAS.json` que las métricas de los cuatro baselines coinciden antes de comparar.

**Estatus de los folds**: son folds de desarrollo. Los baselines de T05 ya se observaron y estos mismos folds se usan para comparar y seleccionar; no constituyen una prueba final independiente. Agosto es el test final posterior y sigue reservado.

## Prueba técnica previa (declarada)

Antes de fijar este protocolo se midió solo el costo de ajuste en el fold F5/SKU (sin calcular errores de validación): 838 570 filas × 24 features (80,5 MB), Random Forest 94 s, XGBoost 6 s, 2 valores negativos recortados. Dentro del presupuesto; no se reduce el submuestreo de orígenes.

## Modelos (parámetros fijos, sin búsqueda)

Un modelo global por nivel (SKU-almacén y categoría) y fold, con h como feature (modelo directo). Mismos hiperparámetros en ambos niveles.
- Random Forest (`RandomForestRegressor`): 100 árboles, profundidad 12, `min_samples_leaf`=20, `max_features`=0,5, seed 20261017, 4 hilos.
- Boosting (`XGBRegressor`, xgboost 3.4.1 instalado): 150 árboles, profundidad 4, tasa 0,1, subsample 0,8, colsample 0,8, `min_child_weight`=5, λ=1, objetivo `reg:squarederror`, método `hist`, seed 20261017, 4 hilos.
- No se incorporan LSTM, redes profundas, AutoML ni servicios externos. No se ajustan hiperparámetros tras ver resultados; cualquier cambio se declara aquí como enmienda antes de re-evaluar.
- Predicciones negativas: recorte a 0 en todos los modelos y folds, con conteo registrado. Sin redondeo a pedidos.

## Muestras, features y etiquetas

- Muestra = (entidad, origen o, horizonte h=1..7). Orígenes de entrenamiento: submuestreo determinista cada 3 días naturales alineado hacia atrás desde corte−7 (o+7 ≤ corte), desde el día 27 del calendario (28/03/2026). Todas las entidades conocidas en o (primera venta ≤ o), incluidas las de historia corta; nunca se muestrea por resultados ni solo ventas positivas.
- Etiqueta: cantidad diaria en o+h con o+h ≤ corte del fold. Se excluyen etiquetas ausentes/enmascaradas/sin registros; los ceros válidos se conservan. El calendario no se comprime.
- Features (24, solo información ≤ o salvo calendario de la fecha objetivo): h; rezagos naturales 0–6; mismo día de semana 1 y 2 semanas antes de la fecha objetivo (siempre ≤ o); media 7 y 28 días, desviación y proporción de ceros de 28 días, observaciones utilizables en 28 días, días desde la última venta, historia disponible, media histórica; día de la semana, día del mes y mes de la fecha objetivo; código de categoría y de almacén del vocabulario de entrenamiento (−1 si desconocido); media 28 días de la categoría. En nivel categoría la media de categoría es la propia serie.
- Ausentes: NaN nativo (ambos modelos lo soportan); no hay imputación que ajustar. El vocabulario de categorías y almacenes se ajusta solo con el entrenamiento del fold. Los IDs de SKU no se usan como números; sirven únicamente como clave de agrupación de historia.
- Precio: **no incorporado en esta iteración** (limitación registrada). Si se añade, solo precio histórico conocido al origen por unidad base, nunca el precio del día objetivo.
- Categoría = productos conocidos al corte, igual que T05; SKU nuevos y categorías desconocidas se reportan aparte.

## Comparación y selección (regla preregistrada)

Se comparan Random Forest, XGBoost y los cuatro baselines (incluido el control cero) en cohorte primaria, universo común, mismos folds.
- Criterio primario SKU: **WAPE de cantidad acumulada en el bloque de 7 días** (por entidad, días evaluables), agregado ponderado por unidades de los 5 folds. Justificación: la reposición decide sobre volumen del periodo, no sobre el día. Difiere deliberadamente del criterio diario con que se escogió `ultimo_dia` en T05; ambos se reportan.
- Criterio primario categoría: **WAPE diario**; el bloque semanal se reporta igualmente.
- Mejor referencia = baseline con menor criterio primario agregado entre los cuatro (incluye el cero).
- Un modelo ML "supera la regla" si, en ese nivel, a la vez: (a) su criterio primario es al menos 2 % relativo menor que el de la mejor referencia; (b) es menor que la mejor referencia en al menos 3 de 5 folds; (c) |sesgo acumulado| / unidades observadas ≤ 0,25. Si ninguno cumple, no se declara ganador: se propone el baseline no nulo con menor criterio primario y se registra que el ML no confirmó mejora en desarrollo. Entre ML que cumplan, el de menor criterio.
- Se reportan también MAE, RMSE, WAPE, sesgo, proporciones sub/sobre, MAPE solo con reales positivos (cobertura y ceros excluidos), R² con condiciones de T05, error por fold, mejoras/retrocesos relativos y número de folds favorables. WAPE y MAPE son **razones** (1,00 = 100 %).
- Una predicción permanentemente nula (control cero) no implica una política de compra válida; se compara también el sesgo.

## Evidencia e inferencia

Modelos entrenados y predicciones en `artifacts/private/t06/` (ignorados por Git); se versionan protocolo, configuración, métricas agregadas, reporte y manifiesto (hashes de código/config/datos/fuentes, seeds, versiones, tiempos, filas, memoria de la matriz). Cada paquete guarda modelo, vocabulario, nombres de features, corte, versión y hash de configuración (joblib: cargar solo artefactos generados localmente). Interfaz `forecast_origin`: desde un origen devuelve siete fechas futuras con cantidades no negativas, modelo, corte y versión. Reproducibilidad: el fold F1 se reentrena y se exige igualdad de predicciones con tolerancia absoluta 1e-9 (ver Enmienda 1).

## Límites declarados

Cinco semanas de validación en desarrollo; un solo almacén y unidad; ventas posiblemente censuradas por stock; sin precio; el horizonte de 7 días no cubre necesariamente lead time + revisión de la simulación (se decide en T07: no se extrapola a 14 días sin evaluar ese horizonte).

## Enmiendas

**Enmienda 1 (17/10/2026, tras la primera ejecución completa, antes de re-evaluar).** La primera ejecución dio `repeticion_f1_identica=false`. Diagnóstico: XGBoost reproduce exactamente; Random Forest con `n_jobs=4` difiere hasta 5,7e-14 (suma de árboles en orden de hilos no determinista, ruido de coma flotante). Motivo del cambio: el criterio «igualdad exacta» era demasiado estricto para un ensamble paralelo; no cambia modelos, features, folds, parámetros ni la regla de selección. Nuevo criterio: diferencia absoluta máxima ≤ 1e-9 en las columnas numéricas e igualdad en las demás; se informa la diferencia máxima observada. Esta enmienda se redacta tras conocer el resumen de la primera ejecución (selección SKU sin ganador ML; categoría con ganador), pero no depende de él: se aplica igual a cualquier resultado. La ejecución se repite para que el manifiesto corresponda a la configuración enmendada.
