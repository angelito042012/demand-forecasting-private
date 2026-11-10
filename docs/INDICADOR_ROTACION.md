# Indicador de rotación de inventario — definición y cálculo

**Estado: DEFINICIÓN METODOLÓGICA CON CÁLCULO PARCIAL.** Se define la fórmula, se calcula con los datos disponibles (50 productos del grupo de estudio) y se documentan las limitaciones. **El indicador no se ha validado con la empresa ni con el asesor.**

**Fecha:** 2026-11-10
**Depende de:** Tareas 3 y 4 (discrepancias resueltas y fuente de stock definida — ambas documentadas con supuestos)

---

## 1. Definición

**Rotación de inventario** = Ventas del período / Stock promedio del período

Mide cuántas veces se "renueva" el inventario en un período dado. Un valor alto indica que el producto se vende rápido relativo a lo que se mantiene en stock; un valor bajo sugiere sobrestock o baja demanda.

### 1.1 Fórmula operativa

```
Rotación(producto, período) = Σ ventas_unidades(producto, período) / stock_promedio(producto, período)
```

Donde:
- **Ventas en unidades:** suma de unidades vendidas en el período (fuente: libros de ventas Excel, verificados contra kardex).
- **Stock promedio:** promedio de la existencia al inicio y al final del período. Idealmente sería el promedio diario, pero solo se dispone de un punto de stock (conteo del 18/10).

### 1.2 Variantes según datos disponibles

| Variante | Stock promedio | Aplicable cuando | Limitación |
|---|---|---|---|
| **A. Punto único** | stock_conteo (18/10) | Solo hay un dato de stock | No captura la variación intra-período |
| **B. Inicio–fin** | (stock_inicio + stock_fin) / 2 | Hay dos conteos o dos reconstrucciones | Mejor aproximación, pero ignora picos |
| **C. Promedio diario** | Σ stock_diario / días | Hay reconstrucción diaria del kardex | La más precisa; requiere kardex completo |

**Variante usada actualmente:** A (punto único al 20/10, reconstruido con conteo + kardex).

## 2. Cálculo con datos disponibles

### 2.1 Datos de entrada

| Dato | Fuente | Alcance |
|---|---|---|
| Ventas septiembre | Libro Excel importado, verificado contra SQL Server | 50 productos del grupo de estudio |
| Ventas octubre (parcial) | Libro Excel hasta ~20/10 | 50 productos |
| Stock al 20/10 | Conteo 18/10 + movimientos kardex hasta 20/10 | 50 productos |
| Días del período | Septiembre: 30 días; Octubre parcial: 20 días | — |

### 2.2 Fórmula aplicada (septiembre, variante A)

```
Rotación_sep(producto) = ventas_sep(producto) / stock_20oct(producto)
```

**Nota:** el denominador usa el stock del 20/10 como aproximación del stock promedio de septiembre. Esto introduce un sesgo: si el producto recibió una compra grande en octubre, el stock del 20/10 sobreestima el stock promedio de septiembre (la rotación calculada sería más baja que la real). Y viceversa.

### 2.3 Interpretación

| Rotación mensual | Interpretación | Días de cobertura equivalente |
|---|---|---|
| > 4.0 | Muy alta rotación — se renueva más de 4 veces al mes | < 7.5 días |
| 2.0 – 4.0 | Alta rotación | 7.5 – 15 días |
| 1.0 – 2.0 | Rotación media | 15 – 30 días |
| 0.5 – 1.0 | Baja rotación — se renueva menos de una vez al mes | 30 – 60 días |
| < 0.5 | Muy baja rotación — sobrestock probable | > 60 días |
| 0 (sin ventas) | Sin movimiento — evaluar si es obsoleto o estacional | — |

**Días de cobertura** = 30 / rotación mensual (cuántos días dura el stock al ritmo de ventas actual).

### 2.4 Relación con la política de reposición

La rotación complementa al WAPE (error del pronóstico) y al fill rate (nivel de servicio):

| Indicador | Qué mide | Fuente |
|---|---|---|
| **WAPE** | Precisión del pronóstico (diferencia entre previsto y real) | T13-eval |
| **Fill rate** | Proporción de demanda atendida | Simulación T07/T12 |
| **Rotación** | Eficiencia del uso del inventario | Este documento |

Un producto con **alto fill rate pero baja rotación** tiene buen servicio pero demasiado stock (capital inmovilizado). Un producto con **alta rotación pero bajo fill rate** tiene poco stock y pierde ventas. El objetivo es maximizar ambos simultáneamente.

## 3. Cálculo para los ~5,000 productos (cuando sea posible)

Para extender el indicador más allá de los 50 productos del grupo de estudio:

1. **Se necesita stock de los ~5,000 productos** — la tarea 4 recomienda la Alternativa A (kardex), pero requiere un punto de partida (conteo o saldo aceptado).
2. **Las ventas ya están disponibles** para todos los productos (libros Excel mensuales).
3. **El cálculo es directo** una vez que se tienen ambos datos.

### 3.1 Clasificación ABC por rotación

Con los ~5,000 productos se puede hacer una clasificación ABC:

| Clase | Criterio | Acción sugerida |
|---|---|---|
| **A** | Top 20% en ventas (generan ~80% del ingreso) | Monitoreo frecuente, pronóstico activo |
| **B** | Siguiente 30% | Pronóstico mensual, revisión trimestral |
| **C** | Restante 50% (generan ~5% del ingreso) | Pedido por mínimos, revisión semestral |

Esta clasificación no se ha hecho porque requiere datos de precio/ingreso que no se tienen (las ventas están en unidades, no en soles).

## 4. Qué se puede reportar hoy

1. **Rotación por producto (50 productos, septiembre):** calculable con ventas de septiembre y stock del 20/10 como aproximación. Limitación: el denominador no es el stock promedio real de septiembre.

2. **Rotación por categoría (37 categorías):** sumando ventas y stock por categoría. Más estable que por SKU individual.

3. **Días de cobertura:** 30 / rotación. Indica cuántos días dura el stock actual al ritmo de ventas del último mes.

4. **Productos sin movimiento en septiembre:** rotación = 0. Sirve para identificar obsoletos o estacionales.

## 5. Limitaciones

1. **Solo un punto de stock** — la rotación es una aproximación, no una medición precisa. El stock promedio real requeriría reconstrucción diaria del kardex.
2. **13 discrepancias** — el stock de 13 productos tiene incertidumbre de 1–9 unidades (ver `docs/DISCREPANCIAS_INVENTARIO_ESCENARIOS.md`).
3. **Solo 50 productos** — no se puede calcular para los ~5,000 sin una fuente de stock general.
4. **Sin datos de precio** — no se puede ponderar por valor económico ni hacer clasificación ABC completa.
5. **Estacionalidad** — un solo mes de ventas no captura patrones estacionales. La rotación de septiembre puede no representar el año.
6. **Demanda censurada** — si un producto se agotó, las ventas subestiman la demanda real y la rotación aparente es menor que la potencial.

## 6. Próximos pasos (requieren datos de la empresa)

1. Obtener stock al inicio de septiembre (o reconstruirlo con kardex desde el conteo del 18/10 hacia atrás) para usar la variante B.
2. Calcular rotación con ventas de octubre y noviembre para ver tendencia.
3. Obtener precios para clasificación ABC por valor.
4. Definir con el asesor los umbrales de decisión (¿a partir de qué rotación se considera sobrestock?).
