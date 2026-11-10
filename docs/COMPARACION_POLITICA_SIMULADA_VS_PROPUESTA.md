# Diseño de comparación justa: política simulada vs política propuesta

**Estado: DISEÑO METODOLÓGICO, NO EJECUTADO.** Este documento describe cómo comparar la política de reposición simulada (T07/T12, inventario sintético) con la política propuesta del equipo (`docs/POLITICA_REPOSICION_PROPUESTA.md`). La comparación no se ha ejecutado porque requiere datos reales que la empresa no ha proporcionado. **Todos los resultados previos de simulación usan inventario simulado con supuestos; no corresponden al inventario real de la empresa.**

**Fecha:** 2026-11-10
**Depende de:** Tarea 2 (política propuesta — hecha con supuestos)

---

## 1. Por qué es necesaria una comparación justa

La simulación de T07 y T12 compara tres políticas de pronóstico (`referencia_fija`, `promedio_28`, `rf_categoria_distribuido`) bajo inventario simulado con 27 combinaciones de parámetros. El resultado clave (T07 §Parte B): `rf_distribuido` tiene mayor fill rate que `promedio_28`, pero también más stock y más compras — **la ventaja de servicio no es concluyente** porque es compatible con simplemente pedir más.

Una comparación justa requiere:
- **Mismo stock inicial** (real, no simulado)
- **Misma demanda** (ventas reales del período evaluado)
- **Mismas restricciones** (plazo, frecuencia, mínimos — de la política real o propuesta)
- **Diferencia solo en el método de pronóstico** o en los parámetros de reposición

## 2. Marco de comparación propuesto

### 2.1 Variables controladas (iguales en ambas políticas)

| Variable | Valor | Fuente |
|---|---|---|
| Stock inicial | Existencia reconstruida al 20/10/2026 (conteo + kardex) | `docs/CONCILIACION_SQL_20261021.md` |
| Demanda | Ventas reales de noviembre 2026 (cuando estén disponibles) | Libros Excel de la empresa |
| Horizonte | 30 días (noviembre completo) | Política propuesta §2.2 |
| Plazos de entrega | 7 y 14 días (escenarios) | Política propuesta §2.2 |
| Reserva | 7 días de venta prevista | Política propuesta §2.2 |
| Mínimo / múltiplo | 1 / 1 | Política propuesta §2.2 |
| Productos | 50 del grupo de estudio | Conteo del 18/10 |

### 2.2 Variable experimental (lo que cambia)

| Dimensión | Política simulada (T07/T12) | Política propuesta |
|---|---|---|
| Stock inicial | **Simulado** (snapshot sintético) | **Real** (conteo + kardex reconstruido) |
| Pronóstico | `promedio_28` (ventana hasta 31/07) | `promedio_28` (ventana hasta 20/10) |
| Revisiones | 5 revisiones en el mes (días 1, 8, 15, 22, 29) con RF reentrenado | 1 revisión al inicio del mes (sin RF) |
| Pedidos por recibir | Ninguno (supuesto) | Ninguno (supuesto, a menos que la empresa confirme) |

### 2.3 Métricas de comparación

| Métrica | Definición | Qué mide |
|---|---|---|
| **Fill rate** | Unidades atendidas / demanda total | Nivel de servicio |
| **Faltantes** | Unidades no atendidas por falta de stock | Ventas perdidas |
| **Compra total** | Unidades pedidas en el período | Inversión en inventario |
| **Stock medio** | Promedio diario de unidades en inventario | Capital inmovilizado |
| **Días-SKU con faltante** | Proporción de (día × producto) con faltante | Frecuencia de desabasto |
| **WAPE del pronóstico** | Error absoluto ponderado de la previsión vs. ventas reales | Calidad del pronóstico |

## 3. Protocolo de ejecución (cuando los datos estén disponibles)

### Paso 1: Obtener ventas reales de noviembre
- La empresa entrega el libro de ventas de noviembre 2026
- Se importa con `scripts/import_operativo importar --ventas noviembre.xlsx --db <base_comparacion>`
- Se verifica contra SQL Server si hay acceso

### Paso 2: Simular la política propuesta con datos reales
- Stock inicial: existencia reconstruida al 20/10
- Pronóstico: `promedio_28` con ventana 23/09–20/10 (ya calculado en el plan v2)
- Compra recomendada: la del plan v2 (7 y 14 días)
- Simular día a día: cada día llegan pedidos, luego se vende, se registra el stock
- Calcular métricas al final del mes

### Paso 3: Simular la política simulada con los MISMOS datos reales
- Stock inicial: **el mismo** (existencia reconstruida, no el simulado de T07)
- Pronóstico: `promedio_28` con ventana hasta 31/07 (el de T12)
- Simular con las mismas 27 combinaciones de T07
- Calcular las mismas métricas

### Paso 4: Comparar
- Fijar una variable (p.ej. compra total) y comparar el servicio
- O fijar el servicio (fill rate ≥ 80%) y comparar la inversión
- Reportar las diferencias con intervalos de confianza si hay suficientes productos

## 4. Resultados previos como referencia (inventario simulado, NO reales)

Del T07 escenario principal L=7, S=7 (3,347 SKU, junio–julio, inventario simulado):

| Política | Fill rate | Perdidas | Stock medio/día | Compras |
|---|---|---|---|---|
| referencia_fija | 0.7410 | 11,054 | 15,283 | 430,952 |
| promedio_28 | 0.7968 | 8,671 | 16,648 | 515,948 |
| rf_distribuido | 0.8086 | 8,170 | 17,891 | 536,575 |

**Estos números NO son la comparación justa.** Son el punto de partida: muestran que promedio_28 tiene fill rate 79,7% con inventario simulado; la comparación justa mediría lo mismo con inventario real y ventas de noviembre.

## 5. Qué se puede hacer hoy (sin ventas de noviembre)

1. **Comparación retrospectiva con septiembre** (ya tenemos esas ventas): simular el mes de septiembre con stock real del conteo del 18/10 retroproyectado y con el pronóstico del plan v2. Limitación: el stock del 18/10 no se puede retroproyectar a agosto/septiembre de forma confiable.

2. **Comparación solo del pronóstico** (sin simular inventario): comparar WAPE del `promedio_28` ventana-hasta-julio (T12) vs. ventana-hasta-octubre (plan v2) usando las ventas de septiembre como test. Esto ya se hizo parcialmente en T13-eval (expanding window backtesting).

3. **Diseño de la simulación lista para ejecutar**: preparar el código que, al recibir las ventas de noviembre, ejecute automáticamente la comparación. Esto es lo que está documentado aquí.

## 6. Limitaciones

1. **No se puede ejecutar hasta tener ventas reales de noviembre** (o al menos de un mes posterior a octubre).
2. **Un solo mes no es suficiente** para declarar superioridad estadística; es un dato, como T12.
3. **El stock inicial tiene 13 discrepancias** que introducen incertidumbre (ver `docs/DISCREPANCIAS_INVENTARIO_ESCENARIOS.md`).
4. **Sin política real de la empresa**, la comparación es entre la política propuesta del equipo y la simulada — no entre lo que la empresa hace y lo que el sistema sugiere.
5. **La demanda real puede estar censurada** por falta de stock: si un producto se agotó, la venta registrada subestima la demanda verdadera.
