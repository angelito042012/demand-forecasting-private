# T06 Comparación de ML con referencias

Lee docs/REVISION_CODEX_04.md, ESTADO/TRASPASO y los contratos pertinentes. T05 queda aceptado al commit dff7d27; no repetir toda la preparación. Agosto continúa reservado. Este encargo autoriza entrenar y evaluar ML únicamente en marzo-julio.

## 1 Protocolo antes de ejecutar

Crea y compromete docs/T06_PROTOCOLO.md y config/t06_config.json antes de obtener resultados. Mantén los cinco folds, horizonte de siete días y universo/cohortes de T05. Define modelos, features, política de ausentes, seeds, límites de cómputo y regla de selección.

Comparar Random Forest y un boosting compatible con las dependencias instaladas; no usar una búsqueda extensa. Preferir un modelo global por nivel (SKU y categoría) en lugar de entrenar miles de modelos individuales. Limitar paralelismo y registrar tiempo/memoria; si el coste es alto, reducir determinísticamente los orígenes de entrenamiento, nunca muestrear solo ventas positivas o elegir muestras por los resultados de validación. Documentar cualquier cambio antes de su evaluación.

Configurar un primer experimento acotado, por ejemplo hasta 100–150 árboles, profundidad limitada, seed fija y máximo cuatro hilos. Fijar la elección exacta compatible con las librerías en la configuración; no variar decenas de configuraciones hasta obtener una tabla favorable. No incorporar LSTM, redes profundas, AutoML ni servicios externos en este incremento.

## 2 Features y etiquetas sin futuro

Usa la ruta de fuentes aprobadas, cortes y máscaras existente. En cada muestra de entrenamiento hay un origen histórico o y un horizonte h=1..7: features solo con información conocida hasta o; etiqueta en o+h, siempre <= corte de entrenamiento del fold. Puede usarse un modelo directo con h como feature; no alimentar con ventas reales de horizontes anteriores del bloque.

Features propuestas acotadas: rezagos por fecha natural, medias y variabilidad histórica de 7/28 días, proporción histórica de ceros, días desde última venta, historia disponible, categoría/almacén conocidos y calendario de la fecha objetivo. Mantener ceros válidos; excluir etiquetas ausentes/enmascaradas y añadir indicadores de ausencia cuando corresponda. No comprimir calendario antes de rezagos.

Si se incorpora precio para cumplir el planteamiento del proyecto, debe ser precio histórico conocido al origen (por unidad base y con equivalencias correctas), nunca PRECIO, TOTAL_LINEA/cantidad o promociones del día futuro objetivo. No derivar una feature de la cantidad que se intenta predecir. Obtener cualquier precio histórico a través de la misma ruta de fuentes/corte aprobados. Si no es viable incluirlo aún, registrar la limitación expresamente.

Transformaciones, imputación y codificadores se ajustan solo en entrenamiento del fold; tratar categorías desconocidas sin usar validación para crear el vocabulario. No convertir IDs de SKU en una escala numérica con significado inventado; usar claves para agrupar historia y una codificación técnicamente justificada si se incluyen como feature. La pertenencia a cohortes y población se decide al origen, como en T05.

Los conjuntos usados para seleccionar modelos están en desarrollo y ya se observaron baselines T05: no describir estos folds como una prueba final independiente. Agosto es el test final posterior.

## 3 Comparación y selección transparentes

Incluir los cuatro baselines T05 en las tablas de comparación, sin omitir el control cero. Verificar identidad de targets/cobertura, reales, cohortes, fechas y máscaras con T05 antes de comparar. Categoría sigue significando productos conocidos al corte; nuevos SKU/desconocidos conservan su reporte aparte.

Definir previamente como criterio primario de desarrollo para SKU el WAPE de cantidad acumulada en el bloque semanal en cohorte primaria/universo común; justificarlo por reposición y declarar que difiere de la regla diaria de referencia T05. Conservar métricas diarias, RMSE, sesgo, error por fold y cobertura. Para categoría fijar criterio primario diario y reportar igualmente el bloque semanal. No cambiar criterios después de ver resultados. No promediar porcentajes sin pesos ni comparar modelos con distintos targets como si fueran iguales.

Un modelo ML que no supere la mejor referencia comparable no se declara ganador. Reportar mejoras/retrocesos relativos, número de folds favorables y sesgo. Mantener cero como control: una predicción permanentemente nula no implica una política de compra válida. Si no hay ventaja estable, proponer mantener el baseline más sólido para la simulación y registrar que el ML no confirmó mejora en desarrollo.

No forzar MAPE<15% ni R²>0,85. MAPE solo sobre reales positivos con cobertura y ceros excluidos; WAPE con denominador válido. Etiquetar razones y porcentajes sin ambigüedad. Preservar resultados desfavorables.

## 4 Artefactos y evidencia

Predicciones/datasets/modelos entrenados bajo artifacts/private/t06/, ignorados por Git. Versionar protocolo, configuración, métricas agregadas, reporte y manifiesto de hashes de código/config/datos/fuentes, seeds, versiones, tiempos y cobertura. La serialización solo carga artefactos confiables generados localmente. Guardar pipeline de transformación junto al modelo, no solo árboles desconectados de las features.

Preparar interfaz de inferencia reproducible desde un origen: recibe historia aprobada, produce siete fechas futuras y cantidades no negativas con modelo, corte y versión identificados. No redondear todavía a pedidos ni generar compras reales. Elegir el tratamiento de predicciones negativas con antelación, documentarlo y aplicarlo igual en todos los folds.

Probar guardado/carga e igualdad de predicciones. No usar datos sintéticos de inventario para entrenar demanda; las ventas reales y el escenario de stock tienen procedencias diferentes.

## 5 Pruebas y límites

Pruebas necesarias: cambiar datos posteriores al origen no cambia features/predicción emitida; etiquetas fuera de corte nunca entran; vocabulario e imputación solo de train; calendario no comprimido; ceros/ausentes/nuevos; mismo universo de T05; inferencia multihorizonte sin ventas futuras; serialización e identidad reproducible con seed. Ejecutar verificaciones pertinentes y una integración final. Logs completos en archivos y resumen breve; no repetir suites amplias varias veces sin cambios.

Si se necesita empezar con un solo fold para comprobar rendimiento técnico, hacerlo como prueba de ejecución y registrar que sus resultados ya son conocidos; después ejecutar los cinco con el protocolo fijado. El resultado completo requiere los cinco folds. No evaluar agosto ni cambiar el dataset reservado para superar una meta.

Mantener visible que la futura simulación de reposición puede necesitar cubrir lead time + revisión, superior a siete días. No extrapolar una validación de siete días a catorce o más sin definir y evaluar el horizonte correspondiente; esa decisión se cerrará al preparar T07.

## 6 Frente web acotado en paralelo

Angular ya está generado y compiló según T05. Un agente separado puede preparar navegación y estados de carga/sin datos/error para las pantallas previstas, con datos de demostración identificados o mocks de contrato. No mostrar métricas inventadas como resultados reales. Verificar compilación y las pruebas básicas de componentes. No ampliar este frente si interfiere con T06 o archivos compartidos; autenticación y API completa siguen en backlog.

## 7 Cierre de entrega

Actualizar ESTADO.md, TRASPASO.md y backlog. Comprometer cambios locales y entregar resumen breve con tarea, commit, pruebas ejecutadas/resultados, evidencias, bloqueos y próximo paso. Los logs extensos permanecen aparte. Presentar la propuesta de modelos/referencias por nivel y sus limitaciones para revisión de Codex.

Detenerse antes de congelar la selección final para agosto, evaluar el test final o declarar mejoras de inventario. La siguiente revisión decidirá preparación de T07 y apertura controlada del test en el momento apropiado.
