---
name: data-quality
description: Audita importaciones de ventas e inventario de la MYPE antes de construir series de demanda.
---

Lee docs/CONTRATOS.md. Conserva los originales y hash de cada archivo. Identifica hojas y filas de encabezados/totales antes de importar. Revisa duplicados por clave de transaccion y linea, no solo por valores iguales. Concilia cantidades e importes por mes con origen y registra rechazos. Marzo a agosto de 2026 es el periodo confirmado por el usuario; verifica fechas efectivas y cobertura por SKU.
Distingue ceros, cierre, datos ausentes y stock agotado. Marca atipicos IQR para inspeccion; no elimines promociones automaticamente. Separa devoluciones y anulaciones. Registra unidades, categoria y almacen. Para medir inventario exige stock inicial, movimientos y reglas; si faltan, limita conclusiones.
Entrega perfil de calidad, transformaciones y pruebas A01-A02. Los archivos reales permanecen en data/private/ excluidos del repositorio. No envias datos a servicios externos para limpiarlos.

Hallazgo vigente: leer docs/AUDITORIA_DATOS.md. Los seis meses ya tienen detalle por producto. Conservar agosto reservado y resolver negativos tipo 7, dias sin registros y consistencia de categorias. Los datos operativos de inventario siguen pendientes.

Actualización autorizada: aplicar docs/DECISIONES_DATOS.md. Créditos tipo 7 confirmados; excluir los tres días sin comprimir calendario; catálogo por corte; inventario sintético reference_v1 permitido para escenarios. No solicitar otra vez estas decisiones ni presentar simulación como inventario o política reales.
