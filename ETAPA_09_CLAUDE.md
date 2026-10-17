# T10R: cerrar cuatro casos de concurrencia y recuperación

Lee `docs/ESTADO.md`, `docs/TRASPASO.md`, `docs/REVISION_CODEX_09.md`, `docs/T10_CONTRATO.md` y el encargo T10 original `ETAPA_08_CLAUDE.md` solo como contexto. Entrega revisada 9596d26. **Continuar lo existente, no reiniciar T10.** Fecha final 23/10/2026 Lima. Agosto reservado, selección congelada intacta, sin despliegue ni gastos en este encargo.

## Alcance y organización

Corregir R07–R10 con pruebas de las intercalaciones exactas antes de ampliar funcionalidades. Repros privadas de Codex en `artifacts/private/codex_review09_*`: sirven como evidencia del defecto anterior; agregar regresiones mantenidas en `tests/`, sin depender de esos archivos privados para CI.

Un integrador; se permite hasta tres agentes independientes: publicación R07/R08, importación R09, timer R10. El integrador controla contratos compartidos y pruebas finales. No pasar horas repitiendo experimentos o toda la demo en cada intento; guardar traspasos/checkpoints por corrección.

## 1. R07 y R08: publicación y limpieza seguras

- La limpieza no puede borrar una generación que todavía puede renovarse/promoverse. Introducir reserva/invalidez mediante CAS antes de borrar una generación expirada; excluirla de `guard`, `complete_run` y activación posterior. Si heartbeat/complete ganó primero, conservarla. Una relectura sola no basta.
- El takeover debe comparar el lease pertinente en su operación atómica; no robar una publicación cuyo propietario renovó entre lectura y CAS.
- Mantener Mongo standalone, generaciones aisladas y lectura por `children_ref`. No alterar los hijos de corridas completed/superseded ni las dos históricas auditadas. No deshabilitar mantenimiento como solución definitiva.
- Pruebas deterministas: limpieza lee expiración → propietario renueva/promueve/activa → limpieza intenta borrar; la corrida visible conserva todos los hijos. Orden inverso: limpieza reserva → propietario antiguo intenta renovar/completar/escribir; no puede publicar. También heartbeat entre lectura y CAS de takeover, dos limpiadores, intento antiguo regresando, fallos parciales de limpieza y repetición idempotente.

## 2. R09: una fuente aprobada por mes, también con dos importadores

- Sustituir el chequeo no atómico de fuentes por exclusión/reserva durable por mes/fuente antes de las escrituras. Dos archivos distintos del mismo mes no pueden terminar ambos aprobados ni mezclar sus ventas. El perdedor queda rechazado/en cuarentena con motivo legible.
- Conservar schema2, claves de líneas, trazabilidad y controles R01–R04. No crear una limpieza alternativa. Mismo archivo/reintento sigue siendo idempotente.
- Integrar propiedad/recuperación durante la importación: el dueño obsoleto no debe poder finalizar/aprobar ni seguir escribiendo libremente después de que otro intento asuma. Definir cómo se trata una escritura parcial y cómo se mantiene la reserva o se remedia; no liberar un mes parcialmente escrito para otra fuente como si estuviera vacío.
- Pruebas en bases temporales: dos fuentes diferentes del mismo mes sincronizadas después del chequeo; un solo ganador, ninguna fila del perdedor, dataset válido para los meses probados. Reinicio a mitad de importación, reintento de la misma fuente, retorno tardío del dueño anterior y fuente diferente durante esa recuperación. Original de desarrollo conocido continúa sin cambios.
- No probar archivos nuevos sobre demand_forecasting_v2 ni modificar originales. No tocar agosto real; solo un caso sintético de rechazo si lo necesita la regresión.

## 3. R10: recuperar la reserva del temporizador

- Las ranuras error/procesando sin job no equivalen a completadas. Permitir retomar/reconciliar una reserva tras fallo o reinicio, con exclusión apropiada para dos timers.
- Si el job se creó y falló la actualización del tick, recuperar su identidad existente y completar el registro; no duplicar ni generar una corrida nueva innecesaria. Usar la misma clave estándar que API/worker.
- Pruebas: caída después de reservar y antes de encolar, fallo transitorio de enqueue, caída después de crear job y antes de guardar job_id, dos timers recuperando simultáneamente, ranura completada repetida, coalescencia y fechas Lima/UTC.
- Probar `--loop` realmente durante un intervalo corto con worker y Mongo reales en una base aislada, sin esperar al cron diario ni dejar procesos residuales. Reloj controlado/adaptador de prueba válido; no tratar dos `--once` como evidencia de un proceso continuo. Temporizador sigue deshabilitado por defecto.

## 4. Decisiones ya resueltas

- **Mantener activate_run=False para desarrollo T10.** La histórica auditada sigue activa. Enlaces y selector deben abrir exactamente la generada elegida; no agregar activación automática. Si no cambia frontend, no repetir sus 106 pruebas/build por rutina.
- No unificar por completo los validadores ni reformatear scripts ajenos: acotar el cambio a invariantes necesarios. No cambiar fórmulas, cohortes, snapshot ni resultados T07.
- Investigar la corrida staging gen-20260620-d438bef389c9 con el mantenimiento corregido. Documentar su estado/razón y ruta de recuperación; conservar evidencia e históricos. No forzarla a completed/failed para maquillar resultados ni borrar corridas sin plan.
- Los datos siguen históricos y el inventario simulado. No inventar actualidad, observaciones posteriores al origen ni una mejora real de la empresa.

## 5. Verificación y cierre acotados

Ejecutar regresiones nuevas (demostrar que fallaban antes), cola/worker/protocolo/timer/handlers y auth/API afectados, sin RUN_REALDATA que repita T06/T07. Usar ruta temporal corta en Windows si la longitud del workspace causa errores. Las pruebas omitidas se declaran como tales. No leer secretos ni imprimir URI; no repetir pruebas amplias si las correcciones no las afectan.

Evidencia privada `artifacts/private/t10r/`: resultados/JUnit, auditoría de concurrencia e integridad, prueba loop y procesos detenidos. Si no cambió UI, una comprobación dirigida del flujo afectado basta; cualquier demo nueva identifica run_id y origen exactos, evita selectores que solo encuentren una corrida cualquiera y separa resultados ya existentes de ejecución nueva.

Actualizar contrato con la semántica final (incluido max_intentos=5 si se mantiene), `docs/T10R_REPORTE.md`, ESTADO/TRASPASO/BACKLOG/HISTORIAL. Commit local revisando exclusiones; resumen final breve con tareas/commits/pruebas/evidencias/bloqueos/siguiente paso. Detener para revisión Codex; **no comenzar T11/T12 automáticamente**.

## 6. Nube actualizada para el siguiente encargo

Azure for Students ya muestra US$100 disponibles hasta 17/10/2027. Atlas Free demand-forecasting-dev creado en São Paulo; aplicación aún no conectada. No volver a pedir crear las cuentas. Rotación de una contraseña que apareció en captura no confirmada: el usuario la maneja de forma privada, no pedirla por chat ni copiarla a logs/archivos versionados. Crear usuario de aplicación de permisos mínimos será parte de T11.

No hay presupuesto de bolsillo autorizado. La base local ya mide **459,39 MB de datos lógicos + índices**, frente a los 185,48 MB anteriores. T11 requiere inventario de colecciones/corridas y plan de crecimiento/archivo/restauración antes de elegir qué publicar, sin borrar datos ni resultados para encajar. No subir ventas o provisionar servicios en esta corrección.
