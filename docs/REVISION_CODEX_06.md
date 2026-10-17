# Revisión T07 y decisión de integración

17/10/2026, America/Lima. Entrega revisada: 5790103 y antecedentes 9419d2f, 325da2f, e3c38c3 y e546641. **T07 aceptado como experimento de desarrollo y simulador bajo supuestos**. Próximo encargo: ETAPA_06_CLAUDE.md (T08 e integración de lectura T09). Agosto continúa reservado.

## Comprobación independiente acotada

Codex ejecutó tests/sim, test_t07_functions.py y test_inference_coherence.py: **22 aprobadas en 2,44 s**. Ruff correcto en forecast, simulación, pruebas y script T07. Revisión adicional de solo lectura del motor/orquestador: sin fallos que invaliden los escenarios actuales. No se repitió el entrenamiento ni la integración real costosa. El log de Claude registra 117 aprobadas, un aviso y 346,26 s antes de ajustes de reporte; esos resultados se distinguen de la comprobación de Codex.

Se verificaron hashes de configuración, código, los dos archivos de resultados y los **13 modelos** contra el manifiesto. Se recorrieron las **293853 predicciones SKU**: claves fold/entidad/fecha únicas, objetivos entre 01/06 y 31/07, 07/06 no evaluable. Se recalcularon independientemente **160 grupos SKU** por fold/agregado, cohorte, método y vista: n, unidades, MAE, RMSE, WAPE y sesgo coinciden dentro de la precisión del CSV (10 cifras significativas). No se presenta esto como recálculo independiente de las métricas por categoría, cuyo detalle fila a fila no está en ese CSV.

Del NPZ se comprobaron las **27 combinaciones** de política/escenario, sobre 3347 SKU y 61 fechas: saldo diario reconstruido como stock0+cumsum(recibido−atendido), recepciones exactamente L días después de pedidos, pedidos solo en revisiones, demanda=atendida+perdida, ausencia de servicio/faltantes en día enmascarado, inventarios no negativos e inicialización igual entre políticas. Se recalcularon métricas totales de servicio, stock, pedidos, tránsito y costos, coincidentes con JSON. Identidad de valor válida. Resumen privado: artifacts/private/codex_review06_audit.json. No se consultó la base real ni se modificaron Excel/bases durante esta revisión.

## Conclusiones que deben conservarse

RF distribuido pierde en los cuatro folds H14: WAPE 0,929209 frente a 0,872571 de promedio_28, aproximadamente 6,49% peor, sesgo relativo +16,74%. También pierde en H10/H21. No cumple la regla ni justifica desplazar al baseline. Promedio_28 queda elegido como método operativo de la primera versión; RF permanece como comparador experimental identificado. Categoría operativa se agrega desde SKU para conservar coherencia, sin presentar la pequeña ventaja diaria T06 como superioridad en reposición.

En L7/S7, fill rate 74,10% referencia fija, 79,68% promedio_28 y 80,86% RF. RF frente a promedio_28: +1,17 puntos porcentuales de servicio, +7,5% stock medio y +4,0% compras. Es un intercambio bajo supuestos, no ahorro ni mejora real de la MYPE. No cambiar de método por ese servicio mayor cuando se mantiene más inventario. Los bloques predictivos solapados no son observaciones independientes.

El cambio a un hilo de RF está declarado en el protocolo comprometido antes de resultados; no es una enmienda posterior oculta. T07 corrigió contexto/vocabulario/horizonte de inferencia. La identidad de filas de entidad sigue siendo responsabilidad del constructor de contexto: número y duplicados se validan, pero no existe un mapa histórico de IDs contra el cual detectar una permutación de nombres. Mantener construcción ordenada y probada al integrar.

## Ajustes pequeños antes de exponer entradas

engine.check_conservation comprueba balance terminal por SKU y demanda por fecha, pero no directamente toda la trayectoria diaria. La auditoría independiente confirmó esa trayectoria en los 27 escenarios. Incorporar el chequeo diario y una prueba que altere un saldo intermedio conservando el final; no requiere regenerar T07.

simulate presupone entradas válidas: validar L>=1, dimensiones, finitud/no negatividad/integralidad de stock y objetivos, días de revisión y costos/tasa antes de aceptar parámetros externos. Los escenarios actuales usan L3/7/14 y enteros válidos; su resultado no está afectado.

## Siguiente decisión

Integrar API autenticada, persistencia versionada y pantallas de lectura con resultados existentes; usar una corrida histórica de desarrollo al 10/07, sin disfrazarla de resultado vigente. Congelar por escrito método operativo, comparador, reglas y métricas de evaluación final sin ejecutar agosto. La ejecución final se autorizará en otro encargo tras revisar integración y congelación. No repetir T06/T07 ni añadir búsquedas para conseguir una ventaja ML. Publicación, carga web/batch completo, restauración y aceptación humana siguen pendientes.
