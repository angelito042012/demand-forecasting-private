---
name: inventory-backtest
description: Simula reposicion y compara politicas de inventario bajo condiciones equivalentes.
---

Lee docs/CONTRATOS.md y la definicion de indicadores en docs/ANALISIS_Y_PLAN.md. Exige politica actual respaldada o etiqueta la sustituta como referencia. No equipares ventas observadas a demanda completa si hubo quiebres.
Fija orden de eventos por dia: recepciones, demanda, actualizacion de stock y revision/pedido, con una convencion explicita para lead time cero. Conserva balance de unidades. Ambas politicas comparten demanda, inventario inicial, plazos, costos y restricciones. No usan futuro real.
Calcula posicion con pedidos en transito y compromisos. El objetivo cubre lead time y periodo de revision, mas seguridad justificada; aplica empaques y minimos. Forecast por categoria requiere desagregacion explicita para recomendar SKU.
Prueba manualmente dias sin demanda, faltante, exceso, recepcion, pedido pendiente, devolucion y reintento. Registra fill rate, quiebres, exceso, holding y rotacion con unidades y denominadores coherentes. Entrega escenarios de sensibilidad si faltan parametros; no presentarlos como efecto real medido.

Hallazgo vigente: leer docs/AUDITORIA_DATOS.md. Los seis meses ya tienen detalle por producto. Conservar agosto reservado y resolver negativos tipo 7, dias sin registros y consistencia de categorias. Los datos operativos de inventario siguen pendientes.

Actualización autorizada: aplicar docs/DECISIONES_DATOS.md. Créditos tipo 7 confirmados; excluir los tres días sin comprimir calendario; catálogo por corte; inventario sintético reference_v1 permitido para escenarios. No solicitar otra vez estas decisiones ni presentar simulación como inventario o política reales.
