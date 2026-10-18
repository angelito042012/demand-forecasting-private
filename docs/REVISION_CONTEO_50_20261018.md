# Revisión del conteo recibido de 50 productos

18/10/2026, Lima. Codex. Estado: **apto como inventario físico reportado en una fecha concreta**. Esto no verifica el conteo presencial ni certifica movimientos históricos. La verificación de este informe es documental.

## Fuente y confirmación

Libro recibido: `artifacts/private/datos_preparados_v1/Solicitud_conteo_50_productos.xlsx`, hoja `Conteo_50_productos`.

SHA-256: `608d15a74a58a1157036c4128b52abf74aa0de3d36b68935d07a04a132c740eb`.

El libro declara fecha 18/10/2026, hora 17:00, Almacén Principal, responsable identificado y alcance de estanterías y almacén principal. La frase del libro sobre movimientos solo descarta recepciones. Rogelio confirmó directamente en esta conversación que todas las cantidades corresponden a las 17:00 del 18/10, que no hubo ventas durante el conteo y que Almacén Principal es el almacén 1 de los reportes. El año 2026 se toma de la celda C3; la respuesta escribió «206», interpretado como error tipográfico por coincidencia del contexto y documento. No se cambió la fuente para incorporar estas aclaraciones; se guardaron aparte.

Copia inmutable y derivados vigentes: `artifacts/private/conteo_recibido_20261018_v2/`:

- `Solicitud_conteo_50_productos.xlsx`: copia idéntica del documento recibido.
- `conteo_reportado.csv`: 50 registros normalizados con fecha/hora Lima, cantidades, presentación, almacén, procedencia, huella y confirmaciones.
- `review.json`: metadatos y verificación. `snapshot_ready=true`; `current_replenishment_ready=false`.

La carpeta v1 conserva la revisión anterior a las confirmaciones; para integración usar **v2**. No usar ni regenerar `conteo_builder.mjs`: es el generador de la plantilla vacía y sobrescribiría el documento recibido.

## Comprobaciones realizadas

- Exactamente los 50 códigos del grupo seleccionado, sin repetidos, faltantes ni códigos agregados.
- Nombres y unidad UND coincidentes con la preparación previa; los identificadores se conservan como texto.
- Definición de presentación completa en cada fila. No hay cantidades vacías, negativas, fraccionarias ni fórmulas en las filas de conteo.
- 48 productos con cantidad disponible positiva y 2 con cantidad disponible cero. Reservadas y no vendibles: cero declarado en las 50 filas.
- Suma administrativa: 12.391 unidades de reporte. Incluye presentaciones diferentes y **no equivale a 12.391 artículos individuales sueltos**.
- Los códigos 6020011 y 6020013 están declarados en cajas de 12. El código 9690035 es un pack de dos productos. Conservar caja/pack como unidad declarada del código; no multiplicar las cantidades por 12 o por 2 por el nombre del producto. Para unir movimientos, verificar que su unidad base tenga la misma interpretación; no inferir una equivalencia distinta.
- Original intacto y copia con huella coincidente. No se modificó ninguna base, modelo, serie histórica, congelación o servicio.

## Lo que ahora permite

Persistir y mostrar la existencia reportada por producto y almacén al **18/10/2026, 17:00 America/Lima**. En esta vista corresponde decir «Inventario informado por la empresa» o «Conteo del 18/10/2026». No aplicar la etiqueta de inventario simulado a este documento. La procedencia y fecha deben seguir visibles; una nueva consulta no cambia la fecha del conteo.

Este registro sustituye la ausencia de una medición para esa fecha. No sustituye retrospectivamente los saldos calculados de marzo–septiembre ni los inventarios simulados de T07/T12. No comparar el saldo calculado al 30/09 con el conteo del 18/10 como si fueran la misma fecha, ni crear un ajuste ficticio para hacerlos coincidir. Tampoco inicializar el backtest de agosto con el conteo de octubre.

## Datos que siguen pendientes y alcance de la siguiente etapa

1. Las fuentes de ventas/compras llegan al 30/09. Los días **01–18/10** no están cubiertos. Para un pronóstico operativo originado en el conteo necesitamos ventas actualizadas hasta ese corte; su ausencia no significa ventas cero. Para reconstruir movimientos entre septiembre y el conteo también hacen falta entradas y ajustes de ese intervalo. Para avanzar desde el conteo se registran movimientos posteriores, no es necesario reconstruir marzo para usar el snapshot actual.
2. Pedidos de compra aún por recibir desconocidos: ausencia de documento no equivale a cero. El conteo no los informa. No emitir automáticamente una cantidad de compra como si fueran conocidos; se puede permitir declaración manual fechada y separar escenarios si no existe confirmación.
3. Plazos, frecuencia, reserva y mínimos siguen siendo parámetros configurables bajo supuestos, salvo nueva evidencia empresarial. Las compras documentadas no proporcionan fecha de pedido para medir plazo. No es necesario pedirlos otra vez para **mostrar el inventario**.
4. La aceptación humana, la integración nueva y la publicación siguen pendientes. La recepción del conteo permite retomar implementación local acotada; no autoriza nube ni reentrenamiento.

## Reproducción

`python -m scripts.review_received_count --output <carpeta_nueva> --confirmed-no-sales --confirmed-warehouse-id 1`.

Las opciones de confirmación corresponden a la respuesta humana de esta conversación, no a inferencias automáticas del archivo. El script rechaza sobrescribir versiones existentes. Verificación adicional de CSV contra celdas originales, confirmaciones y SHA realizada en esta entrega; evidencia privada en la carpeta v2.

Siguiente encargo: `ETAPA_18_CLAUDE.md`, integración local de inventario fechado, manteniendo los límites anteriores.
