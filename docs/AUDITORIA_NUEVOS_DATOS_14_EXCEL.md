# Revisión de los 14 Excel: compras y ventas marzo–septiembre

18/10/2026, America/Lima. Revisión de solo lectura solicitada por Rogelio antes de decidir el nuevo alcance. No se importaron datos, no se alteraron originales/bases/modelos, no se repitió T12 ni se accedió a nube. No autoriza adoptar compras como inventario real.

## Fuentes comprobadas

Carpeta `C:\Users\rogel\Documents\Datos`. Exactamente 14 archivos XLSX, todos con una hoja `Hoja1`, encabezados en fila 2. Los seis originales coinciden con los SHA-256 de `AUDITORIA_ARCHIVOS.json`; los 14 hashes seguían idénticos al finalizar. Fechas de documento válidas y dentro del mes/año esperado: marzo–septiembre de 2026. Los nombres se preservan, incluidas las variantes `compra mayo.xlsx`, `compras seitembre.xlsx` y `setiembre.xlsx`.

| Mes | Archivo ventas | Filas ventas (incluye créditos) | Archivo compras | Filas compras |
|---|---|---:|---|---:|
| Marzo | marzo.xlsx | 14 545 | compras marzo.xlsx | 900 |
| Abril | abril.xlsx | 13 979 | compras abril.xlsx | 683 |
| Mayo | mayo.xlsx | 15 458 | compra mayo.xlsx | 667 |
| Junio | junio.xlsx | 12 591 | compras junio.xlsx | 192 |
| Julio | julio.xlsx | 15 790 | compras julio.xlsx | 714 |
| Agosto | agosto.xlsx | 15 074 | compras agosto.xlsx | 650 |
| Septiembre | setiembre.xlsx | 14 308 | compras seitembre.xlsx | 974 |
| **Total** | | **101 745** | | **4 780** |

Ventas mantiene las 31 columnas auditadas. Compras tiene 26: ID_COMPRA, TIPO_DOC, FECHA, FECHA_CONTABLE, SERIE_NUMERO, ID_PROVEEDOR, PRO_RUC, PROVEEDOR, TIPOPAGO, MONEDA, ID_ARTICULO, ARTICULO, ID_ALMACEN, CANTIDAD, PRECIO, BASE_LINEA, IGV_LINEA, TOTAL_LINEA, ID_UM, EQUIVALENCIA, UM_BASE, CANTIDAD_UM_BASE, GRUPO, SUBGRUPO, MARCA y ESTADO.

Claves compartidas: artículo/almacén/unidad base. Todos los registros indican almacén 1, unidad base UND y estado ACTIVO. Los códigos coincidentes tienen al menos una descripción de producto común, normalizando espacios y mayúsculas; no equivale a validación externa de catálogo. No hay columnas de saldo inicial/final de existencias, fecha de pedido, fecha explícita de recepción ni cantidades por recibir. FECHA_CONTABLE y FECHA coinciden en las 4 780 filas de compras: no representan dos hitos diferentes para medir plazo de entrega.

## Controles y excepciones

- Ventas: 664 líneas TIPO_DOC=7, todas negativas; se mantienen separadas como notas de crédito. No implican retorno físico. Las 101 080 líneas positivas son candidatas para series de venta; queda además una línea de importe cero y conversión inconsistente.
- Ventas septiembre, `Hoja1!O9517:V9517`: cantidad 0,01, equivalencia 1, cantidad base 0 e importe 0. Es la única discrepancia de cantidad × equivalencia frente a cantidad base (tolerancia 0,000001) en los 14 archivos. No corregir, redondear ni imputar sin criterio de negocio confirmado.
- Compras: 1 224 líneas de importe cero y cantidades positivas. Podrían ser bonificaciones u otro tratamiento comercial; no concluirlo sin confirmación. Se incluyeron como candidatas de movimiento por sus unidades, separadas de compras con importe positivo. No eliminar por precio cero.
- Compras septiembre, `Hoja1!N175:V175`: cantidad y cantidad base 12, equivalencia 1, importe −2, TIPO_DOC=1. No clasificar automáticamente como nota de crédito ni retorno. Excluida del cruce cuantitativo preliminar hasta aclarar su significado.
- Seis repeticiones exactas de filas de compra: marzo 645/646; abril 443/444; junio 27/28 y 117/118; agosto 40/41; septiembre 774/775. Sin identificador único de línea, identidad completa no prueba duplicación errónea. Se conservaron todas; no deduplicar automáticamente.
- Compras septiembre contiene 10 líneas cuya moneda indica dólares; las demás compras y todas las ventas indican soles. Importes separados por moneda; no sumar ni tratar precio de compra como costo comparable sin revisar impuestos, descuentos, bonificaciones y conversión monetaria.
- Compras: no se observaron diferencias mayores a un céntimo en BASE_LINEA + IGV_LINEA = TOTAL_LINEA. Ninguna conversión de cantidades de compra discrepó; no faltan campos requeridos en los controles de cantidades/clave/fecha. Sin filas idénticas repetidas de ventas.

## Cruce preliminar, sin borrar ni conciliar artificialmente

Criterio de diagnóstico: ventas positivas ACTIVAS con clave/unidad/conversión válidas, sin TIPO_DOC=7; compras ACTIVAS con cantidad positiva y total no negativo, claves/conversión válidas. Retiene compras de importe cero y todas las repeticiones exactas. No constituye un importador aprobado ni confirma recepción física o integridad de los reportes.

| Cobertura | Productos distintos |
|---|---:|
| Ventas candidatas | 4 025 |
| Compras candidatas (4 779 líneas) | 1 973 |
| En ambas fuentes | 1 802 |
| En ventas sin compras registradas en el período | 2 223 |
| En compras sin ventas registradas en el período | 171 |

Restringir ventas a los 1 802 productos comunes conservaría 44,8 % de los productos vendidos y 66,1 % de las unidades base vendidas en el período. Se perdería 33,9 % de las unidades vendidas del análisis restringido. No propone hacerlo: es una medición de cobertura retrospectiva. Un producto puede vender existencias anteriores sin comprarse en marzo–septiembre; otro puede comprarse y no venderse en ese intervalo. Comprar y vender cantidades distintas no es un error que deba limpiarse.

Un eventual grupo operativo se seleccionaría por identificación verificable, saldo real disponible y cobertura de movimientos; no por producir saldos convenientes, igualdad de cantidades ni resultados favorables. Los grupos de una evaluación temporal no pueden definirse usando compras/ventas futuras respecto a su corte. Este cruce retrospectivo no modifica el universo ni los resultados congelados de T12.

## Qué se puede calcular del inventario

La identidad es: **saldo final = saldo inicial conocido + entradas físicas − salidas físicas + ajustes netos**. Los documentos de compras aportan candidatos de entradas, condicionados a su recepción y fecha; las ventas no abarcan necesariamente todas las salidas. Las notas de crédito no prueban movimientos físicos.

Como diagnóstico exclusivamente, se acumuló por producto/almacén/unidad el neto diario compras candidatas menos ventas candidatas, iniciando en cero el 01/03/2026 y sin inferir devoluciones/ajustes. Entre los 1 802 productos comunes:

- 1 406 presentan algún neto diario acumulado negativo.
- 463 mantienen neto negativo al finalizar septiembre.

Estas cifras no son faltantes reales ni inventario real negativo. Muestran la insuficiencia de asumir saldo inicial cero bajo ese cálculo. Incluso un saldo siempre no negativo no prueba stock inicial cero ni movimientos completos. El saldo inicial mínimo matemático para evitar negativos tampoco identifica el saldo real y no debe presentarse como dato de la empresa.

Sin una existencia verificada en al menos una fecha por producto, no hay reconstrucción única del inventario real. Un conteo acotado de productos sería una alternativa a pedir inventario de toda la tienda; requeriría movimientos completos desde esa fecha y reglas/pendientes confirmados antes de recomendar compras. No necesita conexión al sistema, pero sí actualización manual y trazabilidad.

## Conciliación propuesta, aún no ejecutada

1. Mantener originales y procedencia archivo/hoja/fila; separar ventas, créditos y compras.
2. Resolver las excepciones con evidencia o confirmación del encargado; no suprimir filas para forzar igualdad.
3. Confirmar qué fechas representan recepción, qué significan líneas gratuitas y negativas, y si las repeticiones son legítimas.
4. Normalizar identificadores/unidades y conciliar por documento/mes/moneda contra reportes de control de la empresa, si existen. La comprobación interna no acredita que el export esté completo.
5. Mantener universo de pronóstico de ventas separado del universo con información suficiente para reposición. No exigir compras coincidentes para entrenar ventas.
6. Solo tras decidir alcance: diseñar incorporación de septiembre/compras en una versión separada, sin reescribir la evaluación T12, contaminar datos con simulaciones ni activar nuevas recomendaciones como reales.

Decisión pendiente del usuario. No se autoriza nueva carga, entrenamiento, sustitución de inventario ni publicación por esta revisión.

## Evidencia reproducible privada

`artifacts/private/auditoria_14_excel/audit.py` y `audit.json` (ignorados por Git). Python del runtime de la aplicación, openpyxl en modo read_only/data_only y aritmética Decimal. Recorrido de las 106 525 filas; comprobaciones de cantidades, fechas, estado, moneda, duplicación exacta, intersecciones y balance condicional. Se comprobaron identidades agregadas por mes y de movimientos; hashes de los 14 archivos re-verificados al finalizar. Contiene detalle comercial por clave: no publicarlo.
