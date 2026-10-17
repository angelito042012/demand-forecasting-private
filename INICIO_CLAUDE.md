Este encargo pertenece a una etapa anterior. Para una nueva sesión leer RETOMAR_CLAUDE.md y ESTADO.md; no repetir tareas aceptadas salvo cambios que lo justifiquen.

Lee primero docs/DECISIONES_DATOS.md y después CLAUDE.md, docs/AUDITORIA_DATOS.md, docs/ANALISIS_Y_PLAN.md, docs/CONTRATOS.md, docs/BACKLOG.md y docs/ESTADO.md.

Actúa como integrador del sistema Demand Forecasting, con entrega el 23/10/2026, hora de Lima. Partimos desde cero en esta carpeta. Los seis Excel están en C:\Users\rogel\Documents\Datos y ahora todos contienen detalle por artículo con las mismas 31 columnas. No vuelvas a solicitar reexportación de marzo-julio. Conserva originales; no exportes datos personales innecesarios.

Primera entrega: completa T01/T03 y prepara T04. Comprueba entorno con scripts/doctor.ps1, resuelve la instalación Angular y la base local, crea API con healthcheck e implementa importador trazable e idempotente. Devuelve conteos por mes, reporte de rechazos y pruebas de carga repetida. No deduplicar por ID_PEDIDO: las 560 líneas negativas tienen pedido cero. Conserva tipo documental, unidades y equivalencias. Excluir los tres días acordados del entrenamiento y las métricas, manteniendo fechas naturales. Las líneas tipo 7 son notas de crédito confirmadas: conservarlas aparte, sin reingreso físico automático. Aplicar catálogo de categoría por corte temporal.

Marzo-julio son desarrollo y validación temporal; agosto es test final reservado. La auditoría estructural de agosto ya realizada no autoriza usar sus resultados para seleccionar modelos. Se autorizó usar inventario sintético y ya existe data/synthetic/reference_v1: parámetros, stock, pedidos y movimientos de referencia, con manifiesto. Úsalo para desarrollar y comparar escenarios, nunca como inventario real o política real. Las decisiones sobre créditos, días excluidos, categorías y simulación están cerradas en DECISIONES_DATOS.md; no vuelvas a preguntarlas.

Cuando los contratos sean estables, delega trabajo independiente a los agentes locales, máximo tres simultáneos, con límites de archivos y pruebas concretas. El integrador controla contratos y dependencias. No hay cuentas Azure/Atlas; comienza localmente.

Actualiza docs/ESTADO.md con cambios, pruebas realmente ejecutadas, evidencia, bloqueos y próxima tarea para revisión de Codex. No declares la aplicación completa por tener un prototipo ni inventes métricas o aceptación del usuario.

Detén esta primera entrega después de T01/T03 y la preparación de T04, entrega las pruebas y actualiza ESTADO.md para revisión de Codex antes de entrenar modelos. No modifiques los Excel fuente ni instales conectores que no sean necesarios.
