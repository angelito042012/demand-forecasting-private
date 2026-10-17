# Revisión de la primera entrega de Claude

Resultado: avance comprobado; T03 requiere correcciones antes de aprobarlo. No iniciar entrenamiento. Mantener los Excel y la base actual intactos durante la corrección; probar en bases temporales aisladas.

## Evidencia comprobada por Codex

- Se revisaron importer.py, reconcile.py, calendar.py, catalog.py, API/configuración y pruebas.
- Suite existente con RUN_REALDATA=1: **19 passed, 1 warning**, 22,32 segundos. Se desactivó la carga automática de plugins externos de pytest durante esta ejecución. El aviso es de deprecación de la integración httpx/Starlette; no causó fallo.
- Comparación independiente de las filas y sumas monetarias de cada Excel contra agregaciones de sales y credit_notes en demand_forecasting_dev: coinciden los seis meses, tanto ventas como créditos. Esta verificación no equivale a conciliación contra un reporte contable externo de la MYPE.
- Las reproducciones adicionales usaron datos sintéticos y una base temporal exclusiva, eliminada al finalizar. No se modificó la base del proyecto ni los Excel originales.
- No se entrenaron modelos ni se eligieron hiperparámetros con agosto. La inspección de sus conteos e importes es control de importación.

## R01 Prioridad alta — no ocultar errores de escritura

Ubicación: pipeline/data/importer.py, función _bulk, captura de BulkWriteError alrededor de la línea 286.

La captura trata cualquier BulkWriteError como si fuera una carrera por duplicado: suma nUpserted y considera todo lo restante ya existente. Reproducción: una colección que devuelve error de validación de documento, código 121, con nUpserted=0, hace que _bulk devuelva (0, 1) en lugar de propagar el error. La invariante insertadas + existentes = aceptadas es tautológica con ese cálculo y no detecta pérdida.

Corregir: distinguir duplicados recuperables de errores de validación, autorización, escritura y write concern. Verificar la existencia/equivalencia de cada duplicado recuperado y propagar los demás errores para marcar la carga failed. No anunciar completed con operaciones desconocidas o fallidas. Conservar recuperación tras escritura parcial y reintento.

Pruebas mínimas: error 121, error de write concern, lote mixto con escritura parcial y fallo real, duplicado concurrente legítimo y reintento. Comprobar tanto estado de importación como contenido persistido.

## R02 Prioridad alta — identidad de notas de crédito

Ubicación: pipeline/data/importer.py, construcción de linea_id de notas alrededor de la línea 359.

La clave usa solamente nombre del archivo y fila. No representa la identidad de la nota:

1. Cargar marzo.xlsx con NC-1 por −5,50 en una fila; reemplazar el archivo por NC-2 por −9,00 en la misma fila y nombre; importar de nuevo. Resultado observado: insertadas=0, existentes=1 y en la base sigue solamente −5,50. Una nota nueva se pierde silenciosamente.
2. Reexportar NC-1 con otro nombre/formato. Resultado observado: dos notas por −5,50, duplicando el mismo movimiento lógico.

Corregir: definir identidad consistente con documento (tipo/serie/número mediante hash), almacén/SKU, cantidades/importes normalizados y ocurrencia para líneas iguales legítimas; separar identidad de procedencia. Una versión corregida de una transacción debe detectarse como conflicto/versionado, nunca desaparecer ni añadirse silenciosamente como otra transacción. Si el export no permite decidir identidad de forma segura, registrar conflicto explícito y requerir resolución del caso, sin adivinar. Un cambio de hash no prueba que todas las filas sean nuevas.

Pruebas mínimas: nota idéntica reexportada/renombrada/reordenada; nota distinta en misma fila y nombre; documento corregido; dos líneas idénticas legítimas; recarga exacta; archivos solapados. Conservar trazabilidad de todas las fuentes reconocidas.

## R03 Prioridad media — conciliación de archivos solapados

Ubicación: pipeline/data/reconcile.py, suma filas_leidas por SHA alrededor de la línea 46 y cuadra_filas alrededor de la línea 78.

Se suman las filas de cada archivo distinto, pero se comparan con ventas/créditos únicos en la base. Dos archivos con una misma venta y distinto hash contabilizan dos filas leídas y una venta persistida. El indicador deja de cuadrar aunque la deduplicación sea correcta. En la reproducción combinada se obtuvieron filas_leidas=5, ventas=1, notas_credito=2, rechazos=0 y cuadra_filas=false.

Corregir: separar conciliación por importación (leídas = aceptadas + rechazadas; aceptadas = insertadas + existentes/conflictos según estado) y conciliación del conjunto lógico único. No comparar suma de entradas repetidas con entidades únicas. Contar rechazos y fuentes de forma consistente; distinguir datos de cargas fallidas/incompletas. Añadir una prueba de conciliación tras reexportación y tras reintento.

## Condiciones para la siguiente etapa

1. Resolver R01–R03 con pruebas de regresión antes de completar T03.
2. Antes de construir features de T04/T05, crear una función central de acceso a entrenamiento que impida incluir agosto y aplique el corte del fold. La constante LAST_TRAIN_DATE por sí sola no filtra consultas. Excluir los tres días acordados del objetivo/métricas sin comprimir calendario.
3. Probar que cambiar registros posteriores al corte no modifica el dataset, catálogo o features anteriores. Mantener agosto accesible solo por una ruta de evaluación explícita cuando corresponda.
4. T01 está parcial: Angular sigue pendiente. No bloquear las correcciones de datos por ese problema. Registrar diagnóstico acotado del registro npm; no desactivar TLS ni instalar desde espejos no verificados.
5. No integrar sintéticos como ventas reales. La preparación del escenario ya existe; su integración operativa corresponde a otra tarea.

No se pide todavía autenticación completa, entrenamiento ni nuevas pantallas en esta corrección. El healthcheck existente prueba forma de respuesta, pero su caso denominado éxito admite base unavailable; mejorar esa aserción cuando se amplíe la verificación de disponibilidad.

## Entrega requerida para segunda revisión

Actualizar ESTADO.md con correcciones, pruebas nuevas, resultado completo de la suite y evidencia. Revalidar conteos e importes en una base temporal creada desde cero y luego repetir la importación. Mantener la base actual sin migraciones destructivas: cualquier cambio de claves requiere estrategia explícita antes de aplicarse a los datos existentes. Presentar siguiente revisión y detenerse antes de entrenar.
