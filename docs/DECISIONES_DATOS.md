# Decisiones acordadas antes de iniciar Claude

Actualización del 16/10/2026. Estas decisiones sustituyen las preguntas pendientes sobre los cuatro puntos respondidos por el usuario. No modifican los Excel originales.

## Notas de crédito

El usuario confirma que las 560 líneas negativas son notas de crédito. Conservarlas en una entidad o partición separada y mantener trazabilidad al archivo y fila. No deduplicar por ID_PEDIDO, que vale cero en estas líneas.

El objetivo del pronóstico será unidades de venta bruta observada, usando líneas positivas de venta. Mostrar por separado ventas, créditos y saldo monetario neto. Una nota de crédito no prueba devolución física al almacén: no reingresar stock automáticamente ni inventar su vinculación con una venta. La exclusión de créditos del objetivo predictivo es una decisión metodológica explícita, no eliminación de datos.

## Tres días excluidos

Por decisión del usuario, excluir 2026-04-03, 2026-04-12 y 2026-06-07 del entrenamiento supervisado y de las métricas. Mantener un calendario con una máscara de exclusión: no etiquetarlos como ventas cero ni cerrar artificialmente el calendario. Un rezago de siete días sigue significando siete días naturales. Features que necesiten un dato excluido deben indicar ausencia o usar una imputación ajustada exclusivamente dentro del entrenamiento. El tiempo de entrega sigue transcurriendo en días naturales. No afirmar que la tienda estuvo cerrada; el usuario pidió omitirlos.

## Producto con categoría cambiante

Se identificó el SKU 16140041: una línea de julio figura como MAQUILLAJE PARA ROSTRO y dos de agosto como MAQUILLAJE PARA OJOS. No se puede demostrar cuál es la categoría comercial correcta con estos registros.

Conservar categoria_original en cada transacción. Para modelado, usar un catálogo versionado por fecha de corte: la categoría más reciente conocida dentro del entrenamiento; desempate por frecuencia dentro del entrenamiento y después orden alfabético. En cada fold se construye solo con sus datos de entrenamiento. Para el corte final del 31/07/2026, ese SKU queda en MAQUILLAJE PARA ROSTRO tanto en train como al agregar resultados de agosto. Se registra la discrepancia de agosto sin usarla para corregir el pasado. En futuras corridas el catálogo puede actualizarse con datos ya conocidos. SKU nuevo sin categoría entrenada: categoría desconocida, sin reentrenar con el test.

## Inventario sintético autorizado

El usuario autoriza generar información sintética apoyada en las ventas. Se utilizará para desarrollar la aplicación y ejecutar experimentos de escenarios, con la etiqueta visible **Inventario simulado con supuestos; no corresponde al inventario real de la empresa**.

Separar procedencias: ventas observadas, notas de crédito reales y parámetros/movimientos sintéticos. No mezclar registros sintéticos con los originales ni presentarlos como levantamiento de datos de la MYPE. Ningún stock, costo, proveedor o plazo real puede deducirse de manera única a partir de ventas.

Escenario inicial reproducible, fijado sin optimizar sobre agosto:

| Parámetro | Regla propuesta | Naturaleza |
|---|---|---|
| Fecha inicial | 01/08/2026 | Corte del escenario |
| Productos elegibles | SKU con ventas positivas en marzo–julio | Cobertura parcial explícita |
| Demanda diaria de referencia | Cantidad base de julio 4–31 dividida entre 28 días | Derivada de ventas previas; incluye cero observado del SKU |
| Costo unitario | 65% de mediana de precio por unidad base en marzo–julio | Supuesto, no costo real ni margen demostrado |
| Lead time | 7 días naturales | Supuesto uniforme |
| Revisión | Cada 7 días naturales | Política de referencia sintética |
| Seguridad | 7 días de demanda de referencia | Supuesto de cobertura |
| Stock inicial | Techo de demanda diaria × 14 | Supuesto |
| Objetivo de reposición | Techo de demanda diaria × 21 | Referencia fija, sin ML |
| Empaque y mínimo | 1 unidad | Supuesto |
| Holding | 20% anual del costo; tasa diaria 0,20/365 | Supuesto económico |
| Pedidos iniciales en tránsito | 0 | Supuesto |

El generador ejecuta una política de referencia en agosto: recibe pedidos, atiende la demanda proxy (ventas positivas observadas), registra faltantes simulados y revisa pedidos al final de cada séptimo día empezando el 1 de agosto. Las notas de crédito no crean entradas físicas. Genera movimientos consistentes con saldo inicial, recepciones y salidas; el objetivo y costo permanecen fijos durante agosto. Los SKU que solo aparecen en agosto quedan fuera de este escenario, con cobertura reportada; no inventarles historia.

Agosto se usa como trayectoria de ventas observada para la simulación, nunca para elegir parámetros, categorías o modelos. No entrenar con los archivos sintéticos. Al comparar con ML, reiniciar ambas políticas con exactamente el mismo stock, demanda proxy, lead time y restricciones. Los movimientos de la referencia no deben imponerse como compras de la política ML: cada política genera sus pedidos.

Los faltantes calculados son faltantes del escenario simulado, no quiebres históricos observados. Las ventas reales pueden estar censuradas por inventario desconocido. Los resultados solo sustentan comparación entre escenarios bajo supuestos, no impacto real ni causalidad en la MYPE. Reportar sensibilidad predefinida a lead time 3/7/14 días y seguridad 0/7/14 días sin elegir solo el escenario favorable. Mantener el mismo stock inicial entre políticas dentro de cada escenario.

## Consecuencia para el informe y el producto

Se puede avanzar sin esperar información operativa real, bajo un alcance de evaluación por simulación. El informe debe declarar este cambio respecto a reconstruir la política actual. Su aceptación académica final corresponde al asesor; no se presume aprobada. La comparación se titula política de referencia sintética frente a política basada en pronóstico, nunca política real frente a propuesta.

La discrepancia de cifras del DOCX con los Excel sigue existiendo: usar los conteos auditados actuales para el nuevo análisis y marcar los antiguos como no conciliados, sin atribuirlos a un filtro no comprobado. Azure, Atlas y los problemas de instalación siguen siendo tareas técnicas; estas decisiones no los resuelven.

## Preparación académica adicional, 18/10/2026

Rogelio autorizó a Codex preparar las 14 fuentes y completar parámetros para un alcance universitario sin implementación en la empresa. Entrega separada en `PREPARACION_DATOS_ACADEMICA_V1.md`. Se conservan originales, ventas documentadas, créditos financieros y procedencia. Se seleccionan 50 productos usando solo información hasta julio; se construye un balance retrospectivo marzo–septiembre con saldo inicial mínimo condicionado a los movimientos. No es inventario observado ni conteo físico. No se usa en entrenamiento, backtests ni en la evaluación T12 congelada. La solicitud de completar datos no convierte supuestos en evidencia empresarial. No se han generado compras operativas ni se ha modificado el modelo existente.

## Conteo reportado recibido, 18/10/2026

Rogelio entregó el formulario completado para 50 productos y confirmó corte 18/10/2026 17:00 Lima, sin ventas durante el conteo, Almacén Principal = ID 1. Libro declara sin recepciones; snapshot reportado documentalmente completo y normalizado en `artifacts/private/conteo_recibido_20261018_v2/`. Ya se puede mostrar el inventario reportado de esa fecha. No etiquetarlo como inventario simulado; conservar esa distinción para T07/T12 y saldos retrospectivos. No hay verificación física independiente por Codex, ni conciliación del intervalo 01–18/10. Conservar cajas/packs como presentaciones declaradas; no multiplicar por el texto del envase. Fecha actual de consulta no cambia la fecha del stock. Las ventas faltantes de octubre no equivalen a cero y los pedidos por recibir siguen desconocidos. Siguiente encargo preparado ETAPA_18_CLAUDE.md, sin entrenamiento, nube o sustitución del histórico.
