# T05 Protocolo de validación temporal y baselines (congelado antes de evaluar)

Fecha: 17/10/2026, America/Lima. Configuración versionada: `config/t05_config.json` (versión t05-1). Este documento y esa configuración se comprometen en Git **antes** de ejecutar la evaluación; cualquier cambio posterior se declara aquí como enmienda con su motivo. No se ha observado ningún resultado de T05 al redactarlo. Solo marzo-julio; agosto no se lee ni se evalúa (no se llama `load_final_test_sales`).

## Diseño

- Horizonte de siete días naturales; el pronóstico se emite una vez en el origen (fin de entrenamiento) y no se actualiza con ventas del bloque.
- Cinco folds no solapados con entrenamiento expansivo desde 01/03/2026:

| Fold | Corte de entrenamiento | Validación |
|---|---|---|
| F1 | 31/05 | 01–07/06 |
| F2 | 14/06 | 15–21/06 |
| F3 | 28/06 | 29/06–05/07 |
| F4 | 12/07 | 13–19/07 |
| F5 | 24/07 | 25–31/07 |

- En cada fold se regeneran, con la ruta aprobada (`load_fold`, fuentes aprobadas por corte, máscara, catálogo al corte con `start`=01/03), las ventas, el calendario, el catálogo, las series diarias y la población. No se usa ningún artefacto de T04 al 31/07.
- Días excluidos (03/04, 12/04, 07/06): fuera de entrenamiento y métricas, sin comprimir el calendario. F1 conserva siete fechas naturales pero solo seis evaluables (07/06 no). Un día no enmascarado sin ninguna línea en las fuentes tampoco es evaluable (no se convierte en cero).

## Métodos (deterministas, sin parámetros ajustados)

1. `cero`: control; ganar por abundancia de ceros no demuestra buena reposición.
2. `ultimo_dia`: último día utilizable (puede ser un cero observado); se registra su antigüedad.
3. `naive_semanal`: para t+h usa t+h−7 (dentro de entrenamiento para h=1..7). Si ese día no es utilizable (ausente/enmascarado/anterior a la primera observación) usa `promedio_28` como fallback predefinido y se cuenta; si tampoco existe, no disponible (NaN), nunca cero.
4. `promedio_28`: media de las observaciones utilizables de los 28 días naturales previos al origen (incluye ceros válidos; excluye ausentes y enmascarados), no el promedio de días con venta.

Las predicciones son no negativas por construcción y no se redondean a compras.

## Niveles, cohortes y universos

- Niveles: SKU-almacén y categoría (categoría definida al corte; SKU nuevo ⇒ DESCONOCIDA). Los baselines de categoría se aplican directamente a su serie diaria (suma de unidades heterogéneas, no volumen físico); no equivalen a sumar pronósticos por SKU y no se les exige igualdad.
- Cohorte primaria (fijada solo con entrenamiento, igual para los cuatro métodos): conocidos al origen con ≥56 días naturales de historia desde su primera venta y ≥21 observaciones utilizables en los últimos 28 días. Se evalúan los 7 días de todos esos productos, hayan vendido o no.
- Historia corta: conocidos al origen que no cumplen el criterio; se reportan aparte, con la disponibilidad de cada método.
- Nuevos en validación: sin historia al origen; no se pronostican ni se les inventa historia; se reportan unidades y filas excluidas por fold.
- Universo común: filas donde los cuatro métodos tienen predicción. Los rankings solo se hacen en el universo común; además se informa la cobertura de cada método.

## Métricas

Por fold, método, nivel, cohorte y universo, más agregado ponderado sumando estadísticos (no promedio de porcentajes): MAE, RMSE, WAPE (suma real > 0), sesgo acumulado (predicho − observado), proporción de sub/sobre/exacto, MAPE solo con reales positivos con su cobertura y número de ceros excluidos, R² solo con n ≥ 30 y varianza positiva (si no, indefinido). Dos vistas: error diario y error de cantidad acumulada a siete días por entidad (con días evaluables por bloque; los bloques con días no evaluables suman solo los evaluables, de ambos lados).

## Referencia para T06

Regla fijada ahora: el baseline distinto de cero con menor WAPE agregado (diario, SKU, cohorte primaria, universo común); si el siguiente queda a menos de 1 % relativo se elige el más simple (orden `promedio_28`, `ultimo_dia`, `naive_semanal`). El resultado es descriptivo: no afirma mejora de inventario y se conserva el control cero y cualquier resultado desfavorable.

## Límites declarados

Un único almacén y unidad; cinco folds de una semana (varianza alta, un solo patrón estacional corto); ventas observadas posiblemente censuradas por stock; el catálogo y la cohorte dependen del corte; WAPE diario por SKU está dominado por la intermitencia.

## Enmiendas

Ninguna al momento de la congelación.
