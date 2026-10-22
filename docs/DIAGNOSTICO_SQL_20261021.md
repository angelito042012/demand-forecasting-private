# Diagnóstico de SYDESOFT_2 (SQL Server restaurado) y octubre.xlsx — 21/10/2026

Alcance: **solo lectura** (consultas `SELECT` y metadatos desde `sqlcmd -E`), sin importar nada en la aplicación, sin reemplazar el plan de noviembre, sin tocar permisos, protocolos ni configuración. Evidencia privada en `artifacts/private/sql21/` (tablas y filas, columnas, cobertura, conciliaciones). No se extrajeron datos personales de clientes, usuarios ni proveedores.

## 1. Conexión
- Instancia predeterminada `Rogelio` (servicio `MSSQLSERVER` en ejecución), autenticación de Windows con el usuario de esta sesión: **conecta** (`-C` solo confía en el certificado del cliente; no se cambió nada en el servidor). Codex recibió acceso denegado desde su sesión; no se intentó cambiar eso.
- La sesión tiene rol de administrador del servidor; se usó únicamente para leer. Hay otras dos bases en la instancia (`EFACT_2`, `MULTICOMPANY`) que **no se examinaron**.
- `SYDESOFT_2`: 146 tablas, ONLINE, creada el 21/10/2026 18:14 (restauración).

## 2. Estructura relevante (productos, almacenes, existencias, ventas, compras, pedidos)
| Concepto | Tabla(s) | Claves y campos clave | Filas |
|---|---|---|---|
| Productos | `DM_ARTICULOS` | `ID_ARTICULO` (**8 caracteres con ceros a la izquierda**, p. ej. `03110044`; los libros y la app lo escriben sin ese cero: `3110044`), `ART_DESCRIPCION`, `ID_UMBASE`, `ART_FLGESTADO`, categoría/marca | 12 497 |
| Almacenes | `DM_ALMACEN` | `001` ALMACEN VENTA (stock de venta), `002` almacen2 (virtual), `009` alm de devoluciones | 3 |
| Existencias | `INV_STOCK_ARTICULOS` | (`ID_ARTICULO`, `ID_ALMACEN`, `STOCK_TIPOREGISTRO`=2) `STOCK_CANTIDAD`, `STOCK_CANTRESERVADA` | 12 496 (alm. 001: 12 476; 4 748 con stock ≠ 0) |
| Movimientos de existencias | `KARDEX` | `KAR_FECHA`, `KAR_CONCEPTO` (VENTA, COMPRA, ENTRADA/INVENTARIO, SALIDA/INVENTARIO, NOTA CREDITO VENTA), `KAR_ECANTIDAD`/`KAR_SCANTIDAD`, `ID_VENTA`/`ID_COMPRA` | 1 356 727 |
| Ajustes de inventario | `MOVINV_CAB` / `MOVINV_DET` | fecha **sin hora** | 52 733 / 114 832 |
| Ventas | `VENTA` + `DETALLE_VENTA` | `VEN_FECHA_DOCUMENTO`, `ID_TIPO_DOCUMENTO` (01 factura, 03 boleta, 07 nota de crédito, 12 ticket), `VEN_ESTADO`, `DET_VEN_CANTIDAD` × `DET_VEN_EQUIVALENCIA`, `ID_ALMACEN` | 713 461 / 1 270 980 |
| Pedidos de clientes | `PEDIDO` + `DETALLE_PEDIDO` | pedidos de venta (no de compra) | 767 833 / 1 285 074 |
| Compras | `COMPRA` + `DETALLE_COMPRA` | `COM_FECHA`, `COM_FECHA_RECEPCION`, `COM_FECHA_REGISTRA`, `COM_ESTADO`, `ID_ARTICULO`, `ID_ALMACEN` | 3 470 / 43 836 |
| Órdenes de compra | `ORDEN_COMPRA` + `DETALLE_ORDEN_COMPRA` | tienen `DET_ORD_COM_SALDO` | **2 / 2, ambas de 2019: no se usan** |
| Proveedor por artículo | `DM_ARTICULO_PROVEEDOR` | `APR_ULT_FECHA_OC`, `APR_ULT_FECHA_RECIBO` | 6 703 (para los 50: 31 filas, **ninguna** con fecha de OC) |

Relaciones: `VENTA.ID_VENTA → DETALLE_VENTA.ID_VENTA`; `COMPRA.ID_COMPRA → DETALLE_COMPRA.ID_COMPRA`; `KARDEX.ID_VENTA / ID_COMPRA` enlaza cada movimiento con su documento; `(ID_ARTICULO, ID_ALMACEN)` une kardex, existencias y detalles.

## 3. Cobertura temporal y corte del respaldo
- Última venta: **21/10/2026 16:26:38**; último movimiento de kardex: 21/10/2026 16:26:38. El respaldo equivale a **~16:30 del 21/10**, coherente con lo informado (~17:00). Es un corte **parcial del día 21** (hasta 16:26).
- Ventas: del 26/04/2019 al 21/10/2026, con meses completos de 2021-08 a 2026-09 (6 800–11 100 documentos/mes). Octubre 2026 (1–21) tiene 5 775 documentos.
- Estados de venta: `VEN_ESTADO=2` es el documento vigente (≈99,9 %); `0/1` anulados/otros.
- Compras: 3 376 vigentes (estado 2) hasta el 20/10/2026.

## 4. Coherencia con los libros Excel
- **setiembre.xlsx vs SQL (documentos vigentes, 01–30/09):** líneas y unidades **idénticas** en los cuatro tipos de documento (396 / 13 257 / 104 / 551 líneas; 1 246 / 21 013 / 180 (nota de crédito, el libro la guarda negativa) / 843 unidades; importes iguales). La base reproduce el libro de septiembre.
- **octubre.xlsx vs SQL (01–20/10):** **idénticas** (268 / 8 940 / 88 / 557 líneas; 863 / 14 307 / 164 / 890 unidades; importes iguales). El libro termina el **20/10**; la base añade el **21/10 parcial** (318 líneas, 621 unidades) que **no está en el libro**.
- Conclusión: el libro de octubre y la base son consistentes; la base cubre un día más (parcial).

## 5. Existencias: lo que se puede y no se puede interpretar como stock
- Los 50 productos del conteo existen en `DM_ARTICULOS` y en `INV_STOCK_ARTICULOS` (almacén 001), usando el código de 8 caracteres.
- Conciliación: conteo del 18/10 17:00 + entradas − salidas del kardex posteriores a esa hora vs `STOCK_CANTIDAD` al 21/10: **37 de 50 coinciden exactamente**; 13 difieren en −9 … +1 unidades (suma −23). Posibles causas, **no verificadas**: ajustes de inventario con fecha sin hora (`ENTRADA/INVENTARIO`, `SALIDA/INVENTARIO` a las 00:00), ventas o ajustes entre el conteo y su registro, o error de conteo. No se interpreta como error de nadie.
- `INV_STOCK_ARTICULOS` es el stock del **sistema** (contable/de venta), no una verificación física. Solo el conteo del 18/10 es físico (y reportado).
- **Pedidos pendientes:** no existe una tabla utilizable (`ORDEN_COMPRA` solo tiene 2 filas de 2019). Hay 2 compras ya **registradas y con ingreso a existencias** pero con `COM_FECHA_RECEPCION` futura: 11452 (22/10) y 11455 (23/10); afectan a 06160006 (60 u), 23050035 (56 u) y 12040036 (52 u), tres de los 50. El kardex ya las sumó el 13/10, por lo que el stock del sistema **podría incluir mercadería aún no recibida**. Qué significa exactamente esa fecha (recepción esperada, fecha de pago, etc.) **no está confirmado**: requiere la respuesta de Rogelio.
- Plazo observado compra → recepción (122 compras 2026-03…10 de los 50): promedio 2,4 días (0–33), lo que contrasta con los plazos 7 y 14 usados en el plan; sin confirmar su significado no se usa.

## 6. Datos aprovechables
1. **Ventas 01–21/10/2026** (libro hasta el 20/10; base hasta el 21 16:26): cierran el hueco de octubre y permiten un nuevo corte de ventas.
2. **Stock del sistema al 21/10** y kardex posterior al conteo: útil para conciliar contra el conteo físico, no para reemplazarlo sin decisión.
3. **Compras con fecha de recepción** (histórico y 2 futuras): candidatas a «pedidos por recibir», sujetas a confirmación.
4. Historia más larga (desde 2021-08 completo) para evaluar `promedio_28` y estacionalidad si se decide.

## 7. Límites y decisiones pendientes (de Rogelio)
- Qué significa `COM_FECHA_RECEPCION` futura (11452 y 11455) y si esos 3 productos ya están físicamente en el almacén.
- Si el 21/10 parcial debe entrar (corte 20/10 completo vs 21/10 a las 16:26).
- Si se usa el stock del sistema al 21/10 o se mantiene el conteo físico del 18/10 más movimientos.
- Qué hacer con las 13 diferencias de conciliación.
- Nada se importó ni se reemplazó; el plan de noviembre, la base `df_ens19…`, los libros originales, la base restaurada y las demos 8443/8444/8445 siguen intactos. Aceptación humana: **pendiente**.
