# Estrategia de claves, versionado y migración (importador, esquema v2)

Propuesta técnica del integrador, pendiente de revisión de Codex. No aplicada a `demand_forecasting_dev`.

## Identidad de una línea (esquema v2)

`linea_id = sha256("v2|kind|doc_hash|pedido|fecha|sku|almacen|cantidad|cantidad_base|precio|importe|k")`

- `kind`: S (venta) o N (nota de crédito). `doc_hash = sha256(tipo_doc|serie_numero)`; la serie y el número no se guardan en claro.
- Los números se normalizan (5, 5.0 y 5.00 son iguales); la fecha es el día de negocio.
- `k` es la ocurrencia de la misma tupla dentro del archivo, en orden de fila: dos líneas idénticas legítimas no se fusionan.
- **No** entran nombre de archivo, fila ni sha. Esa **procedencia** vive aparte en `sources[]` (`$addToSet`), y `source_file/sha/row` de nivel superior registran solo la primera fuente. Una línea vista por varias exportaciones conserva todas las fuentes reconocidas.
- Datos reales: cada documento tiene una sola fecha, no hay serie vacía y ningún documento está a la vez en ventas y créditos (comprobado en la base actual, solo lectura).

## Conflictos (no se adivina)

Si el documento (`doc_hash`) ya existe, cargado primero por **otra** fuente, y el archivo trae líneas nuevas de ese documento, esas líneas **no se insertan**: se guardan en `import_conflicts` (estado OPEN, con líneas nuevas y existentes) y la importación queda `completed_with_conflicts` (código de salida 2 en el CLI). Cubre documento corregido y documento dividido entre exportaciones; ambos requieren resolución manual (aceptar la versión nueva, mantener la anterior o fusionar), cuyo procedimiento está pendiente de diseñar. Una línea que desaparece de un archivo reemplazado no se detecta: el export no permite saber si fue anulada.

Límite: si un archivo solapado trae solo parte de un grupo de líneas idénticas, se asume que son las primeras `k`.

## Escrituras y fallos

Solo la clave duplicada (11000) por carrera de upsert se reintenta. Validación (121), permisos, write concern y errores sin detalle detienen la carga como `failed`. Cada lote se verifica contando documentos persistidos. Una recarga posterior completa sin duplicar.

## Migración de la base actual (no ejecutada)

`demand_forecasting_dev` contiene 86 877 ventas y 560 créditos con claves **v1** (`schema_version` 1). El importador v2 se niega a escribir sobre ella (`IncompatibleSchemaError`) para no duplicar todo con claves distintas. Estrategia propuesta, no destructiva:

1. Crear una base nueva (p. ej. `demand_forecasting_v2`) y cargar los seis Excel originales con el importador v2; los originales son la fuente inmutable.
2. Comparar con la base v1: conteos y sumas por mes, y la correspondencia por (hash de documento, fecha, SKU, cantidad, importe). Sin diferencias esperadas.
3. Cambiar `MONGODB_DATABASE` a la nueva base solo tras aprobación explícita. La v1 se conserva (o se respalda con `mongodump`) hasta confirmar; borrarla es una decisión aparte.

Pendiente: cualquier colección derivada (series, catálogos persistidos) deberá regenerarse desde la base v2.
