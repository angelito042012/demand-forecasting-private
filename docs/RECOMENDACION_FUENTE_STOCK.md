# Recomendación técnica: fuente de stock para nuevos cortes

**Estado: PROPUESTA DEL EQUIPO, PENDIENTE DE DECISIÓN DE LA EMPRESA.** La empresa debe elegir cómo proporcionará los datos de stock para futuras actualizaciones del plan. Este documento presenta las alternativas evaluadas y la recomendación del equipo.

**Fecha:** 2026-11-10
**Decisión requerida de:** Responsable de la empresa (Rogelio)

---

## 1. Problema

El plan de compra necesita dos entradas para cada producto: **ventas históricas** (para el pronóstico) y **stock actual** (para calcular cuánto comprar). Las ventas se obtienen de los libros Excel mensuales que la empresa ya genera. El stock es más complejo:

- El **conteo físico del 18/10/2026** fue un evento único para 50 productos.
- El **stock del sistema** (`INV_STOCK_ARTICULOS`) no coincide con la reconstrucción por kardex en 13 de 50 casos.
- No existe un procedimiento automático para obtener stock real de los ~5,000 productos.

## 2. Alternativas evaluadas

### Alternativa A: Paquete del kardex (recomendada)

**Descripción:** usar los movimientos del kardex de SQL Server para reconstruir el stock a partir de un punto de referencia conocido (el conteo del 18/10 o un nuevo conteo).

**Procedimiento:**
1. La empresa exporta los libros de ventas del nuevo período (ya lo hace mensualmente).
2. El equipo ejecuta `scripts/sql21_prepare` (solo lectura) contra SQL Server para obtener los movimientos del kardex desde el último corte.
3. La existencia se reconstruye: `stock_anterior + entradas − salidas`.
4. Se importa con `scripts/import_operativo` y se regenera el plan.

**Ventajas:**
- No requiere un nuevo conteo físico (usa el conteo del 18/10 como base).
- Es reproducible y auditable (cada movimiento tiene documento y fecha).
- Ya se probó en la conciliación del 21/10 con 37 de 50 productos coincidentes.
- Usa herramientas que ya existen (`sql21_prepare`, `import_operativo`).

**Desventajas:**
- Acumula la incertidumbre de las 13 discrepancias del conteo anterior.
- Depende de que el kardex registre todos los movimientos (si hay ajustes fuera de kardex, diverge).
- Requiere acceso de solo lectura a SQL Server (la empresa debe proporcionarlo).

**Requisitos de la empresa:**
- Acceso de solo lectura a SQL Server (o exportación mensual del kardex)
- Confirmación de que el kardex refleja todos los movimientos reales

### Alternativa B: Conteo físico periódico

**Descripción:** la empresa realiza un conteo físico de los productos relevantes antes de cada actualización del plan.

**Procedimiento:**
1. La empresa cuenta los productos (50 o los que se acuerden).
2. Entrega el conteo en el formato CSV ya definido (`conteo_reportado.csv` + `review.json`).
3. Se importa con `scripts/import_operativo --stock` y se regenera el plan.

**Ventajas:**
- El stock es real, no reconstruido.
- Elimina las discrepancias acumuladas.
- No requiere acceso a SQL Server.

**Desventajas:**
- Requiere trabajo manual de la empresa cada mes (contar productos).
- Solo es práctico para un grupo pequeño (50–100 productos); no escala a ~5,000.
- Si el conteo tiene errores, no hay forma de detectarlos sin el kardex.

**Requisitos de la empresa:**
- Compromiso de realizar el conteo antes de cada corte
- Formato CSV estándar (ya definido y probado)

### Alternativa C: Stock del sistema (`INV_STOCK_ARTICULOS`)

**Descripción:** usar directamente el campo `STOCK_CANTIDAD` del sistema.

**Procedimiento:**
1. Consulta directa a `INV_STOCK_ARTICULOS` en SQL Server.
2. Se toma el valor como stock actual.

**Ventajas:**
- Simple y automático.
- Cubre todos los ~5,000 productos.

**Desventajas:**
- El mecanismo de actualización de `INV_STOCK_ARTICULOS` no se pudo explicar (no coincide con el acumulado del kardex).
- 13 de 50 productos discrepan, incluyendo uno con +9 unidades de diferencia.
- No se sabe si refleja reservas, ajustes o movimientos fuera del kardex.
- Si el valor es incorrecto, la compra recomendada también lo será.

**Requisitos de la empresa:**
- Explicación de cómo se actualiza `STOCK_CANTIDAD`
- Acceso de solo lectura a SQL Server

## 3. Recomendación del equipo

**Alternativa A (paquete del kardex)** para actualizaciones regulares, complementada con un **conteo puntual (Alternativa B)** de los 13 productos discrepantes para corregir la base.

**Justificación:**
- El kardex ya demostró correspondencia completa con los libros de ventas (14,308 + 9,853 registros verificados uno a uno).
- El conteo puntual de 13 productos es factible (no son miles) y resuelve la incertidumbre acumulada.
- No se recomienda la Alternativa C hasta que la empresa explique el mecanismo de `INV_STOCK_ARTICULOS`.

**Para escalar a más de 50 productos:**
- La Alternativa A funciona para cualquier cantidad de productos, pero necesita un punto de partida (conteo o saldo inicial aceptado por la empresa).
- La Alternativa B no escala más allá de ~100 productos por el esfuerzo manual.
- A futuro, si la empresa confirma que `INV_STOCK_ARTICULOS` es confiable, la Alternativa C sería la más eficiente.

## 4. Herramientas disponibles

| Herramienta | Para qué | Dónde |
|---|---|---|
| `scripts/sql21_prepare` | Leer kardex y ventas de SQL Server (solo lectura) | `trabajo/scripts/` |
| `scripts/import_operativo preview` | Validar archivos antes de importar | `scripts/import_operativo.py` |
| `scripts/import_operativo importar --stock` | Importar conteo CSV | `scripts/import_operativo.py` |
| `scripts/import_operativo importar --ventas` | Importar ventas Excel | `scripts/import_operativo.py` |
| `scripts/import_operativo activar` | Regenerar pronóstico tras importar | `scripts/import_operativo.py` |

## 5. Decisión pendiente

La empresa debe comunicar:

1. **¿Qué alternativa prefiere?** A (kardex), B (conteo), C (sistema) o una combinación.
2. **¿Puede proporcionar acceso de solo lectura a SQL Server?** (necesario para A y C).
3. **¿Está dispuesta a recontar los 13 productos discrepantes?** (complementa A).
4. **¿Con qué frecuencia se actualizaría?** Mensual (recomendado), quincenal o semanal.

Sin esta decisión, el sistema seguirá usando la existencia reconstruida del conteo del 18/10/2026 + movimientos hasta el 20/10/2026, que es la mejor estimación disponible pero se desactualiza con cada día que pasa.
