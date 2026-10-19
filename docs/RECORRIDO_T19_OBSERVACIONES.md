# Recorrido lector de «Planificar compras» (ens19, 8445) — observaciones de Rogelio

Registro de lo que resulta confuso, para la mejora de claridad posterior (Vercel Web Interface Guidelines como base, Taste Skill para revisar el diseño, Awesome DESIGN.md como inspiración opcional). **No se cambia la interfaz durante la prueba.** La mejora debe conservar cálculos, fechas, unidades y la distinción dato reportado / proyección / supuesto; Angular; se comprobarán de nuevo las pantallas modificadas. **Aceptación humana: PENDIENTE** (este registro no es aceptación).

## Paso 1–2 (18/10/2026)

| Elemento de la pantalla | Lo que se entendió por la pantalla | Lo que no se entendió | Explicación dada |
|---|---|---|---|
| Aviso azul «Plan de compra bajo supuestos… no es una compra ejecutada ni una mejora comprobada» | Es un aviso de que no es oficial | «no ejecutada» y «mejora comprobada» | Nadie compró nada; no se ha probado que seguir el plan mejore frente a lo actual |
| Primer aviso amarillo | Repite el aviso azul | — | Redundancia: propuesta de unificar |
| Aviso amarillo de corte | Ventas hasta el 30/09; octubre desconocido, no cero | «En este escenario no llegan otros pedidos» | No hay datos de pedidos en camino; se supone que solo llega la compra propuesta |
| «Ventas reales: registradas hasta el 30 de septiembre» | Probablemente son los Excel de marzo a septiembre | Confirmación de la fuente | Sí; el cálculo usa los últimos 28 días (03/09–30/09) |
| «Conteo reportado por la empresa… no se verificó de forma independiente» | Fecha, hora y lugar del conteo | Qué significa «no verificado» | Lo informó la empresa y nadie ajeno lo comprobó |
| «Proyección posterior… ventas observadas… limitadas por falta de stock» | Promedio de 28 días | «Ventas observadas»; «limitadas por falta de stock» | Observadas = registradas de verdad; con stock agotado se vende menos que la demanda |
| «Parámetros (supuestos que se pueden cambiar)» | Nada | Todo: decisión, plazos 7/14, reserva, compra mínima, múltiplo | Fecha del pedido; días de entrega; colchón de 7 días; sin mínimo ni múltiplo |
| «Pedidos por recibir» | Que no llegan otros pedidos (supuesto) | Alcance | Ver arriba |
| «Distancia desde el último día con ventas» | Nada | 18 / 32 / 61 días | Cuántos días hay entre el último dato real y el conteo/inicio/fin del mes |
| «Planificación con información desactualizada» | Nada | Todo | Octubre es un hueco: desconocido, no cero |
| «Plan de compra bajo supuestos; no es un pedido ejecutado…» (2.ª vez) | — | Redundante | Mismo aviso repetido |

### Ideas para la mejora de claridad (provisionales)
- Unificar los avisos repetidos (azul, amarillo y la lista de advertencias) en uno solo con una frase breve.
- Reemplazar «ventas observadas», «censura por stock», «corte», «múltiplo», «reserva» por frases cotidianas con un ejemplo.
- En «Parámetros», explicar cada término en una línea («Plazo de entrega: días que tarda en llegar el pedido»).
- Mostrar la distancia como una línea de tiempo (30/09 → 18/10 → 01/11 → 30/11).
- Etiquetar cada dato con «Dato real / Proyección / Supuesto» (colores o rótulos constantes).

## Paso 3 (18/10/2026) — clasificación (entendido tras la ayuda del asistente, no por la pantalla sola)
Rogelio clasificó correctamente: ventas hasta el 30/09 y conteo del 18/10 = datos reales (el conteo es reportado, no verificado); promedio de 28 días = proyección; reserva de 7 días y «no llegan otros pedidos» = supuestos. Matiz explicado: la reserva es una decisión de planificación modificable.
