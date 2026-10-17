# Revisión de T05

Fecha: 17/10/2026. Entrega revisada: dff7d27 y sus antecedentes desde 4cd837a. Resultado: T05 aceptado; puede ejecutarse ETAPA_04_CLAUDE.md para T06. No abrir agosto todavía.

## Verificación acotada

Se revisaron protocolo y configuración, commits previos a evaluación, implementación de baselines, orquestación temporal, métricas, pruebas y manifiesto de resultados. El árbol Git estaba limpio al comenzar. Los métodos reciben matrices limitadas al origen; las poblaciones, categorías y cohortes se reconstruyen por fold.

Codex ejecutó ocho pruebas puras de baselines/métricas y seis pruebas de integración sobre bases temporales: 14 aprobadas (0,04 y 3,04 segundos respectivamente). Análisis de estilo de los módulos/scripts T05 correcto. No se repitió la suite completa: el log guardado por Claude registra 83 aprobadas y un aviso, 70,62 segundos; ese resultado se distingue de las comprobaciones independientes del revisor.

Se verificaron hashes de configuración, código, archivo de predicciones y contenido descomprimido contra el manifiesto. Se recorrieron las 125 391 filas de predicciones, sin objetivos en agosto ni claves repetidas por fold/nivel/entidad/fecha. Se recalcularon independientemente n, MAE, RMSE, WAPE y sesgo de 24 grupos agregados no vacíos del universo común, tanto diario como por bloque; coinciden con T05_METRICAS.json. No se volvió a generar toda la evaluación.

Los cuatro detalles menores de reutilización de T04 están implementados: ventana/máscara en catálogo, unidad en fingerprint, precisión de céntimos y estado SIN_REGISTROS_DIA documentado/conservado. Los avisos de deprecación y pruebas Angular no ejecutadas no invalidan T05; no se declara completa la interfaz.

## Interpretación que debe conservar T06

La selección ultimo_dia cumple la regla preregistrada entre candidatos distintos de cero. No es el mejor método global incluyendo el control cero: WAPE diario por SKU 1,4309 frente a 1,0000. El promedio de 28 días tiene WAPE de bloque 0,9921, apenas inferior al control cero. En categorías los baselines son más sólidos: WAPE diario alrededor de 0,40–0,44 y de bloque alrededor de 0,20–0,32. Son resultados de desarrollo sobre cinco ventanas, no resultados independientes de agosto ni impacto en inventarios.

Predicción cero tiene sesgo acumulado de −23 026 unidades en el universo primario SKU. No convertir su competitividad con error absoluto diario en recomendación de no comprar. Mantenerlo como control y comparar también volumen semanal, sesgo y, más adelante, servicio/costos en la simulación.

Reportar WAPE/MAPE con unidades explícitas: 1,4309 como razón equivale a 143,09%; no a 1,43%. Las tablas actuales los presentan como razones. Mantener ese convenio o etiquetar conversión a porcentaje.

Las categorías se evalúan sobre productos conocidos al corte; unidades de nuevos SKU se reportan como desconocidas y quedan fuera de la comparación primaria. Por tanto, esas métricas no describen sin matices la demanda total de toda la categoría. Preservar cobertura y el objetivo de productos conocidos al comparar ML; no cambiar targets para producir una mejora aparente.

## Decisiones para la siguiente entrega

Modelos acotados: Random Forest y un boosting, con parámetros fijos antes de ejecutar y presupuesto de cómputo explícito. Mantener los folds de T05 y comparar todos los baselines sobre el mismo universo. Entrenar modelos globales por nivel cuando sea apropiado, evitando miles de modelos por producto con poca historia.

La valoración primaria para SKU puede centrarse en volumen del bloque semanal por su uso de reposición, con el cambio de criterio declarado antes de evaluar T06, conservando todas las métricas diarias y resultados T05. En categoría se conserva también error diario y semanal. Ningún modelo se declara superior por cambiar cobertura o descartar ceros. No afirmar umbrales MAPE/R² cumplidos antes de medir.

Si ningún modelo aporta mejora, registrar el resultado y conservar el baseline validado como candidato operativo. Un resultado científico desfavorable no autoriza inventar desempeño. La selección final y apertura de agosto se revisarán después de T06.
