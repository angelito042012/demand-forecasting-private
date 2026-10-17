Este encargo pertenece a una etapa anterior. Para una nueva sesión leer RETOMAR_CLAUDE.md y ESTADO.md; no repetir tareas aceptadas salvo cambios que lo justifiquen.

Lee docs/REVISION_CODEX_01.md y aplica sus correcciones R01, R02 y R03. Codex ejecutó las 19 pruebas actuales y verificó los conteos/importes de los seis Excel, pero reprodujo los fallos descritos en la revisión.

Trabaja primero en pruebas de regresión y correcciones del importador/conciliación. Usa bases temporales propias; no borres ni migres todavía demand_forecasting_dev ni modifiques los Excel. Define estrategia de claves/versionado y trazabilidad antes de una futura migración.

Después incorpora la barrera de acceso a entrenamiento por corte temporal, con pruebas que demuestren que agosto o fechas posteriores al corte del fold no modifican los datos de entrenamiento. Mantén las decisiones de docs/DECISIONES_DATOS.md.

No entrenes modelos, no calcules métricas predictivas y no amplíes pantallas. El bloqueo de Angular no debe detener estas correcciones. No desactives TLS para resolver npm.

Al finalizar ejecuta la suite completa incluyendo datos reales en una base temporal, verifica recarga y sumas por mes, actualiza docs/ESTADO.md con evidencia y entrega el resultado para la segunda revisión de Codex. No marques T03 como completo hasta cubrir los casos de la revisión.
