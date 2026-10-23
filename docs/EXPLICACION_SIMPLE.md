# Explicación sencilla del plan de noviembre (versión entregada, 23/10/2026)

Para estudiar y explicar al grupo. Todas las cifras son las del plan vigente (versión 2, corte de ventas 20/10/2026) y están verificadas en la versión publicada. Un ejemplo recorre todo: el producto **3110044 LAN KERATIN ACOND X 300 ML LISS CARE**.

## 1. ¿Qué responde la aplicación?
«¿Cuántas unidades de cada producto conviene comprar hoy para llegar a fin de noviembre sin quedarnos sin stock, según lo que se vendía y lo que hay en el almacén?» Solo da una **propuesta**: no compra, no envía pedidos y no promete ahorro.

## 2. De dónde salen los datos (fuentes)
- **Ventas:** 15 libros de Excel de la empresa (ventas de marzo a octubre de 2026 y compras de marzo a setiembre). `octubre.xlsx` llega al **20/10**. Las ventas de octubre se contrastaron registro a registro contra la base SQL de la empresa (restaurada, solo lectura) y **coinciden**.
- **Conteo de existencias:** los 50 productos con conteo físico **informado por la empresa** el **18/10/2026 a las 17:00**, almacén 1. Se toma como informado, no verificado por nadie externo.
- **Movimientos del sistema** (entradas y salidas del kardex) entre el conteo y el cierre del 20/10.
- **Parámetros de reposición** (configurados, no confirmados por el proveedor): decisión de compra el **21/10**, plazos de entrega de **7 y 14 días**, reserva de **7 días**, compra mínima 1, múltiplo 1.

## 3. Cortes y fechas (lo que es real y lo que no)
- **Corte de ventas = 20/10/2026**: es el último día completo. El **21/10** solo tiene ventas hasta las 16:26, así que queda **fuera** del cálculo (se guarda aparte y no se usa).
- **Lo posterior al corte es desconocido, no cero.** No se inventan ventas de octubre.
- **Decisión de compra = 21/10**: el primer día simulado es el 21/10 (el stock inicial es el del cierre del 20/10).
- Aviso permanente en pantalla: «Plan de compra bajo supuestos, no es un pedido ejecutado».

## 4. Promedio de 28 días (la previsión de ventas)
Para cada producto se toma el **promedio de unidades vendidas por día en los últimos 28 días con datos válidos** (del 23/09 al 20/10) y se supone que ese ritmo continúa. Es una **proyección**, no ventas observadas. Ejemplo 3110044: vendió 17 unidades en 28 días → 17 ÷ 28 = **0,607 por día** → en los 30 días de noviembre ≈ **18,214 unidades** (el punto es decimal: 18.214 = 18 unidades y 214 milésimas).
Por qué este método: es simple, se puede explicar con una cuenta y en las evaluaciones fue tan bueno como los modelos más complejos (ver «Modelos y método operativo»).

## 5. Existencias reconstruidas
La existencia al cierre del 20/10 = **conteo del 18/10 + entradas − salidas** registradas hasta el cierre del 20/10. Es una **reconstrucción**, no un conteo físico nuevo. 3110044: conteo 0, sin movimientos → **existencia 0**.
- Los movimientos del 21/10 (hasta las 16:26) **no** cambian el plan: solo sirven para comparar con el stock que dice el sistema.
- En **13 productos** la reconstrucción y el sistema no coinciden (**diferencia con el sistema**): están marcados en cada producto y **pendientes de confirmar con la empresa**; no se corrigió ninguna cantidad.
- También está pendiente confirmar las **compras 11452 y 11455** (fecha de recepción futura registrada): no se suman como pedidos por recibir.
- **Supuesto sobre pedidos:** no hay pedidos adicionales por recibir registrados; se supone que no llegan otros (sin confirmar con la empresa).

## 6. Compra recomendada, reserva y faltantes
Para cada plazo (7 o 14 días) se simula día a día desde el 21/10: cada día primero llegan los pedidos y luego se vende. La **compra recomendada** cubre:
> demanda desde que llega el pedido hasta el 30/11 **+ reserva de 7 días** (colchón) **− stock disponible al llegar**, redondeado a unidades enteras (mínimo y múltiplo = 1).

- **Reserva**: 7 días de ventas previstas por si la demanda sube. Es una decisión de planificación que se puede cambiar, no una condición del proveedor.
- **Faltantes**: ventas previstas que **no se podrían atender** porque el pedido todavía no llegó. «Antes» = antes de empezar noviembre (1/11); «Mes» = dentro de noviembre. No se arrastran ni se reponen.
- «Stock al 1/11» = existencia estimada al empezar el mes.

## 7. Plazo de 7 días frente a 14 días (3110044)
| | 7 días | 14 días |
|---|---|---|
| Llega el | 28/10/2026 | 04/11/2026 |
| Stock al 1/11 | 22,571 | 0 |
| **Comprar** | **25** | **21** |
| Estado | Cubre noviembre | **Llega tarde** |
| Faltantes antes de noviembre / en el mes | 4,25 / 0 | 6,679 / 1,821 |
| Ventas que podrían atenderse | 18,214 | 16,393 |
- 7 días: se necesitan 24,893 unidades (34 días de demanda desde la llegada + 4,25 de reserva) y se compran 25.
- 14 días: se necesitan 20,643 unidades (27 días + 4,25) y se compran 21.
- **Por qué compra menos a 14 días:** porque el pedido llega tarde y **se pierden ventas** (1,821 unidades dentro de noviembre y 6,679 antes). **No es un ahorro ni una opción equivalente**: se compra menos porque se vende menos. La pantalla lo explica con estas cifras en «Entender la compra».
- En el plan completo: 19 de 50 productos con compra recomendada en cada plazo; **10 productos** llegan tarde a 14 días.

## 8. Versiones del plan
- **v1** (18/10): ventas hasta el 30/09 y conteo del 18/10. **v2** (21/10, vigente): ventas hasta el 20/10 y existencia reconstruida al cierre del 20/10. La comparación v1/v2 está en «Compra recomendada → Comparar con otra versión»; las existencias son de fechas distintas, por eso las diferencias no se deben solo a la previsión. Ambas se conservan intactas.

## 9. Evaluación académica (separada)
Es el análisis **histórico** (marzo–julio de 2026, agosto como prueba final) con **inventario simulado con supuestos**; no representa el inventario real de la empresa. Está en «Más → Evaluación académica» y no se mezcla con el plan operativo.
