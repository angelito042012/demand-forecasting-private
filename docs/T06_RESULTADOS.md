# T06 Resultados: ML frente a baselines (marzo-julio 2026, desarrollo)

Generado el 2026-10-17 10:50 (America/Lima). Protocolo congelado en 286017d (config sha256 `c674f65117cb`). Solo marzo-julio; agosto no se leyó. **Estos folds son de desarrollo: los baselines de T05 ya se habían observado; no es una prueba final independiente.** WAPE y MAPE son razones (1,00 = 100 %). No se declara mejora de inventario.

## Resumen de selección (regla preregistrada)

### sku (criterio primario: WAPE bloque7, cohorte primaria, universo común, agregado de 5 folds)

| Método | WAPE | Mejora relativa vs mejor referencia | Folds favorables | Sesgo/obs. | Cumple regla |
|---|---|---|---|---|---|
| cero (baseline) | 1.0000 | - | - | - | - |
| ultimo_dia (baseline) | 1.3118 | - | - | - | - |
| naive_semanal (baseline) | 1.0568 | - | - | - | - |
| promedio_28 (baseline) | 0.9921 | - | - | - | - |
| random_forest | 1.0584 | -0.0668 | 1/5 (F2) | 0.278 | no |
| xgboost | 1.0174 | -0.0255 | 2/5 (F2, F5) | 0.121 | no |

- Mejor referencia (incluye cero): **promedio_28**; mejor referencia no nula: **promedio_28**.
- Ganador ML: **ninguno**. Propuesta provisional para la simulación: **promedio_28**. sin ventaja estable de ML en desarrollo: se propone el baseline no nulo mas solido; el control cero se mantiene solo como referencia.

### categoria (criterio primario: WAPE diaria, cohorte primaria, universo común, agregado de 5 folds)

| Método | WAPE | Mejora relativa vs mejor referencia | Folds favorables | Sesgo/obs. | Cumple regla |
|---|---|---|---|---|---|
| cero (baseline) | 1.0000 | - | - | - | - |
| ultimo_dia (baseline) | 0.4318 | - | - | - | - |
| naive_semanal (baseline) | 0.4433 | - | - | - | - |
| promedio_28 (baseline) | 0.4025 | - | - | - | - |
| random_forest | 0.3941 | 0.0207 | 3/5 (F3, F4, F5) | 0.133 | sí |
| xgboost | 0.4370 | -0.0859 | 2/5 (F3, F4) | 0.132 | no |

- Mejor referencia (incluye cero): **promedio_28**; mejor referencia no nula: **promedio_28**.
- Ganador ML: **random_forest**. Propuesta provisional para la simulación: **random_forest**. ML supera la regla preregistrada en desarrollo.

## SKU-almacén: cohorte primaria, universo común, cantidad acumulada a 7 días, agregado de 5 folds

| Método | n | MAE | RMSE | WAPE (razón) | Sesgo (pred−obs) | Sub / Sobre / Exacto | MAPE razón (cobertura; ceros excl.) | R² |
|---|---|---|---|---|---|---|---|---|
| cero | 15315 | 1.503 | 4.772 | 1.0000 | -23026.0 | 0.374 / 0.000 / 0.626 | 1.000 (0.374; 9588) | -0.110 |
| ultimo_dia | 15315 | 1.972 | 7.654 | 1.3118 | -4370.0 | 0.313 / 0.081 / 0.606 | 1.491 (0.374; 9588) | -1.856 |
| naive_semanal | 15315 | 1.589 | 5.888 | 1.0568 | 1717.0 | 0.226 / 0.229 / 0.546 | 1.044 (0.374; 9588) | -0.691 |
| promedio_28 | 15315 | 1.492 | 4.725 | 0.9921 | 1892.9 | 0.255 / 0.438 / 0.308 | 0.839 (0.374; 9588) | -0.089 |
| random_forest | 15315 | 1.591 | 4.432 | 1.0584 | 6410.9 | 0.227 / 0.773 / 0.000 | 0.766 (0.374; 9588) | 0.042 |
| xgboost | 15315 | 1.530 | 4.278 | 1.0174 | 2784.7 | 0.258 / 0.742 / 0.000 | 0.649 (0.374; 9588) | 0.108 |

## SKU-almacén: cohorte primaria, universo común, error diario, agregado de 5 folds

| Método | n | MAE | RMSE | WAPE (razón) | Sesgo (pred−obs) | Sub / Sobre / Exacto | MAPE razón (cobertura; ceros excl.) | R² |
|---|---|---|---|---|---|---|---|---|
| cero | 104533 | 0.220 | 1.350 | 1.0000 | -23026.0 | 0.103 / 0.000 / 0.897 | 1.000 (0.103; 93801) | -0.027 |
| ultimo_dia | 104533 | 0.315 | 1.606 | 1.4309 | -4370.0 | 0.084 / 0.072 / 0.845 | 0.914 (0.103; 93801) | -0.454 |
| naive_semanal | 104533 | 0.358 | 2.198 | 1.6272 | 1717.0 | 0.082 / 0.083 / 0.836 | 0.968 (0.103; 93801) | -1.723 |
| promedio_28 | 104533 | 0.338 | 1.348 | 1.5354 | 1892.9 | 0.093 / 0.568 / 0.339 | 0.789 (0.103; 93801) | -0.024 |
| random_forest | 104533 | 0.367 | 1.322 | 1.6657 | 6410.9 | 0.092 / 0.908 / 0.000 | 0.762 (0.103; 93801) | 0.015 |
| xgboost | 104533 | 0.350 | 1.317 | 1.5900 | 2784.7 | 0.094 / 0.906 / 0.000 | 0.785 (0.103; 93801) | 0.023 |

## Categoría (productos conocidos al corte): cohorte primaria, universo común, cantidad acumulada a 7 días, agregado de 5 folds

| Método | n | MAE | RMSE | WAPE (razón) | Sesgo (pred−obs) | Sub / Sobre / Exacto | MAPE razón (cobertura; ceros excl.) | R² |
|---|---|---|---|---|---|---|---|---|
| cero | 180 | 141.178 | 360.464 | 1.0000 | -25412.0 | 0.861 / 0.000 / 0.139 | 1.000 (0.861; 25) | -0.181 |
| ultimo_dia | 180 | 44.867 | 117.272 | 0.3178 | -4122.0 | 0.567 / 0.278 / 0.156 | 0.509 (0.861; 25) | 0.875 |
| naive_semanal | 180 | 28.378 | 67.453 | 0.2010 | 2052.0 | 0.350 / 0.506 / 0.144 | 0.448 (0.861; 25) | 0.959 |
| promedio_28 | 180 | 28.491 | 63.608 | 0.2018 | 1943.5 | 0.350 / 0.583 / 0.067 | 0.542 (0.861; 25) | 0.963 |
| random_forest | 180 | 30.651 | 69.159 | 0.2171 | 3380.4 | 0.272 / 0.728 / 0.000 | 0.618 (0.861; 25) | 0.957 |
| xgboost | 180 | 39.305 | 93.949 | 0.2784 | 3349.2 | 0.278 / 0.722 / 0.000 | 0.670 (0.861; 25) | 0.920 |

## Categoría (productos conocidos al corte): cohorte primaria, universo común, error diario, agregado de 5 folds

| Método | n | MAE | RMSE | WAPE (razón) | Sesgo (pred−obs) | Sub / Sobre / Exacto | MAPE razón (cobertura; ceros excl.) | R² |
|---|---|---|---|---|---|---|---|---|
| cero | 1224 | 20.761 | 56.298 | 1.0000 | -25412.0 | 0.743 / 0.000 / 0.257 | 1.000 (0.743; 315) | -0.157 |
| ultimo_dia | 1224 | 8.964 | 25.806 | 0.4318 | -4122.0 | 0.413 / 0.324 / 0.262 | 0.768 (0.743; 315) | 0.757 |
| naive_semanal | 1224 | 9.203 | 24.132 | 0.4433 | 2052.0 | 0.357 / 0.398 / 0.245 | 1.039 (0.743; 315) | 0.787 |
| promedio_28 | 1224 | 8.356 | 21.365 | 0.4025 | 1943.5 | 0.310 / 0.615 / 0.074 | 0.881 (0.743; 315) | 0.833 |
| random_forest | 1224 | 8.183 | 19.970 | 0.3941 | 3380.4 | 0.281 / 0.719 / 0.000 | 0.954 (0.743; 315) | 0.854 |
| xgboost | 1224 | 9.073 | 22.318 | 0.4370 | 3349.2 | 0.282 / 0.712 / 0.006 | 0.944 (0.743; 315) | 0.818 |

## WAPE por fold (sku, bloque7, primaria, común)

| Fold | cero | ultimo_dia | naive_semanal | promedio_28 | random_forest | xgboost |
|---|---|---|---|---|---|---|
| F1 | 1.000 | 1.272 | 1.106 | 1.014 | 1.125 | 1.034 |
| F2 | 1.000 | 1.288 | 1.169 | 1.186 | 1.172 | 1.151 |
| F3 | 1.000 | 1.184 | 1.007 | 0.957 | 1.038 | 1.032 |
| F4 | 1.000 | 1.333 | 1.044 | 0.902 | 0.967 | 0.962 |
| F5 | 1.000 | 1.470 | 0.979 | 0.930 | 1.015 | 0.929 |

## WAPE por fold (categoria, diaria, primaria, común)

| Fold | cero | ultimo_dia | naive_semanal | promedio_28 | random_forest | xgboost |
|---|---|---|---|---|---|---|
| F1 | 1.000 | 0.441 | 0.481 | 0.464 | 0.473 | 0.581 |
| F2 | 1.000 | 0.529 | 0.498 | 0.451 | 0.479 | 0.500 |
| F3 | 1.000 | 0.381 | 0.375 | 0.341 | 0.322 | 0.338 |
| F4 | 1.000 | 0.368 | 0.443 | 0.351 | 0.337 | 0.350 |
| F5 | 1.000 | 0.454 | 0.431 | 0.420 | 0.382 | 0.444 |

## SKU historia corta (universo propio, error diario, agregado)

| Método | n | MAE | RMSE | WAPE (razón) | Sesgo (pred−obs) | Sub / Sobre / Exacto | MAPE razón (cobertura; ceros excl.) | R² |
|---|---|---|---|---|---|---|---|---|
| cero | 16251 | 0.147 | 1.003 | 1.0000 | -2386.0 | 0.061 / 0.000 / 0.939 | 1.000 (0.061; 15264) | -0.022 |
| ultimo_dia | 16251 | 0.238 | 1.218 | 1.6186 | 248.0 | 0.050 / 0.057 / 0.892 | 0.961 (0.061; 15264) | -0.508 |
| naive_semanal | 16251 | 0.263 | 1.296 | 1.7903 | 857.3 | 0.049 / 0.101 / 0.850 | 0.909 (0.061; 15264) | -0.707 |
| promedio_28 | 16251 | 0.288 | 0.914 | 1.9643 | 1477.4 | 0.055 / 0.691 / 0.255 | 0.771 (0.061; 15264) | 0.151 |
| random_forest | 16251 | 0.244 | 0.873 | 1.6634 | 483.7 | 0.057 / 0.943 / 0.000 | 0.813 (0.061; 15264) | 0.225 |
| xgboost | 16251 | 0.268 | 0.906 | 1.8231 | 827.1 | 0.058 / 0.942 / 0.000 | 0.815 (0.061; 15264) | 0.165 |

## Cómputo y entrenamiento

| Fold | Nivel | Modelo | Filas | Features | Orígenes | Ajuste (s) | Matriz (MB) | Negativos recortados |
|---|---|---|---|---|---|---|---|---|
| F1 | sku | random_forest | 403590 | 24 | 20 | 39.51 | 38.7 | 0 |
| F1 | sku | xgboost | 403590 | 24 | 20 | 3.15 | 38.7 | 5 |
| F1 | categoria | random_forest | 4896 | 24 | 20 | 0.36 | 0.5 | 0 |
| F1 | categoria | xgboost | 4896 | 24 | 20 | 0.12 | 0.5 | 0 |
| F2 | sku | random_forest | 492788 | 24 | 24 | 49.97 | 47.3 | 0 |
| F2 | sku | xgboost | 492788 | 24 | 24 | 3.54 | 47.3 | 2 |
| F2 | categoria | random_forest | 5796 | 24 | 24 | 0.42 | 0.6 | 0 |
| F2 | categoria | xgboost | 5796 | 24 | 24 | 0.13 | 0.6 | 6 |
| F3 | sku | random_forest | 610940 | 24 | 29 | 64.3 | 58.7 | 0 |
| F3 | sku | xgboost | 610940 | 24 | 29 | 4.35 | 58.7 | 3 |
| F3 | categoria | random_forest | 7056 | 24 | 29 | 0.54 | 0.7 | 0 |
| F3 | categoria | xgboost | 7056 | 24 | 29 | 0.14 | 0.7 | 0 |
| F4 | sku | random_forest | 736195 | 24 | 34 | 79.18 | 70.7 | 0 |
| F4 | sku | xgboost | 736195 | 24 | 34 | 5.27 | 70.7 | 2 |
| F4 | categoria | random_forest | 8352 | 24 | 34 | 0.62 | 0.8 | 0 |
| F4 | categoria | xgboost | 8352 | 24 | 34 | 0.14 | 0.8 | 1 |
| F5 | sku | random_forest | 838570 | 24 | 38 | 91.06 | 80.5 | 0 |
| F5 | sku | xgboost | 838570 | 24 | 38 | 5.87 | 80.5 | 2 |
| F5 | categoria | random_forest | 9360 | 24 | 38 | 0.76 | 0.9 | 0 |
| F5 | categoria | xgboost | 9360 | 24 | 38 | 0.15 | 0.9 | 0 |

Tiempo total de la ejecución completa: 417 s. Repetición de F1 equivalente (tolerancia 1e-9): True (diferencia máxima 1.14e-13). Baselines idénticos a T05: True.

## Limitaciones

- Folds de desarrollo ya observados; la apertura de agosto y la selección final se deciden tras la revisión.
- Sin feature de precio (no incorporado). Un almacén, una unidad base, ventas posiblemente censuradas por stock.
- Horizonte de 7 días: la simulación puede necesitar lead time + revisión mayores; no se extrapola a 14 días.
- Categoría = productos conocidos al corte; las unidades de SKU nuevos quedan fuera (ver T05).
