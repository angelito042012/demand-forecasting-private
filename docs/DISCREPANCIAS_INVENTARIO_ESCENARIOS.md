# Discrepancias de inventario y compras pendientes — escenarios de resolución

**Estado: PENDIENTE DE CONFIRMAR POR LA EMPRESA.** Las discrepancias y las compras 11452/11455 no se resolvieron porque la empresa no ha respondido. Este documento registra los hechos, propone escenarios de resolución y documenta el impacto en el plan de compra. **Ningún escenario se aplicó.**

**Fecha:** 2026-11-10
**Fuente de datos:** Conciliación del 21/10/2026 (`docs/CONCILIACION_SQL_20261021.md`)
**Productos afectados:** 13 de 50 (discrepancias) + 3 de 50 (compras 11452/11455)

---

## 1. Las 13 discrepancias de inventario

Existencia reconstruida = conteo físico (18/10 17:00) + entradas − salidas del kardex (almacén 001) hasta el cierre del 20/10. Se compara con `INV_STOCK_ARTICULOS.STOCK_CANTIDAD` del sistema.

| # | Código | Conteo 18/10 | Reconstruida 20/10 | Stock sistema | Diferencia (sist. − recons.) | Reservado |
|---|---|---|---|---|---|---|
| 1 | 6180005 | 192 | 188 | 190 | +2 | 2 |
| 2 | 23010008 | 53 | 50 | 51 | +1 | 0 |
| 3 | 23030010 | 139 | 136 | 137 | +1 | 45 |
| 4 | 23220015 | 312 | 308 | 310 | +2 | 14 |
| 5 | 26120367 | 14 | 13 | 14 | +1 | 0 |
| 6 | 26120813 | 72 | 60 | 69 | +9 | 0 |
| 7 | 26120815 | 14 | 10 | 11 | +1 | 0 |
| 8 | 26120825 | 87 | 51 | 52 | +1 | 0 |
| 9 | 28010019 | 2979 | 2974 | 2973 | −1 | 4 |
| 10 | 28040010 | 163 | 162 | 163 | +1 | 2 |
| 11 | 28040013 | 298 | 295 | 296 | +1 | 0 |
| 12 | 28040026 | 307 | 304 | 306 | +2 | 1 |
| 13 | 40120090 | 448 | 412 | 414 | +2 | 0 |

**Suma de diferencias:** +23 unidades (el sistema reporta más que la reconstrucción en 12 de 13 casos; solo 28010019 tiene −1).

### Lo que se investigó (sin resultado concluyente)

1. No es por documentos: todas las ventas posteriores de los 13 productos son vigentes y su kardex coincide con su detalle.
2. No es por reserva: la diferencia no sigue a `STOCK_CANTRESERVADA`.
3. Solo un caso (28010019, −1) se explica por la hora del conteo (venta a las 16:59).
4. El stock del sistema no es el acumulado del kardex (solo 15 de 50 coinciden); se actualiza por un mecanismo propio no documentado.
5. Mayor desviación: 26120813 (+9) — el sistema bajó 3 unidades desde el conteo pero el kardex registra 12 vendidas.

### Escenarios de resolución propuestos

#### Escenario A: La empresa recuenta los 13 productos (recomendado)

- **Acción:** reconteo físico de los 13 productos discrepantes.
- **Resultado:** se obtiene el stock real y se actualiza la existencia en el sistema.
- **Impacto en el plan:** la compra recomendada se recalcula con las existencias corregidas. En 12 de 13 casos la diferencia es de 1–2 unidades, por lo que el impacto en la compra sería mínimo. Solo 26120813 (+9) podría cambiar la compra significativamente.
- **Estado:** no solicitado.

#### Escenario B: Se acepta la existencia reconstruida como mejor estimación

- **Acción:** el plan usa la existencia reconstruida (conteo + kardex), que es la que está publicada actualmente.
- **Resultado:** las 13 discrepancias quedan documentadas pero no corregidas. Es lo que el sistema hace ahora.
- **Riesgo:** si el sistema tiene razón, se estaría subestimando el stock en 12 de 13 casos (se compraría ligeramente de más). Si la reconstrucción tiene razón, el plan es correcto.
- **Estado:** es el comportamiento actual por defecto.

#### Escenario C: Se acepta el stock del sistema como verdad

- **Acción:** usar `STOCK_CANTIDAD` del sistema en lugar de la reconstrucción.
- **Resultado:** se confía en el mecanismo del sistema que no se pudo explicar.
- **Riesgo:** en 26120813 el sistema dice 69 pero la reconstrucción dice 60 (diferencia de 9); si el conteo + kardex es correcto, se subestimaría la necesidad de compra.
- **Estado:** no recomendado sin explicación del mecanismo del sistema.

**Decisión actual del equipo:** Escenario B (la existencia reconstruida), con las discrepancias marcadas como pendientes en la interfaz.

---

## 2. Compras 11452 y 11455

Ambas compras están vigentes, son del almacén 001 y ya generaron entrada al kardex el **13/10/2026**, antes del conteo del 18/10.

| Compra | Fecha compra | Entrada kardex | Recepción registrada | Productos (de los 50) |
|---|---|---|---|---|
| 11452 | 13/10 12:45 | 13/10 12:45:26 | 22/10 12:45 | 6160006 (60 u.), 23050035 (56 u.) |
| 11455 | 13/10 00:00 | 13/10 00:00 | 23/10 15:22 | 12040036 (52 u.) + 24 productos fuera de los 50 |

**Anomalía:** la mercadería entró al kardex el 13/10, pero la fecha de recepción registrada es del 22/10 y 23/10 (después del conteo del 18/10 y después de la fecha de decisión del plan).

### Preguntas pendientes para la empresa

1. ¿Qué significa la «fecha de recepción» futura: llegada esperada, fecha de pago o fecha de registro contable?
2. ¿Esa mercadería ya estaba físicamente en el almacén el 18/10 al momento del conteo?
3. ¿Por qué el sistema registró la entrada al stock el 13/10?

### Escenarios de resolución propuestos

#### Escenario A: La mercadería ya estaba al 18/10 (probable)

- **Interpretación:** la entrada al kardex del 13/10 refleja la recepción física real; la «fecha de recepción» registrada es un campo administrativo (pago o registro contable).
- **Impacto:** el conteo del 18/10 ya incluye estas unidades → no son pedidos por recibir → el plan actual es correcto en no contarlas como pendientes.
- **Acción:** documentar y no cambiar nada.

#### Escenario B: La mercadería NO estaba al 18/10

- **Interpretación:** el sistema registró la entrada antes de recibirla (error o anticipación); la fecha de recepción futura es la llegada real.
- **Impacto:** el conteo del 18/10 no las incluye → el stock estaría sobreestimado en las cantidades de estas compras (60+56+52 = 168 unidades en 3 productos) → la compra recomendada podría ser insuficiente para esos productos.
- **Acción:** restar las cantidades del conteo y recalcular. Afecta directamente a 6160006, 23050035 y 12040036.

#### Escenario C: Se ignoran por no poder confirmar

- **Interpretación:** sin respuesta de la empresa, se asume que el plan actual es la mejor estimación disponible.
- **Impacto:** se documentan como pendientes (lo que hace el sistema actualmente: «2 pendientes de confirmar con la empresa»).
- **Riesgo:** si aplica el Escenario B, tres productos podrían tener compra insuficiente.

**Decisión actual del equipo:** Escenario C (pendientes documentados), con aviso visible en la interfaz.

---

## 3. Impacto combinado en el plan de compra

| Concepto | Productos afectados | Rango de impacto | Acción tomada |
|---|---|---|---|
| 13 discrepancias | 13 de 50 | 1–9 unidades por producto (total +23) | Existencia reconstruida usada; discrepancias marcadas |
| Compras 11452/11455 | 3 de 50 | 52–60 unidades por producto | No sumadas como pedidos por recibir; pendientes marcadas |
| **Total incertidumbre** | 15 de 50 (1 producto aparece en ambos) | Menor en 12 de 13 discrepancias; significativa en 26120813 y en los 3 de compras si aplica Escenario B | Documentado, sin corrección |

**Conclusión del equipo:** el impacto de las discrepancias es menor para 12 de 13 productos (1–2 unidades). Los dos casos que podrían cambiar significativamente la compra son 26120813 (+9 de discrepancia) y los 3 productos de las compras 11452/11455 si la mercadería no estaba al 18/10. Sin respuesta de la empresa, el plan publicado es la mejor estimación disponible y las incertidumbres están documentadas y visibles en la interfaz.
