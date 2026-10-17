# Revisión de T06

Fecha: 17/10/2026, America/Lima. Entrega: 3b11fbd, con protocolo 286017d, implementación 2c52c73 y enmienda numérica 00e4e64. **T06 aceptado como experimento de desarrollo**, con el límite de reutilización de inferencia indicado abajo. Siguiente encargo: ETAPA_05_CLAUDE.md (T07). Agosto permanece reservado; no hay selección final ni impacto operativo demostrado.

## Evidencia independiente y alcance

Codex revisó protocolo, configuración, features, entrenamiento, inferencia, selección, manifiesto y pruebas. Ejecutó siete pruebas de features/modelos (2,79 s) y cuatro de integración T06 en bases temporales (4,28 s): **11 aprobadas**. Análisis de estilo de pipeline/forecast, tests/forecast y scripts/run_t06.py correcto. No volvió a entrenar los experimentos completos ni a ejecutar la suite integral.

Verificó hashes de código, ambas configuraciones y archivo de predicciones contra T06_MANIFIESTO.json. Recorrió las 125391 predicciones: sin claves repetidas ni fechas objetivo en agosto. Todas las columnas originales de T05 coinciden exactamente al alinear fold/nivel/entidad/fecha, incluidos reales, cohortes, máscaras y baselines. Recalculó n, MAE, RMSE, WAPE y sesgo de **36 grupos agregados no vacíos del universo común**, diarios y por bloque, para los seis métodos; coinciden con T06_METRICAS.json.

La suite completa de 94 aprobadas y el build/15 pruebas Angular son resultados registrados por Claude; Codex leyó la evidencia, sin repetirlos. La interfaz sigue con mocks identificados; no se verificó visualmente ni se declara conectada o autenticada.

## Resultado y decisiones

En SKU, WAPE semanal de promedio_28 = 0,992109; RF = 1,0584 y XGBoost = 1,0174. Ningún ML cumple la regla. La propuesta operativa provisional es promedio_28; el control cero se conserva como control estadístico, no como recomendación de compra. El denominador observado del universo primario semanal es **23026 unidades**: corregir la cifra 22954 escrita en el resumen de ESTADO.md. Las métricas guardadas son correctas.

En categoría, RF obtiene WAPE diario 0,394 frente a 0,4025 del promedio_28: aproximadamente 2,07% de mejora relativa y tres de cinco folds favorables. Cumple la regla por margen mínimo. Sin embargo, su WAPE semanal 0,217 es peor que naive_semanal 0,201 y promedio_28 0,202. No convertir ese resultado diario en evidencia de mejores pedidos por SKU. La futura asignación categoría→SKU es un método nuevo y requiere validación propia.

La enmienda sobre repetición con tolerancia absoluta 1e-9 es aceptable: documenta ruido de reducción paralela del orden de 1e-13 y no cambia hiperparámetros, población, folds ni selección. Estos resultados son de desarrollo conocido, no una prueba independiente.

## Límite que debe corregirse antes de integrar inferencia

forecast_origin calcula el final del contexto desde bundle.inicio y la longitud, en lugar de validar también ctx.start. Un contexto desplazado con igual longitud puede pasar la comprobación de corte, aunque sus features de calendario correspondan a otras fechas. Además, predict_block recibe códigos ya construidos; el vocabulario guardado no garantiza por sí solo que esos códigos usen la misma correspondencia. La orquestación T06 construye los contextos coherentemente; esto no invalida sus métricas verificadas. Sí debe corregirse y probarse antes de conectar datos arbitrarios, simulación o API: fechas reales del contexto, dimensiones/entidades, vocabulario de entrenamiento y versión/horizonte compatibles.

## Siguiente incremento

T07 evaluará horizontes de protección de 10, 14 y 21 días para lead time 3/7/14 más revisión de 7 días. Es una extensión de desarrollo preregistrada, no extrapolación de T06. Comparará una referencia fija sintética, promedio_28 y un candidato acotado RF por categoría distribuido a SKU con pesos históricos. Puede perder: no se fuerza una mejora ni se busca una configuración favorable.

Los parámetros/stock/costos del escenario de junio-julio deben calcularse con información hasta 31/05, nunca reutilizando los valores de reference_v1 calibrados con julio para agosto. No consultar agosto ni los movimientos sintéticos que lo representan. Después de revisar T07 se decidirá la congelación final y se avanzará a integración/API y prueba final controlada.
