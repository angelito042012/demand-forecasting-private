# T05 Resultados de baselines (marzo-julio 2026)

Generado el 2026-10-17 08:27 (America/Lima) con el protocolo congelado (config sha256 `9dd450a6dafb`, commit del protocolo d763bed). Solo marzo-julio; agosto no se leyó. Cifras agregadas por scripts/run_t05.py; predicciones fila a fila en artifacts/private/t05/.

Advertencia: el control `cero` puede parecer competitivo por la abundancia de ceros; ganar una métrica no demuestra buena reposición ni mejora de inventario. Unidades de categoría = suma de unidades base heterogéneas.

## Folds y días evaluables

| Fold | Corte | Validación | Días evaluables | No evaluables | Fingerprint |
|---|---|---|---|---|---|
| F1 | 2026-05-31 | 2026-06-01…2026-06-07 | 6/7 | ['2026-06-07'] | `9fa7f64e61d6` |
| F2 | 2026-06-14 | 2026-06-15…2026-06-21 | 7/7 | - | `5bcca4c1be49` |
| F3 | 2026-06-28 | 2026-06-29…2026-07-05 | 7/7 | - | `64b79cfb6213` |
| F4 | 2026-07-12 | 2026-07-13…2026-07-19 | 7/7 | - | `590ec26ce58f` |
| F5 | 2026-07-24 | 2026-07-25…2026-07-31 | 7/7 | - | `d31225df74d2` |

## SKU-almacén: cohorte primaria, universo común, error diario, agregado de los 5 folds

| Método | n filas | MAE | RMSE | WAPE | Sesgo (pred−obs) | Sub / Sobre / Exacto | MAPE (cobertura; ceros excl.) | R² |
|---|---|---|---|---|---|---|---|---|
| cero | 104533 | 0.220 | 1.350 | 1.000 | -23026.0 | 0.103 / 0.000 / 0.897 | 1.000 (0.103; 93801) | -0.027 |
| ultimo_dia | 104533 | 0.315 | 1.606 | 1.431 | -4370.0 | 0.084 / 0.072 / 0.845 | 0.914 (0.103; 93801) | -0.454 |
| naive_semanal | 104533 | 0.358 | 2.198 | 1.627 | 1717.0 | 0.082 / 0.083 / 0.836 | 0.968 (0.103; 93801) | -1.723 |
| promedio_28 | 104533 | 0.338 | 1.348 | 1.535 | 1892.9 | 0.093 / 0.568 / 0.339 | 0.789 (0.103; 93801) | -0.024 |

## SKU-almacén: cohorte primaria, universo común, cantidad acumulada a 7 días (por entidad, días evaluables), agregado de los 5 folds

| Método | n filas | MAE | RMSE | WAPE | Sesgo (pred−obs) | Sub / Sobre / Exacto | MAPE (cobertura; ceros excl.) | R² |
|---|---|---|---|---|---|---|---|---|
| cero | 15315 | 1.503 | 4.772 | 1.000 | -23026.0 | 0.374 / 0.000 / 0.626 | 1.000 (0.374; 9588) | -0.110 |
| ultimo_dia | 15315 | 1.972 | 7.654 | 1.312 | -4370.0 | 0.313 / 0.081 / 0.606 | 1.491 (0.374; 9588) | -1.856 |
| naive_semanal | 15315 | 1.589 | 5.888 | 1.057 | 1717.0 | 0.226 / 0.229 / 0.546 | 1.044 (0.374; 9588) | -0.691 |
| promedio_28 | 15315 | 1.492 | 4.725 | 0.992 | 1892.9 | 0.255 / 0.438 / 0.308 | 0.839 (0.374; 9588) | -0.089 |

## Categoría: cohorte primaria, universo común, error diario, agregado de los 5 folds

| Método | n filas | MAE | RMSE | WAPE | Sesgo (pred−obs) | Sub / Sobre / Exacto | MAPE (cobertura; ceros excl.) | R² |
|---|---|---|---|---|---|---|---|---|
| cero | 1224 | 20.761 | 56.298 | 1.000 | -25412.0 | 0.743 / 0.000 / 0.257 | 1.000 (0.743; 315) | -0.157 |
| ultimo_dia | 1224 | 8.964 | 25.806 | 0.432 | -4122.0 | 0.413 / 0.324 / 0.262 | 0.768 (0.743; 315) | 0.757 |
| naive_semanal | 1224 | 9.203 | 24.132 | 0.443 | 2052.0 | 0.357 / 0.398 / 0.245 | 1.039 (0.743; 315) | 0.787 |
| promedio_28 | 1224 | 8.356 | 21.365 | 0.402 | 1943.5 | 0.310 / 0.615 / 0.074 | 0.881 (0.743; 315) | 0.833 |

## Categoría: cohorte primaria, universo común, cantidad acumulada a 7 días (por entidad, días evaluables), agregado de los 5 folds

| Método | n filas | MAE | RMSE | WAPE | Sesgo (pred−obs) | Sub / Sobre / Exacto | MAPE (cobertura; ceros excl.) | R² |
|---|---|---|---|---|---|---|---|---|
| cero | 180 | 141.178 | 360.464 | 1.000 | -25412.0 | 0.861 / 0.000 / 0.139 | 1.000 (0.861; 25) | -0.181 |
| ultimo_dia | 180 | 44.867 | 117.272 | 0.318 | -4122.0 | 0.567 / 0.278 / 0.156 | 0.509 (0.861; 25) | 0.875 |
| naive_semanal | 180 | 28.378 | 67.453 | 0.201 | 2052.0 | 0.350 / 0.506 / 0.144 | 0.448 (0.861; 25) | 0.959 |
| promedio_28 | 180 | 28.491 | 63.608 | 0.202 | 1943.5 | 0.350 / 0.583 / 0.067 | 0.542 (0.861; 25) | 0.963 |

## WAPE diario SKU primaria (universo común) por fold

| Fold | cero | ultimo_dia | naive_semanal | promedio_28 |
|---|---|---|---|---|
| F1 | 1.000 | 1.366 | 1.613 | 1.574 |
| F2 | 1.000 | 1.403 | 1.704 | 1.727 |
| F3 | 1.000 | 1.310 | 1.521 | 1.468 |
| F4 | 1.000 | 1.434 | 1.642 | 1.434 |
| F5 | 1.000 | 1.627 | 1.663 | 1.505 |

## SKU: historia corta (universo propio, error diario, agregado)

| Método | n filas | MAE | RMSE | WAPE | Sesgo (pred−obs) | Sub / Sobre / Exacto | MAPE (cobertura; ceros excl.) | R² |
|---|---|---|---|---|---|---|---|---|
| cero | 16251 | 0.147 | 1.003 | 1.000 | -2386.0 | 0.061 / 0.000 / 0.939 | 1.000 (0.061; 15264) | -0.022 |
| ultimo_dia | 16251 | 0.238 | 1.218 | 1.619 | 248.0 | 0.050 / 0.057 / 0.892 | 0.961 (0.061; 15264) | -0.508 |
| naive_semanal | 16251 | 0.263 | 1.296 | 1.790 | 857.3 | 0.049 / 0.101 / 0.850 | 0.909 (0.061; 15264) | -0.707 |
| promedio_28 | 16251 | 0.288 | 0.914 | 1.964 | 1477.4 | 0.055 / 0.691 / 0.255 | 0.771 (0.061; 15264) | 0.151 |

## Cobertura por fold

| Fold | Nivel | Cohorte | Entidades | Filas objetivo | Filas comunes | Fallback naive (filas) | Antigüedad último día (mediana/p90/max) |
|---|---|---|---|---|---|---|---|
| F1 | sku | primaria | 2672 | 16032 | 16032 | 0 | 0/0/0 |
| F1 | sku | historia_corta | 675 | 4050 | 4050 | 109 | 0/0/0 |
| F1 | categoria | primaria | 36 | 216 | 216 | 0 | 0/0/0 |
| F1 | categoria | historia_corta | 0 | 0 | 0 | 0 | - |
| F2 | sku | primaria | 2914 | 20398 | 20398 | 0 | 0/0/0 |
| F2 | sku | historia_corta | 536 | 3752 | 3752 | 148 | 0/0/0 |
| F2 | categoria | primaria | 36 | 252 | 252 | 0 | 0/0/0 |
| F2 | categoria | historia_corta | 0 | 0 | 0 | 0 | - |
| F3 | sku | primaria | 3121 | 21847 | 21847 | 0 | 0/0/0 |
| F3 | sku | historia_corta | 428 | 2996 | 2996 | 133 | 0/0/0 |
| F3 | categoria | primaria | 36 | 252 | 252 | 0 | 0/0/0 |
| F3 | categoria | historia_corta | 0 | 0 | 0 | 0 | - |
| F4 | sku | primaria | 3267 | 22869 | 22869 | 0 | 0/0/0 |
| F4 | sku | historia_corta | 391 | 2737 | 2737 | 166 | 0/0/0 |
| F4 | categoria | primaria | 36 | 252 | 252 | 0 | 0/0/0 |
| F4 | categoria | historia_corta | 0 | 0 | 0 | 0 | - |
| F5 | sku | primaria | 3341 | 23387 | 23387 | 0 | 0/0/0 |
| F5 | sku | historia_corta | 388 | 2716 | 2716 | 120 | 0/0/0 |
| F5 | categoria | primaria | 36 | 252 | 252 | 0 | 0/0/0 |
| F5 | categoria | historia_corta | 0 | 0 | 0 | 0 | - |

## Nuevos en validación (sin historia al origen; sin predicción)

| Fold | SKU-almacén nuevos | Unidades evaluables | Categorías no conocidas | Unidades (categoría) |
|---|---|---|---|---|
| F1 | 54 | 124 | ['DESCONOCIDA'] | 124 |
| F2 | 56 | 172 | ['DESCONOCIDA'] | 172 |
| F3 | 57 | 113 | ['DESCONOCIDA'] | 113 |
| F4 | 41 | 67 | ['DESCONOCIDA'] | 67 |
| F5 | 29 | 46 | ['DESCONOCIDA'] | 46 |

## Referencia para T06 (regla fijada en el protocolo)

- Selección: **ultimo_dia**; WAPE agregado (SKU, primaria, común, diario): {'ultimo_dia': 1.430904195257535, 'naive_semanal': 1.6272474593937287, 'promedio_28': 1.5354301578569798}; control cero: 1.0; dentro del umbral de empate: ['ultimo_dia'].
- Límites: cinco semanas de validación, un solo almacén, ventas posiblemente censuradas por stock, WAPE diario dominado por intermitencia. No confirma mejora del inventario; sirve solo como referencia mínima para comparar ML en T06.

## Lectura automática frente al control cero (WAPE agregado, primaria, universo común)

- sku, diaria: métodos con WAPE menor que el control cero: ninguno (WAPE: {'cero': 1.0, 'ultimo_dia': 1.431, 'naive_semanal': 1.627, 'promedio_28': 1.535}).
- sku, bloque7: métodos con WAPE menor que el control cero: ['promedio_28'] (WAPE: {'cero': 1.0, 'ultimo_dia': 1.312, 'naive_semanal': 1.057, 'promedio_28': 0.992}).
- categoria, diaria: métodos con WAPE menor que el control cero: ['ultimo_dia', 'naive_semanal', 'promedio_28'] (WAPE: {'cero': 1.0, 'ultimo_dia': 0.432, 'naive_semanal': 0.443, 'promedio_28': 0.402}).
- categoria, bloque7: métodos con WAPE menor que el control cero: ['ultimo_dia', 'naive_semanal', 'promedio_28'] (WAPE: {'cero': 1.0, 'ultimo_dia': 0.318, 'naive_semanal': 0.201, 'promedio_28': 0.202}).
- La cohorte primaria cuenta los ceros observados como observaciones utilizables (definición del protocolo); por eso la antigüedad del último día utilizable es casi siempre 0 y la cohorte incluye productos que venden pocos días.
