# T04 Diccionario de datos derivados

Archivos en `artifacts/private/t04/` (ignorados por Git; contienen datos comerciales). Origen: ventas aprobadas de `demand_forecasting_v2` con corte 2026-07-31 via `load_training_data`. Hash en T04_FIRMA.json.

## series_sku_almacen_diaria.csv.gz

| Campo | Tipo | Significado |
|---|---|---|
| fecha | texto YYYY-MM-DD | Dia natural (America/Lima). Calendario sin comprimir. |
| sku | texto | ID_ARTICULO del Excel. |
| almacen | texto | ID_ALMACEN del Excel (en marzo-julio solo existe '1'). |
| categoria_corte | texto | Categoria del catalogo versionado al corte 2026-07-31 (DESCONOCIDA si no hay). categoria_original no se modifica en la base. |
| estado | VENTA_OBSERVADA | CERO_OBSERVADO | EXCLUIDO_MASCARA | VENTA_OBSERVADA: hay al menos una linea de venta. CERO_OBSERVADO: sin venta desde la primera observacion del par; es un cero de venta observada, NO prueba ausencia de demanda ni stock disponible. EXCLUIDO_MASCARA: 03/04, 12/04 y 07/06 de 2026; cantidad vacia, fuera de entrenamiento y metricas. |
| cantidad_base | decimal | Suma de CANTIDAD_UM_BASE de lineas de venta (TIPO_DOC distinto de 7, importe > 0). Unidad base (todas UND en marzo-julio). Vacio en EXCLUIDO_MASCARA. Excluye notas de credito. |
| n_lineas | entero | Numero de lineas de venta del dia (0 en cero observado, vacio si mascara). |
| importe_centimos | entero | Suma de TOTAL_LINEA de ventas en centimos de sol (exacto, sin coma flotante). |
| dias_desde_primera_obs | entero | 0 en la primera venta observada del par; la serie empieza ahi (los dias anteriores no se rellenan). |

## series_categoria_diaria.csv.gz

| Campo | Tipo | Significado |
|---|---|---|
| fecha / categoria_corte / estado | ver arriba | La serie de cada categoria empieza en su primera venta observada. estado=CERO_OBSERVADO si ninguna linea de la categoria ese dia. |
| cantidad_base_suma_heterogenea | decimal | Suma de cantidades en unidad base de SKU distintos; orientativa, no comparable en volumen fisico. |
| n_lineas, n_sku_con_venta, importe_centimos | entero | Lineas, SKU distintos con venta e importe del dia. |

## intermitencia_sku_almacen.csv

| Campo | Tipo | Significado |
|---|---|---|
| dias, dias_con_venta, unidades | numerico | Sobre dias no enmascarados desde la primera observacion. |
| adi | decimal | Intervalo medio entre demandas = dias / dias_con_venta. |
| cv2 | decimal | Coeficiente de variacion al cuadrado de tamanos no nulos (vacio con una sola venta). |
| proporcion_ceros | decimal | Ceros observados / dias. |
| clase_sbc | texto | Syntetos-Boylan: ADI<1,32 y CV2<0,49 SUAVE; ADI<1,32 y CV2>=0,49 ERRATICA; ADI>=1,32 y CV2<0,49 INTERMITENTE; resto IRREGULAR_LUMPY; UNA_SOLA_VENTA aparte. Descriptivo, no selecciona modelos. |

## Campos de origen (coleccion sales, esquema v2)

linea_id (identidad normalizada), fecha, sku, almacen, cantidad_original/unidad_original, equivalencia, cantidad_base/unidad_base, precio_unitario_original, importe (Decimal128), categoria_original, doc_hash, pedido_id, sources (procedencia: archivo, sha256, fila), tipo_doc. Notas de credito (TIPO_DOC=7) viven en credit_notes y no entran en el objetivo.

## Transformaciones

1. Seleccion de ventas con fuente aprobada, fecha <= 2026-07-31 (R04). 2. Agregacion por (sku, almacen, dia) con suma de cantidad_base. 3. Malla densa desde la primera venta de cada par hasta el corte. 4. Ceros observados tras la primera venta; mascara de 3 dias sin cero ni compresion. 5. Categoria del catalogo al corte. Sin imputacion, sin escalado, sin features, sin rezagos.
