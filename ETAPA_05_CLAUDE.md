# T07: horizontes de reposición y simulación en desarrollo

Lee RETOMAR_CLAUDE.md, docs/ESTADO.md, TRASPASO.md, REVISION_CODEX_05.md y DECISIONES_DATOS.md. T06 aceptado al commit 3b11fbd como experimento, sin ganador ML por SKU. No repetir T04–T06 ni entrenar de nuevo sus cinco folds. Agosto sigue reservado; no leer sus ventas ni los movimientos sintéticos de agosto para este encargo. Fecha límite global: 23/10/2026, Lima.

## 1. Prerrequisito pequeño: inferencia coherente

Corrige el límite señalado en REVISION_CODEX_05.md antes de reutilizar inferencia: comprobar ctx.start y fin real contra inicio/corte del paquete, dimensiones de matrices y longitud/identidad de entidades; construir códigos con el vocabulario guardado, sin reajustarlo silenciosamente al inferir. Guardar/validar versión de features, horizonte entrenado y contexto requerido. Rechazar entradas incompatibles con mensaje útil. Pruebas de contexto desplazado con igual longitud, vocabulario reordenado/desconocidos y serialización. Preservar compatibilidad explícita o rechazar paquetes antiguos; no alterar los artefactos T06 ni afirmar que se regeneraron.

## 2. Protocolo y configuración antes de resultados nuevos

Crear y comprometer docs/T07_PROTOCOLO.md y config/t07_config.json antes de evaluar. Registrar hipótesis, población, horizontes, pesos de asignación, calendario de revisiones, ecuaciones, métricas, reglas de comparación, seeds y cómputo. Cambios posteriores se declaran como enmiendas; no ocultar resultados desfavorables. Conservar el código/artefactos T06 por versión y hashes.

**Horizontes**: revisión R=7 días, lead time L=3/7/14; protección H=L+R=10/14/21. Evaluar H máximo 21 con resultados acumulados a 10, 14 y 21. No multiplicar el pronóstico de 7 días ni reutilizar un modelo entrenado solo en h<=7 como si cubriera 21.

**Folds de desarrollo**: cortes 31/05, 14/06, 28/06 y 10/07/2026; cada bloque comprende los 21 días naturales siguientes, terminando el último el 31/07. Expansión desde marzo, calendario/máscaras originales. Los bloques se solapan: describir dependencia, sin pruebas de significación que presupongan independencia ni duplicar sumas como unidades únicas. Cohortes por corte según T05; conservar primaria, corta y desconocidos, ceros y universo común entre candidatos.

**Métodos acotados**:

- promedio_28 por SKU, referencia no nula provisional. Mantener control cero en métricas predictivas, sin convertirlo en política de compra.
- Random Forest global por categoría, parámetros fijos de T06 (100 árboles, cuatro hilos y seed existente), entrenado directamente con h=1..21; luego asignación a SKU. No otra búsqueda, XGBoost ni RF global por SKU en este incremento.
- Pesos por SKU: proporción de unidades positivas de los 28 días anteriores al origen dentro de su categoría/almacén, solo productos conocidos. Si toda la categoría suma cero, usar proporción histórica hasta el origen; si sigue sin masa, reparto uniforme entre conocidos. Declarar esos fallbacks y sus conteos. Asignar a todos los SKU conocidos antes de filtrar cohortes para métricas; verificar conservación del total de categoría. Mantener cantidades continuas hasta convertirlas en pedidos.

Features/etiquetas siempre conocidas al origen histórico. Para h>7, el mismo día de semana debe buscarse en la última semana **ya observada**: índice o+h-7*ceil(h/7), y siete días antes para el segundo rezago; nunca o+h-7 si cae en futuro. Versionar la semántica extendida. Orígenes de entrenamiento deterministas cada tres días, etiquetas <= corte, todos los horizontes hasta 21 y ceros válidos. Catálogo y pesos por corte; no usar clasificación o ventas futuras para construir muestras antiguas. Si el catálogo requiere cambios internos por origen, resolverlo o registrar/rechazar el caso, sin anticipar cambios conocidos al corte final.

Reportar WAPE, MAE, RMSE, sesgo y cobertura diaria/acumulada por fold/nivel/cohorte; cobertura de asignación y nuevos. Regla provisional del candidato distribuido: criterio primario SKU acumulado H=14, mejora relativa >=2% frente a promedio_28, >=3/4 folds favorables y |sesgo|/observado<=0,25. Si denominadores son cero, declarar no evaluable. Mantener también H10/H21 y categoría: no seleccionar por el horizonte más favorable. Una eventual ventaja predictiva no implica mejor inventario. No congelar todavía selección para agosto.

## 3. Simulador con escenarios idénticos entre políticas

Implementar motor determinista y auditable, con ejecución continua del **01/06 al 31/07/2026**, inicialización con datos <=31/05. Universo fijo: SKU conocidos al 31/05; catálogo fijado para este experimento al mismo corte. Entrenamiento y agregados posteriores deben respetar ese universo/catálogo fijo. Nuevos productos excluidos se reportan aparte con su cobertura; no se inventa stock/historia. No reutilizar stock/costos/medias de reference_v1 calculados con julio: generarlos por separado con datos anteriores al inicio. No modificar el escenario de agosto existente.

Comparar tres políticas, sin asumir ganadora:

1. Referencia fija sintética: demanda diaria media previa de 28 días congelada al 31/05, objetivo ceil(media_inicial*(L+R+S)). No es política real de la empresa.
2. Pronóstico promedio_28 actualizado al origen de cada revisión: objetivo ceil(suma_pronóstico_próximos_H + S*media_histórica_28_al_origen).
3. RF categoría distribuido: misma ecuación, sustituyendo solo el pronóstico; exactamente la misma seguridad, reglas, costos e inicialización que la política 2.

Escenario principal L=7, S=7; matriz predefinida L en {3,7,14}, S en {0,7,14}, R=7. Mostrar los nueve escenarios completos. S expresa días de buffer calculado con historia pasada, no días adicionales de etiquetas futuras. Para cada escenario, stock inicial ceil(media_inicial*(L+R)) y tránsito inicial cero, iguales entre políticas. Costo unitario supuesto =65% de mediana de precio base positiva conocida <=31/05; holding supuesto 20%/365. Declarar reglas para precio ausente sin usar futuro. No cambiar supuestos según el resultado.

Cada día natural: recibir pedidos vencidos, atender demanda proxy de ventas positivas, registrar ventas atendidas/faltantes perdidos, revisar al final de los días 1,8,15,... desde 01/06. Pedido ceil(max(0,objetivo-(disponible+tránsito))); recepción en fecha_pedido+L. Sin backorders ni devoluciones físicas por notas de crédito. Empaque/mínimo=1. Saldo y posición nunca negativos. Documentar el orden temporal exacto y cómo se valoran holding, stock terminal y pedidos pendientes.

El 07/06 enmascarado no contiene demanda conocida: omitir su evento de demanda y sus denominadores de servicio, conservando calendario, recepciones, revisiones y paso del tiempo. No escribirlo como venta observada cero. Declarar explícitamente que no descontar demanda desconocida es un supuesto del escenario y limita los estados posteriores. Preservar las otras máscaras en entrenamiento.

En revisiones, cada método usa historia observada común disponible hasta ese día, incluida su demanda proxy histórica; nunca días posteriores. No realimentar solo ventas servidas por cada política porque cambiaría la señal entre políticas; explicar que es un escenario con demanda proxy exógena observada después de cada día. Reajustar RF por origen de revisión cuando corresponda, con etiquetas <=origen y vocabulario/paquete coherentes. Reutilizar esos pronósticos entre los nueve escenarios: no volver a entrenar por escenario. Conservar timestamps de origen, rango objetivo y trazabilidad. Las predicciones pueden cubrir fechas posteriores al 31/07 para calcular pedidos terminales, pero no consultar sus reales ni evaluarlas como observaciones.

Métricas: unidades proxy elegibles, atendidas/perdidas, fill rate ponderado, días-SKU con faltante sobre días evaluables, stock medio/final, pedidos/recepciones/tránsito final y holding supuesto. Separar desembolso de compras de costos consumidos; no llamar ahorro o utilidad a reducir compras dejando faltantes/stock terminal diferentes. Diferencias absolutas y relativas frente a la referencia y frente a promedio_28, con denominadores válidos. Reportar total y cohortes iniciales; comprobar conservación por SKU/día y sistema. No convertir días excluidos en servicio perfecto. Repetir motor con las mismas entradas y comprobar identidad.

## 4. Pruebas con significado y evidencia

Casos manuales pequeños: llegada exacta con L, revisión semanal, tránsito evita pedido duplicado, faltante perdido, demanda cero/ausente, redondeo, saldo/conservación, stock y tránsito terminal, costos. Pruebas de fuga: cambiar datos posteriores al origen no cambia forecast/pesos/pedido ya emitido; escenarios iniciales no dependen de junio/julio; h=8/14/21 no leen futuro; etiquetas dentro de corte. Probar conservación categoría→SKU y vocabulario/fechas de inferencia.

Una integración real acotada valida el mismo universo entre políticas, fechas, máscaras, fuentes aprobadas y hashes, sin leer agosto. Ejecutar pruebas nuevas y verificaciones pertinentes; una suite integral al cierre si los cambios compartidos lo justifican, no múltiples repeticiones sin cambios. Sin volver a ejecutar T06 completo. Si el cómputo resulta excesivo, registrar el problema y una modificación determinista antes de evaluarla, no muestrear según resultados.

Predicciones, modelos, movimientos, pedidos, series y logs en artifacts/private/t07/, ignorado. Versionar protocolo/config, T07_RESULTADOS.md, T07_METRICAS.json y T07_MANIFIESTO.json con hashes de fuentes/fingerprints, código, config, modelos y predicciones, versiones/seeds/tiempos y bases utilizadas. Manifiesto vincula cada métrica con su artefacto. Registros comerciales no entran en Git. Etiqueta visible: **Inventario simulado con supuestos; no corresponde al inventario real de la empresa**.

## 5. Entrega y límites del incremento

Corregir 22954→23026 en el resumen T06 de ESTADO.md; no cambiar métricas históricas correctas. Actualizar ESTADO/TRASPASO/BACKLOG/HISTORIAL con commits, pruebas realmente ejecutadas, resultados desfavorables y límites. Commit local revisando exclusiones. Respuesta breve, evidencia extensa en archivos.

No abrir agosto ni modificar su selección, no compras reales ni gasto externo. No declarar mejoras reales o aplicación completa. API/autenticación, conexión de pantallas, publicación y entrega siguen después: no añadir otro frente en este incremento si retrasa el núcleo de T07. Puede delegarse motor y pruebas independientes hasta tres trabajadores, con contratos y archivos separados y un integrador. Al terminar, entregar a Codex para revisar T07 y emitir integración/congelación y evaluación final en el orden apropiado.
