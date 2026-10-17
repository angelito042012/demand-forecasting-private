---
name: release-evidence
description: Comprueba la entrega del sistema mediante evidencia de integracion, calidad y reproducibilidad.
---

Lee A01-A14 en docs/CONTRATOS.md y el backlog. Separa pruebas del entorno, pruebas del software y resultados cientificos. Ejecuta solo verificaciones disponibles y registra con claridad las no ejecutadas.
Revisa autenticacion y roles desde la API, cargas malformadas, resultados antiguos, reintentos, ausencia de secretos versionados y consistencia de contratos. Verifica flujo de navegador con datos identificados, batch idempotente, despliegue HTTPS y restauracion real antes de declarar esos hitos completos.
Relaciona requisito, prueba, resultado y evidencia con version del codigo y fecha. Mantiene defectos criticos como bloqueantes de entrega; un modelo con baja precision se reporta, no se maquilla. Actualiza docs/ESTADO.md si tu alcance permite editar; si eres revisor de lectura, devuelve los cambios propuestos al integrador.

Hallazgo vigente: leer docs/AUDITORIA_DATOS.md. Los seis meses ya tienen detalle por producto. Conservar agosto reservado y resolver negativos tipo 7, dias sin registros y consistencia de categorias. Los datos operativos de inventario siguen pendientes.

Actualización autorizada: aplicar docs/DECISIONES_DATOS.md. Créditos tipo 7 confirmados; excluir los tres días sin comprimir calendario; catálogo por corte; inventario sintético reference_v1 permitido para escenarios. No solicitar otra vez estas decisiones ni presentar simulación como inventario o política reales.
