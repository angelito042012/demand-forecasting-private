# Preparación de los 14 Excel — versión académica 1

18/10/2026, Lima. Ejecutor: Codex, por solicitud expresa de Rogelio. Alcance: preparar datos locales antes de un nuevo análisis de Claude. No se importó en Mongo, no se entrenaron modelos, no se alteró T12, no se inició ningún servicio ni se accedió a nube.

## Resultado y ubicación

Paquete privado: `artifacts/private/datos_preparados_v1/` (excluido de Git).

- `00_originales/`: copias idénticas de los 14 Excel. También se conservaron intactos los archivos de `C:\Users\rogel\Documents\Datos`.
- `01_normalizados/`: universo completo en CSV, con esquema común para cantidades, fechas, productos, almacenes, unidades, monedas y procedencia. Compras, ventas, créditos y cuarentena separados. Incluye clasificación completa y candidatos del grupo.
- `02_grupo/`: los 50 productos seleccionados, sus movimientos, balance diario y parámetros.
- `03_excel/01_Ventas_grupo.xlsx`: 12.909 filas de venta y 93 notas de crédito del grupo, separadas.
- `03_excel/02_Compras_grupo.xlsx`: 424 filas de compra del grupo.
- `03_excel/03_Inventario_calculado.xlsx`: saldo por producto, 10.700 balances diarios con fórmulas y supuestos explícitos.
- `03_excel/04_Control_y_decisiones.xlsx`: decisiones, productos elegidos, incidencias y fuentes.
- `manifest.json` y `verification.json`: criterios, huellas, conteos y comprobaciones. Los Excel son vistas de trabajo; los CSV son la interfaz estable para un futuro importador. No cargarlos con el importador antiguo sin adaptar su contrato.

Los campos identificadores permanecen como texto; las cantidades usan unidad base UND, almacén 1. Las monedas se separan en PEN y USD sin convertir importes. Los nombres de productos/categorías conservan el texto fuente, incluso caracteres deteriorados; no se unen productos por nombre ni se inventan correcciones semánticas. Los datos personales de clientes/proveedores no se trasladan a las tablas normalizadas; los originales privados los conservan.

## Aclaración y decisiones sobre incidencias

Estas son decisiones de procesamiento verificables, no explicaciones comerciales confirmadas por la empresa.

| Hallazgo | Tratamiento |
|---|---|
| 1.224 compras con cantidad positiva e importe cero | Conservar unidades e importe cero; clase COMPRA_SIN_CARGO_REGISTRADO. No asumir bonificación ni inventar precio. |
| 6 copias exactas adicionales de líneas de compra | Conservar con grupo de repetición y número de ocurrencia. No hay evidencia suficiente para borrarlas. El balance contempla una sensibilidad sin segundas copias; no cambia el tratamiento principal. |
| Compra de septiembre, fila 175: cantidad 12 e importe −2 PEN | Separar en cuarentena, sin convertirla en devolución o corregir el importe. |
| Venta de septiembre, fila 9517: cantidad 0,01, equivalencia 1 y cantidad base 0 | Separar en cuarentena: la conversión no coincide. No forzar 0 ni 0,01. |
| 664 notas de crédito | Conservar como documentos financieros separados; no inferir devolución física. |
| 10 compras de septiembre en dólares | Identificar USD; mantener separado de PEN. No inventar tipo de cambio. |

Conciliación de las **106.525 filas**: 101.080 ventas + 3.555 compras con importe positivo + 1.224 compras sin cargo registrado + 664 créditos + 2 cuarentenas. Cada fila aparece una sola vez en esta partición. Los importes reconcilian por archivo y moneda, incluyendo las cuarentenas y los créditos; excluir de un cálculo no significa eliminar la evidencia.

No se hizo que compras y ventas tuvieran cantidades iguales. Tampoco se eliminaron ventas por no tener compra coincidente: el inventario anterior a marzo puede explicar parte de esa diferencia y es desconocido.

## Grupo elegido

50 productos del almacén 1, con ventas en cada uno de los cinco meses marzo–julio y compras en al menos dos de esos meses. Hubo 315 elegibles. Se ordenaron por días distintos con ventas, después por unidades vendidas y finalmente por identificador. Se tomaron los primeros 50. Agosto y septiembre no se usan para elegir ni ordenar el grupo.

Son un grupo de productos de venta frecuente, no una muestra representativa de todo el catálogo. Incluye 15 productos para activar el tinte, 8 de fijación/acabado capilar, 7 de higiene capilar, 7 de tinturación, 5 de cuidado capilar, 5 de uñas, 2 acondicionadores y 1 de estuches/ofertas. La lista exacta está en la hoja Productos y en `02_grupo/productos.csv`.

Cobertura marzo–septiembre: 12.909 ventas, 424 compras, 93 créditos y 22.865 unidades vendidas; 13,22 % de las 172.993 unidades vendidas válidas del universo. Ninguna fila en cuarentena ni segunda copia exacta está en este grupo. Esto es una observación posterior, no un filtro de selección.

## Qué saldo se calculó y qué no se obtuvo

No existe un conteo físico proporcionado por la empresa. La preparación no puede producirlo ni certificar que los movimientos físicos están completos. Los campos conteo físico y pedidos pendientes permanecen vacíos, no en cero.

Se construyó un balance retrospectivo condicionado a estas reglas: compras como entradas en la fecha del documento; ventas positivas como salidas; devoluciones físicas y ajustes incorporados iguales a cero por ausencia de evidencia. No se afirma que tales movimientos no existieron. Las notas de crédito no se añaden al stock. FECHA_CONTABLE coincide con FECHA y no prueba plazo de entrega ni fecha de pedido.

Para cada producto, sea C(t) el acumulado de entradas menos salidas desde el 01/03. El saldo inicial mínimo es `max(0, -min(C(t)))`, incluyendo el acumulado inicial cero. El saldo al cierre de cada día es `saldo inicial mínimo + C(t)`. Es el mínimo que evita cierres diarios negativos bajo esas reglas; no resuelve el orden intradiario. Cualquier saldo inicial mayor también sería matemáticamente compatible.

Totales del grupo: saldo inicial mínimo calculado **2.420**, entradas documentadas **49.078**, salidas documentadas **22.865**, saldo calculado al 30/09 **28.633 unidades**. La conservación es 2.420 + 49.078 − 22.865 = 28.633. No es una medición de existencias ni prueba de sobrestock real.

**Este saldo usa toda la trayectoria marzo–septiembre: queda prohibido usarlo como entrada de entrenamiento, como estado inicial de un backtest histórico o como evidencia de rendimiento de T12.** Los días excluidos del pronóstico no se excluyen del balance de movimientos físicos. Los CSV diarios no son observaciones de inventario.

Para un ejercicio posterior se dejaron plazo, revisión y reserva en 7 días y múltiplo en 1 unidad, todos como supuestos configurables no optimizados. No se emitieron recomendaciones de compra. No debe transformarse pedidos pendientes desconocidos en cero por comodidad.

## Validación ejecutada

- 14 originales y 14 copias con SHA-256 coincidentes con la auditoría anterior.
- 106.525 identificadores únicos, partición completa y conciliación de importes por fuente/moneda.
- Exportaciones XLSX releídas: cantidades, fechas e importes del grupo coinciden con la preparación.
- Las 50 filas de saldo y las 10.700 fórmulas diarias exportadas tienen valores calculados coincidentes con el balance independiente.
- 7 pruebas dirigidas: precio cero, compra negativa, conversión incompatible, crédito separado, selección sin información futura, mínimo inicial y efecto de copias/créditos en el balance.
- Revisión visual de los cuatro libros y corrección de textos cortados y formatos numéricos. No se hizo aceptación manual en Microsoft Excel.
- Revisión independiente de metodología realizada antes de construir el paquete; sus observaciones se incorporaron. No se repitieron suites de aplicación ni experimentos.

## Reproducibilidad y siguiente paso

`scripts/prepare_academic_data.py --output <directorio_nuevo>` exige 14 fuentes y sus huellas de la auditoría previa; nunca sobrescribe una versión existente. Usa openpyxl solo para lectura y Decimal para cantidades/importes. `scripts/build_academic_workbooks.mjs` se ejecuta copiado junto al JSON de trabajo, con la dependencia artifact-tool del runtime y ARTIFACT_RUNTIME_ROOT apuntando al runtime Node. `scripts/verify_academic_data.py` verifica la versión entregada sin modificar fuentes.

Antes de modificar la aplicación, revisar este paquete y definir un contrato de importación separado para compras y balances calculados. Las ventas históricas documentadas siguen siendo la fuente para pronóstico. Los datos generados no mejoran por sí mismos la precisión. T12 continúa cerrado con sus resultados originales; cualquier nuevo estudio requiere protocolo y separación temporal propios. No afirmar validación independiente para septiembre, ya inspeccionado en esta preparación.

La preparación técnica está terminada. Integración, nuevo estudio predictivo, aceptación humana y publicación no están realizados ni implícitamente autorizados por estos archivos.
