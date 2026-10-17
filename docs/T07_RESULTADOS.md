# T07 Resultados: horizontes 10/14/21 y simulación junio-julio (desarrollo)

**Inventario simulado con supuestos; no corresponde al inventario real de la empresa.** Generado el 2026-10-17 11:45 (America/Lima). Protocolo congelado en 325da2f. Solo ventas ≤ 31/07; agosto no se leyó. WAPE y razones son fracciones (1,00 = 100 %). Folds de desarrollo (bloques solapados): no son prueba final ni evidencia de impacto en la MYPE.

## Parte A: evaluación predictiva (4 folds, bloques de 21 días)

Regla provisional (SKU, acumulado H=14, primaria, común): WAPE rf_distribuido 0.9292 frente a promedio_28 0.8726; mejora relativa -0.0649; folds favorables []; sesgo/observado 0.167; **no cumple la regla provisional**.

### SKU-almacén: primaria, universo común, acum10, agregado de 4 folds (bloques solapados)

| Método | n | MAE | RMSE | WAPE | Sesgo (pred−obs) | Unidades obs. | Sub/Sobre | R² |
|---|---|---|---|---|---|---|---|---|
| cero | 11957 | 2.231 | 6.909 | 1.0000 | -26676.0 | 26676 | 0.446/0.000 | -0.116 |
| promedio_28 | 11957 | 2.074 | 6.750 | 0.9295 | 1630.9 | 26676 | 0.288/0.426 | -0.065 |
| referencia_fija_0531 | 11957 | 2.457 | 9.370 | 1.1013 | 7451.2 | 26676 | 0.275/0.473 | -1.053 |
| rf_distribuido | 11957 | 2.246 | 7.794 | 1.0067 | 5564.1 | 26676 | 0.268/0.448 | -0.421 |

### SKU-almacén: primaria, universo común, acum14, agregado de 4 folds (bloques solapados)

| Método | n | MAE | RMSE | WAPE | Sesgo (pred−obs) | Unidades obs. | Sub/Sobre | R² |
|---|---|---|---|---|---|---|---|---|
| cero | 11957 | 3.161 | 9.325 | 1.0000 | -37791.0 | 37791 | 0.518/0.000 | -0.130 |
| promedio_28 | 11957 | 2.758 | 9.291 | 0.8726 | 2172.6 | 37791 | 0.316/0.413 | -0.121 |
| referencia_fija_0531 | 11957 | 3.270 | 12.829 | 1.0345 | 10320.9 | 37791 | 0.310/0.447 | -1.138 |
| rf_distribuido | 11957 | 2.937 | 10.540 | 0.9292 | 6326.5 | 37791 | 0.298/0.434 | -0.443 |

### SKU-almacén: primaria, universo común, acum21, agregado de 4 folds (bloques solapados)

| Método | n | MAE | RMSE | WAPE | Sesgo (pred−obs) | Unidades obs. | Sub/Sobre | R² |
|---|---|---|---|---|---|---|---|---|
| cero | 11957 | 4.696 | 12.577 | 1.0000 | -56154.0 | 56154 | 0.592/0.000 | -0.162 |
| promedio_28 | 11957 | 3.929 | 13.310 | 0.8366 | 4208.7 | 56154 | 0.358/0.393 | -0.301 |
| referencia_fija_0531 | 11957 | 4.656 | 18.744 | 0.9914 | 16431.2 | 56154 | 0.338/0.444 | -1.581 |
| rf_distribuido | 11957 | 4.175 | 15.271 | 0.8889 | 10022.6 | 56154 | 0.342/0.410 | -0.713 |

### SKU-almacén: primaria, universo común, diaria, agregado de 4 folds (bloques solapados)

| Método | n | MAE | RMSE | WAPE | Sesgo (pred−obs) | Unidades obs. | Sub/Sobre | R² |
|---|---|---|---|---|---|---|---|---|
| cero | 248425 | 0.226 | 1.554 | 1.0000 | -56154.0 | 56154 | 0.104/0.000 | -0.022 |
| promedio_28 | 248425 | 0.350 | 1.569 | 1.5499 | 4208.7 | 56154 | 0.094/0.577 | -0.042 |
| referencia_fija_0531 | 248425 | 0.388 | 1.691 | 1.7165 | 16431.2 | 56154 | 0.092/0.611 | -0.211 |
| rf_distribuido | 248425 | 0.365 | 1.612 | 1.6150 | 10022.6 | 56154 | 0.093/0.580 | -0.100 |

### Categoría (productos conocidos al corte): primaria, universo común, acum10, agregado de 4 folds (bloques solapados)

| Método | n | MAE | RMSE | WAPE | Sesgo (pred−obs) | Unidades obs. | Sub/Sobre | R² |
|---|---|---|---|---|---|---|---|---|
| cero | 144 | 204.319 | 524.879 | 1.0000 | -29422.0 | 29422 | 0.875/0.000 | -0.179 |
| promedio_28 | 144 | 44.342 | 103.648 | 0.2170 | 1560.5 | 29422 | 0.403/0.521 | 0.954 |
| rf_categoria | 144 | 58.847 | 158.437 | 0.2880 | 5883.4 | 29422 | 0.292/0.708 | 0.893 |

### Categoría (productos conocidos al corte): primaria, universo común, acum14, agregado de 4 folds (bloques solapados)

| Método | n | MAE | RMSE | WAPE | Sesgo (pred−obs) | Unidades obs. | Sub/Sobre | R² |
|---|---|---|---|---|---|---|---|---|
| cero | 144 | 289.417 | 746.572 | 1.0000 | -41676.0 | 41676 | 0.889/0.000 | -0.177 |
| promedio_28 | 144 | 58.419 | 151.057 | 0.2018 | 2066.8 | 41676 | 0.424/0.514 | 0.952 |
| rf_categoria | 144 | 73.752 | 201.068 | 0.2548 | 6638.4 | 41676 | 0.326/0.674 | 0.915 |

### Categoría (productos conocidos al corte): primaria, universo común, acum21, agregado de 4 folds (bloques solapados)

| Método | n | MAE | RMSE | WAPE | Sesgo (pred−obs) | Unidades obs. | Sub/Sobre | R² |
|---|---|---|---|---|---|---|---|---|
| cero | 144 | 430.049 | 1104.131 | 1.0000 | -61927.0 | 61927 | 0.889/0.000 | -0.179 |
| promedio_28 | 144 | 85.525 | 225.133 | 0.1989 | 4146.4 | 61927 | 0.410/0.528 | 0.951 |
| rf_categoria | 144 | 104.556 | 290.972 | 0.2431 | 10528.4 | 61927 | 0.292/0.708 | 0.918 |

### Categoría (productos conocidos al corte): primaria, universo común, diaria, agregado de 4 folds (bloques solapados)

| Método | n | MAE | RMSE | WAPE | Sesgo (pred−obs) | Unidades obs. | Sub/Sobre | R² |
|---|---|---|---|---|---|---|---|---|
| cero | 2988 | 20.725 | 56.513 | 1.0000 | -61927.0 | 61927 | 0.740/0.000 | -0.155 |
| promedio_28 | 2988 | 8.405 | 22.132 | 0.4056 | 4146.4 | 61927 | 0.306/0.612 | 0.823 |
| rf_categoria | 2988 | 8.862 | 22.120 | 0.4276 | 10528.4 | 61927 | 0.283/0.717 | 0.823 |

### WAPE acumulado H=14 SKU primaria por fold

| Fold | cero | promedio_28 | referencia_fija_0531 | rf_distribuido |
|---|---|---|---|---|
| G1 | 1.000 | 0.923 | 0.923 | 1.060 |
| G2 | 1.000 | 1.035 | 1.182 | 1.068 |
| G3 | 1.000 | 0.810 | 1.034 | 0.865 |
| G4 | 1.000 | 0.762 | 1.011 | 0.773 |

### Folds: cobertura, pesos y conservación

| Fold | Corte | SKU conocidos | Nuevos en bloque (uds. evaluables) | Días evaluables | Categorías peso 28d / hist. / uniforme | Conservación cat→SKU | Negativos recortados |
|---|---|---|---|---|---|---|---|
| G1 | 2026-05-31 | 3347 | 159 (682) | 20/21 | 34/2/0 | 1.9e-12 | 0 |
| G2 | 2026-06-14 | 3450 | 156 (744) | 21/21 | 32/4/0 | 3.5e-12 | 0 |
| G3 | 2026-06-28 | 3549 | 150 (424) | 21/21 | 32/4/0 | 2.3e-12 | 0 |
| G4 | 2026-07-10 | 3647 | 111 (296) | 21/21 | 35/1/0 | 2.4e-12 | 0 |

## Parte B: simulación 01/06–31/07 (Inventario simulado con supuestos; no corresponde al inventario real de la empresa)

Universo fijo: 3347 SKU conocidos al 31/05 (2672 primaria, 675 historia corta). Excluidos por ser posteriores: 411 SKU con 3783 unidades de demanda proxy en junio-julio (cobertura aparte). Costos: fuente del precio {'propio': 3347, 'categoria': 0, 'global': 0}. Fallbacks RF→promedio_28 (filas SKU-revisión-escenario): 0. Costos, holding (20 %/365), lead time y seguridad son supuestos; 07/06 sin evento de demanda; demanda proxy exógena.

### Escenario principal L=7, S=7 (total)

| Política | Demanda elegible | Atendidas | Perdidas | Fill rate | Tasa de días-SKU con faltante | Stock medio/día | Stock final | Pedidos (uds.) | Tránsito final | Holding supuesto | Compras desembolsadas | Costo consumido | Valor stock final |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| referencia_fija | 42679 | 31625 | 11054 | 0.7410 | 0.0225 | 15283 | 15182 | 36813 | 3998 | 6033 | 430952 | 373723 | 174538 |
| promedio_28 | 42679 | 34008 | 8671 | 0.7968 | 0.0165 | 16648 | 17653 | 43012 | 5343 | 6786 | 515948 | 403060 | 215188 |
| rf_categoria_distribuido | 42679 | 34509 | 8170 | 0.8086 | 0.0153 | 17891 | 18785 | 44746 | 5444 | 7185 | 536575 | 409251 | 227610 |

### Los nueve escenarios (total): fill rate / perdidas / stock medio / compras desembolsadas (supuesto)

| L | S | referencia_fija | promedio_28 | rf_categoria_distribuido |
|---|---|---|---|---|
| 3 | 0 | 0.6681 / 14165 / 8092 / 321544 | 0.7080 / 12461 / 8520 / 361820 | 0.7248 / 11747 / 9460 / 379245 |
| 3 | 7 | 0.7619 / 10162 / 14023 / 442245 | 0.8208 / 7646 / 15029 / 510111 | 0.8307 / 7224 / 16053 / 522505 |
| 3 | 14 | 0.8005 / 8514 / 19902 / 528649 | 0.8689 / 5596 / 21941 / 627283 | 0.8731 / 5415 / 23047 / 639073 |
| 7 | 0 | 0.6507 / 14906 / 9765 / 309600 | 0.6980 / 12889 / 10793 / 371265 | 0.7198 / 11959 / 12017 / 399724 |
| 7 | 7 | 0.7410 / 11054 / 15283 / 430952 | 0.7968 / 8671 / 16648 / 515948 | 0.8086 / 8170 / 17891 / 536575 |
| 7 | 14 | 0.7743 / 9631 / 20261 / 511413 | 0.8487 / 6456 / 23194 / 637627 | 0.8585 / 6040 / 24708 / 668170 |
| 14 | 0 | 0.6723 / 13985 / 13910 / 319731 | 0.7083 / 12449 / 15244 / 400011 | 0.7279 / 11615 / 16733 / 430785 |
| 14 | 7 | 0.7219 / 11869 / 17928 / 406965 | 0.7784 / 9458 / 20267 / 529125 | 0.7947 / 8760 / 21898 / 565821 |
| 14 | 14 | 0.7705 / 9793 / 23286 / 525609 | 0.8209 / 7642 / 25767 / 663796 | 0.8287 / 7310 / 27243 / 684204 |

### Diferencias del escenario principal frente a referencia fija y a promedio_28 (total)

| Política | vs | Δ fill rate (abs) | Δ perdidas (uds., rel) | Δ stock medio (rel) | Δ compras (rel) | Δ valor stock final (rel) |
|---|---|---|---|---|---|---|
| referencia_fija | promedio_28 | -0.0558 | 2383 (0.275) | -0.082 | -0.165 | -0.189 |
| promedio_28 | referencia_fija | 0.0558 | -2383 (-0.216) | 0.089 | 0.197 | 0.233 |
| rf_categoria_distribuido | referencia_fija | 0.0676 | -2884 (-0.261) | 0.171 | 0.245 | 0.304 |
| rf_categoria_distribuido | promedio_28 | 0.0117 | -501 (-0.058) | 0.075 | 0.040 | 0.058 |

### Servicio frente a inventario: rf_categoria_distribuido vs promedio_28 en los nueve escenarios (total)

| L | S | Δ fill rate | Δ stock medio (rel) | Δ compras (rel) | Δ perdidas (rel) |
|---|---|---|---|---|---|
| 3 | 0 | 0.0167 | 0.110 | 0.048 | -0.057 |
| 3 | 7 | 0.0099 | 0.068 | 0.024 | -0.055 |
| 3 | 14 | 0.0042 | 0.050 | 0.019 | -0.032 |
| 7 | 0 | 0.0218 | 0.113 | 0.077 | -0.072 |
| 7 | 7 | 0.0117 | 0.075 | 0.040 | -0.058 |
| 7 | 14 | 0.0097 | 0.065 | 0.048 | -0.064 |
| 14 | 0 | 0.0195 | 0.098 | 0.077 | -0.067 |
| 14 | 7 | 0.0164 | 0.080 | 0.069 | -0.074 |
| 14 | 14 | 0.0078 | 0.057 | 0.031 | -0.043 |

Lectura: la Parte A muestra que rf_distribuido es peor que promedio_28 como pronóstico y sobrepronostica (sesgo ≈ +17 % en H=14); su mayor fill rate en la simulación coincide con más stock y más compras, de modo que **no** puede atribuirse a un mejor pronóstico: es compatible con simplemente pedir más. Sin una comparación a stock o compras equivalentes, la ventaja de servicio no es concluyente.

### Escenario principal por cohorte inicial

| Cohorte | Política | Demanda elegible | Fill rate | Perdidas | Stock medio/día | Compras desembolsadas |
|---|---|---|---|---|---|---|
| primaria | referencia_fija | 39124 | 0.7492 | 9814 | 13105 | 384730 |
| primaria | promedio_28 | 39124 | 0.8017 | 7757 | 14431 | 457353 |
| primaria | rf_categoria_distribuido | 39124 | 0.8147 | 7250 | 15682 | 478602 |
| historia_corta | referencia_fija | 3555 | 0.6512 | 1240 | 2178 | 46221 |
| historia_corta | promedio_28 | 3555 | 0.7429 | 914 | 2217 | 58594 |
| historia_corta | rf_categoria_distribuido | 3555 | 0.7412 | 920 | 2208 | 57973 |

### Parte A: historia corta (SKU, universo común, acum14, agregado)

| Método | n | WAPE | Sesgo | Unidades obs. |
|---|---|---|---|---|
| cero | 2036 | 1.0000 | -3885.0 | 3885 |
| promedio_28 | 2036 | 1.3997 | 2620.6 | 3885 |
| referencia_fija_0531 | 1431 | 2.2552 | 2502.1 | 1687 |
| rf_distribuido | 2036 | 1.0591 | 312.0 | 3885 |

### Cobertura de la referencia fija (no existe para SKU posteriores al 31/05)

| Fold | Cohorte | Entidades con predicción | Universo común |
|---|---|---|---|
| G1 | primaria | 2672 | 2672 |
| G1 | historia_corta | 675 | 675 |
| G2 | primaria | 2914 | 2914 |
| G2 | historia_corta | 433 | 536 |
| G3 | primaria | 3121 | 3121 |
| G3 | historia_corta | 226 | 428 |
| G4 | primaria | 3250 | 3250 |
| G4 | historia_corta | 97 | 397 |

### Pesos y conservación por revisión de la simulación

| Origen | Cat. peso 28d / hist. / uniforme | Conservación cat→SKU |
|---|---|---|
| 2026-06-01 | 34/2/0 | 2.6e-12 |
| 2026-06-08 | 33/3/0 | 1.5e-12 |
| 2026-06-15 | 32/4/0 | 2.4e-12 |
| 2026-06-22 | 32/4/0 | 1.5e-12 |
| 2026-06-29 | 32/4/0 | 1.4e-12 |
| 2026-07-06 | 32/4/0 | 1.9e-12 |
| 2026-07-13 | 33/3/0 | 1.3e-12 |
| 2026-07-20 | 32/4/0 | 1.5e-12 |
| 2026-07-27 | 33/3/0 | 1.4e-12 |

Reducir compras con más faltantes o distinto stock terminal **no** es ahorro ni utilidad; los desembolsos y los costos consumidos se muestran por separado. Detalle por cohorte y por escenario en T07_METRICAS.json.

## Verificaciones

- Conservación por SKU/día y de sistema y identidad de valor en las 27 combinaciones: True; error máximo de identidad de valor 1.16e-10.
- Repetición completa (predicción + simulación) idéntica: True.
- Tiempo total: 162 s.

## Limitaciones

- Folds y simulación de desarrollo con meses ya usados en T05/T06; sin independencia respecto de la elección de métodos.
- Los hashes de archivos .csv.gz/.npz incluyen metadatos de compresión; la repetición idéntica se comprobó en memoria dentro del mismo proceso.
- La base temporal de las pruebas con datos reales contiene también agosto; la ruta de entrenamiento lo bloquea (convención de ingeniería, no control de seguridad) y los resultados no lo usan.
- El RF por categoría usa solo 36 series; las features mes/día del mes salen del rango de entrenamiento al predecir y pueden explicar parte de su peor desempeño (no investigado).
- El almacén se agrega por categoría (un solo almacén en estos datos).
- Demanda proxy = ventas observadas, posiblemente censuradas por stock real desconocido; sin backorders; 07/06 sin demanda conocida.
- Costos, holding, lead time y seguridad supuestos; sin MOQ ni proveedores reales; un almacén; universo fijo al 31/05.
- La simulación no demuestra impacto en la MYPE ni autoriza compras.
