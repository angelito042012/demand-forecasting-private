# T10: carga web, cola durable, generación y temporizador

Lee RETOMAR_CLAUDE.md, docs/ESTADO.md, TRASPASO.md, REVISION_CODEX_08.md, T08_CONTRATO.md y DECISIONES_DATOS.md. T08R aceptado al commit 80117c0; R05/R06 cerrados en alcance local. Fecha final 23/10/2026 Lima. Este incremento completa el flujo administrativo **carga→trabajo→corrida publicada**, sin abrir agosto ni repetir experimentos T06/T07. No contratar servicios, iniciar compras ni cambiar la selección congelada.

## 1. Contrato y condiciones previas de concurrencia

Fijar docs/T10_CONTRATO.md antes de repartir archivos: tipos/esquemas de trabajos, estados/transiciones, permisos, idempotencia, límites de archivos, barreras temporales, ownership/lease/reintentos y publicación. Mantener Mongo standalone; no asumir transacciones multidocumento. Un integrador; hasta tres agentes en ámbitos separados (cola/worker, importación/API, frontend/pruebas), sin tocar contratos/lockfiles ajenos simultáneamente.

Antes de habilitar ejecución concurrente:

- Sustituir count-then-insert del login por presupuesto/reserva atómica en Mongo. Definir cómo cuentan intentos fallidos/exitosos y ventanas; probar que una ráfaga del mismo usuario/origen no consigue validar más solicitudes de las permitidas. Mantener 429/Retry-After y errores genéricos, CSRF y --no-proxy-headers local. No agregar Redis u otro servicio sin necesidad.
- Cola y publicación con propiedad por intento: token de dueño, generación/fencing, lease renovable y CAS al reclamar/completar. Un worker muerto puede recuperarse; uno obsoleto no puede borrar hijos de otro intento, completar ni activar. Aislar resultados temporales por intento o mecanismo equivalente; renovar durante trabajo largo y detectar pérdida de propiedad. Nada de comprobar una bandera al inicio y escribir sin protección después.
- Solo se publica una corrida coherente; lectores siguen usando la última válida durante fallos/reintentos. Correcciones de precisión y corridas sustituidas conservadas. Pruebas deterministas de dos trabajadores, expiración/toma de control y retorno tardío del antiguo, incluida limpieza fallida y publicación; no solo dos llamadas secuenciales.

Eliminar el contador/noqa inadecuados de scripts/audit_recommendations.py y dejar estilo limpio en archivos afectados. No cambiar su fórmula para ocultar diferencias.

## 2. Cola, API y worker reales

Colección de jobs durable con job_id único, tipo permitido, identidad de entradas/config/código/corte, creador, UTC, estado queued/running/completed/failed, intento/lease/propietario, resultados/conteos y error público saneado. Índices apropiados; estados extra solo si se implementan y prueban. Reintentos acotados para fallos transitorios, errores de datos permanentes sin bucle infinito. El progreso informa etapas/conteos reales, sin porcentajes inventados.

POST /api/v1/imports (archivo) y POST /api/v1/runs (config tipada permitida) son admin, sesión y CSRF. Devuelven 202 + job_id; no ejecutar parsers, entrenamiento ni publicación larga dentro de la petición. GET /jobs y /jobs/{id} muestran estado autorizado y enlace a importación/corrida, sin rutas privadas, tracebacks o credenciales. Lector no encola ni muta; la API valida permisos aunque el botón esté oculto. No aceptar comandos, nombres de módulo, URI de DB, rutas locales o config arbitraria desde navegador.

Worker CLI independiente de HTTP (módulo apropiado y documentado), con --once para pruebas y modo continuo para demo. Reclama atómicamente, renueva lease, procesa tipos permitidos y deja estado recuperable al cerrar. No usar FastAPI BackgroundTasks o una lista en memoria como única cola. Prueba de reinicio real de proceso con job pendiente/interrumpido y sin duplicar resultado.

## 3. Carga Excel y fuentes aprobadas

Aceptar .xlsx con límites explícitos razonables para estos archivos (por ejemplo 25 MiB comprimidos, 250 MiB expandidos, límites de entradas/filas configurados). Validar extensión/formato/contenido/encabezados y mes, no solo MIME. Evitar expansión ZIP sin límite; nombres del cliente no controlan rutas. Guardado privado bajo ruta de aplicación con nombre interno seguro y sha256; no servir uploads como archivos públicos. Rechazo claro de archivos corruptos, macros/formato no admitido, encabezados erróneos, tamaño o contenido fuera de alcance. No enviar Excel ni datos personales a servicios externos.

Worker reutiliza importador schema2 y reglas R01–R04: ventas/notas de crédito separadas, trazabilidad, conflictos, rechazos, validación y persistencia real. No inventar una segunda limpieza incompatible. Mostrar conteos y motivos legibles; duplicado reconocido se informa como sin cambios, no como nuevas ventas. Mismo archivo/reintento no inserta dos veces.

**Barrera de investigación**: agosto no se carga/consulta desde esta nueva función. Rechazar archivos con fechas fuera de marzo–julio y no permitir flag HTTP que abra el test. Una fuente distinta para un mes ya aprobado no sustituye silenciosamente las seis fuentes auditadas: rechazar o dejar en cuarentena con explicación y ruta de remediación existente; no marcarla aprobada ni contaminar el dataset anterior. En base real demostrar reenvío de un original de desarrollo como no-op, con hashes/conteos/fingerprint anteriores intactos. Archivos de prueba nuevos/corruptos/conflictivos se prueban en bases temporales, sin tocar originales. Documentar límites actuales de sustitución de fuentes.

## 4. Generación del método operativo y publicación

Implementar generación real de **promedio_28 por SKU**, con señales exactas, categorías sumadas desde SKU, fechas naturales y cohortes existentes. No hacer pasar una republicación de T07 como un entrenamiento nuevo. Generación y publicación fuera de la petición, con manifiesto de datos/código/config/señales y procedencia. Mantener la lógica común reutilizable: no duplicar fórmulas de techo ni recalcular pedidos desde CSV truncado.

Para este incremento de desarrollo, la política del servidor limita cortes configurables al intervalo 01/06–10/07/2026 y horizonte máximo21 (así todo objetivo queda <=31/07, sin confundir pronóstico futuro con acceso al test). Configuración administrativa del servidor, no parámetro que el cliente pueda saltarse. Día inicial a demostrar:10/07. No ofrecer una corrida «de hoy» con datos antiguos ni inferir que hay información posterior. Tras evaluación final se ampliará el alcance en un encargo separado.

La entrada de cada corrida es historia aprobada solo hasta su origen. No leer reales posteriores para construir pronósticos, señales o pedidos; observed de una corrida emitida debe quedar desconocido/null salvo que se publique expresamente como backtest distinto. Datos futuros ausentes no son cero. Worker baseline no requiere reentrenar RF/XGBoost ni repetir folds. RF histórico solo puede mostrarse si hay un resultado existente explícitamente compatible con origen/universo; en otro caso comparador no disponible, sin inventarlo. Control cero puede derivarse y debe identificarse como tal.

Para recomendaciones de desarrollo puede reutilizarse el snapshot **histórico simulado** T07 de L7/S7/promedio_28 exactamente al cierre del origen dentro del rango habilitado, con tránsito de pedidos emitidos/recibidos hasta esa fecha y señal exacta del mismo origen. Verificar checksum, índice natural, origen y universo fijo de 3347 SKU de la simulación. Producto sin snapshot continúa sin pedido/stock supuesto; no inicializarlo en0. Sugerencia hipotética, no pedido ejecutado ni simulación nueva. No usar tránsito del final del período. Si un origen no cuenta con snapshot compatible, publicar pronóstico y razón de ausencia de recomendación.

Identidad estable incluye tipo, origen, inputs aprobados, método/parámetros y versión del generador/adaptador. Reintentos o dos administradores para la misma entrada obtienen el mismo resultado lógico sin duplicados; entradas diferentes nunca comparten accidentalmente clave. No cambiar el contenido de una corrida completed. Fallo conserva puntero/última válida; activación solo tras validar conteos, coherencia y propiedad del intento. Nuevos kinds/esquemas de corrida deben extender API/UI y no romper historial T08R ni sus backtests.

## 5. Temporizador verificable, sin nube obligatoria

Preparar tick de scheduler desacoplado que encole el mismo tipo de job, con clave por slotUTC/dataset/config y política explícita de coincidencias/missed ticks. Dos ticks simultáneos o reintentos no duplican. Cronograma y zona horaria documentados; fechas de negocio Lima, timestamps técnicos UTC. Configuración deshabilitada o manual por defecto hasta demostrarla; activación local visible en configuración/guía. El timer no ejecuta experimentos ni el test final.

Probar timer local con intervalo corto/fechas de reloj controladas y worker real; dejar guía para el intervalo normal. Si no hay datos/corte elegible nuevo, registrar sin cambios y conservar resultado anterior; no fabricar actualidad. Adaptador de nube se preparará con T11 según cuentas/presupuesto, sin agregar servicios externos ahora. No instalar tareas del sistema al inicio o dejar procesos ocultos permanentes sin que la guía indique su control.

## 6. Frontend y operación local

Importaciones admin: seleccionar archivo, validar/enviar con CSRF, observar job, ver conteos/rechazos/conflictos/sin cambios. Corridas admin: elegir corte permitido y generar; ver estado/errores y abrir resultado completed. No botones falsos ni progreso simulado. Lector consulta sin controles de escritura y recibe 403 si intenta API directa. Reiniciar página no pierde el job durable; API caída no activa mocks.

Pantallas muestran run seleccionado consistentemente, origen/fechas objetivo/cobertura, antigüedad e inventario simulado. Corrida sin comparador u observaciones maneja null con texto, sin ceros ni métricas inventadas. Ajustar rótulo de comparación: origen G4=10/07 no significa que toda su evaluación acabe el 10/07; backtest/simulación tienen sus períodos propios hasta 31/07. No modificar cifras para corregir ese texto.

Actualizar start/stop-local y guía para worker/timer. Registro de procesos con identidad/fecha de inicio/ejecutable o control equivalente: no matar por un PID reutilizado de una sesión antigua ni detener contenedores ajenos. Modo de un solo worker predeterminado, aunque la toma de control y exclusión deben soportar dos procesos en pruebas. No imprimir secretos ni credenciales de demostración.

## 7. Evidencia y cierre

Tests nuevos y regresiones afectadas: permisos/CSRF, upload truncado/corrupto/límites/duplicado/conflicto/agosto, identidad, exactitud, generación sin futuro, dos workers/ticks, heartbeat/fencing, reinicio, fallo parcial y último válido, login concurrente. Bases temporales; no modificar datos reales de investigación. Pruebas de generación: cambiar datos después del origen no cambia salida; categorías=sumSKU; null para datos no disponibles.

Demostración navegador contra backend/Mongo/worker reales: admin carga un Excel original de desarrollo (no-op), sigue job, genera al10/07, observa completed y abre pronóstico/pedido; falla un archivo sintético en base aislada; lector denegado; reintento/reinicio conserva integridad. Guardar logs/capturas/auditoría en artifacts/private/t10/. Build/tests frontend y pruebas backend pertinentes; evitar repetir T06/T07/costosas por rutina. Concurrencia requiere pruebas activas, no solo revisión de código.

Versionar contrato/config/migraciones no destructivas/guía y T10_REPORTE.md con tipos de job, corrida generada, pruebas realmente ejecutadas y límites. Revisar exclusiones, commit local y ESTADO/TRASPASO/BACKLOG/HISTORIAL al día. Informe final breve y evidencia larga por ruta.

Detener para revisión de Codex al cerrar T10, sin abrir agosto ni declarar publicación. Posteriores T12 evaluación final bajo congelación y T11 HTTPS/nube/backup/restauración, rendimiento, aceptación humana e informe. La pregunta de cuentas/presupuesto está pendiente: avanzar local sin asumir aprobación de gasto ni pedir contraseñas por chat.
