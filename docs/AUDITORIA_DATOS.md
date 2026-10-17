# Auditoría actualizada de los seis Excel

Segunda revisión del 16/10/2026. Origen: `C:\Users\rogel\Documents\Datos`. Inspección de solo lectura de todas las filas. Los hashes verifican que marzo–julio fueron reemplazados y agosto permanece idéntico. Esta revisión sustituye el diagnóstico anterior de formatos incompatibles.

## Resultado principal

Los seis archivos tienen una hoja Hoja1, encabezados en la fila 2 y las mismas 31 columnas. Todos incluyen ID_ARTICULO, CANTIDAD, PRECIO, TOTAL_LINEA, GRUPO, ID_ALMACEN, EQUIVALENCIA y CANTIDAD_UM_BASE. El bloqueo por falta de detalle de marzo–julio está resuelto. Es posible preparar series por producto/categoría, después de aplicar las reglas de limpieza.

| Mes | Filas de datos | Líneas positivas identificadas | Líneas negativas | SKU con líneas positivas | Días con registros |
|---|---:|---:|---:|---:|---:|
| marzo | 14545 | 14456 | 89 | 2510 | 31 |
| abril | 13979 | 13907 | 72 | 2524 | 28 |
| mayo | 15458 | 15380 | 78 | 2476 | 31 |
| junio | 12591 | 12510 | 81 | 2401 | 29 |
| julio | 15790 | 15678 | 112 | 2434 | 31 |
| agosto | 15074 | 14946 | 128 | 2364 | 31 |

Total: **87 437 filas**, 86 877 con importe positivo y 560 con importe negativo. Hay 3899 identificadores de artículo distintos en el conjunto, incluyendo todas las filas. Los SKU mensuales no deben sumarse porque se repiten entre meses.

## Comprobaciones y asuntos pendientes

- Todas las fechas son válidas y pertenecen al mes y año del archivo. Todos los registros indican estado ACTIVO y tienda 1. Esto no sustituye una conciliación con el sistema de origen.
- No faltan artículo, cantidad, grupo, almacén, equivalencia ni cantidad base en los campos auditados. No se encontraron filas completamente idénticas repetidas dentro de cada hoja; esto no descarta duplicados semánticos.
- La unidad base normalizada es UND. Se comprobó cantidad × equivalencia = cantidad base en las 87 437 filas con tolerancia 0,000001, sin diferencias ni equivalencias no positivas. Normalizar mayúsculas/minúsculas y mantener la unidad original para trazabilidad.
- Las 560 líneas negativas son TIPO_DOC=7 y tienen ID_PEDIDO=0. El usuario confirmó posteriormente que son notas de crédito. No eliminarlas automáticamente ni deduplicarlas por ID_PEDIDO.
- No hay registros del 3 y 12 de abril ni del 7 de junio. El usuario pidió omitirlos; excluirlos de entrenamiento y métricas, manteniendo un calendario explícito, sin afirmar cierre ni imputar cero.
- Un identificador de artículo aparece asociado a más de una categoría durante el período. Se resuelve para modelado con categoría conocida al corte y conservación de la etiqueta original; ver DECISIONES_DATOS.md.
- La auditoría no demuestra que el export incluya todas las transacciones del negocio. Conciliar cantidades, importes y estados con un reporte de control de la MYPE.

## Discrepancia con el DOCX

Agosto no cambió. Continúa teniendo 14 946 líneas positivas identificadas, 2364 SKU, 34 grupos y una suma de importes positivos de S/ 422 736,88. Esta suma no es venta neta: no incluye las 128 líneas negativas ni una depuración contable. El DOCX describe 755 líneas, 516 SKU, 25 categorías y S/ 20 328,10. Aclarar filtro, versión o subconjunto antes de actualizar el informe; no reutilizar su Pareto como si representara el archivo actual.

## Qué ya permite hacer y qué falta

Se puede implementar el importador, el perfil de calidad, la serie diaria y la comparación de baselines y modelos. Marzo–julio se destinan al desarrollo con validación temporal interna; agosto queda reservado para evaluación predictiva final. La inspección estructural realizada sobre agosto no debe convertirse en selección de modelos o ajuste de hiperparámetros.

No se encontraron campos de saldos de stock, movimientos de inventario, compras pendientes, plazos de entrega o costos de adquisición. ID_ALMACEN solo identifica el almacén; no expresa existencias. Las columnas de proveedor no aportan por sí mismas política o lead time. Por ello, la evaluación operativa real de quiebres, sobrestock y rotación sigue dependiendo de información adicional.

## Evidencia y reproducción

AUDITORIA_ARCHIVOS.json conserva columnas, conteos, fechas, estados y hashes. CAMBIOS_DATOS.json compara hashes anteriores y actuales. AUDITORIA_SEMANTICA.json resume las comprobaciones de equivalencias, unidades y categorías. El script scripts/audit_inputs.py reproduce la auditoría estructural sin modificar los Excel ni exportar datos de clientes.

Localizadores: encabezados Hoja1!A2:AE2 en cada archivo; filas de datos desde la 3 hasta marzo.xlsx: 14547, abril.xlsx: 13981, mayo.xlsx: 15460, junio.xlsx: 12593, julio.xlsx: 15792, agosto.xlsx: 15076. Columnas usadas: FECHA D, ID_ARTICULO L, ID_ALMACEN N, CANTIDAD O, PRECIO P, TOTAL_LINEA R, EQUIVALENCIA T, UM_BASE U, CANTIDAD_UM_BASE V, GRUPO W, VEN_ESTADO Z.

## Resoluciones posteriores

Los cuatro puntos de consulta fueron cerrados por el usuario y documentados en DECISIONES_DATOS.md. El inventario real no fue recibido: se autorizó y generó un escenario sintético separado. Esto permite desarrollo y comparación de escenarios, sin equivaler a evidencia empírica.
