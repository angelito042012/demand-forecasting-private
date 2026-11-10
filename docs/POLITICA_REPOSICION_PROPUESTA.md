# Política de reposición propuesta — supuestos del equipo

**Estado: PROPUESTA NO VALIDADA.** Este documento describe la política de reposición que el equipo propone para la MYPE, basada en los datos disponibles y en prácticas comunes de empresas similares. **No ha sido validada ni confirmada por la empresa.** Si la empresa proporciona su política real, este documento debe reemplazarse.

**Fecha:** 2026-11-10
**Elaboró:** Equipo de proyecto (propuesta académica)
**Fuente de datos:** 122 compras de los 50 productos entre marzo y octubre de 2026 (SQL Server de la empresa, consulta de solo lectura del 21/10/2026)

---

## 1. Contexto observado

De los datos del sistema de la empresa se observan los siguientes patrones (hechos, no supuestos):

| Concepto | Valor observado | Fuente |
|---|---|---|
| Plazo promedio compra→recepción | 2,4 días (122 compras de los 50 productos) | `docs/CONCILIACION_SQL_20261021.md` §5 |
| Frecuencia de compras | Variable; no se identificó un calendario fijo (hay compras en distintos días del mes) | Kardex de compras, marzo–octubre |
| Almacén principal | Almacén 001 (único almacén con movimientos) | Kardex y conteo físico |
| Unidad de compra | Unidad base del producto (cajas y fracciones según presentación) | Detalle de compras |
| Número de proveedores | No determinado (el sistema no expone proveedor por compra en las tablas consultadas) | Limitación de acceso |
| Punto de reorden | No identificado en el sistema (no existe campo de stock mínimo ni alertas configuradas) | Revisión de tablas |

**Lo que no se sabe (pendiente de la empresa):**
- Cómo decide el responsable de compras cuánto pedir y cuándo
- Si existe un día fijo de pedido (semanal, quincenal, mensual)
- Si hay acuerdos de plazo o cantidad mínima con proveedores
- Si se usa un criterio de stock mínimo visual o por experiencia
- Si las compras 11452/11455 (con fecha de recepción futura registrada) representan un patrón habitual

## 2. Política propuesta por el equipo

Basada en lo observado y en prácticas comunes de MYPEs de productos de higiene/cuidado personal:

### 2.1 Método de pronóstico

| Parámetro | Valor propuesto | Justificación |
|---|---|---|
| Método | Promedio móvil de 28 días (`promedio_28`) | Elegido por la evaluación T13-eval: WAPE 11,7% a nivel categoría y 78,2% a nivel SKU (acumulado 14 días). No superó al modelo RF por categoría pero es más simple, interpretable y estable |
| Ventana | 28 días anteriores al corte | Captura estacionalidad semanal (4 semanas completas) sin arrastrar tendencias largas |
| Horizonte | 30 días (un mes calendario) | Cubre un ciclo completo de reposición mensual |

### 2.2 Parámetros de reposición

| Parámetro | Valor propuesto | Justificación |
|---|---|---|
| Frecuencia de revisión | Mensual (una compra por mes) | Decisión de Rogelio (18/10/2026): compra mensual, no calendario semanal. Compatible con el volumen de la MYPE |
| Plazos de entrega evaluados | 7 y 14 días | Escenarios conservador y holgado. El plazo observado promedio es 2,4 días, pero no está confirmado si eso refleja entregas locales o hay proveedores con plazos mayores |
| Reserva de seguridad | 7 días de venta prevista | Colchón contra variabilidad de demanda. Es configurable; se eligió como compromiso entre servicio y exceso de stock |
| Compra mínima | 1 unidad | Sin información de mínimos de proveedor; el sistema no registra restricciones |
| Múltiplo de compra | 1 unidad | Sin información de empaques o lotes mínimos; el sistema no registra restricciones |
| Pedidos por recibir | Ninguno (supuesto) | Sin confirmación de la empresa sobre pedidos en tránsito; las compras 11452/11455 no se suman porque su estado es ambiguo |

### 2.3 Reglas de decisión

1. **Calcular la demanda prevista del mes:** `promedio_28 × días_del_mes`
2. **Estimar el stock al inicio del mes:** existencia reconstruida al corte − consumo proyectado entre el corte y el inicio del mes
3. **Calcular la necesidad:** demanda del mes + reserva − stock al inicio − pedidos por recibir
4. **Compra recomendada:** `max(0, necesidad)`, redondeada al múltiplo y mínimo configurados
5. **Si la compra no llega a tiempo para el inicio del mes:** calcular los faltantes del período descubierto y reportarlos; la compra cubre desde la llegada hasta fin de mes + reserva

### 2.4 Indicadores de control (propuestos, no implementados)

| Indicador | Definición | Meta propuesta |
|---|---|---|
| WAPE de previsión | Error absoluto ponderado del pronóstico vs. ventas reales | < 15% a nivel categoría (acum. 14 días) |
| Nivel de servicio | % de días sin faltante por producto | > 90% (requiere datos reales de faltantes, que no se tienen) |
| Rotación | Ventas / stock promedio | Requiere stock real continuo (no disponible) |
| Cobertura del stock | Días de venta cubiertos por el stock actual | Requiere stock real continuo (no disponible) |

## 3. Limitaciones de esta propuesta

1. **No validada por la empresa:** los parámetros son supuestos del equipo basados en datos observables; la empresa puede tener reglas distintas.
2. **Plazo de entrega no confirmado:** los 2,4 días observados pueden no representar todos los proveedores ni todos los productos.
3. **Sin mínimos ni múltiplos reales:** la empresa puede tener compromisos con proveedores (cajas cerradas, pedidos mínimos) que no figuran en el sistema.
4. **Sin costos de ordenar ni de mantener:** no se calculó un EOQ (cantidad económica de pedido) porque no se conocen los costos relevantes.
5. **Demanda posiblemente censurada:** la venta registrada puede estar limitada por falta de stock; los faltantes reales se desconocen.
6. **Sin pedidos por recibir:** se supone que no llegan otros pedidos; si la empresa tiene pedidos en tránsito, la compra recomendada cambiaría.
7. **50 productos del grupo de estudio:** la política solo cubre los 50 productos con conteo físico; extenderla a los ~5,000 SKUs requiere conteo o saldo confiable de todos.

## 4. Qué se necesita de la empresa para convertir esto en política real

| Información | Para qué sirve | Estado |
|---|---|---|
| Entrevista con el responsable de compras | Conocer la política actual (frecuencia, criterios, proveedores, plazos pactados) | No obtenida |
| Plazos de entrega por proveedor | Ajustar los escenarios de 7/14 días a plazos reales | No obtenido |
| Mínimos y múltiplos de pedido | Redondear la compra a unidades viables | No obtenido |
| Costos de pedido y almacenamiento | Calcular EOQ si se busca optimizar costos | No obtenido |
| Confirmación de pedidos en tránsito | Descontar del cálculo lo que ya viene en camino | No obtenido |
| Validación de los parámetros propuestos | Aceptar, ajustar o rechazar los valores de la sección 2 | No obtenida |
