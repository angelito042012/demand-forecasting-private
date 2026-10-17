# T05 Modelos de referencia y validación temporal

Lee docs/ESTADO.md, docs/TRASPASO.md, docs/REVISION_CODEX_03.md y las decisiones/contratos pertinentes. Codex acepta R04/v2/T04 para las seis fuentes canónicas. Retoma desde el código actual; no repetir la migración ni reconstruir etapas aceptadas sin una razón comprobada.

## 1 Cerrar detalles de reutilización de datos

Incluye unidad_base en la firma. Alinea catálogo con start y máscara de la selección de ventas, o define explícitamente un catálogo histórico separado si fuera necesario; para este encargo usar la misma ventana que el conjunto de entrenamiento. Prueba que una categoría solo presente en un día excluido o anterior a start no altera el catálogo usado por esa ventana. Valida precisión de importes antes de convertir a céntimos: si no son representables exactamente con dos decimales, producir error explicativo; no truncar. Añade SIN_REGISTROS_DIA al diccionario y preserva su identidad al agregar categorías.

Documenta una remediación no destructiva para una fuente de reemplazo fallida: identificar el problema y reconstruir desde fuentes canónicas en una base nueva si no hay mecanismo fiable de resolverlo. No borrar cargas fallidas o conflictos para hacer pasar controles. No desarrollar ahora una interfaz de resolución de conflictos.

## 2 Congelar el protocolo antes de observar resultados

Crea docs/T05_PROTOCOLO.md y una configuración versionada antes de ejecutar la evaluación. Horizonte de siete días naturales; pronóstico emitido una vez en el origen, sin actualización con ventas reales durante el bloque de siete días.

Usa estos cinco folds no solapados de validación:

| Corte de entrenamiento | Validación |
|---|---|
| 31/05/2026 | 01–07/06/2026 |
| 14/06/2026 | 15–21/06/2026 |
| 28/06/2026 | 29/06–05/07/2026 |
| 12/07/2026 | 13–19/07/2026 |
| 24/07/2026 | 25–31/07/2026 |

Entrenamiento expansivo desde 01/03 hasta cada corte. Aplicar los días excluidos: el 07/06 no entra en métricas, aunque el primer bloque conserva siete fechas naturales. Declarar cualquier cambio necesario del protocolo antes de mirar sus resultados y explicar el motivo.

## 3 Implementar baselines pequeños y deterministas

Comparar cero, último día disponible válido, naive semanal y promedio de los últimos 28 días naturales con observaciones utilizables (incluye ceros válidos y excluye ausentes/enmascarados). El último día disponible debe registrar su antigüedad; no confundirlo con promedio solo de días de venta.

Para naive semanal, cada predicción de t+h usa el dato de t+h−7, que sigue dentro de entrenamiento para h=1..7. Si esa fecha es ausente/enmascarada, usar el promedio de la ventana anterior de 28 días como fallback predefinido y contabilizarlo. Si no hay observación utilizable, marcar no disponible, sin sustituir silenciosamente por cero. Nunca realimentar rezagos con ventas reales del bloque futuro.

No introducir todavía Random Forest, boosting, búsqueda de hiperparámetros ni una batería grande de nuevos algoritmos. El baseline cero es una referencia de control: ganar una métrica por abundancia de ceros no demuestra buena reposición.

## 4 Cohortes y ventanas sin fuga

En cada fold obtener ventas, fuentes, calendario y catálogo usando exclusivamente la ruta aprobada y su corte. Regenerar las series del fold; no tomar el catálogo, clasificación de intermitencia, población o historia disponible de T04 al 31/07 para decidir lo que se sabía en mayo/junio.

Para la comparación primaria por SKU/almacén: productos conocidos al origen con al menos 56 días naturales de historia y al menos 21 observaciones utilizables en los últimos 28 días. Criterio fijado por entrenamiento, igual para los cuatro métodos. Mantener filas de validación de todos esos productos aunque no vendan en esa semana; no evaluarlos solo en los días/productos con venta.

Reportar aparte cobertura y resultados para historia corta y SKU nuevos durante validación; no inventarles historia ni ocultar las unidades/filas excluidas. Identificar explícitamente qué se pronostica para cada grupo o por qué no se dispone de predicción.

Evaluar también series por categoría, con categorías definidas al corte. Se pueden implementar baselines a nivel categoría directamente, pero distinguirlos de sumar pronósticos por SKU y no exigir igualdad si son métodos diferentes. Para cada comparación usar el mismo universo de targets y documentar cobertura; categoría nueva/desconocida se informa aparte sin usarla para corregir el pasado. No interpretar suma de unidades heterogéneas como volumen físico homogéneo.

## 5 Métricas y resultados

MAE, RMSE, WAPE cuando la suma real sea positiva, sesgo acumulado (predicho menos observado) y proporción de sub/sobrepronóstico. MAPE solo con reales positivos y cobertura explícita; reportar cantidad de ceros excluidos de ese indicador. R² solo con tamaño y varianza suficientes, sin forzar valores en series constantes.

Presentar errores diarios y error de cantidad acumulada en siete días; los bloques que contienen días excluidos deben informar cuántos días fueron evaluables. Métricas por fold, método, nivel (SKU/categoría) y cohortes de entrenamiento, más agregado ponderado correctamente por conteos/unidades. No promediar porcentajes sin definir sus pesos ni mezclar métodos con distinta cobertura para declarar ganador. Mantener predicciones no negativas; no redondear a compras en esta etapa.

Describir qué baseline sirve como referencia para T06 y sus límites. No afirmar que el resultado del baseline confirma mejora del inventario. Conservar los resultados desfavorables y el control cero.

## 6 Evidencia y pruebas

Predicciones y datos comerciales en artifacts/private/t05/, excluidos de Git. Versionar protocolo, configuración, código, métricas agregadas no sensibles y manifiesto con hashes de datos/código/configuración, fuentes, cortes y versiones. Guardar logs extensos y resultados de pruebas aparte, con rutas en el traspaso. No versionar datos comerciales fila a fila.

Pruebas: datos futuros no alteran pronósticos emitidos; calendario y rezago semanal no se comprimen; categorías/población no vienen del futuro; evaluación incluye ceros de productos elegibles aunque no vendan; fallback contabilizado; constantes/ceros/ausentes y promedios ponderados; repetir la evaluación produce las mismas predicciones y métricas. Ejecutar la suite pertinente y una comprobación de integración final, sin repetir grandes pruebas sin cambios que lo justifiquen.

Agosto sigue reservado: no llamar load_final_test_sales ni calcular métricas de agosto. Todo el desarrollo de esta entrega usa marzo-julio.

## 7 Angular en paralelo si resulta viable

Puede delegarse a otro agente con alcance frontend/ y configuración estrictamente necesaria, coordinando archivos compartidos. Ahora que npm ping respondió, intentar scripts/prepare-frontend.ps1 y compilar la aplicación base, conservando package-lock y versiones. No desactivar TLS. Si falla la red, guardar diagnóstico breve y continuar T05. No construir todavía todas las pantallas ni instalar plugins sin una necesidad concreta.

## 8 Entregar y detenerse

Actualizar ESTADO.md, TRASPASO.md y backlog, crear commit local y dejar un resumen breve con tarea, commit, pruebas/resultados, evidencias, bloqueos y próximo paso. Resultados extensos en archivos referenciados. Detenerse para revisión de Codex antes de T06 y antes de abrir agosto.
