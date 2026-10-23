# Preguntas frecuentes para la exposición (23/10/2026, 19:30 Lima)

Respuestas breves y verificables; cada una indica dónde está la evidencia. Regla: no presentar datos antiguos como actuales, funciones pendientes como terminadas ni mejoras empresariales como demostradas.

**1. ¿Qué hace la aplicación?** Propone cuántas unidades comprar de 50 productos para cubrir noviembre, con entrega en 7 o 14 días, explicando cada cifra. No compra ni envía pedidos. (`EXPLICACION_SIMPLE.md`)
**2. ¿Con qué datos está calculado?** Ventas hasta el **20/10/2026** (último día completo), existencias reconstruidas al cierre del **20/10** (conteo informado del 18/10 17:00 + movimientos del sistema). El 21/10 es parcial y no se usa.
**3. ¿Por qué no usa datos de hoy?** Porque no existen datos completos posteriores al 20/10 en las fuentes disponibles. Incorporar nuevos cortes requiere un procedimiento técnico (conciliar con la base de la empresa, sellar datos y publicarlos); la carga autónoma desde la aplicación es **trabajo futuro** (`T22_VIABILIDAD_ACTUALIZACION_OPERATIVA.md`).
**4. ¿Qué es el promedio de 28 días?** Unidades vendidas ÷ días válidos de los últimos 28 días (23/09–20/10). Ejemplo 3110044: 17 ÷ 28 = 0,607 por día → 18,214 en noviembre.
**5. ¿Por qué no usan Random Forest o XGBoost?** Se evaluaron y no superaron de forma estable a `promedio_28`: en T06 a nivel SKU ninguno cumplió la regla; en la evaluación final de agosto el WAPE a 14 días fue 0,781 (promedio_28) frente a 0,791 (RF). (`MODELOS_Y_METODO_OPERATIVO.md`)
**6. ¿Entonces el ML no sirve?** No decimos eso: en categoría RF cumplió la regla en desarrollo y en productos de historia corta fue mejor en agosto. No fue suficiente para cambiar el método congelado antes de mirar agosto.
**7. ¿Ahorra dinero?** **No lo afirmamos.** El inventario de las simulaciones es simulado con supuestos y la compra recomendada no se ejecutó; no se midió impacto en la empresa.
**8. ¿Qué significa «Llega tarde»?** Con ese plazo el pedido llega después de empezar noviembre y se pierden ventas previstas («Faltantes»). Son 10 productos a 14 días (3110044 entre ellos).
**9. ¿Por qué a 14 días se compra menos?** Porque se vende menos (16,393 frente a 18,214 en 3110044): no es un ahorro. La pantalla lo explica.
**10. ¿Qué es la reserva de 7 días?** Un colchón de 7 días de ventas previstas (4,25 unidades en 3110044). Es un parámetro configurado, no una condición del proveedor.
**11. ¿Qué son los faltantes «Antes» y «Mes»?** Ventas previstas que no se podrían atender antes de empezar noviembre (hasta el 31/10) y durante noviembre, porque el pedido aún no llegó.
**12. ¿Qué es «existencia reconstruida»?** Conteo físico informado (18/10) + entradas − salidas registradas hasta el cierre del 20/10. No es un conteo físico nuevo ni está verificado por un tercero.
**13. ¿Qué son las 13 «diferencias con el sistema»?** Productos donde la reconstrucción y el stock que indica el sistema (al último movimiento, 21/10 16:26) no coinciden. Están **pendientes de confirmar con la empresa**; no se ajustó ninguna cantidad.
**14. ¿Y las compras 11452 y 11455?** Tienen fecha de recepción futura registrada; no se suman como pedidos por recibir y están pendientes de confirmar.
**15. ¿Hay pedidos por recibir?** No hay pedidos adicionales registrados; se **supone** que no llegan otros (supuesto sin confirmar con la empresa). No decimos que «no existen».
**16. ¿Qué es la evaluación académica?** Análisis histórico (marzo–julio, agosto como prueba final reservada) con **inventario simulado**; está separado del plan operativo.
**17. ¿Por qué «Cargar datos» solo acepta marzo–julio?** Es una regla del servidor que protege la evaluación académica (agosto reservado); esa carga no actualiza el plan de noviembre.
**18. ¿Qué es la versión 1 y la 2?** v1 (18/10): ventas hasta el 30/09; v2 (21/10, vigente): ventas hasta el 20/10 y existencias al cierre del 20/10. Se conservan ambas; se pueden comparar.
**19. ¿Es seguro?** Acceso con usuario y contraseña, HTTPS, cookie protegida, protección CSRF, roles lector/administrador, límite de intentos por cliente (`TRUSTED_PROXIES` corregido y probado). La credencial de Atlas expuesta en una captura anterior **sigue pendiente de rotación** (acción en curso).
**20. ¿Qué pasa con los datos personales?** La aplicación no usa nombres de clientes, vendedores ni proveedores; solo productos, cantidades y fechas.
**21. ¿Qué costó?** Consumo observado en Azure: US$ 1,544 hasta el 22/10 (dato con retraso); proyección ≈ US$ 3,5 al 23/10; sin cargos de bolsillo (`CIERRE_ENTREGA_20261023.md`).
**22. ¿Seguirá en línea después del 23/10?** No se asume: depende de una decisión posterior sobre el crédito; los datos se conservan en Atlas aunque se apague el servicio.
**23. Si falla la conexión en vivo…** Usar el respaldo visual (`artifacts/private/respaldo_visual/`, 13 capturas del recorrido con 3110044; privado, no publicar).
