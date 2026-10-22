# Conciliación y preparación de datos con SQL Server — 21/10/2026

Continuación de `docs/DIAGNOSTICO_SQL_20261021.md`. **Solo lectura**: no se importó nada en la aplicación, no se reemplazó el plan vigente, no se modificó SQL Server ni los libros, y las demos 8443/8444/8445 quedaron intactas. Programa reproducible: `python -m scripts.sql21_prepare` (ejecuta únicamente `SELECT`); salidas privadas en `artifacts/private/sql21_prep/` (no se versionan). Aceptación humana: **pendiente**.

## 1. Criterios acordados
- **Último día completo para el pronóstico: 20/10/2026.** El 21/10 (parcial) se guarda aparte y no entra al pronóstico; sus movimientos sí sirven para conciliar inventario hasta el corte disponible.
- El último documento registrado es del 21/10 a las 16:26:38. **Eso es la hora de la última operación, no la hora del respaldo**, que no se conoce (se informó ~17:00). Lo «posterior al conteo» se llama «hasta el último movimiento disponible».

## 2. Ventas: libros contra SQL, registro por registro
Cada línea se compara con la clave (pedido, tipo de documento, serie-número, fecha, código normalizado, almacén, cantidad, precio, descuento, total, unidad, equivalencia) y se cuentan multiplicidades. En notas de crédito (tipo 07) se compara el valor absoluto: el libro las guarda negativas y SQL positivas.

| Libro | Líneas Excel | Líneas SQL | Registros distintos (Excel / SQL) | Solo en Excel | Solo en SQL | Documentos (Excel / SQL) | Documentos con distinto n.º de líneas |
|---|---|---|---|---|---|---|---|
| setiembre.xlsx (01–30/09) | 14 308 | 14 308 | 14 308 / 14 308 | 0 | 0 | 8 122 / 8 122 | 0 |
| octubre.xlsx (01–20/10) | 9 853 | 9 853 | 9 853 / 9 853 | 0 | 0 | 5 609 / 5 609 | 0 |

La multiplicidad máxima de un registro idéntico es 1 en ambos libros. **Resultado: correspondencia completa registro por registro**, además de los totales ya verificados.

Códigos: SQL guarda 8 caracteres con ceros a la izquierda (14 códigos tienen 7 caracteres y 2 contienen un espacio: `114 0001`, `142 0001`); los libros los escriben sin ceros. Quitar los ceros **no produce colisiones** en los 12 497 artículos; los 4 114 códigos distintos de los libros de marzo a octubre existen todos en SQL y ninguno es ambiguo. **Los códigos originales de los libros se conservan** (`codigo_original`) y el código SQL va aparte (`id_articulo_sql`).

## 3. Datos preparados (privados, `artifacts/private/sql21_prep/`)
| Archivo | Contenido |
|---|---|
| `ventas_octubre_01_20_normalizadas.csv` | `octubre.xlsx` normalizado con las reglas de `pipeline/plan/normalize.py` (mismos 21 campos, ventana 01–20/10): 9 765 ventas y 88 notas de crédito (separadas, sin inferir devolución); importe PEN 276 242,10; sha256 del libro `7815dacc…43b6`. |
| `ventas_20261021_parcial_sql.csv` | 318 líneas del 21/10 desde SQL (hasta 16:26:38), **separadas**; sin clientes ni usuarios. |
| `conciliacion_50_productos.csv` | Los 50 productos: conteo, movimientos posteriores por concepto, existencia reconstruida (al 20/10 y al último movimiento), stock del sistema, reservado, diferencia y estado. |
| `compras_11452_11455_para_consultar.csv` | 35 líneas de las dos compras: cantidades, unidad, almacén, fechas y movimiento de kardex. |
| `informe.json` | Informe de la corrida (comparaciones, códigos, conciliación). |

## 4. Conciliación de los 50 productos
Regla: existencia reconstruida = conteo físico reportado (18/10 17:00, almacén 001) + entradas − salidas del kardex del almacén 001 posteriores a esa hora, hasta el último movimiento disponible. Se compara con `INV_STOCK_ARTICULOS.STOCK_CANTIDAD` y se muestra `STOCK_CANTRESERVADA`. **No se ajustó ninguna cantidad para forzar coincidencias.**

**37 de 50 coinciden exactamente; 13 discrepan** (suma +23; rango −1…+9). Todos los movimientos posteriores de los 50 enlazados a una venta pertenecen a documentos vigentes y su cantidad en kardex coincide con su detalle.

| Código | Conteo 18/10 17:00 | Salidas netas posteriores | Reconstruida al último movimiento | Stock del sistema | Reservado (sistema) | Diferencia (sistema − reconstruida) | Salidas netas el 18/10 antes del conteo |
|---|---|---|---|---|---|---|---|
| 6180005 | 192 | 4 | 188 | 190 | 2 | 2 | 2 |
| 23010008 | 53 | 3 | 50 | 51 | 0 | 1 | 0 |
| 23030010 | 139 | 3 | 136 | 137 | 45 | 1 | 2 |
| 23220015 | 312 | 4 | 308 | 310 | 14 | 2 | 2 |
| 26120367 | 14 | 1 | 13 | 14 | 0 | 1 | 0 |
| 26120813 | 72 | 12 | 60 | 69 | 0 | 9 | 2 |
| 26120815 | 14 | 4 | 10 | 11 | 0 | 1 | 3 |
| 26120825 | 87 | 36 | 51 | 52 | 0 | 1 | 0 |
| 28010019 | 2979 | 5 | 2974 | 2973 | 4 | −1 | 2 |
| 28040010 | 163 | 1 | 162 | 163 | 2 | 1 | 0 |
| 28040013 | 298 | 3 | 295 | 296 | 0 | 1 | 0 |
| 28040026 | 307 | 3 | 304 | 306 | 1 | 2 | 0 |
| 40120090 | 448 | 36 | 412 | 414 | 0 | 2 | 0 |

Qué se investigó y qué no se encontró:
1. **No es una cuestión de documentos:** las ventas posteriores de los 13 son vigentes, del almacén 001, y su kardex equivale a su detalle.
2. **No es la reserva:** la diferencia no sigue a `STOCK_CANTRESERVADA` (23030010 reserva 45 y difiere en 1; 26120813 reserva 0 y difiere en 9).
3. **Solo un caso depende de la hora:** 28010019 (−1) coincidiría si el conteo se tomó antes de las 17:00 (hay una venta a las 16:59). Probando inicios de 09:00 del 18/10 a 12:00 del 19/10, el máximo es 38 de 50 con inicio a las 16:45; los otros 12 no se explican por la hora.
4. **El stock del sistema no es el acumulado del kardex:** solo en 15 de los 50 productos el neto histórico del kardex iguala `STOCK_CANTIDAD`; `INV_STOCK_ARTICULOS` se actualiza por un mecanismo propio que no se pudo explicar con las tablas consultadas.
5. **Mayor desviación, 26120813 (+9):** el sistema bajó solo 3 unidades desde el conteo, aunque el kardex registra 12 vendidas después. Sin evidencia para explicarlo: podría ser un error de conteo, un movimiento fuera de kardex o una venta no descontada.
6. **Riesgo a tener presente:** que 37 de 50 conteos coincidan exactamente con el sistema es compatible con un conteo físico fiel, pero también con uno tomado desde el sistema; con estos datos no se distingue. El conteo sigue siendo «reportado, no verificado».

## 5. Compras 11452 y 11455 (detalle mínimo para consultar a la empresa)
**No se suman a pedidos pendientes.** Ambas están vigentes (estado 2), son del almacén 001 y ya generaron la entrada de kardex (concepto COMPRA) el **13/10/2026** (12:45:26 y 15:22:18), antes del conteo del 18/10. Su fecha de recepción registrada es futura:

| Compra | Fecha de la compra | Recepción registrada | Registrada en el sistema | Entrada al kardex |
|---|---|---|---|---|
| 11452 | 13/10/2026 12:45 | 22/10/2026 12:45 | 15/10/2026 12:47 | 13/10/2026 12:45:26 |
| 11455 | 13/10/2026 00:00 | 23/10/2026 15:22 | 16/10/2026 16:18 | 13/10/2026 00:00 |

La suma de las líneas coincide con la entrada de kardex en los 29 productos. Las cantidades por producto (unidad base, almacén 001):

| Compra | Código | Producto | Unidades | ¿Entre los 50? |
|---|---|---|---|---|
| 11452 | 42050002 | LANOSTERIN NEUTRALIZANTE CREMOSO 1 LT | 36 | NO |
| 11452 | 6160006 | LANOSTERIN LAN WAVE X 250 ML LOCION ANTI-FRIZZ | 60 | SÍ |
| 11452 | 23050035 | LANOSTERIN CREMA D/PEINAR LANOBRIL 240 ML | 56 | SÍ |
| 11455 | 12040036 | SALONIN CHAMPU X 1 LT LISS CONTROL | 52 | SÍ |
| 11455 | otros 24 productos | (detalle en `compras_11452_11455_para_consultar.csv`) | 12–84 c/u | NO |

Existencia reconstruida al 20/10 de los tres productos entre los 50: 797 (6160006), 665 (23050035) y 74 (12040036). En 12040036 el conteo físico del 18/10 (74) coincide con el sistema, lo que sugiere que las 52 u ya estaban al contar, pero **no está confirmado**.

**Preguntas para la empresa:**
1. ¿Qué significa «fecha de recepción» 22/10 y 23/10: llegada esperada, fecha de pago o fecha de registro contable?
2. ¿Esa mercadería ya estaba físicamente en el almacén el 18/10, o aún no llega?
3. ¿Por qué el sistema la ingresó al stock el 13/10?

El plazo promedio compra→recepción de 2,4 días (122 compras de los 50 desde marzo) **no se interpreta** hasta tener estas respuestas.

## 6. Propuesta concreta de actualización (nada se ejecuta sin tu aprobación)
1. **Ventas (versión 2 del dataset):** añadir `octubre.xlsx` como fuente 15, corte de ventas **20/10/2026** (ventana de `promedio_28`: 23/09–20/10), con la misma verificación contra los libros; versión nueva en `plan_*` sin tocar la actual. El 21/10 parcial queda en una colección separada, fuera de la previsión.
2. **Existencias (instantánea reconstruida):** conteo del 18/10 + movimientos del kardex hasta el cierre del 20/10 (`existencia_reconstruida_al_20_10`), con la etiqueta «Reconstruida: conteo reportado + movimientos del sistema; no es un conteo». Los 13 casos discrepantes usan la misma regla y quedan marcados; si la empresa recuenta esos 13, se emite otra instantánea sin tocar la anterior.
3. **Plan (versión 2):** decisión el 21/10, escenarios de 7 y 14 días y mismas reglas; el consumo se proyecta desde el 21/10 con el stock de cierre del 20/10. El plan del 18/10 se conserva como versión 1.
4. **Pedidos por recibir:** ninguno hasta que la empresa conteste (§5); 11452 y 11455 no se cuentan como pedidos.
5. **Comparación:** reporte de cambios v1 → v2 por producto (previsión diaria, compra propuesta, faltantes).
6. **Lo que no se hace:** no se reimportan los libros anteriores, no se corrige el stock del sistema, no se usa el 21/10 parcial para pronosticar, no se interpreta el plazo de 2,4 días y no se publica en Azure/Atlas.

**Decisiones para Rogelio:** (a) aprobar o ajustar los puntos 1–3; (b) responder las preguntas del §5 o indicar que se asuma «sin pedidos por recibir»; (c) decidir si se pide un recuento físico de los 13 productos discrepantes.
