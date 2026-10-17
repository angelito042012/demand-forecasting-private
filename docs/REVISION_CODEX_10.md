# T10R aceptado: cierre R07–R10 en alcance local

17/10/2026, Lima. Entrega revisada **6212f6a**, correcciones a984eff/9ba0aff/c0f3bf0. **T10 y T10R aceptados para la demostración local; R07–R10 cerrados en ese alcance.** No equivale a despliegue, garantía de concurrencia de todos los accesos administrativos o aceptación humana. Próximo encargo: `ETAPA_10_CLAUDE.md` (T12, evaluación final bajo congelación).

## Verificación independiente

Codex ejecutó **59 pruebas, todas aprobadas, 0 omitidas, 43,65 s**: las 32 nuevas de T10R, protocolo concurrente anterior, handlers y scheduler. Incluyen Mongo real, intercalaciones deterministas, exclusión de archivos mensuales, reintentos y proceso `--loop` con worker real y reloj de prueba acelerado; sus procesos terminan al cerrar. JUnit/log: `artifacts/private/codex_review10_tests.xml` y `.log`. Ruff en los archivos de código/pruebas afectados: limpio.

Se leyeron los logs previos a la corrección: 7 fallos R07/R08, 6 R09, 9 R10. No se volvió a restaurar código antiguo ni se repitió toda la suite. Las **408 aprobadas/6 omitidas**, frontend sin cambios y logs de ejecución original son evidencia de Claude; no se presentan como ejecución propia de Codex. No se abrió agosto ni se entrenó ningún modelo en esta revisión.

Auditoría propia **solo lectura** de Mongo: histórica `hist-20260710-4ea348836e35` completed/activa y anterior `hist-20260710-52b01cd999dd` superseded, ambas con **77 343 pronósticos, 3 647 recomendaciones y un backtest**. El staging `gen-20260620-d438bef389c9` ahora está failed/INTENTO_ABANDONADO, conservado sin hijos. La selección congelada (documento, JSON y checksum) es idéntica a 9596d26; hashes normalizados verificados. Datos lógicos + índices: **459 394 400 bytes (459,39 MB)**. Evidencia privada: `artifacts/private/codex_review10_audit.json`.

## Por qué se cierran las incidencias

- R07: antes de limpiar un intento vigente vencido, el mantenimiento lo invalida con CAS staging→failed; una renovación/promoción que ganó primero impide esa invalidación. El dueño invalidado no puede promover y los lectores conservan hijos referenciados. Pruebas cubren ambos órdenes, dos limpiadores y limpieza parcial.
- R08: takeover compara también el lease leído; el heartbeat interpuesto invalida ese CAS y se respeta al dueño renovado.
- R09: la reserva durable por mes bloquea otra SHA antes de escribir. Una carga parcial mantiene la reserva; solo la misma fuente puede recuperarla con generación nueva y upserts idempotentes. Las pruebas cubren la carrera original y la vuelta tardía. Una comprobación por lote **no cancela un bulk ya enviado ni es una transacción multidocumento**; ese lote solo pertenece a la misma SHA retenida, sin mezclar otra fuente.
- R10: ticks error o procesando vencidos se retoman con propietario/lease, el job existente se reconcilia mediante la clave común, y el timer obsoleto no pisa la finalización. La prueba de proceso continuo verifica la cadena, sin esperar el cron real de 06:00.

## Límites operativos conservados

1. Importación administrativa por CLI sin fence: **serial y nunca simultánea a cargas web/worker**. La reserva web no debe presentarse como exclusión global de cualquier escritor. Remediación partial solo privilegiada; no abrir una API para liberarla.
2. El timer recupera la clave a partir de fuentes/config actuales: si estas cambian entre crear el job y guardar el tick, puede encolar una identidad diferente. No bloquea el dataset completo y estable actual; mantener scheduler deshabilitado por defecto y no cambiar fuentes/config durante recuperación. Antes de permitir fuentes dinámicas con timer, persistir payload/clave inmutables de cada ranura y probar esa intercalación.
3. Corridas T10 siguen con activate_run=False. Conservar histórica auditada como predeterminada; dos validadores y estilo ajeno no ameritan nueva refactorización para cerrar T10.
4. HTTP local, inventario simulado, sin conexión Atlas/despliegue/HTTPS/copia-restauración ni aceptación humana. La cuota/capacidad requiere plan de conservación antes de publicar; no borrar evidencia para encajar.

## Siguiente decisión

Preparar/ejecutar **T12 según el protocolo congelado**, con verificación de referencias y código antes de leer agosto. La autorización específica y sus límites están en `ETAPA_10_CLAUDE.md`: evaluación predictiva fija y simulación secuencial separadas, sin re-selección. Persistencia inicial en artefactos locales y manifiesto; integración de la entrega final en web/nube se hará con la capacidad y restauración verificadas. T11/T13/T14/T15 siguen pendientes. Fecha final 23/10/2026 Lima.
