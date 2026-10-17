# T12 Resultados: evaluación final de agosto bajo selección congelada

**Inventario simulado con supuestos; no corresponde al inventario real de la empresa.** Generado el 2026-10-17T18:12:23-05:00 (America/Lima). Selección congelada: `config/seleccion_congelada.json` (sha256 `8a9138059391f2b80b9a944b2ee25803cd1e54fe9b359b2dfec0a840f759ef8d`), sin cambios. Predicciones iniciales selladas antes de leer agosto (sello `d587255d87fb2d99e449a098e4c1fa6e1c1c6d5838180b7aa8fe098e9a2ce663`). Un solo bloque (01–21/08, origen 31/07); **no hay umbrales prometidos** y los resultados desfavorables y el control cero se conservan. No demuestra impacto en inventario real de la empresa.

## Hallazgo primario

WAPE acumulado H=14, SKU-almacén, cohorte primaria, universo común (n=3401): **promedio_28 0.7810**, RF categoría distribuido 0.7910, control cero 1.0000. Mejora relativa de RF frente a promedio_28: -0.0129 (positiva = RF mejor). Sesgo/observado: RF 0.030, promedio_28 0.020 (referencia |sesgo|/obs ≤ 0,25). no aplicable: un solo bloque; RF no puede declararse ganador por la prueba final. El método operativo no se modifica por este resultado.

### SKU-almacén: primaria, universo común, acum10

| Método | n | MAE | RMSE | WAPE | Sesgo (pred−obs) | Unidades obs. | Sub/Sobre | MAPE (cobertura de reales > 0) | R² |
|---|---|---|---|---|---|---|---|---|---|
| cero | 3401 | 2.289 | 7.808 | 1.0000 | -7784.0 | 7784 | 0.428/0.000 | 1.0000 (0.428) | -0.094 |
| promedio_28 | 3401 | 1.869 | 6.233 | 0.8165 | -227.9 | 7784 | 0.279/0.378 | 0.8505 (0.428) | 0.303 |
| rf_distribuido | 3401 | 1.901 | 6.274 | 0.8308 | 5.9 | 7784 | 0.274/0.386 | 0.8715 (0.428) | 0.294 |

### SKU-almacén: primaria, universo común, acum14

| Método | n | MAE | RMSE | WAPE | Sesgo (pred−obs) | Unidades obs. | Sub/Sobre | MAPE (cobertura de reales > 0) | R² |
|---|---|---|---|---|---|---|---|---|---|
| cero | 3401 | 3.048 | 9.356 | 1.0000 | -10366.0 | 10366 | 0.485/0.000 | 1.0000 (0.485) | -0.119 |
| promedio_28 | 3401 | 2.380 | 7.288 | 0.7810 | 212.5 | 10366 | 0.305/0.358 | 0.9599 (0.485) | 0.321 |
| rf_distribuido | 3401 | 2.411 | 7.342 | 0.7910 | 311.6 | 10366 | 0.300/0.372 | 0.9709 (0.485) | 0.311 |

### SKU-almacén: primaria, universo común, acum21

| Método | n | MAE | RMSE | WAPE | Sesgo (pred−obs) | Unidades obs. | Sub/Sobre | MAPE (cobertura de reales > 0) | R² |
|---|---|---|---|---|---|---|---|---|---|
| cero | 3401 | 4.346 | 11.971 | 1.0000 | -14781.0 | 14781 | 0.543/0.000 | 1.0000 (0.543) | -0.152 |
| promedio_28 | 3401 | 3.265 | 9.065 | 0.7512 | 1086.8 | 14781 | 0.316/0.368 | 1.0417 (0.543) | 0.340 |
| rf_distribuido | 3401 | 3.299 | 9.128 | 0.7590 | 1123.2 | 14781 | 0.310/0.376 | 1.0518 (0.543) | 0.330 |

### SKU-almacén: primaria, universo común, diaria

| Método | n | MAE | RMSE | WAPE | Sesgo (pred−obs) | Unidades obs. | Sub/Sobre | MAPE (cobertura de reales > 0) | R² |
|---|---|---|---|---|---|---|---|---|---|
| cero | 71421 | 0.207 | 1.432 | 1.0000 | -14781.0 | 14781 | 0.097/0.000 | 1.0000 (0.097) | -0.021 |
| promedio_28 | 71421 | 0.311 | 1.383 | 1.5048 | 1086.8 | 14781 | 0.088/0.531 | 0.7591 (0.097) | 0.048 |
| rf_distribuido | 71421 | 0.311 | 1.383 | 1.5009 | 1123.2 | 14781 | 0.087/0.533 | 0.7606 (0.097) | 0.047 |

### SKU-almacén: historia_corta, universo común, acum10

| Método | n | MAE | RMSE | WAPE | Sesgo (pred−obs) | Unidades obs. | Sub/Sobre | MAPE (cobertura de reales > 0) | R² |
|---|---|---|---|---|---|---|---|---|---|
| cero | 357 | 2.062 | 8.001 | 1.0000 | -736.0 | 736 | 0.339/0.000 | 1.0000 (0.339) | -0.071 |
| promedio_28 | 357 | 2.107 | 4.309 | 1.0218 | 261.5 | 736 | 0.204/0.585 | 0.9117 (0.339) | 0.689 |
| rf_distribuido | 357 | 1.600 | 3.573 | 0.7761 | 30.5 | 736 | 0.246/0.546 | 0.6988 (0.339) | 0.786 |

### SKU-almacén: historia_corta, universo común, acum14

| Método | n | MAE | RMSE | WAPE | Sesgo (pred−obs) | Unidades obs. | Sub/Sobre | MAPE (cobertura de reales > 0) | R² |
|---|---|---|---|---|---|---|---|---|---|
| cero | 357 | 2.667 | 10.055 | 1.0000 | -952.0 | 952 | 0.378/0.000 | 1.0000 (0.378) | -0.076 |
| promedio_28 | 357 | 2.831 | 5.956 | 1.0618 | 444.5 | 952 | 0.218/0.585 | 1.0558 (0.378) | 0.623 |
| rf_distribuido | 357 | 2.136 | 4.936 | 0.8009 | 101.9 | 952 | 0.277/0.527 | 0.7791 (0.378) | 0.741 |

### SKU-almacén: historia_corta, universo común, acum21

| Método | n | MAE | RMSE | WAPE | Sesgo (pred−obs) | Unidades obs. | Sub/Sobre | MAPE (cobertura de reales > 0) | R² |
|---|---|---|---|---|---|---|---|---|---|
| cero | 357 | 3.594 | 13.651 | 1.0000 | -1283.0 | 1283 | 0.434/0.000 | 1.0000 (0.434) | -0.074 |
| promedio_28 | 357 | 4.067 | 9.114 | 1.1316 | 811.7 | 1283 | 0.218/0.599 | 1.4439 (0.434) | 0.521 |
| rf_distribuido | 357 | 2.954 | 7.449 | 0.8219 | 287.0 | 1283 | 0.283/0.535 | 0.9519 (0.434) | 0.680 |

### SKU-almacén: historia_corta, universo común, diaria

| Método | n | MAE | RMSE | WAPE | Sesgo (pred−obs) | Unidades obs. | Sub/Sobre | MAPE (cobertura de reales > 0) | R² |
|---|---|---|---|---|---|---|---|---|---|
| cero | 7497 | 0.171 | 0.963 | 1.0000 | -1283.0 | 1283 | 0.066/0.000 | 1.0000 (0.066) | -0.033 |
| promedio_28 | 7497 | 0.314 | 0.832 | 1.8323 | 811.7 | 1283 | 0.058/0.712 | 0.7586 (0.066) | 0.228 |
| rf_distribuido | 7497 | 0.253 | 0.794 | 1.4767 | 287.0 | 1283 | 0.059/0.712 | 0.8053 (0.066) | 0.298 |

### Categoría (promedio_28 = suma de pronósticos SKU): primaria, universo común, acum10

| Método | n | MAE | RMSE | WAPE | Sesgo (pred−obs) | Unidades obs. | Sub/Sobre | MAPE (cobertura de reales > 0) | R² |
|---|---|---|---|---|---|---|---|---|---|
| cero | 36 | 236.667 | 605.243 | 1.0000 | -8520.0 | 8520 | 0.889/0.000 | 1.0000 (0.889) | -0.181 |
| promedio_28 | 36 | 25.495 | 47.827 | 0.1077 | 30.7 | 8520 | 0.306/0.667 | 0.4292 (0.889) | 0.993 |
| rf_categoria | 36 | 26.784 | 47.619 | 0.1132 | 29.2 | 8520 | 0.250/0.750 | 0.4042 (0.889) | 0.993 |

### Categoría (promedio_28 = suma de pronósticos SKU): primaria, universo común, acum14

| Método | n | MAE | RMSE | WAPE | Sesgo (pred−obs) | Unidades obs. | Sub/Sobre | MAPE (cobertura de reales > 0) | R² |
|---|---|---|---|---|---|---|---|---|---|
| cero | 36 | 314.389 | 831.433 | 1.0000 | -11318.0 | 11318 | 0.889/0.000 | 1.0000 (0.889) | -0.167 |
| promedio_28 | 36 | 36.797 | 61.075 | 0.1170 | 653.0 | 11318 | 0.222/0.750 | 0.4187 (0.889) | 0.994 |
| rf_categoria | 36 | 36.664 | 58.189 | 0.1166 | 404.0 | 11318 | 0.250/0.750 | 0.3693 (0.889) | 0.994 |

### Categoría (promedio_28 = suma de pronósticos SKU): primaria, universo común, acum21

| Método | n | MAE | RMSE | WAPE | Sesgo (pred−obs) | Unidades obs. | Sub/Sobre | MAPE (cobertura de reales > 0) | R² |
|---|---|---|---|---|---|---|---|---|---|
| cero | 36 | 446.222 | 1179.137 | 1.0000 | -16064.0 | 16064 | 0.889/0.000 | 1.0000 (0.889) | -0.167 |
| promedio_28 | 36 | 68.700 | 126.151 | 0.1540 | 1892.5 | 16064 | 0.139/0.833 | 0.4149 (0.889) | 0.987 |
| rf_categoria | 36 | 59.097 | 94.697 | 0.1324 | 1396.7 | 16064 | 0.222/0.778 | 0.3781 (0.889) | 0.992 |

### Categoría (promedio_28 = suma de pronósticos SKU): primaria, universo común, diaria

| Método | n | MAE | RMSE | WAPE | Sesgo (pred−obs) | Unidades obs. | Sub/Sobre | MAPE (cobertura de reales > 0) | R² |
|---|---|---|---|---|---|---|---|---|---|
| cero | 756 | 21.249 | 58.925 | 1.0000 | -16064.0 | 16064 | 0.709/0.000 | 1.0000 (0.709) | -0.149 |
| promedio_28 | 756 | 7.201 | 18.855 | 0.3389 | 1892.5 | 16064 | 0.225/0.747 | 0.7895 (0.709) | 0.882 |
| rf_categoria | 756 | 6.503 | 16.443 | 0.3061 | 1396.7 | 16064 | 0.220/0.780 | 0.7265 (0.709) | 0.910 |

### Categoría (promedio_28 = suma de pronósticos SKU): historia_corta, universo común, acum10

| Método | n | MAE | RMSE | WAPE | Sesgo (pred−obs) | Unidades obs. | Sub/Sobre | MAPE (cobertura de reales > 0) | R² |
|---|---|---|---|---|---|---|---|---|---|
| cero | 1 | 0.000 | 0.000 | n/e | 0.0 | 0 | 0.000/0.000 | n/e (0.000) | n/e |
| promedio_28 | 1 | 2.857 | 2.857 | n/e | 2.9 | 0 | 0.000/1.000 | n/e (0.000) | n/e |
| rf_categoria | 1 | 7.158 | 7.158 | n/e | 7.2 | 0 | 0.000/1.000 | n/e (0.000) | n/e |

### Categoría (promedio_28 = suma de pronósticos SKU): historia_corta, universo común, acum14

| Método | n | MAE | RMSE | WAPE | Sesgo (pred−obs) | Unidades obs. | Sub/Sobre | MAPE (cobertura de reales > 0) | R² |
|---|---|---|---|---|---|---|---|---|---|
| cero | 1 | 0.000 | 0.000 | n/e | 0.0 | 0 | 0.000/0.000 | n/e (0.000) | n/e |
| promedio_28 | 1 | 4.000 | 4.000 | n/e | 4.0 | 0 | 0.000/1.000 | n/e (0.000) | n/e |
| rf_categoria | 1 | 9.524 | 9.524 | n/e | 9.5 | 0 | 0.000/1.000 | n/e (0.000) | n/e |

### Categoría (promedio_28 = suma de pronósticos SKU): historia_corta, universo común, acum21

| Método | n | MAE | RMSE | WAPE | Sesgo (pred−obs) | Unidades obs. | Sub/Sobre | MAPE (cobertura de reales > 0) | R² |
|---|---|---|---|---|---|---|---|---|---|
| cero | 1 | 0.000 | 0.000 | n/e | 0.0 | 0 | 0.000/0.000 | n/e (0.000) | n/e |
| promedio_28 | 1 | 6.000 | 6.000 | n/e | 6.0 | 0 | 0.000/1.000 | n/e (0.000) | n/e |
| rf_categoria | 1 | 13.585 | 13.585 | n/e | 13.6 | 0 | 0.000/1.000 | n/e (0.000) | n/e |

### Categoría (promedio_28 = suma de pronósticos SKU): historia_corta, universo común, diaria

| Método | n | MAE | RMSE | WAPE | Sesgo (pred−obs) | Unidades obs. | Sub/Sobre | MAPE (cobertura de reales > 0) | R² |
|---|---|---|---|---|---|---|---|---|---|
| cero | 21 | 0.000 | 0.000 | n/e | 0.0 | 0 | 0.000/0.000 | n/e (0.000) | n/e |
| promedio_28 | 21 | 0.286 | 0.286 | n/e | 6.0 | 0 | 0.000/1.000 | n/e (0.000) | n/e |
| rf_categoria | 21 | 0.647 | 0.651 | n/e | 13.6 | 0 | 0.000/1.000 | n/e (0.000) | n/e |

### Cobertura y universo

- SKU conocidos al 31/07: 3758 (primaria 3401); categorías: 37. Días evaluables del bloque: 21/21; no evaluables: ninguno.
- SKU nuevos con venta en el bloque (primera venta posterior al 31/07), aparte y sin historia/categoría inventadas: 103 SKU, 353 unidades (universo conocido: 16064 unidades; cobertura de unidades 0.9785).

- Universo común SKU primaria: 3401 de 3401 entidades.
- Universo común SKU historia_corta: 357 de 357 entidades.

## Simulación secuencial 01–31/08 (Inventario simulado con supuestos; no corresponde al inventario real de la empresa)

Universo fijo al 31/07: 3758 SKU (3401 primaria, 357 historia corta). Excluidos por ser nuevos: 141 SKU con 568 unidades de demanda proxy. Costos (fuente del precio): {'propio': 3758, 'categoria': 0, 'global': 0}. Fallbacks RF→promedio_28 (filas): 0. Días sin demanda conocida: ninguno. Revisiones al final de los días 1, 8, 15, 22 y 29 con matrices truncadas; costos, holding (20 %/365), lead time y seguridad son supuestos; demanda proxy exógena.

### Escenario principal L=7, S=7 (total)

| Política | Demanda elegible | Atendidas | Perdidas | Fill rate | Tasa días-SKU con faltante | Stock medio/día | Stock final | Pedidos (uds.) | Tránsito final | Holding sup. | Compras desembolsadas sup. | Costo consumido sup. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| referencia_fija | 23836 | 18023 | 5813 | 0.7561 | 0.0193 | 12648 | 13963 | 23295 | 3956 | 2643 | 267440 | 205736 |
| promedio_28 | 23836 | 18574 | 5262 | 0.7792 | 0.0164 | 13881 | 16546 | 27578 | 5105 | 2857 | 309792 | 212003 |
| rf_categoria_distribuido | 23836 | 18620 | 5216 | 0.7812 | 0.0162 | 13973 | 17093 | 28565 | 5499 | 2932 | 326713 | 213048 |

### Las 27 combinaciones (total): fill rate / perdidas / stock medio / compras desembolsadas (supuesto)

| L | S | referencia_fija | promedio_28 | rf_categoria_distribuido |
|---|---|---|---|---|
| 3 | 0 | 0.6773 / 7693 / 6969 / 179676 | 0.7117 / 6872 / 7714 / 204001 | 0.7101 / 6911 / 7676 / 211904 |
| 3 | 7 | 0.7783 / 5285 / 11910 / 269750 | 0.8103 / 4522 / 13158 / 307012 | 0.8076 / 4585 / 12898 / 312731 |
| 3 | 14 | 0.8185 / 4327 / 16933 / 344267 | 0.8491 / 3598 / 18836 / 396359 | 0.8491 / 3598 / 18665 / 404702 |
| 7 | 0 | 0.6741 / 7768 / 8323 / 174989 | 0.6990 / 7175 / 9192 / 204661 | 0.7078 / 6965 / 9543 / 229935 |
| 7 | 7 | 0.7561 / 5813 / 12648 / 267440 | 0.7792 / 5262 / 13881 / 309792 | 0.7812 / 5216 / 13973 / 326713 |
| 7 | 14 | 0.7841 / 5147 / 16474 / 331079 | 0.8060 / 4625 / 18210 / 388466 | 0.8140 / 4433 / 18816 / 426273 |
| 14 | 0 | 0.6984 / 7188 / 12009 / 181045 | 0.7123 / 6858 / 12915 / 224927 | 0.7143 / 6809 / 13039 / 248862 |
| 14 | 7 | 0.7433 / 6119 / 14475 / 248695 | 0.7532 / 5882 / 15529 / 304339 | 0.7590 / 5745 / 15763 / 343591 |
| 14 | 14 | 0.7834 / 5163 / 18007 / 345105 | 0.7926 / 4944 / 19289 / 421566 | 0.7942 / 4906 / 19202 / 437577 |

### Diferencias frente a referencia fija y promedio_28 (L=7, S=7, total)

| Política | vs | Δ fill rate | Δ perdidas (abs; rel) | Δ stock medio (rel) | Δ compras (rel) | Δ valor stock final (rel) |
|---|---|---|---|---|---|---|
| referencia_fija | promedio_28 | -0.0231 | 551; 0.105 | -0.089 | -0.137 | -0.139 |
| promedio_28 | referencia_fija | 0.0231 | -551; -0.095 | 0.097 | 0.158 | 0.161 |
| rf_categoria_distribuido | referencia_fija | 0.0250 | -597; -0.103 | 0.105 | 0.222 | 0.229 |
| rf_categoria_distribuido | promedio_28 | 0.0019 | -46; -0.009 | 0.007 | 0.055 | 0.059 |

### Servicio frente a inventario: rf_categoria_distribuido vs promedio_28, nueve escenarios (total)

| L | S | Δ fill rate | Δ stock medio (rel) | Δ compras (rel) | Δ perdidas (rel) |
|---|---|---|---|---|---|
| 3 | 0 | -0.0016 | -0.005 | 0.039 | 0.006 |
| 3 | 7 | -0.0026 | -0.020 | 0.019 | 0.014 |
| 3 | 14 | 0.0000 | -0.009 | 0.021 | 0.000 |
| 7 | 0 | 0.0088 | 0.038 | 0.123 | -0.029 |
| 7 | 7 | 0.0019 | 0.007 | 0.055 | -0.009 |
| 7 | 14 | 0.0081 | 0.033 | 0.097 | -0.042 |
| 14 | 0 | 0.0021 | 0.010 | 0.106 | -0.007 |
| 14 | 7 | 0.0057 | 0.015 | 0.129 | -0.023 |
| 14 | 14 | 0.0016 | -0.004 | 0.038 | -0.008 |

Una ventaja de servicio acompañada de más stock o más compras no se presenta como mejora; el desembolso y el costo consumido se muestran por separado y no se calcula ahorro ni utilidad.

### Escenario principal por cohorte inicial

| Cohorte | Política | Demanda elegible | Fill rate | Perdidas | Stock medio/día | Compras desembolsadas |
|---|---|---|---|---|---|---|
| primaria | referencia_fija | 22002 | 0.7462 | 5584 | 11042 | 243306 |
| primaria | promedio_28 | 22002 | 0.7706 | 5047 | 12303 | 288657 |
| primaria | rf_categoria_distribuido | 22002 | 0.7733 | 4988 | 12472 | 306286 |
| historia_corta | referencia_fija | 1834 | 0.8751 | 229 | 1607 | 24134 |
| historia_corta | promedio_28 | 1834 | 0.8828 | 215 | 1578 | 21135 |
| historia_corta | rf_categoria_distribuido | 1834 | 0.8757 | 228 | 1500 | 20427 |

### Revisiones: pesos y conservación categoría→SKU

| Origen | Cat. peso 28d / hist. / uniforme | Conservación | Hash del pronóstico |
|---|---|---|---|
| 2026-08-01 | 36/1/0 | 2.8e-12 | `8f9a706b216fb0e1` |
| 2026-08-08 | 34/3/0 | 2.0e-12 | `2f0e17db0278d1eb` |
| 2026-08-15 | 35/2/0 | 2.5e-12 | `fabde4218fd51ed9` |
| 2026-08-22 | 34/3/0 | 1.8e-12 | `cbc69002de487c82` |
| 2026-08-29 | 33/4/0 | 3.1e-12 | `db4c61a05a5a043c` |

## Verificaciones y auditoría

- Auditoría separada (recomputa desde predicciones selladas y reales guardados, sin reentrenar): **aprobada**; 27 combinaciones con balances re-verificados; identidad de valor máx. 1.09e-10.
- Sello anterior a la lectura de agosto: True. Fingerprint de entrenamiento: `f73f00a79ad02b69bb3c8dfd3af8a7d9a6ff751842f5ad4c5ba5e8d20038c33b`.
- Fases de cálculo: verificacion=completa, preparacion=completa, lectura_agosto=completa, evaluacion_predictiva=completa, simulacion=completa.

## Limitaciones

- Un solo bloque de 21 días: sin intervalo de confianza ni prueba de tres folds; los resultados no son extrapolables por sí solos.
- Demanda proxy = ventas observadas, posiblemente censuradas por stock real desconocido; sin backorders.
- Inventario, costos, holding, lead time y seguridad son supuestos; no hay MOQ ni proveedores reales; un almacén.
- Catálogo de categorías al 31/07, sin corregirlo con agosto; SKU nuevos informados aparte.
- La simulación no demuestra impacto en la MYPE ni autoriza compras. El paquete es local y privado: no está publicado ni desplegado.
