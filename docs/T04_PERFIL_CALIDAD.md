# T04 Perfil de calidad (marzo-julio 2026)

Generado el 2026-10-17 08:25 (America/Lima). Dataset: `f73f00a79ad02b69...` (firma completa en T04_FIRMA.json). Solo marzo-julio; agosto no se uso. Cifras agregadas medidas por scripts/build_t04.py; nada aqui es un resultado de modelo.

## Fuentes y cobertura

- Fuentes aprobadas usadas: 5 (marzo.xlsx, abril.xlsx, mayo.xlsx, junio.xlsx, julio.xlsx); meses requeridos 2026-03, 2026-04, 2026-05, 2026-06, 2026-07; problemas de fuente: 0.
- Lineas de venta: 71931; SKU: 3758; pares SKU-almacen: 3758; almacenes: ['1']; categorias en catalogo al corte: 37.
- Calendario natural: 153 dias, 3 enmascarados (03/04, 12/04, 07/06). Filas de venta omitidas por mascara: 0. Dias sin ningun registro y no enmascarados: ninguno. Filas en dias enmascarados: 0 (filas de venta fechadas en dias enmascarados halladas en la base).

| Mes | Lineas | SKU | Unidades | Importe (S/) | Dias con venta / calendario | Sin registro (no masc.) | Enmascarados |
|---|---|---|---|---|---|---|---|
| 2026-03 | 14456 | 2510 | 24316 | 426456.21 | 31/31 | - | - |
| 2026-04 | 13907 | 2524 | 25481 | 429609.99 | 28/30 | - | ['2026-04-03', '2026-04-12'] |
| 2026-05 | 15380 | 2476 | 29228 | 500621.72 | 31/31 | - | - |
| 2026-06 | 12510 | 2401 | 21020 | 390855.08 | 29/30 | - | ['2026-06-07'] |
| 2026-07 | 15678 | 2434 | 25442 | 453143.28 | 31/31 | - | - |

## Unidades

- unidad_base: {'UND': 71931}; cantidades no enteras: 0; SKU con varias unidades: 0. Cantidad por linea: {'p0': 1.0, 'p10': 1.0, 'p25': 1.0, 'p50': 1.0, 'p75': 1.0, 'p90': 3.0, 'p100': 264.0}.

## Inicio de historia por producto

- Primera venta observada por mes (pares): {'2026-03': 2510, '2026-04': 532, '2026-05': 305, '2026-06': 214, '2026-07': 197}. Se desconoce la historia previa a marzo: las series con primera venta en las primeras semanas pueden estar truncadas por la izquierda, no ser productos nuevos.
- Pares con primera venta posterior al 29/03 (probables altas, heuristica): 1307.
- Dias de historia hasta el corte (cuantiles): {'p0': 1.0, 'p10': 57.0, 'p25': 108.0, 'p50': 140.0, 'p75': 150.0, 'p90': 152.0, 'p100': 153.0}; <28 dias: 159; <56 dias: 357; >=90 dias: 3101.

## Ceros e intermitencia

- Series densas: 459375 filas par-dia = 54266 con venta + 396339 cero observado + 8770 enmascaradas. Proporcion de cero observado sobre dias usables: 0.8796; en pares con >=56 dias de historia: 0.8794.
- Un cero observado es venta observada cero desde la primera observacion; la venta puede estar censurada por stock desconocido, asi que no se interpreta como ausencia de demanda.
- Clase Syntetos-Boylan (pares): {'INTERMITENTE': 2568, 'IRREGULAR_LUMPY': 729, 'UNA_SOLA_VENTA': 445, 'ERRATICA': 9, 'SUAVE': 7}; participacion de unidades por clase: {'ERRATICA': 0.0775, 'INTERMITENTE': 0.4099, 'IRREGULAR_LUMPY': 0.4773, 'SUAVE': 0.0296, 'UNA_SOLA_VENTA': 0.0058}.
- ADI (cuantiles): {'p0': 1.0, 'p10': 3.89, 'p25': 6.73, 'p50': 13.55, 'p75': 29.5, 'p90': 61.65, 'p100': 150.0}; proporcion de ceros: {'p0': 0.0, 'p10': 0.74, 'p25': 0.85, 'p50': 0.93, 'p75': 0.97, 'p90': 0.98, 'p100': 0.99}; dias con venta: {'p0': 1.0, 'p10': 1.0, 'p25': 3.0, 'p50': 8.0, 'p75': 19.0, 'p90': 35.0, 'p100': 138.0}.

## Categorias

- SKU con mas de una categoria original en marzo-julio: 0; lineas cuya categoria original difiere del catalogo al corte: 0; lineas sin categoria: 0; SKU 16140041 en catalogo: MAQUILLAJE PARA ROSTRO.

## Notas de credito (informativo, fuera del objetivo)

Hasta el corte: {'2026-06': {'lineas': 81, 'importe': -9680.6}, '2026-05': {'lineas': 78, 'importe': -2769.38}, '2026-03': {'lineas': 89, 'importe': -3128.0}, '2026-04': {'lineas': 72, 'importe': -2927.5}, '2026-07': {'lineas': 112, 'importe': -4548.76}}. Separadas de ventas brutas; no implican devolucion fisica.

## Limites

- Un unico almacen y una unica unidad base en este periodo: no se ha probado manejo multialmacen ni de equivalencias.
- Cobertura de 5 meses: no permite estacionalidad anual; el patron semanal si es observable.
- La serie por categoria suma unidades heterogeneas (solo orientativa).
- No hay inventario real: no se puede separar demanda de venta censurada por faltante.
